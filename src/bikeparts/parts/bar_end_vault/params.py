"""Parameters for the Vault bar-end plug (docs/PLAN.md part 5)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bikeparts.core.standards import BAR_END_ID


class BarEndVaultParams(BaseModel):
    model_config = ConfigDict(frozen=True)

    bar_id_min: float = Field(default=BAR_END_ID.min_id, ge=14.0, le=24.0)
    bar_id_max: float = Field(default=BAR_END_ID.min_id + 2.5, ge=15.0, le=26.5)
    # source: assumption — 40 mm of tube inside the bar keeps total insertion under ~70 mm,
    # short enough to clear internal routing exits on most bars
    insert_length: float = Field(default=40.0, ge=25.0, le=80.0)
    # source: assumption — covers a 22.2 mm flat-bar end (standards.BARS['22.2']) with margin;
    # drop bars are wrapped in tape so their ends are larger still
    flange_diameter: float = Field(default=24.0, ge=20.0, le=32.0)
    # source: rule 3 — 1.6 mm (4 lines) tube wall
    wall: float = 1.6
    # source: assumption — 5 mm floor under the bolt head; see loads.py for the pull-through check
    floor: float = 5.0
    # source: assumption — detent bump stands this much taller than the lug's axial play; the
    # spigot ring flexes ~0.1 mm per side as the lug cams up the 45° ceiling, giving a click
    # at roughly finger torque. Tune per printer (0 disables the detent).
    detent_interference: float = Field(default=0.10, ge=0.0, le=0.4)

    @model_validator(mode="after")
    def _range(self) -> BarEndVaultParams:
        # source: geometry — the slot wedge keeps ≥ 2 mm walls up to ~3 mm of wedge travel
        if not 1.0 <= self.bar_id_max - self.bar_id_min <= 2.5:
            raise ValueError("bar ID range per printed size must span 1–2.5 mm (wedge travel)")
        # source: geometry — the 45° seating cone needs ≥ 2 mm of radial step over the bar ID
        if self.flange_diameter < self.bar_id_min + 4.0:
            raise ValueError("flange must be ≥ 4 mm wider than the smallest bar ID it fits")
        return self


# Two printed sizes cover the plan's 17–21 mm range (docs/PLAN.md part 5) with overlap.
PRESETS: dict[str, BarEndVaultParams] = {
    "id-17-19.5": BarEndVaultParams(bar_id_min=17.0, bar_id_max=19.5),
    "id-19-21.5": BarEndVaultParams(bar_id_min=19.0, bar_id_max=21.5, flange_diameter=26.0),
}


def sweep() -> list[BarEndVaultParams]:
    return [
        BarEndVaultParams(
            bar_id_min=lo, bar_id_max=lo + span, insert_length=length, flange_diameter=lo + 7.0
        )
        for lo, span, length in (
            (16.0, 1.0, 25.0),
            (18.0, 2.0, 60.0),
            (21.0, 2.5, 40.0),
            (24.0, 2.5, 80.0),
        )
    ]
