"""Shop dummy hub — rear shipping spacer + chain keeper, and front fork spacers.

One part replaces two shop tools. Clamped in the dropouts with the bike's own skewer or
thru-axle, the body holds the frame or fork at exactly hub width for shipping. Rear versions
carry a free-spinning chain roller where the smallest cog sits, so you can backpedal and
scrub the chain with the wheel out, and the derailleur keeps tension during transport.

Bodies (PETG): `body` prints standing up (axle along Z), so dropout clamping and shipping
crush load are compression along the build direction, where layers only press together.
`insert` × 2 press into the body's ends and carry the axle-standard detail (QR stub,
thru-axle end-cap stub, or a flush bushing). `roller` spins on the body like a cog.
"""

from __future__ import annotations

import math

import build123d as bd

from bikeparts.core import features as f
from bikeparts.core.materials import MaterialName
from bikeparts.core.standards import (
    AXLES,
    CHAIN,
    QR_AXLE_STUB,
    SMALLEST_COG_INBOARD,
    THRU_AXLE_ENDCAP_RECESS,
    Axle,
)
from bikeparts.core.tolerances import PRINTER, check_wall
from bikeparts.parts import Bodies, PartDoc, PartSpec, PrintBody
from bikeparts.parts.dummy_hub.params import PRESETS, DummyHubParams, sweep

_UP = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
# source: assumption — 8 mm deep insert sockets with a 45° stop cone, 2.4 mm insert wall
SOCKET_DEPTH = 8.0
INSERT_WALL = 2.4
# source: assumption — 2 mm flanges either side of the chain groove
ROLLER_FLANGE = 2.0
# source: CHAIN.max_outer_width (7.3) + 0.7 mm so 8- to 12-speed chains all fit
ROLLER_GROOVE = 8.0
# Roller's flat face stops this short of the dropout, which puts the groove centre on the
# smallest cog's chainline (and keeps the roller from ever being clamped).
# source: derived from standards.SMALLEST_COG_INBOARD
ROLLER_DROPOUT_GAP = SMALLEST_COG_INBOARD - ROLLER_FLANGE - ROLLER_GROOVE / 2
assert ROLLER_DROPOUT_GAP >= 0.5, "roller would touch the dropout"
# source: assumption — 3 mm collar lip that locates the roller axially
COLLAR_LIP = 3.0
# source: rule 3 — vertical rim above the collar's 45° cone (4 layers ≥ 1.2 mm wall)
COLLAR_RIM = 1.6
# source: assumption — 1.2 mm deep flat on the body for the debossed label
LABEL_FLAT = 1.2


def frame_spacing(axle: Axle) -> float:
    """Inner dropout spacing the body must fill."""
    if axle.kind == "thru" and axle.position == "rear":
        return axle.hub_width - 2 * THRU_AXLE_ENDCAP_RECESS
    return axle.hub_width


def insert_kind(axle: Axle) -> str:
    if axle.kind == "QR":
        return "qr"
    return "thru_stub" if axle.position == "rear" else "thru_flush"


def bores(p: DummyHubParams) -> dict[str, float]:
    axle = AXLES[p.standard]
    pin = axle.skewer_diameter if axle.kind == "QR" else axle.axle_diameter
    assert pin is not None
    insert_id = pin + 2 * PRINTER.sliding_fit
    # one socket size for every standard: fits the largest thru-axle insert
    largest = max(a.axle_diameter for a in AXLES.values() if a.kind == "thru")
    socket = largest + 2 * PRINTER.sliding_fit + 2 * INSERT_WALL
    mid_bore = largest + 2 * PRINTER.sliding_fit + 0.5
    return {"insert_id": insert_id, "socket": socket, "mid_bore": mid_bore}


def roller_dims() -> dict[str, float]:
    # Smallest common cog: 11T. Chain rollers sit on the pitch circle minus a roller diameter.
    # source: pitch-circle diameter of an n-tooth sprocket = pitch / sin(π / n); 11T assumed
    pcd = CHAIN.pitch / math.sin(math.pi / 11)
    seat = pcd - CHAIN.roller_diameter
    return {
        "seat": seat,
        "flange": seat + 2 * 4.0,  # 4 mm flange height retains the side plates
        "width": ROLLER_FLANGE + ROLLER_GROOVE + 4.0 + ROLLER_FLANGE,  # 45° cone under top flange
    }


def max_roller_body() -> float:
    return 2 * (roller_dims()["seat"] / 2 - 2.4 - PRINTER.sliding_fit)


