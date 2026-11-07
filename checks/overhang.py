"""Gate 1: zero unsupported overhang beyond 45° from vertical (print rule 1).

Measured per B-rep face on its tessellation. A surface's overhang angle is its tilt from
vertical, i.e. 90° minus the angle between its outward normal and -Z: a vertical wall is
0°, a flat ceiling is 90°. Anything beyond 45° needs support and is reported as area.

Not counted:
- the bed face (planar, facing -Z, at Z = 0);
- flat ceilings whose shorter side is ≤ 10 mm — bridges (rule 1), listed separately;
- horizontal round holes ≤ 3 mm, which rule 2 explicitly allows without a teardrop.
"""

from __future__ import annotations

import math

import numpy as np

from checks.base import Body, CheckResult, Status, face_triangles
from checks.geometry import cylinder_info, is_bed_face, vertical_cone_tilt_deg

name = "overhang"

# source: docs/PLAN.md print rule 1
MAX_OVERHANG_DEG = 45.0
# source: docs/PLAN.md print rule 1
MAX_BRIDGE_MM = 10.0
# source: docs/PLAN.md print rule 2
SMALL_HOLE_MM = 3.0
# Numerical slack so an exact 45° chamfer/teardrop flank isn't flagged by float noise.
ANGLE_EPS_DEG = 0.5


def check(body: Body) -> CheckResult:
    flagged_area = 0.0
    worst = 0.0
    regions: list[dict[str, object]] = []
    bridges: list[dict[str, object]] = []
    exempt_small_holes = 0
    limit = math.radians(MAX_OVERHANG_DEG + ANGLE_EPS_DEG)

    for face in body.shape.faces():
        if is_bed_face(face):
            continue
        cyl = cylinder_info(face)
        if (
            cyl is not None
            and cyl.concave
            and cyl.is_horizontal
            and cyl.diameter <= SMALL_HOLE_MM + 1e-6
        ):
            exempt_small_holes += 1
            continue
        cone_tilt = vertical_cone_tilt_deg(face)
        if cone_tilt is not None and cone_tilt <= MAX_OVERHANG_DEG + ANGLE_EPS_DEG:
            continue  # exact surface angle is within the limit (e.g. a 45° bed chamfer)
        n = face.normal_at() if face.geom_type.name == "PLANE" else None
        if n is not None and n.Z < -0.999:
            bb = face.bounding_box()
            span = min(bb.size.X, bb.size.Y)
            if span <= MAX_BRIDGE_MM:
                bridges.append(
                    {
                        "span_mm": round(span, 2),
                        "z": round(bb.min.Z, 2),
                        "area_mm2": round(face.area, 1),
                    }
                )
                continue

        centroids, normals, areas = face_triangles(face)
        if len(areas) == 0:
            continue
        # overhang angle from vertical = asin(-nz) for downward-facing triangles
        ang = np.arcsin(np.clip(-normals[:, 2], -1.0, 1.0))
        bad = ang > limit
        if not bad.any():
            continue
        area = float(areas[bad].sum())
        face_worst = math.degrees(float(ang[bad].max()))
        worst = max(worst, face_worst)
        flagged_area += area
        c = (centroids[bad] * areas[bad, None]).sum(axis=0) / areas[bad].sum()
        regions.append(
            {
                "max_angle_deg": round(face_worst, 1),
                "area_mm2": round(area, 1),
                "at": [round(float(x), 2) for x in c],
                "surface": face.geom_type.name.lower(),
            }
        )

    regions.sort(key=lambda r: -float(r["area_mm2"]))  # type: ignore[arg-type]
    details = {
        "overhang_area_mm2": round(flagged_area, 1),
        "worst_angle_deg": round(worst, 1),
        "regions": regions,
        "bridges": bridges,
        "exempt_small_holes": exempt_small_holes,
    }
    if flagged_area > 0:
        return CheckResult(
            name,
            Status.FAIL,
            f"{flagged_area:,.1f} mm² overhangs beyond {MAX_OVERHANG_DEG:.0f}° "
            f"(worst {worst:.1f}° from vertical, {len(regions)} region(s))",
            details,
        )
    extra = f", {len(bridges)} bridge(s) ≤ {MAX_BRIDGE_MM:.0f} mm" if bridges else ""
    return CheckResult(name, Status.PASS, f"0 mm² beyond {MAX_OVERHANG_DEG:.0f}°{extra}", details)
