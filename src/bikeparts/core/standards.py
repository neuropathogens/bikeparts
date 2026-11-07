"""Bicycle interface dimensions: handlebars, seatposts, axles, bottle bosses.

Every entry carries a `source`. "Industry nominal" means a size sold under that name
across manufacturers rather than one governed by a single published spec; `verified`
stays False until confirmed with calipers on a real part (photo in test-reports/).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Sourced(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    source: str
    verified: bool = False


class BarClamp(Sourced):
    diameter: float


class Seatpost(Sourced):
    diameter: float


class Axle(Sourced):
    kind: Literal["QR", "thru"]
    position: Literal["front", "rear"]
    hub_width: float  # over-locknut dimension (OLD), dropout face to dropout face
    axle_diameter: float  # thru-axle shaft, or the QR hollow axle end that sits in the dropout
    skewer_diameter: float | None = None  # QR skewer rod passed through a spacer


class BottleBosses(Sourced):
    spacing: float  # centre-to-centre
    thread: Literal["M5"]


_BAR = "Industry-nominal handlebar clamp diameter (sold as '{d}'); caliper-verify per bar"
BARS: dict[str, BarClamp] = {
    "22.2": BarClamp(name="22.2 mm", diameter=22.2, source=_BAR.format(d="22.2 mm")),
    "25.4": BarClamp(name="25.4 mm", diameter=25.4, source=_BAR.format(d="25.4 mm")),
    "31.8": BarClamp(name="31.8 mm", diameter=31.8, source=_BAR.format(d="31.8 mm")),
    "35.0": BarClamp(name="35.0 mm", diameter=35.0, source=_BAR.format(d="35 mm")),
}

_POST = "Industry-nominal round seatpost diameter (sold as '{d}'); caliper-verify per post"
SEATPOSTS: dict[str, Seatpost] = {
    d: Seatpost(name=f"{d} mm", diameter=float(d), source=_POST.format(d=f"{d} mm"))
    for d in ("27.2", "30.9", "31.6", "34.9")
}

_QR = (
    "Industry-nominal QR hub: {old} mm OLD, {ax} mm hollow axle ends, 5 mm skewer rod "
    "(common practice, from memory) — caliper-verify"
)
_TA = "Industry-nominal thru-axle standard named '{n}' ({ax} mm shaft × {old} mm OLD)"
AXLES: dict[str, Axle] = {
    "QR100": Axle(
        name="QR 100 front",
        kind="QR",
        position="front",
        hub_width=100.0,
        axle_diameter=9.0,
        skewer_diameter=5.0,
        source=_QR.format(old=100, ax=9),
    ),
    "QR130": Axle(
        name="QR 130 rear (road)",
        kind="QR",
        position="rear",
        hub_width=130.0,
        axle_diameter=10.0,
        skewer_diameter=5.0,
        source=_QR.format(old=130, ax=10),
    ),
    "QR135": Axle(
        name="QR 135 rear (MTB)",
        kind="QR",
        position="rear",
        hub_width=135.0,
        axle_diameter=10.0,
        skewer_diameter=5.0,
        source=_QR.format(old=135, ax=10),
    ),
    "12x100": Axle(
        name="12×100 front",
        kind="thru",
        position="front",
        hub_width=100.0,
        axle_diameter=12.0,
        source=_TA.format(n="12x100", ax=12, old=100),
    ),
    "15x100": Axle(
        name="15×100 front",
        kind="thru",
        position="front",
        hub_width=100.0,
        axle_diameter=15.0,
        source=_TA.format(n="15x100", ax=15, old=100),
    ),
    "15x110": Axle(
        name="15×110 front (Boost)",
        kind="thru",
        position="front",
        hub_width=110.0,
        axle_diameter=15.0,
        source=_TA.format(n="15x110 Boost", ax=15, old=110),
    ),
    "12x142": Axle(
        name="12×142 rear",
        kind="thru",
        position="rear",
        hub_width=142.0,
        axle_diameter=12.0,
        source=_TA.format(n="12x142", ax=12, old=142),
    ),
    "12x148": Axle(
        name="12×148 rear (Boost)",
        kind="thru",
        position="rear",
        hub_width=148.0,
        axle_diameter=12.0,
        source=_TA.format(n="12x148 Boost", ax=12, old=148),
    ),
}

BOTTLE_BOSSES = BottleBosses(
    name="Bottle cage bosses",
    spacing=64.0,  # source: docs/PLAN.md part 2 ("standard 64 mm M5 bosses")
    thread="M5",
    source="Industry-nominal 64 mm M5 bottle-cage bosses (docs/PLAN.md part 2); caliper-verify",
)
