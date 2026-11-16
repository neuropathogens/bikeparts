"""Fit tests for the Ghost tracker spacer."""

from __future__ import annotations

import build123d as bd
import pytest

from bikeparts.core.standards import AIRTAG
from bikeparts.parts.tracker_spacer.params import PRESETS
from bikeparts.parts.tracker_spacer.part import build, describe, dims


def _overlap(a: bd.Shape, b: bd.Shape) -> float:
    inter = a & b
    return sum(s.volume for s in inter.solids()) if inter is not None else 0.0


@pytest.mark.parametrize("preset", list(PRESETS))
def test_airtag_fits_and_tube_clears_by_the_pad(preset: str) -> None:
    p = PRESETS[preset]
    spacer = build(p)["spacer"].shape
    d = dims(p)
    tag = bd.Pos(0, 0, p.floor) * bd.Cylinder(
        AIRTAG.diameter / 2,
        AIRTAG.thickness,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    assert _overlap(spacer, tag) == pytest.approx(0.0, abs=1e-3)
    # tag top sits flush with the saddle line, so the pad holds it against the tube
    assert p.floor + AIRTAG.thickness == pytest.approx(d["height"])
    tube = bd.Pos(0, 0, d["height"] + d["r_saddle"]) * bd.Cylinder(
        p.tube_diameter / 2, 200, rotation=(0, 90, 0)
    )
    assert _overlap(spacer, tube) == pytest.approx(0.0, abs=1e-3)
    # and the tube can't touch the tag directly: the pad thickness separates them
    assert _overlap(tag, tube) == pytest.approx(0.0, abs=1e-3)


def test_bolt_holes_on_64mm_bosses_and_clear_the_pocket() -> None:
    p = PRESETS["tube-35"]
    d = dims(p)
    gap = p.boss_spacing / 2 - d["pocket_d"] / 2 - 5.7 / 2
    assert gap >= 2.4  # solid column between bolt and pocket: clamp load bypasses the tag


def test_readme_bolt_length() -> None:
    doc = describe(PRESETS["tube-35"])
    assert any("M5 × 25" in h for h in doc.hardware)
