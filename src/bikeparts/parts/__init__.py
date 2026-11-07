"""Part registry. Each part lives in `parts/<slug>/` and its `part.py` exposes `PART`.

parts/<slug>/params.py   pydantic model + size presets
parts/<slug>/part.py     PART = PartSpec(...); build() returns print-oriented bodies
parts/<slug>/loads.py    design load cases for FEA (Phase 3)
parts/<slug>/README.md   generated
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

import build123d as bd
from pydantic import BaseModel

from bikeparts.core.materials import MaterialName

Bodies = dict[str, bd.Part]


@dataclass(frozen=True)
class PartSpec:
    slug: str
    title: str
    material: MaterialName
    params_model: type[BaseModel]
    presets: Mapping[str, BaseModel]
    build: Callable[[Any], Bodies]  # params → {body name: print-oriented solid on Z = 0}
    # check name → written reason (must also appear in the part's README; design rules)
    exceptions: Mapping[str, str] = field(default_factory=dict)
    # extra parameter sets covering the full range; each must build without kernel errors
    sweep: Callable[[], Iterable[BaseModel]] | None = None


def discover() -> list[PartSpec]:
    specs: list[PartSpec] = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name):
        if not info.ispkg:
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}.part")
        spec = getattr(mod, "PART", None)
        if not isinstance(spec, PartSpec):
            raise TypeError(f"parts/{info.name}/part.py must define PART = PartSpec(...)")
        specs.append(spec)
    return specs
