"""Known-good and known-bad test bodies that prove each check catches what it should.

Not parts: never released. `uv run check --fixture <name>` checks one;
`uv run check --self-test` checks all and compares against `expect_fail`.
All fixtures are print-oriented on Z = 0 like real parts.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import build123d as bd

from bikeparts.core import features as f
from bikeparts.core.features import as_part

_MIN = (bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)


def _cube(size: float = 20.0) -> bd.Part:
    return as_part(bd.Box(size, size, size, align=_MIN))


def overhang_cube(angle_deg: float) -> bd.Part:
    """20 mm cube with a 10 mm ledge on +X whose underside is `angle_deg` from vertical.

    The ledge ends in a 3 mm vertical face so the only defect is the sloped underside.
    Underside area = slant length × 20 mm, e.g. 60° → √(10² + 5.774²) × 20 ≈ 230.9 mm².
    """
    reach, end_t, s = 10.0, 3.0, 20.0
    z_end = s - end_t
    z_root = z_end - reach / math.tan(math.radians(angle_deg))
    ledge = bd.Polygon((s, z_root), (s + reach, z_end), (s + reach, s), (s, s), align=None)
    body = _cube(s) + bd.Pos(0, s, 0) * bd.extrude(bd.Plane.XZ * ledge, amount=s)
    return f.bed_chamfer(body)


def hole_block(teardrop: bool, d: float = 6.0) -> bd.Part:
    tool = f.teardrop_hole(d, 30) if teardrop else bd.Cylinder(d / 2, 30, rotation=(90, 0, 0))
    return f.bed_chamfer(_cube() - bd.Pos(10, 10, 10) * tool)


def small_round_hole_block() -> bd.Part:
    """Ø3 round horizontal hole: allowed by rule 2, must pass both overhang and holes."""
    return f.bed_chamfer(_cube() - bd.Pos(10, 10, 10) * f.horizontal_hole(3.0, 30))


def thin_wall_cup(wall: float = 0.8) -> bd.Part:
    outer = bd.Box(30, 30, 15, align=_MIN)
    inner = bd.Pos(wall, wall, 2.0) * bd.Box(30 - 2 * wall, 30 - 2 * wall, 20, align=_MIN)
    return f.bed_chamfer(outer - inner)


def oversize_bar() -> bd.Part:
    return f.bed_chamfer(bd.Box(230, 20, 10, align=_MIN))


def floating_cube() -> bd.Part:
    return as_part(bd.Pos(0, 0, 1.0) * _cube())


def two_bodies() -> bd.Part:
    """Two separate cubes exported as one body — must be split into separate bodies."""
    return as_part(_cube(10) + bd.Pos(20, 0, 0) * _cube(10))


def boss_plate() -> bd.Part:
    """Plate with an M4 insert boss, a captive M4 nut pocket and a triangular rib."""
    t = 6.0
    plate = bd.Box(60, 30, t, align=_MIN)
    boss = bd.Pos(12, 15, 0) * f.insert_boss("M4", 14)
    rib = bd.Pos(16, 15, t) * f.rib(25, 8, 1.6)  # tall end buried in the boss wall
    nut = bd.Pos(52, 15, t - 3.4) * f.captive_nut_pocket("M4")  # opens on the top face
    pocket = bd.Pos(12, 15, 14) * f.insert_pocket("M4")  # merging refilled the boss's pocket
    return f.bed_chamfer(plate + boss + rib - nut - pocket)


@dataclass(frozen=True)
class Fixture:
    build: Callable[[], dict[str, bd.Part]]
    expect_fail: frozenset[str]
    note: str


def _one(fn: Callable[[], bd.Part]) -> Callable[[], dict[str, bd.Part]]:
    return lambda: {"body": fn()}


def _clamp() -> dict[str, bd.Part]:
    c = f.split_clamp(31.8 + 0.5, 24)
    return {"bolt_half": c.bolt_half, "insert_half": c.insert_half}


FIXTURES: dict[str, Fixture] = {
    "overhang_cube_60": Fixture(
        _one(lambda: overhang_cube(60)),
        frozenset({"overhang"}),
        "20 mm cube with a deliberate 60° overhang ledge (~230.9 mm² underside)",
    ),
    "overhang_cube_45": Fixture(
        _one(lambda: overhang_cube(45)), frozenset(), "same ledge at exactly 45° — the limit"
    ),
    "round_hole_6": Fixture(
        _one(lambda: hole_block(False)),
        frozenset({"hole_orientation", "overhang"}),
        "Ø6 round horizontal hole — needs a teardrop",
    ),
    "teardrop_hole_6": Fixture(
        _one(lambda: hole_block(True)), frozenset(), "Ø6 teardrop horizontal hole"
    ),
    "round_hole_3": Fixture(
        _one(small_round_hole_block), frozenset(), "Ø3 round horizontal hole — allowed"
    ),
    "thin_wall_cup": Fixture(
        _one(thin_wall_cup), frozenset({"min_wall"}), "open cup with 0.8 mm walls"
    ),
    "oversize_bar": Fixture(_one(oversize_bar), frozenset({"bed_fit"}), "230 mm long bar"),
    "floating_cube": Fixture(
        _one(floating_cube),
        frozenset({"bed_fit", "overhang"}),
        "cube 1 mm above the bed — its whole underside is unsupported",
    ),
    "two_bodies": Fixture(
        _one(two_bodies), frozenset({"watertight"}), "two disjoint cubes in one body"
    ),
    "boss_plate": Fixture(
        _one(boss_plate), frozenset(), "insert boss + captive nut + rib on a plate"
    ),
    "split_clamp_31_8": Fixture(
        _clamp, frozenset(), "features.split_clamp for a 31.8 bar, both halves"
    ),
}
