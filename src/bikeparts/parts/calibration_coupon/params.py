"""Parameters for the calibration coupon (docs/PLAN.md Phase 1)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CouponParams(BaseModel):
    model_config = ConfigDict(frozen=True)

    # source: docs/PLAN.md Phase 1 — ladder 0.10 to 0.40 mm per side in 0.05 steps
    ladder: tuple[float, ...] = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40)
    # source: assumption — Ø6 reference peg: big enough to feel, small enough for 7 in a row
    peg_diameter: float = Field(default=6.0, ge=4.0, le=8.0)
    # source: docs/PLAN.md Phase 1 — dovetail pair at three clearances
    dovetail_fits: tuple[float, ...] = (0.15, 0.25, 0.35)
    # source: docs/PLAN.md Phase 1 — teardrop holes at 3 / 5 / 8 mm
    teardrops: tuple[float, ...] = (3.0, 5.0, 8.0)


PRESETS = {"default": CouponParams()}
