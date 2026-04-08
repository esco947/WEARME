"""Pinhole camera model for projecting SMPL mesh into image space."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# MediaPipe landmark indices used for height estimation
_IDX_NOSE    = 0
_IDX_L_ANKLE = 27
_IDX_R_ANKLE = 28

# Head height as fraction of total body height (nose ~ 13.5% below skull top)
_HEAD_FRACTION = 0.135
_MIN_HEIGHT_PX = 50.0


@dataclass(frozen=True)
class CameraParams:
    """Pinhole camera intrinsics estimated from known standing height.

    Attributes:
        focal_length_px: Focal length in pixels (fx == fy assumed).
        cx:              Principal point X (image centre).
        cy:              Principal point Y (image centre).
        pixels_per_metre: Convenience scale factor.
        person_height_px: Detected person height in pixels.
        known_height_m:  User-supplied height in metres.
    """
    focal_length_px:  float
    cx:               float
    cy:               float
    pixels_per_metre: float
    person_height_px: float
    known_height_m:   float


def estimate_camera(
    landmarks: np.ndarray,
    image_shape: tuple[int, ...],
    known_height_m: float,
) -> CameraParams:
    """Estimate camera intrinsics from MediaPipe landmarks and known height.

    Uses a two-iteration approach to correct for the fact that MediaPipe's
    topmost landmark (nose) is ~13.5% below the skull top.

    Args:
        landmarks:      (33, 3) normalised landmark coordinates (x,y in [0,1]).
        image_shape:    (H, W, ...) shape of the source image.
        known_height_m: Person's actual standing height in metres.

    Returns:
        CameraParams with focal_length_px, cx, cy, pixels_per_metre.
    """
    img_h, img_w = image_shape[:2]

    # Convert normalised coords to pixels
    nose_y   = float(landmarks[_IDX_NOSE, 1])   * img_h
    ankle_y  = float(
        (landmarks[_IDX_L_ANKLE, 1] + landmarks[_IDX_R_ANKLE, 1]) / 2.0
    ) * img_h

    if ankle_y > nose_y:
        rough_h_px        = ankle_y - nose_y
        skull_top_y       = max(0.0, nose_y - _HEAD_FRACTION * rough_h_px)
        person_height_px  = ankle_y - skull_top_y
    else:
        # Fallback: assume person occupies 85% of image height
        person_height_px = img_h * 0.85

    if person_height_px < _MIN_HEIGHT_PX:
        raise ValueError(
            f"Detected person height {person_height_px:.1f} px too small. "
            "Ensure the full body is visible."
        )

    pixels_per_metre = person_height_px / known_height_m
    # Focal length: model person depth ~ 2.5× height for typical portrait shot
    focal_length_px  = pixels_per_metre * 2.5

    return CameraParams(
        focal_length_px  = focal_length_px,
        cx               = img_w / 2.0,
        cy               = img_h / 2.0,
        pixels_per_metre = pixels_per_metre,
        person_height_px = person_height_px,
        known_height_m   = known_height_m,
    )


def project_points(
    points_3d: np.ndarray,
    camera: CameraParams,
    R: np.ndarray,
    t: np.ndarray,
) -> np.ndarray:
    """Project 3-D points into image space using a pinhole camera model.

    Args:
        points_3d: (N, 3) array of 3-D points in world space.
        camera:    CameraParams with focal_length_px, cx, cy.
        R:         (3, 3) rotation matrix (world → camera).
        t:         (3,) translation vector (world → camera).

    Returns:
        (N, 2) array of pixel coordinates [x, y].
    """
    # Transform to camera space: p_cam = R @ p_world + t
    p_cam = (R @ points_3d.T).T + t  # (N, 3)

    # Perspective divide and apply intrinsics
    z    = p_cam[:, 2:3]
    z    = np.where(np.abs(z) < 1e-6, 1e-6, z)  # avoid division by zero
    x_px = (p_cam[:, 0:1] / z) * camera.focal_length_px + camera.cx
    y_px = (p_cam[:, 1:2] / z) * camera.focal_length_px + camera.cy

    return np.hstack([x_px, y_px]).astype(np.float32)  # (N, 2)
