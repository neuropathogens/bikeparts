"""Gate 1: horizontal holes over 3 mm must be teardrop (or diamond) shaped (print rule 2).

A round hole is detected as a concave cylindrical face, with its axis within 45° of
horizontal, whose surface includes the hole's topmost line. A teardrop's cylindrical
face stops at the 45° tangent points, so it never covers the top.
"""

from __future__ import annotations

from checks.base import Body, CheckResult, Status
from checks.geometry import cylinder_info

name = "hole_orientation"

# source: docs/PLAN.md print rule 2
MAX_ROUND_HOLE_MM = 3.0


def check(body: Body) -> CheckResult:
    offenders: list[dict[str, object]] = []
    horizontal_holes = 0
    for face in body.shape.faces():
        cyl = cylinder_info(face)
        if cyl is None or not cyl.concave or not cyl.is_horizontal:
            continue
        horizontal_holes += 1
        if cyl.diameter > MAX_ROUND_HOLE_MM + 1e-6 and cyl.covers_top:
            c = face.center()
            offenders.append(
                {
                    "diameter_mm": round(cyl.diameter, 3),
                    "axis": [round(float(x), 3) for x in cyl.axis_dir],
                    "at": [round(c.X, 2), round(c.Y, 2), round(c.Z, 2)],
                }
            )
    details = {"horizontal_hole_faces": horizontal_holes, "round_top_holes": offenders}
    if offenders:
        ds = ", ".join(f"Ø{o['diameter_mm']}" for o in offenders)
        return CheckResult(
            name,
            Status.FAIL,
            f"{len(offenders)} horizontal hole(s) > {MAX_ROUND_HOLE_MM:.0f} mm "
            f"with a round top: {ds}",
            details,
        )
    return CheckResult(
        name,
        Status.PASS,
        f"{horizontal_holes} horizontal hole face(s), none round-topped > 3 mm",
        details,
    )
