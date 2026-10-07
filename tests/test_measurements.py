import pytest
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon

from app.services.measurement_service import measure_geometry


def test_geographic_polygon_is_measured_in_meters() -> None:
    result = measure_geometry(Polygon([(77, 12), (77.001, 12), (77.001, 12.001), (77, 12.001)]), "EPSG:4326")
    assert result.status == "AVAILABLE"
    assert result.measurement_type == "area"
    assert result.value and result.value > 0
    assert result.unit == "m²"


def test_lines_and_multilines_are_measured() -> None:
    result = measure_geometry(LineString([(0, 0), (100, 0)]), "EPSG:3857")
    multi = measure_geometry(MultiLineString([[(0, 0), (3, 4)], [(0, 0), (0, 2)]]), "EPSG:3857")
    assert result.value == pytest.approx(100)
    assert multi.value == pytest.approx(7)


def test_multipolygon_and_points() -> None:
    polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    second_polygon = Polygon([(2, 0), (3, 0), (3, 1), (2, 1)])
    result = measure_geometry(MultiPolygon([polygon, second_polygon]), "EPSG:3857")
    point = measure_geometry(Point(0, 0), "EPSG:4326")
    assert result.value == pytest.approx(2)
    assert point.status == "NOT_APPLICABLE"
    assert measure_geometry(MultiPoint([(0, 0)]), "EPSG:4326").status == "NOT_APPLICABLE"


def test_missing_and_invalid_geometry_are_safe() -> None:
    assert measure_geometry(None, "EPSG:4326").status == "UNAVAILABLE"
    assert measure_geometry(Polygon(), "EPSG:4326").status == "UNAVAILABLE"
    assert measure_geometry(Polygon([(0, 0), (1, 0), (0, 1), (1, 1), (0, 0)]), "EPSG:4326").status in {"AVAILABLE", "INVALID"}


def test_zero_length_and_unsupported_geometry_are_explicit() -> None:
    zero_length = measure_geometry(LineString([(0, 0), (0, 0)]), "EPSG:3857")
    unsupported = measure_geometry(GeometryCollection([Point(0, 0)]), "EPSG:3857")
    assert zero_length.status == "AVAILABLE"
    assert zero_length.value == pytest.approx(0)
    assert unsupported.status == "UNSUPPORTED"


def test_invalid_polygon_is_not_measured() -> None:
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    result = measure_geometry(bowtie, "EPSG:3857")
    assert result.status == "INVALID"
    assert result.value is None
