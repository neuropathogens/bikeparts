"""Ghost tracker spacer — hides an AirTag between the frame and the bottle cage.

Print orientation: cage face on the bed, saddle facing up. The pocket opens toward the frame
tube, so in use the tag is sealed between spacer and tube: it can only be reached by removing
the cage *and* the spacer. All holes are vertical, the saddle is a valley (no overhang), and
the bolt columns are solid so clamp load runs bolt → spacer → frame, never through the pocket.
"""

from __future__ import annotations

import math

import build123d as bd

from bikeparts.core import features as f
from bikeparts.core.hardware import BOLTS, next_bolt_length
from bikeparts.core.materials import MaterialName
from bikeparts.core.standards import RIVNUT_FLANGE_DIAMETER, RIVNUT_FLANGE_HEIGHT
from bikeparts.core.tolerances import PRINTER, check_wall
from bikeparts.parts import Bodies, PartDoc, PartSpec, PrintBody
from bikeparts.parts.tracker_spacer.params import PRESETS, TrackerSpacerParams, sweep

# source: assumption — 2.0 mm flat land where the wings meet the saddle, so no knife edge
LAND = 2.0
# source: assumption — Ø8 push-out / speaker hole through the floor
PUSH_HOLE = 8.0
# source: assumption — plan-view corner radius. Kept at the rule-4 minimum: bigger rounds
# meet the saddle wings at an acute angle and leave a knife edge (min_wall catches it).
CORNER_R = 1.0
# source: assumption — a typical bottle cage bolt is M5 × 12 (caliper your own)
STOCK_CAGE_BOLT = 12.0


def dims(p: TrackerSpacerParams) -> dict[str, float]:
    check_wall(p.floor)
    check_wall(p.side_wall)
    pocket_d = p.tag_diameter + 2 * PRINTER.sliding_fit
    width = pocket_d + 2 * p.side_wall
    height = p.floor + p.tag_thickness  # spacer thickness on the tube's centreline
    r_saddle = p.tube_diameter / 2 + p.pad_thickness
    y_land = width / 2 - LAND
    natural = (
        r_saddle - math.sqrt(max(r_saddle**2 - y_land**2, 0.0)) if y_land < r_saddle else p.wrap_max
    )
    wrap = min(natural, p.wrap_max)
    return {
        "pocket_d": pocket_d,
        "width": width,
        "height": height,
        "r_saddle": r_saddle,
        "wrap": wrap,
        "total": height + wrap,
    }


