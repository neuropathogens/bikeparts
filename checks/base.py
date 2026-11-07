"""Shared types for printability checks.

A `Body` is one printable solid, already print-oriented (+Z build direction, bed at Z = 0).
Checks get both the exact B-rep (for hole/face classification) and a triangle mesh
(for ray casting and mesh topology), tessellated once and cached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from functools import cached_property
from typing import Any, Protocol

import build123d as bd
import numpy as np
import trimesh

from bikeparts.core.features import ExemptRegion

# Linear tessellation tolerance (mm) shared by every mesh-based check and STL export.
MESH_TOLERANCE = 0.01
MESH_ANGULAR_TOLERANCE = 0.1  # radians


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WAIVED = "WAIVED"  # failed, but the part's README carries a written exception


@dataclass
class CheckResult:
    check: str
    status: Status
    summary: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status is not Status.FAIL


@dataclass
class Body:
    name: str
    shape: bd.Part | bd.Solid | bd.Compound
    exempt: tuple[ExemptRegion, ...] = ()

    def exempt_box(self, check: str, lo: bd.Vector, hi: bd.Vector) -> bool:
        return any(check in r.checks and r.contains_box(lo, hi) for r in self.exempt)

    def exempt_points(self, check: str, pts: np.ndarray) -> np.ndarray:
        """Boolean mask of points inside a region exempt from `check`."""
        mask = np.zeros(len(pts), dtype=bool)
        for r in self.exempt:
            if check in r.checks:
                lo, hi = np.array(r.lo) - 1e-3, np.array(r.hi) + 1e-3
                mask |= np.all((pts >= lo) & (pts <= hi), axis=1)
        return mask

    @cached_property
    def mesh(self) -> trimesh.Trimesh:
        verts, tris = self.shape.tessellate(MESH_TOLERANCE, MESH_ANGULAR_TOLERANCE)
        v = np.array([(p.X, p.Y, p.Z) for p in verts], dtype=float)
        f = np.array(tris, dtype=np.int64)
        m = trimesh.Trimesh(vertices=v, faces=f, process=True)
        m.merge_vertices(digits_vertex=6)
        return m


class Check(Protocol):
    name: str

    def __call__(self, body: Body) -> CheckResult: ...


def face_triangles(face: bd.Face) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tessellate one B-rep face → (centroids, unit normals, areas) per triangle.

    Normals point out of the solid (build123d accounts for reversed face orientation).
    """
    verts, tris = face.tessellate(MESH_TOLERANCE, MESH_ANGULAR_TOLERANCE)
    if not tris:
        empty = np.zeros((0, 3))
        return empty, empty, np.zeros(0)
    v = np.array([(p.X, p.Y, p.Z) for p in verts], dtype=float)
    t = np.array(tris, dtype=np.int64)
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    cross = np.cross(b - a, c - a)
    norm = np.linalg.norm(cross, axis=1)
    keep = norm > 1e-12
    normals = cross[keep] / norm[keep, None]
    return (a + b + c)[keep] / 3.0, normals, norm[keep] / 2.0
