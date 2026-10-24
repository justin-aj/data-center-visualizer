"""Tests for privacy-safe context-building height assignment."""

from __future__ import annotations

import json
import math
from io import StringIO
from pathlib import Path

import geopandas as gpd
import pytest
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, box

from dcviz_pipeline.context.heights import (
    AREA_200_TO_1000_SOURCE,
    AREA_AT_LEAST_1000_SOURCE,
    AREA_UNDER_200_SOURCE,
    OSM_EXPLICIT_SOURCE,
    OSM_LEVELS_SOURCE,
    OVERTURE_MICROSOFT_ML_SOURCE,
    OVERTURE_USGS_LIDAR_SOURCE,
    HeightCandidate,
    HeightDataError,
    area_default_height_m,
    assign_building_heights,
    enrich_building_heights,
    height_coverage,
    load_osm_height_candidates,
    overture_height_candidate,
    parse_height_m,
    parse_levels,
)

CRS = "EPSG:26986"
ORIGIN = (216_000.0, 931_000.0)


def _buildings(rows: list[tuple[str, Polygon]], **extra: object) -> gpd.GeoDataFrame:
    records = [
        {
            "id": identifier,
            "geometry": geometry,
            "OWNER": extra.get("OWNER", "Private Person"),
            "ADDRESS": extra.get("ADDRESS", "Not for output"),
        }
        for identifier, geometry in rows
    ]
    return gpd.GeoDataFrame(records, geometry="geometry", crs=CRS)


def _candidate(
    record_id: str,
    geometry: Polygon,
    *,
    height: float | None = None,
    levels: float | None = None,
    source_kind: str = "osm",
) -> HeightCandidate:
    return HeightCandidate(
        record_id=record_id,
        geometry=geometry,
        source_kind=source_kind,  # type: ignore[arg-type]
        explicit_height_m=height,
        levels=levels,
    )


def _osm_way(
    record_id: int,
    geometry: Polygon,
    tags: dict[str, str],
) -> dict[str, object]:
    inverse = Transformer.from_crs(26986, 4326, always_xy=True)
    positions = []
    for x, y in geometry.exterior.coords:
        lon, lat = inverse.transform(x, y)
        positions.append({"lat": lat, "lon": lon})
    return {"type": "way", "id": record_id, "geometry": positions, "tags": tags}


def _write_overpass(path: Path, elements: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"version": 0.6, "elements": elements}), encoding="utf-8")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12", 12.0),
        ("12 m", 12.0),
        ("12m", 12.0),
        ("40 ft", 12.192),
        ("40'", 12.192),
        (" 2.5 M ", 2.5),
    ],
)
def test_parse_height_accepts_supported_metres_and_feet(value: str, expected: float) -> None:
    assert parse_height_m(value) == pytest.approx(expected)


@pytest.mark.parametrize(
    "value",
    [None, 12, "", "0", "-3", "+3", "nan", "inf", "12-14", "12;14", "12 feet", "3m;4m"],
)
def test_parse_height_rejects_malformed_ranges_lists_and_non_positive_values(
    value: object,
) -> None:
    assert parse_height_m(value) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1", 1.0), ("2", 2.0), ("2.5", 2.5), (" 4 ", 4.0)],
)
def test_parse_levels_accepts_positive_decimal_values(value: str, expected: float) -> None:
    assert parse_levels(value) == expected


@pytest.mark.parametrize(
    "value",
    [None, 2, "", "0", "-1", "nan", "2-3", "2;3", "two", "2 levels"],
)
def test_parse_levels_rejects_non_decimal_or_non_positive_values(value: object) -> None:
    assert parse_levels(value) is None


@pytest.mark.parametrize(
    ("area", "height", "source"),
    [
        (199.999, 7.0, AREA_UNDER_200_SOURCE),
        (200.0, 9.0, AREA_200_TO_1000_SOURCE),
        (999.999, 9.0, AREA_200_TO_1000_SOURCE),
        (1_000.0, 12.0, AREA_AT_LEAST_1000_SOURCE),
    ],
)
def test_area_default_boundaries(area: float, height: float, source: str) -> None:
    assert area_default_height_m(area) == (height, source)


