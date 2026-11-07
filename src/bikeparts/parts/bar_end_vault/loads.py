"""Design load cases for the Vault bar-end plug (Gate 2), plus a first-order hand check.

`load_cases()` feeds `uv run fea`. These are screens, not proof: Gate 3 physical tests decide.
"""

from __future__ import annotations

import math

import numpy as np
from dataclasses import dataclass

from bikeparts.core.hardware import BOLTS, INSERTS, WASHER_M6_ON_M5
from bikeparts.core.loads import LoadCase as FeaCase
from bikeparts.core.loads import Pin, Spring, Support, Traction, both, cone_z, cylinder_z, fixed, half_space, plane_z
from bikeparts.core.materials import MATERIALS, MaterialName

# Set by Gate 2 FEA: at 0.5 N·m the threaded wedge's governing stress was SF ~2 (rule 7
# wants 3). 0.3 N·m ≈ 300 N preload still presses each wedge on the bar wall with ~300 N,
# so friction (μ ≈ 0.3) holds the plug at ~180 N of pull — several times a push-in plug.
# source: derived from `uv run fea`; μ is an assumption
BOLT_TORQUE_NM = 0.3
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


def hand_check(floor_mm: float, torque_nm: float = BOLT_TORQUE_NM) -> dict[str, float]:
    """Washer punch-through of the body floor, and insert pull-out along its knurled length."""
    petg = MATERIALS[MaterialName.PETG]
    allow = petg.design_strength_mpa * SHEAR_FRACTION
    f = preload_n(torque_nm)
    washer_area = math.pi * WASHER_M6_ON_M5.outer_diameter * floor_mm
    ins = INSERTS["M5"]
    insert_area = math.pi * ins.pocket_diameter * ins.length
    return {
        "preload_n": f,
        "floor_shear_mpa": f / washer_area,
        "insert_shear_mpa": f / insert_area,
        "allowable_shear_mpa": allow,
        "floor_sf": allow / (f / washer_area),
        "insert_sf": allow / (f / insert_area),
    }


# source: assumption — a 200 N (~20 kg) sideways blow on the flange when the bike falls on
# its bar end. The plug is sacrificial past this; Gate 3's drop test overrides.
SIDE_BLOW_N = 200.0


def load_cases(p: object) -> list[FeaCase]:
    """FEA cases for one preset. Coordinates are the print-oriented bodies' own frames."""
    from bikeparts.parts.bar_end_vault.part import WEDGE_SHORT_NUT, dims

    d = dims(p)  # type: ignore[arg-type]
    floor = p.floor  # type: ignore[attr-defined]
    f = preload_n()
    hole_r = (BOLTS["M5"].clearance_diameter + 0.8) / 2
    w = WASHER_M6_ON_M5
    r_t = d["tube_od"] / 2
    z_cone = p.insert_length  # type: ignore[attr-defined]
    r_f = p.flange_diameter / 2  # type: ignore[attr-defined]
    ins = INSERTS["M5"]
    return [
        FeaCase(
            name="bolt_preload",
            description=(
                f"Body: {f:.0f} N bolt preload through the washer onto the floor, reacted by "
                "the body's bottom face resting on the wedge stack"
            ),
            body="body",
            supports=(
                Support(plane_z(0.0, r_min=hole_r), (2,), "bottom face rests on the wedge stack"),
                # 3-2-1 pins remove in-plane rigid motion; the load is axisymmetric, so they
                # carry no reaction
                Pin((hole_r + 1.0, 0.0, 0.0), (0, 1), "rigid-body pin"),
                Pin((0.0, hole_r + 1.0, 0.0), (0,), "rigid-body pin"),
            ),
            loads=(
                Traction(
                    plane_z(floor, r_min=w.inner_diameter / 2, r_max=w.outer_diameter / 2),
                    (0.0, 0.0, -f),
                    "washer on floor",
                ),
            ),
            source=f"T = K·F·d with T = {BOLT_TORQUE_NM} N·m, K = {NUT_FACTOR}, d = 5 mm",
        ),
        FeaCase(
            name="insert_pull",
            description=(
                f"wedge_nut: the bolt pulls the heat-set insert with {f:.0f} N along its "
                "knurled length, reacted by the 45° slope bearing on the other wedge"
            ),
            body="wedge_nut",
            supports=(
                Spring(
                    lambda x: np.abs(x[2] - (WEDGE_SHORT_NUT + x[0] + r_t)) < 0.15,
                    (-1.0, 0.0, 1.0),
                    "slope bearing on the slot wedge",
                ),
                # the pull drives the wedge toward its tall side (+X), into the bar wall
                Spring(
                    both(cylinder_z(r_t, 0.0, WEDGE_SHORT_NUT + 2 * r_t), lambda x: x[0] > 0.7 * r_t),
                    (1.0, 0.0, 0.0),
                    "tall side against the bar wall",
                ),
                Pin((0.0, -r_t, 1.0), (1,), "rigid-body pin (load is symmetric in Y)"),
            ),
            loads=(
                Traction(
                    cylinder_z(ins.pocket_diameter / 2, 0.0, ins.length),
                    (0.0, 0.0, f),
                    "insert knurls on pocket wall",
                ),
            ),
            source="same preload as bolt_preload",
        ),
        FeaCase(
            name="side_blow",
            description=(
                f"Body: {SIDE_BLOW_N:.0f} N sideways on the flange rim (bike falls on its bar "
                "end), the bar holding the tube and the seating cone"
            ),
            body="body",
            supports=(
                fixed(
                    lambda x: cone_z(r_t, z_cone, r_f, z_cone + d["cone_h"])(x)
                    | cylinder_z(r_t, 0.0, z_cone)(x),
                    "seating cone and tube held by the bar",
                ),
            ),
            loads=(
                Traction(
                    both(cylinder_z(r_f, z_cone + d["cone_h"], d["top"]), half_space(0, 1.0)),
                    (-SIDE_BLOW_N, 0.0, 0.0),
                    "blow on flange rim",
                ),
            ),
            source=f"assumption: SIDE_BLOW_N = {SIDE_BLOW_N:.0f} N",
        ),
    ]
