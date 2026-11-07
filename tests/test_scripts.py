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
    assert build_all.main(["--fixture", "teardrop_hole_6"]) == 0
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


def test_check_with_no_parts_is_green(out: Path) -> None:
    assert check_all.main([]) == 0


def test_self_test_passes(out: Path) -> None:
    assert check_all.main(["--self-test"]) == 0
