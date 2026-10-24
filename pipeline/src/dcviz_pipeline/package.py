"""Assemble the versioned Lowell context-only handoff package."""

from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any, TextIO

import yaml
from shapely.geometry import Point, shape

from dcviz_pipeline.context import build_context
from dcviz_pipeline.context.buildings import (
    CONTEXT_RADIUS_M,
    INITIAL_ANCHOR_LAT,
    INITIAL_ANCHOR_LON,
    MASSACHUSETTS_MAINLAND_EPSG,
    approved_initial_origin,
)
from dcviz_pipeline.package_io import PackageDocuments, PackageError, write_package

PACKAGE_VERSION = "0.1.0"
SCHEMA_VERSION = "1.1.0"
PROJECT_ID = "lowell-markley"
PUBLICATION_DATE = "2026-10-24"

_SELECTED_SOURCES = {
    "massgis-buildings-lowell-160": {
        "date": "2026-05-22",
        "sheetOrPage": "Lowell town ID 160 archive; layer updated May 22, 2026",
    },
    "osm-building-heights-pilot": {
        "date": "2026-10-24",
        "sheetOrPage": "Overpass snapshot at OSM base timestamp 2026-10-24T21:32:51Z",
    },
    "massgis-roads-pilot": {
        "date": "2026-10-24",
        "sheetOrPage": "Bounded ArcGIS REST query snapshot; source vintages vary",
    },
    "massgis-rail-pilot": {
        "date": "2014-07-15",
        "sheetOrPage": "TRAINS_ARC; source metadata states current through July 15, 2014",
    },
    "massgis-water-polygons-pilot": {
        "date": "2026-10-24",
        "sheetOrPage": "Bounded MassDEP Hydrography ArcGIS REST query snapshot",
    },
    "massgis-open-space-pilot": {
        "date": "2026-10-24",
        "sheetOrPage": "Bounded Lowell town ID 160 ArcGIS REST query snapshot",
    },
}

_PROJ4 = (
    "+proj=lcc +lat_0=41 +lon_0=-71.5 +lat_1=41.7166666666667 "
    "+lat_2=42.6833333333333 +x_0=200000 +y_0=750000 +datum=NAD83 "
    "+units=m +no_defs"
)


