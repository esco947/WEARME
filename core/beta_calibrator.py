"""Pre-calibrated sensitivity matrix: maps measurement deltas → SMPL betas.

Architecture
------------
The SMPL forward model is approximately linear in betas around the default
shape (betas=0).  This module pre-computes the sensitivity matrix:

    S[i, j] = dm_j / db_i

where b_i is the i-th beta and m_j is the j-th measurement (in metres).

Given target measurements, the optimal betas are found analytically:

    delta = target - m_default
    betas = argmin ||betas||  s.t.  S.T @ betas ≈ delta

This is a single numpy least-squares call (~0ms) vs. scipy L-BFGS-B
iterating for 2-3 seconds.

The sensitivity matrix is computed once at startup (10 SMPL forward passes
+ 10 measure_mesh calls, ~0.5s total) and cached in memory.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Measurement keys — must match measure_mesh() output and body_schema.SLIDERS
MEASUREMENT_KEYS = [
    "height",
    "chest_circumference",
    "waist_circumference",
    "hip_circumference",
    "shoulder_width",
    "inseam",
]

# Delta used for finite-difference sensitivity (in beta units)
_DELTA_BETA = 2.0

# Cache: gender-key → (S, m_default)
# S shape: (num_betas, num_measurements)
_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def _measure(model, betas: np.ndarray) -> np.ndarray:
    """Return measurement array (num_measurements,) for given betas."""
    from core.mesh_measurements import measure_mesh  # noqa: PLC0415

    verts  = model.forward(betas)
    joints = model.get_joints(betas)
    m      = measure_mesh(verts, model.faces, joints)
    return np.array([m[k] for k in MEASUREMENT_KEYS], dtype=np.float64)


def compute_calibration(model) -> tuple[np.ndarray, np.ndarray]:
    """Compute sensitivity matrix S and default measurements m_default.

    Makes num_betas + 1 SMPL forward passes plus measure_mesh calls.
    Typical runtime: ~0.5 s (cached after first call).

    Args:
        model: Loaded SMPLModel instance.

    Returns:
        S:         Sensitivity matrix, shape (num_betas, num_measurements).
        m_default: Default measurements at betas=0, shape (num_measurements,).
    """
    logger.info("Computing beta sensitivity matrix (num_betas=%d)…", model.num_betas)

    b0       = np.zeros(model.num_betas)
    m_default = _measure(model, b0)

    S = np.zeros((model.num_betas, len(MEASUREMENT_KEYS)), dtype=np.float64)
    for i in range(model.num_betas):
        b      = np.zeros(model.num_betas)
        b[i]   = _DELTA_BETA
        m_pert = _measure(model, b)
        S[i]   = (m_pert - m_default) / _DELTA_BETA

    logger.info("Sensitivity matrix ready. Default shape: %s",
                {k: f"{v*100:.1f}cm" for k, v in zip(MEASUREMENT_KEYS, m_default)})
    return S, m_default


def get_calibration(model, gender: str) -> tuple[np.ndarray, np.ndarray]:
    """Return cached (S, m_default), computing if needed."""
    key = f"{gender}:{model.num_betas}"
    if key not in _cache:
        _cache[key] = compute_calibration(model)
    return _cache[key]


def solve_betas(
    targets: dict[str, float],
    S: np.ndarray,
    m_default: np.ndarray,
    beta_max: float = 5.0,
) -> np.ndarray:
    """Find minimum-norm betas that produce the target measurements.

    Uses numpy least-squares (lstsq) to solve the under-determined linear
    system:  S.T @ betas = delta  (6 equations, 10 unknowns)

    The minimum-norm solution gives the shape closest to the average SMPL
    body while matching the requested measurements as precisely as possible.

    Args:
        targets:   {measurement_key: target_metres}.  Missing keys use
                   the default measurement (no change for that dimension).
        S:         Sensitivity matrix (num_betas, num_measurements).
        m_default: Default measurements (num_measurements,).
        beta_max:  Absolute beta clamp.

    Returns:
        betas (num_betas,), clamped to [-beta_max, +beta_max].
    """
    # Build target vector — use m_default for any missing key
    target_arr  = m_default.copy()
    for j, key in enumerate(MEASUREMENT_KEYS):
        if key in targets:
            target_arr[j] = targets[key]

    delta = target_arr - m_default  # (num_measurements,)

    # S.T has shape (num_measurements, num_betas)
    # We want: S.T @ betas ≈ delta
    # lstsq returns the min-norm least-squares solution
    betas, residuals, rank, sv = np.linalg.lstsq(S.T, delta, rcond=None)

    logger.debug(
        "Beta solve: rank=%d, residual=%s, |betas|=%.3f",
        rank,
        f"{float(np.sum(residuals)):.6f}" if residuals.size else "n/a",
        float(np.linalg.norm(betas)),
    )

    return np.clip(betas, -beta_max, beta_max)
