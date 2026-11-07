"""Vault bar-end plug — expanding bar plug with a twist-lock storage core.

Bodies (all PETG, all print with their axis vertical):
- body: tube that goes in the bar, a 45° cone that seats on the bar end, and a flange whose
  bore carries a quarter-turn bayonet. The hollow core stores tubeless plugs. Printed
  inboard-end down, so the core opens upward and the flange's underside is the 45° cone.
- cap: printed outer-face down; its lugs' 45° faces are the ones that bear on the bayonet lip.
- wedge (× 2, identical): a cylinder cut at 45°. Stacked slope-to-slope they make a cylinder;
  an M5 bolt from inside the core pulls them together, they slide apart sideways and lock
  against the bar wall. All load is compression and in-plane shear — no flexing fingers,
  which would bend across the layer lines.
"""

from __future__ import annotations

import math
from typing import cast

import build123d as bd

from bikeparts.core import features as f
from bikeparts.core.hardware import BOLTS, NUTS, WASHERS, next_bolt_length
from bikeparts.core.materials import MaterialName
from bikeparts.core.tolerances import PRINTER, check_wall
from bikeparts.parts import Bodies, PartDoc, PartSpec, PrintBody
from bikeparts.parts.bar_end_vault.loads import BOLT_TORQUE_NM, hand_check
from bikeparts.parts.bar_end_vault.params import PRESETS, BarEndVaultParams, sweep

_UP = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
# source: assumption — bayonet proportions sized for a Ø13 core in a Ø24 flange
LIP = 1.6  # material above the groove (rule 3 multiple)
GROOVE_DEPTH = 1.4  # radial
GROOVE_H = 3.6  # height at the core wall (lug outer edge stays ≥ 1.6 mm thick)
LUG_CLEAR = 0.25  # per face, = sliding fit
LUG_ARC = 3.6  # mm, along the circumference
FLANGE_H = 7.0
CAP_T = 2.4
CAP_WALL = 2.0
# source: assumption — 3 mm short side on each wedge (no knife edge)
WEDGE_SHORT = 3.0
# source: rule 3 — preferred shelf beside the hole's downhill breakout (≥ 1.2 mm wall)
WEDGE_SHELF = 1.2
# source: assumption — plan-view round on the slot wedge's notch mouth (rule 4 ≥ 1 mm)
NOTCH_MOUTH_R = 1.2
# source: assumption — Ø1.6 grip scallops round the cap rim
KNURL_D = 1.6
# source: assumption — detent bump is a 1.8 mm-wide ridge on the groove floor
DETENT_HALF = 0.9
KNURL_N = 18


def dims(p: BarEndVaultParams) -> dict[str, float]:
    check_wall(p.wall)
    tube_od = p.bar_id_min - 2 * PRINTER.sliding_fit
    core_d = tube_od - 2 * p.wall
    cone_h = (p.flange_diameter - tube_od) / 2
    top = p.insert_length + cone_h + FLANGE_H
    travel = p.bar_id_max - tube_od  # relative sideways travel the wedges must provide
    wedge_h = WEDGE_SHORT + 1.5 * tube_od / 2  # rim cone meets the slope at x = r / 2
    return {
        "tube_od": tube_od,
        "core_d": core_d,
        "cone_h": cone_h,
        "top": top,
        "travel": travel,
        "wedge_h": wedge_h,
        "wedge_mid": WEDGE_SHORT + tube_od / 2,
        "spigot_od": core_d - 2 * PRINTER.sliding_fit,
    }


def _revolve(points: list[tuple[float, float]], start_deg: float, arc_deg: float) -> bd.Part:
    return f.revolve_rz(points, arc_deg, start_deg)


def lug_axial_play() -> float:
    """Free axial travel of a lug in the groove: bottom gap + vertical gap under the 45° ceiling."""
    bottom = LIP + GROOVE_H - spigot_length()
    top = LUG_CLEAR * math.sqrt(2)
    return bottom + top


def spigot_length() -> float:
    return LIP + GROOVE_H - LUG_CLEAR - 0.1


