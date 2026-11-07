# Open-Source 3D-Printable Bike Parts — Catalog & Claude Code Build Plan

Nov 6, 2026 · Paul Wang

## Overview

Build a 12-part open-source library of parametric bike parts, modeled in code with build123d, every part printable without supports and validated by automated geometry checks, FEA, and a physical test protocol before release.

The bet: most printable bike parts online are one-off STLs for one handlebar size, printed in PLA, with no load data. This library wins on three things: every part is parametric (one source file covers every standard size), every part ships with a recommended material and print orientation chosen for the load path, and every part has a published test result.

Three tiers, 12 parts:

- **Cockpit & mounts (4):** where riders actually want customization
- **Security & carry (4):** things off-the-shelf products do badly or expensively
- **Shop & transport (4):** tools that pay for themselves in a refurb or repair workflow

**Deliberately excluded.** Nothing in the primary load path of the rider: stems, handlebars, seatpost heads, crank parts, pedal bodies, brake levers, steerer star-nut replacements, or derailleur hangers. A failed printed light mount costs you a light; a failed printed stem costs you teeth. Every part in this library is designed so that its worst-case failure is losing the accessory, never losing control.

**Hardware philosophy.** Plastic carries shape, metal carries clamp force. Every clamp uses steel bolts into brass heat-set inserts or captive nuts, never screws threaded into plastic.

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

## Part catalog

Twelve parts, built in three waves: Wave 1 proves the pipeline on three parts with very different geometry, Waves 2 and 3 reuse its interfaces and checks.

| # | Part | Tier | Wave | Material | Sizes covered by one source file |
|---|---|---|---|---|---|
| 1 | Spine modular out-front mount | Cockpit | 1 | PA-CF or PETG | Bars Ø 31.8, 35.0 |
| 2 | Ghost tracker cage spacer | Security | 1 | ASA | Any frame with 64 mm bottle bosses |
| 3 | Dropout & fork shipping spacers | Shop | 1 | PETG | QR 100/130/135, thru-axle 12×100, 15×100, 15×110, 12×142, 12×148 |
| 4 | Seatpost accessory rail | Cockpit | 2 | ASA | Posts Ø 27.2, 30.9, 31.6, 34.9 |
| 5 | Expanding bar-end tool plug | Cockpit | 2 | PETG + TPU | Bar ID 17–21 mm |
| 6 | Tool-free cable clips | Cockpit | 2 | TPU 95A | Housing 4–5 mm, hose 5 mm, bundles of 1–4 |
| 7 | Bayonet tool pod | Carry | 2 | PETG + TPU sleeve | 64 mm bosses or strap mount |
| 8 | Saddle-rail cradle | Carry | 2 | PA-CF | Rails 7 mm round, 7×9 oval |
| 9 | U-lock carrier | Carry | 3 | PA-CF | Shackle Ø 13–18 mm; bosses or tube Ø 28–45 mm |
| 10 | Dummy hub chain keeper | Shop | 3 | PETG + 608 bearing | QR 130/135, thru-axle 12×142, 12×148 |
| 11 | Brake pad spacers & bleed blocks | Shop | 3 | PETG | Per caliper family, gap set by parameter |
| 12 | Interlocking wheel display stand | Shop | 3 | PETG | Wheels 20–29 in / 700c, tires 23 mm–2.6 in |

### 1. Spine modular out-front mount

- **Problem:** riders stack a computer mount, a light mount and a camera mount on one bar. Each is a separate clamp fighting for space.
- **Innovation:** one two-piece split clamp with a bolted dovetail rail. Interchangeable heads slide onto the rail: Garmin/Wahoo quarter-turn on top, GoPro-style 3-prong and an under-mount light on the bottom. One clamp, any combination, swap heads without removing the clamp.
- **Structure:** clamp printed on its side so hoop stress runs in-plane; 4× M4 bolts into heat-set inserts; a tether eyelet so a cracked head can't drop a $500 computer.
- **Interfaces to measure:** quarter-turn tab geometry and GoPro prong spacing are measured from real OEM parts with calipers and stored once in `interfaces/` with a photo of the measurement.
- **Test:** 5 N·m bolt torque without cracking; head holds a 250 g payload through 30-minute vibration and a 1 m drop of the bike onto its side.

### 2. Ghost tracker cage spacer

