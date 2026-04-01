"""Tests for wearme.body.measurements (Phase 2 param-based path)."""

from __future__ import annotations

import pytest

from wearme.body.body_params import BodyParameters
from wearme.body.measurements import (
    GarmentMeasurements,
    compute_measurements,
    measurements_from_params,
)


# ── GarmentMeasurements dataclass ─────────────────────────────────────────────

class TestGarmentMeasurementsDataclass:
    def test_is_frozen(self) -> None:
        """GarmentMeasurements is immutable (frozen dataclass)."""
        m = measurements_from_params(BodyParameters())
        with pytest.raises((AttributeError, TypeError)):
            m.chest_m = 1.0  # type: ignore[misc]

    def test_has_required_fields(self) -> None:
        """GarmentMeasurements must have all required measurement fields."""
        m = measurements_from_params(BodyParameters())
        required = {
            "height_m", "chest_m", "underbust_m", "waist_m", "abdomen_m",
            "hip_m", "neck_m", "shoulder_width_m", "arm_length_m",
            "upper_arm_m", "forearm_m", "wrist_m",
            "inseam_m", "outseam_m", "thigh_m", "calf_m", "ankle_m",
            "front_length_m", "back_length_m", "dart_width_m",
            "chest_with_ease_m", "waist_with_ease_m", "hip_with_ease_m",
            "eu_size_top", "eu_size_bottom", "us_size_top",
        }
        for field in required:
            assert hasattr(m, field), f"Missing field: {field}"

    def test_sizing_fields_are_strings(self) -> None:
        """EU/US sizing fields should be strings."""
        m = measurements_from_params(BodyParameters())
        assert isinstance(m.eu_size_top, str)
        assert isinstance(m.eu_size_bottom, str)
        assert isinstance(m.us_size_top, str)

    def test_all_numeric_fields_positive(self) -> None:
        """All numeric measurement fields should be positive."""
        m = measurements_from_params(BodyParameters())
        for field_name in m.__dataclass_fields__:
            val = getattr(m, field_name)
            if isinstance(val, (int, float)):
                assert val > 0, f"Field {field_name}={val} is not positive"


# ── measurements_from_params ──────────────────────────────────────────────────

class TestMeasurementsFromParams:
    def test_returns_garment_measurements(self) -> None:
        """measurements_from_params returns a GarmentMeasurements instance."""
        p = BodyParameters()
        assert isinstance(measurements_from_params(p), GarmentMeasurements)

    def test_height_matches_params(self) -> None:
        """height_m in measurements matches the body parameter."""
        p = BodyParameters(height_m=1.80)
        m = measurements_from_params(p)
        assert m.height_m == pytest.approx(1.80, abs=0.001)

    def test_ease_allowances_applied(self) -> None:
        """Ease-added fields should be larger than their base measurements."""
        p = BodyParameters()
        m = measurements_from_params(p)
        assert m.chest_with_ease_m > m.chest_m
        assert m.waist_with_ease_m > m.waist_m
        assert m.hip_with_ease_m   > m.hip_m

    def test_chest_ease_is_8cm(self) -> None:
        """EN 13402: chest ease allowance is 8 cm."""
        p = BodyParameters()
        m = measurements_from_params(p)
        assert m.chest_with_ease_m == pytest.approx(m.chest_m + 0.08, abs=0.001)

    def test_waist_ease_is_4cm(self) -> None:
        """EN 13402: waist ease allowance is 4 cm."""
        p = BodyParameters()
        m = measurements_from_params(p)
        assert m.waist_with_ease_m == pytest.approx(m.waist_m + 0.04, abs=0.001)

    def test_hip_ease_is_6cm(self) -> None:
        """EN 13402: hip ease allowance is 6 cm."""
        p = BodyParameters()
        m = measurements_from_params(p)
        assert m.hip_with_ease_m == pytest.approx(m.hip_m + 0.06, abs=0.001)

    def test_wider_hips_increases_hip_m(self) -> None:
        """Setting wider hip circumference increases hip_m in measurements."""
        p_wide   = BodyParameters()
        p_narrow = BodyParameters()
        p_wide._params["hip_circ_m"]   = 1.10
        p_narrow._params["hip_circ_m"] = 0.85
        assert measurements_from_params(p_wide).hip_m > measurements_from_params(p_narrow).hip_m

    def test_longer_inseam_increases_inseam_m(self) -> None:
        """Setting longer inseam increases inseam_m in measurements."""
        p_long  = BodyParameters()
        p_short = BodyParameters()
        p_long._params["inseam_m"]  = 0.90
        p_short._params["inseam_m"] = 0.70
        assert measurements_from_params(p_long).inseam_m > measurements_from_params(p_short).inseam_m

    def test_measurements_in_reasonable_range(self) -> None:
        """All numeric measurements should be physiologically plausible."""
        p = BodyParameters()
        m = measurements_from_params(p)
        assert 1.4  <= m.height_m          <= 2.2
        assert 0.7  <= m.chest_m           <= 1.5
        assert 0.5  <= m.waist_m           <= 1.4
        assert 0.7  <= m.hip_m             <= 1.5
        assert 0.5  <= m.inseam_m          <= 1.1
        assert 0.2  <= m.shoulder_width_m  <= 0.7