def build_spacer(p: TrackerSpacerParams) -> PrintBody:
    d = dims(p)
    w, h, r = d["width"], d["height"], d["r_saddle"]
    outline = bd.Rectangle(p.length, w).faces()[0]
    outline = outline.fillet_2d(CORNER_R, outline.vertices())
    block = bd.extrude(outline, amount=d["total"])
    saddle = bd.Pos(0, 0, h + r) * bd.Cylinder(r, p.length + 2, rotation=(0, 90, 0))
    body = block - saddle

    up = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    pocket = bd.Pos(0, 0, p.floor) * bd.Cylinder(d["pocket_d"] / 2, 60, align=up)
    push = bd.Pos(0, 0, -1) * bd.Cylinder(PUSH_HOLE / 2, p.floor + 2, align=up)
    body = body - pocket - push

    bolt = BOLTS["M5"]
    for sx in (-1, 1):
        x = sx * p.boss_spacing / 2
        hole = bd.Pos(x, 0, -1) * bd.Cylinder(bolt.clearance_diameter / 2, 60, align=up)
        flange = bd.Pos(x, 0, h - RIVNUT_FLANGE_HEIGHT) * bd.Cylinder(
            RIVNUT_FLANGE_DIAMETER / 2, 60, align=up
        )
        body = body - hole - flange

    exempt: tuple[f.ExemptRegion, ...] = ()
    if p.label:
        face = bd.Plane(origin=(p.length / 2, 0, h / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        cutter, region = f.deboss_text(f"{p.tube_diameter:g}", 4.5, face)
        body = body - cutter
        exempt = (region,)
    return PrintBody(f.bed_chamfer(body), MaterialName.PETG, exempt=exempt)


def build_pad(p: TrackerSpacerParams) -> PrintBody:
    """Flat TPU pad; it bends to the tube. Holes clear the rivnut flanges."""
    d = dims(p)
    # developed width of the saddle up to the wings' land, capped at the spacer width
    half_angle = math.asin(min(1.0, (d["width"] / 2 - LAND) / d["r_saddle"]))
    pad_w = min(2 * d["r_saddle"] * half_angle, d["width"])
    # 1 mm shorter each end than the spacer: keeps ≥ 1.2 mm between the flange holes and the ends
    outline = bd.Rectangle(p.length - 2, pad_w).faces()[0]
    outline = outline.fillet_2d(CORNER_R, outline.vertices())
    pad = bd.extrude(outline, amount=p.pad_thickness)
    for sx in (-1, 1):
        pad = pad - bd.Pos(sx * p.boss_spacing / 2, 0, 0) * bd.Cylinder(
            RIVNUT_FLANGE_DIAMETER / 2 + 0.25, 10
        )
    return PrintBody(
        f.as_part(pad),
        MaterialName.TPU_95A,
        optional=True,
        note="Optional. No TPU? Use a 1 mm adhesive rubber or felt pad cut to the same shape.",
    )


def build(p: TrackerSpacerParams) -> Bodies:
    return {"spacer": build_spacer(p), "pad": build_pad(p)}


def describe(p: TrackerSpacerParams) -> PartDoc:
    d = dims(p)
    added = d["height"] + p.pad_thickness
    bolt = next_bolt_length(STOCK_CAGE_BOLT + added)
    return PartDoc(
        hardware=[
            f"2 × M5 × {bolt:g} socket head cap screws (replace the stock cage bolts; "
            "security-Torx M5 bolts make the tag harder to steal)",
            "1 × Apple AirTag (or any tracker up to Ø31.9 × 8.0 mm)",
        ],
        assembly=[
            "Remove the bottle cage. Clean the tube.",
            "Lay the TPU pad on the tube with its holes over the bosses.",
            "Drop the AirTag into the spacer's pocket (any side up).",
            "Hold the spacer saddle-down on the pad, pocket against the tube, so the tag is trapped.",
            f"Put the cage on top and bolt through cage and spacer with the M5 × {bolt:g} bolts. "
            "Snug them like normal cage bolts (about 2–3 N·m).",
            "Check the bolt reaches the boss thread but doesn't bottom out: it should pull the "
            "cage down firmly before it gets tight. If it bottoms, add a washer under the head.",
        ],
        facts={
            "Tube": f"Ø{p.tube_diameter:g} mm",
            "Stack height on tube centreline": f"{d['height']:.1f} mm spacer + {p.pad_thickness} mm pad",
            "Cage bolts": f"stock length + {added:.1f} mm → M5 × {bolt:g} if your stock bolts are "
            f"M5 × {STOCK_CAGE_BOLT:g}",
            "Tag pocket": f"Ø{d['pocket_d']:.2f} × {p.tag_thickness:g} mm",
        },
    )


PART = PartSpec(
    slug="tracker_spacer",
    number=2,
    title="Ghost tracker spacer",
    tagline="Hides an AirTag between your frame and bottle cage, out of sight and out of reach.",
    problem=(
        "Visible trackers get ripped off, and the clever hiding spots (steerer, seat tube) are "
        "expensive or touch safety parts."
    ),
    innovation=(
        "An 11 mm spacer that sits under the bottle cage on the standard 64 mm bosses. The "
        "AirTag pocket faces the frame, so the tag is sealed between spacer and tube — a thief "
        "has to remove the cage and the spacer to find it, and nothing shows from outside."
    ),
    material=MaterialName.PETG,
    orientation=(
        "Cage face on the bed, saddle up. The spacer is loaded in compression between cage and "
        "tube, across the layers, which is the direction layers are strong in. Every hole is "
        "vertical and the saddle is an open valley, so it needs no supports."
    ),
    params_model=TrackerSpacerParams,
    presets=PRESETS,
    build=build,
    describe=describe,
    sweep=sweep,
    gate3=("bolt_torque", "heat_soak", "ride_vibration"),
    assumptions=(
        "Stock cage bolts are M5 × 12 (the README states the added length so you can adjust).",
        "Rivnut flanges stand less than 1.2 mm proud of the tube and are under Ø10 mm.",
        "The 1.2 mm pad takes up the tag's play; without any pad the tag can rattle 1.2 mm.",
    ),
)
