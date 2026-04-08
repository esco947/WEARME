"""MediaPipe Pose landmark extraction for the SMPL-first vision pipeline."""

from __future__ import annotations

import numpy as np


def extract_landmarks(
    image_bgr: np.ndarray,
    min_confidence: float = 0.5,
) -> tuple[np.ndarray, float]:
    """Detect MediaPipe Pose landmarks in a BGR image.

    Args:
        image_bgr:       Input image, shape (H, W, 3), BGR.
        min_confidence:  Minimum detection confidence threshold.

    Returns:
        landmarks: (33, 3) array — [x_norm, y_norm, z_norm] where x,y in [0,1].
        confidence: Mean visibility score across all landmarks.

    Raises:
        ValueError: If no person detected or mean confidence < min_confidence.
    """
    try:
        import mediapipe as mp  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("MediaPipe is required. Install: pip install mediapipe>=0.10") from exc

    _MP_POSE = mp.solutions.pose

    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError(f"image_bgr must have shape (H, W, 3), got {image_bgr.shape}.")

    image_rgb = image_bgr[:, :, ::-1].copy()

    with _MP_POSE.Pose(
        model_complexity=2,
        enable_segmentation=True,
        static_image_mode=True,
        min_detection_confidence=min_confidence,
        min_tracking_confidence=min_confidence,
    ) as pose:
        results = pose.process(image_rgb)

    if results.pose_landmarks is None:
        raise ValueError("No person detected in image.")

    landmarks = np.array(
        [[lm.x, lm.y, lm.z] for lm in results.pose_landmarks.landmark],
        dtype=np.float32,
    )  # (33, 3)

    visibility = np.array(
        [lm.visibility for lm in results.pose_landmarks.landmark],
        dtype=np.float32,
    )
    confidence = float(visibility.mean())

    if confidence < min_confidence:
        raise ValueError(
            f"Detection confidence {confidence:.2f} below threshold {min_confidence}."
        )

    return landmarks, confidence
