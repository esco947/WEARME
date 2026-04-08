"""Photo-based SMPL beta optimizer.

Fits SMPL betas to silhouette IoU + landmark reprojection loss from
front and side photos of a person, plus a height constraint.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize  # type: ignore[import]

from core.smpl_model import SMPLModel
from vision.landmark_extractor import extract_landmarks
from vision.silhouette_extractor import extract_silhouette
from vision.camera_model import estimate_camera, project_points, CameraParams
from vision.contour_fitter import compute_silhouette_iou, compute_landmark_reprojection_error

# Rotation matrices for front (identity) and side (90° around Y) views
_R_FRONT = np.eye(3, dtype=np.float64)
_R_SIDE  = np.array([
    [ 0., 0., 1.],
    [ 0., 1., 0.],
    [-1., 0., 0.],
], dtype=np.float64)

_BETA_MIN = -5.0
_BETA_MAX =  5.0


def _make_translation(height_m: float) -> np.ndarray:
    """Camera-space translation vector: person centred, ~2.5m away."""
    return np.array([0.0, -height_m / 2.0, 2.5], dtype=np.float64)


def optimize_betas_from_photos(
    model: SMPLModel,
    front_image: np.ndarray,
    side_image: np.ndarray,
    known_height_m: float,
    current_betas: np.ndarray,
    lambda_sil: float    = 1.0,
    lambda_lmk: float    = 0.5,
    lambda_height: float = 2.0,
    lambda_reg: float    = 0.005,
    max_iter: int        = 100,
) -> np.ndarray:
    """Fit SMPL betas to front + side photos using silhouette and landmarks.

    Args:
        model:           Loaded SMPLModel instance (male or female).
        front_image:     BGR image of person facing camera.
        side_image:      BGR image of person in side profile.
        known_height_m:  Person's actual height in metres.
        current_betas:   (10,) starting point for optimisation.
        lambda_sil:      Weight for silhouette IoU loss (per view).
        lambda_lmk:      Weight for landmark reprojection loss (per view).
        lambda_height:   Weight for height constraint.
        lambda_reg:      L2 regularisation on betas.
        max_iter:        Maximum L-BFGS-B iterations.

    Returns:
        Optimised betas (10,) clamped to [-5, +5].
    """
    # --- Extract front view features ---
    try:
        lmk_front, _ = extract_landmarks(front_image)
        sil_front     = extract_silhouette(front_image)
        cam_front     = estimate_camera(lmk_front, front_image.shape, known_height_m)
    except ValueError as e:
        raise ValueError(f"Front image processing failed: {e}") from e

    # --- Extract side view features ---
    try:
        lmk_side, _ = extract_landmarks(side_image)
        sil_side     = extract_silhouette(side_image)
        cam_side     = estimate_camera(lmk_side, side_image.shape, known_height_m)
    except ValueError as e:
        raise ValueError(f"Side image processing failed: {e}") from e

    t_front = _make_translation(known_height_m)
    t_side  = _make_translation(known_height_m)

    bounds = [(_BETA_MIN, _BETA_MAX)] * model.num_betas

    def loss(betas: np.ndarray) -> float:
        betas = np.clip(betas, _BETA_MIN, _BETA_MAX)

        verts  = model.forward(betas)           # (6890, 3)
        joints = model.get_joints(betas)        # (24, 3)

        # ── Front view ────────────────────────────────────────────────────────
        proj_v_front = project_points(verts,  cam_front, _R_FRONT, t_front)  # (6890,2)
        proj_j_front = project_points(joints, cam_front, _R_FRONT, t_front)  # (24,2)

        sil_iou_front = compute_silhouette_iou(
            proj_v_front, model.faces, sil_front, front_image.shape
        )
        lmk_err_front = compute_landmark_reprojection_error(
            proj_j_front, lmk_front, front_image.shape
        )

        # ── Side view ─────────────────────────────────────────────────────────
        proj_v_side = project_points(verts,  cam_side, _R_SIDE, t_side)
        proj_j_side = project_points(joints, cam_side, _R_SIDE, t_side)

        sil_iou_side = compute_silhouette_iou(
            proj_v_side, model.faces, sil_side, side_image.shape
        )
        lmk_err_side = compute_landmark_reprojection_error(
            proj_j_side, lmk_side, side_image.shape
        )

        # ── Height constraint ─────────────────────────────────────────────────
        height = float(verts[:, 1].max() - verts[:, 1].min())
        height_err = (height - known_height_m) ** 2

        # ── Combined loss ─────────────────────────────────────────────────────
        silhouette_loss   = (1.0 - sil_iou_front) + (1.0 - sil_iou_side)
        landmark_loss     = lmk_err_front + lmk_err_side
        regularisation    = float(np.sum(betas ** 2))

        return (
            lambda_sil    * silhouette_loss
            + lambda_lmk  * landmark_loss
            + lambda_height * height_err
            + lambda_reg  * regularisation
        )

    result = minimize(
        loss,
        x0     = np.clip(current_betas.copy(), _BETA_MIN, _BETA_MAX),
        method = "L-BFGS-B",
        bounds = bounds,
        options = {
            "maxiter": max_iter,
            "eps":     0.01,
            "ftol":    1e-8,
            "gtol":    1e-5,
        },
    )

    return np.clip(result.x, _BETA_MIN, _BETA_MAX)