def build_body(p: DummyHubParams) -> PrintBody:
    axle = AXLES[p.standard]
    length = frame_spacing(axle)
    b = bores(p)
    r = p.body_diameter / 2
    check_wall(round((p.body_diameter - b["socket"]) / 2 / 0.4) * 0.4)
    body = bd.Cylinder(r, length, align=_UP)

    # bore: insert sockets at both ends, 45° stop cones, narrower through-bore between
    rs, rm = b["socket"] / 2, b["mid_bore"] / 2
    step = rs - rm
    # The insert's 45° bed chamfer lands flat on the 45° stop cone, so the cone starts one
    # chamfer short of the socket depth and the insert seats flush with the body end.
    stop = SOCKET_DEPTH - PRINTER.bed_chamfer
    bore_rz = [
        (0, -1),
        (rs, -1),
        (rs, stop),
        (rm, stop + step),
        (rm, length - stop - step),
        (rs, length - stop),
        (rs, length + 1),
        (0, length + 1),
    ]
    bore = f.revolve_rz(bore_rz)
    body = body - bore

    if p.has_roller:
        rd = roller_dims()
        z_top_roller = length - ROLLER_DROPOUT_GAP
        z_collar = z_top_roller - rd["width"] - 0.5  # 0.5 mm axial play
        collar_r = r + COLLAR_LIP
        collar = f.revolve_rz(
            [
                (r - 0.5, z_collar - COLLAR_LIP - COLLAR_RIM),
                (r, z_collar - COLLAR_LIP - COLLAR_RIM),
                (collar_r, z_collar - COLLAR_RIM),
                (collar_r, z_collar),
                (r - 0.5, z_collar),
            ]
        )
        body = body + collar

    exempt: tuple[f.ExemptRegion, ...] = ()
    if p.label:
        x_flat = r - LABEL_FLAT
        z0, z1 = SOCKET_DEPTH + 4, min(length * 0.55, SOCKET_DEPTH + 60)
        flat = bd.Pos(x_flat, 0, z0) * bd.Box(
            10, 3 * r, z1 - z0, align=(bd.Align.MIN, bd.Align.CENTER, bd.Align.MIN)
        )
        body = body - flat
        face = bd.Plane(origin=(x_flat, 0, (z0 + z1) / 2), x_dir=(0, 0, 1), z_dir=(1, 0, 0))
        text = axle.name.split(" (")[0].replace("×", "x")
        cutter, region = f.deboss_text(text, 5.0, face)
        body = body - cutter
        exempt = (region,)
    return PrintBody(
        f.bed_chamfer(body),
        MaterialName.PETG,
        exempt=exempt,
        slicer={"brim-width": "5"},
        note="Tall and slim: print with the 5 mm brim (set automatically in the slice).",
    )


def build_insert(p: DummyHubParams) -> PrintBody:
    axle = AXLES[p.standard]
    b = bores(p)
    kind = insert_kind(axle)
    spigot_r = b["socket"] / 2 - PRINTER.press_fit
    part = bd.Cylinder(spigot_r, SOCKET_DEPTH, align=_UP)
    if kind == "qr":
        # stub slightly under the dropout slot width, which matches the hub's axle end
        stub_d = axle.axle_diameter - 2 * 0.2  # source: assumption, 0.2 mm per side in the slot
        part = part + bd.Pos(0, 0, SOCKET_DEPTH) * bd.Cylinder(stub_d / 2, QR_AXLE_STUB, align=_UP)
    elif kind == "thru_stub":
        stub_d = b["insert_id"] + 2 * 1.6  # source: rule 3, 1.6 mm wall around the axle
        part = part + bd.Pos(0, 0, SOCKET_DEPTH) * bd.Cylinder(
            stub_d / 2, THRU_AXLE_ENDCAP_RECESS, align=_UP
        )
    part = part - bd.Pos(0, 0, -1) * bd.Cylinder(b["insert_id"] / 2, 40, align=_UP)
    return PrintBody(f.bed_chamfer(part), MaterialName.PETG, qty=2)


def build_roller(p: DummyHubParams) -> PrintBody:
    rd = roller_dims()
    bore_r = p.body_diameter / 2 + PRINTER.sliding_fit
    rs, rf = rd["seat"] / 2, rd["flange"] / 2
    if rs - bore_r < 2.4:  # source: rule 3, 2.4 mm roller wall under the chain seat
        raise ValueError(
            f"body Ø{p.body_diameter:g} leaves the roller under 2.4 mm wall; max Ø{max_roller_body():.1f}"
        )
    z1 = ROLLER_FLANGE
    z2 = z1 + ROLLER_GROOVE
    z3 = z2 + (rf - rs)  # 45° cone under the top flange
    z4 = z3 + ROLLER_FLANGE
    profile = [(bore_r, 0), (rf, 0), (rf, z1), (rs, z1), (rs, z2), (rf, z3), (rf, z4), (bore_r, z4)]
    roller = f.revolve_rz(profile)
    return PrintBody(f.bed_chamfer(roller), MaterialName.PETG)


