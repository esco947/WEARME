"""MediaPipe Pose landmark detection (Phase 4).

Wraps the MediaPipe Pose v2 solution to detect 33 body landmarks from a
BGR image.  Both 2-D pixel coordinates and 3-D normalised coordinates are
returned alongside the per-landmark visibility scores and the person
segmentation mask.

Requires the vision extras::

    pip install wearme[vision]

Usage::

    import cv2
    from wearme.vision.landmarks import detect_landmarks

    image = cv2.imread("front.jpg")
    result = detect_landmarks(image)
    if result is not None:
        print(result.landmarks_2d.shape)   # (33, 2)
        print(result.segmentation_mask.shape)  # (H, W)

Key landmark indices
--------------------
    0  = nose
    11 = left shoulder
    12 = right shoulder
    23 = left hip
    24 = right hip
    27 = left ankle
    28 = right ankle
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Lazy import of mediapipe — raises a clear error if not installed.
try:
    import mediapipe as mp  # type: ignore[import]
    _MP_POSE = mp.solutions.pose
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "MediaPipe is required for landmark detection. "
        "Install the vision extras: pip install wearme[vision]"
    ) from exc


# ── Result container ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LandmarkResult:
    """Output of :func:`detect_landmarks`.

    Attributes:
        landmarks_2d:       Pixel coordinates, shape ``(33, 2)`` — ``[x, y]``.
                            Origin at top-left; Y increases downward.
        landmarks_3d:       Normalised 3-D coordinates from MediaPipe, shape
                            ``(33, 3)`` — ``[x, y, z]``.  X and Y are in
                            ``[0, 1]`` (normalised by image size); Z is in the
                            same scale as X.
        visibility:         Per-landmark confidence scores, shape ``(33,)``,
                            values in ``[0, 1]``.
        segmentation_mask:  Float32 person segmentation mask, shape ``(H, W)``,
                            values in ``[0, 1]``.  ``None`` when segmentation
                            is disabled.
    """

    landmarks_2d:      np.ndarray            # (33, 2) pixels
    landmarks_3d:      np.ndarray            # (33, 3) normalised
    visibility:        np.ndarray            # (33,) float32
    segmentation_mask: np.ndarray | None     # (H, W) float32 or None


# ── Detection ─────────────────────────────────────────────────────────────────

def detect_landmarks(
    image_bgr: np.ndarray,
    min_detection_confidence: float = 0.5,
    min_tracking_confidence: float = 0.5,
) -> LandmarkResult | None:
    """Detect MediaPipe Pose landmarks in a BGR image.

    Runs the MediaPipe Pose solution in static-image mode (no temporal
    filtering).  Converts BGR → RGB internally before passing to MediaPipe.

    Args:
        image_bgr:                 Input image, shape ``(H, W, 3)``, BGR.
        min_detection_confidence:  Minimum detection score threshold.
                                   Default 0.5.
        min_tracking_confidence:   Minimum tracking score threshold.
                                   Default 0.5.

    Returns:
        :class:`LandmarkResult` if a person is detected, ``None`` otherwise.
    """
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError(
            f"image_bgr must have shape (H, W, 3), got {image_bgr.shape}."
        )

    img_h, img_w = image_bgr.shape[:2]
    image_rgb = image_bgr[:, :, ::-1].copy()  # BGR → RGB

    with _MP_POSE.Pose(
        model_complexity=2,
        enable_segmentation=True,
        static_image_mode=True,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    ) as pose:
        results = pose.process(image_rgb)

    if results.pose_landmarks is None:
        logger.debug("No person detected in image (%d×%d)", img_w, img_h)
        return None

    # ── Extract 2-D pixel coordinates ─────────────────────────────────────────
    landmarks_2d = np.array(
        [[lm.x * img_w, lm.y * img_h] for lm in results.pose_landmarks.landmark],
        dtype=np.float32,
    )  # (33, 2)

    # ── Extract 3-D normalised coordinates ────────────────────────────────────
    if results.pose_world_landmarks is not None:
        landmarks_3d = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.pose_world_landmarks.landmark],
            dtype=np.float32,
        )  # (33, 3)
    else:
        landmarks_3d = np.zeros((33, 3), dtype=np.float32)

    # ── Extract visibility ────────────────────────────────────────────────────
    visibility = np.array(
        [lm.visibility for lm in results.pose_landmarks.landmark],
        dtype=np.float32,
    )  # (33,)

    # ── Segmentation mask ─────────────────────────────────────────────────────
    seg_mask: np.ndarray | None = None
    if results.segmentation_mask is not None:
        seg_mask = np.array(results.segmentation_mask, dtype=np.float32)

    logger.debug(
        "Detected %d landmarks (min_vis=%.2f) in %d×%d image",
        len(results.pose_landmarks.landmark),
        float(visibility.min()),
        img_w,
        img_h,
    )

    return LandmarkResult(
        landmarks_2d=landmarks_2d,
        landmarks_3d=landmarks_3d,
        visibility=visibility,
        segmentation_mask=seg_mask,
    )
