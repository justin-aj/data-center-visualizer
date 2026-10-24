"""Load, validate, and clip MassGIS context layers for the Lowell pilot.

Road widths and the rail width in this module are visualization values. They are
not surveyed, right-of-way, pavement, or other official physical widths.
"""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

import geopandas as gpd
from shapely.geometry import GeometryCollection, LinearRing, LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

from dcviz_pipeline.context.buildings import (
    CIRCLE_QUAD_SEGS,
    CONTEXT_RADIUS_M,
    MASSACHUSETTS_MAINLAND_EPSG,
    approved_initial_origin,
)

# These class labels and widths are a stable visualization lookup, not official
# road widths. CLASS meanings follow the MassGIS-MassDOT Roads coded-value domain.
ROAD_CLASS_VISUALIZATION: dict[int, tuple[str, float]] = {
    1: ("limited-access-highway", 24.0),
    2: ("multi-lane-highway", 18.0),
    3: ("numbered-route", 14.0),
    4: ("arterial-or-collector", 12.0),
    5: ("local-road", 8.0),
    6: ("local-road-no-inventory", 8.0),
    7: ("ramp", 10.0),
    8: ("tunnel", 8.0),
    9: ("tunnel-limited-access-highway", 24.0),
    10: ("tunnel-multi-lane-highway", 18.0),
    11: ("tunnel-numbered-route", 14.0),
}

# Symbolic rendering width only. The source does not provide corridor width.
RAIL_RENDER_WIDTH_M = 4.0
RAIL_CORRIDOR_NEAR_ORIGIN_M = 100.0


class LayerDataError(ValueError):
    """An ArcGIS context source does not satisfy the layer data contract."""


@dataclass(frozen=True, slots=True)
class LandmarkEvidence:
    """Non-published evidence used to verify the Lowell context package."""

    river_meadow_brook: bool
    olivera_park: bool
    rail_corridor_near_origin: bool
    olivera_source_name: str | None
    rail_nearest_origin_m: float | None
    linear_water_source_features: int


@dataclass(frozen=True, slots=True)
class ContextLayers:
    """Contract-safe State Plane frames ready for task 3.4 serialization."""

    roads: gpd.GeoDataFrame
    railways: gpd.GeoDataFrame
    water: gpd.GeoDataFrame
    open_space: gpd.GeoDataFrame
    landmark_evidence: LandmarkEvidence


@dataclass(frozen=True, slots=True)
class _FeatureComponent:
    attributes: Mapping[str, Any]
    geometry: LineString | Polygon
    diagnostic: str


def _finite_number(value: object, diagnostic: str) -> float:
    if isinstance(value, bool):
        raise LayerDataError(f"{diagnostic}: coordinate must be a finite number")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise LayerDataError(f"{diagnostic}: coordinate must be a finite number") from error
    if not math.isfinite(number):
        raise LayerDataError(f"{diagnostic}: coordinate must be a finite number")
    return number


def _validate_origin_radius(
    origin: tuple[float, float], radius_m: float
) -> tuple[float, float, float]:
    try:
        easting, northing = origin
    except (TypeError, ValueError) as error:
        raise LayerDataError("origin must contain easting and northing") from error
    x = _finite_number(easting, "origin easting")
    y = _finite_number(northing, "origin northing")
    radius = _finite_number(radius_m, "clip radius")
    if radius <= 0:
        raise LayerDataError("clip radius must be greater than zero")
    return x, y, radius


def _feature_diagnostic(source: str, index: int, feature: Mapping[str, Any]) -> str:
    attributes = feature.get("attributes")
    object_id = attributes.get("OBJECTID") if isinstance(attributes, Mapping) else None
    suffix = f" (OBJECTID={object_id})" if object_id is not None else ""
    return f"{source} feature {index}{suffix}"


