"""Load and prepare privacy-safe MassGIS building footprints for Lowell."""

from __future__ import annotations

import math
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

MASSACHUSETTS_MAINLAND_EPSG = 26986
LOWELL_TOWN_ID = 160
INITIAL_ANCHOR_LON = -71.3042290
INITIAL_ANCHOR_LAT = 42.6305082
CONTEXT_RADIUS_M = 1_200.0
SIMPLIFY_TOLERANCE_M = 0.3
MIN_FOOTPRINT_AREA_M2 = 8.0
CIRCLE_QUAD_SEGS = 128

_REQUIRED_FIELDS = {"STRUCT_ID", "TOWN_ID", "TOWN_ID2", "TOWN_ID3"}


class BuildingDataError(ValueError):
    """MassGIS building input does not satisfy the task's data contract."""


def approved_initial_origin() -> tuple[float, float]:
    """Return the approved initial anchor in EPSG:26986 metres."""
    transformer = Transformer.from_crs(
        4326,
        MASSACHUSETTS_MAINLAND_EPSG,
        always_xy=True,
    )
    easting, northing = transformer.transform(INITIAL_ANCHOR_LON, INITIAL_ANCHOR_LAT)
    return float(easting), float(northing)


def _finite_number(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise BuildingDataError(f"{name} must be finite")
    return number


def _validate_parameters(
    origin: tuple[float, float],
    radius_m: float,
    simplify_tolerance_m: float,
    min_area_m2: float,
) -> tuple[float, float, float, float, float]:
    try:
        origin_easting, origin_northing = origin
    except (TypeError, ValueError) as error:
        raise BuildingDataError("origin must contain easting and northing") from error

    easting = _finite_number(origin_easting, "origin easting")
    northing = _finite_number(origin_northing, "origin northing")
    radius = _finite_number(radius_m, "clip radius")
    tolerance = _finite_number(simplify_tolerance_m, "simplification tolerance")
    minimum_area = _finite_number(min_area_m2, "minimum footprint area")
    if radius <= 0:
        raise BuildingDataError("clip radius must be greater than zero")
    if tolerance < 0:
        raise BuildingDataError("simplification tolerance must not be negative")
    if minimum_area < 0:
        raise BuildingDataError("minimum footprint area must not be negative")
    return easting, northing, radius, tolerance, minimum_area


def _validate_source(buildings: gpd.GeoDataFrame) -> None:
    if not isinstance(buildings, gpd.GeoDataFrame):
        raise BuildingDataError("building source must be a GeoDataFrame")

    missing = sorted(_REQUIRED_FIELDS - set(buildings.columns))
    if missing:
        raise BuildingDataError(f"building source is missing required fields: {', '.join(missing)}")

    if buildings.crs is None:
        raise BuildingDataError("building source CRS is missing")
    if buildings.crs.to_epsg() != MASSACHUSETTS_MAINLAND_EPSG:
        raise BuildingDataError(
            f"building source must use EPSG:{MASSACHUSETTS_MAINLAND_EPSG}"
        )

    identifiers = buildings["STRUCT_ID"]
    if identifiers.isna().any():
        raise BuildingDataError("STRUCT_ID values must not be null")
    if not identifiers.map(lambda value: isinstance(value, str)).all():
        raise BuildingDataError("STRUCT_ID values must be strings")
    normalized_ids = identifiers.str.strip()
    if normalized_ids.eq("").any():
        raise BuildingDataError("STRUCT_ID values must not be blank")
    duplicates = sorted(normalized_ids[normalized_ids.duplicated(keep=False)].unique())
    if duplicates:
        raise BuildingDataError(f"STRUCT_ID values must be unique: {', '.join(duplicates)}")

    geometries = buildings.geometry
    if geometries.isna().any():
        raise BuildingDataError("building geometries must not be null")
    if geometries.is_empty.any():
        raise BuildingDataError("building geometries must not be empty")
    if not geometries.is_valid.all():
        raise BuildingDataError("building geometries must be valid")
    unsupported = sorted(set(buildings.geom_type) - {"Polygon", "MultiPolygon"})
    if unsupported:
        raise BuildingDataError(
            f"building geometries must be Polygon or MultiPolygon, got: {', '.join(unsupported)}"
        )


def _town_matches(value: object) -> bool:
    try:
        numeric_value = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric_value) and numeric_value == LOWELL_TOWN_ID


