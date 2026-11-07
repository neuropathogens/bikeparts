"""Unit tests for core/features.py — one block per feature."""

from __future__ import annotations

import math

import build123d as bd
import pytest

from bikeparts.core import features as f
from bikeparts.core.hardware import BOLTS, INSERTS, MIN_INSERT_WALL, NUTS
from bikeparts.core.tolerances import PRINTER
from checks import Body, Status, run_checks

# ---------------------------------------------------------------- teardrop_hole


def test_teardrop_tip_points_up_at_r_sqrt2() -> None:
    t = f.teardrop_hole(6.0, 10.0)
    bb = t.bounding_box()
    assert t.is_valid
    assert pytest.approx(3.0 * math.sqrt(2), abs=1e-6) == bb.max.Z
    assert pytest.approx(-3.0, abs=1e-6) == bb.min.Z
    assert pytest.approx(10.0) == bb.size.Y  # axis along Y by default


def test_teardrop_axis_x_and_truncate() -> None:
    t = f.teardrop_hole(6.0, 10.0, axis="X", truncate=3.5)
    bb = t.bounding_box()
    assert pytest.approx(10.0) == bb.size.X
    assert pytest.approx(3.5) == bb.max.Z


def test_teardrop_rejects_bad_truncate() -> None:
    with pytest.raises(ValueError):
        f.teardrop_hole(6.0, 10.0, truncate=2.0)  # below the radius


def test_horizontal_hole_switches_at_3mm() -> None:
    small = f.horizontal_hole(3.0, 10.0)
    big = f.horizontal_hole(3.2, 10.0)
    assert pytest.approx(1.5) == small.bounding_box().max.Z  # round
    assert pytest.approx(1.6 * math.sqrt(2)) == big.bounding_box().max.Z  # teardrop


# ---------------------------------------------------------------- insert_boss


def test_insert_boss_wall_and_pocket() -> None:
    ins = INSERTS["M4"]
    boss = f.insert_boss("M4", 14.0)
    od = ins.pocket_diameter + 2 * MIN_INSERT_WALL
    expected = math.pi / 4 * (od**2 * 14.0 - ins.pocket_diameter**2 * ins.pocket_depth)
    assert boss.is_valid
    assert boss.volume == pytest.approx(expected, rel=1e-4)
    assert pytest.approx(0.0) == boss.bounding_box().min.Z


def test_insert_boss_rejects_thin_wall_and_short_boss() -> None:
    with pytest.raises(ValueError, match=r"2\.4"):
        f.insert_boss("M4", 14.0, outer_d=INSERTS["M4"].pocket_diameter + 2.0)
    with pytest.raises(ValueError, match="pocket depth"):
        f.insert_boss("M5", 8.0)


# ---------------------------------------------------------------- captive_nut_pocket


def test_nut_pocket_across_flats_includes_tolerance() -> None:
    p = f.captive_nut_pocket("M4")
    bb = p.bounding_box()
    assert pytest.approx(NUTS["M4"].across_flats + PRINTER.nut_pocket_flats, abs=1e-6) == bb.size.Y
    assert pytest.approx(0.0) == bb.min.Z


def test_nut_pocket_slot_extends_plus_x() -> None:
    p = f.captive_nut_pocket("M3", slot=8.0)
    assert pytest.approx(8.0) == p.bounding_box().max.X


def test_nut_pocket_rejects_shallow() -> None:
    with pytest.raises(ValueError):
        f.captive_nut_pocket("M5", depth=2.0)


# ---------------------------------------------------------------- rib


def test_rib_triangle_volume_and_position() -> None:
    r = f.rib(20.0, 10.0, 1.6)
    assert r.volume == pytest.approx(0.5 * 20 * 10 * 1.6, rel=1e-6)
    bb = r.bounding_box()
    assert pytest.approx((0.0, 0.0), abs=1e-9) == (bb.min.X, bb.min.Z)


@pytest.mark.parametrize("t", [1.0, 1.5, 2.2])
def test_rib_rejects_non_nozzle_walls(t: float) -> None:
    with pytest.raises(ValueError):
        f.rib(20.0, 10.0, t)


# ---------------------------------------------------------------- bed_chamfer


def test_bed_chamfer_shrinks_only_the_bottom_face() -> None:
    box = f.as_part(bd.Box(20, 20, 10, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)))
    c = PRINTER.bed_chamfer
    out = f.bed_chamfer(box)
    bottom = [fc for fc in out.faces() if fc.bounding_box().max.Z < 1e-6]
    top = [fc for fc in out.faces() if fc.bounding_box().min.Z > 10 - 1e-6]
    assert bottom[0].area == pytest.approx((20 - 2 * c) ** 2, rel=1e-6)
    assert top[0].area == pytest.approx(400.0)


def test_bed_chamfer_requires_part_on_bed() -> None:
    with pytest.raises(ValueError, match="Z = 0"):
        f.bed_chamfer(bd.Pos(0, 0, 10) * bd.Box(10, 10, 10))


# ---------------------------------------------------------------- split_clamp


@pytest.mark.parametrize("bar", [31.8, 35.0])
def test_split_clamp_geometry(bar: float) -> None:
    bore = bar + 0.5
    c = f.split_clamp(bore, 24.0)
    for half in (c.bolt_half, c.insert_half):
        assert half.is_valid and len(half.solids()) == 1
        assert pytest.approx(0.0) == half.bounding_box().min.Z
        assert pytest.approx(24.0) == half.bounding_box().max.Z
    assert pytest.approx(c.gap / 2) == c.bolt_half.bounding_box().min.Y
    assert pytest.approx(-c.gap / 2) == c.insert_half.bounding_box().max.Y
    # rule 3: ≥ 2.4 mm between insert pocket and bore
    assert c.bolt_x - bore / 2 - INSERTS["M4"].pocket_diameter / 2 >= MIN_INSERT_WALL - 1e-9
    # bore is clear: a cylinder of the bore diameter doesn't intersect either half
    probe = bd.Cylinder(bore / 2 - 0.01, 100)
    assert (c.bolt_half & probe).volume == pytest.approx(0.0, abs=1e-6)
    assert c.bolt_grip == pytest.approx(c.ear_thickness + c.gap + INSERTS["M4"].length)
    assert BOLTS["M4"].clearance_diameter > 4.0


@pytest.mark.parametrize("bar", [31.8, 35.0])
def test_split_clamp_halves_pass_every_check(bar: float) -> None:
    c = f.split_clamp(bar + 0.5, 24.0)
    for name, half in (("bolt", c.bolt_half), ("insert", c.insert_half)):
        results = run_checks(Body(name, half))
        assert all(r.status is Status.PASS for r in results), [
            (r.check, r.summary) for r in results if r.status is not Status.PASS
        ]


def test_split_clamp_rejects_narrow_width_and_bad_wall() -> None:
    with pytest.raises(ValueError, match="too narrow"):
        f.split_clamp(32.3, 20.0)
    with pytest.raises(ValueError):
        f.split_clamp(32.3, 24.0, wall=3.0)
