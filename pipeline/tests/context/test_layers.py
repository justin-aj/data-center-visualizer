"""Tests for Lowell roads, rail, polygonal water, and open-space processing."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from shapely.geometry import Point

from dcviz_pipeline.context.layers import (
    RAIL_RENDER_WIDTH_M,
    ROAD_CLASS_VISUALIZATION,
    LandmarkEvidence,
    LayerDataError,
    assemble_context_layers,
    load_open_space,
    load_railways,
    load_roads,
    load_water_polygons,
    verify_required_landmarks,
)

ORIGIN = (216_000.0, 931_000.0)


def _point(dx: float, dy: float) -> list[float]:
    return [ORIGIN[0] + dx, ORIGIN[1] + dy]


def _clockwise_box(dx: float, dy: float, size: float = 10.0) -> list[list[float]]:
    x = ORIGIN[0] + dx
    y = ORIGIN[1] + dy
    return [[x, y], [x, y + size], [x + size, y + size], [x + size, y], [x, y]]


def _counter_clockwise_box(dx: float, dy: float, size: float = 10.0) -> list[list[float]]:
    return list(reversed(_clockwise_box(dx, dy, size)))


def _line_feature(
    object_id: int,
    paths: list[list[list[float]]],
    **attributes: object,
) -> dict[str, object]:
    return {
        "attributes": {"OBJECTID": object_id, **attributes},
        "geometry": {"paths": paths},
    }


def _polygon_feature(
    object_id: int,
    rings: list[list[list[float]]],
    **attributes: object,
) -> dict[str, object]:
    return {
        "attributes": {"OBJECTID": object_id, **attributes},
        "geometry": {"rings": rings},
    }


def _write_feature_set(
    path: Path,
    geometry_type: str,
    features: list[object],
    *,
    spatial_reference: object = None,
) -> Path:
    payload = {
        "geometryType": geometry_type,
        "spatialReference": (
            {"wkid": 26986, "latestWkid": 26986} if spatial_reference is None else spatial_reference
        ),
        "features": features,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _roads(path: Path, features: list[object]) -> Path:
    return _write_feature_set(path, "esriGeometryPolyline", features)


def _railways(path: Path, features: list[object]) -> Path:
    return _write_feature_set(path, "esriGeometryPolyline", features)


def _water_lines(path: Path, features: list[object]) -> Path:
    return _write_feature_set(path, "esriGeometryPolyline", features)


def _polygons(path: Path, features: list[object]) -> Path:
    return _write_feature_set(path, "esriGeometryPolygon", features)


def _assembly_sources(tmp_path: Path) -> dict[str, Path]:
    return {
        "roads_path": _roads(
            tmp_path / "roads.json",
            [
                _line_feature(
                    1,
                    [[_point(-30, 0), _point(30, 0)], [_point(0, -30), _point(0, 30)]],
                    CLASS=4,
                    STREETNAME="Must not escape",
                )
            ],
        ),
        "railways_path": _railways(
            tmp_path / "rail.json",
            [
                _line_feature(
                    2,
                    [[_point(-30, 20), _point(30, 20)]],
                    OWNERSHIP="Must not escape",
                    FREIGHT_OP="Must not escape",
                )
            ],
        ),
        "water_polygons_path": _polygons(
            tmp_path / "water-polygons.json",
            [
                _polygon_feature(
                    3,
                    [_clockwise_box(-20, -20, 15)],
                    NAME=" River Meadow Brook ",
                    SOURCE="Must not escape",
                )
            ],
        ),
        "water_lines_path": _water_lines(
            tmp_path / "water-lines.json",
            [
                _line_feature(
                    4,
                    [[_point(-20, 5), _point(20, 5)], [_point(-20, 7), _point(20, 7)]],
                    NAME="River Meadow Brook",
                )
            ],
        ),
        "open_space_path": _polygons(
            tmp_path / "open-space.json",
            [
                _polygon_feature(
                    5,
                    [_clockwise_box(20, 20, 15)],
                    SITE_NAME="Olivera Park",
                    ALT_SITE_NAME=None,
                    FORMAL_SITE_NAME=None,
                    PRIM_PURP="R",
                    PUB_ACCESS="Y",
                    OS_TYPE=None,
                    OWNERS="Must not escape",
                )
            ],
        ),
    }


def test_assembly_returns_contract_safe_frames_and_landmark_evidence(tmp_path: Path) -> None:
    output = StringIO()

    layers = assemble_context_layers(
        **_assembly_sources(tmp_path),
        origin=ORIGIN,
        radius_m=100,
        stream=output,
    )

    assert list(layers.roads.columns) == ["class", "widthM", "geometry"]
    assert list(layers.railways.columns) == ["widthM", "geometry"]
    assert list(layers.water.columns) == ["name", "geometry"]
    assert list(layers.open_space.columns) == ["kind", "publicAccess", "geometry"]
    assert all(
        frame.crs.to_epsg() == 26986
        for frame in (
            layers.roads,
            layers.railways,
            layers.water,
            layers.open_space,
        )
    )
    assert len(layers.roads) == 2
    assert len(layers.railways) == len(layers.water) == len(layers.open_space) == 1
    assert layers.landmark_evidence.river_meadow_brook
    assert layers.landmark_evidence.olivera_park
    assert layers.landmark_evidence.olivera_source_name == "Olivera Park"
    assert layers.landmark_evidence.rail_corridor_near_origin
    assert layers.landmark_evidence.linear_water_source_features == 1
    assert "OWNER" not in " ".join(layers.open_space.columns)
    assert "name" not in layers.open_space.columns
    assert "Context roads: 2" in output.getvalue()
    assert "Linear water: 1 source features validated; 0 emitted" in output.getvalue()
    assert "Polygon-only; no buffering applied" in output.getvalue()
    assert "River Meadow Brook=yes" in output.getvalue()
    assert "Olivera Park=yes" in output.getvalue()
    assert "rail corridor near origin=yes" in output.getvalue()


@pytest.mark.parametrize(
    ("code", "label", "width"),
    [
        (1, "limited-access-highway", 24.0),
        (2, "multi-lane-highway", 18.0),
        (3, "numbered-route", 14.0),
        (4, "arterial-or-collector", 12.0),
        (5, "local-road", 8.0),
        (6, "local-road-no-inventory", 8.0),
        (7, "ramp", 10.0),
        (8, "tunnel", 8.0),
        (9, "tunnel-limited-access-highway", 24.0),
        (10, "tunnel-multi-lane-highway", 18.0),
        (11, "tunnel-numbered-route", 14.0),
    ],
)
def test_road_class_visualization_lookup(
    tmp_path: Path, code: int, label: str, width: float
) -> None:
    path = _roads(
        tmp_path / f"roads-{code}.json",
        [_line_feature(code, [[_point(-5, 0), _point(5, 0)]], CLASS=code)],
    )

    roads = load_roads(path, origin=ORIGIN, radius_m=10)

    assert ROAD_CLASS_VISUALIZATION[code] == (label, width)
    assert roads.iloc[0].to_dict()["class"] == label
    assert roads.iloc[0].to_dict()["widthM"] == width


@pytest.mark.parametrize("road_class", [None, 0, 12, 1.5, "unknown", True])
def test_roads_reject_null_and_unknown_classes(tmp_path: Path, road_class: object) -> None:
    path = _roads(
        tmp_path / "roads.json",
        [_line_feature(91, [[_point(-5, 0), _point(5, 0)]], CLASS=road_class)],
    )

    with pytest.raises(LayerDataError, match=r"roads feature 1 \(OBJECTID=91\).*CLASS"):
        load_roads(path, origin=ORIGIN, radius_m=10)


def test_each_polyline_path_is_separate_and_clipped_in_source_order(tmp_path: Path) -> None:
    path = _roads(
        tmp_path / "roads.json",
        [
            _line_feature(
                1,
                [
                    [_point(-20, 1), _point(20, 1)],
                    [_point(-20, 2), _point(20, 2)],
                ],
                CLASS=5,
            ),
            _line_feature(2, [[_point(-20, 3), _point(20, 3)]], CLASS=7),
            _line_feature(3, [[_point(20, 20), _point(30, 30)]], CLASS=4),
        ],
    )

    roads = load_roads(path, origin=ORIGIN, radius_m=10)

    assert list(roads["class"]) == ["local-road", "local-road", "ramp"]
    assert [line.coords[0][1] for line in roads.geometry] == pytest.approx(
        [ORIGIN[1] + 1, ORIGIN[1] + 2, ORIGIN[1] + 3]
    )
    assert all(Point(ORIGIN).distance(line) <= 10 for line in roads.geometry)
    assert all(line.length < 40 for line in roads.geometry)


def test_rail_uses_non_official_rendering_width_and_drops_attributes(tmp_path: Path) -> None:
    path = _railways(
        tmp_path / "rail.json",
        [
            _line_feature(
                7,
                [[_point(-5, 0), _point(5, 0)]],
                OWNERSHIP="Private operator",
                FREIGHT_OP="Private operator",
            )
        ],
    )

    railways = load_railways(path, origin=ORIGIN, radius_m=10)

    assert RAIL_RENDER_WIDTH_M == 4.0
    assert list(railways.columns) == ["widthM", "geometry"]
    assert railways["widthM"].tolist() == [4.0]


def test_polygon_parser_groups_holes_and_multiple_exteriors_in_ring_order(
    tmp_path: Path,
) -> None:
    outer_first = _clockwise_box(-40, -10, 20)
    outer_second = _clockwise_box(20, -10, 20)
    hole_for_first = _counter_clockwise_box(-35, -5, 5)
    path = _polygons(
        tmp_path / "water.json",
        [
            _polygon_feature(
                1,
                [hole_for_first, outer_first, outer_second],
                NAME="Two ponds",
            )
        ],
    )

    water = load_water_polygons(path, origin=ORIGIN, radius_m=100)

    assert len(water) == 2
    assert len(water.geometry.iloc[0].interiors) == 1
    assert len(water.geometry.iloc[1].interiors) == 0
    assert water.geometry.iloc[0].bounds[0] < water.geometry.iloc[1].bounds[0]
    assert water.geometry.is_valid.all()


@pytest.mark.parametrize(
    ("access", "expected"),
    [("Y", True), (" y ", True), ("L", False), ("unknown", False), (None, False), (7, False)],
)
def test_open_space_access_is_conservative(tmp_path: Path, access: object, expected: bool) -> None:
    path = _polygons(
        tmp_path / "open.json",
        [
            _polygon_feature(
                1,
                [_clockwise_box(-5, -5)],
                SITE_NAME="Test",
                PRIM_PURP="R",
                PUB_ACCESS=access,
                OS_TYPE=None,
            )
        ],
    )

    open_space = load_open_space(path, origin=ORIGIN, radius_m=20)

    assert bool(open_space.iloc[0]["publicAccess"]) is expected


@pytest.mark.parametrize(
    ("purpose", "open_space_type", "expected"),
    [
        ("R", None, "park"),
        ("C", "Park (Active Outdoor Recreation)", "park"),
        ("C", "Playing Field", "field"),
        ("C", "Woodland", "wooded"),
        ("C", "Conservation Area", "other"),
        (None, None, "other"),
    ],
)
def test_open_space_kind_requires_direct_source_support(
    tmp_path: Path,
    purpose: object,
    open_space_type: object,
    expected: str,
) -> None:
    path = _polygons(
        tmp_path / "open.json",
        [
            _polygon_feature(
                1,
                [_clockwise_box(-5, -5)],
                SITE_NAME="Test",
                PRIM_PURP=purpose,
                PUB_ACCESS="Y",
                OS_TYPE=open_space_type,
            )
        ],
    )

    open_space = load_open_space(path, origin=ORIGIN, radius_m=20)

    assert open_space["kind"].tolist() == [expected]


def test_blank_water_names_become_null_and_nonblank_names_are_preserved(
    tmp_path: Path,
) -> None:
    path = _polygons(
        tmp_path / "water.json",
        [
            _polygon_feature(1, [_clockwise_box(-20, 0)], NAME="  "),
            _polygon_feature(2, [_clockwise_box(20, 0)], NAME=" Named Pond "),
        ],
    )

    water = load_water_polygons(path, origin=ORIGIN, radius_m=100)

    assert water["name"].tolist() == [None, "Named Pond"]


def test_linear_water_is_validated_but_never_buffered_or_emitted(tmp_path: Path) -> None:
    sources = _assembly_sources(tmp_path)
    sources["water_polygons_path"] = _polygons(
        tmp_path / "water-polygons.json",
        [
            _polygon_feature(
                3,
                [_clockwise_box(-20, -20, 15)],
                NAME="River Meadow Brook",
            )
        ],
    )
    sources["water_lines_path"] = _water_lines(
        tmp_path / "water-lines.json",
        [
            _line_feature(9, [[_point(-90, 0), _point(90, 0)]], NAME="Another stream"),
            _line_feature(10, [[_point(-80, 5), _point(80, 5)]], NAME=None),
        ],
    )

    layers = assemble_context_layers(
        **sources,
        origin=ORIGIN,
        radius_m=100,
        stream=StringIO(),
    )

    assert len(layers.water) == 1
    assert layers.water.geom_type.tolist() == ["Polygon"]
    assert layers.landmark_evidence.linear_water_source_features == 2


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda payload: payload.update(
                {"error": {"message": "Denied", "details": ["No access"]}}
            ),
            "ArcGIS service error: Denied: No access",
        ),
        (lambda payload: payload.update({"features": {}}), "features must be a list"),
        (
            lambda payload: payload.update({"geometryType": "esriGeometryPoint"}),
            "geometryType must be esriGeometryPolyline",
        ),
        (
            lambda payload: payload.update({"spatialReference": {"wkid": 4326}}),
            "must resolve to EPSG:26986",
        ),
    ],
)
def test_arcgis_envelope_validation(
    tmp_path: Path,
    mutator: Any,
    message: str,
) -> None:
    payload: dict[str, object] = {
        "geometryType": "esriGeometryPolyline",
        "spatialReference": {"wkid": 26986},
        "features": [],
    }
    mutator(payload)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(LayerDataError, match=message):
        load_roads(path, origin=ORIGIN, radius_m=10)


@pytest.mark.parametrize(
    ("feature", "message"),
    [
        ("not an object", "feature 1: record must be an object"),
        ({"attributes": [], "geometry": {"paths": []}}, "attributes must be an object"),
        (
            {"attributes": {"OBJECTID": 8}, "geometry": None},
            r"OBJECTID=8\).*geometry must be an object",
        ),
        (_line_feature(9, [], CLASS=4), r"OBJECTID=9\).*paths must be a non-empty list"),
        (
            _line_feature(10, [[_point(0, 0)]], CLASS=4),
            r"OBJECTID=10\).*at least two points",
        ),
        (
            _line_feature(
                11,
                [[[float("nan"), ORIGIN[1]], _point(1, 1)]],
                CLASS=4,
            ),
            r"OBJECTID=11\).*finite number",
        ),
        (
            _line_feature(12, [[_point(0, 0), _point(0, 0)]], CLASS=4),
            r"OBJECTID=12\).*non-zero line",
        ),
        (
            _line_feature(13, [[_point(-1, 0), _point(1, 0)]]),
            r"OBJECTID=13\).*attributes.CLASS is required",
        ),
    ],
)
def test_malformed_polyline_records_have_feature_diagnostics(
    tmp_path: Path, feature: object, message: str
) -> None:
    path = _roads(tmp_path / "bad-road.json", [feature])

    with pytest.raises(LayerDataError, match=message):
        load_roads(path, origin=ORIGIN, radius_m=10)


@pytest.mark.parametrize(
    ("rings", "message"),
    [
        ([], "rings must be a non-empty list"),
        ([[_point(0, 0), _point(1, 0), _point(0, 0)]], "at least four points"),
        ([[_point(0, 0), _point(0, 2), _point(2, 2), _point(2, 0)]], "ring must be closed"),
        ([[_point(0, 0), _point(1, 1), _point(2, 2), _point(0, 0)]], "non-zero area"),
        ([_counter_clockwise_box(-5, -5)], "no clockwise exterior"),
        ([_clockwise_box(-5, -5), _counter_clockwise_box(20, 20, 3)], "hole is not inside"),
    ],
)
def test_malformed_polygon_records_have_ring_diagnostics(
    tmp_path: Path, rings: list[list[list[float]]], message: str
) -> None:
    path = _polygons(
        tmp_path / "bad-water.json",
        [_polygon_feature(44, rings, NAME="Bad")],
    )

    with pytest.raises(LayerDataError, match=rf"OBJECTID=44\).*{message}"):
        load_water_polygons(path, origin=ORIGIN, radius_m=100)


@pytest.mark.parametrize(
    ("origin", "radius", "message"),
    [
        ((float("nan"), ORIGIN[1]), 10, "origin easting.*finite number"),
        (ORIGIN, 0, "clip radius must be greater than zero"),
        (ORIGIN, -1, "clip radius must be greater than zero"),
    ],
)
def test_processing_parameters_are_validated(
    tmp_path: Path,
    origin: tuple[float, float],
    radius: float,
    message: str,
) -> None:
    path = _roads(tmp_path / "roads.json", [])

    with pytest.raises(LayerDataError, match=message):
        load_roads(path, origin=origin, radius_m=radius)


def test_missing_file_error_identifies_source_and_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"

    with pytest.raises(LayerDataError, match=r"roads: could not read ArcGIS JSON.*missing.json"):
        load_roads(missing, origin=ORIGIN)


def test_required_landmark_verification_lists_missing_evidence() -> None:
    evidence = LandmarkEvidence(
        river_meadow_brook=False,
        olivera_park=False,
        rail_corridor_near_origin=False,
        olivera_source_name=None,
        rail_nearest_origin_m=500.0,
        linear_water_source_features=0,
    )

    with pytest.raises(LayerDataError) as error:
        verify_required_landmarks(evidence)

    assert "River Meadow Brook" in str(error.value)
    assert "Olivera Park" in str(error.value)
    assert "rail corridor within 100 m" in str(error.value)


def test_assembly_can_return_failed_landmark_evidence_for_non_real_fixture(
    tmp_path: Path,
) -> None:
    sources = _assembly_sources(tmp_path)
    sources["water_polygons_path"] = _polygons(
        tmp_path / "water-polygons.json",
        [_polygon_feature(3, [_clockwise_box(-20, -20, 15)], NAME="Other water")],
    )
    sources["open_space_path"] = _polygons(
        tmp_path / "open-space.json",
        [
            _polygon_feature(
                5,
                [_clockwise_box(20, 20, 15)],
                SITE_NAME="Other park",
                PRIM_PURP="R",
                PUB_ACCESS="Y",
                OS_TYPE=None,
            )
        ],
    )

    layers = assemble_context_layers(
        **sources,
        origin=ORIGIN,
        radius_m=100,
        require_landmarks=False,
        stream=StringIO(),
    )

    assert not layers.landmark_evidence.river_meadow_brook
    assert not layers.landmark_evidence.olivera_park