def build(p: DummyHubParams) -> Bodies:
    bodies = {"body": build_body(p), "insert": build_insert(p)}
    if p.has_roller:
        bodies["roller"] = build_roller(p)
    return bodies


def describe(p: DummyHubParams) -> PartDoc:
    axle = AXLES[p.standard]
    kind = insert_kind(axle)
    b = bores(p)
    steps = [
        "Press an insert into each end of the body (stub facing out) until it stops on the "
        "internal cone. A vise or a tap with a mallet does it.",
    ]
    if p.has_roller:
        steps.append(
            "Slide the roller onto the drive-side end, the flat flange face outward, so it "
            "rests on the collar. It should spin freely."
        )
    steps += [
        "Remove the wheel. Rear: shift to the smallest cog first.",
        "Set the dummy hub in the dropouts"
        + (
            " with the roller on the drive side and the chain over the roller"
            if p.has_roller
            else ""
        )
        + ".",
        "Clamp it with the bike's own "
        + ("quick-release skewer" if axle.kind == "QR" else "thru-axle")
        + " at normal closing force.",
    ]
    if p.has_roller:
        steps.append(
            "Backpedal: the chain runs on the roller like a cog, so you can wash and lube it."
        )
    facts = {
        "Axle standard": axle.name,
        "Body length (dropout to dropout)": f"{frame_spacing(axle):g} mm",
        "Insert": {
            "qr": f"QR stub Ø{axle.axle_diameter - 0.4:g} × {QR_AXLE_STUB:g} mm, bore Ø{b['insert_id']:.1f} for the skewer",
            "thru_stub": f"end-cap stub {THRU_AXLE_ENDCAP_RECESS:g} mm into the dropout recess, "
            f"bore Ø{b['insert_id']:.1f}",
            "thru_flush": f"flush bushing, bore Ø{b['insert_id']:.1f}",
        }[kind],
    }
    if p.has_roller:
        rd = roller_dims()
        facts["Chain roller"] = (
            f"seat Ø{rd['seat']:.1f} (an 11T cog's root circle), groove {ROLLER_GROOVE:g} mm, "
            f"centred ~{SMALLEST_COG_INBOARD:g} mm inboard of the drive dropout"
        )
    if axle.kind == "thru" and axle.position == "rear":
        facts["Check first"] = (
            f"inner dropout spacing should be {frame_spacing(axle):g} mm "
            f"({axle.hub_width:g} − 2 × {THRU_AXLE_ENDCAP_RECESS:g} mm end-cap recesses) — "
            "UNVERIFIED, measure one frame before printing a batch"
        )
    return PartDoc(
        hardware=["None: uses the bike's own skewer or thru-axle."], assembly=steps, facts=facts
    )


PART = PartSpec(
    slug="dummy_hub",
    number=3,
    title="Shop dummy hub",
    tagline="Shipping spacer and chain keeper in one: holds the dropouts and spins the chain.",
    problem=(
        "Bikes shipped without wheels get crushed fork blades and bent rear triangles, and "
        "with the rear wheel out the chain flops, grinds the frame and can't be cleaned."
    ),
    innovation=(
        "One parametric body per axle standard, clamped by the bike's own skewer or "
        "thru-axle, so it's exactly hub-width and can't fall out in the box. Rear versions "
        "carry a free-spinning roller where the smallest cog sits: backpedal to wash the "
        "chain with the wheel out, and the derailleur stays tensioned in transit. Swap-in end "
        "inserts carry the axle-specific detail; the standard is debossed on the body and "
        "each standard gets its own filament colour."
    ),
    material=MaterialName.PETG,
    orientation=(
        "The body prints standing up so the dropout clamp and shipping crush load run along "
        "the build axis, where layers simply press together. The roller and inserts print "
        "flat on their faces; every overhang is a 45° cone."
    ),
    params_model=DummyHubParams,
    presets=PRESETS,
    build=build,
    describe=describe,
    sweep=sweep,
    gate3=("shipping_compression", "heat_soak"),
    assumptions=(
        "12×142 and 12×148 frames have 3.5 mm end-cap recesses, so the body is 135 / 141 mm "
        "between dropouts. UNVERIFIED: measure a frame before printing a batch.",
        "QR axle ends are Ø9 (front) / Ø10 (rear) and dropouts are thicker than the 3 mm stub.",
        "The smallest cog's chainline is ~7 mm inboard of the drive dropout.",
        "PETG-on-PETG bushing is fine for hand-speed backpedalling; it is not a bearing.",
    ),
)
