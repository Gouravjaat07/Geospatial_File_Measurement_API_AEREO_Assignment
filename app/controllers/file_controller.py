import logging

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.database import get_db
from app.models.file_model import FileRecord
from app.schemas.file_schema import ErrorResponse, FileResponse, MeasurementResponse, MeasurementsResponse
from app.services.file_service import FileService
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/files", tags=["files"])


@router.post(
    "/",
    response_model=FileResponse,
    status_code=201,
    summary="Upload and measure a geospatial file",
    description="Accept one KML file or a ZIP containing exactly one Shapefile layer.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid geospatial input."},
        413: {"model": ErrorResponse, "description": "Upload exceeds the configured size limit."},
        415: {"model": ErrorResponse, "description": "Unsupported file type."},
        422: {"model": ErrorResponse, "description": "Request validation failed."},
        500: {"model": ErrorResponse, "description": "Unexpected server error."},
    },
)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)) -> FileRecord:
    return await FileService(db, get_settings()).process_upload(file)


def _get_file(file_id: str, db: Session) -> FileRecord:
    record = db.get(FileRecord, file_id)
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File was not found.")
    return record


@router.get(
    "/{file_id}/",
    response_model=FileResponse,
    summary="Get processed file information",
    responses={404: {"model": ErrorResponse, "description": "File was not found."}},
)
def get_file(file_id: str, db: Session = Depends(get_db)) -> FileRecord:
    return _get_file(file_id, db)


@router.get(
    "/{file_id}/measurements/",
    response_model=MeasurementsResponse,
    summary="Get measurements for a processed file",
    responses={404: {"model": ErrorResponse, "description": "File was not found."}},
)
def get_measurements(file_id: str, db: Session = Depends(get_db)) -> MeasurementsResponse:
    record = _get_file(file_id, db)
    measurements = []
    measurement_crs_values = set()
    for feature in record.features:
        if feature.measurement_crs:
            measurement_crs_values.add(feature.measurement_crs)
        value = feature.area if feature.area is not None else feature.length
        unit = feature.area_unit if feature.area is not None else feature.length_unit
        measurement_type = "area" if feature.area is not None else "length" if feature.length is not None else None
        measurements.append(MeasurementResponse(feature_id=feature.feature_index, geometry_type=feature.geometry_type, measurement_type=measurement_type, value=value, unit=unit, status=feature.measurement_status, message=feature.measurement_message))
    measurement_crs = next(iter(measurement_crs_values), None) if len(measurement_crs_values) == 1 else None
    return MeasurementsResponse(file_id=record.id, filename=record.original_filename, source_crs=record.source_crs, measurement_crs=measurement_crs, measurements=measurements)
