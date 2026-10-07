import io
import zipfile
from pathlib import PurePosixPath, PureWindowsPath

from app.config import Settings
from app.utils.exceptions import InvalidGeospatialFileError, UnsafeArchiveError, UnsupportedFileTypeError, UploadTooLargeError


def validate_filename(filename: str | None, settings: Settings) -> str:
    if not filename:
        raise InvalidGeospatialFileError("Uploaded file must have a filename.")
    extension = PureWindowsPath(filename).suffix.lower()
    if extension not in settings.allowed_file_extensions:
        raise UnsupportedFileTypeError("Only KML files and ZIP Shapefile archives are supported.")
    return extension


def validate_upload_bytes(data: bytes, extension: str, settings: Settings) -> None:
    if not data:
        raise InvalidGeospatialFileError("Uploaded file is empty.")
    if len(data) > settings.max_upload_size_bytes:
        raise UploadTooLargeError("Uploaded file exceeds the configured size limit.")
    if extension == ".zip":
        validate_shapefile_archive(data, settings)
    elif not data.lstrip().startswith(b"<?xml") and b"<kml" not in data[:4096].lower():
        raise InvalidGeospatialFileError("Uploaded file is not a recognizable KML document.")


def validate_shapefile_archive(data: bytes, settings: Settings) -> list[str]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise InvalidGeospatialFileError("Uploaded ZIP archive is malformed.") from exc
    total_size = 0
    shapefiles: set[str] = set()
    for member in archive.infolist():
        name = member.filename
        posix = PurePosixPath(name)
        windows = PureWindowsPath(name)
        if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts or ".." in windows.parts:
            raise UnsafeArchiveError("ZIP archive contains an unsafe path.")
        if member.is_dir():
            continue
        total_size += member.file_size
        if total_size > settings.max_extracted_size_bytes:
            raise UnsafeArchiveError("ZIP archive expands beyond the configured extraction limit.")
        if posix.suffix.lower() == ".shp":
            shapefiles.add(str(posix.with_suffix("")).lower())
    if not shapefiles:
        raise InvalidGeospatialFileError("Uploaded archive does not contain a Shapefile.")
    if len(shapefiles) > 1:
        raise InvalidGeospatialFileError("Uploaded archive contains multiple Shapefiles; provide one layer per archive.")
    stem = next(iter(shapefiles))
    names = {PurePosixPath(item.filename).with_suffix("").as_posix().lower() for item in archive.infolist() if not item.is_dir()}
    required = {stem}
    if not required.issubset(names):
        raise InvalidGeospatialFileError("Uploaded archive is missing its .shp component.")
    if not any(PurePosixPath(item.filename).with_suffix("").as_posix().lower() == stem and PurePosixPath(item.filename).suffix.lower() == ".dbf" for item in archive.infolist()):
        raise InvalidGeospatialFileError("Uploaded Shapefile archive is missing its .dbf component.")
    if not any(PurePosixPath(item.filename).with_suffix("").as_posix().lower() == stem and PurePosixPath(item.filename).suffix.lower() == ".shx" for item in archive.infolist()):
        raise InvalidGeospatialFileError("Uploaded Shapefile archive is missing its .shx component.")
    return [stem]
