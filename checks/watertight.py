"""Gate 1: the body is one valid closed solid and its mesh is watertight."""

from __future__ import annotations

from checks.base import Body, CheckResult, Status

name = "watertight"


def check(body: Body) -> CheckResult:
    shape = body.shape
    n_solids = len(shape.solids())
    valid = bool(shape.is_valid)
    m = body.mesh
    problems: list[str] = []
    if not valid:
        problems.append("B-rep is not valid")
    if n_solids != 1:
        problems.append(f"{n_solids} solids (expected exactly 1 per printable body)")
    if not m.is_watertight:
        problems.append("mesh has open edges")
    if not m.is_winding_consistent:
        problems.append("mesh winding inconsistent")
    if m.volume <= 0:
        problems.append(f"mesh volume {m.volume:.1f} mm³ (inside-out?)")
    details = {
        "brep_valid": valid,
        "solids": n_solids,
        "mesh_watertight": bool(m.is_watertight),
        "volume_mm3": round(float(m.volume), 2),
        "triangles": len(m.faces),
    }
    if problems:
        return CheckResult(name, Status.FAIL, "; ".join(problems), details)
    return CheckResult(name, Status.PASS, f"1 solid, watertight, {m.volume:,.0f} mm³", details)
