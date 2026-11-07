"""Calibration coupon — one small print that measures this printer's real fits.

Two bodies printed in the same job (both under 60 × 60 × 12 mm):
- `coupon`: an 8 mm plate with a hole ladder (Ø6 + 2 × 0.10 … 0.40 mm), M3/M4/M5 heat-set
  insert bosses, a captive M4 nut pocket, and three female dovetail slots at 0.15 / 0.25 /
  0.35 mm. Clearances are debossed on the plate's edges.
- `key`: the nominal Ø6 peg and male dovetail to try in each hole and slot, and a block with
  Ø3/5/8 horizontal teardrop holes (they print the way every horizontal hole in a part does).

Print it in the material you'll print parts in (PETG for v1), with the `profiles/`.
"""

from __future__ import annotations

import build123d as bd

from bikeparts.core import features as f
from bikeparts.core.hardware import BOLTS, INSERTS, NUTS, Thread
from bikeparts.core.materials import MaterialName
from bikeparts.core.tolerances import PRINTER
from bikeparts.interfaces.dovetail_rail import RAIL, female_cutter, male_rail
from bikeparts.parts import Bodies, PartDoc, PartSpec, PrintBody
from bikeparts.parts.calibration_coupon.params import PRESETS, CouponParams

_MIN = (bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)
_UP = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
# source: assumption — layout of a 58 × 58 mm coupon (fits the 60 × 60 limit in PLAN Phase 1)
SIZE = 58.0
PLATE_T = 8.0  # dovetail slot depth + ≥ 1.2 mm floor after the 0.45 mm bed chamfer
LADDER_PITCH = 8.0
LADDER_Y = 7.0
BOSS_Y = 20.0
BLOCK_H = 12.0  # teardrop block on the key
SLOT_LEN = 20.0
LABEL = 3.6  # text size on the plate edge
SLOT_LABEL = 3.0  # fits the 4.8 mm gaps between dovetail slots


def _hundredths(c: float) -> str:
    return f"{round(c * 100):02d}"


BOSSES: tuple[tuple[float, Thread], ...] = ((10.0, "M3"), (25.0, "M4"), (41.0, "M5"))


def boss_height(thread: Thread) -> float:
    """Tall enough for the pocket plus a 1.2 mm floor, and 2 mm proud of the plate."""
    return max(INSERTS[thread].pocket_depth + 1.2, PLATE_T + 2.0)