# ── EU / US sizing ────────────────────────────────────────────────────────────

class TestSizing:
    def _make_with_chest(self, chest_cm: float) -> GarmentMeasurements:
        p = BodyParameters()
        p._params["chest_circ_m"] = chest_cm / 100.0
        return measurements_from_params(p)

    def _make_with_waist(self, waist_cm: float) -> GarmentMeasurements:
        p = BodyParameters()
        p._params["waist_circ_m"] = waist_cm / 100.0
        return measurements_from_params(p)

    def test_eu_top_xs(self) -> None:
        """Chest ≤ 80 cm → EU top XS."""
        m = self._make_with_chest(78)
        assert m.eu_size_top == "XS"

    def test_eu_top_s(self) -> None:
        """Chest ≤ 84 cm → EU top S."""
        m = self._make_with_chest(82)
        assert m.eu_size_top == "S"

    def test_eu_top_m(self) -> None:
        """Chest ≤ 88 cm → EU top M."""
        m = self._make_with_chest(86)
        assert m.eu_size_top == "M"

    def test_eu_top_l(self) -> None:
        """Chest ≤ 92 cm → EU top L."""
        m = self._make_with_chest(90)
        assert m.eu_size_top == "L"

    def test_eu_top_xl(self) -> None:
        """Chest ≤ 96 cm → EU top XL."""
        m = self._make_with_chest(94)
        assert m.eu_size_top == "XL"

    def test_eu_top_xxl(self) -> None:
        """Chest ≤ 100 cm → EU top XXL."""
        m = self._make_with_chest(98)
        assert m.eu_size_top == "XXL"

    def test_eu_top_xxxl(self) -> None:
        """Chest > 100 cm → EU top XXXL."""
        m = self._make_with_chest(105)
        assert m.eu_size_top == "XXXL"

    def test_eu_top_xxs(self) -> None:
        """Chest ≤ 76 cm → EU top XXS."""
        m = self._make_with_chest(74)
        assert m.eu_size_top == "XXS"

    def test_us_top_s(self) -> None:
        """Chest ≤ 86 cm → US top S."""
        m = self._make_with_chest(84)
        assert m.us_size_top == "S"

    def test_eu_bottom_size(self) -> None:
        """EU bottom size is determined by waist circumference."""
        m = self._make_with_waist(78)
        assert m.eu_size_bottom in ("38", "40", "42")

    def test_sizing_strings_not_empty(self) -> None:
        """All sizing strings must be non-empty for any valid body."""
        for h in (1.50, 1.75, 1.95):
            for w in (50.0, 70.0, 100.0):
                p = BodyParameters(height_m=h, weight_kg=w)
                m = measurements_from_params(p)
                assert m.eu_size_top
                assert m.eu_size_bottom
                assert m.us_size_top


# ── compute_measurements (backward-compat) ────────────────────────────────────

class TestComputeMeasurements:
    def test_returns_legacy_dict(self) -> None:
        """compute_measurements returns a dict with the 4 legacy keys."""
        p = BodyParameters()
        result = compute_measurements(p)
        assert set(result.keys()) >= {"height_m", "chest_m", "waist_m", "hips_m"}

    def test_height_matches(self) -> None:
        """Legacy height_m matches BodyParameters height."""
        p = BodyParameters(height_m=1.72)
        result = compute_measurements(p)
        assert result["height_m"] == pytest.approx(1.72, abs=0.005)

    def test_values_in_range(self) -> None:
        """Legacy circumferences should be physiologically plausible."""
        p = BodyParameters()
        result = compute_measurements(p)
        assert 0.7  <= result["chest_m"] <= 1.5
        assert 0.5  <= result["waist_m"] <= 1.4
        assert 0.7  <= result["hips_m"]  <= 1.5

    def test_compute_measurements_consistent_with_from_params(self) -> None:
        """compute_measurements should agree with measurements_from_params."""
        p = BodyParameters()
        legacy = compute_measurements(p)
        full   = measurements_from_params(p)
        assert legacy["chest_m"] == pytest.approx(full.chest_m, abs=0.01)
        assert legacy["waist_m"] == pytest.approx(full.waist_m, abs=0.01)
