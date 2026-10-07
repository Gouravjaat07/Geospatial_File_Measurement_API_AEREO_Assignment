import math
from dataclasses import dataclass

from shapely.geometry.base import BaseGeometry

from app.services.crs_service import measurement_context
from app.utils.exceptions import CRSProcessingError


@dataclass(frozen=True)
class MeasurementResult:
    measurement_type: str | None
    value: float | None
    unit: str | None
    status: str
    message: str | None
    measurement_crs: str | None


def measure_geometry(geometry: BaseGeometry | None, source_crs: object) -> MeasurementResult:
    if geometry is None:
        return MeasurementResult(None, None, None, "UNAVAILABLE", "Measurement unavailable because geometry is missing.", None)
    if geometry.is_empty:
        return MeasurementResult(None, None, None, "UNAVAILABLE", "Measurement unavailable because geometry is empty.", None)
    geometry_type = geometry.geom_type
    if geometry_type in {"Point", "MultiPoint"}:
        return MeasurementResult(None, None, None, "NOT_APPLICABLE", "Point geometries do not have area or length measurements.", None)
    if geometry_type not in {"Polygon", "MultiPolygon", "LineString", "MultiLineString"}:
        return MeasurementResult(None, None, None, "UNSUPPORTED", f"Geometry type {geometry_type} is not supported for measurement.", None)
    if geometry_type in {"LineString", "MultiLineString"} and geometry.length == 0:
        try:
            context = measurement_context(geometry, source_crs)
            return MeasurementResult("length", 0.0, context.linear_unit, "AVAILABLE", None, context.measurement_crs)
        except CRSProcessingError as exc:
            return MeasurementResult(None, None, None, "UNAVAILABLE", exc.message, None)
    if not geometry.is_valid:
        return MeasurementResult(None, None, None, "INVALID", "Geometry is invalid and was not measured.", None)
    try:
        context = measurement_context(geometry, source_crs)
    except CRSProcessingError as exc:
        return MeasurementResult(None, None, None, "UNAVAILABLE", exc.message, None)
    if context.message and context.geometry is geometry:
        return MeasurementResult(None, None, None, "UNAVAILABLE", context.message, context.measurement_crs)
    try:
        if geometry_type in {"Polygon", "MultiPolygon"}:
            value, kind, unit = context.geometry.area, "area", f"{context.linear_unit}²" if context.linear_unit != "m" else "m²"
        else:
            value, kind, unit = context.geometry.length, "length", context.linear_unit
        if not math.isfinite(value):
            return MeasurementResult(kind, None, None, "INVALID", "Measurement produced a non-finite value.", context.measurement_crs)
        return MeasurementResult(kind, float(value), unit, "AVAILABLE", None, context.measurement_crs)
    except Exception:
        return MeasurementResult(None, None, None, "INVALID", "Geometry could not be measured safely.", context.measurement_crs)
