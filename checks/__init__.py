"""Printability and structural analyzers. Each module exposes `name` and `check(body)`."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from checks import bed_fit, hole_orientation, min_wall, overhang, watertight
from checks.base import Body, CheckResult, Status

ALL_CHECKS: dict[str, Callable[[Body], CheckResult]] = {
    m.name: m.check for m in (watertight, bed_fit, overhang, min_wall, hole_orientation)
}


def run_checks(body: Body, exceptions: Mapping[str, str] | None = None) -> list[CheckResult]:
    """Run every check. A failing check named in `exceptions` is WAIVED with that reason."""
    exceptions = exceptions or {}
    unknown = set(exceptions) - set(ALL_CHECKS)
    if unknown:
        raise ValueError(f"exceptions name unknown checks: {sorted(unknown)}")
    results = []
    for check_name, fn in ALL_CHECKS.items():
        try:
            r = fn(body)
        except Exception as exc:  # a crashing check is a failing check
            r = CheckResult(check_name, Status.FAIL, f"check crashed: {exc!r}")
        if r.status is Status.FAIL and check_name in exceptions:
            r = CheckResult(
                check_name,
                Status.WAIVED,
                f"{r.summary} — waived: {exceptions[check_name]}",
                r.details,
            )
        results.append(r)
    return results


__all__ = ["ALL_CHECKS", "Body", "CheckResult", "Status", "run_checks"]
