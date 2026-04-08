"""Silhouette IoU and landmark reprojection error for the photo optimizer."""

from __future__ import annotations

import numpy as np


# SMPL joint index → MediaPipe landmark index
# Only reliable, high-visibility joints are included.
_SMPL_TO_MP: list[tuple[int, int]] = [
    (13, 11),   # L shoulder
    (14, 12),   # R shoulder
    (16, 15),   # L wrist  (SMPL) → L wrist (MP)
    (17, 16),   # R wrist
    (1,  23),   # L hip
    (2,  24),   # R hip
    (4,  25),   # L knee
    (5,  26),   # R knee
    (7,  27),   # L ankle
    (8,  28),   # R ankle
]


def compute_silhouette_iou(
    projected_vertices: np.ndarray,
    faces: np.ndarray,
    target_contour: np.ndarray,
    image_shape: tuple[int, ...],
) -> float:  # noqa: D401
    """Compute IoU between projected SMPL mesh silhouette and target contour.

    Args:
        projected_vertices: (6890, 2) pixel coordinates of SMPL vertices.
        faces:              (13776, 3) SMPL face indices.
        target_contour:     (N, 2) pixel contour [x, y] of the person.
        image_shape:        (H, W, ...) image dimensions for the rasterisation canvas.

    Returns:
        IoU value in [0, 1].  Returns 0.0 if either mask is empty.
    """
    try:
        import cv2  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("OpenCV is required. Install: pip install opencv-python-headless>=4.8") from exc

    img_h, img_w = int(image_shape[0]), int(image_shape[1])

    # Rasterise target contour
    target_mask = np.zeros((img_h, img_w), dtype=np.uint8)
    pts_target  = target_contour.astype(np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(target_mask, [pts_target], 255)

    # Rasterise projected mesh via convex hull of visible vertices
    proj_mask = np.zeros((img_h, img_w), dtype=np.uint8)
    verts_i   = projected_vertices.astype(np.int32)

    # Clip to image bounds to avoid out-of-canvas artifacts
    valid = (
        (verts_i[:, 0] >= 0) & (verts_i[:, 0] < img_w) &
        (verts_i[:, 1] >= 0) & (verts_i[:, 1] < img_h)
    )
    verts_valid = verts_i[valid]
    if len(verts_valid) < 3:
        return 0.0

    hull = cv2.convexHull(verts_valid.reshape(-1, 1, 2))
    cv2.fillPoly(proj_mask, [hull], 255)

    intersection = np.count_nonzero((target_mask > 0) & (proj_mask > 0))
    union        = np.count_nonzero((target_mask > 0) | (proj_mask > 0))

    if union == 0:
        return 0.0
    return float(intersection) / float(union)


def compute_landmark_reprojection_error(
    projected_joints: np.ndarray,
    target_landmarks: np.ndarray,
    image_shape: tuple[int, ...],
) -> float:
    """Compute MSE between projected SMPL joints and MediaPipe landmarks.

    Args:
        projected_joints:  (24, 2) pixel coordinates of SMPL joints.
        target_landmarks:  (33, 3) normalised MediaPipe landmarks [x, y, z] (x,y in [0,1]).
        image_shape:       (H, W, ...) for converting normalised → pixel coords.

    Returns:
        Mean squared error in pixels², normalised by image diagonal².
        Returns 0.0 if no joint pairs are available.
    """
    img_h, img_w = float(image_shape[0]), float(image_shape[1])
    diag2 = img_h**2 + img_w**2

    errors = []
    for smpl_idx, mp_idx in _SMPL_TO_MP:
        if smpl_idx >= len(projected_joints) or mp_idx >= len(target_landmarks):
            continue
        px_smpl = projected_joints[smpl_idx]           # (2,) pixels [x,y]
        lm      = target_landmarks[mp_idx]              # (3,) [x_norm, y_norm, z_norm]
        px_mp   = np.array([lm[0] * img_w, lm[1] * img_h], dtype=np.float32)
        dx      = float(px_smpl[0] - px_mp[0])
        dy      = float(px_smpl[1] - px_mp[1])
        errors.append(dx**2 + dy**2)

    if not errors:
        return 0.0

    return float(np.mean(errors)) / diag2
