"""Off-the-shelf metal hardware: heat-set inserts, socket-head bolts, hex nuts, bearings.

Rule: plastic carries shape, metal carries clamp force. Every item carries a `source`.
ISO values are nominal dimensions from the cited standard. Heat-set inserts are
brand-specific and flagged `verified=False` until checked against your insert's
datasheet (Phase 1's coupon measures the real pocket fit).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from bikeparts.core.tolerances import PRINTER

Thread = Literal["M3", "M4", "M5"]

# source: docs/PLAN.md structural rule 3 (≥ 2.4 mm wall around an insert)
MIN_INSERT_WALL = 2.4


class HeatSetInsert(BaseModel):
    model_config = ConfigDict(frozen=True)

    thread: Thread
    hole_diameter: float  # recommended pocket diameter
    length: float
    source: str
    verified: bool = False

    @property
    def pocket_diameter(self) -> float:
        return self.hole_diameter + 2 * PRINTER.insert_pocket_extra

    @property
    def pocket_depth(self) -> float:
        # source: assumption — 1.0 mm extra depth so displaced plastic and the insert tip
        # don't bottom out; confirm on the Phase 1 coupon.
        return self.length + 1.0

    @property
    def boss_diameter(self) -> float:
        """Minimum boss OD that keeps the rule-3 wall around the pocket."""
        return self.pocket_diameter + 2 * MIN_INSERT_WALL


class SocketHeadBolt(BaseModel):
    model_config = ConfigDict(frozen=True)

    thread: Thread
    nominal: float
    head_diameter: float
    head_height: float
    hex_key: float
    clearance_hole: float  # ISO 273 medium series
    source: str
    verified: bool = True

    @property
    def clearance_diameter(self) -> float:
        return self.clearance_hole + 2 * PRINTER.bolt_hole_extra

    @property
    def counterbore_diameter(self) -> float:
        # source: assumption — 0.5 mm per side so the head drops in without a fight
        return self.head_diameter + 1.0


class HexNut(BaseModel):
    model_config = ConfigDict(frozen=True)

    thread: Thread
    across_flats: float
    thickness: float
    source: str
    verified: bool = True

    @property
    def pocket_flats(self) -> float:
        return self.across_flats + PRINTER.nut_pocket_flats

    @property
    def pocket_corners(self) -> float:
        """Across-corners of the pocket hexagon (flats / cos 30°)."""
        return self.pocket_flats / 0.8660254037844386


class Bearing(BaseModel):
    model_config = ConfigDict(frozen=True)

    designation: str
    bore: float
    outer_diameter: float
    width: float
    source: str
    verified: bool = True


_RUTHEX = (
    "Ruthex RX-{t} recommended hole diameter (manufacturer table, from memory) — "
    "UNVERIFIED: check your insert's datasheet; Phase 1 coupon calibrates"
)

INSERTS: dict[Thread, HeatSetInsert] = {
    "M3": HeatSetInsert(
        thread="M3", hole_diameter=4.0, length=5.7, source=_RUTHEX.format(t="M3x5.7")
    ),
    "M4": HeatSetInsert(
        thread="M4", hole_diameter=5.6, length=8.1, source=_RUTHEX.format(t="M4x8.1")
    ),
    "M5": HeatSetInsert(
        thread="M5", hole_diameter=6.4, length=9.5, source=_RUTHEX.format(t="M5x9.5")
    ),
}

_ISO4762 = "ISO 4762 socket head cap screw, max head dims; clearance hole ISO 273 medium"

BOLTS: dict[Thread, SocketHeadBolt] = {
    "M3": SocketHeadBolt(
        thread="M3",
        nominal=3.0,
        head_diameter=5.5,
        head_height=3.0,
        hex_key=2.5,
        clearance_hole=3.4,
        source=_ISO4762,
    ),
    "M4": SocketHeadBolt(
        thread="M4",
        nominal=4.0,
        head_diameter=7.0,
        head_height=4.0,
        hex_key=3.0,
        clearance_hole=4.5,
        source=_ISO4762,
    ),
    "M5": SocketHeadBolt(
        thread="M5",
        nominal=5.0,
        head_diameter=8.5,
        head_height=5.0,
        hex_key=4.0,
        clearance_hole=5.5,
        source=_ISO4762,
    ),
}

_ISO4032 = "ISO 4032 hex nut style 1, s nominal and m max"

NUTS: dict[Thread, HexNut] = {
    "M3": HexNut(thread="M3", across_flats=5.5, thickness=2.4, source=_ISO4032),
    "M4": HexNut(thread="M4", across_flats=7.0, thickness=3.2, source=_ISO4032),
    "M5": HexNut(thread="M5", across_flats=8.0, thickness=4.7, source=_ISO4032),
}

BEARING_608 = Bearing(
    designation="608",
    bore=8.0,
    outer_diameter=22.0,
    width=7.0,
    source="ISO 15 deep-groove ball bearing, series 60, bore code 8 (8×22×7)",
)


# ISO 4762 preferred nominal lengths for M3–M5 socket head cap screws.
# source: ISO 4762 length series (preferred lengths, mm)
BOLT_LENGTHS: tuple[float, ...] = (6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50)


def next_bolt_length(needed: float) -> float:
    """Shortest ISO 4762 preferred length ≥ `needed`."""
    for length in BOLT_LENGTHS:
        if length >= needed - 1e-9:
            return float(length)
    raise ValueError(f"no standard bolt length ≥ {needed:.1f} mm")


class Washer(BaseModel):
    model_config = ConfigDict(frozen=True)

    thread: Thread
    outer_diameter: float
    thickness: float
    source: str
    verified: bool = True


WASHERS: dict[Thread, Washer] = {
    "M5": Washer(
        thread="M5",
        outer_diameter=10.0,
        thickness=1.0,
        source="ISO 7089 (DIN 125-A) plain washer M5: Ø10 × 1 mm",
    ),
}
