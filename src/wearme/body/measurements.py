"""Body measurement calculations from SMPL vertices.

Computes standard clothing measurements by slicing the SMPL mesh with
horizontal planes and measuring the resulting cross-section perimeters using
``trimesh``. All measurements are returned in metres.

Coordinate system (SMPL):
    Y axis = vertical (up)
    X axis = left/right
    Z axis = front/back

Usage::

    from wearme.body.measurements import compute_measurements
    from wearme.body.body_params import BodyParameters

    params = BodyParameters()
    measurements = compute_measurements(params)
    print(measurements["chest_m"], measurements["height_m"])
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import trimesh

from wearme.body.body_params import BodyParameters
from wearme.body.smpl_bridge import SMPLModelData, generate_vertices, load_model_data

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_PLANE_NORMAL = np.array([0.0, 1.0, 0.0])  # horizontal plane (Y up)

#: Vertical slice half-thickness for vertex-based cross-section sampling (metres)
_SLICE_TOLERANCE_M: float = 0.010

#: Minimum number of cross-section points required for a convex hull estimate
_MIN_CROSS_SECTION_POINTS: int = 3

# ── Internal helpers ──────────────────────────────────────────────────────────


def _circumference_at_height(
    vertices: np.ndarray,
    y: float,
    tolerance: float = _SLICE_TOLERANCE_M,
) -> float:
    """Estimate circumference at a height from raw vertex slice (convex hull).

    Selects all vertices within *tolerance* metres of height *y*, projects
    them onto the XZ plane, and returns the convex hull perimeter.

    Note: This is a lower-level utility. For accurate measurements use
    :func:`_section_length` which works on the full mesh topology.

    Args:
        vertices: Mesh vertices. Shape ``(N, 3)``.
        y: Measurement height (Y coordinate) in metres.
        tolerance: Half-thickness of the horizontal slice.

    Returns:
        Approximate circumference in metres. Returns 0.0 when fewer than
        ``_MIN_CROSS_SECTION_POINTS`` vertices fall in the slice.
    """
    from scipy.spatial import ConvexHull  # noqa: PLC0415

    mask = np.abs(vertices[:, 1] - y) < tolerance
    pts = np.unique(vertices[mask][:, [0, 2]], axis=0)  # XZ projection

    if len(pts) < _MIN_CROSS_SECTION_POINTS:
        return 0.0

    try:
        hull = ConvexHull(pts)
    except Exception:  # noqa: BLE001
        return 0.0

    verts = pts[hull.vertices]
    closed = np.vstack([verts, verts[0]])
    return float(np.sum(np.linalg.norm(np.diff(closed, axis=0), axis=1)))


def _build_mesh(params: BodyParameters, model_data: SMPLModelData) -> trimesh.Trimesh:
    """Generate a trimesh Trimesh from body parameters.

    Args:
        params: Body parameters.
        model_data: Loaded SMPL model data.

    Returns:
        Trimesh mesh object.
    """
    vertices = generate_vertices(params, model_data)
    return trimesh.Trimesh(
        vertices=vertices,
        faces=model_data.faces,
        process=False,
    )


def _section_length(mesh: trimesh.Trimesh, y: float) -> float:
    """Measure the torso circumference at a horizontal cross-section at height *y*.

    In T-pose the cross-section at chest/waist/hip height may include multiple
    disconnected loops (torso + arms + legs). This function isolates the loop
    whose centroid is closest to the body's central axis (X≈0, Z≈0) — i.e. the
    torso loop.

    Args:
        mesh: Trimesh mesh (SMPL body in T-pose).
        y: Height in metres (SMPL Y axis).

    Returns:
        Torso cross-section perimeter in metres. Returns 0.0 if the plane does
        not intersect the mesh at this height.
    """
    plane_origin = np.array([0.0, y, 0.0])
    section = mesh.section(
        plane_normal=_PLANE_NORMAL,
        plane_origin=plane_origin,
    )
    if section is None:
        logger.debug("No cross-section at y=%.3f", y)
        return 0.0

    path_2d, _ = section.to_2D()

    # Path2D may contain multiple discrete closed curves (torso + arms + legs).
    # Pick the one whose centroid is nearest to the body axis (2D origin = 0,0).
    if len(path_2d.entities) == 1:
        return float(path_2d.length)

    best_length = 0.0
    best_dist = float("inf")
    for entity in path_2d.entities:
        pts = path_2d.vertices[entity.points]
        centroid = pts.mean(axis=0)
        dist = float(np.linalg.norm(centroid))
        # Compute length of this entity
        closed = np.vstack([pts, pts[0]])
        length = float(np.sum(np.linalg.norm(np.diff(closed, axis=0), axis=1)))
        if dist < best_dist:
            best_dist = dist
            best_length = length

    return best_length


def _scan_for_extremum(
    mesh: trimesh.Trimesh,
    y_min: float,
    y_max: float,
    find_max: bool,
    n_steps: int = 30,
) -> tuple[float, float]:
    """Scan heights to find the max or min circumference in a range.

    Args:
        mesh: Body mesh.
        y_min: Lower bound of search range.
        y_max: Upper bound of search range.
        find_max: If ``True``, find the widest cross-section; otherwise the narrowest.
        n_steps: Number of heights to evaluate.

    Returns:
        Tuple ``(best_y, best_circumference)`` in metres.
    """
    heights = np.linspace(y_min, y_max, n_steps)
    results = [(h, _section_length(mesh, h)) for h in heights]
    valid = [(h, c) for h, c in results if c > 0.0]
    if not valid:
        mid = (y_min + y_max) / 2.0
        return mid, 0.0
    if find_max:
        return max(valid, key=lambda x: x[1])
    return min(valid, key=lambda x: x[1])


# ── Public API ────────────────────────────────────────────────────────────────


def compute_measurements(
    params: BodyParameters,
    model_data: SMPLModelData | None = None,
) -> dict[str, float]:
    """Compute standard body measurements from SMPL mesh in T-pose.

    If *model_data* is not provided, the SMPL model is loaded automatically
    using ``params.gender``.

    Args:
        params: Body parameters used to generate the shaped mesh.
        model_data: Optional pre-loaded
            :class:`~wearme.body.smpl_bridge.SMPLModelData`.
            Pass this when calling in a loop to avoid re-loading the model.

    Returns:
        Dictionary of measurements, all values in **metres**:

        - ``"height_m"``: total standing height (Y range of vertices)
        - ``"chest_m"``: chest circumference at fullest chest level
        - ``"waist_m"``: waist circumference at the narrowest midsection
        - ``"hips_m"``: hip circumference at the fullest hip level
        - ``"chest_y"``, ``"waist_y"``, ``"hips_y"``: Y heights used
    """
    if model_data is None:
        model_data = load_model_data(params.gender)

    mesh = _build_mesh(params, model_data)

    y_min = float(mesh.vertices[:, 1].min())
    y_max = float(mesh.vertices[:, 1].max())
    height = y_max - y_min

    # Empirical height fractions for SMPL (neutral T-pose, Y range ≈ -1.16 to 0.56):
    #   Chest band: 68-76% — fullest chest, safely BELOW the shoulder junction (≈80%)
    #               where arms+torso merge into a complex cross-section.
    #   Hip band:   44-58% — fullest hip/seat level
    #   Waist band: 57-69% — narrowest midsection between chest and hips
    chest_band = (y_min + 0.68 * height, y_min + 0.76 * height)
    hip_band = (y_min + 0.44 * height, y_min + 0.58 * height)
    waist_band = (y_min + 0.57 * height, y_min + 0.69 * height)

    chest_y, chest_m = _scan_for_extremum(mesh, *chest_band, find_max=True)
    hips_y, hips_m = _scan_for_extremum(mesh, *hip_band, find_max=True)
    waist_y, waist_m = _scan_for_extremum(mesh, *waist_band, find_max=False)

    logger.debug(
        "Measurements — height: %.3fm  chest: %.3fm (y=%.3f)  "
        "waist: %.3fm (y=%.3f)  hips: %.3fm (y=%.3f)",
        height,
        chest_m,
        chest_y,
        waist_m,
        waist_y,
        hips_m,
        hips_y,
    )

    return {
        "height_m": round(height, 4),
        "chest_m": round(chest_m, 4),
        "waist_m": round(waist_m, 4),
        "hips_m": round(hips_m, 4),
        "chest_y": round(chest_y, 4),
        "waist_y": round(waist_y, 4),
        "hips_y": round(hips_y, 4),
    }
