"""Every check proven against fixtures that must pass or must fail."""

from __future__ import annotations

import pytest

from bikeparts.fixtures import FIXTURES, overhang_cube
from checks import ALL_CHECKS, Body, Status, run_checks
from checks import overhang as overhang_check


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_fixture_fails_exactly_expected_checks(name: str) -> None:
    fx = FIXTURES[name]
    for body, shape in fx.build().items():
        results = run_checks(Body(body, shape))
        failed = {r.check for r in results if r.status is Status.FAIL}
        assert failed == set(fx.expect_fail), [(r.check, r.summary) for r in results]


def test_every_check_has_a_failing_fixture() -> None:
    covered = set().union(*(fx.expect_fail for fx in FIXTURES.values()))
    assert covered == set(ALL_CHECKS)


def test_60_degree_overhang_area_matches_hand_calculation() -> None:
    r = overhang_check.check(Body("cube", overhang_cube(60)))
    # underside: slant √(10² + (10/tan 60°)²) × 20 mm deep
    expected = (10**2 + (10 / 3**0.5) ** 2) ** 0.5 * 20
    assert r.status is Status.FAIL
    assert r.details["overhang_area_mm2"] == pytest.approx(expected, abs=0.5)
    assert r.details["worst_angle_deg"] == pytest.approx(60.0, abs=0.2)


@pytest.mark.parametrize("angle,fails", [(35, False), (45, False), (46, True), (75, True)])
def test_overhang_threshold(angle: float, fails: bool) -> None:
    r = overhang_check.check(Body("cube", overhang_cube(angle)))
    assert (r.status is Status.FAIL) is fails


def test_waiver_turns_fail_into_waived() -> None:
    shape = FIXTURES["oversize_bar"].build()["body"]
    results = run_checks(Body("bar", shape), {"bed_fit": "printed diagonally on a 250 mm bed"})
    r = next(r for r in results if r.check == "bed_fit")
    assert r.status is Status.WAIVED and r.ok


def test_waiver_for_unknown_check_is_rejected() -> None:
    with pytest.raises(ValueError):
        run_checks(Body("x", FIXTURES["boss_plate"].build()["body"]), {"supports": "nope"})
