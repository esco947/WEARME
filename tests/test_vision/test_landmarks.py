"""Tests for wearme.vision.landmarks.

Uses ``pytest.importorskip`` to skip the full test suite when MediaPipe
is not installed.  Structure tests mock the MediaPipe internals so they
run without a real model download.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Skip the entire module if mediapipe is not installed.
mp = pytest.importorskip("mediapipe", reason="mediapipe not installed")

from wearme.vision.landmarks import LandmarkResult, detect_landmarks  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_fake_landmark(x: float = 0.5, y: float = 0.5, z: float = 0.0, vis: float = 0.9):
    lm = MagicMock()
    lm.x = x
    lm.y = y
    lm.z = z
    lm.visibility = vis
    return lm


def _make_fake_results(detected: bool = True, with_seg: bool = True):
    """Return a mock MediaPipe Pose results object."""
    results = MagicMock()
    if not detected:
        results.pose_landmarks = None
        results.pose_world_landmarks = None
        results.segmentation_mask = None
        return results

    # 33 landmarks all at image centre
    landmarks = [_make_fake_landmark(0.5, 0.5) for _ in range(33)]
    results.pose_landmarks.landmark = landmarks
    results.pose_world_landmarks.landmark = landmarks
    results.segmentation_mask = (
        np.full((480, 640), 0.9, dtype=np.float32) if with_seg else None
    )
    return results


def _make_bgr_image(h: int = 480, w: int = 640) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


# ── LandmarkResult dataclass ──────────────────────────────────────────────────

class TestLandmarkResultDataclass:
    def test_is_frozen(self) -> None:
        """LandmarkResult should be immutable."""
        r = LandmarkResult(
            landmarks_2d=np.zeros((33, 2), dtype=np.float32),
            landmarks_3d=np.zeros((33, 3), dtype=np.float32),
            visibility=np.ones(33, dtype=np.float32),
            segmentation_mask=None,
        )
        with pytest.raises((AttributeError, TypeError)):
            r.visibility = np.zeros(33, dtype=np.float32)  # type: ignore[misc]

    def test_field_shapes(self) -> None:
        r = LandmarkResult(
            landmarks_2d=np.zeros((33, 2), dtype=np.float32),
            landmarks_3d=np.zeros((33, 3), dtype=np.float32),
            visibility=np.ones(33, dtype=np.float32),
            segmentation_mask=np.zeros((480, 640), dtype=np.float32),
        )
        assert r.landmarks_2d.shape == (33, 2)
        assert r.landmarks_3d.shape == (33, 3)
        assert r.visibility.shape == (33,)
        assert r.segmentation_mask is not None
        assert r.segmentation_mask.shape == (480, 640)


# ── detect_landmarks function ─────────────────────────────────────────────────

class TestDetectLandmarks:
    def test_returns_none_when_no_person(self) -> None:
        """Returns None when MediaPipe detects no person."""
        image = _make_bgr_image()
        fake_results = _make_fake_results(detected=False)

        with patch("wearme.vision.landmarks._MP_POSE.Pose") as MockPose:
            ctx = MockPose.return_value.__enter__.return_value
            ctx.process.return_value = fake_results
            result = detect_landmarks(image)

        assert result is None

    def test_returns_landmark_result_when_person_detected(self) -> None:
        """Returns LandmarkResult when a person is detected."""
        image = _make_bgr_image(h=480, w=640)
        fake_results = _make_fake_results(detected=True)

        with patch("wearme.vision.landmarks._MP_POSE.Pose") as MockPose:
            ctx = MockPose.return_value.__enter__.return_value
            ctx.process.return_value = fake_results
            result = detect_landmarks(image)

        assert result is not None
        assert isinstance(result, LandmarkResult)

    def test_landmarks_2d_shape(self) -> None:
        """landmarks_2d has shape (33, 2)."""
        image = _make_bgr_image(h=480, w=640)
        fake_results = _make_fake_results(detected=True)

        with patch("wearme.vision.landmarks._MP_POSE.Pose") as MockPose:
            ctx = MockPose.return_value.__enter__.return_value
            ctx.process.return_value = fake_results
            result = detect_landmarks(image)

        assert result is not None
        assert result.landmarks_2d.shape == (33, 2)
        assert result.landmarks_3d.shape == (33, 3)
        assert result.visibility.shape == (33,)

    def test_visibility_in_range(self) -> None:
        """All visibility scores are in [0, 1]."""
        image = _make_bgr_image()
        fake_results = _make_fake_results(detected=True)

        with patch("wearme.vision.landmarks._MP_POSE.Pose") as MockPose:
            ctx = MockPose.return_value.__enter__.return_value
            ctx.process.return_value = fake_results
            result = detect_landmarks(image)

        assert result is not None
        assert np.all(result.visibility >= 0.0)
        assert np.all(result.visibility <= 1.0)

    def test_2d_coords_scaled_by_image_size(self) -> None:
        """Pixel coords should be 0.5 × image_size when all landmarks at (0.5, 0.5)."""
        h, w = 480, 640
        image = _make_bgr_image(h=h, w=w)
        fake_results = _make_fake_results(detected=True)

        with patch("wearme.vision.landmarks._MP_POSE.Pose") as MockPose:
            ctx = MockPose.return_value.__enter__.return_value
            ctx.process.return_value = fake_results
            result = detect_landmarks(image)

        assert result is not None
        assert np.allclose(result.landmarks_2d[:, 0], 0.5 * w, atol=1.0)
        assert np.allclose(result.landmarks_2d[:, 1], 0.5 * h, atol=1.0)

    def test_raises_on_non_3channel_image(self) -> None:
        """ValueError on grayscale input."""
        gray = np.zeros((480, 640), dtype=np.uint8)
        with pytest.raises(ValueError, match="shape"):
            detect_landmarks(gray)

    def test_segmentation_mask_attached(self) -> None:
        """Segmentation mask is included when MediaPipe provides it."""
        image = _make_bgr_image(h=480, w=640)
        fake_results = _make_fake_results(detected=True, with_seg=True)

        with patch("wearme.vision.landmarks._MP_POSE.Pose") as MockPose:
            ctx = MockPose.return_value.__enter__.return_value
            ctx.process.return_value = fake_results
            result = detect_landmarks(image)

        assert result is not None
        assert result.segmentation_mask is not None