def build_body(p: BarEndVaultParams) -> PrintBody:
    d = dims(p)
    r_t, r_c, r_f = d["tube_od"] / 2, d["core_d"] / 2, p.flange_diameter / 2
    z_cone, top = p.insert_length, d["top"]
    outer = _revolve(
        [(0, 0), (r_t, 0), (r_t, z_cone), (r_f, z_cone + d["cone_h"]), (r_f, top), (0, top)], 0, 360
    )
    core = bd.Pos(0, 0, p.floor) * bd.Cylinder(r_c, top, align=_UP)
    bolt_hole = bd.Pos(0, 0, -1) * bd.Cylinder(
        (BOLTS["M5"].clearance_diameter + 0.8) / 2, p.floor + 2, align=_UP
    )
    body = outer - core - bolt_hole

    # Bayonet: groove with a 45° ceiling under a LIP-thick lip, two axial entry slots.
    r_g = r_c + GROOVE_DEPTH
    z_floor = top - LIP - GROOVE_H
    groove_rz = [
        (r_c - 0.5, z_floor),
        (r_g, z_floor),
        (r_g, top - LIP - GROOVE_DEPTH),
        (r_c, top - LIP),
        (r_c - 0.5, top - LIP),
    ]
    lug_deg = math.degrees(LUG_ARC / r_c)
    slot_deg = math.degrees((LUG_ARC + 2 * LUG_CLEAR + 0.4) / r_c)
    lock_deg = 90.0
    slot_rz = [(r_c - 0.5, z_floor), (r_g, z_floor), (r_g, top + 1), (r_c - 0.5, top + 1)]
    for base in (0.0, 180.0):
        body = body - _revolve(
            groove_rz, base - slot_deg / 2, lock_deg + lug_deg / 2 + slot_deg / 2 + 3
        )
        body = body - _revolve(slot_rz, base - slot_deg / 2, slot_deg)
        if p.detent_interference > 0:
            height = lug_axial_play() + p.detent_interference
            bump = bd.extrude(
                bd.Plane.YZ
                * bd.Polygon((-DETENT_HALF, 0), (DETENT_HALF, 0), (0, height), align=None),
                amount=r_g - r_c - 0.2,
            )
            # entirely behind the locked lug: lug half-width + bump half-width + 1° margin
            bump_half_deg = math.degrees(DETENT_HALF / (r_c + 0.3))
            ang = base + lock_deg - lug_deg / 2 - bump_half_deg - 1.0
            body = body + bd.Rot(0, 0, ang) * bd.Pos(r_c + 0.3, 0, z_floor) * bump
    return PrintBody(f.bed_chamfer(body), MaterialName.PETG)


def build_cap(p: BarEndVaultParams) -> PrintBody:
    d = dims(p)
    r_c = d["core_d"] / 2
    r_s = d["spigot_od"] / 2
    r_g = r_c + GROOVE_DEPTH
    r_l = r_g - LUG_CLEAR
    # depths below the body's top face, measured in use; print z = CAP_T + depth
    lug_top_at_rs = LIP + LUG_CLEAR * math.sqrt(2) + (r_s - r_c)  # parallel to the 45° ceiling
    spigot_len = spigot_length()
    disc = bd.Cylinder(p.flange_diameter / 2, CAP_T, align=_UP)
    for i in range(KNURL_N):
        a = 2 * math.pi * i / KNURL_N
        disc = disc - bd.Pos(
            p.flange_diameter / 2 * math.cos(a), p.flange_diameter / 2 * math.sin(a), -1
        ) * bd.Cylinder(KNURL_D / 2, CAP_T + 2, align=_UP)
    spigot = bd.Pos(0, 0, CAP_T) * (
        bd.Cylinder(r_s, spigot_len, align=_UP) - bd.Cylinder(r_s - CAP_WALL, spigot_len, align=_UP)
    )
    cap = disc + spigot
    z_lo = CAP_T + lug_top_at_rs
    z_hi = CAP_T + spigot_len
    lug_rz = [
        (r_s - 0.6, z_lo),
        (r_s, z_lo),
        (r_l, z_lo + (r_l - r_s)),
        (r_l, z_hi),
        (r_s - 0.6, z_hi),
    ]
    lug_deg = math.degrees(LUG_ARC / r_c)
    for base in (0.0, 180.0):
        cap = cap + _revolve(lug_rz, base - lug_deg / 2, lug_deg)
    return PrintBody(f.bed_chamfer(cap), MaterialName.PETG)


