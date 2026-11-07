"""`uv run check` — run every printability check on every part preset body (Gate 1).

    uv run check                         all registered parts (+ parametric sweeps)
    uv run check --part spine_mount      one part
    uv run check --fixture overhang_cube_60
    uv run check --self-test             every fixture must fail exactly its expected checks

Exit code is non-zero if any check fails (WAIVED counts as passing; the waiver text must
also be in the part's README).
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from bikeparts.fixtures import FIXTURES
from checks import Body, CheckResult, Status, run_checks
from scripts.common import OUT, Target, fixture_targets, part_targets, select_parts

_MARK = {Status.PASS: "PASS  ", Status.FAIL: "FAIL  ", Status.WAIVED: "WAIVED"}


def _print_results(t: Target, results: list[CheckResult], verbose: bool) -> None:
    print(f"\n{t.label}")
    for r in results:
        print(f"  {_MARK[r.status]} {r.check:<17} {r.summary}")
        if r.status is not Status.PASS and verbose:
            for k, v in r.details.items():
                if v in ([], {}, None):
                    continue
                print(f"           {k}: {json.dumps(v)}")


def _sweep(specs: list) -> int:
    failed = 0
    for spec in specs:
        if spec.sweep is None:
            continue
        n = 0
        for params in spec.sweep():
            n += 1
            try:
                for body, shape in spec.build(params).items():
                    if not shape.is_valid or len(shape.solids()) != 1:
                        raise ValueError(f"{body}: invalid or not a single solid")
            except Exception as exc:
                failed += 1
                print(f"  FAIL   sweep {spec.slug} {params!r}: {exc!r}")
        print(f"  sweep  {spec.slug}: {n - failed}/{n} parameter sets build")
    return failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="check", description=__doc__)
    ap.add_argument("--part", action="append", help="only this part slug (repeatable)")
    ap.add_argument("--fixture", action="append", default=[], help="check a test fixture")
    ap.add_argument("--self-test", action="store_true", help="verify every fixture's outcome")
    ap.add_argument("--no-sweep", action="store_true", help="skip parametric sweeps")
    ap.add_argument("-q", "--quiet", action="store_true", help="no per-region details")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    specs = [] if args.fixture and not args.part else select_parts(args.part)
    targets = [*part_targets(specs), *fixture_targets(args.fixture)]
    if not targets:
        print("No parts registered yet (src/bikeparts/parts/<slug>/part.py). Nothing to check.")
        return 0

    report: dict[str, list[dict[str, object]]] = {}
    failures = 0
    for t in targets:
        results = run_checks(Body(t.body, t.shape), t.exceptions)
        _print_results(t, results, verbose=not args.quiet)
        failures += sum(not r.ok for r in results)
        report[t.label] = [
            {"check": r.check, "status": r.status.value, "summary": r.summary, "details": r.details}
            for r in results
        ]
    if not args.no_sweep and specs:
        print()
        failures += _sweep(specs)

    OUT.mkdir(exist_ok=True)
    (OUT / "check-report.json").write_text(json.dumps(report, indent=2))
    n = sum(len(v) for v in report.values())
    print(
        f"\n{n - failures}/{n} checks passed on {len(targets)} bodies"
        + (" — FAILED" if failures else "")
    )
    return 1 if failures else 0


def _self_test() -> int:
    """Each fixture must fail exactly the checks it was built to fail — no more, no less."""
    bad = 0
    t0 = time.perf_counter()
    for t in fixture_targets(sorted(FIXTURES)):
        results = run_checks(Body(t.body, t.shape))
        failed = {r.check for r in results if r.status is Status.FAIL}
        expected = set(t.expect_fail or ())
        ok = failed == expected
        bad += not ok
        exp = ", ".join(sorted(expected)) or "nothing"
        print(f"  {'ok ' if ok else 'BAD'} {t.label:<38} expected to fail: {exp}")
        if not ok:
            for r in results:
                print(f"        {_MARK[r.status]} {r.check:<17} {r.summary}")
    print(
        f"\nself-test: {'all fixtures behave' if not bad else f'{bad} fixture(s) misbehave'} "
        f"({time.perf_counter() - t0:.1f}s)"
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
