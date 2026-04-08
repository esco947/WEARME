"""Photo-to-body-params fitting pipeline (Phase 4).

Orchestrates the full pipeline from one or two photos to a populated
:class:`~wearme.body.body_params.BodyParameters` object:

1. MediaPipe Pose landmark detection (:mod:`~wearme.vision.landmarks`)
2. Body silhouette extraction (:mod:`~wearme.vision.segmentation`)
3. Camera scale estimation (:mod:`~wearme.vision.camera_estimation`)
4. Contour width/depth measurement (:mod:`~wearme.vision.contour_analyzer`)
5. Metric conversion + known height injection
6. SMPL beta optimisation (:mod:`~wearme.body.beta_optimizer`)
7. Return a fully-populated :class:`~wearme.body.body_params.BodyParameters`

Requires the vision extras::

    pip install wearme[vision]

Usage::

    import cv2
    from wearme.vision.photo_fitter import PhotoFitter

    fitter = PhotoFitter(n_iter=100)
    front = cv2.imread("front.jpg")
    params = fitter.fit(front, known_height_m=1.75, gender="male")
    print(params.betas)
    print(params._params["chest_circ_m"])
"""

from __future__ import annotations

import logging

import numpy as np

from wearme.body.beta_optimizer import optimize_betas
from wearme.body.body_params import BodyParameters
from wearme.body.proportions import PARAM_REGISTRY
from wearme.vision.camera_estimation import estimate_from_landmarks
from wearme.vision.contour_analyzer import ContourAnalyzer
from wearme.vision.landmarks import detect_landmarks
from wearme.vision.segmentation import extract_silhouette

logger = logging.getLogger(__name__)

# ── Measurement key mapping ───────────────────────────────────────────────────
# Maps metric dict keys from ContourAnalyzer.convert_to_metric() to the
# corresponding PARAM_REGISTRY keys used in BodyParameters._params.
_METRIC_TO_PARAM: dict[str, str] = {
    "chest_m":          "chest_circ_m",
    "waist_m":          "waist_circ_m",
    "hip_m":            "hip_circ_m",
    "shoulder_width_m": "shoulder_width_m",
}


# ── PhotoFitter ───────────────────────────────────────────────────────────────

