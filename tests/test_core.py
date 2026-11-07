"""Core data: tolerances, materials, hardware and standards carry sources and sane values."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bikeparts.core import hardware, materials, standards, tolerances

CORE = Path(tolerances.__file__).parent


def test_check_wall() -> None:
    for t in (1.2, 1.6, 2.0, 2.4, 4.0):
        assert tolerances.check_wall(t) == t
    for t in (0.8, 1.5, 2.2):
        with pytest.raises(ValueError):
            tolerances.check_wall(t)


def test_tolerances_validate() -> None:
    with pytest.raises(ValueError):
        tolerances.Tolerances(bed_chamfer=0.2)


def test_heat_floor_excludes_pla() -> None:
    m = materials.MATERIALS
    assert not m[materials.MaterialName.PLA].allowed_on_bike
    for name in ("PETG", "ASA", "PA-CF", "TPU 95A"):
        assert m[materials.MaterialName(name)].allowed_on_bike


def test_design_strength_applies_knockdown() -> None:
    petg = materials.MATERIALS[materials.MaterialName.PETG]
    assert petg.tensile_strength_mpa is not None
    assert petg.design_strength_mpa == pytest.approx(petg.tensile_strength_mpa * 0.5)


def test_unverified_materials_are_flagged() -> None:
    # Phase 3 FEA must refuse these until datasheet values are entered.
    assert all(not m.verified for m in materials.MATERIALS.values())


def _all_sourced() -> list[object]:
    return [
        *hardware.INSERTS.values(),
        *hardware.BOLTS.values(),
        *hardware.NUTS.values(),
        hardware.BEARING_608,
        *standards.BARS.values(),
        *standards.SEATPOSTS.values(),
        *standards.AXLES.values(),
        standards.BOTTLE_BOSSES,
        *materials.MATERIALS.values(),
    ]


@pytest.mark.parametrize(
    "item",
    _all_sourced(),
    ids=lambda i: str(
        getattr(i, "name", None) or i.thread
        if hasattr(i, "thread")
        else getattr(i, "designation", "")
    ),
)
def test_every_dimension_has_a_source(item: object) -> None:
    src = getattr(item, "source", "")
    assert isinstance(src, str) and len(src) > 10


def test_insert_bosses_meet_rule_3() -> None:
    for ins in hardware.INSERTS.values():
        wall = (ins.boss_diameter - ins.pocket_diameter) / 2
        assert wall == pytest.approx(hardware.MIN_INSERT_WALL) or wall > hardware.MIN_INSERT_WALL


def test_nut_pocket_geometry() -> None:
    n = hardware.NUTS["M4"]
    assert n.pocket_flats == pytest.approx(7.0 + tolerances.PRINTER.nut_pocket_flats)
    assert n.pocket_corners == pytest.approx(n.pocket_flats * 2 / 3**0.5)


def _module_constants_missing_source(path: Path) -> list[str]:
    """UPPER_CASE = <number> at module level must have a `source:` comment on/above it."""
    lines = path.read_text().splitlines()
    tree = ast.parse(path.read_text())
    missing = []
    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        value = node.value
        if not names or not names[0].isupper() or not isinstance(value, ast.Constant):
            continue
        if not isinstance(value.value, int | float) or isinstance(value.value, bool):
            continue
        here = lines[node.lineno - 1]
        above = lines[node.lineno - 2] if node.lineno > 1 else ""
        if "source:" not in here and "source:" not in above:
            missing.append(f"{path.name}:{node.lineno} {names[0]}")
    return missing


@pytest.mark.parametrize(
    "path",
    sorted(CORE.glob("*.py")),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_numeric_constants_cite_a_source(path: Path) -> None:
    assert _module_constants_missing_source(path) == []
