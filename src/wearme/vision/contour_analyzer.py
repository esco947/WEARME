"""Body width measurement extraction from silhouette contours (Phase 4).

Analyses front-view and (optionally) side-view body silhouette contours to
extract anatomical widths and depths at landmark-derived heights.  The
measurements are then converted to metric (metres) and approximate
circumferences via the elliptical perimeter formula.

All coordinates use the **image convention**: origin at top-left, Y increases
downward.  This matches both MediaPipe and OpenCV.

Usage::

    import numpy as np
    from wearme.vision.contour_analyzer import ContourAnalyzer

    analyzer = ContourAnalyzer()
    front_m = analyzer.analyze_front(contour, landmarks_2d, img_h, img_w)
    metric  = ContourAnalyzer.convert_to_metric(front_m, side_m=None,
                  pixels_per_metre=cam.pixels_per_metre)
    # metric: {"shoulder_width_m": 0.42, "chest_m": 0.97, ...}
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# ── MediaPipe landmark indices ────────────────────────────────────────────────

_IDX_L_SHOULDER: int = 11
_IDX_R_SHOULDER: int = 12
_IDX_L_HIP:      int = 23
_IDX_R_HIP:      int = 24

# ── Elliptical circumference depth ratios (ANSUR II / PARAM_REGISTRY) ─────────
# When no side view is available, depth is estimated from front width.
#   chest  : depth / width ≈ 0.68  (215 mm / 315 mm from PARAM_REGISTRY defaults)
#   waist  : depth / width ≈ 0.74  (waist_depth_m / waist_width_m)
#   hip    : depth / width ≈ 0.72  (hip_depth_m / hip_width_m)
_DEPTH_RATIO_CHEST: float = 0.68
_DEPTH_RATIO_WAIST: float = 0.74
_DEPTH_RATIO_HIP:   float = 0.72

# ── Scan band width ───────────────────────────────────────────────────────────
# Contour points within ±BAND_FRACTION × img_h of the target Y are used.
_BAND_FRACTION: float = 0.008


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FrontMeasures:
    """Body widths extracted from a front-view silhouette (pixels).

    Attributes:
        shoulder_width_px: Horizontal distance between shoulder points.
        chest_width_px:    Width at chest level (≈60 % shoulder-to-hip).
        waist_width_px:    Width at the narrowest mid-trunk point.
        hip_width_px:      Width at hip level.
        shoulder_y_px:     Y coordinate of the shoulder scan line.
        waist_y_px:        Y coordinate of the waist scan line.
        hip_y_px:          Y coordinate of the hip scan line.
    """

    shoulder_width_px: float
    chest_width_px:    float
    waist_width_px:    float
    hip_width_px:      float
    shoulder_y_px:     float
    waist_y_px:        float
    hip_y_px:          float


@dataclass(frozen=True)
class SideMeasures:
    """Body depths extracted from a side-view silhouette (pixels).

    Attributes:
        chest_depth_px: Depth (front-to-back) at chest level.
        waist_depth_px: Depth at waist level.
        hip_depth_px:   Depth at hip level.
    """

    chest_depth_px: float
    waist_depth_px: float
    hip_depth_px:   float


# ── Helper ────────────────────────────────────────────────────────────────────

def _measure_width_at_y(
    contour: np.ndarray,
    y_target: float,
    band_px: float,
) -> float:
    """Measure contour width at a given Y position.

    Finds all contour points within ±band_px of y_target and returns the
    horizontal span (x_max - x_min).

    Args:
        contour:  Contour points, shape ``(N, 2)`` — pixel ``[x, y]``.
        y_target: Target Y coordinate.
        band_px:  Half-bandwidth in pixels.

    Returns:
        Width in pixels, or 0.0 if fewer than 2 points are found.
    """
    mask = np.abs(contour[:, 1] - y_target) <= band_px
    if not np.any(mask):
        return 0.0
    x_vals = contour[mask, 0]
    if len(x_vals) < 2:
        return 0.0
    return float(x_vals.max() - x_vals.min())


def _ellipse_circumference(width_m: float, depth_m: float) -> float:
    """Approximate ellipse perimeter from semi-axes.

    Uses the formula: circ ≈ π × sqrt(2 × ((w/2)² + (d/2)²)).
    This is the Ramanujan-style first-order approximation, accurate to
    within ~5 % for realistic body cross-sections.

    Args:
        width_m: Horizontal diameter (metres).
        depth_m: Depth / antero-posterior diameter (metres).

    Returns:
        Approximate circumference in metres.
    """
    a = width_m / 2.0
    b = depth_m / 2.0
    return math.pi * math.sqrt(2.0 * (a * a + b * b))


# ── Main class ────────────────────────────────────────────────────────────────

class ContourAnalyzer:
    """Extracts body width and depth measurements from silhouette contours.

    Uses MediaPipe Pose landmarks to locate anatomically meaningful Y
    positions, then measures the contour width at each position.
    """

    def analyze_front(
        self,
        contour: np.ndarray,
        landmarks_2d: np.ndarray,
        img_h: int,
        img_w: int,
    ) -> FrontMeasures:
        """Measure widths from a front-view silhouette.

        Landmark-derived Y positions::

            shoulder_y = mean Y of landmarks 11 (L) and 12 (R shoulder)
            hip_y      = mean Y of landmarks 23 (L) and 24 (R hip)
            waist_y    = midpoint(shoulder_y, hip_y)
            chest_y    = shoulder_y + 0.40 × (hip_y - shoulder_y)

        Args:
            contour:      Contour points, shape ``(N, 2)``.
            landmarks_2d: Pixel landmarks, shape ``(33, 2)``.
            img_h:        Image height in pixels.
            img_w:        Image width in pixels.

        Returns:
            :class:`FrontMeasures` with pixel-space measurements.
        """
        band_px = max(4.0, _BAND_FRACTION * img_h)

        shoulder_y = float(
            (landmarks_2d[_IDX_L_SHOULDER, 1] + landmarks_2d[_IDX_R_SHOULDER, 1]) / 2.0
        )
        hip_y = float(
            (landmarks_2d[_IDX_L_HIP, 1] + landmarks_2d[_IDX_R_HIP, 1]) / 2.0
        )
        waist_y = (shoulder_y + hip_y) / 2.0
        chest_y = shoulder_y + 0.40 * (hip_y - shoulder_y)

        # Direct shoulder width: distance between landmark X positions
        shoulder_width_px = float(abs(
            landmarks_2d[_IDX_L_SHOULDER, 0] - landmarks_2d[_IDX_R_SHOULDER, 0]
        ))

        # Contour-based widths
        chest_width_px = _measure_width_at_y(contour, chest_y, band_px)
        waist_width_px = _measure_width_at_y(contour, waist_y, band_px)
        hip_width_px   = _measure_width_at_y(contour, hip_y,   band_px)

        # Fallback: use shoulder width if contour measure failed
        if chest_width_px <= 0.0:
            chest_width_px = shoulder_width_px * 1.05
        if waist_width_px <= 0.0:
            waist_width_px = shoulder_width_px * 0.80
        if hip_width_px <= 0.0:
            hip_width_px = shoulder_width_px * 1.10

        logger.debug(
            "Front measures (px): shoulder=%.1f chest=%.1f waist=%.1f hip=%.1f",
            shoulder_width_px, chest_width_px, waist_width_px, hip_width_px,
        )

        return FrontMeasures(
            shoulder_width_px=shoulder_width_px,
            chest_width_px=chest_width_px,
            waist_width_px=waist_width_px,
            hip_width_px=hip_width_px,
            shoulder_y_px=shoulder_y,
            waist_y_px=waist_y,
            hip_y_px=hip_y,
        )

    def analyze_side(
        self,
        contour: np.ndarray,
        landmarks_2d: np.ndarray,
        img_h: int,
        img_w: int,
    ) -> SideMeasures:
        """Measure depths from a side-view silhouette.

        Reuses the same Y positions derived from side-view landmarks.

        Args:
            contour:      Contour points from side-view silhouette.
            landmarks_2d: Pixel landmarks from side-view image.
            img_h:        Image height in pixels.
            img_w:        Image width in pixels.

        Returns:
            :class:`SideMeasures` with pixel-space depths.
        """
        band_px = max(4.0, _BAND_FRACTION * img_h)

        shoulder_y = float(
            (landmarks_2d[_IDX_L_SHOULDER, 1] + landmarks_2d[_IDX_R_SHOULDER, 1]) / 2.0
        )
        hip_y = float(
            (landmarks_2d[_IDX_L_HIP, 1] + landmarks_2d[_IDX_R_HIP, 1]) / 2.0
        )
        waist_y = (shoulder_y + hip_y) / 2.0
        chest_y = shoulder_y + 0.40 * (hip_y - shoulder_y)

        chest_depth_px = _measure_width_at_y(contour, chest_y, band_px)
        waist_depth_px = _measure_width_at_y(contour, waist_y, band_px)
        hip_depth_px   = _measure_width_at_y(contour, hip_y,   band_px)

        logger.debug(
            "Side measures (px): chest=%.1f waist=%.1f hip=%.1f",
            chest_depth_px, waist_depth_px, hip_depth_px,
        )

        return SideMeasures(
            chest_depth_px=chest_depth_px,
            waist_depth_px=waist_depth_px,
            hip_depth_px=hip_depth_px,
        )

    @staticmethod
    def convert_to_metric(
        front: FrontMeasures,
        side: SideMeasures | None,
        pixels_per_metre: float,
    ) -> dict[str, float]:
        """Convert pixel measurements to metric and estimate circumferences.

        When *side* is provided, the actual depth is used.  Otherwise, depth
        is estimated from width via empirical ratios derived from ANSUR II data
        and the PARAM_REGISTRY default body proportions.

        Circumference formula (elliptical cross-section)::

            circ ≈ π × sqrt(2 × ((width/2)² + (depth/2)²))

        Args:
            front:             Front-view pixel measurements.
            side:              Side-view pixel measurements or ``None``.
            pixels_per_metre:  Scale factor from
                               :class:`~wearme.vision.camera_estimation.CameraParams`.

        Returns:
            Dict with keys:

            * ``"shoulder_width_m"``
            * ``"chest_m"``   — chest circumference
            * ``"waist_m"``   — waist circumference
            * ``"hip_m"``     — hip circumference

        Raises:
            ValueError: If *pixels_per_metre* is zero or negative.
        """
        if pixels_per_metre <= 0.0:
            raise ValueError(
                f"pixels_per_metre must be positive, got {pixels_per_metre}."
            )

        ppm = pixels_per_metre

        # Convert widths to metres
        shoulder_w = front.shoulder_width_px / ppm
        chest_w    = front.chest_width_px    / ppm
        waist_w    = front.waist_width_px    / ppm
        hip_w      = front.hip_width_px      / ppm

        # Depths (from side or estimated)
        if side is not None and side.chest_depth_px > 0.0:
            chest_d = side.chest_depth_px / ppm
            waist_d = side.waist_depth_px / ppm if side.waist_depth_px > 0.0 else waist_w * _DEPTH_RATIO_WAIST
            hip_d   = side.hip_depth_px   / ppm if side.hip_depth_px   > 0.0 else hip_w   * _DEPTH_RATIO_HIP
        else:
            chest_d = chest_w * _DEPTH_RATIO_CHEST
            waist_d = waist_w * _DEPTH_RATIO_WAIST
            hip_d   = hip_w   * _DEPTH_RATIO_HIP

        chest_circ = _ellipse_circumference(chest_w, chest_d)
        waist_circ = _ellipse_circumference(waist_w, waist_d)
        hip_circ   = _ellipse_circumference(hip_w,   hip_d)

        logger.debug(
            "Metric: shoulder=%.3f m  chest=%.3f m  waist=%.3f m  hip=%.3f m",
            shoulder_w, chest_circ, waist_circ, hip_circ,
        )

        return {
            "shoulder_width_m": round(shoulder_w, 4),
            "chest_m":          round(chest_circ, 4),
            "waist_m":          round(waist_circ, 4),
            "hip_m":            round(hip_circ,   4),
        }
