"""The FEA screen against textbook answers (uniform bar in tension: σ = F / A)."""

from __future__ import annotations

import build123d as bd
import numpy as np
import pytest

from bikeparts.core.features import as_part
from bikeparts.core.loads import LoadCase, Pin, Spring, Support, Traction, fixed, plane_z
from bikeparts.core.materials import MATERIALS, MaterialName
from checks.fea import FeaError, solve_case

PETG = MATERIALS[MaterialName.PETG]
BAR = as_part(bd.Box(10, 10, 60, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)))
F = 1000.0  # N on 100 mm² → 10 MPa
TOP = Traction(plane_z(60.0), (0.0, 0.0, F), "pull on top face")


def test_clamped_bar_in_tension() -> None:
    """A fully clamped end also stops Poisson contraction, which really does raise stress for
    about one bar-width past the clamp — so it reads above F/A. (Why load cases use rollers
    and springs for contacts: see the next test.)"""
    case = LoadCase("tension", "", "bar", (fixed(plane_z(0.0)),), (TOP,), "test")
    r = solve_case(BAR, case, PETG, h=2.5)
    assert 10.0 < r.max_vm < 16.0
    assert r.bearing == pytest.approx(10.0, rel=1e-6)  # applied pressure on the top face
    # elongation F·L / (E·A)
    assert r.max_disp == pytest.approx(F * 60 / (PETG.youngs_modulus_mpa * 100), rel=0.05)  # type: ignore[operator]
    assert r.safety_factor == pytest.approx(PETG.design_strength_mpa / r.governing)


def test_roller_and_pins_have_no_clamp_artifact() -> None:
    """A roller support plus 3-2-1 pins: stress is uniform even at the supported face."""
    case = LoadCase(
        "tension_roller",
        "",
        "bar",
        (
            Support(plane_z(0.0), (2,), "roller"),
            Pin((0.0, 0.0, 0.0), (0, 1), "pin"),
            Pin((5.0, 0.0, 0.0), (1,), "pin"),
        ),
        (TOP,),
        "test",
    )
    r = solve_case(BAR, case, PETG, h=2.5)
    assert r.raw_max_vm == pytest.approx(10.0, rel=0.03)


def test_spring_support_reacts_like_contact() -> None:
    case = LoadCase(
        "tension_spring",
        "",
        "bar",
        (
            Spring(plane_z(0.0), (0.0, 0.0, 1.0), "resting on a stiff plate"),
            Pin((0.0, 0.0, 0.0), (0, 1), "pin"),
            Pin((5.0, 0.0, 0.0), (1,), "pin"),
        ),
        (Traction(plane_z(60.0), (0.0, 0.0, -F), "push on top face"),),
        "test",
    )
    r = solve_case(BAR, case, PETG, h=2.5)
    assert r.max_vm == pytest.approx(10.0, rel=0.03)
    assert r.bearing == pytest.approx(10.0, rel=0.05)  # mean contact pressure = F / A


def test_selector_that_matches_nothing_is_an_error() -> None:
    case = LoadCase("bad", "", "bar", (fixed(plane_z(-5.0)),), (TOP,), "test")
    with pytest.raises(FeaError, match="matched no faces"):
        solve_case(BAR, case, PETG, h=2.5)


def test_rigid_body_modes_are_in_the_nullspace() -> None:
    from skfem import Basis, ElementTetP2, ElementVector, MeshTet, asm
    from skfem.models.elasticity import lame_parameters, linear_elasticity

    from checks.fea import _rigid_body_modes

    mesh = MeshTet().refined(1)
    basis = Basis(mesh, ElementVector(ElementTetP2()))
    K = asm(linear_elasticity(*lame_parameters(1000.0, 0.3)), basis)
    B = _rigid_body_modes(mesh, basis)
    assert np.abs(K @ B).max() < 1e-8 * np.abs(K).max()
