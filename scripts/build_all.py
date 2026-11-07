"""`uv run build` — export STEP, STL, 3MF and an SVG drawing for every part preset body.

Output: out/<part>/<preset>/<body>.{step,stl,3mf,svg}. Nothing in out/ is hand-edited;
rerun this to regenerate it.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time

import build123d as bd

from checks.base import MESH_ANGULAR_TOLERANCE, MESH_TOLERANCE
from scripts.common import OUT, Target, fixture_targets, part_targets, select_parts
from scripts.render import write_drawing


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="build", description=__doc__)
    ap.add_argument("--part", action="append", help="only this part slug (repeatable)")
    ap.add_argument("--fixture", action="append", default=[], help="also export a test fixture")
    ap.add_argument("--clean", action="store_true", help="delete out/ first")
    args = ap.parse_args(argv)

    if args.clean and OUT.exists():
        shutil.rmtree(OUT)
    specs = select_parts(args.part)
    targets = [*part_targets(specs), *fixture_targets(args.fixture)]
    if not targets:
        print("No parts registered yet (src/bikeparts/parts/<slug>/part.py). Nothing to build.")
        return 0
    failed = 0
    for t in targets:
        t0 = time.perf_counter()
        try:
            files = export(t)
            print(f"  built  {t.label:<50} {', '.join(files)}  ({time.perf_counter() - t0:.1f}s)")
        except Exception as exc:
            failed += 1
            print(f"  FAILED {t.label:<50} {exc!r}", file=sys.stderr)
    print(f"\n{len(targets) - failed}/{len(targets)} bodies exported to {OUT}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
