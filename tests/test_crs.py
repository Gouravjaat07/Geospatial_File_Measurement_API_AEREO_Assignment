from shapely.geometry import Point

from app.services.crs_service import measurement_context


def test_geographic_crs_selects_local_utm() -> None:
    context = measurement_context(Point(77, 12), "EPSG:4326")
    assert context.measurement_crs and "32643" in context.measurement_crs


def test_southern_hemisphere_uses_southern_utm() -> None:
    context = measurement_context(Point(151, -33), "EPSG:4326")
    assert context.measurement_crs and "32756" in context.measurement_crs


def test_projected_crs_is_preserved() -> None:
    context = measurement_context(Point(0, 0), "EPSG:3857")
    assert context.measurement_crs == "EPSG:3857"


def test_missing_crs_does_not_measure() -> None:
    context = measurement_context(Point(0, 0), None)
    assert context.measurement_crs is None
    assert context.message


def test_utm_zone_edges_are_clamped_and_deterministic() -> None:
    assert measurement_context(Point(-179.9, 10), "EPSG:4326").measurement_crs == "EPSG:32601"
    assert measurement_context(Point(179.9, 10), "EPSG:4326").measurement_crs == "EPSG:32660"
    assert measurement_context(Point(3, 10), "EPSG:4326").measurement_crs == "EPSG:32631"
