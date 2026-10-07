from dataclasses import dataclass

import geopandas as gpd
from pyproj import CRS
from shapely.geometry.base import BaseGeometry

from app.utils.exceptions import CRSProcessingError


@dataclass(frozen=True)
class MeasurementContext:
    source_crs: str | None
    measurement_crs: str | None
    geometry: BaseGeometry | None
    message: str | None = None
    linear_unit: str = "m"


def _utm_crs(longitude: float, latitude: float) -> CRS:
    zone = min(60, max(1, int((longitude + 180) // 6) + 1))
    return CRS.from_dict({"proj": "utm", "zone": zone, "south": latitude < 0})


def measurement_context(geometry: BaseGeometry | None, source_crs: object) -> MeasurementContext:
    if geometry is None or geometry.is_empty:
        return MeasurementContext(_crs_name(source_crs), None, geometry, "Measurement unavailable because geometry is empty.")
    if source_crs is None:
        return MeasurementContext(None, None, geometry, "Measurement unavailable because the source CRS is undefined.")
    try:
        crs = CRS.from_user_input(source_crs)
        source_name = crs.to_string()
        if crs.is_geographic:
            point = geometry.representative_point()
            target = _utm_crs(point.x, point.y)
            transformed = gpd.GeoSeries([geometry], crs=crs).to_crs(target).iloc[0]
            return MeasurementContext(source_name, _crs_label(target), transformed)
        unit = crs.axis_info[0].unit_name if crs.axis_info else None
        if unit and unit.lower() not in {"metre", "meter", "metres", "meters"}:
            return MeasurementContext(source_name, source_name, geometry, f"Projected CRS uses {unit}; measurements retain those native units.", unit or "native units")
        return MeasurementContext(source_name, source_name, geometry)
    except Exception as exc:
        raise CRSProcessingError("Measurement unavailable because the source CRS is invalid.") from exc


def _crs_name(value: object) -> str | None:
    if value is None:
        return None
    try:
        return CRS.from_user_input(value).to_string()
    except Exception:
        return str(value)


def _crs_label(crs: CRS) -> str:
    epsg = crs.to_epsg()
    return f"EPSG:{epsg}" if epsg else crs.to_string()
