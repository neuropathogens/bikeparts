"""Design load cases for the Vault bar-end plug (Gate 2 FEA runs these in Phase 3).

Until the FEA pipeline exists, `hand_check()` gives first-order stresses so the README can
state the margin honestly. These are screens, not proof: Gate 3 physical tests decide.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from bikeparts.core.hardware import NUTS, WASHERS
from bikeparts.core.materials import MATERIALS, MaterialName

# Chosen so the hand check meets rule 7 (SF ≥ 3) at the design load. ~500 N of preload still
# gives ~150 N of friction holding the plug in (μ ≈ 0.3 assumed). Gate 3 torques to this + 25 %.
# source: derived — see hand_check(); μ is an assumption
BOLT_TORQUE_NM = 0.5
# source: common nut-factor approximation T = K·F·d with K ≈ 0.2 (dry steel)
NUT_FACTOR = 0.2
# source: assumption — plastic shear strength taken as half the design tensile strength
SHEAR_FRACTION = 0.5


@dataclass(frozen=True)
class LoadCase:
    name: str
    description: str
    force_n: float


def preload_n(torque_nm: float = BOLT_TORQUE_NM, d_mm: float = 5.0) -> float:
    return torque_nm / (NUT_FACTOR * d_mm / 1000.0)


LOAD_CASES = [
    LoadCase(
        "bolt_preload",
        "M5 bolt preload at the spec torque, clamping body floor, wedges and nut pocket",
        preload_n(),
    ),
    LoadCase(
        "gate3_overtorque",
        "Gate 3 bolt-torque test: spec torque + 25 %",
        preload_n(BOLT_TORQUE_NM * 1.25),
    ),
]


def hand_check(
    floor_mm: float, nut_cover_mm: float, torque_nm: float = BOLT_TORQUE_NM
) -> dict[str, float]:
    """Punch-through shear of the washer through the floor and of the nut through the wedge."""
    petg = MATERIALS[MaterialName.PETG]
    allow = petg.design_strength_mpa * SHEAR_FRACTION
    f = preload_n(torque_nm)
    washer_area = math.pi * WASHERS["M5"].outer_diameter * floor_mm
    nut = NUTS["M5"]
    nut_area = 6 * (nut.pocket_corners / 2) * nut_cover_mm  # hexagon perimeter × depth
    return {
        "preload_n": f,
        "floor_shear_mpa": f / washer_area,
        "nut_shear_mpa": f / nut_area,
        "allowable_shear_mpa": allow,
        "floor_sf": allow / (f / washer_area),
        "nut_sf": allow / (f / nut_area),
    }
