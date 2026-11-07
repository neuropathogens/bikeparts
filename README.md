# bikeparts

Open-source, parametric, 3D-printable bicycle **accessory** parts, modeled in code with
[build123d](https://github.com/gumyr/build123d). Every part prints without supports, ships
with a recommended material and print orientation chosen for its load path, and passes
automated geometry checks, FEA (where it carries load) and a physical test before release.

> **Scope:** accessories only — never anything in the rider's primary load path. A failed
> part should cost you an accessory, never control of the bike. No warranty; see
> [LICENSE.md](LICENSE.md).

Plan and design rules: [docs/PLAN.md](docs/PLAN.md) · agent conventions: [CLAUDE.md](CLAUDE.md)

## Status

| Phase | | |
|---|---|---|
| 0 | Scaffold: core modules, check suite, CI | ✅ |
| 1 | Calibration coupon | — |
| 2 | Wave 1: shipping spacers, tracker spacer, Spine mount | — |
| 3 | FEA pipeline | — |
| 4–5 | Waves 2–3 | — |
| 6 | v1.0 release and catalog site | — |

## Quick start

```sh
uv sync
uv run pytest                          # unit tests
uv run check --self-test               # proves every check catches its defect
uv run check --fixture overhang_cube_60
uv run build                           # out/<part>/<preset>/<body>.{step,stl,3mf,svg}
uv run check                           # Gate 1 on every part
```

## Gate 1 checks

| Check | What fails it |
|---|---|
| `watertight` | invalid B-rep, more than one solid per body, open or inconsistent mesh |
| `bed_fit` | larger than 220 × 220 × 250 mm, not sitting on Z = 0, no flat bed face |
| `overhang` | any surface tilted more than 45° from vertical, reported in mm². Bed face, bridges ≤ 10 mm and round holes ≤ 3 mm are exempt |
| `min_wall` | more than 0.5 mm² of wall under 1.2 mm, by inward ray casting from 4000 surface samples |
| `hole_orientation` | a horizontal hole > 3 mm whose top is round (must be a teardrop or diamond) |

A part may waive a check only with a written reason in `PartSpec.exceptions` and its README.

## Layout

```
src/bikeparts/core/        tolerances, materials, hardware, standards, features
src/bikeparts/interfaces/  dovetail rail, quarter-turn, 3-prong (Phase 2)
src/bikeparts/parts/       one package per part
src/bikeparts/fixtures.py  known-good / known-bad bodies for the checks
checks/                    Gate 1 analyzers
scripts/                   build, check, render (SVG drawings)
profiles/                  PrusaSlicer profiles per material
test-reports/              physical test logs and photos
```