def wedge_shape(p: BarEndVaultParams, nut: bool) -> bd.Part:
    """A cylinder cut by the 45° plane z = WEDGE_SHORT + (x + r), print-ready.

    Edge fixes so nothing is feathered (feathered PETG lips curl or chip and jam the slide):
    - the tall half's rim is trimmed by a 45° cone (a plain 45° cut leaves it acute);
    - nut wedge: on the downhill side of the bolt hole a flat shelf replaces the slope where
      the hole breaks out (the uphill side of the breakout is already obtuse);
    - slot wedge: the slot is open-ended through the short side (a U-notch with rounded
      mouth corners), so there is no downhill breakout at all.

    As the stack tightens, each wedge is pushed toward its own tall side — that side bears on
    the bar wall. The slot wedge slides *downhill* relative to the bolt, hence the notch.
    """
    d = dims(p)
    r = d["tube_od"] / 2
    ws = WEDGE_SHORT
    bolt = BOLTS["M5"]
    a = bolt.clearance_diameter / 2

    plan = cast(bd.Sketch, bd.Sketch() + bd.Circle(r))
    if not nut:
        notch = bd.Pos(0.25, 0) * bd.Circle(a) + bd.Pos(0.25, 0) * bd.Rectangle(
            r + 2, 2 * a, align=(bd.Align.MAX, bd.Align.CENTER)
        )
        face = (plan - notch).faces()[0]
        mouth = [v for v in face.vertices() if abs(math.hypot(v.X, v.Y) - r) < 1e-3]
        plan = cast(bd.Sketch, bd.Sketch() + face.fillet_2d(NOTCH_MOUTH_R, mouth))
    base = bd.extrude(plan, amount=ws + 2 * r + 2)
    below_slope = bd.extrude(
        f.xz_face([(-r - 1, -1), (r + 1, -1), (r + 1, ws + 2 * r + 1), (-r - 1, ws - 1)]),
        amount=r + 1,
        both=True,
    )
    z_c = ws + r  # slope height on the axis; the rim cone starts here
    rim_cone = f.revolve_rz([(0, -1), (r + 1, -1), (r + 1, z_c - 1), (0, z_c + r)])
    w = base & below_slope & rim_cone

    if nut:
        profile = cast(bd.Sketch, bd.Sketch() + bd.Circle(a))
        w = w - f.captive_nut_pocket("M5")
        w = w - bd.Pos(0, 0, -1) * bd.extrude(profile, amount=60)
        x_arc = 0.0  # centre of the downhill end of the hole
        reach = _channel_reach(a, x_arc, r)
        z_s = ws + (x_arc - reach + r)  # slope height where the shelf meets it
        # The hole carried straight downhill above z_s: walls face sideways (90° to the
        # slope), the floor meets the slope at 135°, and the walls die out where the slope
        # drops below z_s, before they reach the rim.
        channel = bd.Pos(x_arc, 0) * bd.Rectangle(
            2 * r + 2, 2 * reach, align=(bd.Align.MAX, bd.Align.CENTER)
        )
        w = w - bd.Pos(0, 0, z_s) * bd.extrude(channel, amount=60)
    return f.bed_chamfer(w)


def _channel_reach(a: float, x_arc: float, r: float) -> float:
    """Half-width of the shelf channel: wider than the hole so a real shelf exists at the
    breakout, but narrow enough that the walls die out (slope below z_s) before the rim."""
    for extra in (WEDGE_SHELF, 0.8, 0.6, 0.4):
        reach = a + extra
        x_end = x_arc - reach  # where the slope drops to the shelf height
        if r**2 - x_end**2 > (reach + 0.4) ** 2:
            return reach
    raise ValueError("wedge too small for the bolt slot; reduce travel or raise bar ID")


def build(p: BarEndVaultParams) -> Bodies:
    return {
        "body": build_body(p),
        "cap": build_cap(p),
        "wedge_nut": PrintBody(wedge_shape(p, nut=True), MaterialName.PETG),
        "wedge_slot": PrintBody(wedge_shape(p, nut=False), MaterialName.PETG),
    }


def bolt_length(p: BarEndVaultParams) -> float:
    d = dims(p)
    return next_bolt_length(p.floor + 2 * d["wedge_mid"] + WASHERS["M5"].thickness)


