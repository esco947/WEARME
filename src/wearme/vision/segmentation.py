"""Body silhouette extraction from MediaPipe segmentation masks (Phase 4).

Takes the float32 segmentation mask produced by MediaPipe Pose and applies
morphological cleanup to produce a crisp binary silhouette contour suitable
for body measurement extraction.

Requires the vision extras::

    pip install wearme[vision]

Usage::

    import cv2
    from wearme.vision.landmarks import detect_landmarks
    from wearme.vision.segmentation import extract_silhouette

    image = cv2.imread("front.jpg")
    result_lm = detect_landmarks(image)
    if result_lm is not None:
        sil = extract_silhouette(image, result_lm.segmentation_mask)
        if sil is not None:
            print(sil.contour.shape)        # (N, 2)
            print(sil.bounding_box)         # (x, y, w, h)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2  # type: ignore[import]
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "OpenCV is required for silhouette extraction. "
        "Install the vision extras: pip install wearme[vision]"
    ) from exc


# ── Result container ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SilhouetteResult:
    """Cleaned binary silhouette from a person segmentation mask.

    Attributes:
        binary_mask:   uint8 binary mask, shape ``(H, W)``.  Person pixels = 255,
                       background = 0.
        contour:       Outer contour points, shape ``(N, 2)`` — pixel ``[x, y]``.
                       All contour points are kept (``CHAIN_APPROX_NONE``) for
                       accurate downstream width measurements.
        bounding_box:  Axis-aligned bounding box of the contour: ``(x, y, w, h)``.
    """

    binary_mask:  np.ndarray                     # (H, W) uint8
    contour:      np.ndarray                     # (N, 2) pixels [x, y]
    bounding_box: tuple[int, int, int, int]      # (x, y, w, h)


# ── Morphological constants ───────────────────────────────────────────────────

_CLOSE_KERNEL_SIZE: int = 5
_CLOSE_ITERATIONS:  int = 3
_OPEN_KERNEL_SIZE:  int = 3
_OPEN_ITERATIONS:   int = 2


# ── Public API ────────────────────────────────────────────────────────────────

def extract_silhouette(
    image: np.ndarray,
    mask: np.ndarray,
    threshold: float = 0.5,
) -> SilhouetteResult | None:
    """Extract a clean binary silhouette from a MediaPipe segmentation mask.

    Pipeline:

    1. Threshold the float mask to a uint8 binary image.
    2. Morphological **closing** (5×5 kernel, 3 iter) — fills small holes.
    3. Morphological **opening** (3×3 kernel, 2 iter) — removes noise.
    4. Keep only the **largest connected component** (the person).
    5. Extract the outer contour with ``CHAIN_APPROX_NONE``.

    Args:
        image:      Original BGR image, shape ``(H, W, 3)``.  Used only for
                    shape validation.
        mask:       Float32 segmentation mask, shape ``(H, W)``, values in
                    ``[0, 1]``.  Typically ``result.segmentation_mask`` from
                    :func:`~wearme.vision.landmarks.detect_landmarks`.
        threshold:  Binary threshold.  Pixels above this value are foreground.
                    Default 0.5.

    Returns:
        :class:`SilhouetteResult` or ``None`` if no foreground contour is found.

    Raises:
        ValueError: If *mask* shape does not match *image* height/width.
    """
    if mask.ndim != 2:
        raise ValueError(f"mask must be 2-D, got shape {mask.shape}.")
    img_h, img_w = image.shape[:2]
    if mask.shape != (img_h, img_w):
        raise ValueError(
            f"mask shape {mask.shape} does not match image ({img_h}, {img_w})."
        )

    # 1. Threshold → uint8
    binary = (mask > threshold).astype(np.uint8) * 255

    # 2. Morphological closing
    k_close = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (_CLOSE_KERNEL_SIZE, _CLOSE_KERNEL_SIZE)
    )
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k_close, iterations=_CLOSE_ITERATIONS)

    # 3. Morphological opening
    k_open = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (_OPEN_KERNEL_SIZE, _OPEN_KERNEL_SIZE)
    )
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k_open, iterations=_OPEN_ITERATIONS)

    # 4. Keep largest connected component
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if n_labels <= 1:
        logger.debug("No foreground connected components found.")
        return None

    # stats[0] is background — skip it
    largest_label = int(np.argmax(stats[1:, cv2.CC_STAT_AREA]) + 1)
    cleaned = np.zeros_like(binary)
    cleaned[labels == largest_label] = 255

    # 5. Extract outer contour
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        logger.debug("No contours found after morphological cleanup.")
        return None

    # Use the largest contour by arc length
    main_contour = max(contours, key=cv2.contourArea)
    contour_pts = main_contour[:, 0, :]  # reshape (N, 1, 2) → (N, 2)

    # Bounding box
    x, y, w, h = cv2.boundingRect(main_contour)

    logger.debug(
        "Silhouette extracted: %d contour points, bbox=(%d,%d,%d,%d)",
        len(contour_pts), x, y, w, h,
    )

    return SilhouetteResult(
        binary_mask=cleaned,
        contour=contour_pts.astype(np.float32),
        bounding_box=(int(x), int(y), int(w), int(h)),
    )