- **Problem:** visible trackers get ripped off; seat-tube and steerer hides are either expensive or touch safety parts.
- **Innovation:** an ~11 mm spacer that sits between the frame and the bottle cage on the standard 64 mm M5 bosses, with an AirTag pocket (Ø 31.9 × 8.0 mm) between the bolts. You can only reach it by removing the cage. Optional security-Torx bolts.
- **Structure:** contact face parameterized to the tube diameter, with a TPU pad; bolt holes sleeved so the clamp load goes bolt to frame, not through the pocket.
- **Note:** cage bolts must be ~12 mm longer; the README lists the exact length.

### 3. Dropout & fork shipping spacers

- **Problem:** bikes shipped without wheels get crushed fork blades and bent rear triangles. Cardboard-shop spacers are thin and generic.
- **Innovation:** one parametric body per axle standard with a through-bore so you can run the real thru-axle or skewer through it and clamp it. Ribbed, nestable, color-coded by standard so a shop can grab the right one at a glance.
- **Structure:** compression along the axle, which is the strong direction when printed standing up. Tiny cost, very high value for anyone who ships bikes.

### 4. Seatpost accessory rail

- **Problem:** rear radar, tail light, and bag attachments all clamp separately to an already crowded seatpost.
- **Innovation:** the same dovetail rail as Spine, wrapped around the seatpost with a TPU liner. Rear radar or light on the quarter-turn head; a tracker pocket behind it.
- **Structure:** same split-clamp rules; aero and D-shaped posts are out of scope for v1.

### 5. Expanding bar-end tool plug

