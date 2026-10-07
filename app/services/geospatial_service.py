import json
import math
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import mapping

from app.services.measurement_service import MeasurementResult, measure_geometry
from app.utils.exceptions import InvalidGeospatialFileError


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if value is pd.NaT or (not isinstance(value, (list, tuple, dict)) and pd.isna(value)):
        return None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _json_value(value.item())
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _properties(row: Any, columns: list[str]) -> dict[str, Any]:
    return {column: _json_value(row[column]) for column in columns}


def read_geospatial_file(path: Path, file_type: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        if file_type == ".zip":
            with tempfile.TemporaryDirectory(prefix="geospatial-extract-") as directory:
                with zipfile.ZipFile(path) as archive:
                    for member in archive.infolist():
                        target = Path(directory, *Path(member.filename.replace("\\", "/")).parts)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if not member.is_dir():
                            with archive.open(member) as source, target.open("wb") as destination:
                                destination.write(source.read())
                shp = next(Path(directory).rglob("*.shp"))
                frame = gpd.read_file(shp)
        else:
            frame = gpd.read_file(path, driver="KML")
    except StopIteration as exc:
        raise InvalidGeospatialFileError("Uploaded archive does not contain a readable Shapefile.") from exc
    except Exception as exc:
        raise InvalidGeospatialFileError("Uploaded geospatial file could not be parsed.") from exc
    columns = [column for column in frame.columns if column != frame.geometry.name]
    source_crs = frame.crs.to_string() if frame.crs else None
    features = []
    for index, row in frame.iterrows():
        geometry = row.geometry
        geometry_json = None if geometry is None or geometry.is_empty else _json_value(mapping(geometry))
        measurement: MeasurementResult = measure_geometry(geometry, frame.crs)
        features.append(
            {
                "feature_index": int(index) if isinstance(index, (int, np.integer)) else len(features),
                "geometry_type": geometry.geom_type if geometry is not None else None,
                "geometry": geometry_json,
                "properties": _properties(row, columns),
                "measurement": measurement,
            }
        )
    return features, source_crs
