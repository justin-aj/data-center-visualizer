"""Tests for Lowell MassGIS building-footprint processing."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import geopandas as gpd
import pytest
from pyproj import Transformer
from shapely.geometry import LineString, MultiPolygon, Polygon, box

from dcviz_pipeline.context.buildings import (
    CIRCLE_QUAD_SEGS,
    BuildingDataError,
    approved_initial_origin,
    load_massgis_buildings,
    process_buildings,
)

CRS = "EPSG:26986"
ORIGIN = (216_000.0, 931_000.0)


def _row(
    identifier: object,
    geometry: object,
    *,
    town_id: object = 160,
    town_id2: object = 0,
    town_id3: object = 0,
    owner: str = "Private Person",
) -> dict[str, object]:
    return {
        "STRUCT_ID": identifier,
        "TOWN_ID": town_id,
        "TOWN_ID2": town_id2,
        "TOWN_ID3": town_id3,
        "OWNER": owner,
        "ADDRESS": "Not for output",
        "geometry": geometry,
    }


def _frame(rows: list[dict[str, object]], *, crs: str | None = CRS) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)


def _square(dx: float, dy: float, size: float = 10.0) -> Polygon:
    x, y = ORIGIN
    return box(x + dx, y + dy, x + dx + size, y + dy + size)


def _write_zip_archive(path: Path, buildings: gpd.GeoDataFrame) -> None:
    shapefile_dir = path.parent / "shape"
    shapefile_dir.mkdir()
    shapefile = shapefile_dir / "structures_poly.shp"
    buildings.to_file(shapefile, driver="ESRI Shapefile", index=False)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for component in sorted(shapefile_dir.iterdir()):
            archive.write(component, arcname=component.name)


def test_approved_initial_origin_uses_lon_lat_order_and_epsg_26986() -> None:
    expected = Transformer.from_crs(4326, 26986, always_xy=True).transform(
        -71.3042290,
        42.6305082,
    )

    assert approved_initial_origin() == pytest.approx(expected)


def test_process_clips_filters_towns_and_keeps_only_privacy_safe_columns() -> None:
    source = _frame(
        [
            _row("primary", _square(-4, -4, size=3.0)),
            _row("town-two", _square(1, -4, size=3.0), town_id=161, town_id2=160),
            _row("town-three", _square(-4, 1, size=3.0), town_id=161, town_id3="160"),
            _row("other-town", _square(1, 1, size=3.0), town_id=161),
            _row("outside-radius", _square(1_500, 0)),
            _row("under-eight", _square(5, 1, size=2.0)),
            _row("post-clip-sliver", _square(9.5, -2, size=4.0)),
            _row("clipped", _square(7, -3, size=6.0)),
        ]
    )
    output = StringIO()

    result = process_buildings(
        source,
        origin=ORIGIN,
        radius_m=10,
        simplify_tolerance_m=0,
        stream=output,
    )

    assert list(result.columns) == ["id", "geometry"]
    assert list(result["id"]) == ["clipped", "primary", "town-three", "town-two"]
    assert result.crs.to_epsg() == 26986
    assert (result.geometry.area >= 8).all()
    assert result.total_bounds[2] <= ORIGIN[0] + 10
    assert "OWNER" not in result.columns
    assert "ADDRESS" not in result.columns
    assert output.getvalue().startswith("MassGIS Lowell building footprints: 4\n")
    assert "Bounds (EPSG:26986 metres):" in output.getvalue()


def test_simplifies_after_clipping_and_preserves_valid_polygon_topology() -> None:
    x, y = ORIGIN
    detailed = Polygon(
        [
            (x - 5, y - 5),
            (x, y - 5.1),
            (x + 5, y - 5),
            (x + 5, y + 5),
            (x - 5, y + 5),
            (x - 5, y - 5),
        ]
    )

    result = process_buildings(
        _frame([_row("detailed", detailed)]),
        origin=ORIGIN,
        radius_m=20,
        simplify_tolerance_m=0.3,
        stream=StringIO(),
    )

    assert len(detailed.exterior.coords) == 6
    assert len(result.geometry.iloc[0].exterior.coords) == 5
    assert result.geometry.iloc[0].is_valid


def test_high_resolution_circle_is_deterministic() -> None:
    enclosing_square = _square(-20, -20, size=40)

    result = process_buildings(
        _frame([_row("circle", enclosing_square)]),
        origin=ORIGIN,
        radius_m=10,
        simplify_tolerance_m=0,
        min_area_m2=0,
        stream=StringIO(),
    )

    assert CIRCLE_QUAD_SEGS == 128
    assert len(result.geometry.iloc[0].exterior.coords) == 4 * CIRCLE_QUAD_SEGS + 1
    assert result.total_bounds == pytest.approx(
        [ORIGIN[0] - 10, ORIGIN[1] - 10, ORIGIN[0] + 10, ORIGIN[1] + 10]
    )


def test_multipolygons_get_stable_unique_suffixes_and_polygon_rows() -> None:
    multipart = MultiPolygon([_square(30, 0), _square(-30, 0)])

    result = process_buildings(
        _frame([_row("multi", multipart)]),
        origin=ORIGIN,
        radius_m=100,
        stream=StringIO(),
    )

    assert list(result["id"]) == ["multi::part-001", "multi::part-002"]
    assert list(result.geom_type) == ["Polygon", "Polygon"]
    assert result.geometry.iloc[0].bounds[0] < result.geometry.iloc[1].bounds[0]


def test_loader_reads_a_temporary_archive_without_repository_raw_data(tmp_path: Path) -> None:
    archive = tmp_path / "synthetic-buildings.zip"
    source = _frame([_row("from-archive", _square(-5, -5))])
    _write_zip_archive(archive, source)

    result = load_massgis_buildings(archive, origin=ORIGIN, stream=StringIO())

    assert list(result["id"]) == ["from-archive"]
    assert list(result.columns) == ["id", "geometry"]
    assert result.crs.to_epsg() == 26986


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            _frame([_row("missing-field", _square(0, 0))]).drop(columns="TOWN_ID3"),
            "missing required fields: TOWN_ID3",
        ),
        (_frame([_row("missing-crs", _square(0, 0))], crs=None), "CRS is missing"),
        (
            _frame([_row("wrong-crs", box(-71.31, 42.62, -71.30, 42.63))], crs="EPSG:4326"),
            "must use EPSG:26986",
        ),
        (_frame([_row(None, _square(0, 0))]), "must not be null"),
        (_frame([_row("   ", _square(0, 0))]), "must not be blank"),
        (_frame([_row(123, _square(0, 0))]), "must be strings"),
        (
            _frame([_row("duplicate", _square(0, 0)), _row("duplicate", _square(20, 0))]),
            "must be unique",
        ),
        (_frame([_row("null-geometry", None)]), "geometries must not be null"),
        (_frame([_row("empty-geometry", Polygon())]), "geometries must not be empty"),
        (
            _frame(
                [
                    _row(
                        "invalid-geometry",
                        Polygon(
                            [
                                (ORIGIN[0], ORIGIN[1]),
                                (ORIGIN[0] + 10, ORIGIN[1] + 10),
                                (ORIGIN[0] + 10, ORIGIN[1]),
                                (ORIGIN[0], ORIGIN[1] + 10),
                                (ORIGIN[0], ORIGIN[1]),
                            ]
                        ),
                    )
                ]
            ),
            "geometries must be valid",
        ),
        (
            _frame([_row("line", LineString([ORIGIN, (ORIGIN[0] + 10, ORIGIN[1])]))]),
            "must be Polygon or MultiPolygon",
        ),
    ],
)
def test_validation_rejects_malformed_source(
    source: gpd.GeoDataFrame,
    message: str,
) -> None:
    with pytest.raises(BuildingDataError, match=message):
        process_buildings(source, origin=ORIGIN, stream=StringIO())


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"origin": (float("nan"), 0)}, "origin easting must be finite"),
        ({"radius_m": 0}, "clip radius must be greater than zero"),
        ({"simplify_tolerance_m": -0.1}, "simplification tolerance must not be negative"),
        ({"min_area_m2": -1}, "minimum footprint area must not be negative"),
    ],
)
def test_validation_rejects_invalid_processing_parameters(
    kwargs: dict[str, object],
    message: str,
) -> None:
    options: dict[str, object] = {
        "origin": ORIGIN,
        "stream": StringIO(),
    }
    options.update(kwargs)
    with pytest.raises(BuildingDataError, match=message):
        process_buildings(
            _frame([_row("valid", _square(0, 0))]),
            **options,
        )


def test_empty_result_reports_count_and_empty_bounds() -> None:
    output = StringIO()

    result = process_buildings(
        _frame([_row("outside", _square(2_000, 0))]),
        origin=ORIGIN,
        stream=output,
    )

    assert result.empty
    assert list(result.columns) == ["id", "geometry"]
    assert result.crs.to_epsg() == 26986
    assert output.getvalue() == (
        "MassGIS Lowell building footprints: 0\n"
        "Bounds (EPSG:26986 metres): empty\n"
    )


def test_loader_wraps_archive_read_errors(tmp_path: Path) -> None:
    missing = tmp_path / "missing.zip"

    with pytest.raises(BuildingDataError, match="could not read MassGIS building archive"):
        load_massgis_buildings(missing, stream=StringIO())
