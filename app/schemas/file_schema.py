from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    original_filename: str
    file_type: str
    feature_count: int
    source_crs: str | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class MeasurementResponse(BaseModel):
    feature_id: int
    geometry_type: str | None
    measurement_type: str | None
    value: float | None
    unit: str | None
    status: str
    message: str | None


class MeasurementsResponse(BaseModel):
    file_id: str
    filename: str
    source_crs: str | None
    measurement_crs: str | None
    measurements: list[MeasurementResponse]


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
