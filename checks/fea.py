# scikit-fem types mesh arrays as Optional and interpolations as plain tuples; at runtime they
# are always set here. Relax those rules for this wrapper module only.
# pyright: reportOptionalSubscript=false, reportAttributeAccessIssue=false
# pyright: reportCallIssue=false, reportArgumentType=false
"""Gate 2: linear-static FEA screen (docs/PLAN.md Phase 3).

Pipeline: build123d STEP → gmsh (run as a separate program; tets) → scikit-fem with
quadratic (P2) displacement elements → von Mises stress → safety factor against the
material's design strength (tensile × 0.5 interlayer knockdown, structural rule 7).

The plan named CalculiX as the solver. It isn't packaged for Homebrew or pip, so the solve
is done with scikit-fem (BSD) instead; meshing is still gmsh. See docs/DECISIONS.md.

FEA is a screen, not proof: printed parts are anisotropic and porous, and Gate 3 physical
tests override a passing result.

Which stress governs: idealised supports and point-applied loads make artificial peaks at
their edges that grow without bound as the mesh is refined. So, as is standard practice, the
governing von Mises stress is the maximum over elements more than EXCLUDE_MIN from any
loaded or supported face (Saint-Venant), and the bearing stress on those faces is checked
separately: the applied pressure, and the mean contact pressure over each spring support.
The safety factor uses the larger of the two. The raw maximum and the peak contact pressure
at patch edges are reported too — those are where Gate 3 should look.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import build123d as bd
import meshio
import numpy as np
import pyamg
from skfem import (
    Basis,
    BilinearForm,
    ElementTetP2,
    ElementVector,
    FacetBasis,
    Functional,
    LinearForm,
    MeshTet,
    asm,
    condense,
)
from skfem.models.elasticity import lame_parameters, linear_elasticity

from bikeparts.core.loads import LoadCase, Pin, Spring, Support
from bikeparts.core.materials import MIN_SAFETY_FACTOR, Material

# source: assumption — 1.2 mm target element size (≈ 3 nozzle widths), plus a refined run.
# A study on the bar-end wedge (1.2 / 0.8 / 0.55 / 0.4 mm → +14 %, +24 %, +4 %) showed 0.8 mm
# was not converged; 0.55 mm was within 4 % of 0.4 mm.
DEFAULT_H = 1.2
REFINED_H = 0.55
# Contact springs: stiffness = SPRING_FACTOR × E / h, so a 10 MPa contact pressure moves the
# face ~10⁻⁴ mm — rigid next to the part, but without a clamped edge's singularity.
# source: assumption (penalty method); results checked insensitive to ×10 changes
SPRING_FACTOR = 20.0
# source: assumption — exclude elements within 1.5 mm (≈ 4 nozzle widths) of load / support
# faces when finding the governing stress; fixed, so coarse and refined meshes are comparable
EXCLUDE_MIN = 1.5


class FeaError(RuntimeError):
    pass


@dataclass
class FeaResult:
    case: LoadCase
    material: Material
    h: float
    n_tets: int
    raw_max_vm: float
    max_vm: float  # governing: away from load / support faces
    p99_vm: float
    bearing: float  # max applied pressure, or mean contact pressure on a spring support
    contact_peak: float  # highest spring contact pressure at a patch edge (reported only)
    at: tuple[float, float, float]
    max_disp: float
    # for plotting
    points: np.ndarray
    surface_tris: np.ndarray
    surface_vm: np.ndarray

    @property
    def design_strength(self) -> float:
        return self.material.design_strength_mpa

    @property
    def governing(self) -> float:
        return max(self.max_vm, self.bearing)

    @property
    def safety_factor(self) -> float:
        return self.design_strength / self.governing if self.governing > 0 else float("inf")

    @property
    def passes(self) -> bool:
        return self.safety_factor >= MIN_SAFETY_FACTOR


def gmsh_exe() -> str:
    exe = shutil.which("gmsh")
    if exe is None:
        raise FeaError("gmsh not found — `uv sync` installs it (dev group)")
    return exe


def mesh_shape(shape: bd.Shape, h: float, workdir: Path) -> MeshTet:
    step = workdir / "part.step"
    msh = workdir / "part.msh"
    bd.export_step(shape, str(step))
    cmd = [gmsh_exe(), str(step), "-3", "-format", "msh22", "-clmax", str(h), "-clmin", str(h / 3)]
    cmd += ["-o", str(msh), "-v", "1"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0 or not msh.exists():
        raise FeaError(f"gmsh failed: {proc.stderr[-600:] or proc.stdout[-600:]}")
    m = meshio.read(msh)
    tets = m.cells_dict.get("tetra")
    if tets is None or len(tets) == 0:
        raise FeaError("gmsh produced no tetrahedra")
    used = np.unique(tets)
    remap = np.full(len(m.points), -1)
    remap[used] = np.arange(len(used))
    return MeshTet(m.points[used].T, remap[tets].T)


def solve_case(
    shape: bd.Shape, case: LoadCase, material: Material, h: float = DEFAULT_H
) -> FeaResult:
    if material.youngs_modulus_mpa is None or material.poisson_ratio is None:
        raise FeaError(f"{material.name} has no elastic constants")
    with tempfile.TemporaryDirectory() as tmp:
        mesh = mesh_shape(shape, h, Path(tmp))
    lam, mu = lame_parameters(material.youngs_modulus_mpa, material.poisson_ratio)
    elem = ElementVector(ElementTetP2())
    basis = Basis(mesh, elem)
    K = asm(linear_elasticity(lam, mu), basis)

    held: list[np.ndarray] = [np.zeros(0, dtype=np.int64)]
    bc_vertices: list[np.ndarray] = []
    springs: list[tuple[np.ndarray, np.ndarray]] = []  # (facets, normal)
    bearing = 0.0
    contact_peak = 0.0
    k_spring = SPRING_FACTOR * material.youngs_modulus_mpa / h  # N/mm³
    for sup in case.supports:
        if isinstance(sup, Pin):
            v = int(np.argmin(np.linalg.norm(mesh.p.T - np.asarray(sup.at), axis=1)))
            held.append(np.array([basis.nodal_dofs[c, v] for c in sup.components]))
            continue
        facets = mesh.facets_satisfying(sup.where, boundaries_only=True)
        if len(facets) == 0:
            raise FeaError(f"{case.name}: support '{sup.label}' matched no faces")
        bc_vertices.append(np.unique(mesh.facets[:, facets]))
        if isinstance(sup, Support):
            held.append(basis.get_dofs(facets).all([f"u^{c + 1}" for c in sup.components]))
        elif isinstance(sup, Spring):
            n = np.asarray(sup.normal, dtype=float)
            n /= np.linalg.norm(n)

            @BilinearForm
            def spring(u, v, w, n=n):
                un = n[0] * u[0] + n[1] * u[1] + n[2] * u[2]
                vn = n[0] * v[0] + n[1] * v[1] + n[2] * v[2]
                return k_spring * un * vn

            K = K + asm(spring, FacetBasis(mesh, elem, facets=facets))
            springs.append((facets, n))
    f = np.zeros(basis.N)
    for t in case.loads:
        facets = mesh.facets_satisfying(t.where, boundaries_only=True)
        if len(facets) == 0:
            raise FeaError(f"{case.name}: load '{t.label}' matched no faces")
        area = Functional(lambda w: 1.0 + 0.0 * w.x[0]).assemble(
            FacetBasis(mesh, ElementTetP2(), facets=facets)
        )
        traction = np.asarray(t.force) / area
        bearing = max(bearing, float(np.linalg.norm(traction)))
        bc_vertices.append(np.unique(mesh.facets[:, facets]))

        @LinearForm
        def load(v, w, traction=traction):
            return traction[0] * v[0] + traction[1] * v[1] + traction[2] * v[2]

        f += asm(load, FacetBasis(mesh, elem, facets=facets))

    dofs = np.unique(np.concatenate(held))
    A, b, x0, interior = condense(K, f, D=dofs)
    # Elasticity needs the six rigid-body modes as AMG's near-nullspace to converge.
    B = _rigid_body_modes(mesh, basis)[interior]
    ml = pyamg.smoothed_aggregation_solver(A.tocsr(), B=B, symmetry="symmetric", max_coarse=500)
    residuals: list[float] = []
    xi = ml.solve(b, tol=1e-9, accel="cg", maxiter=1000, residuals=residuals)
    if residuals and residuals[-1] > 1e-6 * max(np.linalg.norm(b), 1e-30):
        raise FeaError(f"{case.name}: solver did not converge (residual {residuals[-1]:.2e})")
    u = x0.copy()
    u[interior] = xi

    G = basis.interpolate(u).grad  # (3, 3, n_el, n_qp)
    eps = 0.5 * (G + np.transpose(G, (1, 0, 2, 3)))
    tr = eps[0, 0] + eps[1, 1] + eps[2, 2]
    s = 2 * mu * eps
    for i in range(3):
        s[i, i] += lam * tr
    vm = np.sqrt(
        0.5 * ((s[0, 0] - s[1, 1]) ** 2 + (s[1, 1] - s[2, 2]) ** 2 + (s[2, 2] - s[0, 0]) ** 2)
        + 3 * (s[0, 1] ** 2 + s[1, 2] ** 2 + s[0, 2] ** 2)
    )
    vm_el = vm.max(axis=1)

    # Saint-Venant: judge stress away from where idealised loads / supports are applied
    from scipy.spatial import cKDTree

    bc = mesh.p[:, np.unique(np.concatenate(bc_vertices))].T
    centroids = mesh.p[:, mesh.t].mean(axis=1).T
    dist, _ = cKDTree(bc).query(centroids)
    away = dist > EXCLUDE_MIN
    if not away.any():
        raise FeaError(f"{case.name}: every element is next to a load or support; refine the mesh")
    vm_away = np.where(away, vm_el, 0.0)
    worst = int(vm_away.argmax())
    at = mesh.p[:, mesh.t[:, worst]].mean(axis=1)

    bfac = mesh.boundary_facets()
    tris = mesh.facets[:, bfac].T
    owner = mesh.f2t[0, bfac]
    disp = u[basis.nodal_dofs].T  # (n_nodes, 3) at vertices
    for facets, n in springs:  # contact pressure = k · (u · n), compression or tension
        verts = np.unique(mesh.facets[:, facets])
        pv = np.abs(k_spring * disp[verts] @ n)
        # Mean pressure over the patch governs; the edge peak of a wedge-on-wall contact is a
        # nonlinear contact effect (the plastic conforms) that linear springs can't size.
        bearing = max(bearing, float(pv.mean()))
        contact_peak = max(contact_peak, float(pv.max()))
    return FeaResult(
        case=case,
        material=material,
        h=h,
        n_tets=mesh.t.shape[1],
        raw_max_vm=float(vm_el.max()),
        max_vm=float(vm_away.max()),
        p99_vm=float(np.percentile(vm_el[away], 99)),
        bearing=bearing,
        contact_peak=contact_peak,
        at=(float(at[0]), float(at[1]), float(at[2])),
        max_disp=float(np.linalg.norm(disp, axis=1).max()),
        points=mesh.p.T.copy(),
        surface_tris=tris,
        surface_vm=vm_el[owner],
    )


def _rigid_body_modes(mesh: MeshTet, basis: Basis) -> np.ndarray:
    """(N, 6) translations and rotations about the origin, for P2 vector DOFs."""
    B = np.zeros((basis.N, 6))
    for dofs, locs in ((basis.nodal_dofs, mesh.p), (basis.edge_dofs, _edge_midpoints(mesh))):
        x, y, z = locs
        for c in range(3):
            B[dofs[c], c] = 1.0
        # rotation about Z: (−y, x, 0); about X: (0, −z, y); about Y: (z, 0, −x)
        B[dofs[0], 3], B[dofs[1], 3] = -y, x
        B[dofs[1], 4], B[dofs[2], 4] = -z, y
        B[dofs[0], 5], B[dofs[2], 5] = z, -x
    return B


def _edge_midpoints(mesh: MeshTet) -> np.ndarray:
    return 0.5 * (mesh.p[:, mesh.edges[0]] + mesh.p[:, mesh.edges[1]])


def plot(result: FeaResult, path: Path) -> None:
    """Greyscale von Mises plot on the surface, two views, to match the drawings' style."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    pts, tris, vm = result.points, result.surface_tris, result.surface_vm
    vmax = max(result.max_vm, 1e-9)  # scale to the governing stress; raw peaks saturate
    cmap = plt.get_cmap("Greys")
    fig = plt.figure(figsize=(9, 4.6), dpi=110)
    for k, (elev, azim) in enumerate(((25, -60), (-25, 120))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        polys = pts[tris]
        coll = Poly3DCollection(polys, facecolors=cmap(0.12 + 0.88 * vm / vmax), edgecolors="none")
        ax.add_collection3d(coll)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        c, r = (lo + hi) / 2, (hi - lo).max() / 2
        ax.set_xlim(c[0] - r, c[0] + r)
        ax.set_ylim(c[1] - r, c[1] + r)
        ax.set_zlim(c[2] - r, c[2] + r)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.scatter(*result.at, s=60, facecolors="none", edgecolors="black", linewidths=1.2)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax))
    cb = fig.colorbar(sm, ax=fig.axes, shrink=0.7, pad=0.02)
    cb.set_label("von Mises (MPa)", fontfamily="monospace")
    fig.suptitle(
        f"{result.case.name}: governing {result.max_vm:.1f} MPa (circled), bearing "
        f"{result.bearing:.1f} MPa, SF {result.safety_factor:.1f}",
        fontfamily="monospace",
        fontsize=11,
    )
    fig.savefig(path, facecolor="white")
    plt.close(fig)
