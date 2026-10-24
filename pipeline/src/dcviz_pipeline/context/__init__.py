"""Assemble and write the schema-validated Lowell context scene."""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, TextIO

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError
from shapely.errors import ShapelyError
from shapely.geometry import LineString, Polygon

from dcviz_pipeline.context.buildings import (
    CONTEXT_RADIUS_M,
    BuildingDataError,
    approved_initial_origin,
    load_massgis_buildings,
)
from dcviz_pipeline.context.heights import HeightDataError, enrich_building_heights
from dcviz_pipeline.context.layers import LayerDataError, assemble_context_layers
from dcviz_pipeline.frame import LocalFrame, round_local_point

CONTEXT_SIZE_TARGET_BYTES = 6_000_000

_BUILDINGS_PATH = Path("data/raw/massgis-buildings-lowell-160.zip")
_OSM_HEIGHTS_PATH = Path("data/raw/osm-building-heights-pilot.json")
_ROADS_PATH = Path("data/raw/massgis-roads-pilot.json")
_RAILWAYS_PATH = Path("data/raw/massgis-rail-pilot.json")
_WATER_POLYGONS_PATH = Path("data/raw/massgis-water-polygons-pilot.json")
_WATER_LINES_PATH = Path("data/raw/massgis-water-lines-pilot.json")
_OPEN_SPACE_PATH = Path("data/raw/massgis-open-space-pilot.json")
_CONTEXT_SCHEMA_PATH = Path("contracts/context-scene.schema.json")
_CONTEXT_OUTPUT_PATH = Path("pipeline/build/context.json")

JsonObject = dict[str, Any]
Position = tuple[float, float]


class ContextBuildError(ValueError):
    """Context assembly, serialization, or validation failed."""


