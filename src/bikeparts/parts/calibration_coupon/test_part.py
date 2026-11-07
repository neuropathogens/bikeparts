"""Fit tests for the calibration coupon: every feature is really there and really fits."""

from __future__ import annotations

import build123d as bd
import pytest

from bikeparts.core.features import as_part
from bikeparts.core.hardware import INSERTS, NUTS, Thread
from bikeparts.interfaces.dovetail_rail import RAIL, male_rail
from bikeparts.parts.calibration_coupon.params import PRESETS
from bikeparts.parts.calibration_coupon.part import (
    BOSS_Y,
    BOSSES,
    KEY_PEG_Y,
    LADDER_PITCH,
    LADDER_Y,
    PLATE_T,
    SIZE,
    SLOT_LEN,
    boss_height,
    build,
    key_width,
)

P = PRESETS["default"]
_UP = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)


def _overlap(a: bd.Shape, b: bd.Shape) -> float:
    inter = a & b
    return sum(s.volume for s in inter.solids()) if inter is not None else 0.0


@pytest.fixture(scope="module")
def coupon() -> bd.Part:
    return build(P)["coupon"].shape


def test_fits_the_plan_envelope(coupon: bd.Part) -> None:
    for body in build(P).values():
        s = body.shape.bounding_box().size
        assert s.X <= 60 and s.Y <= 60 and s.Z <= 12  # docs/PLAN.md Phase 1


@pytest.mark.parametrize("thread", ["M3", "M4", "M5"])
def test_insert_pockets_are_open(coupon: bd.Part, thread: Thread) -> None:
    """Regression: merging bosses into the plate once refilled the pockets."""
    x = dict((t, xx) for xx, t in BOSSES)[thread]
    ins = INSERTS[thread]
    top = boss_height(thread)
    probe = bd.Pos(x, BOSS_Y, top - ins.pocket_depth + 0.05) * bd.Cylinder(
        ins.pocket_diameter / 2 - 0.05, ins.pocket_depth - 0.1, align=_UP
    )
    assert _overlap(coupon, probe) == pytest.approx(0.0, abs=1e-3)


@pytest.mark.parametrize("i", range(7))
def test_ladder_holes_take_the_peg(coupon: bd.Part, i: int) -> None:
    x = 5.0 + LADDER_PITCH * i
    peg = bd.Pos(x, LADDER_Y, -1) * bd.Cylinder(P.peg_diameter / 2, PLATE_T + 2, align=_UP)
    assert _overlap(coupon, peg) == pytest.approx(0.0, abs=1e-3)


@pytest.mark.parametrize("i", range(3))
def test_nominal_male_slides_in_each_slot(coupon: bd.Part, i: int) -> None:
    x = 9.0 + 18.0 * i
    # male rail hanging upside-down into the slot from the plate's top face
    male = bd.Pos(x, SIZE - SLOT_LEN, PLATE_T) * bd.mirror(male_rail(SLOT_LEN), bd.Plane.XY)
    assert pytest.approx(PLATE_T - RAIL.height) == male.bounding_box().min.Z
    assert _overlap(coupon, male) == pytest.approx(0.0, abs=1e-3)


def test_nut_pocket_takes_an_m4_nut(coupon: bd.Part) -> None:
    nut = NUTS["M4"]
    hexagon = bd.RegularPolygon(nut.across_flats / 3**0.5, 6)
    probe = bd.Pos(52.5, BOSS_Y, PLATE_T - nut.thickness) * bd.extrude(
        hexagon, amount=nut.thickness
    )
    assert _overlap(coupon, probe) == pytest.approx(0.0, abs=1e-3)


def _key_flipped() -> bd.Part:
    """The whole key turned over (features pointing down) and spun 180° about Z, with its
    peg at the origin of X and Y and its bar's underside at Z = 0."""
    key = build(P)["key"].shape
    flipped = bd.mirror(key, bd.Plane.XY)  # bar now z −4..0, features hang below
    spun = bd.Rot(0, 0, 180) * flipped
    return as_part(
        bd.Pos(key_width() / 2, KEY_PEG_Y, 4.0) * spun
    )  # peg axis → (0, 0), bar on z = 0


@pytest.mark.parametrize("i", [0, 3, 6])
def test_whole_key_peg_goes_through_a_hole(coupon: bd.Part, i: int) -> None:
    """With the peg in a ladder hole, the rest of the key must hang off the front edge."""
    x = 5.0 + LADDER_PITCH * i
    key = bd.Pos(x, LADDER_Y, PLATE_T) * _key_flipped()
    assert abs(key.bounding_box().min.Z) < 1e-6  # peg reaches the bed
    assert _overlap(coupon, key) == pytest.approx(0.0, abs=1e-3)


@pytest.mark.parametrize("i", range(3))
def test_whole_key_rail_slides_into_a_slot(coupon: bd.Part, i: int) -> None:
    """Rail fully home in a slot: the rest of the key must hang off the back edge."""
    x = 9.0 + 18.0 * i
    key = build(P)["key"].shape
    flipped = bd.mirror(key, bd.Plane.XY)  # rail hangs below the bar
    # rail occupies key y 38..58; put that at coupon y 38..58 with the key's rest beyond y=58
    spun = bd.Rot(0, 0, 180) * flipped  # rail now y −58..−38, x −bar_w..0
    key_in = bd.Pos(x + key_width() / 2, 2 * SIZE - SLOT_LEN, PLATE_T + 4.0) * spun
    rail_bb = key_in.bounding_box()
    assert abs(rail_bb.min.Y - (SIZE - SLOT_LEN)) < 1e-6  # rail fully home
    assert _overlap(coupon, key_in) == pytest.approx(0.0, abs=1e-3)
