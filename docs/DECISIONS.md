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
- **Phase 1 (calibration coupon) is deferred.** Parts use the plan's default clearances. If a
  fit is off on your printer, print the coupon (Phase 1) and rerun `uv run calibrate`.

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

## Still unverified (measure before trusting)

- 12×142 / 12×148 frames: inner dropout spacing 135 / 141 mm (3.5 mm end-cap recesses).
- QR axle-end stubs (3 mm) shorter than the thinnest dropout in the shop.
- Smallest-cog chainline ~7 mm inboard of the drive dropout.
- Heat-set insert hole sizes and every material strength (`verified=False` in `core/`).