def test_loader_converts_lon_lat_filters_circle_and_discards_unrelated_tags(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "overpass.json"
    inside = box(ORIGIN[0] - 5, ORIGIN[1] - 5, ORIGIN[0] + 5, ORIGIN[1] + 5)
    crossing = box(ORIGIN[0] + 995, ORIGIN[1] - 10, ORIGIN[0] + 1_005, ORIGIN[1] + 10)
    outside = box(ORIGIN[0] + 1_100, ORIGIN[1], ORIGIN[0] + 1_110, ORIGIN[1] + 10)
    _write_overpass(
        cache,
        [
            _osm_way(
                1,
                inside,
                {
                    "height": "40 ft",
                    "building:levels": "4",
                    "name": "Must not escape",
                    "addr:housenumber": "123",
                    "website": "https://example.invalid",
                    "user": "Must not escape",
                },
            ),
            _osm_way(2, crossing, {"height": "bad", "building:levels": "2.5"}),
            _osm_way(3, outside, {"height": "10"}),
        ],
    )
    output = StringIO()

    candidates = load_osm_height_candidates(
        cache,
        origin=ORIGIN,
        radius_m=1_000,
        stream=output,
    )

    assert [candidate.record_id for candidate in candidates] == ["1", "2"]
    assert candidates[0].explicit_height_m == pytest.approx(12.192)
    assert candidates[0].levels == 4.0
    assert candidates[0].geometry.centroid.x == pytest.approx(ORIGIN[0], abs=0.01)
    assert candidates[1].explicit_height_m is None
    assert candidates[1].levels == 2.5
    assert not hasattr(candidates[0], "tags")
    assert "Must not escape" not in repr(candidates)
    assert output.getvalue() == (
        "OSM height cache: 3 ways in bounding box; 2 intersect the clip circle; "
        "2 valid observations\n"
    )


def test_loader_rejects_relations_explicitly(tmp_path: Path) -> None:
    cache = tmp_path / "relations.json"
    _write_overpass(cache, [{"type": "relation", "id": 9, "members": [], "tags": {}}])

    with pytest.raises(HeightDataError, match="OSM relation 9 is not supported"):
        load_osm_height_candidates(cache, origin=ORIGIN, stream=StringIO())


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "elements array"),
        ({"elements": ["bad"]}, "each OSM element"),
        (
            {
                "elements": [
                    {"type": "way", "id": 1, "geometry": [], "tags": {"height": "10"}}
                ]
            },
            "at least four geometry positions",
        ),
        (
            {
                "elements": [
                    {
                        "type": "node",
                        "id": 1,
                        "geometry": [],
                        "tags": {"height": "10"},
                    }
                ]
            },
            "unsupported OSM element type",
        ),
    ],
)
def test_loader_rejects_malformed_overpass_structures(
    tmp_path: Path,
    payload: object,
    message: str,
) -> None:
    cache = tmp_path / "malformed.json"
    cache.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(HeightDataError, match=message):
        load_osm_height_candidates(cache, origin=ORIGIN, stream=StringIO())


def test_loader_rejects_open_way_geometry(tmp_path: Path) -> None:
    cache = tmp_path / "open.json"
    way = _osm_way(1, box(*ORIGIN, ORIGIN[0] + 10, ORIGIN[1] + 10), {"height": "10"})
    way["geometry"] = way["geometry"][:-1]  # type: ignore[index]
    _write_overpass(cache, [way])

    with pytest.raises(HeightDataError, match="geometry must be closed"):
        load_osm_height_candidates(cache, origin=ORIGIN, stream=StringIO())