- **Problem:** open bar ends are an injury hazard, and a tubeless repair kit is useless if it's at home.
- **Innovation:** a slotted sleeve expanded by a bolt-driven cone (like a stem's expander wedge) locks into any bar ID from 17 to 21 mm. Hollow core stores tubeless plugs and a reamer behind a twist cap.
- **Structure:** the expanding fingers are printed vertically so they flex along layers; TPU outer band grips without scratching.

### 6. Tool-free cable clips

- **Problem:** zip ties are single-use, ugly, and scratch frames.
- **Innovation:** a family of TPU snap clips: housing-to-housing bundlers (1–4 lines), and a clip that grabs a frame tube with a stretch band. Re-routable without cutting anything.
- **Structure:** TPU elasticity does the clamping; no metal needed.

### 7. Bayonet tool pod

- **Problem:** saddle bags rattle and sag; frame bags block bottle cages.
- **Innovation:** a sealed cylinder that mounts on bottle bosses (under or instead of a cage) with a quarter-turn bayonet lid instead of printed threads, which print badly and cross-thread. A TPU inner sleeve holds a CO₂ cartridge, levers, multi-tool and quick links silently.
- **Structure:** bayonet lugs printed in-plane; O-ring groove sized for a standard O-ring for water resistance.

### 8. Saddle-rail cradle

- **Problem:** strap-on tube rolls slide and swing.
- **Innovation:** a low-profile cradle that clamps both rails behind the seatpost, with a strap slot for a tube and CO₂. Parameterized for round and oval carbon rails, with a TPU liner and a clamp force limited by a hard stop so it can't crush carbon.

### 9. U-lock carrier

- **Problem:** stock U-lock brackets are notorious for rattling loose and dropping the lock.
- **Innovation:** a two-point carrier with a spring-loaded TPU latch that captures the shackle, plus a bumper that stops the lock body from swinging. Mounts on bosses or strap-mounts to a tube.
- **Structure:** this is the highest dynamic load in the library (1–2 kg lock bouncing on rough road). It gets FEA plus a 2-hour vibration and drop test before release.

### 10. Dummy hub chain keeper

- **Problem:** with the rear wheel out, the chain flops and grinds the frame during washing, shipping and repair.
- **Innovation:** a body that bolts into the dropouts with interchangeable axle inserts for each standard, carrying a free-spinning roller on a standard 608 skateboard bearing so you can backpedal and clean the chain with the wheel out.

### 11. Brake pad spacers & bleed blocks

- **Problem:** pistons get pushed out when the wheel is off; OEM spacers get lost.
- **Innovation:** parametric spacers and bleed blocks generated per caliper family from one measured pad-pocket profile. Ship as a labeled keyring set.
- **Note:** pad pocket profiles must be measured from real pads; no guessed OEM dimensions.

### 12. Interlocking wheel display stand

- **Problem:** kickstands mar paint, and wall hooks need drilling. A resale floor needs bikes upright and in neat rows.
- **Innovation:** a tire-slot floor stand that prints in two halves joined by a dovetail and two bolts, so it fits a 220 mm bed but stands wider than one. Tire-width inserts swap for road to MTB. Stands chain together in a row.
- **Structure:** the tipping moment is resisted by footprint, not by plastic strength; footprint sized so a 15 kg bike stays up at a 10° lean.

## Repo architecture

A Python monorepo where every part is code: build123d for geometry, pydantic for parameters, pytest for printability and fit checks, and GitHub Actions that rebuild, check and publish every part on each commit.

Each part flows from parameters to release; a failed check at any gate sends it back to source, never to a hand-edited file.

### Stack

| Layer | Tool | Why |
|---|---|---|
| Geometry | build123d (OpenCascade kernel) | Real B-rep CAD in Python; exports STEP, so anyone can edit in Fusion or FreeCAD |
| Parameters | pydantic models | Every size is a validated config, so `Spine(bar=35.0)` fails loudly on nonsense |
| Env & tooling | uv, ruff, pyright, pre-commit | Fast installs, one lockfile, typed code |
| Mesh checks | trimesh + custom analyzers | Watertight, overhang, wall-thickness and bed-fit checks on the exported mesh |
| FEA | gmsh + CalculiX | Open-source static stress on clamps and load-bearing parts |
| Slicing | PrusaSlicer CLI | Real print time and grams for each part's README, with supports disabled |
| Drawings | build123d SVG export | Black-and-white dimensioned drawings in every README |
| CI/CD | GitHub Actions | Build all, check all, attach STEP/3MF/STL to tagged releases |
| Catalog site (Phase 6) | Next.js + three.js | Browse, rotate and configure parts in the browser |

### Layout

```
bikeparts/
├── CLAUDE.md                  # design rules + conventions (the rules section above)
├── pyproject.toml / uv.lock
├── src/bikeparts/
│   ├── core/
│   │   ├── tolerances.py      # clearances, tunable per printer
│   │   ├── materials.py       # strengths, knockdowns, max temps
│   │   ├── hardware.py        # heat-set inserts, bolts, nuts, 608 bearing, O-rings
│   │   ├── standards.py       # bar, seatpost, axle, boss, rail dimensions
│   │   └── features.py        # teardrop_hole, insert_boss, split_clamp, rib, bed_chamfer
│   ├── interfaces/            # measured once, reused everywhere
│   │   ├── dovetail_rail.py   # the Spine / seatpost rail
│   │   ├── quarter_turn.py    # computer / radar mount
│   │   └── three_prong.py     # camera / light mount
│   └── parts/
│       └── spine_mount/
│           ├── params.py      # pydantic model + size presets
│           ├── part.py        # geometry, oriented for printing
│           ├── loads.py       # design load cases for FEA
│           ├── README.md      # generated: drawing, BOM, print settings, test results
│           └── test_part.py
├── checks/                    # printability + structural analyzers
├── scripts/                   # build_all, render, slice, fea, make_readme
├── profiles/                  # PrusaSlicer profiles per material
├── test-reports/              # physical test logs + photos, per part
└── site/                      # Next.js catalog (Phase 6)
```

### Conventions

- **Build direction is +Z.** `part.py` returns the part already oriented for printing, flat face on Z = 0. The overhang check depends on this.
- **Shared features, not copied geometry.** A split clamp is written once in `features.py`; four parts reuse it. A fix lands everywhere.
- **Every dimension traces to a source.** Standards cite the spec or the caliper measurement (with photo) in a comment. No dimension from memory.
- **Outputs are reproducible.** `uv run build` regenerates every STEP, 3MF, STL, drawing and README from source; nothing in `out/` is hand-edited.

## Phased build plan

Seven phases, each a separate Claude Code session ending in a merged PR. Phase 1 (a tolerance coupon) comes before any real part, because every fit in the library depends on how your printer actually prints.

How to run each phase: start Claude Code in the repo, press Shift+Tab into plan mode, paste the prompt, review the plan, then let it build. One part per branch. Don't let it move on until `uv run check` is green.

1. **Phase 0 — Scaffold.** Repo, tooling, core modules, check suite, CI. No parts yet.
2. **Phase 1 — Calibration coupon.** One small print that measures your printer's real clearances; results go into `tolerances.py`.
3. **Phase 2 — Wave 1 parts.** Shipping spacers (simplest), tracker spacer, then Spine (hardest; creates the shared interfaces).
4. **Phase 3 — FEA pipeline.** Static stress on Spine's clamp; becomes a reusable check.
5. **Phase 4 — Wave 2 parts.** Seatpost rail, bar-end plug, cable clips, tool pod, saddle cradle.
6. **Phase 5 — Wave 3 parts.** U-lock carrier, dummy hub, brake spacers, display stand.
7. **Phase 6 — Release & catalog site.** v1.0 tag, release assets, Next.js catalog.

### Phase 0 prompt — Scaffold

```
Create a Python monorepo called bikeparts for open-source, parametric, 3D-printable bicycle parts.

Stack: Python 3.12, uv, build123d, pydantic v2, trimesh, pytest, ruff, pyright, pre-commit.
Use the layout and conventions in docs/PLAN.md exactly.

Build, in order:
1. CLAUDE.md containing the design rules from docs/PLAN.md verbatim, plus: "build direction is +Z, parts are returned print-oriented on Z=0; never state a dimension without a source comment."
2. core/tolerances.py, materials.py, hardware.py (M3/M4/M5 heat-set insert pockets, socket-head bolts, hex nuts, 608 bearing), standards.py (bar, seatpost, axle, bottle-boss dimensions with source comments).
3. core/features.py: teardrop_hole, insert_boss, captive_nut_pocket, split_clamp, rib, bed_chamfer. Each with a unit test.
4. checks/: watertight, bed_fit (220x220x250), overhang (faces whose downward normal exceeds 45 deg from -Z, excluding the bed face, reported as area in mm^2), min_wall (ray-cast sampling, flag < 1.2 mm), and hole_orientation (horizontal holes > 3 mm must be teardrop).
5. scripts: `uv run build` (export STEP, 3MF, STL + SVG drawing per part to out/), `uv run check` (all checks on all parts).
6. GitHub Actions: on push run lint, typecheck, tests, build, check; on tag attach out/ artifacts to the release.

Stop after scaffolding. Show me the check output on a dummy test cube with a deliberate 60-degree overhang so I can see the overhang check fail correctly.
```

### Phase 1 prompt — Calibration coupon

```
Create parts/calibration_coupon: a single flat print under 60x60x12 mm that measures this printer's real fits.
Include: a clearance ladder of pegs and holes from 0.10 to 0.40 mm per side in 0.05 steps (labeled, debossed), an M3/M4/M5 heat-set insert boss row, a captive M4 nut pocket, teardrop holes at 3/5/8 mm, and a 20 mm dovetail male/female pair at three clearances.
Write a README with what to measure and a short form for me to fill in.
Then add a script `uv run calibrate` that takes my measured best-fit values and updates tolerances.py.
```

### Phase 2 prompts — Wave 1

```
Build parts/shipping_spacers per docs/PLAN.md part 3.
One pydantic preset per axle standard. Through-bore sized for the axle with sliding clearance. Ribbed walls, printed standing up so axial compression runs along the layers. Debossed standard label on the side.
All checks green. Generate the README with drawing, print settings, grams and print time from PrusaSlicer CLI.
```

```
Build parts/tracker_spacer per docs/PLAN.md part 2.
64 mm M5 boss spacing, AirTag pocket 31.9 x 8.0 mm plus tolerance, frame contact face parameterized by tube diameter with a TPU pad as a separate printable body.
Bolt holes sleeved so clamp load does not pass through the pocket wall. README states required bolt length.
```

```
Build parts/spine_mount per docs/PLAN.md part 1. This part defines shared interfaces, so build those first:
1. interfaces/dovetail_rail.py (male on clamp, female on heads), with tolerance from tolerances.py.
2. interfaces/quarter_turn.py and interfaces/three_prong.py. Leave every OEM dimension as a TODO constant and ask me for caliper measurements before finalizing. Do not guess them.
3. Two-piece split clamp from features.split_clamp, 4x M4 inserts, printed on its side so hoop stress is in-plane. Tether eyelet.
4. Heads: top quarter-turn, bottom three-prong, bottom light.
Presets for 31.8 and 35.0 bars. Render an exploded assembly SVG for the README.
```

### Phase 3 prompt — FEA

```
Add an FEA check using gmsh and CalculiX (ccx).
scripts/fea.py: take a part's STEP and its loads.py (fixed faces, applied forces), mesh with second-order tets, run linear static, report max von Mises and safety factor.
Material strength = datasheet tensile x 0.5 interlayer knockdown. Fail the check if safety factor < 3.
Run it on spine_mount with: bolt clamp preload equivalent to 5 N-m on M4, plus a 250 g head mass at 10 g vertical shock. Save a stress-plot PNG to the README.
If it fails, propose geometry changes (ribs, fillets), apply them, and rerun.
```

### Phase 4–5 prompt template

```
Build parts/<name> per docs/PLAN.md part <n>.
Reuse core/features and interfaces/ wherever possible; do not duplicate geometry.
Add loads.py and run FEA if the part carries a clamp or a hanging load.
All checks green, README generated, then stop and list anything you had to assume.
```

### Phase 6 prompt — Release & site

```
1. Tag v1.0.0; CI attaches a zip per part (STEP, 3MF, STL, README.pdf).
2. Build site/ in Next.js (app router, static export): a catalog grid, a part page with a three.js STL viewer, size presets, BOM, print settings and test results pulled from each README.
   Visual style: black and white, IBM Plex Mono, technical-drawing feel.
3. Deploy to Netlify.
```

## Validation

No part is tagged for release until it passes three gates in order: automated checks on every commit, FEA for anything carrying a clamp or hanging load, and a physical test printed in the recommended material.

### Gate 1 — Automated (every commit, in CI)

- Watertight mesh, fits a 220 × 220 × 250 mm build volume
- Zero unsupported overhang area beyond 45° (bed face excluded)
- No wall under 1.2 mm; no horizontal hole over 3 mm without a teardrop
- Every size preset builds; parametric sweep over the full range builds without kernel errors
- Slices in PrusaSlicer with supports off; grams and print time written to the README

### Gate 2 — FEA (clamps and hanging loads)

Applies to parts 1, 4, 5, 8, 9 and 12. Pass = safety factor ≥ 3 against datasheet tensile strength × 0.5 interlayer knockdown. FEA is a screen, not proof: printed parts are anisotropic and porous, so Gate 3 always overrides a passing FEA result.

### Gate 3 — Physical test

Print in the recommended material with the profile in `profiles/`. Mark every bolt head with a paint line before testing so loosening is visible.

| Test | Method | Pass criterion | Parts |
|---|---|---|---|
| Bolt torque | Torque to spec + 25% with a torque wrench | No cracks, no insert pull-out | All bolted parts |
| Rotational slip | 2 kg hung on a 15 cm arm from the head (~3 N·m) for 10 min | No rotation on the bar or post | 1, 4, 8 |
| Heat soak | 1 hr at 70 °C (oven or car dash), then re-torque check | Fit holds, no warp, bolts still at torque | All on-bike parts |
| Ride vibration | 50 km including gravel or rough pavement | Paint marks unbroken, nothing loose or rattling | 1, 2, 4, 5, 7, 8, 9 |
| Drop | Bike dropped onto its side from upright, 3× per side | Part intact; accessory retained or caught by tether | 1, 4, 9 |
| Dynamic load | 20 drops off a 10 cm curb with lock fitted, plus 2 hr ride | Lock retained, no cracks at latch | 9 |
| Tip test | 15 kg bike leaned 10° in stand | Stays upright, no slot deformation | 12 |
| Shipping compression | 50 kg static load on spacer for 24 hr | Under 0.5 mm permanent set | 3 |

Each result goes into `test-reports/<part>/` with photos, filament brand, printer and date, and the README links it. Parts that only pass in one material say so plainly.

**Real bikes to test on:** a refurb-and-resale operation sees many frames, bar and post sizes, which is exactly the fit coverage this library needs. Testing on every bike that comes through the shop turns that into data.

## Licensing and publishing

Use three licenses, one per kind of content, and publish source on GitHub with print files mirrored to the major model-sharing sites.

| Content | Suggested license | Effect |
|---|---|---|
| Part designs (STEP, 3MF, STL) | CERN-OHL-S v2 | Anyone can make and sell them; modified designs they distribute must stay open |
| Code (build123d, checks, scripts) | Apache-2.0 | Permissive, with a patent grant |
| Docs, drawings, photos | CC BY-SA 4.0 | Shareable with attribution |

If you'd rather let companies build closed products on the designs, swap CERN-OHL-S for CERN-OHL-P. That's a values choice, not a technical one. This is a general summary, not legal advice.

**Required in every README:**

- A no-warranty statement and the scope line: accessories only, never in the rider's primary load path
- The material and orientation the part was tested in, and a warning that other materials are untested
- Compatibility described generically ("quarter-turn computer mount", "3-prong camera mount"). Brand names only to describe compatibility, never in a part's name

**Where to publish:**

1. GitHub — source of truth; releases carry the files
2. Printables and MakerWorld — where riders actually find printable parts; link back to GitHub
3. Catalog site (Phase 6) — configure a size and download

Before Phase 0: export this doc to Markdown and commit it as `docs/PLAN.md`, since every Claude Code prompt above points at it.

## Open questions

- Which printer and materials do you have? Without an enclosure, ASA and PA-CF parts move to PETG for v1.
- Who owns the repo: you personally, or a brand like University Bikes?
- Which three parts matter most to you? The waves above are ordered by engineering risk, not by what you'd use first.
