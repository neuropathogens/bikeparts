"""`uv run build` and `uv run check` entry points."""

from __future__ import annotations

from pathlib import Path

import pytest
import trimesh

from scripts import build_all, check_all, common


@pytest.fixture
def out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(common, "OUT", tmp_path)
    monkeypatch.setattr(build_all, "OUT", tmp_path)
    monkeypatch.setattr(check_all, "OUT", tmp_path)
    return tmp_path


def test_build_exports_all_formats(out: Path) -> None:
    assert (
        build_all.main(
            ["--part", "bar_end_vault", "--no-slice", "--no-readme", "--fixture", "teardrop_hole_6"]
        )
        == 0
    )
    d = out / "fixtures" / "teardrop_hole_6" / "default"
    for ext in ("step", "stl", "3mf", "svg"):
        assert (d / f"body.{ext}").stat().st_size > 0
    mesh = trimesh.load(d / "body.stl")
    assert isinstance(mesh, trimesh.Trimesh) and mesh.is_watertight
    assert "<svg" in (d / "body.svg").read_text(encoding="utf-8")[:200]


def test_check_exit_codes(out: Path) -> None:
    assert check_all.main(["--fixture", "overhang_cube_60", "-q"]) == 1
    assert check_all.main(["--fixture", "overhang_cube_45", "-q"]) == 0
    assert (out / "check-report.json").exists()


def test_check_one_part_is_green(out: Path) -> None:
    assert check_all.main(["--part", "bar_end_vault", "-q"]) == 0


def test_self_test_passes(out: Path) -> None:
    assert check_all.main(["--self-test"]) == 0


def test_calibrate_rewrites_only_the_block() -> None:
    import argparse

    from bikeparts.core import tolerances as tol
    from scripts import calibrate

    args = argparse.Namespace(
        sliding=0.2,
        press=0.1,
        nut="tight",
        nut_flats=None,
        inserts="loose",
        holes={3.0: 2.86, 5.0: 4.88, 8.0: 7.9},
        dovetail=None,
    )
    new = calibrate.new_values(tol.PRINTER, args)
    assert (new.sliding_fit, new.press_fit) == (0.2, 0.1)
    assert new.nut_pocket_flats == pytest.approx(tol.PRINTER.nut_pocket_flats + 0.10)
    assert new.insert_pocket_extra == pytest.approx(tol.PRINTER.insert_pocket_extra - 0.05)
    assert new.bolt_hole_extra == pytest.approx(0.1)  # mean shrink 0.06 → rounded up to 0.10
    src = Path(tol.__file__).read_text(encoding="utf-8")
    out = calibrate.update_source(src, new, "calibrated test")
    ns: dict[str, object] = {}
    exec(compile(out, "tolerances_test.py", "exec"), ns)  # the rewritten file still runs
    assert ns["PRINTER"].model_dump() == new.model_dump()  # type: ignore[attr-defined]
    assert out.split("# --- calibrate:begin")[0] == src.split("# --- calibrate:begin")[0]


def test_calibrate_rejects_press_looser_than_sliding() -> None:
    import argparse

    from bikeparts.core import tolerances as tol
    from scripts import calibrate

    args = argparse.Namespace(
        sliding=0.1, press=0.2, nut=None, nut_flats=None, inserts=None, holes=None, dovetail=None
    )
    with pytest.raises(SystemExit):
        calibrate.new_values(tol.PRINTER, args)
