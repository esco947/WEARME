"""Mesh-based body measurements using trimesh cross-sections.

All measurements are in **metres**.

The only public function is ``measure_mesh(vertices, faces, joints)``, which
returns a dict with keys matching the slider names in ``body_schema.SLIDERS``
plus a ``"height"`` key:

    {
        "height":               float,   # m
        "chest_circumference":  float,   # m
        "waist_circumference":  float,   # m
        "hip_circumference":    float,   # m
        "shoulder_width":       float,   # m
        "inseam":               float,   # m
    }

SMPL joint indices (standard v1.1.0):
    0=pelvis, 1=L_hip, 2=R_hip, 3=spine1, 4=L_knee, 5=R_knee,
    6=spine2, 7=L_ankle, 8=R_ankle, 9=spine3, 10=L_foot, 11=R_foot,
    12=neck, 13=L_collar, 14=R_collar, 15=head,
    16=L_shoulder, 17=R_shoulder, 18=L_elbow, 19=R_elbow,
    20=L_wrist, 21=R_wrist, 22=L_hand, 23=R_hand

Usage::

    from core.smpl_model import load_smpl
    from core.mesh_measurements import measure_mesh
    import numpy as np

    model = load_smpl("male")
    verts = model.forward(np.zeros(10))
    joints = model.get_joints(np.zeros(10))
    m = measure_mesh(verts, model.faces, joints)
    print(m)
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Y-axis is vertical in SMPL.
_PLANE_NORMAL = np.array([0.0, 1.0, 0.0])

# SMPL joint indices used for measurements
_IDX_L_SHOULDER = 16
_IDX_R_SHOULDER = 17
_IDX_L_ANKLE    = 7
_IDX_R_ANKLE    = 8
_IDX_PELVIS     = 0


def _section_length(mesh, y: float) -> float:
    """Return the circumference (m) of the mesh cross-section at height *y*.

    When the plane intersects multiple disconnected loops (e.g. between the
    legs), we return the largest loop closest to the body axis (X=0, Z=0).
    """
    import trimesh  # noqa: PLC0415

    try:
        section = mesh.section(
            plane_normal=_PLANE_NORMAL,
            plane_origin=np.array([0.0, y, 0.0]),
        )
    except Exception:
        return 0.0

    if section is None:
        return 0.0

    try:
        path_2d, _ = section.to_2D()
    except Exception:
        return 0.0

    if len(path_2d.entities) == 0:
        return 0.0
    if len(path_2d.entities) == 1:
        return float(path_2d.length)

    # Multiple loops — pick the one whose centroid is closest to the origin
    best_length = 0.0
    best_dist   = float("inf")
    for entity in path_2d.entities:
        pts      = path_2d.vertices[entity.points]
        centroid = pts.mean(axis=0)
        dist     = float(np.linalg.norm(centroid))
        closed   = np.vstack([pts, pts[0]])
        length   = float(np.sum(np.linalg.norm(np.diff(closed, axis=0), axis=1)))
        if dist < best_dist and length > 0.0:
            best_dist   = dist
            best_length = length
    return best_length


def _scan_band(
    mesh,
    y_lo: float,
    y_hi: float,
    find_max: bool,
    n_steps: int = 30,
) -> float:
    """Scan *n_steps* cross-sections between *y_lo* and *y_hi*.

    Returns the maximum circumference (chest/hip) or minimum (waist).
    """
    heights = np.linspace(y_lo, y_hi, n_steps)
    results = [(h, _section_length(mesh, h)) for h in heights]
    valid   = [(h, c) for h, c in results if c > 0.0]
    if not valid:
        return 0.0
    if find_max:
        return max(valid, key=lambda x: x[1])[1]
    return min(valid, key=lambda x: x[1])[1]


def measure_mesh(
    vertices: np.ndarray,
    faces: np.ndarray,
    joints: np.ndarray | None = None,
) -> dict[str, float]:
    """Compute body measurements from SMPL mesh vertices.

    Args:
        vertices: Mesh vertices ``(6890, 3)`` in metres.
        faces:    Triangle face indices ``(13776, 3)``.
        joints:   Joint positions ``(24, 3)`` in metres.  Optional — used for
                  shoulder width.  If None, shoulder width is estimated from
                  the vertex extent.

    Returns:
        Dict with keys: ``height``, ``chest_circumference``,
        ``waist_circumference``, ``hip_circumference``, ``shoulder_width``,
        ``inseam``.  All values in metres.
    """
    import trimesh  # noqa: PLC0415

    mesh  = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    y_min = float(vertices[:, 1].min())
    y_max = float(vertices[:, 1].max())
    h     = y_max - y_min

    # ── Height ────────────────────────────────────────────────────────────────
    height = h

    # ── Circumferences ─────────────────────────────────────────────────────────
    # Y-fraction bands calibrated on SMPL v1.1.0 male/female T-pose.
    # Arms connect at frac≥0.76 and produce a spike (>2m) — stay below.
    # Crotch produces a spike at frac≈0.46 — avoid with hip_lo=0.48.
    chest_circ = _scan_band(mesh, y_min + 0.68 * h, y_min + 0.74 * h, find_max=True)
    waist_circ = _scan_band(mesh, y_min + 0.58 * h, y_min + 0.68 * h, find_max=False)
    hip_circ   = _scan_band(mesh, y_min + 0.48 * h, y_min + 0.56 * h, find_max=True)

    # ── Shoulder width ────────────────────────────────────────────────────────
    if joints is not None and joints.shape == (24, 3):
        shoulder_width = float(
            np.linalg.norm(joints[_IDX_L_SHOULDER] - joints[_IDX_R_SHOULDER])
        )
    else:
        # Fallback: X-extent of vertices in the shoulder band
        shoulder_band_mask = (
            (vertices[:, 1] >= y_min + 0.80 * h) &
            (vertices[:, 1] <= y_min + 0.90 * h)
        )
        if shoulder_band_mask.any():
            band_verts = vertices[shoulder_band_mask]
            shoulder_width = float(band_verts[:, 0].max() - band_verts[:, 0].min())
        else:
            shoulder_width = 0.0

    # ── Inseam ────────────────────────────────────────────────────────────────
    # Inseam = crotch Y − floor Y.
    # Crotch approximation: lowest Y among vertices with |X| < 0.05 m
    # (centre-line vertices between the legs).
    if joints is not None and joints.shape == (24, 3):
        # Floor = mean of ankle Y positions
        floor_y   = float((joints[_IDX_L_ANKLE, 1] + joints[_IDX_R_ANKLE, 1]) / 2.0)
        # Crotch ≈ pelvis Y minus a small offset
        pelvis_y  = float(joints[_IDX_PELVIS, 1])
        crotch_y  = pelvis_y - 0.02  # ~2 cm below pelvis centre
        inseam    = max(0.0, crotch_y - floor_y)
    else:
        # Fallback: use vertex-based approach
        centre_mask = np.abs(vertices[:, 0]) < 0.05
        if centre_mask.any():
            crotch_y = float(vertices[centre_mask, 1].min() + 0.05 * h)
        else:
            crotch_y = y_min + 0.45 * h
        inseam = max(0.0, crotch_y - y_min)

    return {
        "height":               round(height, 4),
        "chest_circumference":  round(chest_circ, 4),
        "waist_circumference":  round(waist_circ, 4),
        "hip_circumference":    round(hip_circ, 4),
        "shoulder_width":       round(shoulder_width, 4),
        "inseam":               round(inseam, 4),
    }
