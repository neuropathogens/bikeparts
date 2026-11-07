"""Shared plumbing for `uv run build` and `uv run check`: what to build, and where."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import build123d as bd

from bikeparts.fixtures import FIXTURES
from bikeparts.parts import PartSpec, discover

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "out"


@dataclass
class Target:
    """One buildable body: part (or fixture) × preset × body."""

    group: str  # "parts" or "fixtures"
    slug: str
    preset: str
    body: str
    shape: bd.Part
    exceptions: dict[str, str] = field(default_factory=dict)
    expect_fail: frozenset[str] | None = None  # fixtures only

    @property
    def label(self) -> str:
        return f"{self.slug}/{self.preset}/{self.body}"

    @property
    def out_dir(self) -> Path:
        base = OUT if self.group == "parts" else OUT / "fixtures"
        return base / self.slug / self.preset


def part_targets(specs: list[PartSpec]) -> Iterator[Target]:
    for spec in specs:
        for preset, params in spec.presets.items():
            for body, shape in spec.build(params).items():
                yield Target("parts", spec.slug, preset, body, shape, dict(spec.exceptions))


def fixture_targets(names: list[str]) -> Iterator[Target]:
    unknown = [n for n in names if n not in FIXTURES]
    if unknown:
        raise SystemExit(f"unknown fixture(s) {unknown}; choose from {sorted(FIXTURES)}")
    for name in names:
        fx = FIXTURES[name]
        for body, shape in fx.build().items():
            yield Target("fixtures", name, "default", body, shape, expect_fail=fx.expect_fail)


def select_parts(only: list[str] | None) -> list[PartSpec]:
    specs = discover()
    if only:
        missing = set(only) - {s.slug for s in specs}
        if missing:
            raise SystemExit(f"unknown part(s) {sorted(missing)}; have {[s.slug for s in specs]}")
        specs = [s for s in specs if s.slug in only]
    return specs
