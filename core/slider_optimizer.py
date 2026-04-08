"""Beta optimizer driven by measurement targets.

Uses a pre-calibrated sensitivity matrix to solve for betas analytically
(numpy lstsq) instead of iterating with scipy.optimize.

Speed:
- First call: ~0.5 s (computes sensitivity matrix: 10 forward passes)
- Subsequent calls: ~5 ms (matrix multiply + forward + GLB export)

vs. previous scipy L-BFGS-B approach: 2-155 s per call.
"""

from __future__ import annotations

import logging

import numpy as np

from core.beta_calibrator import MEASUREMENT_KEYS, get_calibration, solve_betas

logger = logging.getLogger(__name__)

BETA_MIN = -5.0
BETA_MAX = 5.0

_VALID_KEYS = frozenset(MEASUREMENT_KEYS)


def optimize_betas_from_targets(
    model,
    targets: dict[str, float],
    _current_betas: np.ndarray,
    gender: str = "male",
    **__kwargs,  # absorb legacy lambda_reg / max_iter arguments
) -> np.ndarray:
    """Find SMPL betas matching target measurements using linear calibration.

    Args:
        model:         SMPLModel instance.
        targets:       {measurement_key: target_metres}.
        current_betas: Starting betas — not used for the linear solve, kept
                       for API compatibility.
        gender:        "male" or "female" — used to cache the sensitivity
                       matrix separately per gender.

    Returns:
        Betas (num_betas,), clamped to [-5, +5].
    """
    valid_targets = {k: v for k, v in targets.items() if k in _VALID_KEYS}
    if not valid_targets:
        raise ValueError(
            f"No valid keys in targets. Got {list(targets)}, "
            f"expected one of {sorted(_VALID_KEYS)}."
        )

    S, m_default = get_calibration(model, gender)
    betas = solve_betas(valid_targets, S, m_default, beta_max=BETA_MAX)

    logger.info(
        "Slider solve: targets=%s → |betas|=%.3f",
        {k: f"{v*100:.1f}cm" for k, v in valid_targets.items()},
        float(np.linalg.norm(betas)),
    )
    return betas
