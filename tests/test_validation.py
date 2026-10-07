import io
import zipfile

import pytest

from app.config import Settings
from app.utils.exceptions import InvalidGeospatialFileError, UnsafeArchiveError, UploadTooLargeError
from app.utils.file_validator import validate_shapefile_archive, validate_upload_bytes


def settings() -> Settings:
    return Settings(database_url="sqlite:///test.db", max_upload_size_mb=1)


def archive(*members: tuple[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as value:
        for name, content in members:
            value.writestr(name, content)
    return stream.getvalue()


def test_valid_shapefile_components_are_recognized() -> None:
    data = archive(("survey.shp", b"x"), ("survey.shx", b"x"), ("survey.dbf", b"x"))
    assert validate_shapefile_archive(data, settings()) == ["survey"]


def test_archive_traversal_is_rejected() -> None:
    data = archive(("../survey.shp", b"x"))
    with pytest.raises(UnsafeArchiveError):
        validate_shapefile_archive(data, settings())
    with pytest.raises(UnsafeArchiveError):
        validate_shapefile_archive(archive((r"..\..\evil.shp", b"x")), settings())


def test_missing_components_and_malformed_uploads_are_rejected() -> None:
    with pytest.raises(InvalidGeospatialFileError):
        validate_shapefile_archive(archive(("survey.shp", b"x")), settings())
    with pytest.raises(InvalidGeospatialFileError):
        validate_upload_bytes(b"", ".kml", settings())


def test_upload_size_limit_is_enforced() -> None:
    with pytest.raises(UploadTooLargeError) as error:
        validate_upload_bytes(b"x" * (1024 * 1024 + 1), ".kml", settings())
    assert "size limit" in str(error.value)
