"""Tests for wearme.body.proportions."""

from __future__ import annotations

import pytest

from wearme.body.proportions import (
    PARAM_REGISTRY,
    ParamBounds,
    allometric_scale,
    get_defaults,
    validate_param,
    weight_redistribute,
)


# ── PARAM_REGISTRY ────────────────────────────────────────────────────────────

def test_registry_has_55_params() -> None:
    """PARAM_REGISTRY should contain exactly 56 entries (55 anatomical + bmi)."""
    assert len(PARAM_REGISTRY) == 56


def test_registry_contains_required_keys() -> None:
    """Critical params must be present in the registry."""
    required = {
        "height_m", "weight_kg",
        "chest_circ_m", "waist_circ_m", "hip_circ_m",
        "shoulder_width_m", "arm_length_m", "inseam_m",
        "bmi",
    }
    assert required.issubset(PARAM_REGISTRY.keys())


def test_all_entries_are_param_bounds() -> None:
    """Every entry in PARAM_REGISTRY is a ParamBounds instance."""
    for name, bounds in PARAM_REGISTRY.items():
        assert isinstance(bounds, ParamBounds), f"{name} is not ParamBounds"


def test_min_less_than_max() -> None:
    """min_val must be strictly less than max_val for all params."""
    for name, b in PARAM_REGISTRY.items():
        assert b.min_val < b.max_val, f"{name}: min >= max"


def test_defaults_within_bounds() -> None:
    """All sex-specific defaults must lie within [min_val, max_val]."""
    for name, b in PARAM_REGISTRY.items():
        assert b.min_val <= b.default_male    <= b.max_val, f"{name} male default out of range"
        assert b.min_val <= b.default_female  <= b.max_val, f"{name} female default out of range"
        assert b.min_val <= b.default_neutral <= b.max_val, f"{name} neutral default out of range"


def test_height_exponent_non_negative() -> None:
    """height_exponent must be non-negative for all params."""
    for name, b in PARAM_REGISTRY.items():
        assert b.height_exponent >= 0.0, f"{name}: negative exponent"


def test_bmi_is_read_only() -> None:
    """bmi must be marked as read_only."""
    assert PARAM_REGISTRY["bmi"].read_only is True


def test_height_weight_not_read_only() -> None:
    """height_m and weight_kg must not be read_only."""
    assert PARAM_REGISTRY["height_m"].read_only is False
    assert PARAM_REGISTRY["weight_kg"].read_only is False


# ── get_defaults ──────────────────────────────────────────────────────────────

def test_get_defaults_neutral_returns_all_params() -> None:
    """get_defaults('neutral') returns a key for every registry entry."""
    d = get_defaults("neutral")
    assert set(d.keys()) == set(PARAM_REGISTRY.keys())


def test_get_defaults_gender_specific_values() -> None:
    """Male and female defaults differ for sexually dimorphic params."""
    male    = get_defaults("male")
    female  = get_defaults("female")
    # Men are taller on average
    assert male["height_m"]   > female["height_m"]
    # Women have wider hips on average
    assert female["hip_circ_m"] > male["hip_circ_m"]


def test_get_defaults_neutral_between_male_female() -> None:
    """Neutral defaults should be between male and female for most params."""
    male    = get_defaults("male")
    female  = get_defaults("female")
    neutral = get_defaults("neutral")
    # For height_m: female < neutral < male
    assert female["height_m"] <= neutral["height_m"] <= male["height_m"]


def test_get_defaults_unknown_gender_falls_back_to_neutral() -> None:
    """get_defaults silently falls back to neutral for an unknown gender string."""
    result  = get_defaults("robot")
    neutral = get_defaults("neutral")
    assert result == neutral


# ── validate_param ────────────────────────────────────────────────────────────

def test_validate_param_passes_in_range() -> None:
    """validate_param accepts values within bounds."""
    validate_param("height_m", 1.75)
    validate_param("chest_circ_m", 0.95)


def test_validate_param_rejects_too_low() -> None:
    """validate_param raises ValueError when value is below min."""
    with pytest.raises(ValueError):
        validate_param("height_m", 1.0)  # below 1.40


def test_validate_param_rejects_too_high() -> None:
    """validate_param raises ValueError when value exceeds max."""
    with pytest.raises(ValueError):
        validate_param("height_m", 3.0)  # above 2.20


def test_validate_param_rejects_unknown_name() -> None:
    """validate_param raises an error for an unknown param name."""
    with pytest.raises((KeyError, ValueError)):
        validate_param("nonexistent_param", 1.0)


def test_validate_param_accepts_boundary_values() -> None:
    """validate_param accepts values exactly at min and max."""
    b = PARAM_REGISTRY["height_m"]
    validate_param("height_m", b.min_val)
    validate_param("height_m", b.max_val)


# ── allometric_scale ──────────────────────────────────────────────────────────

