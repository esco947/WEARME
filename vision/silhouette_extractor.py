"""Body silhouette extraction from MediaPipe segmentation mask."""

from __future__ import annotations

import numpy as np


def extract_silhouette(image_bgr: np.ndarray) -> np.ndarray:
    """Extract person silhouette contour from a BGR image using MediaPipe.

    Runs MediaPipe segmentation, applies morphological cleanup, and returns
    the outer contour of the largest connected component.

    Args:
        image_bgr: Input image, shape (H, W, 3), BGR.

    Returns:
        contour: (N, 2) array of pixel coordinates [x, y].

    Raises:
        ValueError: If no person detected or no contour found.
    """
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError(f"image_bgr must have shape (H, W, 3), got {image_bgr.shape}.")

    try:
        import cv2  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("OpenCV is required. Install: pip install opencv-python-headless>=4.8") from exc

    try:
        import mediapipe as mp  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("MediaPipe is required. Install: pip install mediapipe>=0.10") from exc

    _MP_POSE = mp.solutions.pose

    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError(f"image_bgr must have shape (H, W, 3), got {image_bgr.shape}.")

    image_rgb = image_bgr[:, :, ::-1].copy()

    with _MP_POSE.Pose(
        model_complexity=1,
        enable_segmentation=True,
        static_image_mode=True,
        min_detection_confidence=0.5,
    ) as pose:
        results = pose.process(image_rgb)

    if results.pose_landmarks is None or results.segmentation_mask is None:
        raise ValueError("No person detected in image.")

    mask = np.array(results.segmentation_mask, dtype=np.float32)
    binary = (mask > 0.5).astype(np.uint8) * 255

    # Morphological closing — fill small holes
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k_close, iterations=3)

    # Morphological opening — remove noise
    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k_open, iterations=2)

    # Keep largest connected component
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if n_labels <= 1:
        raise ValueError("No foreground connected components found.")

    largest_label = int(np.argmax(stats[1:, cv2.CC_STAT_AREA]) + 1)
    cleaned = np.zeros_like(binary)
    cleaned[labels == largest_label] = 255

    # Extract outer contour
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("No contours found after morphological cleanup.")

    main_contour = max(contours, key=cv2.contourArea)
    contour_pts = main_contour[:, 0, :]  # (N, 1, 2) -> (N, 2)

    return contour_pts.astype(np.float32)
