"""Black-and-white orthographic drawing (front / top / right / iso) as SVG.

Hidden-line removal comes from OpenCascade (build123d `project_to_viewport`). Overall
dimensions are drawn on the front and top views. Part-specific dimensions are added in
later phases by passing extra `Dim`s.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import build123d as bd
import numpy as np

_VIEWS = {
    # name: (direction from centre to eye, up vector)
    "FRONT": ((0, -1, 0), (0, 0, 1)),
    "TOP": ((0, 0, 1), (0, 1, 0)),
    "RIGHT": ((1, 0, 0), (0, 0, 1)),
    "ISO": ((1, -1, 1), (0, 0, 1)),
}
_LAYOUT = {"FRONT": (0, 1), "TOP": (0, 0), "RIGHT": (1, 1), "ISO": (1, 0)}


@dataclass
class _View:
    visible: list[np.ndarray]
    hidden: list[np.ndarray]
    lo: np.ndarray
    hi: np.ndarray


def _polyline(edge: bd.Edge) -> np.ndarray:
    n = 2 if edge.geom_type == bd.GeomType.LINE else max(8, int(edge.length / 0.5))
    n = min(n, 200)
    pts = [edge.position_at(t) for t in np.linspace(0, 1, n)]
    return np.array([(p.X, p.Y) for p in pts])


def _project(
    shape: bd.Shape, direction: tuple[float, float, float], up: tuple[float, float, float]
) -> _View:
    c = shape.bounding_box().center()
    eye = c + bd.Vector(*direction).normalized() * 2000
    vis, hid = shape.project_to_viewport(eye, up, c)  # pyright: ignore[reportAttributeAccessIssue]
    visible = [_polyline(e) for e in vis]
    hidden = [_polyline(e) for e in hid]
    allpts = np.vstack(visible + hidden) if visible or hidden else np.zeros((1, 2))
    return _View(visible, hidden, allpts.min(axis=0), allpts.max(axis=0))


def drawing_svg(shape: bd.Shape, title: str, subtitle: str = "") -> str:
    views = {k: _project(shape, d, u) for k, (d, u) in _VIEWS.items()}
    bb = shape.bounding_box()
    cell = max(float(np.max(v.hi - v.lo)) for v in views.values())
    cell_px = 300.0
    scale = cell_px / max(cell, 1e-6) * 0.72
    margin, title_h = 30.0, 60.0
    w = margin * 2 + cell_px * 2
    h = margin * 2 + cell_px * 2 + title_h
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
        f'width="{w:.0f}" height="{h:.0f}" font-family="IBM Plex Mono, monospace">',
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="#fff"/>',
    ]

    def to_px(view: _View, col: int, row: int, pts: np.ndarray) -> np.ndarray:
        mid = (view.lo + view.hi) / 2
        cx = margin + cell_px * (col + 0.5)
        cy = margin + cell_px * (row + 0.5)
        return np.column_stack(
            [cx + (pts[:, 0] - mid[0]) * scale, cy - (pts[:, 1] - mid[1]) * scale]
        )

    def path(pts: np.ndarray) -> str:
        return " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)

    for name, view in views.items():
        col, row = _LAYOUT[name]
        out.append(f'<g id="{name.lower()}">')
        for pl in view.hidden:
            out.append(
                f'<polyline points="{path(to_px(view, col, row, pl))}" fill="none" '
                'stroke="#000" stroke-width="0.5" stroke-dasharray="3,2"/>'
            )
        for pl in view.visible:
            out.append(
                f'<polyline points="{path(to_px(view, col, row, pl))}" fill="none" '
                'stroke="#000" stroke-width="1.1" stroke-linejoin="round"/>'
            )
        lo = to_px(view, col, row, view.lo[None, :])[0]
        hi = to_px(view, col, row, view.hi[None, :])[0]
        x0, x1 = min(lo[0], hi[0]), max(lo[0], hi[0])
        y0, y1 = min(lo[1], hi[1]), max(lo[1], hi[1])
        lx = margin + cell_px * col + 8
        ly = margin + cell_px * row + 16
        out.append(f'<text x="{lx:.0f}" y="{ly:.0f}" font-size="11">{name}</text>')
        if name == "FRONT":
            out += _dim_h(x0, x1, y1 + 18, f"{bb.size.X:.1f}")
            out += _dim_v(x1 + 18, y0, y1, f"{bb.size.Z:.1f}")
        elif name == "TOP":
            out += _dim_v(x1 + 18, y0, y1, f"{bb.size.Y:.1f}")
        out.append("</g>")

    ty = h - title_h + 10
    out.append(f'<line x1="{margin}" y1="{ty}" x2="{w - margin}" y2="{ty}" stroke="#000"/>')
    out.append(
        f'<text x="{margin}" y="{ty + 22}" font-size="15" font-weight="600">{escape(title)}</text>'
    )
    out.append(
        f'<text x="{margin}" y="{ty + 40}" font-size="10">{escape(subtitle)} · units mm · '
        f"+Z = build direction · bbox {bb.size.X:.1f} × {bb.size.Y:.1f} × {bb.size.Z:.1f}</text>"
    )
    out.append("</svg>")
    return "\n".join(out)


def _line(x1: float, y1: float, x2: float, y2: float, width: float = 0.6) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="#000" stroke-width="{width}"/>'
    )


def _dim_h(x0: float, x1: float, y: float, label: str) -> list[str]:
    mid = (x0 + x1) / 2
    return [
        _line(x0, y, x1, y),
        _line(x0, y - 4, x0, y + 4),
        _line(x1, y - 4, x1, y + 4),
        f'<text x="{mid:.1f}" y="{y - 3:.1f}" font-size="10" text-anchor="middle">{label}</text>',
    ]


def _dim_v(x: float, y0: float, y1: float, label: str) -> list[str]:
    cy = (y0 + y1) / 2
    tx = x + 4
    return [
        _line(x, y0, x, y1),
        _line(x - 4, y0, x + 4, y0),
        _line(x - 4, y1, x + 4, y1),
        f'<text x="{tx:.1f}" y="{cy:.1f}" font-size="10" text-anchor="middle" dy="-2" '
        f'transform="rotate(-90 {tx:.1f} {cy:.1f})">{label}</text>',
    ]


def write_drawing(shape: bd.Shape, path: Path, title: str, subtitle: str = "") -> None:
    path.write_text(drawing_svg(shape, title, subtitle), encoding="utf-8")