class ContextPackageError(ValueError):
    """The context-only package cannot be assembled truthfully or safely."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContextPackageError(f"could not read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContextPackageError(f"{path} must contain a JSON object")
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ContextPackageError(f"could not read YAML {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContextPackageError(f"{path} must contain a mapping")
    return value


def _source_references(root: Path) -> list[dict[str, Any]]:
    manifest = _read_yaml(root / "data/sources.yaml")
    source_entries = manifest.get("sources")
    if not isinstance(source_entries, list):
        raise ContextPackageError("data/sources.yaml must contain a sources list")
    sources_by_id = {
        entry.get("id"): entry
        for entry in source_entries
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    }

    fetch_log = _read_json(root / "data/raw/fetch-log.json")
    fetch_entries = fetch_log.get("sources")
    if not isinstance(fetch_entries, list):
        raise ContextPackageError("fetch-log.json must contain a sources list")
    fetch_by_id = {
        entry.get("id"): entry
        for entry in fetch_entries
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    }

    references: list[dict[str, Any]] = []
    for source_id, details in _SELECTED_SOURCES.items():
        source = sources_by_id.get(source_id)
        fetched = fetch_by_id.get(source_id)
        if not isinstance(source, Mapping):
            raise ContextPackageError(f"source manifest is missing {source_id}")
        if not isinstance(fetched, Mapping) or fetched.get("outcome") not in {
            "downloaded",
            "cached",
        }:
            raise ContextPackageError(f"successful fetch metadata is missing for {source_id}")
        if source.get("status") != "verified":
            raise ContextPackageError(f"selected publication source is unverified: {source_id}")
        if source.get("distributable") is not True:
            raise ContextPackageError(
                f"selected publication source is not distributable: {source_id}"
            )

        retrieved = fetched.get("retrievedAt")
        if not isinstance(retrieved, str) or len(retrieved) < 10:
            raise ContextPackageError(f"retrieval date is missing for {source_id}")
        references.append(
            {
                "id": source_id,
                "title": str(source["title"]),
                "issuer": str(source["issuer"]),
                "date": details["date"],
                "sheetOrPage": details["sheetOrPage"],
                "url": str(source["url"]),
                "retrievedAt": retrieved[:10],
                "license": str(source["license"]),
                "distributable": True,
            }
        )
    return references


def _viewpoints(
    root: Path, context: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = root / "pipeline/curation/lowell-markley/viewpoints.yaml"
    curation = _read_yaml(path)
    viewpoints = curation.get("viewpoints")
    review = curation.get("review")
    if not isinstance(viewpoints, list) or not isinstance(review, Mapping):
        raise ContextPackageError("viewpoints curation must contain viewpoints and review")

    public_spaces = [
        shape(feature["geometry"])
        for feature in context.get("openSpace", [])
        if isinstance(feature, Mapping) and feature.get("publicAccess") is True
    ]
    buildings = [
        shape(feature["geometry"])
        for feature in context.get("buildings", [])
        if isinstance(feature, Mapping)
    ]
    output: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    ground_count = 0
    aerial_count = 0

    for index, value in enumerate(viewpoints):
        if not isinstance(value, Mapping):
            raise ContextPackageError(f"viewpoints[{index}] must be a mapping")
        identifier = value.get("id")
        label = value.get("label")
        kind = value.get("kind")
        position = value.get("position")
        target = value.get("target")
        public_access = value.get("publicAccess")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ContextPackageError(f"viewpoints[{index}] has an invalid or duplicate id")
        identifiers.add(identifier)
        if not isinstance(label, str) or not label:
            raise ContextPackageError(f"viewpoints[{index}] has an invalid label")
        if kind not in {"aerial", "ground"}:
            raise ContextPackageError(f"viewpoints[{index}] has an invalid kind")
        if (
            not isinstance(position, list)
            or not isinstance(target, list)
            or len(position) != 3
            or len(target) != 3
            or any(
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(float(number))
                for number in [*position, *target]
            )
        ):
            raise ContextPackageError(f"viewpoints[{index}] positions must be finite 3D values")
        if not isinstance(public_access, bool):
            raise ContextPackageError(f"viewpoints[{index}].publicAccess must be boolean")

        if kind == "ground":
            ground_count += 1
            point = Point(float(position[0]), float(position[1]))
            if math.hypot(point.x, point.y) > CONTEXT_RADIUS_M:
                raise ContextPackageError(f"ground viewpoint {identifier} lies outside the radius")
            if not any(space.covers(point) for space in public_spaces):
                raise ContextPackageError(
                    f"ground viewpoint {identifier} is not in public open space"
                )
            if any(building.covers(point) for building in buildings):
                raise ContextPackageError(f"ground viewpoint {identifier} lies in a building")
            if public_access is not True:
                raise ContextPackageError(f"ground viewpoint {identifier} must be public")
        else:
            aerial_count += 1
            if public_access is not False:
                raise ContextPackageError(f"aerial viewpoint {identifier} must not claim access")

        output.append(
            {
                "id": identifier,
                "label": label,
                "kind": kind,
                "position": [float(number) for number in position],
                "target": [float(number) for number in target],
                "publicAccess": public_access,
            }
        )

    if ground_count < 3 or aerial_count < 1:
        raise ContextPackageError("viewpoints require one aerial and at least three ground views")
    return output, dict(review)


def _manifest(
    root: Path,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    easting, northing = approved_initial_origin()
    viewpoints, review = _viewpoints(root, context)
    reviewer = review.get("reviewer")
    review_date_value = review.get("date")
    review_date = (
        review_date_value.isoformat()
        if isinstance(review_date_value, date)
        else review_date_value
    )
    review_result = review.get("result")
    if not all(
        isinstance(value, str) and value for value in (reviewer, review_date, review_result)
    ):
        raise ContextPackageError("viewpoint review metadata is incomplete")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "packageKind": "context-only",
        "projectId": PROJECT_ID,
        "packageVersion": PACKAGE_VERSION,
        "title": "Lowell Markley Area Context",
        "siteAddress": "2 Prince Avenue / 1 Markley Way, Lowell, Massachusetts",
        "baselineDate": PUBLICATION_DATE,
        "proposalDate": "2024-08-09",
        "verifiedAt": PUBLICATION_DATE,
        "proposalVersionLabel": (
            "Context-only neighborhood package; August 9, 2024 proposal geometry "
            "and georeference are not included"
        ),
        "origin": {
            "lon": INITIAL_ANCHOR_LON,
            "lat": INITIAL_ANCHOR_LAT,
            "epsg": MASSACHUSETTS_MAINLAND_EPSG,
            "easting": easting,
            "northing": northing,
            "proj4": _PROJ4,
        },
        "datum": {
            "kind": "flat",
            "siteGradeNavd88M": None,
            "note": (
                "Ground is shown as a flat visualization plane; terrain and site grade "
                "are unknown."
            ),
        },
        "contextRadiusM": CONTEXT_RADIUS_M,
        "sources": _source_references(root),
        "claims": [
            {
                "id": "context-building-height-estimates",
                "kind": "estimate",
                "text": (
                    "Context building heights use sparse OpenStreetMap level counts and "
                    "documented footprint-area visual-massing defaults; none are official heights."
                ),
                "sourceRefs": [
                    "massgis-buildings-lowell-160",
                    "osm-building-heights-pilot",
                ],
            },
            {
                "id": "context-line-width-estimates",
                "kind": "estimate",
                "text": (
                    "Road and railway widths are visualization conventions, not surveyed or "
                    "official physical widths."
                ),
                "sourceRefs": ["massgis-roads-pilot", "massgis-rail-pilot"],
            },
        ],
        "viewpoints": viewpoints,
        "publicViewingAreas": ["roads", "openSpace"],
        "reviewIssues": [
            {
                "id": "context-only-no-proposal-georeference",
                "severity": "information",
                "description": (
                    "This package contains neighborhood context only. It contains no proposal "
                    "features or proposal-plan georeference."
                ),
                "featureIds": [],
            },
            {
                "id": "context-mixed-source-vintages",
                "severity": "limitation",
                "description": (
                    "Context layers have different source vintages. The baseline date records "
                    "package verification, not a claim that every feature was observed that day."
                ),
                "featureIds": [],
            },
        ],
        "review": {
            "reviewer": reviewer,
            "date": review_date,
            "result": review_result,
            "checklistRef": "data/sources.yaml and pipeline/docs/height-sources.md",
        },
        "attribution": [
            (
                "Bureau of Geographic Information (MassGIS), Commonwealth of Massachusetts, "
                "Executive Office of Technology Services and Security"
            ),
            "Road data: Massachusetts Department of Transportation and MassGIS",
            "Rail data: Central Transportation Planning Staff and MassGIS",
            "Hydrography: USGS, MassDEP, and MassGIS",
            (
                "Open space: Massachusetts Executive Office of Energy and Environmental "
                "Affairs and MassGIS"
            ),
            (
                "© OpenStreetMap contributors; Open Database License 1.0: "
                "https://www.openstreetmap.org/copyright"
            ),
        ],
        "excludedFields": [
            "owner",
            "ownership",
            "own_name",
            "owner_address",
            "assessor",
            "site_address",
            "abutter",
            "phone",
            "email",
        ],
    }


def build_context_package(
    repo_root: Path | None = None,
    stream: TextIO | None = None,
) -> Path:
    """Build and publish the immutable Lowell 0.1.0 context-only package."""
    root = (repo_root or _repo_root()).resolve()
    output = stream or sys.stdout
    destination = root / "data/published" / PROJECT_ID / PACKAGE_VERSION
    if destination.exists():
        raise ContextPackageError(f"package version already exists: {destination}")

    context_path = build_context(repo_root=root, stream=output)
    context = _read_json(context_path)
    documents = PackageDocuments(
        manifest=_manifest(root, context),
        proposal={"features": []},
        context=context,
    )
    write_package(destination, documents, root / "contracts")
    print(f"Published context-only package: {destination}", file=output)
    return destination


def run_package() -> int:
    """Build the context-only package and return a CLI-style status code."""
    try:
        build_context_package()
    except (ContextPackageError, PackageError, OSError, ValueError) as error:
        print(f"ERROR package: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_package())
