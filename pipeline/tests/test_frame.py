"""Coordinate property tests and package I/O examples."""

from __future__ import annotations

import copy
import math
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dcviz_pipeline.frame import LocalFrame, round_local_ordinate, round_local_point
from dcviz_pipeline.package_io import (
    PackageDocuments,
    PackageError,
    PackageValidationError,
    read_package,
    write_package,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"
FIXTURE_DIR = CONTRACTS_DIR / "fixtures/synthetic-site"
finite_coordinate = st.floats(
    min_value=-2_000_000,
    max_value=2_000_000,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)


@given(
    origin_easting=finite_coordinate,
    origin_northing=finite_coordinate,
    easting=finite_coordinate,
    northing=finite_coordinate,
)
def test_state_plane_local_round_trip_within_one_millimetre(
    origin_easting: float,
    origin_northing: float,
    easting: float,
    northing: float,
) -> None:
    frame = LocalFrame(origin_easting, origin_northing)

    local = frame.to_local(easting, northing)
    recovered = frame.to_state_plane(*local)

    assert math.dist(recovered, (easting, northing)) <= 0.001


@given(
    origin_easting=finite_coordinate,
    origin_northing=finite_coordinate,
    x=finite_coordinate,
    y=finite_coordinate,
)
def test_local_state_plane_round_trip_within_one_millimetre(
    origin_easting: float,
    origin_northing: float,
    x: float,
    y: float,
) -> None:
    frame = LocalFrame(origin_easting, origin_northing)

    state_plane = frame.to_state_plane(x, y)
    recovered = frame.to_local(*state_plane)

    assert math.dist(recovered, (x, y)) <= 0.001


@given(x=finite_coordinate, y=finite_coordinate)
def test_decimetre_rounding_moves_each_ordinate_no_more_than_five_centimetres(
    x: float,
    y: float,
) -> None:
    rounded_x, rounded_y = round_local_point(x, y)

    assert abs(rounded_x - x) <= 0.05 + 1e-10
    assert abs(rounded_y - y) <= 0.05 + 1e-10
    assert round_local_ordinate(rounded_x) == rounded_x
    assert round_local_ordinate(rounded_y) == rounded_y


def test_frame_uses_manifest_origin() -> None:
    package = read_package(FIXTURE_DIR, CONTRACTS_DIR)
    frame = LocalFrame.from_manifest(package.manifest)

    assert frame.to_local(frame.origin_easting, frame.origin_northing) == (0.0, 0.0)
    assert frame.epsg == 26986


def test_package_read_write_round_trip(tmp_path: Path) -> None:
    package = read_package(FIXTURE_DIR, CONTRACTS_DIR)
    destination = tmp_path / "synthetic-civic-site" / "1.0.0"

    write_package(destination, package, CONTRACTS_DIR)
    recovered = read_package(destination, CONTRACTS_DIR)

    assert recovered == package
    assert set(path.name for path in destination.iterdir()) == {
        "manifest.json",
        "proposal.json",
        "context.json",
    }
    with pytest.raises(PackageError, match="already exists"):
        write_package(destination, package, CONTRACTS_DIR)


def test_invalid_package_is_rejected_before_writing(tmp_path: Path) -> None:
    package = read_package(FIXTURE_DIR, CONTRACTS_DIR)
    invalid_manifest = copy.deepcopy(package.manifest)
    del invalid_manifest["projectId"]
    invalid_package = PackageDocuments(
        manifest=invalid_manifest,
        proposal=package.proposal,
        context=package.context,
    )
    destination = tmp_path / "invalid-package"

    with pytest.raises(PackageValidationError) as caught:
        write_package(destination, invalid_package, CONTRACTS_DIR)

    assert "manifest.json at $" in str(caught.value)
    assert "'projectId' is a required property" in str(caught.value)
    assert not destination.exists()
