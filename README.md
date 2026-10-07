# Geospatial File Measurement API

FastAPI service that securely accepts KML files or single-layer Shapefile ZIP
archives, stores normalized feature data, and calculates defensible area/length
measurements.

## Features and architecture

The request path is `Controller -> FileService -> GeospatialService -> CRSService /
MeasurementService -> SQLAlchemy models`. Controllers only handle HTTP concerns;
services own processing and models own persistence. GeoJSON geometry and normalized
properties are stored as JSON, avoiding a PostGIS requirement while retaining
portable PostgreSQL persistence.

## Stack

Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL/psycopg,
GeoPandas, Fiona, Shapely, PyProj, pytest and HTTPX.

## Setup

1. Copy `.env.example` to `.env` and set `DATABASE_URL` (do not commit `.env`).
2. Create a Python 3.12 virtual environment and install `pip install -r requirements.txt`.
3. Start PostgreSQL and run `alembic upgrade head`.
4. Start the API with `uvicorn app.main:app --reload`.

The Docker path is `docker compose up --build`; it starts PostgreSQL, waits for
its health check, applies migrations, and starts the API. PostgreSQL data is
stored in the `postgres_data` volume.

## Configuration

`DATABASE_URL`, `MAX_UPLOAD_SIZE_MB`, `MAX_EXTRACTED_SIZE_MB`,
`UPLOAD_DIRECTORY`, `ALLOWED_FILE_EXTENSIONS`, `APP_NAME`, `APP_ENV`, and
`LOG_LEVEL` are configurable. Defaults are suitable for local development except
for the database, which should be explicitly configured.

## API

Interactive documentation is available at `/docs`, ReDoc at `/redoc`, and the
OpenAPI document at `/openapi.json`.

### `GET /health`

Returns `{"status":"ok"}`. This is an application liveness check and does not
claim database availability.

### `POST /api/files/`

Send `multipart/form-data` with a `file` field:

```bash
curl -F "file=@survey.kml" http://localhost:8000/api/files/
```

The response contains the public UUID, original filename, file type, feature count,
source CRS, status, timestamps, and a safe error message when applicable.
Possible errors include 400 invalid content, 413 size limit, 415 unsupported
extension, and 500 unexpected server failure.

Example successful response:

```json
{
  "id": "4e790523-d36e-42fb-a4ef-7ec9a18c3935",
  "original_filename": "survey.kml",
  "file_type": ".kml",
  "feature_count": 3,
  "source_crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null
}
```

For a Shapefile, create a ZIP containing the matching `.shp`, `.shx`, and `.dbf`
files, plus a `.prj` file for trustworthy measurements:

```bash
zip survey.zip survey.shp survey.shx survey.dbf survey.prj
curl -F "file=@survey.zip" http://localhost:8000/api/files/
```

### `GET /api/files/{id}/`

Returns persisted file metadata. Unknown IDs return 404.

### `GET /api/files/{id}/measurements/`

Returns one measurement record per source feature. Polygon/MultiPolygon values are
areas; LineString/MultiLineString values are lengths; Point/MultiPoint are
`NOT_APPLICABLE`; unsupported, empty, invalid, or unknown-CRS features retain
their geometry and properties with a null measurement and explanatory status.

## Geospatial and CRS behavior

Latitude/longitude in EPSG:4326 are angular degrees, not a constant physical unit,
so Shapely's planar `.area` and `.length` on them are not real-world measurements.
For geographic CRS data, the service chooses a UTM zone from a representative
point, uses the correct northern or southern hemisphere EPSG code, transforms with
PyProj/GeoPandas, then measures in meters. Projected metric CRS data is measured
without unnecessary transformation. Other projected units retain their native
unit description rather than being mislabeled as meters.

Missing or invalid CRS never defaults to EPSG:4326: measurements become
`UNAVAILABLE`. UTM is a practical local strategy; very large datasets spanning
multiple zones may need a local or equal-area projection strategy in future.

Invalid geometries are not globally rewritten. They are detected and preserved;
measurement errors are isolated to the feature and do not discard other valid
features.

## Security and reliability

Uploads use UUID storage names, extension/content checks, size limits, strict ZIP
member path validation, extracted-size limits, temporary extraction directories,
and client-safe errors. Original filenames are metadata only. Database commits
occur after feature processing; failures roll back incomplete inserts and mark the
file failed where possible. No secrets, cloud credentials, authentication,
permissive CORS, or paid APIs are required.

## Testing and migration

Run `pytest`. Tests generate small in-memory geometries and cover measurements,
UTM selection, missing CRS, upload validation, traversal protection, and the
health endpoint. Additional manual API lifecycle tests should use a local
PostgreSQL instance or Docker.

Alembic is the schema authority:

```bash
alembic upgrade head
alembic downgrade -1
```

The current migration head is `0002_measurement_crs`; it adds the selected
projected CRS used for a feature's measurement.

## Project structure

`app/controllers` contains HTTP routes; `app/services` contains upload,
geospatial, CRS, and measurement logic; `app/models` contains database mappings;
`app/schemas` contains explicit API models; `app/utils` contains validation and
application exceptions; `alembic` contains migrations; `tests` contains
deterministic checks.

## Limitations and future scope

Current support is KML and one Shapefile layer per ZIP, synchronous processing,
local file storage, and JSON geometry storage. Future improvements could include
GeoJSON/raster support, S3, pagination, PostGIS spatial queries, advanced
projection selection, Celery/Redis for very large files, authentication and
authorization, rate limiting, metrics, tracing, and distributed processing.

## Design decisions and learning

FastAPI provides typed request/response contracts and useful OpenAPI output.
GeoPandas and Fiona handle supported file formats, Shapely provides geometry
operations, and PyProj performs CRS transformations. PostgreSQL with SQLAlchemy
and Alembic gives durable relational persistence without requiring PostGIS for
this assignment. Processing is synchronous to keep transaction behavior and
debugging straightforward; Celery/Redis can be introduced later for large
uploads. Temporary directories isolate archive extraction, UUID storage names
avoid trusting filenames, and UTM provides a defensible local metric projection.
JSON/GeoJSON storage keeps the schema understandable while preserving geometry
and attributes. Authentication, cloud object storage, rate limiting, and
PostGIS are intentionally future scope rather than claimed capabilities.
