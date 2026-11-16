# CLAUDE.md — bikeparts

Open-source, parametric, 3D-printable bicycle **accessory** parts. Full plan: `docs/PLAN.md`.
Scope line: accessories only, never in the rider's primary load path (no stems, bars,
seatpost heads, cranks, pedals, brake levers, star nuts, derailleur hangers).

**Build direction is +Z, parts are returned print-oriented on Z=0; never state a dimension without a source comment.**

## Design rules

These rules go into the repo's CLAUDE.md verbatim and are enforced by tests where possible. A part that breaks one needs a written exception in its README.

### Print-friendly

1. **Zero supports.** Every part prints flat-side-down with no support material. Overhangs ≤ 45°; bridges ≤ 10 mm.
2. **Teardrop or diamond holes** for any horizontal hole over 3 mm, so the top of the hole doesn't sag.
3. **Walls in nozzle multiples** for a 0.4 mm nozzle: 1.2, 1.6, 2.0, 2.4 mm. No 1.5 mm walls that slice into a gap-fill mess.
4. **0.4–0.5 mm chamfer on every bed-contact edge** to absorb elephant's foot, so press fits and mating faces stay true.
5. **Clearances as named parameters:** sliding fit 0.25 mm per side, press fit 0.05 mm, captive nut pocket +0.15 mm across flats. One `tolerances.py` file, tunable per printer.
6. **Fits a 220 × 220 mm bed**, so it prints on any common printer.
7. **Text and logos debossed 0.4 mm** on vertical faces, never embossed on the top surface.

### Structural

1. **Orient for the load path.** Layer lines are the weak axis: interlayer strength is roughly 30–60% of in-plane strength. Every part's main bending or hoop stress must run along the layers, not across them. The print orientation is a design input, chosen before the geometry.
2. **Split clamps, not snap-ring clamps.** A full ring printed flat puts hoop stress across layers at two points; a two-piece clamp with bolts on both sides keeps the ring's tension in-plane.
3. **Metal carries clamp force.** Brass heat-set inserts (M3, M4, M5) or hex-captive nuts. Bolt bosses get ≥ 2.4 mm wall around the insert.
4. **No sharp internal corners.** Minimum 1.0 mm fillet at every load-bearing inside corner; 2.0 mm where FEA shows stress concentration.
5. **Ribs over thickness.** Stiffen with ribs aligned to the layer plane rather than solid blocks that just add print time and warp.
6. **Heat floor of 70 °C.** A bike in a parked car hits that. No PLA for anything that lives on the bike: PETG is the minimum, ASA preferred for sun exposure, PA-CF (nylon carbon fiber) for clamps under real load. TPU for anything that touches paint or carbon.
7. **Safety factor ≥ 3** on the published design load, after applying a 0.5 knockdown for interlayer strength.
8. **Fail-safe failure mode.** Where possible, a tether point or a geometry that holds the accessory if the primary clamp cracks.

### Material quick reference

| Material | Use it for | Glass transition (approx.) | Notes |
|---|---|---|---|
| PETG | General on-bike parts, shop tools | ~80 °C | Default. Tough, forgiving to print |
| ASA | Parts in constant sun | ~100 °C | UV-stable; needs an enclosure |
| PA-CF | Clamps, mounts under vibration | ~100 °C+ (varies by brand) | Stiffest option; dry the filament; hardened nozzle |
| TPU 95A | Shims, jaw covers, bumpers | n/a (elastomer) | Protects finishes, damps vibration |

Glass-transition figures are approximate typical values from memory; check the datasheet for the specific filament you buy.

## Repo conventions

- **Build direction is +Z.** `part.py` returns the part already oriented for printing, flat face on Z = 0. The overhang check depends on this.
- **Shared features, not copied geometry.** A split clamp is written once in `features.py`; four parts reuse it. A fix lands everywhere.
- **Every dimension traces to a source.** Standards cite the spec or the caliper measurement (with photo) in a comment. No dimension from memory.
- **Outputs are reproducible.** `uv run build` regenerates every STEP, 3MF, STL, drawing and README from source; nothing in `out/` is hand-edited.

## How the code enforces this

- Shared geometry lives in `src/bikeparts/core/features.py` (`teardrop_hole`, `horizontal_hole`,
  `insert_boss`, `captive_nut_pocket`, `split_clamp`, `rib`, `bed_chamfer`). Reuse them; never
  copy their geometry into a part.
- Clearances come only from `core/tolerances.py` (`PRINTER`). Walls go through
  `tolerances.check_wall()` (nozzle multiples, ≥ 1.2 mm).
- Hardware (`core/hardware.py`), standards (`core/standards.py`) and materials
  (`core/materials.py`) are pydantic models with a required `source` string and a `verified`
  flag. `verified=False` means "from memory or brand-specific — confirm with calipers or a
  datasheet". Module-level numeric constants in `core/` need a `# source:` comment
  (enforced by `tests/test_core.py`).
- Materials are all `verified=False` until real datasheet values are entered; Phase 3 FEA
  must refuse unverified materials.
- A part is `src/bikeparts/parts/<slug>/` with `params.py`, `part.py` (exposes
  `PART = PartSpec(...)`), `loads.py` (if FEA applies), generated `README.md` + `drawings/`,
  `test_part.py` (virtual-assembly fit tests: build the bodies, place them as assembled,
  assert zero overlap where they must clear and overlap where they must stop).
  `PartSpec.build(params)` returns `{body name: PrintBody}` — one printable solid on Z = 0 with
  its material, quantity, slicer overrides and any rule-7 label `ExemptRegion`s.
- Merging an `insert_boss` into another body refills its pocket: re-cut with
  `features.insert_pocket()` after the union, and probe the pocket in a fit test.
- Labels: `features.deboss_text()` returns the cutter and its `ExemptRegion`; pass the region
  in `PrintBody.exempt` so overhang/min_wall skip only the glyphs.
- Decisions and deviations from the plan go in `docs/DECISIONS.md`.
- A rule exception goes in `PartSpec.exceptions` (check name → reason) **and** in the part's
  README. The check then reports WAIVED instead of FAIL.
- OEM interface dimensions (quarter-turn, 3-prong, brake pads) are never guessed: leave a
  TODO constant and ask Paul for caliper measurements.

## Commands

```
uv sync                         # install
uv run pytest                   # unit tests (features, checks, core, scripts)
uv run check                    # Gate 1 on every part preset + parametric sweeps
uv run check --part <slug>      # one part
uv run check --fixture <name>   # a known-good/bad fixture (src/bikeparts/fixtures.py)
uv run check --self-test        # every fixture fails exactly its expected checks
uv run build [--part <slug>]    # out/<part>/<preset>/<body>.step|stl|3mf|svg + READMEs
uv run calibrate --dry-run ...  # coupon results → core/tolerances.py
uv run ruff check . && uv run ruff format --check . && uv run pyright
```

Don't move on from a part until `uv run check` is green. One part per branch; commit messages
`phase N: <summary>`.
