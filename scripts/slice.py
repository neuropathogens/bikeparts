"""Slice a body with PrusaSlicer's CLI to get real grams and print time (supports off)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bikeparts.core.materials import MaterialName

REPO = Path(__file__).resolve().parents[1]
PROFILES = REPO / "profiles"
_MATERIAL_PROFILE = {
    MaterialName.PETG: "petg.ini",
    MaterialName.TPU_95A: "tpu95a.ini",
}
_CANDIDATES = [
    "/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer",
    "prusa-slicer",
    "PrusaSlicer",
]


@dataclass(frozen=True)
class SliceResult:
    grams: float
    time: str


def slicer_path() -> str | None:
    env = os.environ.get("PRUSASLICER")
    for c in [env, *_CANDIDATES]:
        if c and (Path(c).exists() or shutil.which(c)):
            return c if Path(c).exists() else shutil.which(c)
    return None


def profile_files(material: MaterialName) -> list[Path]:
    if material not in _MATERIAL_PROFILE:
        raise ValueError(f"no slicer profile for {material}; v1 parts use PETG or TPU 95A")
    return [
        PROFILES / "printer-generic-220.ini",
        PROFILES / "process-0.20mm.ini",
        PROFILES / _MATERIAL_PROFILE[material],
    ]


def slice_stl(
    stl: Path, material: MaterialName, overrides: Mapping[str, str] | None = None
) -> SliceResult | None:
    exe = slicer_path()
    if exe is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        gcode = Path(tmp) / "out.gcode"
        cmd = [exe, "--export-gcode"]  # supports are off in process-0.20mm.ini
        for p in profile_files(material):
            cmd += ["--load", str(p)]
        for k, v in (overrides or {}).items():
            cmd += [f"--{k}", v]
        cmd += ["--output", str(gcode), str(stl)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0 or not gcode.exists():
            raise RuntimeError(f"PrusaSlicer failed on {stl.name}: {proc.stderr[-800:]}")
        text = gcode.read_text(errors="replace")
    grams = re.search(r"^; (?:total )?filament used \[g\] = ([\d.]+)", text, re.M)
    time = re.search(r"^; estimated printing time \(normal mode\) = (.+)$", text, re.M)
    if not grams or not time:
        raise RuntimeError(f"could not read grams/time from the G-code for {stl.name}")
    return SliceResult(float(grams.group(1)), time.group(1).strip())
