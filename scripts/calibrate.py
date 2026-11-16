"""`uv run calibrate` — write the calibration coupon's results into core/tolerances.py.

Fill in the coupon's measurement form (src/bikeparts/parts/calibration_coupon/README.md),
then pass what you found. Only the options you give change; the rest keep their values.

    uv run calibrate --sliding 0.20 --press 0.10 --nut good --inserts straight \\
                     --holes 3=2.86,5=4.88,8=7.90 --printer "Prusa MK4, Prusament PETG"

Then `uv run build` regenerates every part with the new clearances.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import re
import sys
from pathlib import Path

from bikeparts.core import tolerances as tol_mod
from bikeparts.core.tolerances import Tolerances

TOLERANCES_PY = Path(tol_mod.__file__)
_BLOCK = re.compile(r"(# --- calibrate:begin[^\n]*\n)(.*?)(# --- calibrate:end ---)", re.DOTALL)
# source: assumption — one coupon judgement ("tight", "loose") moves a fit by this much
NUT_STEP = {"tight": +0.10, "good": 0.0, "loose": -0.05}
INSERT_STEP = {"tight": +0.05, "straight": 0.0, "loose": -0.05}


def _round05(x: float) -> float:
    """Round up to the next 0.05 mm (fits err toward clearance)."""
    return math.ceil(round(x / 0.05, 6)) * 0.05


def hole_extra(measured: dict[float, float]) -> float:
    """Per-side extra for horizontal holes from nominal→measured diameters."""
    shrink = [(nom - got) / 2 for nom, got in measured.items()]
    return max(0.0, _round05(sum(shrink) / len(shrink)))


def parse_holes(text: str) -> dict[float, float]:
    out: dict[float, float] = {}
    for item in text.split(","):
        nom, _, got = item.partition("=")
        if not got:
            raise argparse.ArgumentTypeError(f"--holes wants NOMINAL=MEASURED, got {item!r}")
        out[float(nom)] = float(got)
    return out


def new_values(current: Tolerances, args: argparse.Namespace) -> Tolerances:
    v = current.model_dump()
    if args.sliding is not None:
        v["sliding_fit"] = args.sliding
    if args.press is not None:
        v["press_fit"] = args.press
    if args.nut is not None:
        v["nut_pocket_flats"] = round(current.nut_pocket_flats + NUT_STEP[args.nut], 2)
    if args.nut_flats is not None:
        v["nut_pocket_flats"] = args.nut_flats
    if args.inserts is not None:
        v["insert_pocket_extra"] = round(current.insert_pocket_extra + INSERT_STEP[args.inserts], 2)
    if args.holes is not None:
        v["bolt_hole_extra"] = round(hole_extra(args.holes), 2)
    new = Tolerances(**v)  # validates ranges
    if new.press_fit >= new.sliding_fit:
        raise SystemExit("press fit must be tighter (smaller) than the sliding fit")
    return new


def render_block(t: Tolerances, note: str) -> str:
    lines = [f"# {note}\n"] if note else []
    lines.append("PRINTER = Tolerances(\n")
    for name in Tolerances.model_fields:
        lines.append(f"    {name}={getattr(t, name)!r},\n")
    lines.append(")\n")
    return "".join(lines)


def update_source(source: str, t: Tolerances, note: str) -> str:
    m = _BLOCK.search(source)
    if not m:
        raise SystemExit("calibrate:begin/end markers not found in tolerances.py")
    return source[: m.start(2)] + render_block(t, note) + source[m.end(2) :]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="calibrate", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--sliding",
        type=float,
        help="smallest ladder hole the peg slides through freely (mm per side)",
    )
    ap.add_argument(
        "--press", type=float, help="smallest ladder hole the peg presses into firmly (mm per side)"
    )
    ap.add_argument("--nut", choices=sorted(NUT_STEP), help="how the M4 nut fit its pocket")
    ap.add_argument(
        "--nut-flats", type=float, help="set the nut-pocket allowance directly (mm across flats)"
    )
    ap.add_argument(
        "--inserts", choices=sorted(INSERT_STEP), help="how the heat-set inserts went in"
    )
    ap.add_argument(
        "--holes",
        type=parse_holes,
        help="teardrop holes NOMINAL=MEASURED, e.g. 3=2.86,5=4.88,8=7.9",
    )
    ap.add_argument(
        "--dovetail", type=float, help="tightest dovetail that slid full length (recorded only)"
    )
    ap.add_argument("--printer", default="", help="printer and filament, recorded in tolerances.py")
    ap.add_argument("--dry-run", action="store_true", help="show the change without writing it")
    args = ap.parse_args(argv)

    current = tol_mod.PRINTER
    new = new_values(current, args)
    note = f"calibrated {dt.date.today().isoformat()}" + (
        f" on {args.printer}" if args.printer else ""
    )
    if args.dovetail is not None:
        note += f"; dovetail slid at {args.dovetail:.2f}"
    for name in Tolerances.model_fields:
        a, b = getattr(current, name), getattr(new, name)
        mark = "→" if a != b else " "
        print(f"  {name:<20} {a:>6} {mark} {b}")
    if args.dovetail is not None and abs(args.dovetail - new.sliding_fit) > 0.051:
        print(
            f"  note: dovetail fit {args.dovetail:.2f} differs from sliding_fit {new.sliding_fit:.2f}"
        )
    if args.dry_run:
        print("dry run: tolerances.py not changed")
        return 0
    src = TOLERANCES_PY.read_text(encoding="utf-8")
    TOLERANCES_PY.write_text(update_source(src, new, note), encoding="utf-8")
    print(f"wrote {TOLERANCES_PY}. Now run `uv run build` to regenerate the parts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
