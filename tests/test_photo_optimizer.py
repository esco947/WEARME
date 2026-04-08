"""Tests for core/photo_optimizer.py.

These tests use mocks to avoid requiring real images, MediaPipe, or SMPL PKL files.
They verify the interface contract and basic numerical properties.
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_model(num_betas: int = 10) -> MagicMock:
    """Return a mock SMPLModel with realistic outputs."""
    model = MagicMock()
    model.num_betas = num_betas
    model.faces = np.zeros((13776, 3), dtype=np.int32)

    def fake_forward(betas, **_kwargs):
        # Simple shape: betas[0] controls Y-scale (height proxy)
        verts = np.random.default_rng(42).uniform(-1, 1, (6890, 3)).astype(np.float64)
        verts[:, 1] *= 0.9 + 0.05 * float(betas[0])  # beta[0] slightly affects height
        return verts

    def fake_joints(betas, **_kwargs):
        return np.random.default_rng(0).uniform(-1, 1, (24, 3)).astype(np.float64)

    model.forward.side_effect = fake_forward
    model.get_joints.side_effect = fake_joints
    return model


def _make_fake_image(h: int = 480, w: int = 320) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_interface_returns_correct_shape():
    """optimize_betas_from_photos returns (num_betas,) array."""
    from core.photo_optimizer import optimize_betas_from_photos

    model = _make_fake_model(10)

    fake_lmk = np.zeros((33, 3), dtype=np.float32)
    # Give landmarks plausible Y values (normalised [0,1])
    fake_lmk[0, 1]  = 0.05   # nose near top
    fake_lmk[27, 1] = 0.90   # left ankle near bottom
    fake_lmk[28, 1] = 0.90   # right ankle

    fake_silhouette = np.array([[100, 50], [200, 50], [200, 400], [100, 400]], dtype=np.float32)

    with (
        patch("core.photo_optimizer.extract_landmarks",   return_value=(fake_lmk, 0.9)),
        patch("core.photo_optimizer.extract_silhouette",  return_value=fake_silhouette),
        patch("core.photo_optimizer.estimate_camera",     return_value=MagicMock(
            focal_length_px=700.0, cx=160.0, cy=240.0,
            pixels_per_metre=400.0, person_height_px=340.0, known_height_m=1.75,
        )),
        patch("core.photo_optimizer.project_points",      return_value=np.zeros((6890, 2), dtype=np.float32)),
        patch("core.photo_optimizer.compute_silhouette_iou",             return_value=0.7),
        patch("core.photo_optimizer.compute_landmark_reprojection_error", return_value=0.01),
    ):
        result = optimize_betas_from_photos(
            model        = model,
            front_image  = _make_fake_image(),
            side_image   = _make_fake_image(),
            known_height_m = 1.75,
            current_betas  = np.zeros(10),
            max_iter       = 5,
        )

    assert result.shape == (10,), f"Expected shape (10,), got {result.shape}"


def test_betas_in_bounds():
    """Output betas must always be in [-5, +5]."""
    from core.photo_optimizer import optimize_betas_from_photos

    model = _make_fake_model(10)

    fake_lmk = np.zeros((33, 3), dtype=np.float32)
    fake_lmk[0, 1]  = 0.05
    fake_lmk[27, 1] = 0.90
    fake_lmk[28, 1] = 0.90

    fake_sil = np.array([[10, 10], [200, 10], [200, 400], [10, 400]], dtype=np.float32)

    with (
        patch("core.photo_optimizer.extract_landmarks",   return_value=(fake_lmk, 0.9)),
        patch("core.photo_optimizer.extract_silhouette",  return_value=fake_sil),
        patch("core.photo_optimizer.estimate_camera",     return_value=MagicMock(
            focal_length_px=700.0, cx=160.0, cy=240.0,
            pixels_per_metre=400.0, person_height_px=340.0, known_height_m=1.75,
        )),
        patch("core.photo_optimizer.project_points",      return_value=np.zeros((6890, 2), dtype=np.float32)),
        patch("core.photo_optimizer.compute_silhouette_iou",             return_value=0.5),
        patch("core.photo_optimizer.compute_landmark_reprojection_error", return_value=0.05),
    ):
        # Start with extreme values to stress-test clamping
        result = optimize_betas_from_photos(
            model          = model,
            front_image    = _make_fake_image(),
            side_image     = _make_fake_image(),
            known_height_m = 1.75,
            current_betas  = np.array([10.0] * 10),
            max_iter       = 3,
        )

    assert np.all(result >= -5.0), f"Betas below -5: {result}"
    assert np.all(result <= +5.0), f"Betas above +5: {result}"


def test_front_image_failure_raises():
    """ValueError in front processing propagates cleanly."""
    from core.photo_optimizer import optimize_betas_from_photos

    model = _make_fake_model()

    with patch("core.photo_optimizer.extract_landmarks", side_effect=ValueError("no person")):
        with pytest.raises(ValueError, match="Front image"):
            optimize_betas_from_photos(
                model          = model,
                front_image    = _make_fake_image(),
                side_image     = _make_fake_image(),
                known_height_m = 1.75,
                current_betas  = np.zeros(10),
            )


def test_side_image_failure_raises():
    """ValueError in side processing propagates cleanly."""
    from core.photo_optimizer import optimize_betas_from_photos

    model = _make_fake_model()

    fake_lmk = np.zeros((33, 3), dtype=np.float32)
    fake_lmk[0, 1] = 0.05
    fake_lmk[27, 1] = 0.90
    fake_lmk[28, 1] = 0.90

    fake_sil = np.array([[10, 10], [200, 400]], dtype=np.float32)

    call_count = {"n": 0}

    def side_effect_landmarks(img, **kwargs):
        call_count["n"] += 1
        if call_count["n"] > 1:
            raise ValueError("no person in side view")
        return fake_lmk, 0.9

    def side_effect_silhouette(img, **kwargs):
        if call_count["n"] > 1:
            raise ValueError("no contour in side view")
        return fake_sil

    with (
        patch("core.photo_optimizer.extract_landmarks",  side_effect=side_effect_landmarks),
        patch("core.photo_optimizer.extract_silhouette", side_effect=side_effect_silhouette),
        patch("core.photo_optimizer.estimate_camera",    return_value=MagicMock(
            focal_length_px=700.0, cx=160.0, cy=240.0,
            pixels_per_metre=400.0, person_height_px=340.0, known_height_m=1.75,
        )),
    ):
        with pytest.raises(ValueError, match="Side image"):
            optimize_betas_from_photos(
                model          = model,
                front_image    = _make_fake_image(),
                side_image     = _make_fake_image(),
                known_height_m = 1.75,
                current_betas  = np.zeros(10),
            )
