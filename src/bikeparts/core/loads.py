"""Design load cases for FEA (Gate 2), as plain data.

A load case says which boundary faces are held fixed and which carry a total force. Faces
are picked by geometric predicates on facet midpoints, so a load case survives remeshing and
parameter changes. Each part's `loads.py` returns its cases for a given parameter set; the
solver lives in `checks/fea.py`.

Units: mm, N, MPa.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

# x is a (3, n) array of facet midpoints; return a boolean mask of length n.
Selector = Callable[[np.ndarray], np.ndarray]

# source: assumption — tolerance for picking faces on a plane / cylinder from a straight-sided
# tet mesh (chord sag of a 1.5 mm element on an r = 4 mm cylinder is ~0.07 mm)
TOL = 0.1


@dataclass(frozen=True)
class Traction:
    where: Selector
    force: tuple[float, float, float]  # total force (N), spread uniformly over the faces
    label: str


@dataclass(frozen=True)
class Support:
    """Faces held in some directions only: components 0, 1, 2 = X, Y, Z.

    A face resting on another part is a roller in its normal direction — clamping it in all
    three directions instead puts a false stress spike where the clamped face ends.
    """

    where: Selector
    components: tuple[int, ...]
    label: str


@dataclass(frozen=True)
class Spring:
    """Faces resting on another part along `normal` (unit vector, any direction): a stiff
    elastic foundation that resists motion along the normal only. Models contact without
    the false stress spike a fully clamped face makes where it ends."""

    where: Selector
    normal: tuple[float, float, float]
    label: str


@dataclass(frozen=True)
class Pin:
    """Hold the mesh vertex nearest `at` in some directions. Only for removing leftover
    rigid-body motion: place pins where the load path puts (almost) no reaction."""

    at: tuple[float, float, float]
    components: tuple[int, ...]
    label: str


@dataclass(frozen=True)
class LoadCase:
    name: str
    description: str
    body: str  # which PrintBody it applies to
    supports: tuple[Support | Spring | Pin, ...]
    loads: tuple[Traction, ...]
    source: str  # where the load magnitude comes from


def fixed(where: Selector, label: str = "fixed") -> Support:
    return Support(where, (0, 1, 2), label)


def _r(x: np.ndarray) -> np.ndarray:
    return np.hypot(x[0], x[1])


def plane_z(z: float, r_min: float = 0.0, r_max: float = np.inf) -> Selector:
    """Faces lying in the plane Z = z, within an annulus about the Z axis."""
    return lambda x: (np.abs(x[2] - z) < TOL) & (_r(x) >= r_min - TOL) & (_r(x) <= r_max + TOL)


def cylinder_z(r: float, z_min: float = -np.inf, z_max: float = np.inf) -> Selector:
    """Faces on the cylinder of radius r about Z, between two heights."""
    return lambda x: (np.abs(_r(x) - r) < TOL * 2) & (x[2] >= z_min - TOL) & (x[2] <= z_max + TOL)


def cone_z(r0: float, z0: float, r1: float, z1: float) -> Selector:
    """Faces on the conical surface through (r0, z0) and (r1, z1) about Z."""

    def sel(x: np.ndarray) -> np.ndarray:
        t = (x[2] - z0) / (z1 - z0)
        on = np.abs(_r(x) - (r0 + t * (r1 - r0))) < TOL * 2
        return on & (t >= -0.01) & (t <= 1.01)

    return sel


def half_space(axis: int, sign: float) -> Selector:
    """Faces on one side of a coordinate plane through the origin (e.g. +X half)."""
    return lambda x: sign * x[axis] > 0


def both(a: Selector, b: Selector) -> Selector:
    return lambda x: a(x) & b(x)


def either(a: Selector, b: Selector) -> Selector:
    return lambda x: a(x) | b(x)
