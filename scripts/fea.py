"""`uv run fea` — Gate 2 FEA screen for every part that declares load cases.

    uv run fea                       all Gate 2 parts, default preset, both mesh sizes
    uv run fea --part bar_end_vault  one part
    uv run fea --quick               coarse mesh only (no refinement run)

Writes src/bikeparts/parts/<part>/fea/results.json and a stress plot per case, which the
part README shows. Exit code 1 if any case's safety factor is under 3 (structural rule 7).
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from bikeparts.core.materials import MATERIALS, MIN_SAFETY_FACTOR
from checks.fea import DEFAULT_H, REFINED_H, FeaError, plot, solve_case
from scripts.common import PARTS_SRC, select_parts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fea", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", action="append", help="only this part slug (repeatable)")
    ap.add_argument("--quick", action="store_true", help="skip the refined-mesh run")
    args = ap.parse_args(argv)

    specs = [s for s in select_parts(args.part) if s.load_cases is not None]
    if not specs:
        print("No parts declare load cases.")
        return 0
    failed = 0
    for spec in specs:
        preset = spec.default_preset
        params = spec.presets[preset]
        bodies = spec.build(params)
        out_dir = PARTS_SRC / spec.slug / "fea"
        out_dir.mkdir(exist_ok=True)
        records = []
        assert spec.load_cases is not None
        for case in spec.load_cases(params):
            pb = bodies[case.body]
            material = MATERIALS[pb.material]
            t0 = time.perf_counter()
            try:
                coarse = solve_case(pb.shape, case, material, DEFAULT_H)
                fine = None if args.quick else solve_case(pb.shape, case, material, REFINED_H)
            except FeaError as exc:
                failed += 1
                print(f"  ERROR  {spec.slug}/{case.name}: {exc}")
                continue
            res = fine or coarse
            plot(res, out_dir / f"{case.name}.png")
            change = (fine.governing / coarse.governing - 1) * 100 if fine else None
            ok = res.passes
            failed += not ok
            records.append(
                {
                    "case": case.name,
                    "description": case.description,
                    "source": case.source,
                    "body": case.body,
                    "material": str(material.name),
                    "material_verified": material.verified,
                    "design_strength_mpa": round(res.design_strength, 2),
                    "max_von_mises_mpa": round(res.max_vm, 2),
                    "raw_max_von_mises_mpa": round(res.raw_max_vm, 2),
                    "bearing_mpa": round(res.bearing, 2),
                    "contact_peak_mpa": round(res.contact_peak, 2),
                    "governing_mpa": round(res.governing, 2),
                    "p99_von_mises_mpa": round(res.p99_vm, 2),
                    "at_mm": [round(v, 2) for v in res.at],
                    "max_displacement_mm": round(res.max_disp, 4),
                    "safety_factor": round(res.safety_factor, 2),
                    "passes": ok,
                    "mesh_h_mm": res.h,
                    "tets": res.n_tets,
                    "coarse_governing_mpa": round(coarse.governing, 2),
                    "mesh_change_pct": None if change is None else round(change, 1),
                    "preset": preset,
                }
            )
            mark = "PASS" if ok else "FAIL"
            delta = f", {change:+.0f}% vs coarse mesh" if change is not None else ""
            print(
                f"  {mark}   {spec.slug}/{case.name:<13} vm {res.max_vm:5.2f} bearing "
                f"{res.bearing:5.2f} (raw peak {res.raw_max_vm:5.2f}) MPa  SF {res.safety_factor:4.1f} "
                f"[{res.n_tets} tets{delta}]  {time.perf_counter() - t0:.0f}s"
            )
        (out_dir / "results.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(
        f"\nGate 2: {'all cases SF ≥ ' + str(MIN_SAFETY_FACTOR) if not failed else str(failed) + ' case(s) failing'}"
        " — material values are typical, not your filament's datasheet (verified=False)."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
