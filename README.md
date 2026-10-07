# Geospatial File Measurement API

Backend service for uploading geospatial files, extracting their features, preserving
their geometry and attributes, and calculating CRS-aware measurements. The project
was built as an SDE Intern geospatial backend assignment and intentionally keeps the
architecture small enough to understand and extend.

## Local working: run it first

The application can be run locally with Python and a PostgreSQL database. The
commands below use the project’s current configuration and migration setup.

### 1. Open the project

```powershell
cd Geospatial_File_Measurement_API
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Python 3.12+ is supported by the project’s Docker image and is recommended for
local development.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

The requirements include FastAPI, Uvicorn, Pydantic, SQLAlchemy, psycopg,
Alembic, GeoPandas, Fiona, Shapely, PyProj, pytest, and HTTPX.

### 4. Configure environment variables

Copy the template and edit the local configuration:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`. Set `DATABASE_URL` to the PostgreSQL instance available to
the local application, for example:

```text
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/geospatial_db
```

The complete configuration reference is in [Configuration](#configuration).

### 5. Start PostgreSQL

For local execution, PostgreSQL must be running and the database named in
`DATABASE_URL` must be available. The application does not create a PostgreSQL
server for a local Python run.

### 6. Apply database migrations

Run migrations from the project root:

```powershell
alembic upgrade head
```

The current migration head creates the `files` and `features` tables and adds the
stored measurement CRS column.

### 7. Start FastAPI

```powershell
uvicorn app.main:app --reload
```

The API listens on `http://localhost:8000` by default.

### 8. Open Swagger

Open [http://localhost:8000/docs](http://localhost:8000/docs). FastAPI also
provides `/redoc` and `/openapi.json`.

### 9. Upload a supported file

Use Swagger’s `POST /api/files/` operation or:

```powershell
curl.exe -F "file=@survey.kml" http://localhost:8000/api/files/
```

The backend validates the upload, processes its features, detects the source CRS,
selects or preserves a measurement CRS, calculates supported measurements, and
persists the normalized file and feature records.

### 10. Retrieve the result

Use the returned file ID:

```text
GET /api/files/{file_id}/
GET /api/files/{file_id}/measurements/
```

`GET /health` returns a lightweight application liveness response:

```json
{"status": "ok"}
```

## What the application does

The end-to-end processing path is:

```text
Client
  -> FastAPI controller
  -> upload and archive validation
  -> FileService
  -> GeoPandas/Fiona geospatial reading
  -> CRS detection and transformation
  -> MeasurementService
  -> SQLAlchemy FileRecord and FeatureRecord
  -> PostgreSQL
  -> typed API response
```

Responsibilities are separated as follows:

- `file_controller.py` defines the HTTP routes, dependency injection, response
  models, and HTTP-level error mapping.
- `file_validator.py` checks filenames, extensions, KML signatures, ZIP structure,
  archive paths, required Shapefile components, and size limits.
- `file_service.py` coordinates upload storage, file status transitions, feature
  persistence, transaction handling, and cleanup.
- `geospatial_service.py` reads KML or an extracted Shapefile, normalizes
  properties, serializes geometry to GeoJSON-style dictionaries, and delegates
  measurement.
- `crs_service.py` validates CRS metadata, chooses a local UTM CRS for geographic
  data, transforms geometries, and preserves suitable projected CRSs.
- `measurement_service.py` calculates area or length and returns explicit
  measurement status and messages.
- SQLAlchemy models persist file and feature data.

## Architecture

The project uses a small MVC-inspired layered structure:

```text
Controller/API layer
        |
        v
Service layer
        |
        v
SQLAlchemy models and database session
```

Controllers are intentionally thin. Geospatial and measurement rules stay in
services, while database models describe persistence. This makes the processing
pipeline testable without putting area, length, or CRS logic into route handlers.

## Project structure

```text
Geospatial_File_Measurement_API/
├── app/
│   ├── controllers/
│   │   └── file_controller.py
│   ├── models/
│   │   ├── database.py
│   │   ├── file_model.py
│   │   └── feature_model.py
│   ├── schemas/
│   │   └── file_schema.py
│   ├── services/
│   │   ├── file_service.py
│   │   ├── geospatial_service.py
│   │   ├── measurement_service.py
│   │   └── crs_service.py
│   ├── utils/
│   │   ├── file_validator.py
│   │   └── exceptions.py
│   ├── config.py
│   └── main.py
├── tests/
│   ├── test_upload.py
│   ├── test_measurements.py
│   ├── test_crs.py
│   └── test_validation.py
├── sample_data/
│   └── README.md
├── uploads/
│   └── .gitkeep
├── alembic/
│   ├── versions/
│   │   ├── 0001_initial.py
│   │   └── 0002_measurement_crs.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
└── README.md
```

## Technology stack

| Area | Technology |
|---|---|
| API | FastAPI, Uvicorn |
| Validation and settings | Pydantic v2, pydantic-settings |
| Persistence | SQLAlchemy 2.x, PostgreSQL, psycopg |
| Migrations | Alembic |
| Geospatial I/O | GeoPandas, Fiona |
| Geometry | Shapely |
| CRS and projection | PyProj |
| Tests | Pytest, HTTPX |
| Deployment | Docker, Docker Compose |

## Supported input formats

### KML

`.kml` uploads are read with GeoPandas using the KML driver. Multiple placemarks
are processed as individual features. KML properties exposed by the reader are
normalized into JSON-compatible values.

### Shapefile ZIP

`.zip` uploads must contain exactly one Shapefile layer. The archive must include
matching `.shp`, `.shx`, and `.dbf` components. A `.prj` file is strongly
recommended because it supplies the source CRS needed for trustworthy
measurements.

Archives containing multiple independent `.shp` layers are rejected rather than
choosing one arbitrarily. An archive without a readable Shapefile is rejected.
The `sample_data/README.md` describes how to supply private or local datasets
without committing them.

## Geospatial processing and measurements

For every feature, the service attempts to preserve:

- deterministic source feature index
- geometry type
- GeoJSON-style geometry dictionary
- JSON-compatible properties
- source file CRS at file level
- measurement value, unit, CRS, status, and message

Supported measurements are:

| Geometry | Measurement |
|---|---|
| `Polygon` | Area |
| `MultiPolygon` | Combined area |
| `LineString` | Length |
| `MultiLineString` | Combined length |
| `Point` | `NOT_APPLICABLE`, no value |
| `MultiPoint` | `NOT_APPLICABLE`, no value |
| Other geometry types | `UNSUPPORTED`, no value |

Empty or missing geometries are marked `UNAVAILABLE`. Invalid measurable
geometries are marked `INVALID` rather than silently producing a potentially
misleading value. A feature-level measurement problem does not discard other
features in the same successfully parsed file.

Property serialization handles nulls, NumPy scalar values, datetime-like values,
`NaN`, and non-finite values without returning invalid JSON. Missing values become
`null`; non-finite numeric measurements are never returned as `NaN` or infinity.

## CRS handling

EPSG:4326 is a geographic CRS: its coordinates are longitude and latitude in
angular degrees. Shapely’s planar `area` and `length` operations on those raw
coordinates do not represent real-world square meters or meters. Therefore the
service does not directly measure geographic coordinates.

The current CRS behavior is:

1. If the source CRS is geographic, the service obtains a representative point
   from the geometry.
2. It calculates the UTM zone from longitude, clamped to zones 1 through 60.
3. It selects the northern or southern UTM hemisphere from latitude.
4. It transforms the geometry with GeoPandas/PyProj.
5. It measures the transformed geometry.
6. The selected measurement CRS is stored on each feature and exposed when all
   returned measurements share one measurement CRS.

For already projected data, the service avoids unnecessary transformation. If the
projected CRS uses meters, area is reported in `m²` and length in `m`. Other
projected units are retained in the measurement metadata rather than being
incorrectly labeled as meters.

If the source CRS is missing, the service does not guess EPSG:4326. Measurement
values remain unavailable with a clear message. Invalid CRS metadata is handled
similarly and does not expose an internal traceback.

The UTM strategy is appropriate for local or regional data. A very large dataset
spanning multiple UTM zones may need a more advanced local, equal-area, or
multi-zone projection strategy in future.

## REST API

All file routes are under `/api/files`.

### `GET /health`

Checks application availability without performing database or geospatial work.

Response:

```json
{
  "status": "ok"
}
```

### `POST /api/files/`

Accepts `multipart/form-data` with one field named `file`.

```bash
curl -F "file=@survey.kml" http://localhost:8000/api/files/
```

Example response:

```json
{
  "id": "4e790523-d36e-42fb-a4ef-7ec9a18c3935",
  "original_filename": "survey.kml",
  "file_type": ".kml",
  "feature_count": 3,
  "source_crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2026-10-07T17:54:58",
  "updated_at": "2026-10-07T17:54:58"
}
```

Important statuses include:

- `201` successful processing
- `400` invalid or malformed geospatial input
- `413` upload exceeds the configured size limit
- `415` unsupported extension
- `422` request validation failure
- `500` unexpected server failure

### `GET /api/files/{file_id}/`

Returns persisted file metadata:

```json
{
  "id": "4e790523-d36e-42fb-a4ef-7ec9a18c3935",
  "original_filename": "survey.kml",
  "file_type": ".kml",
  "feature_count": 3,
  "source_crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2026-10-07T17:54:58",
  "updated_at": "2026-10-07T17:54:58"
}
```

An unknown ID returns `404` with:

```json
{"detail": "File was not found."}
```

### `GET /api/files/{file_id}/measurements/`

Returns feature-level measurement results:

```json
{
  "file_id": "4e790523-d36e-42fb-a4ef-7ec9a18c3935",
  "filename": "survey.kml",
  "source_crs": "EPSG:4326",
  "measurement_crs": "EPSG:32643",
  "measurements": [
    {
      "feature_id": 0,
      "geometry_type": "Polygon",
      "measurement_type": "area",
      "value": 12051.54471573999,
      "unit": "m²",
      "status": "AVAILABLE",
      "message": null
    },
    {
      "feature_id": 2,
      "geometry_type": "Point",
      "measurement_type": null,
      "value": null,
      "unit": null,
      "status": "NOT_APPLICABLE",
      "message": "Point geometries do not have area or length measurements."
    }
  ]
}
```

The endpoint returns `404` for an unknown file ID. `measurement_crs` is returned
when the file’s measurable features share one selected CRS; it is `null` when
there is no single CRS to report.

## Database design

The application uses PostgreSQL through SQLAlchemy. Database sessions are created
per request and closed by the FastAPI dependency.

### `files`

The `FileRecord` model stores:

- UUID string ID
- original filename
- UUID-based stored filename
- file type
- feature count
- source CRS
- `PROCESSING`, `COMPLETED`, or `FAILED` status
- safe error message when applicable
- created and updated timestamps

### `features`

The `FeatureRecord` model stores:

- database feature ID
- foreign key to the uploaded file
- source feature index
- geometry type
- GeoJSON geometry in JSON
- normalized properties in JSON
- area and area unit
- length and length unit
- selected measurement CRS
- measurement status and message

Features have a foreign key to their file and are configured with delete-orphan
cascade behavior.

Alembic is the schema authority; the application does not use SQLAlchemy
`create_all()` as its migration strategy:

```powershell
alembic upgrade head
alembic downgrade -1
```

The migration history is:

- `0001_initial`: creates `files`, `features`, and the feature file index.
- `0002_measurement_crs`: adds `features.measurement_crs`.

## Security and validation

The upload path includes:

- allowed extension validation (`.kml` and `.zip`)
- empty-file rejection
- KML content recognition rather than trusting only MIME type
- configurable upload-size limit
- ZIP validity checks
- required `.shp`, `.shx`, and `.dbf` checks
- single-Shapefile archive enforcement
- cumulative extracted-size limit
- POSIX traversal protection
- Windows traversal and drive-path protection
- absolute-path protection
- UUID-based internal storage names
- temporary directory extraction for ZIP processing
- cleanup of the stored upload after processing
- client-safe error messages
- no server filesystem paths in API responses
- SQLAlchemy-based parameterized database access
- `.env` excluded by `.gitignore`

The configured upload limit is read as megabytes and converted to bytes by
`app/config.py`. The upload service reads at most one byte beyond that limit so
oversized uploads can be rejected without reading an unbounded request body.

## Reliability and error handling

The service creates a file record in `PROCESSING`, parses and measures features,
adds feature records, and commits the completed transaction. If file-level
processing fails, incomplete feature work is rolled back and the file is marked
`FAILED` with a safe error message. Unexpected details are logged server-side;
tracebacks and internal paths are not returned to clients.

A measurable feature can fail independently because of invalid, empty, missing,
unsupported, or CRS-unavailable geometry. Such a feature is preserved with an
explicit measurement status while other valid features continue to be processed.

## Testing

Run the test suite from the project root:

```powershell
pytest
pytest -v
```

The tests are self-contained and use generated or in-memory fixtures rather than
requiring private datasets. They cover:

- health and API route behavior
- KML upload and complete retrieval lifecycle
- temporary Shapefile creation, ZIP upload, attribute preservation, and
  measurement persistence
- unsupported, empty, malformed, and oversized uploads
- missing Shapefile components
- multiple-file archive behavior
- ZIP traversal attempts, including Windows-style paths
- geographic, projected, northern-hemisphere, southern-hemisphere, and boundary
  CRS behavior
- Polygon, MultiPolygon, LineString, MultiLineString, Point, MultiPoint,
  zero-length, invalid, empty, and unsupported geometries
- OpenAPI route and multipart schema generation

## Docker Compose

The repository’s `docker-compose.yml` defines only two services:

- `db`: PostgreSQL 16 Alpine, with database `geospatial_db`, user `postgres`,
  a health check using `pg_isready`, and a named `postgres_data` volume.
- `api`: the FastAPI application built from `Dockerfile`, exposed on host port
  `8000`, with the local `uploads` directory mounted at `/app/uploads`.

Inside Compose, the API receives a database URL using the service hostname
`db`, not `localhost`. This is separate from the host-local `.env` value, where
`localhost` is appropriate for a PostgreSQL server running on the host.

Start the Compose deployment with:

```powershell
docker compose up --build
```

The API service waits for the database health check, runs:

```text
alembic upgrade head
```

and then starts:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

With Compose running, use:

- API: [http://localhost:8000](http://localhost:8000)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- PostgreSQL data volume: `postgres_data`

Stop the services with:

```powershell
docker compose down
```

This README documents the configured Docker workflow; Docker execution depends
on Docker Desktop or another working Docker Engine on the machine.

## Configuration

`.env.example` is the configuration template:

| Variable | Purpose | Example/default |
|---|---|---|
| `APP_NAME` | FastAPI application title | `Geospatial File Measurement API` |
| `APP_ENV` | Application environment label | `development` |
| `LOG_LEVEL` | Python logging level | `INFO` |
| `DATABASE_URL` | SQLAlchemy database URL | `postgresql+psycopg://...` |
| `MAX_UPLOAD_SIZE_MB` | Maximum uploaded request file size | `25` |
| `MAX_EXTRACTED_SIZE_MB` | Maximum cumulative ZIP expansion | `100` |
| `UPLOAD_DIRECTORY` | Local temporary upload storage directory | `uploads` |
| `ALLOWED_FILE_EXTENSIONS` | Comma-separated accepted extensions | `.kml,.zip` |

Settings are loaded through Pydantic Settings from `.env` and environment
variables. The actual `.env` is local configuration and must not be committed.

## Design decisions

- **FastAPI** provides typed request handling, dependency injection, automatic
  OpenAPI documentation, and a concise API layer.
- **Service separation** keeps file orchestration, geospatial parsing, CRS
  transformation, and measurement rules independently understandable.
- **GeoPandas, Fiona, Shapely, and PyProj** provide format reading, geometry
  operations, and coordinate transformation rather than custom GIS logic.
- **PostgreSQL and SQLAlchemy** provide durable relational persistence for files
  and processed features without requiring a spatial database extension.
- **JSON geometry and properties** preserve GeoJSON-compatible feature data while
  keeping the schema understandable for this assignment.
- **Synchronous processing** keeps the upload-to-result transaction direct and
  easy to debug for the expected assignment-sized inputs.
- **UTM selection** provides a practical local metric projection for geographic
  coordinates without pretending one global UTM zone is correct for every
  dataset.
- **Temporary extraction** limits the lifetime and location of extracted archive
  contents and avoids permanently storing arbitrary archive members.
- **Alembic migrations** make the database schema reproducible instead of relying
  on implicit table creation.

## Current scope and limitations

Currently implemented:

- synchronous KML and single-layer Shapefile ZIP uploads
- local upload storage during processing
- PostgreSQL persistence through SQLAlchemy
- JSON/GeoJSON feature storage
- CRS-aware measurements
- API documentation and automated tests
- Docker Compose configuration for the API and PostgreSQL

Current limitations:

- only KML and Shapefile ZIP inputs are supported
- one Shapefile layer is accepted per archive
- local storage is used instead of object storage
- processing is synchronous
- no pagination is implemented for very large feature collections
- UTM selection is a local strategy and is not ideal for continent-scale or
  global datasets
- the health endpoint reports application liveness and does not perform a
  database health query
- authentication, authorization, rate limiting, and frontend functionality are
  not part of this assignment

## Future scope

Possible future improvements, not current features, include:

- GeoJSON and raster input support
- PostGIS geometry columns and spatial queries
- S3 or another object-storage backend
- background processing with Celery and Redis
- larger-file streaming and pagination
- advanced projection strategies for multi-zone datasets
- authentication and authorization
- rate limiting, metrics, tracing, and broader observability

## Assignment scope

This implementation focuses on the requested backend fundamentals:

- Python and object-oriented service design
- FastAPI REST endpoints
- SQL and relational persistence
- Alembic migrations
- secure file handling
- geospatial feature processing
- CRS-aware GIS measurements
- Docker readiness
- deterministic automated testing

It deliberately does not add a frontend, message broker, microservices, or
cloud credentials because those are outside the assignment’s minimum scope.

## Author

Prepared as an SDE Intern take-home assignment implementation for Aereo.