class PhotoFitter:
    """Full photo-to-body-params fitting pipeline.

    Args:
        n_iter:            Number of L-BFGS-B optimisation iterations passed to
                           :func:`~wearme.body.beta_optimizer.optimize_betas`.
                           Use 50 for a quick estimate, 200 for better accuracy.
        require_side_view: If ``True``, :meth:`fit` raises :exc:`ValueError`
                           when *side_image* is ``None``.  Default ``False``.
    """

    def __init__(
        self,
        n_iter: int = 200,
        require_side_view: bool = False,
    ) -> None:
        self.n_iter = n_iter
        self.require_side_view = require_side_view
        self._analyzer = ContourAnalyzer()

    def fit(
        self,
        front_image: np.ndarray,
        known_height_m: float,
        gender: str = "neutral",
        side_image: np.ndarray | None = None,
    ) -> BodyParameters:
        """Fit body parameters from one or two photos.

        Args:
            front_image:    Front-view image, BGR numpy array ``(H, W, 3)``.
            known_height_m: Actual standing height in metres (required).
            gender:         SMPL model gender: ``"neutral"`` | ``"male"`` | ``"female"``.
            side_image:     Optional side-view image (BGR). Improves depth
                            measurements when provided.

        Returns:
            :class:`~wearme.body.body_params.BodyParameters` with optimised
            betas and measurement-populated ``_params``.

        Raises:
            ValueError: If landmark detection fails on *front_image*.
            ValueError: If *side_image* is ``None`` and ``require_side_view=True``.
            ValueError: If *known_height_m* is not in the valid height range.
        """
        if self.require_side_view and side_image is None:
            raise ValueError(
                "side_image is required (require_side_view=True)."
            )

        img_h, img_w = front_image.shape[:2]

        # ── Step 1: Front landmark detection ─────────────────────────────────
        logger.info("Running MediaPipe landmark detection on front image (%d×%d)", img_w, img_h)
        front_lm = detect_landmarks(front_image)
        if front_lm is None:
            raise ValueError(
                "No person detected in front_image. "
                "Ensure the full body is visible and well-lit."
            )

        # ── Step 2: Front silhouette extraction ───────────────────────────────
        front_sil = None
        if front_lm.segmentation_mask is not None:
            front_sil = extract_silhouette(front_image, front_lm.segmentation_mask)
        if front_sil is None:
            logger.warning("Could not extract front silhouette; contour measurements will use fallback values.")

        # ── Step 3: Camera scale estimation ──────────────────────────────────
        cam = estimate_from_landmarks(
            front_lm.landmarks_2d,
            known_height_m=known_height_m,
            img_h=img_h,
            img_w=img_w,
        )
        logger.info("Camera scale: %.1f px/m", cam.pixels_per_metre)

        # ── Step 4 (optional): Side view ──────────────────────────────────────
        side_measures = None
        if side_image is not None:
            side_h, side_w = side_image.shape[:2]
            logger.info("Running MediaPipe on side image (%d×%d)", side_w, side_h)
            side_lm = detect_landmarks(side_image)
            if side_lm is not None and side_lm.segmentation_mask is not None:
                side_sil = extract_silhouette(side_image, side_lm.segmentation_mask)
                if side_sil is not None:
                    side_measures = self._analyzer.analyze_side(
                        side_sil.contour,
                        side_lm.landmarks_2d,
                        side_h,
                        side_w,
                    )
            if side_measures is None:
                logger.warning("Side view processing failed; using depth fallbacks.")

        # ── Step 5: Measure front contour ─────────────────────────────────────
        if front_sil is not None:
            front_measures = self._analyzer.analyze_front(
                front_sil.contour,
                front_lm.landmarks_2d,
                img_h,
                img_w,
            )
        else:
            # Fallback: estimate from landmark distances only
            front_measures = self._analyzer.analyze_front(
                # Create a minimal dummy contour from landmark X range
                _landmarks_to_dummy_contour(front_lm.landmarks_2d, img_h, img_w),
                front_lm.landmarks_2d,
                img_h,
                img_w,
            )

        # ── Step 6: Convert to metric ─────────────────────────────────────────
        metric = ContourAnalyzer.convert_to_metric(
            front_measures,
            side_measures,
            cam.pixels_per_metre,
        )
        metric["height_m"] = known_height_m  # ground truth overrides any estimate

        logger.info(
            "Extracted measurements: %s",
            {k: f"{v:.3f}" for k, v in metric.items()},
        )

        # ── Step 7: Optimise SMPL betas ───────────────────────────────────────
        # Only pass keys recognised by the optimizer
        optimizer_targets = {k: v for k, v in metric.items()
                             if k in {"height_m", "chest_m", "waist_m", "hip_m"}}
        logger.info("Optimising SMPL betas (n_iter=%d, gender=%r)...", self.n_iter, gender)
        betas = optimize_betas(
            target_measures=optimizer_targets,
            gender=gender,
            n_iter=self.n_iter,
        )

        # ── Step 8: Build BodyParameters ──────────────────────────────────────
        params = BodyParameters(
            gender=gender,
            betas=betas,
            height_m=known_height_m,
        )

        # Populate _params with the photo-derived measurements so that
        # sliders in BodyEditor reflect the actual measurements.
        for metric_key, param_key in _METRIC_TO_PARAM.items():
            if metric_key in metric and param_key in PARAM_REGISTRY:
                bounds = PARAM_REGISTRY[param_key]
                value = float(np.clip(metric[metric_key], bounds.min_val, bounds.max_val))
                params._params[param_key] = value

        logger.info("Photo fitting complete. Final betas: %s", betas.round(3))
        return params


# ── Internal helper ───────────────────────────────────────────────────────────

def _landmarks_to_dummy_contour(
    landmarks_2d: np.ndarray,
    img_h: int,
    img_w: int,
) -> np.ndarray:
    """Create a minimal rectangular dummy contour from landmark X extent.

    Used as a fallback when silhouette extraction fails.  The contour spans
    the full vertical range of the visible landmarks.

    Args:
        landmarks_2d: Pixel landmarks, shape ``(33, 2)``.
        img_h:        Image height.
        img_w:        Image width.

    Returns:
        Numpy array ``(N, 2)`` representing a rectangle.
    """
    x_min = float(landmarks_2d[:, 0].min())
    x_max = float(landmarks_2d[:, 0].max())
    y_min = float(landmarks_2d[:, 1].min())
    y_max = float(landmarks_2d[:, 1].max())

    # Pad by 10 % to approximate the body boundary beyond the skeleton
    x_pad = (x_max - x_min) * 0.10
    x_min = max(0.0, x_min - x_pad)
    x_max = min(float(img_w), x_max + x_pad)

    # Build a rectangular contour with enough points for width measurement
    n_pts = 100
    xs_top = np.linspace(x_min, x_max, n_pts // 4)
    xs_bot = np.linspace(x_max, x_min, n_pts // 4)
    ys_r   = np.linspace(y_min, y_max, n_pts // 4)
    ys_l   = np.linspace(y_max, y_min, n_pts // 4)

    top = np.column_stack([xs_top, np.full(len(xs_top), y_min)])
    right = np.column_stack([np.full(len(ys_r), x_max), ys_r])
    bottom = np.column_stack([xs_bot, np.full(len(xs_bot), y_max)])
    left = np.column_stack([np.full(len(ys_l), x_min), ys_l])

    return np.vstack([top, right, bottom, left]).astype(np.float32)
