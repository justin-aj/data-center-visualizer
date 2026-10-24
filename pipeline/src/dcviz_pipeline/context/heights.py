"""Assign privacy-safe height evidence to MassGIS context buildings."""

from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TextIO

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point, Polygon

from dcviz_pipeline.context.buildings import (
    CIRCLE_QUAD_SEGS,
    CONTEXT_RADIUS_M,
    MASSACHUSETTS_MAINLAND_EPSG,
    approved_initial_origin,
)

LEVEL_HEIGHT_M = 3.0
MIN_OVERLAP_COEFFICIENT = 0.75
MAX_CENTROID_DISTANCE_M = 10.0
EXPLICIT_AGREEMENT_TOLERANCE_M = 0.5

OSM_EXPLICIT_SOURCE = "OpenStreetMap explicit height"
OSM_LEVELS_SOURCE = "OpenStreetMap building:levels × 3.0 m"
OVERTURE_USGS_LIDAR_SOURCE = "Overture explicit height (USGS Lidar)"
OVERTURE_MICROSOFT_ML_SOURCE = "Overture explicit height (Microsoft ML Buildings)"
OVERTURE_UNSPECIFIED_SOURCE = "Overture explicit height (source unspecified)"
AREA_UNDER_200_SOURCE = "Visual-massing area default (<200 m²): 7 m"
AREA_200_TO_1000_SOURCE = "Visual-massing area default (200–<1000 m²): 9 m"
AREA_AT_LEAST_1000_SOURCE = "Visual-massing area default (≥1000 m²): 12 m"

_HEIGHT_PATTERN = re.compile(
    r"^(?P<number>(?:\d+(?:\.\d+)?|\.\d+))\s*(?P<unit>m|ft|')?$",
    re.IGNORECASE,
)
_LEVELS_PATTERN = re.compile(r"^(?:\d+(?:\.\d+)?|\.\d+)$")
_ALLOWED_SOURCE_KINDS = {
    "osm",
    "overture-usgs-lidar",
    "overture-microsoft-ml",
    "overture-unspecified",
}
_SOURCE_LABELS = {
    "osm": OSM_EXPLICIT_SOURCE,
    "overture-usgs-lidar": OVERTURE_USGS_LIDAR_SOURCE,
    "overture-microsoft-ml": OVERTURE_MICROSOFT_ML_SOURCE,
    "overture-unspecified": OVERTURE_UNSPECIFIED_SOURCE,
}
_SOURCE_STATUSES = {
    "osm": "estimated",
    "overture-usgs-lidar": "derived",
    "overture-microsoft-ml": "estimated",
    "overture-unspecified": "estimated",
}

SourceKind = Literal[
    "osm",
    "overture-usgs-lidar",
    "overture-microsoft-ml",
    "overture-unspecified",
]
HeightStatus = Literal["derived", "estimated"]


class HeightDataError(ValueError):
    """Height evidence or building input violates the context-height contract."""


@dataclass(frozen=True, slots=True)
class HeightCandidate:
    """A normalized, geometry-only height observation in EPSG:26986.

    ``source_kind`` is intentionally a closed vocabulary. It prevents source records from
    carrying names, addresses, websites, contributor metadata, or arbitrary tags into output.
    """

    record_id: str
    geometry: Polygon
    source_kind: SourceKind
    explicit_height_m: float | None = None
    levels: float | None = None


@dataclass(frozen=True, slots=True)
class HeightCoverage:
    """Final building counts grouped by the exact emitted ``heightSource`` value."""

    total_buildings: int
    counts_by_source: dict[str, int]

    def percentage(self, source: str) -> float:
        """Return a source's percentage of all buildings, or zero for an empty frame."""
        if self.total_buildings == 0:
            return 0.0
        return 100.0 * self.counts_by_source.get(source, 0) / self.total_buildings