def build_coupon(p: CouponParams) -> PrintBody:
    plate = bd.Box(SIZE, SIZE, PLATE_T, align=_MIN)
    exempt: list[f.ExemptRegion] = []

    # hole ladder, labelled on the front edge
    for i, c in enumerate(p.ladder):
        x = 5.0 + LADDER_PITCH * i
        plate -= bd.Pos(x, LADDER_Y, -1) * bd.Cylinder(
            p.peg_diameter / 2 + c, PLATE_T + 2, align=_UP
        )
        face = bd.Plane(origin=(x, 0, PLATE_T / 2), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
        cutter, region = f.deboss_text(_hundredths(c), LABEL, face)
        plate -= cutter
        exempt.append(region)

    # insert bosses (standing on the bed, merged into the plate) + captive nut pocket
    for x, thread in BOSSES:
        h = boss_height(thread)
        plate += bd.Pos(x, BOSS_Y, 0) * f.insert_boss(thread, h)
    for x, thread in BOSSES:  # re-cut: merging into the plate refilled the pockets
        plate -= bd.Pos(x, BOSS_Y, boss_height(thread)) * f.insert_pocket(thread)
    nut_x = 52.5
    plate -= bd.Pos(nut_x, BOSS_Y, PLATE_T - NUTS["M4"].thickness - 0.2) * f.captive_nut_pocket(
        "M4"
    )
    plate -= bd.Pos(nut_x, BOSS_Y, -1) * bd.Cylinder(
        BOLTS["M4"].clearance_diameter / 2, 20, align=_UP
    )

    # three female dovetail slots open at the back edge, labelled on the back edge
    for i, c in enumerate(p.dovetail_fits):
        x = 9.0 + 18.0 * i
        plate -= bd.Pos(x, SIZE - SLOT_LEN, PLATE_T) * female_cutter(SLOT_LEN + 1, c)
        # label in the gap to the slot's right (reads correctly from behind the coupon)
        face = bd.Plane(origin=(x + 9.0, SIZE, PLATE_T / 2), x_dir=(-1, 0, 0), z_dir=(0, 1, 0))
        cutter, region = f.deboss_text(_hundredths(c), SLOT_LABEL, face)
        plate -= cutter
        exempt.append(region)

    return PrintBody(f.bed_chamfer(plate), MaterialName.PETG, exempt=tuple(exempt))


# Key layout along Y: peg at one end, rail at the other, teardrop block between. Using the
# peg or the rail, the rest of the key hangs off the coupon's edge instead of hitting it.
KEY_PEG_Y = 5.0
KEY_BLOCK_Y0, KEY_BLOCK_Y1 = 13.0, SIZE - SLOT_LEN - 1.0
KEY_RAIL_Y0 = SIZE - SLOT_LEN


def key_width() -> float:
    return RAIL.top_width + 4.0


def build_key(p: CouponParams) -> PrintBody:
    """Bar with the nominal Ø6 peg (one end), the nominal male dovetail (other end), and a
    block between them with Ø3/5/8 teardrop holes running across it, open on both sides."""
    bar_w = key_width()
    bar_t = 4.0
    key = bd.Box(bar_w, SIZE, bar_t, align=_MIN)
    key += bd.Pos(bar_w / 2, KEY_PEG_Y, bar_t) * bd.Cylinder(p.peg_diameter / 2, PLATE_T, align=_UP)
    key += bd.Pos(bar_w / 2, KEY_RAIL_Y0, bar_t) * male_rail(SLOT_LEN)
    key += bd.Pos(0, KEY_BLOCK_Y0, 0) * bd.Box(
        bar_w, KEY_BLOCK_Y1 - KEY_BLOCK_Y0, BLOCK_H, align=_MIN
    )
    zc = 5.5
    y = KEY_BLOCK_Y0 + 1.6
    for d in p.teardrops:
        r = d / 2
        tip = r * 2**0.5
        room = BLOCK_H - 1.6 - zc  # keep ≥ 1.6 mm above the hole
        if room < r:
            raise ValueError(f"Ø{d} teardrop doesn't fit the {BLOCK_H} mm block")
        y += r
        key -= bd.Pos(bar_w / 2, y, zc) * f.teardrop_hole(
            d, bar_w + 2, axis="X", truncate=room if room < tip else None
        )
        y += r + 1.6
    if y > KEY_BLOCK_Y1:
        raise ValueError("teardrop holes don't fit on the key's block")
    return PrintBody(f.bed_chamfer(key), MaterialName.PETG)


def build(p: CouponParams) -> Bodies:
    return {"coupon": build_coupon(p), "key": build_key(p)}


def describe(p: CouponParams) -> PartDoc:
    ladder = ", ".join(_hundredths(c) for c in p.ladder)
    return PartDoc(
        hardware=[
            "1 each of the heat-set inserts you'll use: M3, M4, M5",
            "1 × M4 hex nut, 1 × M4 bolt (any length ≥ 10 mm)",
            "Calipers; drill bits or pin gauges of 3, 5 and 8 mm",
        ],
        assembly=[
            f"Holes ({ladder}, hundredths of a mm per side): push the key's Ø{p.peg_diameter:g} "
            "peg through each hole, smallest first. Note the smallest hole it slides through "
            "freely by hand (**sliding fit**) and the smallest it can be pressed into firmly "
            "with your thumb (**press fit**).",
            "Dovetails (15 / 25 / 35): slide the key's rail into each slot from the back edge. "
            "Note the tightest one that slides the full length without forcing (**dovetail**).",
            "Nut: press the M4 nut into the hex pocket. Note **tight** (needs a tap), **good** "
            "(firm push, stays put upside-down) or **loose** (falls out).",
            "Inserts: install each insert with a soldering iron. Note whether it went in "
            "**straight** and flush, **tight** (bulged plastic, crooked) or **loose** (spins "
            "with a bolt in it).",
            "Teardrop holes: try 3, 5 and 8 mm drill shanks (or pin gauges) in the key's block. "
            "Measure the round part of each hole with calipers if a shank won't go.",
            "Fill in the form below, then run `uv run calibrate` with your numbers.",
        ],
        facts={
            "Hole ladder": f"Ø{p.peg_diameter:g} + 2 × ({ladder}) / 100 mm",
            "Dovetail fits": ", ".join(f"{c:.2f}" for c in p.dovetail_fits) + " mm per side",
            "Current tolerances.py": (
                f"sliding {PRINTER.sliding_fit}, press {PRINTER.press_fit}, nut "
                f"+{PRINTER.nut_pocket_flats}, bolt holes +{PRINTER.bolt_hole_extra}, inserts "
                f"{PRINTER.insert_pocket_extra:+}"
            ),
        },
    )


FORM = """\
## Measurement form

Copy this into `test-reports/calibration_coupon/<date>-<printer>.md`, fill it in, then run
the command at the bottom.

```
Printer:                Filament (brand, type):         Date:
Sliding fit (smallest free hole):   0.__   (hundredths → mm per side)
Press fit (smallest firm-press hole): 0.__
Dovetail (tightest full-length slide): 0.__
M4 nut in pocket:        tight / good / loose
Inserts M3 / M4 / M5:    straight / tight / loose   (each)
Teardrop 3 / 5 / 8:      measured Ø __ / __ / __    (round part, calipers)
```

```sh
uv run calibrate --sliding 0.20 --press 0.10 --nut good --inserts straight \\
                 --holes 3=2.86,5=4.88,8=7.90 --printer "Prusa MK4, Prusament PETG"
uv run calibrate --help    # what each option does; --dry-run shows the change first
```

The dovetail result sets the sliding fit for rails if it differs from the peg's; the
calibrate script reports it but rails use `sliding_fit` until a part needs otherwise.
"""


PART = PartSpec(
    slug="calibration_coupon",
    number=0,
    title="Calibration coupon",
    tagline="One 58 mm print that measures your printer's real fits, so every part fits.",
    problem=(
        "Every printer and filament prints holes a little small and pegs a little big. "
        "Clearances guessed for someone else's printer make press fits loose and slides stick."
    ),
    innovation=(
        "Each fit the library uses — sliding, press, captive nut, heat-set insert, horizontal "
        "teardrop hole, dovetail rail — on one small plate with a matching key. You write down "
        "what fits; `uv run calibrate` writes it into `core/tolerances.py` and every part "
        "regenerates with your printer's numbers."
    ),
    material=MaterialName.PETG,
    orientation=(
        "Flat on the bed, like the parts it calibrates: holes vertical, teardrops horizontal, "
        "dovetail undercuts at the 45° limit."
    ),
    params_model=CouponParams,
    presets=PRESETS,
    build=build,
    describe=describe,
    extra_readme=FORM,
)
