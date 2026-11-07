"""B-rep face classification shared by the overhang and hole_orientation checks."""

from __future__ import annotations

import math
from dataclasses import dataclass

import build123d as bd
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface  # pyright: ignore[reportAttributeAccessIssue]
from OCP.GeomAbs import (
    GeomAbs_Cone,  # pyright: ignore[reportAttributeAccessIssue]
    GeomAbs_Cylinder,  # pyright: ignore[reportAttributeAccessIssue]
)

# Axes within this angle of horizontal count as "horizontal holes" (their ceilings sag).
HORIZONTAL_AXIS_MAX_TILT_DEG = 45.0


@dataclass(frozen=True)
class CylinderInfo:
    radius: float
    axis_origin: np.ndarray
    axis_dir: np.ndarray
    concave: bool  # True → a hole (solid surrounds the axis), False → a boss / round
    covers_top: bool  # the face includes the topmost line of the cylinder (round ceiling)
    tilt_deg: float  # axis angle above horizontal

    @property
    def diameter(self) -> float:
        return 2 * self.radius

    @property
    def is_horizontal(self) -> bool:
        return self.tilt_deg < HORIZONTAL_AXIS_MAX_TILT_DEG


def cylinder_info(face: bd.Face) -> CylinderInfo | None:
    """Describe a cylindrical face, or None if the face is not a cylinder."""
    adaptor = BRepAdaptor_Surface(face.wrapped)
    if adaptor.GetType() != GeomAbs_Cylinder:
        return None
    cyl = adaptor.Cylinder()
    pos = cyl.Position()
    loc = pos.Location()
    xd, yd, zd = pos.XDirection(), pos.YDirection(), pos.Direction()
    origin = np.array([loc.X(), loc.Y(), loc.Z()])
    x_dir = np.array([xd.X(), xd.Y(), xd.Z()])
    y_dir = np.array([yd.X(), yd.Y(), yd.Z()])
    axis = np.array([zd.X(), zd.Y(), zd.Z()])
    r = cyl.Radius()
    tilt = math.degrees(math.asin(min(1.0, abs(float(axis[2])))))

    # Concavity: at the mid-parameter point, does the outward normal point at the axis?
    p = face.position_at(0.5, 0.5)
    n = face.normal_at(0.5, 0.5)
    pt = np.array([p.X, p.Y, p.Z])
    radial = pt - origin
    radial -= axis * float(np.dot(radial, axis))
    concave = float(np.dot(radial, np.array([n.X, n.Y, n.Z]))) < 0

    # "Up" in the hole's cross-section: +Z projected onto the plane ⟂ axis.
    up = np.array([0.0, 0.0, 1.0]) - axis * float(axis[2])
    covers_top = False
    if np.linalg.norm(up) > 1e-9:
        up /= np.linalg.norm(up)
        u_top = math.atan2(float(np.dot(up, y_dir)), float(np.dot(up, x_dir)))
        u0, u1 = adaptor.FirstUParameter(), adaptor.LastUParameter()
        covers_top = _angle_in_range(u_top, u0, u1)
    return CylinderInfo(r, origin, axis, concave, covers_top, tilt)


def _angle_in_range(a: float, u0: float, u1: float, eps: float = 1e-6) -> bool:
    span = u1 - u0
    if span >= 2 * math.pi - eps:
        return True
    rel = (a - u0) % (2 * math.pi)
    return eps < rel < span - eps


def is_bed_face(face: bd.Face, z: float = 0.0) -> bool:
    bb = face.bounding_box()
    if abs(bb.min.Z - z) > 1e-6 or abs(bb.max.Z - z) > 1e-6:
        return False
    n = face.normal_at()
    return n.Z < -0.999


def vertical_cone_tilt_deg(face: bd.Face) -> float | None:
    """For a cone with a vertical axis, its exact surface tilt from vertical (the semi-angle).

    Bed chamfers along filleted outlines become 45° cones; their tessellated triangles read a
    fraction of a degree steeper than the true surface, so the overhang check uses this.
    """
    adaptor = BRepAdaptor_Surface(face.wrapped)
    if adaptor.GetType() != GeomAbs_Cone:
        return None
    cone = adaptor.Cone()
    d = cone.Axis().Direction()
    if abs(d.Z()) < 1 - 1e-9:
        return None
    return math.degrees(abs(cone.SemiAngle()))
