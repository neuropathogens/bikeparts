# Decisions

Decisions that change or fill in `docs/PLAN.md`. Newest first.

## 2026-11-06 — v1 scope (Paul)

**Owner and visibility.** Public repository, owned by Paul Wang (who also owns University
Bikes). Copyright lines name Paul Wang.

**Printers.** "Reasonable for most printers." So v1 assumes no enclosure and no hardened
nozzle: every rigid part is **PETG** (the plan's ASA and PA-CF picks move to PETG, as the
plan's open questions anticipated). TPU 95A only for optional pads. 0.4 mm nozzle, 220 × 220
mm bed, generic conservative slicer profiles in `profiles/`.

**The three parts (chosen by Claude, per Paul).** Picked for usefulness and novelty, and
because each can be finished without guessed OEM dimensions — the plan forbids guessing, so
Spine (#1: quarter-turn and 3-prong interfaces) and brake spacers (#11: pad profiles) wait for
caliper measurements.

1. **Ghost tracker spacer** (#2) — anti-theft for every rider; hides an AirTag sealed
   between frame and bottle cage.
2. **Vault bar-end plug** (#5) — every bike needs bar-end plugs; this one also carries the
   tubeless kit.
3. **Shop dummy hub** (#3 + #10 merged) — shipping spacer and chain keeper in one, for
   University Bikes' shipping and wash workflow; covers all 8 axle standards.

## Deviations from PLAN.md, and why

- **Bar-end plug expander is a double wedge, not slotted fingers.** Fingers printed upright
  flex by bending across the layer lines (rule 1's weak axis). Two 45° wedges, like a quill
  stem's, keep every printed piece in compression or in-plane shear.
- **Bar-end plug covers 17–21.5 mm in two printed sizes** (17–19.5, 19–21.5) from one source
  file. One size for the whole 17–21 range needs 4.5 mm of wedge travel, which left a 0.65 mm
  wall at the slot wedge.
- **Bar-end bolt torque is 0.5 N·m.** At 1.2 N·m the hand check gave a safety factor of
  1.2–1.3, under rule 7's 3. 0.5 N·m gives 3.5 (floor) and 4.0 (nut).
- **Parts 3 and 10 are one part.** A rear shipping spacer with a chain roller *is* a dummy hub.
- **The chain roller runs on a PETG bushing, not a 608 bearing.** A 608's 8 mm bore can't sit
  coaxially on a 12 or 15 mm thru-axle, and backpedalling by hand doesn't need a bearing.
- **Phase 1 (calibration coupon) came after the first three parts**, which use the plan's
  default clearances until someone runs `uv run calibrate` with coupon results.
- **Coupon layout:** the Ø3/5/8 teardrop holes are on the key's block, not the plate, so a
  drill shank goes straight through to air on both sides.
- **Dovetail rail profile** (`interfaces/dovetail_rail.py`): 6 mm neck, 1.6 mm neck height,
  3 mm of 45° flare, 1.2 mm vertical cap — 45° flanks print unsupported, and the neck and cap
  keep every edge ≥ 90°.

## Phase 3 — FEA (Gate 2)

- **Solver: scikit-fem, not CalculiX.** CalculiX isn't packaged for Homebrew or pip; gmsh
  (meshing, run as a separate program) and scikit-fem (BSD, quadratic tets) both pip-install
  on macOS and CI. `uv run fea` writes `parts/<part>/fea/results.json` + stress plots.
- **What governs.** Peaks at the edges of idealised supports/loads grow without bound with
  mesh refinement, so the governing von Mises stress is taken > 1.5 mm from any loaded or
  supported face, and bearing (applied pressure, or *mean* contact pressure over a spring
  support) is checked separately. Raw peaks and contact-edge pressures are still reported.
  Contacts are modelled as normal-direction springs plus load-free 3-2-1 pins, not clamps.
- **Mesh.** Coarse 1.2 mm + refined 0.55 mm. A study showed 0.8 mm was not converged.
- **Materials are unverified** (typical PETG values), so Gate 2 is a screen until datasheet
  values are entered.

### Bar-end plug changes forced by Gate 2

| Finding | Change |
|---|---|
| Washer bearing on the floor, SF 2.1 | M6 washer (Ø12 × 1.6) on the M5 bolt |
| Only ~2.3 mm of roof over a captive nut, SF 0.7 | threaded wedge's short side 3 → 10 mm |
| Hex-nut face crushing PETG in bearing, SF 1.3 | M5 heat-set insert instead of a nut |
| Sharp inside corner at the shelf channel beside the bolt hole, SF ~2.5 (converged) — a rule-4 breach | 1.5 mm fillet on the channel floor edges → SF 4.4 |
| Stress scales with preload | bolt torque 0.5 → 0.3 N·m (~180 N of friction grip remains) |

## Check-suite changes made while building the parts

- **Label regions.** Rule 7 allows 0.4 mm debossed text; glyph ceilings and strokes would
  trip `overhang` and `min_wall`. Parts declare the label's box (`ExemptRegion`), and the
  README lists it.
- **min_wall ignores grazing hits** (ray within ~14.5° of parallel to the face it hits).
  Rays cast from points right at a 90° edge skim the neighbouring face and read as walls a
  fraction of a millimetre thick. Real thin walls are hit near head-on, or at 45° in a wedge;
  the `thin_wall_cup` fixture still fails.
- **Source comments may be multi-line**: the lint reads the whole comment block above a
  constant.

## Bugs the checks couldn't see (caught by fit tests)

- 2026-11-06: merging an `insert_boss` into a thicker body refilled the insert pocket — the
  coupon would have printed without insert holes. Fixed with `features.insert_pocket()` cut
  after merging; `calibration_coupon/test_part.py` probes every pocket.

## Still unverified (measure before trusting)

- 12×142 / 12×148 frames: inner dropout spacing 135 / 141 mm (3.5 mm end-cap recesses).
- QR axle-end stubs (3 mm) shorter than the thinnest dropout in the shop.
- Smallest-cog chainline ~7 mm inboard of the drive dropout.
- Heat-set insert hole sizes and every material strength (`verified=False` in `core/`).
