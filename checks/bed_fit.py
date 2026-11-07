"""Gate 1: fits a 220 × 220 × 250 mm build volume and sits on the bed at Z = 0."""

from __future__ import annotations

from checks.base import Body, CheckResult, Status
from checks.geometry import is_bed_face

name = "bed_fit"

# source: docs/PLAN.md print rule 6 and Gate 1 (220 × 220 × 250 mm build volume)
BED_X = 220.0
BED_Y = 220.0
BED_Z = 250.0
_Z_TOL = 1e-3


def check(body: Body) -> CheckResult:
    bb = body.shape.bounding_box()
    sx, sy, sz = bb.size.X, bb.size.Y, bb.size.Z
    contact = sum(f.area for f in body.shape.faces() if is_bed_face(f))
    problems: list[str] = []
    if sx > BED_X or sy > BED_Y:
        problems.append(f"footprint {sx:.1f} × {sy:.1f} exceeds {BED_X:.0f} × {BED_Y:.0f}")
    if sz > BED_Z:
        problems.append(f"height {sz:.1f} exceeds {BED_Z:.0f}")
    if abs(bb.min.Z) > _Z_TOL:
        problems.append(f"lowest point at Z = {bb.min.Z:.3f}, not on the bed (Z = 0)")
    if contact <= 0:
        problems.append("no flat face on the bed at Z = 0")
    details = {
        "size_mm": [round(sx, 2), round(sy, 2), round(sz, 2)],
        "min_z": round(bb.min.Z, 4),
        "bed_contact_mm2": round(contact, 1),
    }
    summary = f"{sx:.1f} × {sy:.1f} × {sz:.1f} mm, {contact:,.0f} mm² on bed"
    if problems:
        return CheckResult(name, Status.FAIL, "; ".join(problems), details)
    return CheckResult(name, Status.PASS, summary, details)
