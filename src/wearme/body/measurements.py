"""Body measurement calculations — Phase 2.

Provides two computation paths:

1. **Param-based** (``measurements_from_params``): reads directly from
   ``BodyParameters._params``.  Fast — no SMPL model required.  Used as
   the primary path when the 55-param system is populated.

2. **Mesh-based** (``measurements_from_mesh``): uses trimesh cross-sections
   of the SMPL mesh for accurate chest / waist / hips circumferences, then
   fills remaining fields from ``_params``.

``compute_measurements`` is the backward-compatible wrapper that returns the
legacy 4-key dict (``height_m``, ``chest_m``, ``waist_m``, ``hips_m``).

All measurements are in **metres** unless otherwise noted.

Usage::

    from wearme.body.measurements import measurements_from_params, compute_measurements
    from wearme.body.body_params import BodyParameters

    params = BodyParameters(gender="female", height_m=1.65, weight_kg=58.0)
    m = measurements_from_params(params)
    print(m.chest_m, m.eu_size_top)

    legacy = compute_measurements(params)   # {'height_m': …, 'chest_m': …, …}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from wearme.body.body_params import BodyParameters

if TYPE_CHECKING:
    from wearme.body.smpl_bridge import SMPLModelData

logger = logging.getLogger(__name__)

# ── Ease allowances (EN 13402 garment ease) ──────────────────────────────────
_CHEST_EASE_M:  float = 0.08   # +8 cm
_WAIST_EASE_M:  float = 0.04   # +4 cm
_HIP_EASE_M:    float = 0.06   # +6 cm

# ── EU top sizing table (by chest circumference in cm) ────────────────────────
_EU_TOP_SIZES: list[tuple[float, str]] = [
    (76,        "XXS"),
    (80,        "XS"),
    (84,        "S"),
    (88,        "M"),
    (92,        "L"),
    (96,        "XL"),
    (100,       "XXL"),
    (float("inf"), "XXXL"),
]

# ── EU bottom sizing table (by waist circumference in cm) ────────────────────
_EU_BOTTOM_SIZES: list[tuple[float, str]] = [
    (68,        "34"),
    (72,        "36"),
    (76,        "38"),
    (80,        "40"),
    (84,        "42"),
    (88,        "44"),
    (92,        "46"),
    (float("inf"), "48"),
]

# ── US top sizing table (by chest circumference in cm) ───────────────────────
_US_TOP_SIZES: list[tuple[float, str]] = [
    (79,        "XS"),
    (86,        "S"),
    (94,        "M"),
    (102,       "L"),
    (110,       "XL"),
    (float("inf"), "XXL"),
]

_PLANE_NORMAL = np.array([0.0, 1.0, 0.0])
_SLICE_TOLERANCE_M: float = 0.010
_MIN_CROSS_SECTION_POINTS: int = 3


# ── GarmentMeasurements dataclass ─────────────────────────────────────────────

@dataclass(frozen=True)
class GarmentMeasurements:
    """Complete set of garment-ready body measurements.

    All length/circumference values are in **metres**.  Sizing strings follow
    ISO 8559 / EN 13402 conventions.
    """
    # ── Height / global ──────────────────────────────────────────────────────
    height_m:             float
    # ── Trunk circumferences ─────────────────────────────────────────────────
    chest_m:              float
    underbust_m:          float
    waist_m:              float
    abdomen_m:            float
    hip_m:                float
    neck_m:               float
    # ── Trunk widths ─────────────────────────────────────────────────────────
    shoulder_width_m:     float
    # ── Upper limbs ──────────────────────────────────────────────────────────
    arm_length_m:         float
    upper_arm_m:          float
    forearm_m:            float
    wrist_m:              float
    # ── Lower limbs ──────────────────────────────────────────────────────────
    inseam_m:             float
    outseam_m:            float
    thigh_m:              float
    calf_m:               float
    ankle_m:              float
    # ── Garment surface ──────────────────────────────────────────────────────
    front_length_m:       float
    back_length_m:        float
    dart_width_m:         float
    # ── Ease-added circumferences ─────────────────────────────────────────────
    chest_with_ease_m:    float
    waist_with_ease_m:    float
    hip_with_ease_m:      float
    # ── Sizing ───────────────────────────────────────────────────────────────
    eu_size_top:          str
    eu_size_bottom:       str
    us_size_top:          str


# ── Sizing lookup helpers ────────────────────────────────────────────────────

def _lookup_size(circ_m: float, table: list[tuple[float, str]]) -> str:
    circ_cm = circ_m * 100.0
    for threshold, label in table:
        if circ_cm <= threshold:
            return label
    return table[-1][1]


# ── Param-based path (fast, no SMPL) ─────────────────────────────────────────

def measurements_from_params(params: BodyParameters) -> GarmentMeasurements:
    """Extract garment measurements directly from ``params._params``.

    Fast path — does not require the SMPL model.  Use this whenever the
    55-param system has been populated (i.e. ``body_data`` is present in DB).

    Args:
        params: Body parameters with ``_params`` populated.

    Returns:
        :class:`GarmentMeasurements` instance.
    """
    p = params._params

    def g(key: str, default: float) -> float:
        return float(p.get(key, default))

    height_m         = g("height_m",         1.695)
    chest_m          = g("chest_circ_m",      0.945)
    underbust_m      = g("underbust_circ_m",  0.858)
    waist_m          = g("waist_circ_m",      0.785)
    abdomen_m        = g("abdomen_circ_m",    0.855)
    hip_m            = g("hip_circ_m",        0.980)
    neck_m           = g("neck_circ_m",       0.358)
    shoulder_width_m = g("shoulder_width_m",  0.393)
    arm_length_m     = g("arm_length_m",      0.595)
    upper_arm_m      = g("upper_arm_circ_m",  0.320)
    forearm_m        = g("forearm_circ_m",    0.270)
    wrist_m          = g("wrist_circ_m",      0.162)
    inseam_m         = g("inseam_m",          0.778)
    outseam_m        = g("outseam_m",         1.013)
    thigh_m          = g("thigh_circ_m",      0.573)
    calf_m           = g("calf_circ_m",       0.373)
    ankle_m          = g("ankle_circ_m",      0.228)
    front_length_m   = g("front_length_m",    0.408)
    back_length_m    = g("back_length_m",     0.433)
    dart_width_m     = g("dart_width_m",      0.025)

    return GarmentMeasurements(
        height_m=round(height_m, 4),
        chest_m=round(chest_m, 4),
        underbust_m=round(underbust_m, 4),
        waist_m=round(waist_m, 4),
        abdomen_m=round(abdomen_m, 4),
        hip_m=round(hip_m, 4),
        neck_m=round(neck_m, 4),
        shoulder_width_m=round(shoulder_width_m, 4),
        arm_length_m=round(arm_length_m, 4),
        upper_arm_m=round(upper_arm_m, 4),
        forearm_m=round(forearm_m, 4),
        wrist_m=round(wrist_m, 4),
        inseam_m=round(inseam_m, 4),
        outseam_m=round(outseam_m, 4),
        thigh_m=round(thigh_m, 4),
        calf_m=round(calf_m, 4),
        ankle_m=round(ankle_m, 4),
        front_length_m=round(front_length_m, 4),
        back_length_m=round(back_length_m, 4),
        dart_width_m=round(dart_width_m, 4),
        chest_with_ease_m=round(chest_m + _CHEST_EASE_M, 4),
        waist_with_ease_m=round(waist_m + _WAIST_EASE_M, 4),
        hip_with_ease_m=round(hip_m + _HIP_EASE_M, 4),
        eu_size_top=_lookup_size(chest_m, _EU_TOP_SIZES),
        eu_size_bottom=_lookup_size(waist_m, _EU_BOTTOM_SIZES),
        us_size_top=_lookup_size(chest_m, _US_TOP_SIZES),
    )


# ── Mesh-based path (accurate, requires SMPL) ─────────────────────────────────

def _circumference_at_height(
    vertices: np.ndarray,
    y: float,
    tolerance: float = _SLICE_TOLERANCE_M,
) -> float:
    from scipy.spatial import ConvexHull  # noqa: PLC0415

    mask = np.abs(vertices[:, 1] - y) < tolerance
    pts  = np.unique(vertices[mask][:, [0, 2]], axis=0)
    if len(pts) < _MIN_CROSS_SECTION_POINTS:
        return 0.0
    try:
        hull = ConvexHull(pts)
    except Exception:  # noqa: BLE001
        return 0.0
    verts  = pts[hull.vertices]
    closed = np.vstack([verts, verts[0]])
    return float(np.sum(np.linalg.norm(np.diff(closed, axis=0), axis=1)))


def _section_length(mesh, y: float) -> float:
    import trimesh  # noqa: PLC0415

    plane_origin = np.array([0.0, y, 0.0])
    section = mesh.section(plane_normal=_PLANE_NORMAL, plane_origin=plane_origin)
    if section is None:
        return 0.0
    path_2d, _ = section.to_2D()
    if len(path_2d.entities) == 1:
        return float(path_2d.length)
    best_length = 0.0
    best_dist   = float("inf")
    for entity in path_2d.entities:
        pts      = path_2d.vertices[entity.points]
        centroid = pts.mean(axis=0)
        dist     = float(np.linalg.norm(centroid))
        closed   = np.vstack([pts, pts[0]])
        length   = float(np.sum(np.linalg.norm(np.diff(closed, axis=0), axis=1)))
        if dist < best_dist:
            best_dist   = dist
            best_length = length
    return best_length


def _scan_for_extremum(
    mesh,
    y_min: float,
    y_max: float,
    find_max: bool,
    n_steps: int = 30,
) -> tuple[float, float]:
    heights = np.linspace(y_min, y_max, n_steps)
    results = [(h, _section_length(mesh, h)) for h in heights]
    valid   = [(h, c) for h, c in results if c > 0.0]
    if not valid:
        return (y_min + y_max) / 2.0, 0.0
    if find_max:
        return max(valid, key=lambda x: x[1])
    return min(valid, key=lambda x: x[1])


def measurements_from_mesh(
    params: BodyParameters,
    model_data: SMPLModelData | None = None,
) -> GarmentMeasurements:
    """Compute measurements using trimesh cross-sections of the SMPL mesh.

    Chest, waist, and hip circumferences are measured accurately from the
    mesh.  All other fields are filled from ``params._params``.

    Args:
        params:     Body parameters.
        model_data: Pre-loaded SMPL model data.  Loaded automatically if
                    ``None``.

    Returns:
        :class:`GarmentMeasurements` with mesh-accurate circumferences.
    """
    import trimesh  # noqa: PLC0415

    from wearme.body.smpl_bridge import generate_vertices, load_model_data  # noqa: PLC0415

    if model_data is None:
        model_data = load_model_data(params.gender)

    vertices = generate_vertices(params, model_data)
    mesh     = trimesh.Trimesh(vertices=vertices, faces=model_data.faces, process=False)

    y_min   = float(vertices[:, 1].min())
    y_max   = float(vertices[:, 1].max())
    height  = y_max - y_min

    # Empirical SMPL height fractions (neutral T-pose, Y range ≈ -1.16 to +0.56)
    chest_band = (y_min + 0.68 * height, y_min + 0.76 * height)
    hip_band   = (y_min + 0.44 * height, y_min + 0.58 * height)
    waist_band = (y_min + 0.57 * height, y_min + 0.69 * height)

    _, chest_m = _scan_for_extremum(mesh, *chest_band, find_max=True)
    _, hips_m  = _scan_for_extremum(mesh, *hip_band,   find_max=True)
    _, waist_m = _scan_for_extremum(mesh, *waist_band, find_max=False)

    # Build from params, then override the three mesh-accurate values
    base = measurements_from_params(params)
    return GarmentMeasurements(
        height_m=round(height, 4),
        chest_m=round(chest_m, 4),
        underbust_m=base.underbust_m,
        waist_m=round(waist_m, 4),
        abdomen_m=base.abdomen_m,
        hip_m=round(hips_m, 4),
        neck_m=base.neck_m,
        shoulder_width_m=base.shoulder_width_m,
        arm_length_m=base.arm_length_m,
        upper_arm_m=base.upper_arm_m,
        forearm_m=base.forearm_m,
        wrist_m=base.wrist_m,
        inseam_m=base.inseam_m,
        outseam_m=base.outseam_m,
        thigh_m=base.thigh_m,
        calf_m=base.calf_m,
        ankle_m=base.ankle_m,
        front_length_m=base.front_length_m,
        back_length_m=base.back_length_m,
        dart_width_m=base.dart_width_m,
        chest_with_ease_m=round(chest_m + _CHEST_EASE_M, 4),
        waist_with_ease_m=round(waist_m + _WAIST_EASE_M, 4),
        hip_with_ease_m=round(hips_m + _HIP_EASE_M, 4),
        eu_size_top=_lookup_size(chest_m, _EU_TOP_SIZES),
        eu_size_bottom=_lookup_size(waist_m, _EU_BOTTOM_SIZES),
        us_size_top=_lookup_size(chest_m, _US_TOP_SIZES),
    )


# ── Backward-compatible wrapper ───────────────────────────────────────────────

def compute_measurements(
    params: BodyParameters,
    model_data: SMPLModelData | None = None,
) -> dict[str, float]:
    """Compute standard body measurements.

    Backward-compatible API: returns the same 4-key dict as Phase 1::

        {"height_m": …, "chest_m": …, "waist_m": …, "hips_m": …,
         "chest_y": …, "waist_y": …, "hips_y": …}

    When *model_data* is provided, uses the mesh-based path for accurate
    chest / waist / hip values.  Otherwise falls back to the fast param path.

    Args:
        params:     Body parameters.
        model_data: Optional pre-loaded SMPL model data.

    Returns:
        Legacy 4-key measurement dict (all values in metres).
    """
    if model_data is not None:
        m = measurements_from_mesh(params, model_data)
    else:
        # Fast path — use params directly (no SMPL model needed)
        m = measurements_from_params(params)

    return {
        "height_m": m.height_m,
        "chest_m":  m.chest_m,
        "waist_m":  m.waist_m,
        "hips_m":   m.hip_m,
        # Legacy Y-height keys — not available in param path, return 0.0
        "chest_y":  0.0,
        "waist_y":  0.0,
        "hips_y":   0.0,
    }