def _lowell_members(buildings: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    membership = buildings["TOWN_ID"].map(_town_matches)
    membership |= buildings["TOWN_ID2"].map(_town_matches)
    membership |= buildings["TOWN_ID3"].map(_town_matches)
    return buildings.loc[membership].copy()


def _sorted_polygon_parts(geometry: BaseGeometry) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return sorted(
            geometry.geoms,
            key=lambda part: (*part.bounds, part.wkb_hex),
        )
    return []


def _explode_polygons(
    rows: Iterable[tuple[str, BaseGeometry]],
    min_area_m2: float,
) -> list[dict[str, object]]:
    exploded: list[dict[str, object]] = []
    for identifier, geometry in rows:
        parts = _sorted_polygon_parts(geometry)
        multipart = len(parts) > 1 or isinstance(geometry, MultiPolygon)
        for part_number, part in enumerate(parts, start=1):
            if part.is_empty or part.area < min_area_m2:
                continue
            output_id = identifier
            if multipart:
                output_id = f"{identifier}::part-{part_number:03d}"
            exploded.append({"id": output_id, "geometry": part})
    return exploded


def _report(buildings: gpd.GeoDataFrame, stream: TextIO) -> None:
    stream.write(f"MassGIS Lowell building footprints: {len(buildings)}\n")
    if buildings.empty:
        stream.write("Bounds (EPSG:26986 metres): empty\n")
        return
    min_easting, min_northing, max_easting, max_northing = buildings.total_bounds
    stream.write(
        "Bounds (EPSG:26986 metres): "
        f"min_easting={min_easting:.3f}, min_northing={min_northing:.3f}, "
        f"max_easting={max_easting:.3f}, max_northing={max_northing:.3f}\n"
    )


def process_buildings(
    buildings: gpd.GeoDataFrame,
    *,
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
    simplify_tolerance_m: float = SIMPLIFY_TOLERANCE_M,
    min_area_m2: float = MIN_FOOTPRINT_AREA_M2,
    stream: TextIO | None = None,
) -> gpd.GeoDataFrame:
    """Filter, clip, simplify, and safely project MassGIS building records."""
    _validate_source(buildings)
    resolved_origin = approved_initial_origin() if origin is None else origin
    easting, northing, radius, tolerance, minimum_area = _validate_parameters(
        resolved_origin,
        radius_m,
        simplify_tolerance_m,
        min_area_m2,
    )

    circle = Point(easting, northing).buffer(radius, quad_segs=CIRCLE_QUAD_SEGS)
    selected = _lowell_members(buildings)
    selected["STRUCT_ID"] = selected["STRUCT_ID"].str.strip()
    selected = selected.loc[selected.geometry.intersects(circle), ["STRUCT_ID", "geometry"]]
    selected["geometry"] = selected.geometry.intersection(circle)
    selected = selected.loc[~selected.geometry.is_empty].copy()
    selected["geometry"] = selected.geometry.simplify(tolerance, preserve_topology=True)

    records = _explode_polygons(
        (
            (identifier, geometry)
            for identifier, geometry in zip(
                selected["STRUCT_ID"],
                selected.geometry,
                strict=True,
            )
        ),
        minimum_area,
    )
    result = gpd.GeoDataFrame(
        records,
        columns=["id", "geometry"],
        geometry="geometry",
        crs=f"EPSG:{MASSACHUSETTS_MAINLAND_EPSG}",
    )
    result = result.sort_values("id", kind="stable").reset_index(drop=True)

    if result["id"].duplicated().any():
        duplicates = sorted(result.loc[result["id"].duplicated(keep=False), "id"].unique())
        raise BuildingDataError(f"exploded building IDs are not unique: {', '.join(duplicates)}")
    if not result.empty and (not result.geometry.is_valid.all() or result.geometry.is_empty.any()):
        raise BuildingDataError("processed building geometries must be non-empty and valid")
    if set(result.geom_type) - {"Polygon"}:
        raise BuildingDataError("processed building geometries must all be Polygon")

    _report(result, sys.stdout if stream is None else stream)
    return result


def load_massgis_buildings(
    archive_path: str | Path,
    *,
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
    simplify_tolerance_m: float = SIMPLIFY_TOLERANCE_M,
    min_area_m2: float = MIN_FOOTPRINT_AREA_M2,
    stream: TextIO | None = None,
) -> gpd.GeoDataFrame:
    """Read a MassGIS archive and return processed Lowell footprints in EPSG:26986."""
    path = Path(archive_path)
    try:
        buildings = gpd.read_file(path)
    except Exception as error:
        message = f"could not read MassGIS building archive {path}: {error}"
        raise BuildingDataError(message) from error
    return process_buildings(
        buildings,
        origin=origin,
        radius_m=radius_m,
        simplify_tolerance_m=simplify_tolerance_m,
        min_area_m2=min_area_m2,
        stream=stream,
    )
