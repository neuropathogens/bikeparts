# PrusaSlicer profiles

`uv run build` slices every printable body with these to get the grams and print time in
each part README. Physical tests (Gate 3) must use them too.

| File | What |
|---|---|
| `printer-generic-220.ini` | 220 × 220 × 250 mm bed, 0.4 mm nozzle, conservative motion limits |
| `process-0.20mm.ini` | 0.20 mm layers, 3 perimeters, 30 % gyroid, **supports off** |
| `petg.ini` | generic PETG — every rigid part in v1 |
| `tpu95a.ini` | generic TPU 95A — optional pads |

Loaded in that order: printer, process, then material. Part-specific overrides (e.g. a
brim on a tall part) come from the part's `PrintBody.slicer` and are listed in its README.
Times are estimates for a generic printer; a tuned CoreXY prints much faster.
