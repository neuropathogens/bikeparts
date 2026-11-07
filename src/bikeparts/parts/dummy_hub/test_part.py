"""Fit tests for the shop dummy hub."""

from __future__ import annotations

import build123d as bd
import pytest

from bikeparts.core.standards import AXLES, SMALLEST_COG_INBOARD
from bikeparts.core.tolerances import PRINTER
from bikeparts.parts.dummy_hub.params import PRESETS, DummyHubParams
from bikeparts.parts.dummy_hub.part import (
    ROLLER_DROPOUT_GAP,
    ROLLER_FLANGE,
    ROLLER_GROOVE,
    SOCKET_DEPTH,
    bores,
    build,
    frame_spacing,
    roller_dims,
)


def _overlap(a: bd.Shape, b: bd.Shape) -> float:
    inter = a & b
    return sum(s.volume for s in inter.solids()) if inter is not None else 0.0


def test_one_preset_per_axle_standard() -> None:
    assert {p.standard for p in PRESETS.values()} == set(AXLES)


@pytest.mark.parametrize("preset", ["12x148", "qr130"])
def test_roller_spins_free_on_body_above_collar(preset: str) -> None:
    p = PRESETS[preset]
    bodies = build(p)
    length = frame_spacing(AXLES[p.standard])
    width = roller_dims()["width"]
    # flat flange outward (toward the drive dropout): flip the printed roller
    roller = bd.Pos(0, 0, length - ROLLER_DROPOUT_GAP) * bd.Rot(180, 0, 0) * bodies["roller"].shape
    assert pytest.approx(length - ROLLER_DROPOUT_GAP - width) == roller.bounding_box().min.Z
    assert _overlap(bodies["body"].shape, roller) == pytest.approx(0.0, abs=1e-3)
    # groove centre on the smallest cog's chainline
    groove_centre = length - ROLLER_DROPOUT_GAP - ROLLER_FLANGE - ROLLER_GROOVE / 2
    assert length - groove_centre == pytest.approx(SMALLEST_COG_INBOARD)


@pytest.mark.parametrize("preset", list(PRESETS))
def test_insert_presses_into_socket(preset: str) -> None:
    p = PRESETS[preset]
    bodies = build(p)
    socket = bores(p)["socket"]
    ins = bodies["insert"].shape
    spigot = [f for f in ins.faces() if f.geom_type == bd.GeomType.CYLINDER]
    od = max(2 * (f.radius or 0.0) for f in spigot)
    assert od == pytest.approx(socket - 2 * PRINTER.press_fit)
    # pressed into the top end (spigot down, stub out): seated, it only touches with the CAD
    # press-fit clearance; pushed 0.3 mm further it hits the body's internal stop cone
    length = frame_spacing(AXLES[p.standard])
    seated = bd.Pos(0, 0, length - SOCKET_DEPTH) * ins
    body = bodies["body"].shape
    assert _overlap(body, seated) == pytest.approx(0.0, abs=1e-3)
    assert _overlap(body, bd.Pos(0, 0, -0.3) * seated) > 0


def test_rear_thru_axle_body_is_spacing_minus_endcaps() -> None:
    assert frame_spacing(AXLES["12x142"]) == pytest.approx(135.0)
    assert frame_spacing(AXLES["12x148"]) == pytest.approx(141.0)
    assert frame_spacing(AXLES["QR130"]) == pytest.approx(130.0)


def test_axles_pass_through() -> None:
    for p in PRESETS.values():
        axle = AXLES[p.standard]
        pin = axle.skewer_diameter or axle.axle_diameter
        assert bores(p)["insert_id"] > pin
        assert bores(p)["mid_bore"] > axle.axle_diameter


def test_rejects_unknown_standard_and_fat_roller_body() -> None:
    with pytest.raises(ValueError):
        DummyHubParams(standard="20x110")
    with pytest.raises(ValueError):
        build(DummyHubParams(standard="12x148", body_diameter=36.0))
