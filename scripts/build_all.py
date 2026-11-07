"""`uv run build` — export STEP, STL, 3MF and an SVG drawing for every part preset body,
slice each with PrusaSlicer for grams and print time, and regenerate each part's README.

Output: out/<part>/<preset>/<body>.{step,stl,3mf,svg} and src/bikeparts/parts/<part>/
README.md + drawings/. Nothing generated is hand-edited; rerun this to regenerate it.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time

import build123d as bd

from bikeparts.parts import PartSpec
from checks import Body, run_checks
from checks.base import MESH_ANGULAR_TOLERANCE, MESH_TOLERANCE
from scripts.common import OUT, REPO, Target, fixture_targets, preset_targets, select_parts
from scripts.make_readme import BodyResult
from scripts.make_readme import write as write_readme
from scripts.render import write_drawing
from scripts.slice import slice_stl, slicer_path


def export(t: Target) -> list[str]:
    d = t.out_dir
    d.mkdir(parents=True, exist_ok=True)
    stem = d / t.body
    bd.export_step(t.shape, str(stem.with_suffix(".step")))
    bd.export_stl(t.shape, str(stem.with_suffix(".stl")), MESH_TOLERANCE, MESH_ANGULAR_TOLERANCE)
    mesher = bd.Mesher()
    mesher.add_shape(
        t.shape, linear_deflection=MESH_TOLERANCE, angular_deflection=MESH_ANGULAR_TOLERANCE
    )
    mesher.write(str(stem.with_suffix(".3mf")))
    write_drawing(t.shape, stem.with_suffix(".svg"), f"{t.slug} — {t.body}", f"preset {t.preset}")
    return [p.name for p in sorted(d.glob(f"{t.body}.*"))]


def build_part(spec: PartSpec, slice_it: bool, readme: bool) -> int:
    failed = 0
    results: dict[str, list[BodyResult]] = {}
    for preset in spec.presets:
        rows: list[BodyResult] = []
        for t in preset_targets(spec, preset):
            t0 = time.perf_counter()
            try:
                files = export(t)
                sliced = (
                    slice_stl(t.out_dir / f"{t.body}.stl", t.material, t.slicer)
                    if slice_it
                    else None
                )
                checks = run_checks(Body(t.body, t.shape, t.exempt), t.exceptions)
                rows.append(BodyResult(t, sliced, checks))
                extra = f"  {sliced.grams:.1f} g, {sliced.time}" if sliced else ""
                print(
                    f"  built  {t.label:<45} {', '.join(files)}{extra}  ({time.perf_counter() - t0:.1f}s)"
                )
            except Exception as exc:
                failed += 1
                print(f"  FAILED {t.label:<45} {exc!r}", file=sys.stderr)
        results[preset] = rows
    if readme and not failed:
        d = spec.default_preset
        drawings = {r.target.body: r.target.out_dir / f"{r.target.body}.svg" for r in results[d]}
        path = write_readme(spec, results, drawings)
        print(f"  readme {path.relative_to(REPO)}")
    return failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="build", description=__doc__)
    ap.add_argument("--part", action="append", help="only this part slug (repeatable)")
    ap.add_argument("--fixture", action="append", default=[], help="also export a test fixture")
    ap.add_argument("--clean", action="store_true", help="delete out/ first")
    ap.add_argument("--no-slice", action="store_true", help="skip PrusaSlicer grams/time")
    ap.add_argument("--no-readme", action="store_true", help="don't regenerate part READMEs")
    args = ap.parse_args(argv)

    if args.clean and OUT.exists():
        shutil.rmtree(OUT)
    specs = select_parts(args.part)
    slice_it = not args.no_slice and slicer_path() is not None
    if not args.no_slice and not slice_it:
        print("PrusaSlicer not found (set PRUSASLICER=…): READMEs will have no grams/time.")
    failed = 0
    for spec in specs:
        print(f"\n{spec.slug}")
        failed += build_part(spec, slice_it, readme=not args.no_readme)
    fixtures = list(fixture_targets(args.fixture))
    for t in fixtures:
        try:
            files = export(t)
            print(f"  built  {t.label:<45} {', '.join(files)}")
        except Exception as exc:
            failed += 1
            print(f"  FAILED {t.label:<45} {exc!r}", file=sys.stderr)
    if not specs and not fixtures:
        print("No parts registered yet (src/bikeparts/parts/<slug>/part.py). Nothing to build.")
        return 0
    print(f"\n{'FAILED: ' + str(failed) + ' bodies' if failed else 'all bodies exported'} → {OUT}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
