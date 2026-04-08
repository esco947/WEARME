"""Camera scale estimation from known body height (Phase 4).

Estimates the pixel-to-metre scale factor from the detected body landmarks
and the user-supplied standing height.  No camera intrinsics or calibration
data are required — the scale is derived purely from the ratio of the
detected person height in pixels to the known standing height in metres.

Usage::

    from wearme.vision.camera_estimation import estimate_from_landmarks

    cam = estimate_from_landmarks(
        landmarks_2d=result.landmarks_2d,
        known_height_m=1.75,
        img_h=720,
        img_w=480,
    )
    print(cam.pixels_per_metre)   # e.g. 380.5
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# ── Anatomical constants ──────────────────────────────────────────────────────

# Fraction of standing height occupied by the head (top of skull → chin).
# Derived from PARAM_REGISTRY defaults: head_height_m / height_m ≈ 0.227/1.695.
_HEAD_HEIGHT_FRACTION: float = 0.135

# MediaPipe landmark indices used for height estimation.
_IDX_NOSE:       int = 0
_IDX_L_SHOULDER: int = 11
_IDX_R_SHOULDER: int = 12
_IDX_L_ANKLE:    int = 27
_IDX_R_ANKLE:    int = 28

# Minimum plausible person height in pixels — reject detections below this.
_MIN_HEIGHT_PX: float = 50.0


# ── Result container ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CameraParams:
    """Pixel-to-metre scale factor estimated from known standing height.

    Attributes:
        pixels_per_metre: Number of pixels per metre in the image plane.
        person_height_px: Estimated full body height in pixels.
        known_height_m:   User-supplied actual standing height (m).
    """

    pixels_per_metre: float
    person_height_px: float
    known_height_m:   float


# ── Public API ────────────────────────────────────────────────────────────────

def estimate_from_landmarks(
    landmarks_2d: np.ndarray,
    known_height_m: float,
    img_h: int,
    img_w: int,
) -> CameraParams:
    """Estimate pixel scale from known height and detected MediaPipe landmarks.

    Strategy
    --------
    MediaPipe's top body landmark is the **nose** (index 0), not the top of
    the skull.  The head contributes ~13.5 % of standing height.  We estimate
    the skull top as::

        skull_top_y = nose_y - HEAD_HEIGHT_FRACTION * person_height_estimate

    To avoid circular dependency, we use two iterations:

    1. Rough height estimate from nose_y to mean ankle_y.
    2. Correct skull_top_y with the head fraction.
    3. Final height = skull_top_y to mean ankle_y.

    Args:
        landmarks_2d:   Pixel coordinates, shape ``(33, 2)``.
        known_height_m: Actual standing height in metres.
        img_h:          Image height in pixels.
        img_w:          Image width in pixels (unused, kept for API symmetry).

    Returns:
        :class:`CameraParams` with scale factor.

    Raises:
        ValueError: If key landmarks are missing or height is implausible.
    """
    if landmarks_2d.shape != (33, 2):
        raise ValueError(
            f"landmarks_2d must have shape (33, 2), got {landmarks_2d.shape}."
        )
    if known_height_m <= 0.0:
        raise ValueError(f"known_height_m must be positive, got {known_height_m}.")

    nose_y = float(landmarks_2d[_IDX_NOSE, 1])
    ankle_y = float(
        (landmarks_2d[_IDX_L_ANKLE, 1] + landmarks_2d[_IDX_R_ANKLE, 1]) / 2.0
    )

    if ankle_y <= nose_y:
        # Flip or unexpected pose — fallback: use image height as proxy
        logger.warning(
            "Ankle Y (%.1f) <= nose Y (%.1f); using image height as fallback.",
            ankle_y, nose_y,
        )
        person_height_px = float(img_h) * 0.85
    else:
        # Iteration 1: rough estimate (nose to ankles)
        rough_height_px = ankle_y - nose_y

        # Iteration 2: correct for head height above nose
        head_correction_px = _HEAD_HEIGHT_FRACTION * rough_height_px
        skull_top_y = nose_y - head_correction_px

        # Clamp skull_top to image bounds
        skull_top_y = max(0.0, skull_top_y)
        person_height_px = ankle_y - skull_top_y

    if person_height_px < _MIN_HEIGHT_PX:
        raise ValueError(
            f"Estimated person height ({person_height_px:.1f} px) is too small. "
            "Check that the full body is visible in the image."
        )

    pixels_per_metre = person_height_px / known_height_m

    logger.debug(
        "Camera scale: %.1f px/m  (person=%.1f px, known=%.3f m)",
        pixels_per_metre, person_height_px, known_height_m,
    )

    return CameraParams(
        pixels_per_metre=pixels_per_metre,
        person_height_px=person_height_px,
        known_height_m=known_height_m,
    )
