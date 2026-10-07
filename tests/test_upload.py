import zipfile
from collections.abc import Generator
from pathlib import Path

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.main import app
from app.models.database import Base
from app.models.database import get_db as production_get_db
from app.controllers import file_controller


@pytest.fixture()
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_directory=tmp_path / "uploads",
    )

    def get_test_db() -> Generator[Session, None, None]:
        db = sessions()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[production_get_db] = get_test_db
    monkeypatch.setattr(file_controller, "get_settings", lambda: settings)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def kml_fixture() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
      <Placemark><name>parcel</name><description>10</description>
        <Polygon><outerBoundaryIs><LinearRing><coordinates>
          77,12,0 77.001,12,0 77.001,12.001,0 77,12.001,0 77,12,0
        </coordinates></LinearRing></outerBoundaryIs></Polygon>
      </Placemark>
      <Placemark><name>route</name><LineString><coordinates>77,12,0 77.002,12,0</coordinates></LineString></Placemark>
      <Placemark><name>marker</name><Point><coordinates>77,12,0</coordinates></Point></Placemark>
    </Document></kml>"""


def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_kml_upload_lifecycle_and_persistence(api_client: TestClient) -> None:
    response = api_client.post("/api/files/", files={"file": ("survey.kml", kml_fixture(), "application/octet-stream")})
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["original_filename"] == "survey.kml"
    assert payload["feature_count"] == 3
    assert payload["source_crs"] == "EPSG:4326"
    assert payload["status"] == "COMPLETED"

    file_id = payload["id"]
    detail = api_client.get(f"/api/files/{file_id}/")
    measurements = api_client.get(f"/api/files/{file_id}/measurements/")
    assert detail.status_code == 200
    assert measurements.status_code == 200
    measurement_payload = measurements.json()
    assert measurement_payload["measurement_crs"] == "EPSG:32643"
    assert [item["geometry_type"] for item in measurement_payload["measurements"]] == ["Polygon", "LineString", "Point"]
    assert measurement_payload["measurements"][0]["value"] > 0
    assert measurement_payload["measurements"][1]["value"] > 0
    assert measurement_payload["measurements"][2]["status"] == "NOT_APPLICABLE"


def test_shapefile_zip_upload_preserves_attributes(api_client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    frame = gpd.GeoDataFrame(
        {"name": ["line"], "count": [3]},
        geometry=[LineString([(0, 0), (100, 0)])],
        crs="EPSG:3857",
    )
    frame.to_file(source / "survey.shp", driver="ESRI Shapefile")
    archive_path = tmp_path / "survey.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for component in source.iterdir():
            archive.write(component, component.name)

    response = api_client.post("/api/files/", files={"file": ("survey.zip", archive_path.read_bytes(), "application/zip")})
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["feature_count"] == 1
    assert payload["source_crs"] == "EPSG:3857"
    measurements = api_client.get(f"/api/files/{payload['id']}/measurements/").json()
    assert measurements["measurements"][0]["value"] == pytest.approx(100)


def test_invalid_uploads_and_missing_ids(api_client: TestClient) -> None:
    assert api_client.post("/api/files/", files={"file": ("empty.kml", b"")}).status_code == 400
    assert api_client.post("/api/files/", files={"file": ("notes.txt", b"hello")}).status_code == 415
    assert api_client.post("/api/files/", files={"file": ("bad.kml", b"<kml>")}).status_code == 400
    assert api_client.get("/api/files/not-found/").status_code == 404
    assert api_client.get("/api/files/not-found/measurements/").status_code == 404


def test_openapi_documents_all_endpoints(api_client: TestClient) -> None:
    document = api_client.get("/openapi.json").json()
    assert {"/health", "/api/files/", "/api/files/{file_id}/", "/api/files/{file_id}/measurements/"} <= set(document["paths"])
    assert "multipart/form-data" in document["paths"]["/api/files/"]["post"]["requestBody"]["content"]