def _load_feature_set(
    path: str | Path, *, source: str, geometry_type: str
) -> tuple[list[Any], str]:
    input_path = Path(path)
    try:
        with input_path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        message = f"{source}: could not read ArcGIS JSON {input_path}: {error}"
        raise LayerDataError(message) from error

    if not isinstance(payload, Mapping):
        raise LayerDataError(f"{source}: ArcGIS JSON root must be an object")
    if "error" in payload:
        arc_error = payload["error"]
        if isinstance(arc_error, Mapping):
            message = arc_error.get("message", "unknown ArcGIS service error")
            details = arc_error.get("details")
            if isinstance(details, list) and details:
                message = f"{message}: {'; '.join(str(item) for item in details)}"
        else:
            message = str(arc_error)
        raise LayerDataError(f"{source}: ArcGIS service error: {message}")

    actual_type = payload.get("geometryType")
    if actual_type != geometry_type:
        raise LayerDataError(f"{source}: geometryType must be {geometry_type}, got {actual_type!r}")

    spatial_reference = payload.get("spatialReference")
    if not isinstance(spatial_reference, Mapping):
        raise LayerDataError(f"{source}: spatialReference must be an object")
    epsg = spatial_reference.get("latestWkid", spatial_reference.get("wkid"))
    if epsg != MASSACHUSETTS_MAINLAND_EPSG:
        raise LayerDataError(
            f"{source}: spatialReference must resolve to EPSG:{MASSACHUSETTS_MAINLAND_EPSG}, "
            f"got {epsg!r}"
        )

    features = payload.get("features")
    if not isinstance(features, list):
        raise LayerDataError(f"{source}: features must be a list")
    return features, str(input_path)


def _feature_parts(
    feature: object, *, source: str, index: int
) -> tuple[Mapping[str, Any], Mapping[str, Any], str]:
    if not isinstance(feature, Mapping):
        raise LayerDataError(f"{source} feature {index}: record must be an object")
    diagnostic = _feature_diagnostic(source, index, feature)
    attributes = feature.get("attributes")
    geometry = feature.get("geometry")
    if not isinstance(attributes, Mapping):
        raise LayerDataError(f"{diagnostic}: attributes must be an object")
    if not isinstance(geometry, Mapping):
        raise LayerDataError(f"{diagnostic}: geometry must be an object")
    return attributes, geometry, diagnostic