def describe(p: BarEndVaultParams) -> PartDoc:
    d = dims(p)
    cover = d["wedge_mid"] - NUTS["M5"].thickness - 0.2
    hc = hand_check(p.floor, cover)
    hc3 = hand_check(p.floor, cover, BOLT_TORQUE_NM * 1.25)
    bl = bolt_length(p)
    stack = 2 * WEDGE_SHORT + d["tube_od"]
    return PartDoc(
        hardware=[
            f"1 × M5 × {bl:g} socket head cap screw (ISO 4762)",
            "1 × M5 hex nut (ISO 4032)",
            "1 × M5 plain washer, Ø10 (ISO 7089 / DIN 125-A)",
        ],
        assembly=[
            "Press the M5 nut into the hex pocket on the flat end of `wedge_nut`.",
            "Drop the washer and bolt into the body's core so the bolt pokes out of the inboard end.",
            "Slide `wedge_slot` sideways onto the bolt (it has an open notch), flat face against "
            "the body. Thread the bolt into `wedge_nut` with its slope facing `wedge_slot`: the "
            "two slopes mate into one cylinder.",
            "Turn the bolt until the stack holds together but is still the tube's diameter.",
            "Slide the plug into the bar until the cone seats on the bar end.",
            f"Tighten with a long-arm 4 mm hex key through the core to {BOLT_TORQUE_NM:g} N·m — "
            "snug, fingertip force on a short hex key. The wedges slide apart and lock against "
            "the bar wall. More torque does not hold better; it crushes the plastic.",
            "Fill the core (tubeless plugs, a reamer, a quick link) and twist the cap on a quarter "
            "turn until it clicks past the detent.",
        ],
        facts={
            "Fits bar inner diameter": f"{p.bar_id_min:g}–{p.bar_id_max:g} mm",
            "Insertion depth": f"{p.insert_length + stack:.1f} mm (body {p.insert_length:g} + wedge stack {stack:.1f})",
            "Storage core": f"Ø{d['core_d']:.1f} × {d['top'] - p.floor - 5:.0f} mm (above the bolt head)",
            "Bolt torque": f"{BOLT_TORQUE_NM:g} N·m (preload ≈ {hc['preload_n']:.0f} N)",
            "Hand check at design torque": (
                f"washer punch-through {hc['floor_shear_mpa']:.1f} MPa (SF {hc['floor_sf']:.1f}); "
                f"nut pull-through {hc['nut_shear_mpa']:.1f} MPa (SF {hc['nut_sf']:.1f}); "
                f"allowable {hc['allowable_shear_mpa']:.1f} MPa (unverified PETG values)"
            ),
            "Hand check at Gate 3 over-torque (+25 %)": (
                f"SF {hc3['floor_sf']:.1f} floor, {hc3['nut_sf']:.1f} nut"
            ),
        },
    )


PART = PartSpec(
    slug="bar_end_vault",
    number=5,
    title="Vault bar-end plug",
    tagline="Expanding bar-end plug with a twist-lock core that carries your tubeless repair kit.",
    problem=(
        "Open bar ends are an injury hazard, push-in plugs fall out, and a tubeless repair "
        "kit is useless when it's at home."
    ),
    innovation=(
        "A stem-style double wedge locks the plug into bars from 17 to 21.5 mm inside "
        "diameter (two printed sizes from one source file), and the hollow core behind a quarter-turn bayonet "
        "cap holds tubeless plugs and a reamer. No printed threads and no flexing fingers: "
        "every printed piece works in compression or in-plane shear."
    ),
    material=MaterialName.PETG,
    orientation=(
        "Every piece prints with its axis vertical. The body's bayonet groove and lip are "
        "rings in the layer plane, so the cap's pull-out load is hoop and in-plane shear. The "
        "wedges' 45° faces print facing up and slide on each other in compression."
    ),
    params_model=BarEndVaultParams,
    presets=PRESETS,
    build=build,
    describe=describe,
    sweep=sweep,
    fea=(
        "Gate 2 applies (part 5). FEA pipeline is Phase 3 and has not run. The hand check in "
        "the facts table covers bolt preload only; impact on the bar end is untested."
    ),
    gate3=("bolt_torque", "heat_soak", "ride_vibration", "drop"),
    assumptions=(
        "Bar ends are round inside and 17–21.5 mm across; internal routing ports sit deeper "
        "than ~70 mm.",
        "0.5 N·m (≈ 500 N preload, ~150 N friction at μ ≈ 0.3) is enough to hold the plug; "
        "Gate 3 tests will confirm.",
        "The cap detent (bump 0.1 mm taller than the lug's play) gives a click on a printer "
        "close to the default tolerances; tune `detent_interference` if the cap is too loose "
        "or too stiff.",
    ),
)