class ContextValidationError(ContextBuildError):
    """The serialized context document violates the context schema."""

    def __init__(self, issues: Sequence[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("schema validation failed:\n" + "\n".join(self.issues))


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _native_scalar(value: object) -> object:
    """Convert pandas/NumPy scalar wrappers without accepting arbitrary objects."""
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except (TypeError, ValueError):
            return value
    return value


def _native_string(value: object, label: str) -> str:
    normalized = _native_scalar(value)
    if not isinstance(normalized, str) or not normalized.strip():
        raise ContextBuildError(f"{label} must be a non-empty string")
    return str(normalized)


def _native_float(value: object, label: str) -> float:
    normalized = _native_scalar(value)
    if isinstance(normalized, bool):
        raise ContextBuildError(f"{label} must be a finite number")
    try:
        number = float(normalized)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise ContextBuildError(f"{label} must be a finite number") from error
    if not math.isfinite(number):
        raise ContextBuildError(f"{label} must be a finite number")
    return number


def _native_bool(value: object, label: str) -> bool:
    normalized = _native_scalar(value)
    if not isinstance(normalized, bool):
        raise ContextBuildError(f"{label} must be a boolean")
    return bool(normalized)


def _round_inside_radius(
    frame: LocalFrame,
    easting: float,
    northing: float,
    *,
    label: str,
) -> Position:
    """Round locally, moving boundary points to the nearest in-radius grid point."""
    local_x, local_y = frame.to_local(easting, northing)
    source_radius = math.hypot(local_x, local_y)
    if source_radius > CONTEXT_RADIUS_M + 1e-6:
        raise ContextBuildError(f"{label} lies outside the {CONTEXT_RADIUS_M:g} m context radius")

    rounded_x, rounded_y = round_local_point(local_x, local_y)
    if math.hypot(rounded_x, rounded_y) <= CONTEXT_RADIUS_M:
        return rounded_x, rounded_y

    center_x = int(round(rounded_x * 10.0))
    center_y = int(round(rounded_y * 10.0))
    candidates: list[tuple[float, int, int]] = []
    for grid_x in range(center_x - 1, center_x + 2):
        for grid_y in range(center_y - 1, center_y + 2):
            candidate_x = grid_x / 10.0
            candidate_y = grid_y / 10.0
            if math.hypot(candidate_x, candidate_y) <= CONTEXT_RADIUS_M:
                displacement = (candidate_x - local_x) ** 2 + (candidate_y - local_y) ** 2
                candidates.append((displacement, grid_x, grid_y))
    if not candidates:
        raise ContextBuildError(f"{label} cannot be rounded inside the context radius")

    _, grid_x, grid_y = min(candidates)
    selected_x = grid_x / 10.0
    selected_y = grid_y / 10.0
    return (0.0 if selected_x == 0 else selected_x, 0.0 if selected_y == 0 else selected_y)


def _rounded_positions(
    coordinates: Iterable[Sequence[float]],
    frame: LocalFrame,
    *,
    label: str,
) -> list[Position]:
    positions: list[Position] = []
    for index, coordinate in enumerate(coordinates):
        if len(coordinate) < 2:
            raise ContextBuildError(f"{label} coordinate {index} has no x/y pair")
        position = _round_inside_radius(
            frame,
            coordinate[0],
            coordinate[1],
            label=f"{label} coordinate {index}",
        )
        if not positions or position != positions[-1]:
            positions.append(position)
    return positions


def _line_geometry(geometry: object, frame: LocalFrame, label: str) -> JsonObject:
    if not isinstance(geometry, LineString):
        raise ContextBuildError(f"{label} geometry must be a LineString")
    positions = _rounded_positions(geometry.coords, frame, label=label)
    if len(set(positions)) < 2:
        raise ContextBuildError(f"{label} has fewer than two distinct rounded positions")
    try:
        reconstructed = LineString(positions)
    except ShapelyError as error:
        raise ContextBuildError(f"{label} rounded geometry could not be reconstructed") from error
    if reconstructed.is_empty or not reconstructed.is_valid or reconstructed.length <= 0:
        raise ContextBuildError(f"{label} rounded geometry is empty, invalid, or zero-length")
    return {"type": "LineString", "coordinates": [list(position) for position in positions]}


def _rounded_ring(
    coordinates: Iterable[Sequence[float]],
    frame: LocalFrame,
    *,
    label: str,
) -> list[Position]:
    positions = _rounded_positions(coordinates, frame, label=label)
    if positions and positions[0] != positions[-1]:
        positions.append(positions[0])
    if len(set(positions[:-1])) < 3:
        raise ContextBuildError(f"{label} has fewer than three distinct rounded vertices")
    if len(positions) < 4 or positions[0] != positions[-1]:
        raise ContextBuildError(f"{label} is not a closed rounded ring")
    return positions


def _polygon_geometry(geometry: object, frame: LocalFrame, label: str) -> JsonObject:
    if not isinstance(geometry, Polygon):
        raise ContextBuildError(f"{label} geometry must be a Polygon")
    exterior = _rounded_ring(geometry.exterior.coords, frame, label=f"{label} exterior")
    holes = [
        _rounded_ring(ring.coords, frame, label=f"{label} hole {index}")
        for index, ring in enumerate(geometry.interiors)
    ]
    try:
        reconstructed = Polygon(exterior, holes)
    except ShapelyError as error:
        raise ContextBuildError(f"{label} rounded geometry could not be reconstructed") from error
    if reconstructed.is_empty or not reconstructed.is_valid or reconstructed.area <= 0:
        raise ContextBuildError(f"{label} rounded geometry is empty, invalid, or zero-area")
    rings = [exterior, *holes]
    return {
        "type": "Polygon",
        "coordinates": [[list(position) for position in ring] for ring in rings],
    }


def _serialize_buildings(buildings: Any, frame: LocalFrame) -> list[JsonObject]:
    records: list[JsonObject] = []
    for index in range(len(buildings)):
        label = f"building[{index}]"
        records.append(
            {
                "id": _native_string(buildings["id"].iloc[index], f"{label}.id"),
                "geometry": _polygon_geometry(buildings.geometry.iloc[index], frame, label),
                "baseElevationM": 0.0,
                "heightM": _native_float(buildings["heightM"].iloc[index], f"{label}.heightM"),
                "heightStatus": _native_string(
                    buildings["heightStatus"].iloc[index], f"{label}.heightStatus"
                ),
                "heightSource": _native_string(
                    buildings["heightSource"].iloc[index], f"{label}.heightSource"
                ),
            }
        )
    return records


def _serialize_roads(roads: Any, frame: LocalFrame) -> list[JsonObject]:
    records: list[JsonObject] = []
    for index in range(len(roads)):
        label = f"road[{index}]"
        records.append(
            {
                "geometry": _line_geometry(roads.geometry.iloc[index], frame, label),
                "class": _native_string(roads["class"].iloc[index], f"{label}.class"),
                "widthM": _native_float(roads["widthM"].iloc[index], f"{label}.widthM"),
            }
        )
    return records


def _serialize_railways(railways: Any, frame: LocalFrame) -> list[JsonObject]:
    records: list[JsonObject] = []
    for index in range(len(railways)):
        label = f"railway[{index}]"
        records.append(
            {
                "geometry": _line_geometry(railways.geometry.iloc[index], frame, label),
                "widthM": _native_float(railways["widthM"].iloc[index], f"{label}.widthM"),
            }
        )
    return records


def _serialize_water(water: Any, frame: LocalFrame) -> list[JsonObject]:
    records: list[JsonObject] = []
    for index in range(len(water)):
        label = f"water[{index}]"
        record: JsonObject = {
            "geometry": _polygon_geometry(water.geometry.iloc[index], frame, label)
        }
        name = _native_scalar(water["name"].iloc[index])
        if name is not None:
            record["name"] = _native_string(name, f"{label}.name")
        records.append(record)
    return records


def _serialize_open_space(open_space: Any, frame: LocalFrame) -> list[JsonObject]:
    records: list[JsonObject] = []
    for index in range(len(open_space)):
        label = f"openSpace[{index}]"
        records.append(
            {
                "geometry": _polygon_geometry(open_space.geometry.iloc[index], frame, label),
                "kind": _native_string(open_space["kind"].iloc[index], f"{label}.kind"),
                "publicAccess": _native_bool(
                    open_space["publicAccess"].iloc[index], f"{label}.publicAccess"
                ),
            }
        )
    return records


def _load_validator(schema_path: Path) -> Draft202012Validator:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ContextBuildError(f"could not read context schema {schema_path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ContextBuildError(
            f"invalid JSON in context schema {schema_path} at line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(schema, dict):
        raise ContextBuildError(f"context schema {schema_path} must contain a JSON object")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ContextBuildError(f"invalid context schema: {error.message}") from error
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _json_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _serialize_and_validate(document: JsonObject, schema_path: Path) -> bytes:
    try:
        text = (
            json.dumps(
                document,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            + "\n"
        )
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ContextBuildError(f"could not serialize context JSON: {error}") from error

    validator = _load_validator(schema_path)
    errors = sorted(
        validator.iter_errors(parsed),
        key=lambda error: (_json_path(error), error.message),
    )
    if errors:
        raise ContextValidationError([f"{_json_path(error)}: {error.message}" for error in errors])
    return text.encode("utf-8")


def _write_atomic(output_path: Path, payload: bytes) -> None:
    part_path = output_path.with_name(f"{output_path.name}.part")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.write_bytes(payload)
        part_path.replace(output_path)
    except OSError:
        try:
            part_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def build_context(
    repo_root: Path | None = None,
    stream: TextIO | None = None,
) -> Path:
    """Build, validate, and atomically write the Lowell flat-datum context scene."""
    root = (repo_root or _default_repo_root()).resolve()
    output = stream or sys.stdout
    origin = approved_initial_origin()
    frame = LocalFrame(*origin)

    buildings = load_massgis_buildings(root / _BUILDINGS_PATH, origin=origin, stream=output)
    buildings = enrich_building_heights(
        buildings,
        root / _OSM_HEIGHTS_PATH,
        origin=origin,
        stream=output,
    )
    layers = assemble_context_layers(
        roads_path=root / _ROADS_PATH,
        railways_path=root / _RAILWAYS_PATH,
        water_polygons_path=root / _WATER_POLYGONS_PATH,
        water_lines_path=root / _WATER_LINES_PATH,
        open_space_path=root / _OPEN_SPACE_PATH,
        origin=origin,
        require_landmarks=True,
        stream=output,
    )

    required_layers = {
        "buildings": buildings,
        "roads": layers.roads,
        "railways": layers.railways,
        "water": layers.water,
        "openSpace": layers.open_space,
    }
    empty_layers = [name for name, layer in required_layers.items() if layer.empty]
    if empty_layers:
        raise ContextBuildError(f"required output layers are empty: {', '.join(empty_layers)}")

    document: JsonObject = {
        "ground": {"elevationM": None},
        "buildings": _serialize_buildings(buildings, frame),
        "roads": _serialize_roads(layers.roads, frame),
        "railways": _serialize_railways(layers.railways, frame),
        "water": _serialize_water(layers.water, frame),
        "openSpace": _serialize_open_space(layers.open_space, frame),
    }
    payload = _serialize_and_validate(document, root / _CONTEXT_SCHEMA_PATH)
    output_path = root / _CONTEXT_OUTPUT_PATH
    _write_atomic(output_path, payload)

    size_bytes = len(payload)
    size_mb = size_bytes / 1_000_000
    under_target = size_bytes < CONTEXT_SIZE_TARGET_BYTES
    print(f"Context output: {output_path}", file=output)
    print(
        f"Context size: {size_bytes} bytes ({size_mb:.6f} MB); "
        f"under 6,000,000-byte target: {'yes' if under_target else 'no'}",
        file=output,
    )
    if not under_target:
        print("WARNING context output exceeds the 6 MB size target", file=output)
    return output_path


def run_context(
    repo_root: Path | None = None,
    stream: TextIO | None = None,
) -> int:
    """Run context generation and convert expected failures into a CLI status."""
    output = stream or sys.stdout
    try:
        build_context(repo_root=repo_root, stream=output)
    except (
        ContextBuildError,
        BuildingDataError,
        HeightDataError,
        LayerDataError,
        OSError,
        SchemaError,
        ShapelyError,
        UnicodeError,
    ) as error:
        print(f"ERROR context: {error}", file=output)
        return 1
    return 0


__all__ = [
    "CONTEXT_SIZE_TARGET_BYTES",
    "ContextBuildError",
    "ContextValidationError",
    "build_context",
    "run_context",
]
