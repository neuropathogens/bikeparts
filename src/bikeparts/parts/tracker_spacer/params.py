"""Parameters for the Ghost tracker spacer (docs/PLAN.md part 2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bikeparts.core.standards import AIRTAG, BOTTLE_BOSSES


class TrackerSpacerParams(BaseModel):
    model_config = ConfigDict(frozen=True)

    tube_diameter: float = Field(ge=25.0, le=120.0, description="frame tube under the bosses")
    boss_spacing: float = Field(default=BOTTLE_BOSSES.spacing, description="see standards")
    tag_diameter: float = Field(default=AIRTAG.diameter)
    tag_thickness: float = Field(default=AIRTAG.thickness)
    # source: rule 3 nozzle multiples — 2.4 mm floor under the tag, 2.0 mm pocket side walls
    floor: float = 2.4
    side_wall: float = 2.0
    # source: assumption — 80 mm covers a bottle cage's base plate with margin past both bolts
    length: float = Field(default=80.0, ge=70.0, le=120.0)
    # source: rule 3 — 1.2 mm TPU pad (3 lines); also sets the saddle radius allowance
    pad_thickness: float = 1.2
    # source: assumption — wings hug the tube by at most 6 mm so the spacer stays low-profile
    wrap_max: float = 6.0
    label: bool = True


# Presets: common round tube diameters that carry bottle bosses.
# source: assumption — 28.6/31.8 steel & alloy seat tubes, 35–50 mm alloy/carbon down tubes;
# oval tubes: pick the preset closest to the tube's width across the bosses.
PRESETS: dict[str, TrackerSpacerParams] = {
    f"tube-{d:g}": TrackerSpacerParams(tube_diameter=d)
    for d in (35.0, 28.6, 31.8, 38.0, 44.0, 50.0)
}


def sweep() -> list[TrackerSpacerParams]:
    return [TrackerSpacerParams(tube_diameter=d) for d in (25.0, 30.0, 40.0, 60.0, 90.0, 120.0)]
