"""Filament properties used for material choice and (Phase 3) FEA.

IMPORTANT: every number here is a *typical* value, flagged `verified=False`. Filaments
vary a lot by brand and print settings. Before Phase 3 FEA, replace each figure you use
with the datasheet value for the exact filament you print, set `source` to that datasheet
and flip `verified=True`. The FEA check refuses unverified materials.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# source: docs/PLAN.md structural rule 7 (0.5 knockdown for interlayer strength)
INTERLAYER_KNOCKDOWN = 0.5
# source: docs/PLAN.md structural rule 7
MIN_SAFETY_FACTOR = 3.0
# source: docs/PLAN.md structural rule 6 (parked car)
HEAT_FLOOR_C = 70.0


class MaterialName(StrEnum):
    PLA = "PLA"
    PETG = "PETG"
    ASA = "ASA"
    PA_CF = "PA-CF"
    TPU_95A = "TPU 95A"


class Material(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: MaterialName
    use_for: str
    tensile_strength_mpa: float | None = Field(
        description="in-plane (XY) tensile strength; None for elastomers"
    )
    youngs_modulus_mpa: float | None
    poisson_ratio: float | None
    glass_transition_c: float | None
    density_g_cm3: float
    needs_enclosure: bool
    needs_hardened_nozzle: bool
    source: str
    verified: bool = False

    @property
    def design_strength_mpa(self) -> float:
        """Strength used for safety factor: tensile × interlayer knockdown (rule 7)."""
        if self.tensile_strength_mpa is None:
            raise ValueError(f"{self.name} has no tensile strength (elastomer)")
        return self.tensile_strength_mpa * INTERLAYER_KNOCKDOWN

    @property
    def allowed_on_bike(self) -> bool:
        """Rule 6: anything that lives on the bike must survive the 70 °C heat floor."""
        if self.name is MaterialName.TPU_95A:
            return True  # elastomer: used for pads/liners, no load-bearing Tg limit
        return self.glass_transition_c is not None and self.glass_transition_c > HEAT_FLOOR_C


_TYPICAL = (
    "UNVERIFIED typical value from memory for a generic filament; replace with the "
    "datasheet of the filament you buy"
)

MATERIALS: dict[MaterialName, Material] = {
    MaterialName.PLA: Material(
        name=MaterialName.PLA,
        use_for="Calibration coupons and prototypes only — never on the bike (rule 6)",
        tensile_strength_mpa=50.0,
        youngs_modulus_mpa=2300.0,
        poisson_ratio=0.35,
        glass_transition_c=60.0,
        density_g_cm3=1.24,
        needs_enclosure=False,
        needs_hardened_nozzle=False,
        source=_TYPICAL,
    ),
    MaterialName.PETG: Material(
        name=MaterialName.PETG,
        use_for="General on-bike parts, shop tools (default)",
        tensile_strength_mpa=45.0,
        youngs_modulus_mpa=1800.0,
        poisson_ratio=0.38,
        glass_transition_c=80.0,  # source: docs/PLAN.md material table (~80 °C)
        density_g_cm3=1.27,
        needs_enclosure=False,
        needs_hardened_nozzle=False,
        source=_TYPICAL,
    ),
    MaterialName.ASA: Material(
        name=MaterialName.ASA,
        use_for="Parts in constant sun (UV-stable)",
        tensile_strength_mpa=40.0,
        youngs_modulus_mpa=1900.0,
        poisson_ratio=0.35,
        glass_transition_c=100.0,  # source: docs/PLAN.md material table (~100 °C)
        density_g_cm3=1.07,
        needs_enclosure=True,
        needs_hardened_nozzle=False,
        source=_TYPICAL,
    ),
    MaterialName.PA_CF: Material(
        name=MaterialName.PA_CF,
        use_for="Clamps and mounts under vibration (stiffest; dry before printing)",
        tensile_strength_mpa=70.0,
        youngs_modulus_mpa=5000.0,
        poisson_ratio=0.35,
        glass_transition_c=100.0,  # source: docs/PLAN.md material table (~100 °C+, varies)
        density_g_cm3=1.15,
        needs_enclosure=True,
        needs_hardened_nozzle=True,
        source=_TYPICAL,
    ),
    MaterialName.TPU_95A: Material(
        name=MaterialName.TPU_95A,
        use_for="Shims, liners, jaw covers, bumpers — anything touching paint or carbon",
        tensile_strength_mpa=None,
        youngs_modulus_mpa=None,
        poisson_ratio=None,
        glass_transition_c=None,  # source: docs/PLAN.md material table (n/a, elastomer)
        density_g_cm3=1.21,
        needs_enclosure=False,
        needs_hardened_nozzle=False,
        source=_TYPICAL,
    ),
}
