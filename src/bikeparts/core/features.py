"""Shared, print-aware geometry features. Written once, reused by every part.

Conventions (CLAUDE.md):
- Build direction is +Z; parts are returned print-oriented on Z = 0.
- Cutters (teardrop_hole, captive_nut_pocket) are returned as solids to subtract.
- Every hole that runs horizontally and is > 3 mm uses `teardrop_hole` (print rule 2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, cast

import build123d as bd

from bikeparts.core.hardware import BOLTS, INSERTS, MIN_INSERT_WALL, HeatSetInsert, HexNut, Thread
from bikeparts.core.tolerances import PRINTER, check_wall

# source: docs/PLAN.md structural rule 4 (minimum 1.0 mm fillet at load-bearing inside corners)
MIN_INSIDE_FILLET = 1.0
# source: docs/PLAN.md print rule 2 (teardrop any horizontal hole over 3 mm)
TEARDROP_THRESHOLD = 3.0
_SQRT2 = math.sqrt(2.0)


def as_part(shape: object) -> bd.Part:
    """Normalise a build123d algebra result to a `Part`.

    build123d's operators are typed as returning `Compound | Wire`; at runtime 3D booleans
    return `Part`. This keeps signatures honest for pyright and fails loudly otherwise.
    """
    if isinstance(shape, bd.Part):
        return shape
    if isinstance(shape, bd.Solid | bd.Compound):
        return cast(bd.Part, bd.Part() + shape)
    raise TypeError(f"expected a 3D shape, got {type(shape).__name__}")


# --------------------------------------------------------------------------- holes


def teardrop_profile(diameter: float, truncate: float | None = None) -> bd.Sketch:
    """2D teardrop in local XY with its tip toward local +Y.

    The tip's flanks are tangent to the circle at 45°, so the ceiling of the printed hole
    never overhangs more than 45°. `truncate` cuts the tip flat at that height above the
    centre (a short bridge) — must stay between r and r·√2.
    """
    if diameter <= 0:
        raise ValueError("diameter must be positive")
    r = diameter / 2
    t = r / _SQRT2
    shape = bd.Circle(r) + bd.Polygon((-t, t), (t, t), (0, r * _SQRT2), align=None)
    if truncate is not None:
        if not r <= truncate <= r * _SQRT2:
            raise ValueError(f"truncate must be in [{r:.3f}, {r * _SQRT2:.3f}] for d={diameter}")
        keep = bd.Rectangle(4 * r, r + truncate, align=(bd.Align.CENTER, bd.Align.MAX))
        shape = shape & bd.Pos(0, truncate) * keep
    return cast(bd.Sketch, shape)


def teardrop_hole(
    diameter: float,
    length: float,
    axis: Literal["X", "Y"] = "Y",
    truncate: float | None = None,
) -> bd.Part:
    """Cutter for a horizontal hole, centred on the origin, tip pointing +Z."""
    if length <= 0:
        raise ValueError("length must be positive")
    profile = teardrop_profile(diameter, truncate)
    tool = bd.extrude(bd.Plane.XZ * profile, amount=length / 2, both=True)
    if axis == "X":
        tool = bd.Rot(0, 0, 90) * tool
    return as_part(tool)


def horizontal_hole(diameter: float, length: float, axis: Literal["X", "Y"] = "Y") -> bd.Part:
    """Round hole cutter if ≤ 3 mm (allowed by rule 2), otherwise a teardrop."""
    if diameter <= TEARDROP_THRESHOLD:
        rot = (90, 0, 0) if axis == "Y" else (0, 90, 0)
        return as_part(bd.Cylinder(diameter / 2, length, rotation=rot))
    return teardrop_hole(diameter, length, axis)


# --------------------------------------------------------------------------- hardware


def insert_boss(
    insert: HeatSetInsert | Thread, height: float, outer_d: float | None = None
) -> bd.Part:
    """Vertical cylindrical boss on Z = 0 with a heat-set insert pocket opening at the top.

    The pocket is vertical so the insert is pressed along +Z; the wall around it is at least
    MIN_INSERT_WALL (structural rule 3).
    """
    ins = INSERTS[insert] if isinstance(insert, str) else insert
    od = ins.boss_diameter if outer_d is None else outer_d
    if od + 1e-9 < ins.boss_diameter:
        raise ValueError(
            f"boss Ø{od} leaves < {MIN_INSERT_WALL} mm around a Ø{ins.pocket_diameter} pocket"
        )
    if height < ins.pocket_depth + 1.2:
        raise ValueError(
            f"boss height {height} must be ≥ pocket depth {ins.pocket_depth} + 1.2 mm floor"
        )
    boss = bd.Cylinder(od / 2, height, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
    pocket = bd.Pos(0, 0, height - ins.pocket_depth) * bd.Cylinder(
        ins.pocket_diameter / 2,
        ins.pocket_depth + 1.0,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
    )
    return as_part(boss - pocket)


def captive_nut_pocket(
    nut: HexNut | Thread, depth: float | None = None, slot: float = 0.0
) -> bd.Part:
    """Cutter: hex pocket with its axis along Z, bottom at Z = 0, flats parallel to X.

    `slot` > 0 extends the pocket along +X by that length (width = across flats) so the nut
    can be slid in from the side. Size includes PRINTER.nut_pocket_flats.
    """
    from bikeparts.core.hardware import NUTS

    n = NUTS[nut] if isinstance(nut, str) else nut
    d = n.thickness + 0.2 if depth is None else depth  # source: assumption, 0.2 mm Z slop
    if d < n.thickness:
        raise ValueError(f"pocket depth {d} is shallower than the nut ({n.thickness})")
    hexagon = bd.RegularPolygon(n.pocket_corners / 2, 6, major_radius=True)
    tool = bd.extrude(hexagon, amount=d)
    if slot > 0:
        tool += bd.extrude(
            bd.Rectangle(slot, n.pocket_flats, align=(bd.Align.MIN, bd.Align.CENTER)), amount=d
        )
    return as_part(tool)


# --------------------------------------------------------------------------- structure


def rib(
    length: float,
    height: float,
    thickness: float,
    profile: Literal["triangle", "rect"] = "triangle",
) -> bd.Part:
    """Stiffening web in the XZ plane, on Z = 0, starting at X = 0, centred on Y = 0.

    The triangle's sloped face faces up and out, so it never overhangs. Thickness must be a
    nozzle multiple (print rule 3).
    """
    check_wall(thickness)
    if length <= 0 or height <= 0:
        raise ValueError("rib length and height must be positive")
    if profile == "triangle":
        sk = bd.Polygon((0, 0), (length, 0), (0, height), align=None)
    else:
        sk = bd.Rectangle(length, height, align=(bd.Align.MIN, bd.Align.MIN))
    return as_part(bd.extrude(bd.Plane.XZ * sk, amount=thickness / 2, both=True))


def bed_chamfer(part: bd.Shape, size: float | None = None, z: float = 0.0) -> bd.Part:
    """Chamfer every edge lying in the bed plane (print rule 4: elephant's-foot relief)."""
    c = PRINTER.bed_chamfer if size is None else size
    edges = [
        e
        for e in part.edges()
        if abs(e.bounding_box().max.Z - z) < 1e-6 and abs(e.bounding_box().min.Z - z) < 1e-6
    ]
    if not edges:
        raise ValueError("no edges on the bed plane — is the part print-oriented on Z = 0?")
    try:
        return as_part(part.chamfer(c, None, edges))  # pyright: ignore[reportAttributeAccessIssue]
    except Exception as exc:  # OCC raises StdFail_NotDone et al.
        raise ValueError(f"bed chamfer {c} mm failed on {len(edges)} edges: {exc}") from exc


# --------------------------------------------------------------------------- clamps


@dataclass(frozen=True)
class SplitClamp:
    """Two halves of a split clamp, both print-oriented with the clamp axis along +Z.

    The ring lies in the XY (layer) plane, so hoop tension runs along the layers
    (structural rules 1 and 2). Bolts run along Y across the split plane Y = 0.
    `bolt_half` (Y > 0) has clearance holes; `insert_half` (Y < 0) has heat-set pockets.
    """

    bolt_half: bd.Part
    insert_half: bd.Part
    bore_diameter: float
    width: float
    gap: float
    ear_thickness: float
    bolt_x: float
    bolt_z: tuple[float, ...]
    thread: Thread

    @property
    def bolt_grip(self) -> float:
        """Bolt shank needed from under the head to the far end of the insert."""
        return self.ear_thickness + self.gap + INSERTS[self.thread].length


def split_clamp(
    bore_diameter: float,
    width: float,
    wall: float = 4.0,
    thread: Thread = "M4",
    bolts_per_side: int = 2,
    gap: float = 1.0,
    fillet: float = MIN_INSIDE_FILLET,
) -> SplitClamp:
    """Two-piece split clamp around a tube of `bore_diameter` (liner allowance already added).

    `wall` is the ring wall and must be a nozzle multiple. `gap` is the total gap between the
    halves when assembled, so the bolts can pull the halves onto the tube.
    """
    check_wall(wall)
    if bolts_per_side < 1:
        raise ValueError("need at least one bolt per side")
    ins = INSERTS[thread]
    bolt = BOLTS[thread]
    r_bore = bore_diameter / 2
    r_out = r_bore + wall
    boss = ins.boss_diameter
    ear_t = ins.pocket_depth + 1.6  # source: assumption — 1.6 mm (4 lines) floor behind pocket
    if ear_t >= r_out:
        raise ValueError(
            f"ear thickness {ear_t:.2f} ≥ ring radius {r_out:.2f}; increase wall or bore"
        )
    # Bolt axis far enough out that (a) the insert keeps its rule-3 wall to the bore and
    # (b) the bolt head seats on the ear face clear of the ring's shoulder.
    ring_x_at_ear = math.sqrt(r_out**2 - ear_t**2)
    bolt_x = max(r_bore + boss / 2, ring_x_at_ear + bolt.counterbore_diameter / 2)
    ear_end = bolt_x + boss / 2
    pitch = width / bolts_per_side
    if pitch < boss:
        raise ValueError(f"width {width} too narrow for {bolts_per_side} bosses of Ø{boss:.1f}")
    bolt_z = tuple(pitch * (i + 0.5) for i in range(bolts_per_side))

    # Half profile above the split line, in XY, before shifting by gap/2.
    ring = bd.Circle(r_out) & bd.Rectangle(2 * r_out, r_out, align=(bd.Align.CENTER, bd.Align.MIN))
    ears = bd.Rectangle(2 * ear_end, ear_t, align=(bd.Align.CENTER, bd.Align.MIN))
    outline = (ring + ears).faces()[0]
    # Fillet the concave ear-to-ring junctions (rule 4) and the ear tips.
    fillet_vs = [v for v in outline.vertices() if v.Y > 1e-6]
    outline = outline.fillet_2d(fillet, fillet_vs)
    profile = cast(bd.Sketch, bd.Sketch() + outline - bd.Circle(r_bore))

    half = bd.extrude(bd.Pos(0, gap / 2) * profile, amount=width)
    half = bed_chamfer(half)

    y0 = gap / 2
    bolt_half = half
    insert_half = half
    for sx in (-1, 1):
        for z in bolt_z:
            hole = teardrop_hole(bolt.clearance_diameter, ear_t + 2.0)
            bolt_half = bolt_half - bd.Pos(sx * bolt_x, y0 + ear_t / 2, z) * hole
            pocket = teardrop_hole(ins.pocket_diameter, ins.pocket_depth + 0.2)
            insert_half = (
                insert_half
                - bd.Pos(sx * bolt_x, y0 + (ins.pocket_depth + 0.2) / 2 - 0.2, z) * pocket
            )

    insert_half = bd.mirror(insert_half, bd.Plane.XZ)
    return SplitClamp(
        bolt_half=as_part(bolt_half),
        insert_half=as_part(insert_half),
        bore_diameter=bore_diameter,
        width=width,
        gap=gap,
        ear_thickness=ear_t,
        bolt_x=bolt_x,
        bolt_z=bolt_z,
        thread=thread,
    )
