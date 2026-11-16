"""The library's dovetail rail: male on clamps, female on heads (docs/PLAN.md parts 1, 4).

This is our own interface, not an OEM one, so its dimensions are design choices:
- 45° flanks, so the male's flare and the female's undercut both print without supports
  (exactly the rule-1 limit);
- a vertical neck under the flare and a vertical cap above it, so neither half has a
  feathered 45° edge.

Profiles are drawn in a local (u, v) plane: u across the rail, v up from the male's base.
Extrude them along the rail axis. The female cutter is the male profile offset by the fit
clearance and hung from the mating surface, so `female_cutter(c)` subtracted from a part
whose top face is at v = 0 gives a slot that the nominal male slides into.
"""

from __future__ import annotations

from typing import cast

import build123d as bd
from pydantic import BaseModel, ConfigDict

from bikeparts.core.tolerances import PRINTER


class Dovetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    # source: design choice — 6 mm neck; 1.6 mm neck height keeps the female's lip ≥ 1.2 mm
    # after the clearance offset; 3 mm of 45° flare gives 12 mm across; a 1.2 mm vertical cap
    # (rule 3) keeps the male's top corners at 135° / 90° instead of a 45° knife edge
    neck_width: float = 6.0
    neck_height: float = 1.6
    flare_height: float = 3.0
    cap_height: float = 1.2

    @property
    def top_width(self) -> float:
        return self.neck_width + 2 * self.flare_height  # 45° flanks

    @property
    def height(self) -> float:
        return self.neck_height + self.flare_height + self.cap_height


RAIL = Dovetail()


def male_profile(d: Dovetail = RAIL) -> bd.Sketch:
    n, w = d.neck_width / 2, d.top_width / 2
    pts = [
        (-n, 0.0),
        (n, 0.0),
        (n, d.neck_height),
        (w, d.neck_height + d.flare_height),
        (w, d.height),
        (-w, d.height),
        (-w, d.neck_height + d.flare_height),
        (-n, d.neck_height),
    ]
    return cast(bd.Sketch, bd.Sketch() + bd.Polygon(*pts, align=None))


def female_profile(clearance: float | None = None, d: Dovetail = RAIL) -> bd.Sketch:
    """Male profile grown by `clearance` per side, flipped to hang below v = 0."""
    c = PRINTER.sliding_fit if clearance is None else clearance
    grown = bd.offset(male_profile(d), c, kind=bd.Kind.INTERSECTION)
    # extend through the mating surface so the slot is open at the top
    grown = grown + bd.Pos(0, -0.5) * bd.Rectangle(d.neck_width + 2 * c, 1.0 + 2 * c)
    return cast(bd.Sketch, bd.Sketch() + bd.mirror(grown, bd.Plane.XZ))


def male_rail(length: float, d: Dovetail = RAIL) -> bd.Part:
    """Male rail standing on Z = 0, running along +Y from Y = 0."""
    return _along_y(male_profile(d), length)


def female_cutter(length: float, clearance: float | None = None, d: Dovetail = RAIL) -> bd.Part:
    """Slot cutter hanging below Z = 0, running along +Y from Y = 0."""
    return _along_y(female_profile(clearance, d), length)


def _along_y(profile: bd.Sketch, length: float) -> bd.Part:
    # Plane.XZ maps local (u, v) → (X, Z) and extrudes toward −Y; flip so it runs +Y.
    solid = bd.extrude(bd.Plane.XZ * profile, amount=-length)
    from bikeparts.core.features import as_part

    return as_part(solid)
