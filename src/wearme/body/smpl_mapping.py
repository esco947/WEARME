"""Bidirectional mapping between anatomical params and SMPL betas.

Provides two directions:

* **Forward** (``anatomical_to_betas``): Convert the 55-param anatomical
  system to 10 SMPL beta coefficients for mesh generation.  Uses a weighted
  sum of z-scored params per beta axis, calibrated from the empirical beta
  semantics of the SMPL neutral model.

* **Inverse** (``betas_to_anatomical``): Estimate anatomical params from
  SMPL betas (e.g. when reading a legacy avatar).  Uses the pseudo-inverse
  of the weight matrix, then pins height/weight and re-runs proportional
  scaling.

Call ``update_smpl_betas(params)`` after any anatomical change to keep
``params.betas`` in sync before passing ``params`` to ``smpl_bridge``.

Usage::

    from wearme.body.smpl_mapping import anatomical_to_betas, update_smpl_betas
    from wearme.body.body_params import BodyParameters

    params = BodyParameters(gender="female", height_m=1.65)
    update_smpl_betas(params)          # writes params.betas in-place
    # now params.betas is ready for smpl_bridge.generate_vertices(params, …)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from wearme.body.proportions import (
    PARAM_REGISTRY,
    allometric_scale,
    get_defaults,
    weight_redistribute,
)

if TYPE_CHECKING:
    from wearme.body.body_params import BodyParameters


_BETA_CLAMP: float = 3.5
_N_BETAS:    int   = 10

# ── Empirical weight matrix ────────────────────────────────────────────────────
# _BETA_WEIGHTS[i] maps param names → weights that contribute to beta[i].
# Z-scored params (value − neutral_default) / ((max − min) / 6) are multiplied
# by these weights and summed to produce each beta.
#
# Signs follow the known SMPL neutral-model semantics (CLAUDE.md):
#   b[1]  corpulence (INVERTED):   + = mince, − = gros
#   b[2]  limb lengths:            + = longer
#   b[3]  shoulder + chest:        + = wider
#   b[4]  hips (INVERTED):         − = wider
#   b[5]  global volume (INVERTED):− = fuller
#   b[6]  belly protrusion:        + = rounder
#   b[7]  leg thickness (INVERTED):− = thicker
#   b[8]  arm length (secondary):  + = longer
#   b[9]  hips (secondary):        + = wider

_BETA_WEIGHTS: dict[int, dict[str, float]] = {
    0: {},   # beta[0] not used here — height handled via mesh rescaling in avatar_service
    1: {     # corpulence (INVERTED: negative beta = heavier)
        "bmi":              -0.35,
        "chest_circ_m":     -0.25,
        "waist_circ_m":     -0.15,
        "hip_circ_m":       -0.10,
        "upper_arm_circ_m": -0.08,
        "thigh_circ_m":     -0.07,
    },
    2: {     # limb lengths
        "arm_length_m":      0.45,
        "inseam_m":          0.40,
        "forearm_length_m":  0.10,
        "upper_arm_length_m": 0.05,
    },
    3: {     # shoulder breadth + chest width
        "shoulder_width_m":  0.40,
        "chest_circ_m":      0.25,
        "chest_width_m":     0.20,
        "upper_arm_circ_m":  0.10,
        "back_width_m":      0.05,
    },
    4: {     # pelvis / hips (INVERTED: negative beta = wider hips)
        "hip_circ_m":       -0.45,
        "hip_width_m":      -0.35,
        "thigh_circ_m":     -0.15,
        "mid_hip_circ_m":   -0.05,
    },
    5: {     # global body volume (INVERTED: negative beta = fuller)
        "chest_circ_m":     -0.35,
        "chest_depth_m":    -0.30,
        "shoulder_width_m": -0.20,
        "back_width_m":     -0.15,
    },
    6: {     # belly protrusion
        "abdomen_circ_m":    0.50,
        "waist_depth_m":     0.30,
        "waist_circ_m":      0.15,
        "rise_front_m":      0.05,
    },
    7: {     # leg/glute thickness (INVERTED)
        "thigh_circ_m":      -0.40,
        "calf_circ_m":       -0.25,
        "mid_thigh_circ_m":  -0.20,
        "hip_depth_m":       -0.10,
        "knee_circ_m":       -0.05,
    },
    8: {     # arm length (secondary component)
        "arm_length_m":       0.60,
        "upper_arm_length_m": 0.40,
    },
    9: {     # hip width (subtle secondary component)
        "hip_circ_m":         0.50,
        "hip_width_m":        0.30,
        "mid_hip_circ_m":     0.20,
    },
}


def _z_score(name: str, value: float) -> float:
    """Compute z-score of *value* for param *name*.

    Uses (max − min) / 6 as the standard-deviation approximation
    (the "six-sigma" rule assuming the range spans ±3σ).
    """
    bounds = PARAM_REGISTRY[name]
    std    = (bounds.max_val - bounds.min_val) / 6.0
    if std <= 0.0:
        return 0.0
    return (value - bounds.default_neutral) / std


def anatomical_to_betas(params: BodyParameters) -> np.ndarray:
    """Convert anatomical params to 10 SMPL beta coefficients.

    Args:
        params: Body parameters with ``_params`` populated.

    Returns:
        Numpy array of shape ``(10,)`` with betas clamped to ±3.5.
    """
    p      = params._params
    betas  = np.zeros(_N_BETAS, dtype=np.float64)

    for beta_idx, weights in _BETA_WEIGHTS.items():
        total = 0.0
        for pname, w in weights.items():
            if pname in p and pname in PARAM_REGISTRY:
                total += w * _z_score(pname, p[pname])
        betas[beta_idx] = total

    return np.clip(betas, -_BETA_CLAMP, _BETA_CLAMP)


def betas_to_anatomical(
    betas: np.ndarray,
    height_m: float,
    weight_kg: float,
    gender: str = "neutral",
) -> dict[str, float]:
    """Estimate anatomical params from SMPL betas (inverse mapping).

    The inversion is approximate because the 10-dimensional beta space
    cannot uniquely specify all 55 anatomical params.  The strategy is:

    1. Compute the pseudo-inverse of the weight matrix.
    2. Apply it to *betas* to get z-score offsets.
    3. Convert z-scores back to param values.
    4. Override ``height_m`` / ``weight_kg`` from the supplied arguments.
    5. Re-run ``allometric_scale`` and ``weight_redistribute`` so all
       height/weight-dependent params are consistent.

    Args:
        betas:     SMPL shape coefficients, shape ``(10,)``.
        height_m:  Known height (m) — used to pin and propagate.
        weight_kg: Known weight (kg) — used to pin and propagate.
        gender:    ``"neutral"`` | ``"male"`` | ``"female"``.

    Returns:
        Dict of anatomical param values (all 55+ keys from PARAM_REGISTRY).
    """
    # Build weight matrix W  (shape: n_betas × n_params)
    # Collect ordered list of param names that appear in the weight table
    param_names: list[str] = sorted(
        {pname for weights in _BETA_WEIGHTS.values() for pname in weights}
    )
    n_params = len(param_names)
    W = np.zeros((_N_BETAS, n_params), dtype=np.float64)
    for beta_idx, weights in _BETA_WEIGHTS.items():
        for j, pname in enumerate(param_names):
            W[beta_idx, j] = weights.get(pname, 0.0)

    # Pseudo-inverse: W_pinv has shape (n_params × n_betas)
    W_pinv = np.linalg.pinv(W)

    # z_scores shape: (n_params,)
    z_scores = W_pinv @ np.clip(betas[:_N_BETAS], -_BETA_CLAMP, _BETA_CLAMP)

    # Start from population defaults, then offset by z_scores
    result = get_defaults(gender)
    for j, pname in enumerate(param_names):
        bounds = PARAM_REGISTRY.get(pname)
        if bounds is None or bounds.read_only:
            continue
        std       = (bounds.max_val - bounds.min_val) / 6.0
        estimated = bounds.default_neutral + z_scores[j] * std
        result[pname] = float(np.clip(estimated, bounds.min_val, bounds.max_val))

    # Pin height and weight, then propagate
    result["height_m"]  = height_m
    result["weight_kg"] = weight_kg
    locked: set[str] = set()  # no locks — full propagation
    allometric_scale(result, height_m, locked)
    weight_redistribute(result, weight_kg, gender, locked)

    return result


def update_smpl_betas(params: BodyParameters) -> BodyParameters:
    """Compute SMPL betas from anatomical params and write into ``params.betas``.

    Must be called before passing *params* to ``smpl_bridge.generate_vertices``
    if anatomical params were changed via ``set_param``.

    Args:
        params: Body parameters to update in-place.

    Returns:
        The same *params* object (mutated).
    """
    params.betas = anatomical_to_betas(params)
    return params
