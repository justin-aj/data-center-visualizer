"""Coordinate utilities for the EPSG:26986 site-local frame."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

MASSACHUSETTS_MAINLAND_EPSG = 26986
_DECIMETER = Decimal("0.1")


def _finite_float(value: float, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def round_local_ordinate(value: float) -> float:
    """Round one local-coordinate ordinate to the nearest 0.1 metre."""
    number = _finite_float(value, "local coordinate")
    rounded = float(Decimal(str(number)).quantize(_DECIMETER, rounding=ROUND_HALF_EVEN))
    return 0.0 if rounded == 0 else rounded


def round_local_point(x: float, y: float) -> tuple[float, float]:
    """Round both horizontal ordinates of a local point to 0.1 metre."""
    return round_local_ordinate(x), round_local_ordinate(y)


@dataclass(frozen=True, slots=True)
class LocalFrame:
    """Translation between EPSG:26986 coordinates and a site-local metric frame."""

    origin_easting: float
    origin_northing: float
    epsg: int = MASSACHUSETTS_MAINLAND_EPSG

    def __post_init__(self) -> None:
        if self.epsg != MASSACHUSETTS_MAINLAND_EPSG:
            raise ValueError(
                f"local frame requires EPSG:{MASSACHUSETTS_MAINLAND_EPSG}, got EPSG:{self.epsg}"
            )
        object.__setattr__(
            self,
            "origin_easting",
            _finite_float(self.origin_easting, "origin easting"),
        )
        object.__setattr__(
            self,
            "origin_northing",
            _finite_float(self.origin_northing, "origin northing"),
        )

    @classmethod
    def from_manifest(cls, manifest: Mapping[str, Any]) -> LocalFrame:
        """Create a local frame from a validated package manifest."""
        try:
            origin = manifest["origin"]
            return cls(
                origin_easting=origin["easting"],
                origin_northing=origin["northing"],
                epsg=origin["epsg"],
            )
        except (KeyError, TypeError) as error:
            raise ValueError("manifest origin is missing required coordinate fields") from error

    def to_local(self, easting: float, northing: float) -> tuple[float, float]:
        """Translate an EPSG:26986 point into unrounded local metres."""
        state_easting = _finite_float(easting, "easting")
        state_northing = _finite_float(northing, "northing")
        return state_easting - self.origin_easting, state_northing - self.origin_northing

    def to_state_plane(self, x: float, y: float) -> tuple[float, float]:
        """Translate an unrounded local point into EPSG:26986 metres."""
        local_x = _finite_float(x, "local x")
        local_y = _finite_float(y, "local y")
        return local_x + self.origin_easting, local_y + self.origin_northing
