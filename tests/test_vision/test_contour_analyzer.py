"""Tests for wearme.vision.contour_analyzer.

Uses synthetic contours generated programmatically — no real images or
MediaPipe required.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from wearme.vision.contour_analyzer import (
    ContourAnalyzer,
    FrontMeasures,
    SideMeasures,
    _ellipse_circumference,
    _measure_width_at_y,
)


# ── Synthetic contour helpers ─────────────────────────────────────────────────

def _make_rect_contour(x0: float, y0: float, x1: float, y1: float, n_pts: int = 400) -> np.ndarray:
    """Generate a rectangular contour (N, 2) with evenly-spaced perimeter points."""
    perimeter = 2 * ((x1 - x0) + (y1 - y0))
    pts_per_side = max(2, n_pts // 4)

    top    = np.column_stack([np.linspace(x0, x1, pts_per_side), np.full(pts_per_side, y0)])
    right  = np.column_stack([np.full(pts_per_side, x1),          np.linspace(y0, y1, pts_per_side)])
    bottom = np.column_stack([np.linspace(x1, x0, pts_per_side), np.full(pts_per_side, y1)])
    left   = np.column_stack([np.full(pts_per_side, x0),          np.linspace(y1, y0, pts_per_side)])

    return np.vstack([top, right, bottom, left]).astype(np.float32)


def _make_hourglass_contour(img_w: int = 640, img_h: int = 1200) -> np.ndarray:
    """Generate a rough hourglass silhouette with shoulder wider than waist."""
    # Shoulders at y=200, width=400 (x: 120-520)
    # Waist at y=600, width=200 (x: 220-420)
    # Hips at y=800, width=380 (x: 130-510)
    pts = []
    for y, half_w in [
        (100, 150), (200, 200), (400, 170), (600, 100),
        (800, 190), (1000, 150), (1100, 100),
    ]:
        cx = img_w // 2
        pts.append([cx - half_w, y])
        pts.append([cx + half_w, y])
    return np.array(pts, dtype=np.float32)


def _make_landmarks(
    shoulder_y: float = 200.0,
    hip_y: float = 800.0,
    shoulder_x_l: float = 200.0,
    shoulder_x_r: float = 440.0,
    img_w: int = 640,
    img_h: int = 1200,
) -> np.ndarray:
    """Create a minimal 33-landmark array with key positions set."""
    lm = np.zeros((33, 2), dtype=np.float32)
    lm[11] = [shoulder_x_l, shoulder_y]   # left shoulder
    lm[12] = [shoulder_x_r, shoulder_y]   # right shoulder
    lm[23] = [img_w / 2 - 80, hip_y]      # left hip
    lm[24] = [img_w / 2 + 80, hip_y]      # right hip
    lm[27] = [img_w / 2 - 60, 1100.0]     # left ankle
    lm[28] = [img_w / 2 + 60, 1100.0]     # right ankle
    return lm


# ── _measure_width_at_y ───────────────────────────────────────────────────────

class TestMeasureWidthAtY:
    def test_width_of_known_rectangle(self) -> None:
        """Width of a 300 px wide rectangle should be ~300 px."""
        contour = _make_rect_contour(100, 50, 400, 500)
        width = _measure_width_at_y(contour, y_target=250.0, band_px=10.0)
        assert abs(width - 300.0) < 5.0, f"Expected ~300 px, got {width:.1f}"

    def test_returns_zero_when_no_points(self) -> None:
        """Returns 0.0 when no contour points are near the target Y."""
        contour = _make_rect_contour(0, 0, 100, 100)
        width = _measure_width_at_y(contour, y_target=500.0, band_px=5.0)
        assert width == 0.0

    def test_wider_band_captures_more(self) -> None:
        """A wider band should return at least as wide a measurement."""
        contour = _make_rect_contour(0, 0, 200, 400)
        w_narrow = _measure_width_at_y(contour, y_target=200.0, band_px=2.0)
        w_wide   = _measure_width_at_y(contour, y_target=200.0, band_px=20.0)
        assert w_wide >= w_narrow


# ── _ellipse_circumference ────────────────────────────────────────────────────

class TestEllipseCircumference:
    def test_circle_approximation(self) -> None:
        """For a circle (width == depth), circ ≈ π × d."""
        d = 0.30
        circ = _ellipse_circumference(d, d)
        expected = math.pi * d
        assert abs(circ - expected) < 0.001, f"Expected {expected:.4f}, got {circ:.4f}"

    def test_typical_waist_plausible(self) -> None:
        """A 25 cm wide, 18 cm deep waist gives a realistic circumference."""
        circ = _ellipse_circumference(0.25, 0.18)
        assert 0.60 < circ < 0.90, f"Waist circumference out of range: {circ:.3f} m"

    def test_width_greater_than_depth_gives_larger_circ(self) -> None:
        """Wider cross-section → larger circumference."""
        c_narrow = _ellipse_circumference(0.20, 0.15)
        c_wide   = _ellipse_circumference(0.40, 0.30)
        assert c_wide > c_narrow


# ── ContourAnalyzer.analyze_front ────────────────────────────────────────────

class TestAnalyzeFront:
    def setup_method(self) -> None:
        self.analyzer = ContourAnalyzer()
        self.img_h = 1200
        self.img_w = 640

    def test_returns_front_measures(self) -> None:
        contour = _make_rect_contour(100, 0, 540, 1100)
        lm = _make_landmarks(shoulder_y=200, hip_y=800)
        result = self.analyzer.analyze_front(contour, lm, self.img_h, self.img_w)
        assert isinstance(result, FrontMeasures)

    def test_shoulder_wider_than_waist(self) -> None:
        """Shoulder width from landmarks should be wider than waist contour."""
        contour = _make_rect_contour(220, 0, 420, 1100)  # 200 px wide
        # Shoulders at x=150 to x=490 → 340 px
        lm = _make_landmarks(shoulder_y=200, hip_y=800,
                              shoulder_x_l=150, shoulder_x_r=490)
        result = self.analyzer.analyze_front(contour, lm, self.img_h, self.img_w)
        assert result.shoulder_width_px > result.waist_width_px

    def test_all_widths_positive(self) -> None:
        """All width measurements must be positive."""
        contour = _make_rect_contour(100, 0, 540, 1100)
        lm = _make_landmarks()
        result = self.analyzer.analyze_front(contour, lm, self.img_h, self.img_w)
        assert result.shoulder_width_px > 0
        assert result.chest_width_px    > 0
        assert result.waist_width_px    > 0
        assert result.hip_width_px      > 0

    def test_y_positions_ordered(self) -> None:
        """shoulder_y < waist_y < hip_y (Y increases downward)."""
        contour = _make_rect_contour(100, 0, 540, 1100)
        lm = _make_landmarks(shoulder_y=200, hip_y=800)
        result = self.analyzer.analyze_front(contour, lm, self.img_h, self.img_w)
        assert result.shoulder_y_px < result.waist_y_px
        assert result.waist_y_px    < result.hip_y_px


# ── ContourAnalyzer.analyze_side ─────────────────────────────────────────────

class TestAnalyzeSide:
    def setup_method(self) -> None:
        self.analyzer = ContourAnalyzer()

    def test_returns_side_measures(self) -> None:
        contour = _make_rect_contour(200, 0, 440, 1100)
        lm = _make_landmarks()
        result = self.analyzer.analyze_side(contour, lm, 1200, 640)
        assert isinstance(result, SideMeasures)

    def test_all_depths_positive(self) -> None:
        contour = _make_rect_contour(200, 0, 440, 1100)
        lm = _make_landmarks()
        result = self.analyzer.analyze_side(contour, lm, 1200, 640)
        assert result.chest_depth_px > 0
        assert result.waist_depth_px > 0
        assert result.hip_depth_px   > 0


# ── ContourAnalyzer.convert_to_metric ────────────────────────────────────────

class TestConvertToMetric:
    def test_known_width_converts_correctly(self) -> None:
        """300 px / 1000 px_per_m = 0.30 m shoulder width."""
        front = FrontMeasures(
            shoulder_width_px=300.0,
            chest_width_px=280.0,
            waist_width_px=220.0,
            hip_width_px=290.0,
            shoulder_y_px=200.0,
            waist_y_px=500.0,
            hip_y_px=800.0,
        )
        metric = ContourAnalyzer.convert_to_metric(front, side=None, pixels_per_metre=1000.0)
        assert abs(metric["shoulder_width_m"] - 0.30) < 0.001

    def test_circumferences_larger_than_widths(self) -> None:
        """Estimated circumferences must be larger than the raw front widths."""
        front = FrontMeasures(
            shoulder_width_px=400.0,
            chest_width_px=380.0,
            waist_width_px=280.0,
            hip_width_px=390.0,
            shoulder_y_px=200.0,
            waist_y_px=500.0,
            hip_y_px=800.0,
        )
        metric = ContourAnalyzer.convert_to_metric(front, side=None, pixels_per_metre=1000.0)
        chest_width_m = front.chest_width_px / 1000.0
        assert metric["chest_m"] > chest_width_m
        assert metric["waist_m"] > front.waist_width_px / 1000.0
        assert metric["hip_m"]   > front.hip_width_px   / 1000.0

    def test_typical_body_values_plausible(self) -> None:
        """A typical body should give measurements in the human range."""
        # 420 px shoulder at 1000 px/m → 42 cm shoulder width
        front = FrontMeasures(
            shoulder_width_px=420.0,
            chest_width_px=400.0,
            waist_width_px=300.0,
            hip_width_px=410.0,
            shoulder_y_px=200.0,
            waist_y_px=500.0,
            hip_y_px=800.0,
        )
        metric = ContourAnalyzer.convert_to_metric(front, side=None, pixels_per_metre=1000.0)
        assert 0.30 < metric["shoulder_width_m"] < 0.60
        assert 0.70 < metric["chest_m"]           < 1.50
        assert 0.50 < metric["waist_m"]            < 1.20
        assert 0.70 < metric["hip_m"]              < 1.50

    def test_side_view_depth_used_when_provided(self) -> None:
        """When side is given, its depths are used instead of fallback ratios."""
        front = FrontMeasures(
            shoulder_width_px=400.0, chest_width_px=380.0,
            waist_width_px=280.0, hip_width_px=390.0,
            shoulder_y_px=200.0, waist_y_px=500.0, hip_y_px=800.0,
        )
        side_narrow = SideMeasures(chest_depth_px=100.0, waist_depth_px=80.0, hip_depth_px=110.0)
        side_wide   = SideMeasures(chest_depth_px=350.0, waist_depth_px=300.0, hip_depth_px=360.0)

        m_narrow = ContourAnalyzer.convert_to_metric(front, side_narrow, pixels_per_metre=1000.0)
        m_wide   = ContourAnalyzer.convert_to_metric(front, side_wide,   pixels_per_metre=1000.0)

        assert m_wide["chest_m"] > m_narrow["chest_m"]

    def test_raises_on_zero_pixels_per_metre(self) -> None:
        front = FrontMeasures(
            shoulder_width_px=300.0, chest_width_px=280.0,
            waist_width_px=220.0, hip_width_px=290.0,
            shoulder_y_px=200.0, waist_y_px=500.0, hip_y_px=800.0,
        )
        with pytest.raises(ValueError, match="pixels_per_metre"):
            ContourAnalyzer.convert_to_metric(front, side=None, pixels_per_metre=0.0)