def parse_height_m(value: object) -> float | None:
    """Parse a strict positive OSM height in metres or feet.

    Accepted forms include ``12``, ``12 m``, ``40 ft``, and ``40'``. Ranges, lists,
    descriptive text, non-finite values, zero, and negative values are rejected.
    """
    if not isinstance(value, str):
        return None
    match = _HEIGHT_PATTERN.fullmatch(value.strip())
    if match is None:
        return None
    number = float(match.group("number"))
    unit = (match.group("unit") or "").lower()
    if unit in {"ft", "'"}:
        number *= 0.3048
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def parse_levels(value: object) -> float | None:
    """Parse a strict positive decimal building-level count."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if _LEVELS_PATTERN.fullmatch(normalized) is None:
        return None
    levels = float(normalized)
    if not math.isfinite(levels) or levels <= 0:
        return None
    return levels


def area_default_height_m(area_m2: float) -> tuple[float, str]:
    """Return the documented visual-massing assumption for a footprint area."""
    try:
        area = float(area_m2)
    except (TypeError, ValueError) as error:
        raise HeightDataError("footprint area must be a finite non-negative number") from error
    if not math.isfinite(area) or area < 0:
        raise HeightDataError("footprint area must be a finite non-negative number")
    if area < 200.0:
        return 7.0, AREA_UNDER_200_SOURCE
    if area < 1_000.0:
        return 9.0, AREA_200_TO_1000_SOURCE
    return 12.0, AREA_AT_LEAST_1000_SOURCE


def overture_height_candidate(
    record_id: str,
    geometry: Polygon,
    height_m: float,
    *,
    source_dataset: Literal["usgs-lidar", "microsoft-ml", "unspecified"] = "unspecified",
) -> HeightCandidate:
    """Create an optional normalized Overture candidate without requiring live services.

    The caller remains responsible for loading a bounded, versioned Overture extract and for
    mapping its documented height-property source to ``source_dataset``.
    """
    source_kinds: dict[str, SourceKind] = {
        "usgs-lidar": "overture-usgs-lidar",
        "microsoft-ml": "overture-microsoft-ml",
        "unspecified": "overture-unspecified",
    }
    if source_dataset not in source_kinds:
        raise HeightDataError(f"unsupported Overture source dataset: {source_dataset}")
    candidate = HeightCandidate(
        record_id=record_id,
        geometry=geometry,
        source_kind=source_kinds[source_dataset],
        explicit_height_m=height_m,
    )
    _validate_candidate(candidate)
    return candidate


def _finite_coordinate(value: object, field: str, record_id: str) -> float:
    if isinstance(value, bool):
        raise HeightDataError(f"OSM way {record_id} has invalid {field}")
    try:
        coordinate = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise HeightDataError(f"OSM way {record_id} has invalid {field}") from error
    if not math.isfinite(coordinate):
        raise HeightDataError(f"OSM way {record_id} has invalid {field}")
    return coordinate


def _way_polygon(
    element: Mapping[str, object],
    transformer: Transformer,
    record_id: str,
) -> Polygon:
    raw_geometry = element.get("geometry")
    if not isinstance(raw_geometry, list) or len(raw_geometry) < 4:
        raise HeightDataError(f"OSM way {record_id} must have at least four geometry positions")

    lon_lat: list[tuple[float, float]] = []
    for position in raw_geometry:
        if not isinstance(position, Mapping):
            raise HeightDataError(f"OSM way {record_id} has an invalid geometry position")
        lon = _finite_coordinate(position.get("lon"), "longitude", record_id)
        lat = _finite_coordinate(position.get("lat"), "latitude", record_id)
        if not -180.0 <= lon <= 180.0 or not -90.0 <= lat <= 90.0:
            raise HeightDataError(f"OSM way {record_id} has an out-of-range coordinate")
        lon_lat.append((lon, lat))

    if lon_lat[0] != lon_lat[-1]:
        raise HeightDataError(f"OSM way {record_id} geometry must be closed")
    geometry = Polygon([transformer.transform(lon, lat) for lon, lat in lon_lat])
    if geometry.is_empty or not geometry.is_valid or geometry.area <= 0:
        raise HeightDataError(f"OSM way {record_id} geometry must be a valid non-empty polygon")
    return geometry


def _element_id(element: Mapping[str, object]) -> str:
    value = element.get("id")
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise HeightDataError("OSM element id must be a string or integer")
    record_id = str(value).strip()
    if not record_id:
        raise HeightDataError("OSM element id must not be blank")
    return record_id


def load_osm_height_candidates(
    cache_path: str | Path,
    *,
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
    stream: TextIO | None = None,
) -> tuple[HeightCandidate, ...]:
    """Load a cached Overpass JSON response into privacy-safe height candidates.

    Closed OSM ways are supported. Relations are rejected explicitly because reconstructing
    multipolygon member roles from ``out tags geom`` safely is outside this task's contract.
    """
    path = Path(cache_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise HeightDataError(f"could not read OSM height cache {path}: {error}") from error
    if not isinstance(payload, Mapping):
        raise HeightDataError("OSM height cache root must be an object")
    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise HeightDataError("OSM height cache must contain an elements array")

    resolved_origin = approved_initial_origin() if origin is None else origin
    try:
        origin_x, origin_y = (float(value) for value in resolved_origin)
        radius = float(radius_m)
    except (TypeError, ValueError) as error:
        raise HeightDataError("clip origin and radius must be finite numbers") from error
    if not all(math.isfinite(value) for value in (origin_x, origin_y, radius)) or radius <= 0:
        raise HeightDataError("clip origin must be finite and radius must be positive")

    transformer = Transformer.from_crs(4326, MASSACHUSETTS_MAINLAND_EPSG, always_xy=True)
    circle = Point(origin_x, origin_y).buffer(radius, quad_segs=CIRCLE_QUAD_SEGS)
    seen_ids: set[str] = set()
    candidates: list[HeightCandidate] = []
    ways_in_circle = 0
    rejected_values = 0

    for raw_element in elements:
        if not isinstance(raw_element, Mapping):
            raise HeightDataError("each OSM element must be an object")
        element_type = raw_element.get("type")
        record_id = _element_id(raw_element)
        if element_type == "relation":
            raise HeightDataError(f"OSM relation {record_id} is not supported")
        if element_type != "way":
            raise HeightDataError(f"unsupported OSM element type for {record_id}: {element_type}")
        if record_id in seen_ids:
            raise HeightDataError(f"duplicate OSM element id: {record_id}")
        seen_ids.add(record_id)

        geometry = _way_polygon(raw_element, transformer, record_id)
        if not geometry.intersects(circle):
            continue
        ways_in_circle += 1

        tags = raw_element.get("tags")
        if not isinstance(tags, Mapping):
            raise HeightDataError(f"OSM way {record_id} tags must be an object")
        explicit = parse_height_m(tags.get("height")) if "height" in tags else None
        levels = parse_levels(tags.get("building:levels")) if "building:levels" in tags else None
        if explicit is None and levels is None:
            rejected_values += 1
            continue
        candidates.append(
            HeightCandidate(
                record_id=record_id,
                geometry=geometry,
                source_kind="osm",
                explicit_height_m=explicit,
                levels=levels,
            )
        )

    output = sys.stdout if stream is None else stream
    output.write(
        f"OSM height cache: {len(elements)} ways in bounding box; "
        f"{ways_in_circle} intersect the clip circle; "
        f"{len(candidates)} valid observations\n"
    )
    if rejected_values:
        output.write(f"Rejected OSM observations with no valid height value: {rejected_values}\n")
    return tuple(candidates)


def _validate_buildings(buildings: gpd.GeoDataFrame) -> None:
    if not isinstance(buildings, gpd.GeoDataFrame):
        raise HeightDataError("buildings must be a GeoDataFrame")
    missing = sorted({"id", "geometry"} - set(buildings.columns))
    if missing:
        raise HeightDataError(f"buildings are missing required fields: {', '.join(missing)}")
    if buildings.crs is None:
        raise HeightDataError("building CRS is missing")
    if buildings.crs.to_epsg() != MASSACHUSETTS_MAINLAND_EPSG:
        raise HeightDataError(
            f"buildings must use EPSG:{MASSACHUSETTS_MAINLAND_EPSG}"
        )
    identifiers = buildings["id"]
    if identifiers.isna().any() or not identifiers.map(lambda value: isinstance(value, str)).all():
        raise HeightDataError("building ids must be non-null strings")
    normalized = identifiers.map(lambda value: value.strip())
    if normalized.eq("").any():
        raise HeightDataError("building ids must not be blank")
    if normalized.duplicated().any():
        raise HeightDataError("building ids must be unique")
    geometries = buildings.geometry
    if geometries.isna().any() or geometries.is_empty.any():
        raise HeightDataError("building geometries must be non-null and non-empty")
    if not geometries.is_valid.all() or set(buildings.geom_type) - {"Polygon"}:
        raise HeightDataError("building geometries must be valid Polygons")


def _validate_candidate(candidate: HeightCandidate) -> None:
    if not isinstance(candidate, HeightCandidate):
        raise HeightDataError("height candidates must be HeightCandidate instances")
    if not isinstance(candidate.record_id, str) or not candidate.record_id.strip():
        raise HeightDataError("height candidate record_id must be a non-empty string")
    if candidate.source_kind not in _ALLOWED_SOURCE_KINDS:
        raise HeightDataError(f"unsupported height candidate source: {candidate.source_kind}")
    if not isinstance(candidate.geometry, Polygon):
        raise HeightDataError(f"height candidate {candidate.record_id} geometry must be a Polygon")
    if (
        candidate.geometry.is_empty
        or not candidate.geometry.is_valid
        or candidate.geometry.area <= 0
    ):
        raise HeightDataError(
            f"height candidate {candidate.record_id} geometry must be valid and non-empty"
        )
    for field, value in (
        ("explicit_height_m", candidate.explicit_height_m),
        ("levels", candidate.levels),
    ):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HeightDataError(f"height candidate {candidate.record_id} {field} must be numeric")
        if not math.isfinite(float(value)) or float(value) <= 0:
            raise HeightDataError(
                f"height candidate {candidate.record_id} {field} must be positive and finite"
            )
    if candidate.explicit_height_m is None and candidate.levels is None:
        raise HeightDataError(
            f"height candidate {candidate.record_id} has no usable height evidence"
        )
    if candidate.source_kind != "osm" and candidate.levels is not None:
        raise HeightDataError("only OpenStreetMap candidates may contain building levels")


def _matching_candidates(
    buildings: gpd.GeoDataFrame,
    candidates: Sequence[HeightCandidate],
    stream: TextIO,
) -> tuple[dict[int, list[HeightCandidate]], int, int]:
    matches: dict[int, list[HeightCandidate]] = defaultdict(list)
    ambiguous = 0
    unmatched = 0
    spatial_index = buildings.sindex

    for candidate in sorted(candidates, key=lambda item: (item.source_kind, item.record_id)):
        eligible: list[tuple[float, float, int, str]] = []
        for position in spatial_index.query(candidate.geometry, predicate="intersects"):
            building_geometry = buildings.geometry.iloc[position]
            intersection_area = candidate.geometry.intersection(building_geometry).area
            denominator = min(candidate.geometry.area, building_geometry.area)
            overlap = intersection_area / denominator
            distance = candidate.geometry.centroid.distance(building_geometry.centroid)
            if overlap >= MIN_OVERLAP_COEFFICIENT and distance <= MAX_CENTROID_DISTANCE_M:
                eligible.append((overlap, distance, int(position), buildings["id"].iloc[position]))

        eligible.sort(key=lambda item: (-item[0], item[1], item[3]))
        if not eligible:
            unmatched += 1
            continue
        if len(eligible) > 1 and math.isclose(
            eligible[0][0], eligible[1][0], abs_tol=1e-12
        ) and math.isclose(eligible[0][1], eligible[1][1], abs_tol=1e-9):
            ambiguous += 1
            stream.write(
                f"Ambiguous geometry match for {candidate.source_kind} record "
                f"{candidate.record_id}; candidate ignored\n"
            )
            continue
        matches[eligible[0][2]].append(candidate)

    return matches, ambiguous, unmatched


def _agree(values: Sequence[float]) -> bool:
    return max(values) - min(values) <= EXPLICIT_AGREEMENT_TOLERANCE_M


def _explicit_assignment(
    candidates: Sequence[HeightCandidate],
) -> tuple[float, HeightStatus, str] | None:
    explicit = [candidate for candidate in candidates if candidate.explicit_height_m is not None]
    if not explicit:
        return None
    values = [float(candidate.explicit_height_m) for candidate in explicit]
    if not _agree(values):
        return None
    labels = sorted({_SOURCE_LABELS[candidate.source_kind] for candidate in explicit})
    source = labels[0] if len(labels) == 1 else "Agreeing explicit heights: " + " + ".join(labels)
    statuses = {_SOURCE_STATUSES[candidate.source_kind] for candidate in explicit}
    status: HeightStatus = "derived" if statuses == {"derived"} else "estimated"
    return sum(values) / len(values), status, source


def _levels_assignment(
    candidates: Sequence[HeightCandidate],
) -> tuple[float, HeightStatus, str] | None:
    values = [
        float(candidate.levels) * LEVEL_HEIGHT_M
        for candidate in candidates
        if candidate.levels
    ]
    if not values or not _agree(values):
        return None
    return sum(values) / len(values), "estimated", OSM_LEVELS_SOURCE


def height_coverage(buildings: gpd.GeoDataFrame) -> HeightCoverage:
    """Count enriched buildings by exact ``heightSource`` value."""
    if "heightSource" not in buildings.columns:
        raise HeightDataError("enriched buildings are missing heightSource")
    counts = {
        str(source): int(count)
        for source, count in buildings["heightSource"].value_counts(sort=False).items()
    }
    return HeightCoverage(
        total_buildings=len(buildings),
        counts_by_source=dict(sorted(counts.items())),
    )


def _validate_output(buildings: gpd.GeoDataFrame) -> None:
    expected = ["id", "heightM", "heightStatus", "heightSource", "geometry"]
    if list(buildings.columns) != expected:
        raise HeightDataError("height output has unexpected columns")
    if not buildings["heightM"].map(
        lambda value: isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0
    ).all():
        raise HeightDataError("every building height must be positive and finite")
    if not buildings["heightStatus"].isin({"derived", "estimated"}).all():
        raise HeightDataError("every building heightStatus must be derived or estimated")
    if not buildings["heightSource"].map(
        lambda value: isinstance(value, str) and bool(value.strip())
    ).all():
        raise HeightDataError("every building heightSource must be a non-empty string")


def assign_building_heights(
    buildings: gpd.GeoDataFrame,
    *,
    osm_candidates: Iterable[HeightCandidate] = (),
    overture_candidates: Iterable[HeightCandidate] = (),
    stream: TextIO | None = None,
) -> gpd.GeoDataFrame:
    """Enrich task 3.1 buildings using explicit, levels, then area-default evidence."""
    _validate_buildings(buildings)
    output = sys.stdout if stream is None else stream
    osm = tuple(osm_candidates)
    overture = tuple(overture_candidates)
    for candidate in (*osm, *overture):
        _validate_candidate(candidate)
    if any(candidate.source_kind != "osm" for candidate in osm):
        raise HeightDataError("osm_candidates contains a non-OSM source")
    if any(candidate.source_kind == "osm" for candidate in overture):
        raise HeightDataError("overture_candidates contains an OSM source")

    working = buildings.loc[:, ["id", "geometry"]].copy().reset_index(drop=True)
    matched, ambiguous, unmatched = _matching_candidates(working, (*osm, *overture), output)
    heights: list[float] = []
    statuses: list[HeightStatus] = []
    sources: list[str] = []
    conflicts = 0

    for position, geometry in enumerate(working.geometry):
        candidates = matched.get(position, [])
        explicit_values = [
            float(candidate.explicit_height_m)
            for candidate in candidates
            if candidate.explicit_height_m is not None
        ]
        assignment = _explicit_assignment(candidates)
        if explicit_values and assignment is None:
            conflicts += 1
            output.write(
                f"Conflicting explicit heights for building {working['id'].iloc[position]}; "
                "falling through\n"
            )
        if assignment is None:
            level_values = [
                float(candidate.levels) * LEVEL_HEIGHT_M
                for candidate in candidates
                if candidate.levels is not None
            ]
            assignment = _levels_assignment(candidates)
            if level_values and assignment is None:
                conflicts += 1
                output.write(
                    f"Conflicting level heights for building {working['id'].iloc[position]}; "
                    "using area default\n"
                )
        if assignment is None:
            height, source = area_default_height_m(geometry.area)
            assignment = height, "estimated", source
        height, status, source = assignment
        heights.append(height)
        statuses.append(status)
        sources.append(source)

    working.insert(1, "heightM", heights)
    working.insert(2, "heightStatus", statuses)
    working.insert(3, "heightSource", sources)
    result = gpd.GeoDataFrame(working, geometry="geometry", crs=buildings.crs)
    _validate_output(result)

    coverage = height_coverage(result)
    output.write(f"Building height coverage: {coverage.total_buildings}\n")
    for source, count in coverage.counts_by_source.items():
        output.write(f"{source}: {count} ({coverage.percentage(source):.3f}%)\n")
    output.write(
        f"Height candidate diagnostics: {ambiguous} ambiguous, {unmatched} unmatched, "
        f"{conflicts} target conflicts\n"
    )
    return result


def enrich_building_heights(
    buildings: gpd.GeoDataFrame,
    osm_cache_path: str | Path,
    *,
    overture_candidates: Iterable[HeightCandidate] = (),
    origin: tuple[float, float] | None = None,
    radius_m: float = CONTEXT_RADIUS_M,
    stream: TextIO | None = None,
) -> gpd.GeoDataFrame:
    """Load cached OSM evidence and return task 3.4-ready enriched buildings."""
    output = sys.stdout if stream is None else stream
    candidates = load_osm_height_candidates(
        osm_cache_path,
        origin=origin,
        radius_m=radius_m,
        stream=output,
    )
    return assign_building_heights(
        buildings,
        osm_candidates=candidates,
        overture_candidates=overture_candidates,
        stream=output,
    )
