"""Parameters for the shop dummy hub (docs/PLAN.md parts 3 + 10, merged)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bikeparts.core.standards import AXLES


class DummyHubParams(BaseModel):
    model_config = ConfigDict(frozen=True)

    standard: str = Field(description="key into standards.AXLES")
    # source: assumption — Ø30 body: ~470 mm² of PETG in compression, and a bushing for the roller
    body_diameter: float = Field(default=30.0, ge=24.0, le=40.0)
    # source: assumption — rear presets carry the chain roller; set False for a plain spacer
    chain_roller: bool | None = None
    label: bool = True

    @field_validator("standard")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in AXLES:
            raise ValueError(f"unknown axle standard {v!r}; choose from {sorted(AXLES)}")
        return v

    @property
    def has_roller(self) -> bool:
        if self.chain_roller is not None:
            return self.chain_roller
        return AXLES[self.standard].position == "rear"


# One preset per axle standard (docs/PLAN.md part 3). Print each in its own colour so a shop
# can grab the right one at a glance; the standard is also debossed on the body.
PRESETS: dict[str, DummyHubParams] = {
    key.lower(): DummyHubParams(standard=key)
    for key in ("12x142", "12x148", "QR130", "QR135", "QR100", "12x100", "15x100", "15x110")
}


def sweep() -> list[DummyHubParams]:
    return [
        DummyHubParams(standard=s, body_diameter=d)
        for s, d in (("QR130", 24.0), ("12x148", 32.0), ("15x110", 40.0))
    ]