def test_priority_combination_statuses_conflicts_and_defaults() -> None:
    geometries = {
        "explicit": box(0, 0, 10, 10),
        "derived": box(20, 0, 30, 10),
        "conflict-falls-to-levels": box(40, 0, 50, 10),
        "level-conflict-default": box(60, 0, 70, 10),
        "medium-default": box(80, 0, 100, 20),
        "large-default": box(120, 0, 160, 30),
    }
    buildings = _buildings(list(geometries.items()))
    osm = [
        _candidate("osm-explicit", geometries["explicit"], height=12.0, levels=9),
        _candidate("osm-agree", geometries["explicit"], height=12.4),
        _candidate("osm-conflict", geometries["conflict-falls-to-levels"], height=12, levels=2),
        _candidate("osm-level-a", geometries["level-conflict-default"], levels=2),
        _candidate("osm-level-b", geometries["level-conflict-default"], levels=3),
    ]
    overture = [
        overture_height_candidate(
            "ml-agree",
            geometries["explicit"],
            12.2,
            source_dataset="microsoft-ml",
        ),
        overture_height_candidate(
            "lidar",
            geometries["derived"],
            18,
            source_dataset="usgs-lidar",
        ),
        overture_height_candidate(
            "overture-conflict",
            geometries["conflict-falls-to-levels"],
            13,
            source_dataset="microsoft-ml",
        ),
    ]
    output = StringIO()

    result = assign_building_heights(
        buildings,
        osm_candidates=osm,
        overture_candidates=overture,
        stream=output,
    ).set_index("id")

    assert result.at["explicit", "heightM"] == pytest.approx((12 + 12.4 + 12.2) / 3)
    assert result.at["explicit", "heightStatus"] == "estimated"
    assert result.at["explicit", "heightSource"].startswith("Agreeing explicit heights:")
    assert OSM_EXPLICIT_SOURCE in result.at["explicit", "heightSource"]
    assert OVERTURE_MICROSOFT_ML_SOURCE in result.at["explicit", "heightSource"]
    assert result.loc["derived", ["heightM", "heightStatus", "heightSource"]].tolist() == [
        18.0,
        "derived",
        OVERTURE_USGS_LIDAR_SOURCE,
    ]
    assert result.loc[
        "conflict-falls-to-levels", ["heightM", "heightStatus", "heightSource"]
    ].tolist() == [6.0, "estimated", OSM_LEVELS_SOURCE]
    assert result.loc[
        "level-conflict-default", ["heightM", "heightStatus", "heightSource"]
    ].tolist() == [7.0, "estimated", AREA_UNDER_200_SOURCE]
    assert result.at["medium-default", "heightM"] == 9.0
    assert result.at["large-default", "heightM"] == 12.0
    assert "Conflicting explicit heights for building conflict-falls-to-levels" in output.getvalue()
    assert "Conflicting level heights for building level-conflict-default" in output.getvalue()


def test_many_to_one_agreeing_levels_are_accepted() -> None:
    geometry = box(0, 0, 20, 20)
    candidates = [
        _candidate("part-a", box(0, 0, 10, 20), levels=2),
        _candidate("part-b", box(10, 0, 20, 20), levels=2),
    ]

    result = assign_building_heights(
        _buildings([("one", geometry)]),
        osm_candidates=candidates,
        stream=StringIO(),
    )

    assert result.loc[0, "heightM"] == 6.0
    assert result.loc[0, "heightSource"] == OSM_LEVELS_SOURCE


def test_overlap_and_centroid_thresholds_must_both_pass() -> None:
    small = box(0, 0, 10, 10)
    large = box(100, 0, 200, 100)
    candidates = [
        _candidate("low-overlap", box(2.6, 0, 12.6, 10), levels=2),
        _candidate("far-centroid", box(100, 0, 110, 10), levels=2),
    ]

    result = assign_building_heights(
        _buildings([("small", small), ("large", large)]),
        osm_candidates=candidates,
        stream=StringIO(),
    ).set_index("id")

    assert result.at["small", "heightSource"] == AREA_UNDER_200_SOURCE
    assert result.at["large", "heightSource"] == AREA_AT_LEAST_1000_SOURCE


def test_equal_best_geometry_match_is_ambiguous_and_falls_back() -> None:
    identical = box(0, 0, 10, 10)
    output = StringIO()

    result = assign_building_heights(
        _buildings([("a", identical), ("b", identical)]),
        osm_candidates=[_candidate("ambiguous", identical, height=20)],
        stream=output,
    )

    assert set(result["heightSource"]) == {AREA_UNDER_200_SOURCE}
    assert "Ambiguous geometry match for osm record ambiguous" in output.getvalue()
    assert "1 ambiguous" in output.getvalue()