def _coordinate(value: object, diagnostic: str) -> tuple[float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 2:
        raise LayerDataError(f"{diagnostic}: coordinate must contain x and y")
    return (
        _finite_number(value[0], f"{diagnostic} x"),
        _finite_number(value[1], f"{diagnostic} y"),
    )


def _read_polyline_components(path: str | Path, *, source: str) -> list[_FeatureComponent]:
    features, _ = _load_feature_set(path, source=source, geometry_type="esriGeometryPolyline")
    components: list[_FeatureComponent] = []
    for feature_index, feature in enumerate(features, start=1):
        attributes, geometry, diagnostic = _feature_parts(
            feature, source=source, index=feature_index
        )
        paths = geometry.get("paths")
        if not isinstance(paths, list) or not paths:
            raise LayerDataError(f"{diagnostic}: geometry.paths must be a non-empty list")
        for path_index, path_points in enumerate(paths, start=1):
            path_diagnostic = f"{diagnostic} path {path_index}"
            if not isinstance(path_points, list) or len(path_points) < 2:
                raise LayerDataError(f"{path_diagnostic}: path must contain at least two points")
            coordinates = [
                _coordinate(point, f"{path_diagnostic} point {point_index}")
                for point_index, point in enumerate(path_points, start=1)
            ]
            line = LineString(coordinates)
            if line.is_empty or not line.is_valid or line.length == 0:
                raise LayerDataError(f"{path_diagnostic}: path must form a valid non-zero line")
            components.append(_FeatureComponent(attributes, line, path_diagnostic))
    return components


def _signed_ring_area(coordinates: Sequence[tuple[float, float]]) -> float:
    return 0.5 * sum(
        (x1 * y2) - (x2 * y1) for (x1, y1), (x2, y2) in zip(coordinates, coordinates[1:])
    )


def _polygon_components(
    rings_value: object, *, attributes: Mapping[str, Any], diagnostic: str
) -> list[_FeatureComponent]:
    if not isinstance(rings_value, list) or not rings_value:
        raise LayerDataError(f"{diagnostic}: geometry.rings must be a non-empty list")

    rings: list[tuple[int, list[tuple[float, float]], float, Polygon]] = []
    for ring_index, ring_points in enumerate(rings_value, start=1):
        ring_diagnostic = f"{diagnostic} ring {ring_index}"
        if not isinstance(ring_points, list) or len(ring_points) < 4:
            raise LayerDataError(f"{ring_diagnostic}: ring must contain at least four points")
        coordinates = [
            _coordinate(point, f"{ring_diagnostic} point {point_index}")
            for point_index, point in enumerate(ring_points, start=1)
        ]
        if coordinates[0] != coordinates[-1]:
            raise LayerDataError(f"{ring_diagnostic}: ring must be closed")
        area = _signed_ring_area(coordinates)
        if area == 0:
            raise LayerDataError(f"{ring_diagnostic}: ring must enclose a non-zero area")
        linear_ring = LinearRing(coordinates)
        ring_polygon = Polygon(linear_ring)
        if not linear_ring.is_simple or not ring_polygon.is_valid:
            raise LayerDataError(f"{ring_diagnostic}: ring must be simple and valid")
        rings.append((ring_index, coordinates, area, ring_polygon))

    # ArcGIS polygon rings use clockwise exteriors and counter-clockwise holes.
    exteriors = [ring for ring in rings if ring[2] < 0]
    holes = [ring for ring in rings if ring[2] > 0]
    if not exteriors:
        raise LayerDataError(f"{diagnostic}: polygon has no clockwise exterior ring")

    assigned_holes: dict[int, list[list[tuple[float, float]]]] = {
        exterior[0]: [] for exterior in exteriors
    }
    for hole_index, hole_coordinates, _, hole_polygon in holes:
        containers = [exterior for exterior in exteriors if exterior[3].covers(hole_polygon)]
        if not containers:
            raise LayerDataError(
                f"{diagnostic} ring {hole_index}: counter-clockwise hole is not inside an exterior"
            )
        container = min(containers, key=lambda exterior: exterior[3].area)
        assigned_holes[container[0]].append(hole_coordinates)

    components: list[_FeatureComponent] = []
    for exterior_index, exterior_coordinates, _, _ in exteriors:
        polygon = Polygon(exterior_coordinates, assigned_holes[exterior_index])
        if polygon.is_empty or not polygon.is_valid or polygon.area == 0:
            raise LayerDataError(
                f"{diagnostic} ring {exterior_index}: grouped polygon must be valid"
            )
        components.append(
            _FeatureComponent(attributes, polygon, f"{diagnostic} exterior {exterior_index}")
        )
    return components


def _read_polygon_components(path: str | Path, *, source: str) -> list[_FeatureComponent]:
    features, _ = _load_feature_set(path, source=source, geometry_type="esriGeometryPolygon")
    components: list[_FeatureComponent] = []
    for feature_index, feature in enumerate(features, start=1):
        attributes, geometry, diagnostic = _feature_parts(
            feature, source=source, index=feature_index
        )
        components.extend(
            _polygon_components(geometry.get("rings"), attributes=attributes, diagnostic=diagnostic)
        )
    return components


def _line_parts(geometry: BaseGeometry) -> list[LineString]:
    if isinstance(geometry, LineString):
        return [geometry]
    if geometry.geom_type == "MultiLineString" or isinstance(geometry, GeometryCollection):
        parts: list[LineString] = []
        for component in geometry.geoms:  # type: ignore[attr-defined]
            parts.extend(_line_parts(component))
        return parts
    return []


def _polygon_parts(geometry: BaseGeometry) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if geometry.geom_type == "MultiPolygon" or isinstance(geometry, GeometryCollection):
        parts: list[Polygon] = []
        for component in geometry.geoms:  # type: ignore[attr-defined]
            parts.extend(_polygon_parts(component))
        return parts
    return []


def _clip_parts(
    geometry: LineString | Polygon, clip_circle: Polygon, *, diagnostic: str
) -> list[LineString] | list[Polygon]:
    if not geometry.intersects(clip_circle):
        return []
    clipped = geometry.intersection(clip_circle)
    parts = _line_parts(clipped) if isinstance(geometry, LineString) else _polygon_parts(clipped)
    valid_parts = [part for part in parts if not part.is_empty and part.is_valid]
    if any(isinstance(part, LineString) and part.length == 0 for part in valid_parts):
        raise LayerDataError(f"{diagnostic}: clipping produced a zero-length line")
    if any(isinstance(part, Polygon) and part.area == 0 for part in valid_parts):
        raise LayerDataError(f"{diagnostic}: clipping produced a zero-area polygon")
    return valid_parts


def _frame(records: list[dict[str, object]], columns: list[str]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        records,
        columns=columns,
        geometry="geometry",
        crs=f"EPSG:{MASSACHUSETTS_MAINLAND_EPSG}",
    )


def _required_attribute(attributes: Mapping[str, Any], name: str, diagnostic: str) -> Any:
    if name not in attributes:
        raise LayerDataError(f"{diagnostic}: attributes.{name} is required")
    return attributes[name]


def _road_class(value: object, diagnostic: str) -> tuple[str, float]:
    if isinstance(value, bool) or value is None:
        raise LayerDataError(f"{diagnostic}: CLASS must be one of 1 through 11")
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise LayerDataError(f"{diagnostic}: CLASS must be one of 1 through 11") from error
    if not math.isfinite(numeric) or not numeric.is_integer():
        raise LayerDataError(f"{diagnostic}: CLASS must be one of 1 through 11")
    road_class = int(numeric)
    try:
        return ROAD_CLASS_VISUALIZATION[road_class]
    except KeyError as error:
        raise LayerDataError(
            f"{diagnostic}: unsupported road CLASS {road_class}; expected 1 through 11"
        ) from error


def load_roads(
    path: str | Path,
    *,
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
) -> gpd.GeoDataFrame:
    """Load roads as contract-safe EPSG:26986 LineStrings."""
    resolved_origin = approved_initial_origin() if origin is None else origin
    x, y, radius = _validate_origin_radius(resolved_origin, radius_m)
    circle = Point(x, y).buffer(radius, quad_segs=CIRCLE_QUAD_SEGS)
    records: list[dict[str, object]] = []
    for component in _read_polyline_components(path, source="roads"):
        class_label, width = _road_class(
            _required_attribute(component.attributes, "CLASS", component.diagnostic),
            component.diagnostic,
        )
        for line in _clip_parts(component.geometry, circle, diagnostic=component.diagnostic):
            records.append({"class": class_label, "widthM": width, "geometry": line})
    return _frame(records, ["class", "widthM", "geometry"])


def load_railways(
    path: str | Path,
    *,
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
) -> gpd.GeoDataFrame:
    """Load rail linework with an explicitly non-official rendering width."""
    resolved_origin = approved_initial_origin() if origin is None else origin
    x, y, radius = _validate_origin_radius(resolved_origin, radius_m)
    circle = Point(x, y).buffer(radius, quad_segs=CIRCLE_QUAD_SEGS)
    records: list[dict[str, object]] = []
    for component in _read_polyline_components(path, source="railways"):
        for line in _clip_parts(component.geometry, circle, diagnostic=component.diagnostic):
            records.append({"widthM": RAIL_RENDER_WIDTH_M, "geometry": line})
    return _frame(records, ["widthM", "geometry"])


def _clean_optional_name(value: object, diagnostic: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise LayerDataError(f"{diagnostic}: NAME must be a string or null")
    normalized = value.strip()
    return normalized or None


def load_water_polygons(
    path: str | Path,
    *,
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
) -> gpd.GeoDataFrame:
    """Load polygonal water only; linear hydrography is never buffered."""
    resolved_origin = approved_initial_origin() if origin is None else origin
    x, y, radius = _validate_origin_radius(resolved_origin, radius_m)
    circle = Point(x, y).buffer(radius, quad_segs=CIRCLE_QUAD_SEGS)
    records: list[dict[str, object]] = []
    for component in _read_polygon_components(path, source="water polygons"):
        name = _clean_optional_name(
            _required_attribute(component.attributes, "NAME", component.diagnostic),
            component.diagnostic,
        )
        for polygon in _clip_parts(component.geometry, circle, diagnostic=component.diagnostic):
            records.append({"name": name, "geometry": polygon})
    frame = _frame(records, ["name", "geometry"])
    # Pandas may infer its string dtype and replace None with NaN. Keep a true
    # nullable object value so task 3.4 can omit unnamed features safely.
    frame["name"] = frame["name"].astype(object)
    frame.loc[frame["name"].isna(), "name"] = None
    return frame


def _open_space_kind(attributes: Mapping[str, Any], diagnostic: str) -> str:
    purpose = _required_attribute(attributes, "PRIM_PURP", diagnostic)
    open_space_type = _required_attribute(attributes, "OS_TYPE", diagnostic)
    for field_name, value in (("PRIM_PURP", purpose), ("OS_TYPE", open_space_type)):
        if value is not None and not isinstance(value, str):
            raise LayerDataError(f"{diagnostic}: {field_name} must be a string or null")
    purpose_text = purpose.strip().casefold() if isinstance(purpose, str) else ""
    type_text = open_space_type.strip().casefold() if isinstance(open_space_type, str) else ""
    if "field" in type_text:
        return "field"
    if any(term in type_text for term in ("wooded", "woodland", "forest")):
        return "wooded"
    if purpose_text == "r" or ("park" in type_text and "active" in type_text):
        return "park"
    return "other"


def _public_access(value: object) -> bool:
    return isinstance(value, str) and value.strip().casefold() == "y"


def _open_space_name(attributes: Mapping[str, Any]) -> str | None:
    for field in ("SITE_NAME", "ALT_SITE_NAME", "FORMAL_SITE_NAME"):
        value = attributes.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _load_open_space_with_evidence(
    path: str | Path,
    *,
    origin: tuple[float, float],
    radius_m: float,
) -> tuple[gpd.GeoDataFrame, str | None]:
    x, y, radius = _validate_origin_radius(origin, radius_m)
    circle = Point(x, y).buffer(radius, quad_segs=CIRCLE_QUAD_SEGS)
    records: list[dict[str, object]] = []
    olivera_source_name: str | None = None
    for component in _read_polygon_components(path, source="open space"):
        kind = _open_space_kind(component.attributes, component.diagnostic)
        access = _public_access(
            _required_attribute(component.attributes, "PUB_ACCESS", component.diagnostic)
        )
        clipped_parts = _clip_parts(component.geometry, circle, diagnostic=component.diagnostic)
        name = _open_space_name(component.attributes)
        if clipped_parts and name is not None and name.casefold() == "olivera park":
            olivera_source_name = name
        for polygon in clipped_parts:
            records.append({"kind": kind, "publicAccess": access, "geometry": polygon})
    return _frame(records, ["kind", "publicAccess", "geometry"]), olivera_source_name


def load_open_space(
    path: str | Path,
    *,
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
) -> gpd.GeoDataFrame:
    """Load privacy-safe open space without publishing source names or ownership."""
    resolved_origin = approved_initial_origin() if origin is None else origin
    frame, _ = _load_open_space_with_evidence(path, origin=resolved_origin, radius_m=radius_m)
    return frame


def _linear_water_feature_count(path: str | Path) -> int:
    features = _read_polyline_components(path, source="linear water")
    # Count source records rather than paths while still validating every path.
    return len({component.diagnostic.split(" path ", maxsplit=1)[0] for component in features})


def verify_required_landmarks(evidence: LandmarkEvidence) -> None:
    """Require the three Lowell landmarks named by task 3.3."""
    missing: list[str] = []
    if not evidence.river_meadow_brook:
        missing.append("River Meadow Brook")
    if not evidence.olivera_park:
        missing.append("Olivera Park (source spelling; task calls it Oliveira Park)")
    if not evidence.rail_corridor_near_origin:
        missing.append(f"rail corridor within {RAIL_CORRIDOR_NEAR_ORIGIN_M:g} m of origin")
    if missing:
        raise LayerDataError(f"Lowell landmark verification failed: {', '.join(missing)}")


def assemble_context_layers(
    *,
    roads_path: str | Path,
    railways_path: str | Path,
    water_polygons_path: str | Path,
    water_lines_path: str | Path,
    open_space_path: str | Path,
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
    require_landmarks: bool = True,
    stream: TextIO | None = None,
) -> ContextLayers:
    """Assemble all context layers in EPSG:26986 for the context writer."""
    resolved_origin = approved_initial_origin() if origin is None else origin
    x, y, radius = _validate_origin_radius(resolved_origin, radius_m)
    output = sys.stdout if stream is None else stream

    roads = load_roads(roads_path, origin=(x, y), radius_m=radius)
    railways = load_railways(railways_path, origin=(x, y), radius_m=radius)
    water = load_water_polygons(water_polygons_path, origin=(x, y), radius_m=radius)
    open_space, olivera_source_name = _load_open_space_with_evidence(
        open_space_path, origin=(x, y), radius_m=radius
    )
    linear_water_count = _linear_water_feature_count(water_lines_path)

    origin_point = Point(x, y)
    nearest_rail = (
        min(float(geometry.distance(origin_point)) for geometry in railways.geometry)
        if not railways.empty
        else None
    )
    evidence = LandmarkEvidence(
        river_meadow_brook=any(
            isinstance(name, str) and name.casefold() == "river meadow brook"
            for name in water["name"]
        ),
        olivera_park=olivera_source_name is not None,
        rail_corridor_near_origin=(
            nearest_rail is not None and nearest_rail <= RAIL_CORRIDOR_NEAR_ORIGIN_M
        ),
        olivera_source_name=olivera_source_name,
        rail_nearest_origin_m=nearest_rail,
        linear_water_source_features=linear_water_count,
    )
    if require_landmarks:
        verify_required_landmarks(evidence)

    output.write(f"Context roads: {len(roads)}\n")
    output.write(f"Context railways: {len(railways)}\n")
    output.write(f"Context water polygons: {len(water)}\n")
    output.write(f"Context open space: {len(open_space)}\n")
    output.write(
        f"Linear water: {linear_water_count} source features validated; 0 emitted "
        "(context contract is Polygon-only; no buffering applied)\n"
    )
    nearest_text = "none" if nearest_rail is None else f"{nearest_rail:.1f} m"
    output.write(
        "Landmarks: "
        f"River Meadow Brook={'yes' if evidence.river_meadow_brook else 'no'}; "
        f"Olivera Park={'yes' if evidence.olivera_park else 'no'} "
        "(source spelling; task calls it Oliveira Park); "
        f"rail corridor near origin={'yes' if evidence.rail_corridor_near_origin else 'no'} "
        f"(nearest {nearest_text})\n"
    )

    return ContextLayers(roads, railways, water, open_space, evidence)