def test_allometric_scale_taller_increases_lengths() -> None:
    """Scaling to a taller height increases length params."""
    params = get_defaults("neutral")
    original_inseam = params["inseam_m"]
    result = allometric_scale(params, new_height=1.90, locked=set())
    assert result["inseam_m"] > original_inseam


def test_allometric_scale_shorter_decreases_lengths() -> None:
    """Scaling to a shorter height decreases length params."""
    params = get_defaults("neutral")
    original_arm = params["arm_length_m"]
    result = allometric_scale(params, new_height=1.60, locked=set())
    assert result["arm_length_m"] < original_arm


def test_allometric_scale_preserves_same_height() -> None:
    """Scaling to the same height leaves all params unchanged."""
    params = get_defaults("neutral")
    h = params["height_m"]
    result = allometric_scale(params, new_height=h, locked=set())
    for name in result:
        assert abs(result[name] - params[name]) < 1e-9, f"{name} changed unexpectedly"


def test_allometric_scale_respects_lock() -> None:
    """Locked params are not changed by allometric scaling."""
    params = get_defaults("neutral")
    original_inseam = params["inseam_m"]
    locked = {"inseam_m"}
    result = allometric_scale(params, new_height=2.00, locked=locked)
    assert result["inseam_m"] == pytest.approx(original_inseam)


def test_allometric_scale_non_height_params_unchanged() -> None:
    """Params with height_exponent=0 are not changed by allometric scaling."""
    params = get_defaults("neutral")
    orig_slope = params["shoulder_slope_deg"]
    result = allometric_scale(params, new_height=2.00, locked=set())
    assert result["shoulder_slope_deg"] == pytest.approx(orig_slope)


def test_allometric_scale_stays_within_bounds() -> None:
    """Scaled values should stay within registry bounds."""
    params = get_defaults("neutral")
    result = allometric_scale(params, new_height=2.20, locked=set())
    for name, value in result.items():
        bounds = PARAM_REGISTRY[name]
        assert bounds.min_val <= value <= bounds.max_val, \
            f"{name}={value:.4f} out of [{bounds.min_val}, {bounds.max_val}]"


# ── weight_redistribute ───────────────────────────────────────────────────────

def test_weight_redistribute_heavier_increases_circumferences() -> None:
    """Adding weight increases circumferences."""
    params = get_defaults("neutral")
    original_chest = params["chest_circ_m"]
    result = weight_redistribute(params, new_weight=100.0, gender="neutral", locked=set())
    assert result["chest_circ_m"] > original_chest


def test_weight_redistribute_lighter_decreases_circumferences() -> None:
    """Removing weight decreases circumferences."""
    params = get_defaults("neutral")
    original_waist = params["waist_circ_m"]
    result = weight_redistribute(params, new_weight=50.0, gender="neutral", locked=set())
    assert result["waist_circ_m"] < original_waist


def test_weight_redistribute_same_weight_unchanged() -> None:
    """Redistributing the same weight leaves circumferences unchanged."""
    params = get_defaults("neutral")
    w = params["weight_kg"]
    result = weight_redistribute(params, new_weight=w, gender="neutral", locked=set())
    assert result["chest_circ_m"] == pytest.approx(params["chest_circ_m"], abs=1e-6)


def test_weight_redistribute_android_vs_gynoid() -> None:
    """Male (android) pattern should increase waist more than hip vs female (gynoid)."""
    base = get_defaults("neutral")
    male_result   = weight_redistribute(dict(base), new_weight=100.0, gender="male",   locked=set())
    female_result = weight_redistribute(dict(base), new_weight=100.0, gender="female", locked=set())
    # Android: waist gains more
    waist_delta_male   = male_result["waist_circ_m"]   - base["waist_circ_m"]
    waist_delta_female = female_result["waist_circ_m"] - base["waist_circ_m"]
    assert waist_delta_male > waist_delta_female
    # Gynoid: hip gains more
    hip_delta_male   = male_result["hip_circ_m"]   - base["hip_circ_m"]
    hip_delta_female = female_result["hip_circ_m"] - base["hip_circ_m"]
    assert hip_delta_female > hip_delta_male


def test_weight_redistribute_respects_lock() -> None:
    """Locked circumferences are not changed."""
    params = get_defaults("neutral")
    original_chest = params["chest_circ_m"]
    locked = {"chest_circ_m"}
    result = weight_redistribute(params, new_weight=100.0, gender="neutral", locked=locked)
    assert result["chest_circ_m"] == pytest.approx(original_chest)


def test_weight_redistribute_stays_within_bounds() -> None:
    """Redistributed values stay within registry bounds."""
    params = get_defaults("neutral")
    result = weight_redistribute(params, new_weight=150.0, gender="male", locked=set())
    for name, value in result.items():
        if name in PARAM_REGISTRY:
            bounds = PARAM_REGISTRY[name]
            assert bounds.min_val <= value <= bounds.max_val, \
                f"{name}={value:.4f} out of [{bounds.min_val}, {bounds.max_val}]"