def test_output_is_exact_deterministic_privacy_safe_and_complete() -> None:
    source = _buildings(
        [
            ("z", box(0, 0, 10, 10)),
            ("a", box(20, 0, 40, 20)),
            ("large", box(50, 0, 90, 30)),
        ]
    )
    candidate = _candidate("safe-id", source.geometry.iloc[0], levels=2.5)

    first = assign_building_heights(
        source,
        osm_candidates=[candidate],
        stream=StringIO(),
    )
    second = assign_building_heights(
        source,
        osm_candidates=[candidate],
        stream=StringIO(),
    )

    assert list(first.columns) == ["id", "heightM", "heightStatus", "heightSource", "geometry"]
    assert list(first["id"]) == ["z", "a", "large"]
    assert first.crs.to_epsg() == 26986
    assert first.equals(second)
    assert first.geometry.equals(source.geometry)
    assert "OWNER" not in first.columns
    assert "ADDRESS" not in first.columns
    assert (first["heightM"] > 0).all()
    assert first["heightM"].map(math.isfinite).all()
    assert set(first["heightStatus"]) <= {"derived", "estimated"}
    assert first["heightSource"].str.strip().ne("").all()

    coverage = height_coverage(first)
    assert coverage.total_buildings == 3
    assert sum(coverage.counts_by_source.values()) == coverage.total_buildings
    assert coverage.counts_by_source == {
        AREA_200_TO_1000_SOURCE: 1,
        AREA_AT_LEAST_1000_SOURCE: 1,
        OSM_LEVELS_SOURCE: 1,
    }


def test_enrich_public_api_loads_cache_and_returns_task_34_shape(tmp_path: Path) -> None:
    geometry = box(ORIGIN[0] - 5, ORIGIN[1] - 5, ORIGIN[0] + 5, ORIGIN[1] + 5)
    cache = tmp_path / "osm.json"
    _write_overpass(cache, [_osm_way(7, geometry, {"building:levels": "2.5"})])

    result = enrich_building_heights(
        _buildings([("building", geometry)]),
        cache,
        origin=ORIGIN,
        radius_m=100,
        stream=StringIO(),
    )

    assert list(result.columns) == ["id", "heightM", "heightStatus", "heightSource", "geometry"]
    assert result.loc[0, ["heightM", "heightStatus", "heightSource"]].tolist() == [
        7.5,
        "estimated",
        OSM_LEVELS_SOURCE,
    ]


@pytest.mark.parametrize(
    ("buildings", "message"),
    [
        (
            gpd.GeoDataFrame(
                {"geometry": [box(0, 0, 10, 10)]}, geometry="geometry", crs=CRS
            ),
            "missing required fields",
        ),
        (_buildings([("a", box(0, 0, 10, 10))]).set_crs(None, allow_override=True), "CRS"),
        (
            _buildings([("a", box(0, 0, 10, 10))]).to_crs(4326),
            "must use EPSG:26986",
        ),
        (_buildings([(" ", box(0, 0, 10, 10))]), "must not be blank"),
        (
            _buildings([("same", box(0, 0, 10, 10)), ("same", box(20, 0, 30, 10))]),
            "must be unique",
        ),
        (
            gpd.GeoDataFrame(
                {"id": ["line"], "geometry": [LineString([(0, 0), (1, 1)])]},
                geometry="geometry",
                crs=CRS,
            ),
            "valid Polygons",
        ),
    ],
)
def test_assignment_rejects_invalid_task_31_inputs(
    buildings: gpd.GeoDataFrame,
    message: str,
) -> None:
    with pytest.raises(HeightDataError, match=message):
        assign_building_heights(buildings, stream=StringIO())


def test_empty_building_frame_has_complete_empty_output_and_coverage() -> None:
    empty = gpd.GeoDataFrame(
        {"id": [], "geometry": []},
        geometry="geometry",
        crs=CRS,
    )

    result = assign_building_heights(empty, stream=StringIO())
    coverage = height_coverage(result)

    assert result.empty
    assert list(result.columns) == ["id", "heightM", "heightStatus", "heightSource", "geometry"]
    assert coverage.total_buildings == 0
    assert coverage.counts_by_source == {}
    assert coverage.percentage("missing") == 0


def test_overlap_and_centroid_threshold_boundaries_are_inclusive() -> None:
    overlap_boundary = box(0, 0, 10, 10)
    distance_boundary = box(100, 0, 200, 10)
    candidates = [
        _candidate("exact-overlap", box(2.5, 0, 12.5, 10), levels=2),
        _candidate("exact-distance", box(110, 0, 210, 10), levels=3),
    ]

    result = assign_building_heights(
        _buildings(
            [
                ("overlap-boundary", overlap_boundary),
                ("distance-boundary", distance_boundary),
            ]
        ),
        osm_candidates=candidates,
        stream=StringIO(),
    ).set_index("id")

    assert result.at["overlap-boundary", "heightM"] == 6.0
    assert result.at["distance-boundary", "heightM"] == 9.0
    assert set(result["heightSource"]) == {OSM_LEVELS_SOURCE}
