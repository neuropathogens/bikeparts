"""Virtual-assembly fit tests for the Vault bar-end plug."""

from __future__ import annotations

import build123d as bd
import pytest

from bikeparts.parts.bar_end_vault.params import PRESETS, BarEndVaultParams
from bikeparts.parts.bar_end_vault.part import (
    BOLTS,
    WEDGE_SHORT,
    bolt_length,
    build,
    dims,
    lug_axial_play,
)


def _overlap(a: bd.Shape, b: bd.Shape) -> float:
    inter = a & b
    return sum(s.volume for s in inter.solids()) if inter is not None else 0.0


def _cap_in_body(p: BarEndVaultParams, turn_deg: float) -> tuple[bd.Part, bd.Part]:
    bodies = build(p)
    top = dims(p)["top"]
    cap = bd.Rot(0, 0, turn_deg) * bd.Pos(0, 0, top + 2.4) * bd.Rot(180, 0, 0) * bodies["cap"].shape
    return bodies["body"].shape, cap


@pytest.mark.parametrize("preset", list(PRESETS))
@pytest.mark.parametrize("turn", [0.0, 45.0, 90.0])
def test_cap_enters_and_turns_without_collision(preset: str, turn: float) -> None:
    p = PRESETS[preset].model_copy(update={"detent_interference": 0.0})
    body, cap = _cap_in_body(p, turn)
    assert _overlap(body, cap) == pytest.approx(0.0, abs=1e-3)


@pytest.mark.parametrize("preset", list(PRESETS))
def test_cap_cannot_lift_out_when_locked(preset: str) -> None:
    """Locked at 90°, lifting the cap by more than its play makes the lugs hit the lip."""
    p = PRESETS[preset].model_copy(update={"detent_interference": 0.0})
    body, cap = _cap_in_body(p, 90.0)
    lifted = bd.Pos(0, 0, lug_axial_play() + 0.3) * cap
    assert _overlap(body, lifted) > 0.5


@pytest.mark.parametrize("preset", list(PRESETS))
def test_detent_clear_when_locked_but_blocks_on_the_way(preset: str) -> None:
    p = PRESETS[preset]
    body, locked = _cap_in_body(p, 90.0)
    assert _overlap(body, locked) == pytest.approx(0.0, abs=1e-3)
    # lifted to the top of its play, the lug still has to climb the bump at ~70°
    _, passing = _cap_in_body(p, 72.0)
    lifted = bd.Pos(0, 0, lug_axial_play() - 0.01) * passing
    assert _overlap(body, lifted) > 0.0


@pytest.mark.parametrize("preset", list(PRESETS))
def test_wedges_stack_into_a_cylinder(preset: str) -> None:
    p = PRESETS[preset]
    bodies = build(p)
    r = dims(p)["tube_od"] / 2
    lower = bodies["wedge_nut"].shape
    upper = bd.Pos(0, 0, 2 * WEDGE_SHORT + 2 * r) * bd.Rot(0, 180, 0) * bodies["wedge_slot"].shape
    assert _overlap(lower, upper) == pytest.approx(0.0, abs=1e-2)
    stack = lower + upper
    bb = stack.bounding_box()
    assert pytest.approx(2 * r, abs=0.05) == bb.size.X  # coaxial → same diameter as the tube
    # sliding the upper wedge downhill by the full travel still clears the bolt
    d = dims(p)
    shifted = bd.Pos(-d["travel"], 0, -d["travel"]) * upper  # −x world = its downhill
    bolt = bd.Cylinder(BOLTS["M5"].nominal / 2, 100)
    assert _overlap(shifted, bolt) == pytest.approx(0.0, abs=1e-3)


def test_presets_cover_the_plan_range() -> None:
    lo = min(p.bar_id_min for p in PRESETS.values())
    hi = max(p.bar_id_max for p in PRESETS.values())
    assert lo <= 17.0 and hi >= 21.0  # docs/PLAN.md part 5


def test_bolt_is_a_standard_length() -> None:
    assert bolt_length(PRESETS["id-17-19.5"]) in (25.0, 30.0, 35.0)


def test_rejects_too_wide_a_range() -> None:
    with pytest.raises(ValueError):
        BarEndVaultParams(bar_id_min=17.0, bar_id_max=21.0)


@pytest.mark.parametrize("preset", list(PRESETS))
def test_hand_check_meets_rule_7_at_design_torque(preset: str) -> None:
    from bikeparts.core.hardware import NUTS
    from bikeparts.core.materials import MIN_SAFETY_FACTOR
    from bikeparts.parts.bar_end_vault.loads import hand_check

    p = PRESETS[preset]
    hc = hand_check(p.floor, dims(p)["wedge_mid"] - NUTS["M5"].thickness - 0.2)
    assert hc["floor_sf"] >= MIN_SAFETY_FACTOR
    assert hc["nut_sf"] >= MIN_SAFETY_FACTOR
