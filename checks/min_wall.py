"""Gate 1: no wall under 1.2 mm, by ray-cast sampling.

Points are sampled uniformly by area over the surface; from each, a ray is cast inward
along the surface normal and the distance to the first surface it meets is the local wall
thickness. The thin area is estimated as (thin samples / samples) × total surface area.
"""

from __future__ import annotations

import numpy as np
import trimesh

from bikeparts.core.tolerances import MIN_WALL
from checks.base import Body, CheckResult, Status

name = "min_wall"

SAMPLES = 4000
# Tessellation chords are inside the true surface; allow that much before flagging.
THICKNESS_EPS = 0.02
# Thin area tolerated before failing — absorbs sampling noise at knife-edge corners.
MAX_THIN_AREA_MM2 = 0.5
_OFFSET = 1e-4


# A hit on a triangle nearly parallel to the ray is a graze along the face next to the
# sample's edge (tessellation chords sit a hair inside the true surface), not a wall.
GRAZE_COS = 0.25  # ≈ 14.5°: real thin walls are hit near head-on (or at 45° in a wedge)


def measure(mesh: trimesh.Trimesh, samples: int = SAMPLES, seed: int = 0) -> np.ndarray:
    """Return rows of (x, y, z, thickness) sampled over the mesh; thickness is inf on a miss."""
    sampled = trimesh.sample.sample_surface(mesh, samples, seed=seed)
    pts, tri_idx = np.asarray(sampled[0]), np.asarray(sampled[1])
    normals = mesh.face_normals[tri_idx]
    origins = pts - normals * _OFFSET
    dirs = -normals
    hits = mesh.ray.intersects_location(origins, dirs, multiple_hits=True)
    locs, ray_idx, hit_tri = np.asarray(hits[0]), np.asarray(hits[1]), np.asarray(hits[2])
    thick = np.full(len(pts), np.inf)
    if len(ray_idx):
        facing = np.abs(np.einsum("ij,ij->i", dirs[ray_idx], mesh.face_normals[hit_tri]))
        ok = facing >= GRAZE_COS
        d = np.linalg.norm(locs - origins[ray_idx], axis=1) + _OFFSET
        np.minimum.at(thick, ray_idx[ok], d[ok])
    return np.column_stack([pts, thick])


def check(body: Body, min_wall: float = MIN_WALL) -> CheckResult:
    m = body.mesh
    data = measure(m)
    keep = ~body.exempt_points(name, data[:, :3])
    data = data[keep]
    thick = data[:, 3]
    hit = np.isfinite(thick)
    thin = hit & (thick < min_wall - THICKNESS_EPS)
    # each kept sample still represents total_area / SAMPLES of surface
    thin_area = float(thin.sum()) / len(keep) * float(m.area)
    tmin = float(thick[hit].min()) if hit.any() else float("nan")
    at = data[np.argmin(np.where(hit, thick, np.inf)), :3]
    details = {
        "min_thickness_mm": round(tmin, 3),
        "thin_area_mm2": round(thin_area, 2),
        "samples": len(thick),
        "misses": int((~hit).sum()),
        "exempt_samples": int((~keep).sum()),
        "thinnest_at": [round(float(x), 2) for x in at],
        "threshold_mm": min_wall,
    }
    if thin_area > MAX_THIN_AREA_MM2:
        return CheckResult(
            name,
            Status.FAIL,
            f"~{thin_area:,.1f} mm² of wall under {min_wall} mm "
            f"(thinnest {tmin:.2f} mm near {details['thinnest_at']})",
            details,
        )
    return CheckResult(name, Status.PASS, f"thinnest sampled wall {tmin:.2f} mm", details)
