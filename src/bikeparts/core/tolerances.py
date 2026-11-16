"""Printer-specific clearances. ONE file, tuned per printer.

The defaults below are the starting values from docs/PLAN.md (design rule 5).
Phase 1's calibration coupon measures your printer's real fits, and
`uv run calibrate` rewrites the literals in the `PRINTER = Tolerances(...)` block.
Do not hand-edit other files to compensate for a printer; change it here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Tolerances(BaseModel):
    """All values in mm. "Per side" means added to a radius, not a diameter."""

    model_config = ConfigDict(frozen=True)

    # source: docs/PLAN.md design rule 5 (default until Phase 1 calibration)
    sliding_fit: float = Field(
        default=0.25, ge=0.0, le=1.0, description="per side, parts that slide"
    )
    # source: docs/PLAN.md design rule 5
    press_fit: float = Field(
        default=0.05, ge=0.0, le=0.5, description="per side, parts pressed together"
    )
    # source: docs/PLAN.md design rule 5
    nut_pocket_flats: float = Field(
        default=0.15, ge=0.0, le=1.0, description="added across flats of a captive hex nut pocket"
    )
    # source: docs/PLAN.md print rule 4 (0.4-0.5 mm elephant's-foot chamfer)
    bed_chamfer: float = Field(
        default=0.45, ge=0.4, le=0.5, description="chamfer on bed-contact edges"
    )
    # source: assumption — bolt clearance holes print undersize roughly like a sliding fit;
    # replace with the Phase 1 coupon's measured value.
    bolt_hole_extra: float = Field(
        default=0.1, ge=0.0, le=0.5, description="per side, on ISO 273 holes"
    )
    # source: assumption — heat-set pockets per insert maker's hole diameter, no extra by default;
    # Phase 1 coupon calibrates.
    insert_pocket_extra: float = Field(default=0.0, ge=-0.3, le=0.3, description="per side")


# --- calibrate:begin (rewritten by `uv run calibrate`; keep literal values only) ---
PRINTER = Tolerances(
    sliding_fit=0.25,
    press_fit=0.05,
    nut_pocket_flats=0.15,
    bed_chamfer=0.45,
    bolt_hole_extra=0.1,
    insert_pocket_extra=0.0,
)
# --- calibrate:end ---

# Nozzle-multiple walls (docs/PLAN.md print rule 3, 0.4 mm nozzle).
NOZZLE = 0.4  # source: docs/PLAN.md print rule 3
ALLOWED_WALLS: tuple[float, ...] = (1.2, 1.6, 2.0, 2.4)  # source: docs/PLAN.md print rule 3
MIN_WALL = 1.2  # source: docs/PLAN.md Gate 1 (no wall under 1.2 mm)


def check_wall(thickness: float) -> float:
    """Return `thickness` if it is a whole number of nozzle widths ≥ MIN_WALL, else raise.

    Rule 3 lists 1.2–2.4 explicitly; thicker structural walls are allowed as long as they
    stay on the 0.4 mm grid so the slicer lays down whole perimeters.
    """
    if thickness < MIN_WALL - 1e-9:
        raise ValueError(f"wall {thickness} mm is under the {MIN_WALL} mm minimum")
    n = thickness / NOZZLE
    if abs(n - round(n)) > 1e-6:
        raise ValueError(
            f"wall {thickness} mm is not a multiple of the {NOZZLE} mm nozzle "
            f"(use one of {ALLOWED_WALLS} or another 0.4 multiple)"
        )
    return thickness
