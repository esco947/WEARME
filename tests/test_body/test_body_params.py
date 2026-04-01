"""Tests for wearme.body.body_params."""

from __future__ import annotations

import json

import numpy as np
import pytest

from wearme.body.body_params import BETA_MAX, BETA_MIN, SMPL_POSE_DIMS, BodyParameters
from wearme.core.constants import (
    BODY_HEIGHT_DEFAULT_M,
    BODY_HEIGHT_MAX_M,
    BODY_HEIGHT_MIN_M,
    BODY_WEIGHT_DEFAULT_KG,
    BODY_WEIGHT_MAX_KG,
    BODY_WEIGHT_MIN_KG,
    SMPL_SHAPE_DIMS,
)

# ── Construction ──────────────────────────────────────────────────────────────


def test_default_construction() -> None:
    """BodyParameters can be created with no arguments."""
    b = BodyParameters()
    assert b.gender == "neutral"
    assert b.betas.shape == (SMPL_SHAPE_DIMS,)
    assert b.pose.shape == (SMPL_POSE_DIMS,)
    assert b.trans.shape == (3,)
    assert b.height_m == BODY_HEIGHT_DEFAULT_M
    assert b.weight_kg == BODY_WEIGHT_DEFAULT_KG


def test_default_arrays_are_zeros() -> None:
    """Default betas, pose, and trans are all zeros."""
    b = BodyParameters()
    np.testing.assert_array_equal(b.betas, np.zeros(SMPL_SHAPE_DIMS))
    np.testing.assert_array_equal(b.pose, np.zeros(SMPL_POSE_DIMS))
    np.testing.assert_array_equal(b.trans, np.zeros(3))


def test_custom_gender() -> None:
    """Gender field accepts all valid values."""
    for gender in ("neutral", "male", "female"):
        b = BodyParameters(gender=gender)
        b.validate()
        assert b.gender == gender


def test_custom_betas() -> None:
    """Custom betas array is stored correctly."""
    betas = np.ones(SMPL_SHAPE_DIMS) * 0.5
    b = BodyParameters(betas=betas)
    np.testing.assert_array_equal(b.betas, betas)


# ── Validation — success ──────────────────────────────────────────────────────


def test_validate_passes_defaults() -> None:
    """Default BodyParameters passes validation."""
    BodyParameters().validate()


def test_validate_passes_boundary_heights() -> None:
    """Validation accepts height at min and max boundaries."""
    BodyParameters(height_m=BODY_HEIGHT_MIN_M).validate()
    BodyParameters(height_m=BODY_HEIGHT_MAX_M).validate()


def test_validate_passes_boundary_weights() -> None:
    """Validation accepts weight at min and max boundaries."""
    BodyParameters(weight_kg=BODY_WEIGHT_MIN_KG).validate()
    BodyParameters(weight_kg=BODY_WEIGHT_MAX_KG).validate()


def test_validate_passes_boundary_betas() -> None:
    """Validation accepts betas at min and max values."""
    b = BodyParameters(betas=np.full(SMPL_SHAPE_DIMS, BETA_MIN))
    b.validate()
    b2 = BodyParameters(betas=np.full(SMPL_SHAPE_DIMS, BETA_MAX))
    b2.validate()


# ── Validation — failure ──────────────────────────────────────────────────────


def test_validate_rejects_invalid_gender() -> None:
    """Validation raises ValueError for an unknown gender string."""
    b = BodyParameters(gender="other")
    with pytest.raises(ValueError, match="Invalid gender"):
        b.validate()


def test_validate_rejects_height_too_low() -> None:
    """Validation raises ValueError when height is below minimum."""
    b = BodyParameters(height_m=BODY_HEIGHT_MIN_M - 0.01)
    with pytest.raises(ValueError, match="height_m"):
        b.validate()


def test_validate_rejects_height_too_high() -> None:
    """Validation raises ValueError when height exceeds maximum."""
    b = BodyParameters(height_m=BODY_HEIGHT_MAX_M + 0.01)
    with pytest.raises(ValueError, match="height_m"):
        b.validate()


def test_validate_rejects_weight_too_low() -> None:
    """Validation raises ValueError when weight is below minimum."""
    b = BodyParameters(weight_kg=BODY_WEIGHT_MIN_KG - 1.0)
    with pytest.raises(ValueError, match="weight_kg"):
        b.validate()


def test_validate_rejects_weight_too_high() -> None:
    """Validation raises ValueError when weight exceeds maximum."""
    b = BodyParameters(weight_kg=BODY_WEIGHT_MAX_KG + 1.0)
    with pytest.raises(ValueError, match="weight_kg"):
        b.validate()


def test_validate_rejects_betas_out_of_range() -> None:
    """Validation raises ValueError when any beta exceeds the allowed range."""
    betas = np.zeros(SMPL_SHAPE_DIMS)
    betas[3] = BETA_MAX + 0.1
    b = BodyParameters(betas=betas)
    with pytest.raises(ValueError, match="betas"):
        b.validate()


def test_validate_rejects_wrong_betas_shape() -> None:
    """Validation raises ValueError for a betas array with wrong shape."""
    b = BodyParameters(betas=np.zeros(5))
    with pytest.raises(ValueError, match="betas"):
        b.validate()


def test_validate_rejects_wrong_pose_shape() -> None:
    """Validation raises ValueError for a pose array with wrong shape."""
    b = BodyParameters(pose=np.zeros(10))
    with pytest.raises(ValueError, match="pose"):
        b.validate()


# ── Serialisation ─────────────────────────────────────────────────────────────


def test_to_dict_is_json_serialisable() -> None:
    """to_dict() produces a dict that can be serialised to JSON."""
    b = BodyParameters()
    d = b.to_dict()
    serialised = json.dumps(d)
    assert isinstance(serialised, str)


def test_to_dict_contains_required_keys() -> None:
    """to_dict() includes all expected keys (Phase 2 adds params and locked)."""
    d = BodyParameters().to_dict()
    required = {"gender", "betas", "pose", "trans", "height_m", "weight_kg", "params", "locked"}
    assert required.issubset(set(d.keys()))


def test_round_trip_preserves_values() -> None:
    """from_dict(to_dict(b)) returns a BodyParameters equal to b."""
    betas = np.linspace(-1.0, 1.0, SMPL_SHAPE_DIMS)
    original = BodyParameters(
        gender="female",
        betas=betas,
        height_m=1.65,
        weight_kg=58.0,
    )
    restored = BodyParameters.from_dict(original.to_dict())

    assert restored.gender == original.gender
    np.testing.assert_array_almost_equal(restored.betas, original.betas)
    np.testing.assert_array_almost_equal(restored.pose, original.pose)
    np.testing.assert_array_almost_equal(restored.trans, original.trans)
    assert restored.height_m == pytest.approx(original.height_m)
    assert restored.weight_kg == pytest.approx(original.weight_kg)


def test_from_dict_accepts_unknown_gender() -> None:
    """from_dict() does not raise for an unknown gender — validation is the caller's job."""
    d = BodyParameters().to_dict()
    d["gender"] = "robot"
    # Phase 2: from_dict doesn't call validate(); caller must invoke .validate() explicitly
    b = BodyParameters.from_dict(d)
    assert b.gender == "robot"


# ── Copy ─────────────────────────────────────────────────────────────────────


def test_copy_is_independent() -> None:
    """copy() returns an independent instance — mutating it does not affect original."""
    original = BodyParameters()
    copied = original.copy()
    copied.betas[0] = 2.0
    assert original.betas[0] == pytest.approx(0.0)


def test_copy_preserves_values() -> None:
    """copy() preserves all field values."""
    original = BodyParameters(gender="male", height_m=1.85, weight_kg=80.0)
    copied = original.copy()
    assert copied.gender == original.gender
    assert copied.height_m == pytest.approx(original.height_m)
    assert copied.weight_kg == pytest.approx(original.weight_kg)


# ── Phase 2: _params bootstrap ────────────────────────────────────────────────


def test_params_populated_after_construction() -> None:
    """_params dict is populated after construction with all registry keys."""
    from wearme.body.proportions import PARAM_REGISTRY
    b = BodyParameters()
    assert len(b._params) == len(PARAM_REGISTRY)


def test_params_height_matches_constructor() -> None:
    """_params['height_m'] matches the height_m constructor argument."""
    b = BodyParameters(height_m=1.80)
    assert b._params["height_m"] == pytest.approx(1.80)


def test_params_weight_matches_constructor() -> None:
    """_params['weight_kg'] matches the weight_kg constructor argument."""
    b = BodyParameters(weight_kg=85.0)
    assert b._params["weight_kg"] == pytest.approx(85.0)


def test_params_bmi_is_derived() -> None:
    """_params['bmi'] is computed as weight / height^2."""
    b = BodyParameters(height_m=1.75, weight_kg=70.0)
    expected_bmi = 70.0 / (1.75 ** 2)
    assert b._params["bmi"] == pytest.approx(expected_bmi, rel=1e-4)


def test_params_gender_defaults_differ() -> None:
    """Male and female defaults produce different _params for sexually dimorphic params."""
    male   = BodyParameters(gender="male")
    female = BodyParameters(gender="female")
    # height_m is overridden by the constructor arg (default 1.75 for both);
    # check a sexually dimorphic param not overridden by the constructor.
    assert male._params["shoulder_width_m"] > female._params["shoulder_width_m"]


# ── Phase 2: set_param ────────────────────────────────────────────────────────


def test_set_param_updates_value() -> None:
    """set_param updates the value in _params."""
    b = BodyParameters()
    b.set_param("chest_circ_m", 1.00, propagate=False)
    assert b._params["chest_circ_m"] == pytest.approx(1.00)


def test_set_param_height_with_propagation_updates_lengths() -> None:
    """set_param('height_m', …, propagate=True) rescales limb lengths."""
    b = BodyParameters(height_m=1.75)
    original_inseam = b._params["inseam_m"]
    b.set_param("height_m", 1.90, propagate=True)
    assert b._params["inseam_m"] > original_inseam
    assert b.height_m == pytest.approx(1.90)


def test_set_param_height_no_propagation() -> None:
    """set_param('height_m', …, propagate=False) only updates height."""
    b = BodyParameters(height_m=1.75)
    original_inseam = b._params["inseam_m"]
    b.set_param("height_m", 1.90, propagate=False)
    assert b._params["inseam_m"] == pytest.approx(original_inseam)
    assert b.height_m == pytest.approx(1.90)


def test_set_param_weight_with_propagation_updates_circumferences() -> None:
    """set_param('weight_kg', …, propagate=True) redistributes circumferences."""
    b = BodyParameters(weight_kg=70.0)
    original_chest = b._params["chest_circ_m"]
    b.set_param("weight_kg", 100.0, propagate=True)
    assert b._params["chest_circ_m"] > original_chest
    assert b.weight_kg == pytest.approx(100.0)


def test_set_param_rejects_out_of_bounds() -> None:
    """set_param raises ValueError for an out-of-bounds value."""
    b = BodyParameters()
    with pytest.raises(ValueError):
        b.set_param("height_m", 0.5)  # below 1.40


def test_set_param_rejects_read_only() -> None:
    """set_param raises ValueError for a read-only param (bmi)."""
    b = BodyParameters()
    with pytest.raises((ValueError, KeyError)):
        b.set_param("bmi", 30.0)


def test_set_param_rejects_unknown_name() -> None:
    """set_param raises an error for an unknown param name."""
    b = BodyParameters()
    with pytest.raises((KeyError, ValueError)):
        b.set_param("nonexistent", 1.0)


# ── Phase 2: lock / unlock ────────────────────────────────────────────────────


def test_lock_prevents_propagation() -> None:
    """A locked param is not changed by allometric scaling."""
    b = BodyParameters(height_m=1.75)
    original_inseam = b._params["inseam_m"]
    b.lock("inseam_m")
    b.set_param("height_m", 1.90, propagate=True)
    assert b._params["inseam_m"] == pytest.approx(original_inseam)


def test_unlock_allows_propagation() -> None:
    """After unlock, allometric scaling affects the previously locked param."""
    b = BodyParameters(height_m=1.75)
    b.lock("inseam_m")
    b.unlock("inseam_m")
    original_inseam = b._params["inseam_m"]
    b.set_param("height_m", 1.90, propagate=True)
    assert b._params["inseam_m"] > original_inseam


def test_is_locked_returns_correct_state() -> None:
    """is_locked reflects current lock state."""
    b = BodyParameters()
    assert b.is_locked("chest_circ_m") is False
    b.lock("chest_circ_m")
    assert b.is_locked("chest_circ_m") is True
    b.unlock("chest_circ_m")
    assert b.is_locked("chest_circ_m") is False


def test_locked_param_silently_skipped_by_set_param() -> None:
    """Calling set_param on a locked param does not raise — it silently skips."""
    b = BodyParameters()
    b.lock("chest_circ_m")
    original = b._params["chest_circ_m"]
    b.set_param("chest_circ_m", original + 0.05, propagate=False)
    assert b._params["chest_circ_m"] == pytest.approx(original)


# ── Phase 2: to_dict / from_dict (new format) ─────────────────────────────────


def test_to_dict_new_format_contains_params_key() -> None:
    """Phase 2 to_dict() includes a 'params' key with all 55+ values."""
    b = BodyParameters()
    d = b.to_dict()
    assert "params" in d
    assert isinstance(d["params"], dict)
    assert len(d["params"]) > 50


def test_to_dict_new_format_contains_locked_key() -> None:
    """Phase 2 to_dict() includes a 'locked' key."""
    b = BodyParameters()
    b.lock("inseam_m")
    d = b.to_dict()
    assert "locked" in d
    assert "inseam_m" in d["locked"]


def test_from_dict_new_format_restores_params() -> None:
    """from_dict with a 'params' key restores _params correctly."""
    b = BodyParameters()
    b.set_param("chest_circ_m", 1.05, propagate=False)
    b.lock("dart_width_m")
    d = b.to_dict()
    b2 = BodyParameters.from_dict(d)
    assert b2._params["chest_circ_m"] == pytest.approx(1.05)


def test_from_dict_new_format_restores_locked() -> None:
    """from_dict with a 'locked' key restores the locked set."""
    b = BodyParameters()
    b.lock("shoulder_width_m")
    b2 = BodyParameters.from_dict(b.to_dict())
    assert b2.is_locked("shoulder_width_m")


def test_from_dict_legacy_format_works() -> None:
    """from_dict with no 'params' key (legacy format) still produces valid object."""
    legacy_dict = {
        "gender":    "male",
        "betas":     [0.0] * SMPL_SHAPE_DIMS,
        "height_m":  1.80,
        "weight_kg": 80.0,
    }
    b = BodyParameters.from_dict(legacy_dict)
    assert b.gender == "male"
    assert b.height_m == pytest.approx(1.80)
    assert b.weight_kg == pytest.approx(80.0)


# ── Phase 2: copy preserves Phase 2 state ─────────────────────────────────────


def test_copy_preserves_params() -> None:
    """copy() deep-copies _params so mutations don't affect the original."""
    b = BodyParameters()
    b.set_param("chest_circ_m", 1.05, propagate=False)
    c = b.copy()
    c._params["chest_circ_m"] = 0.90
    assert b._params["chest_circ_m"] == pytest.approx(1.05)


def test_copy_preserves_locked() -> None:
    """copy() preserves the locked set independently."""
    b = BodyParameters()
    b.lock("inseam_m")
    c = b.copy()
    c.unlock("inseam_m")
    assert b.is_locked("inseam_m")


# ── Phase 2: bmi property ─────────────────────────────────────────────────────


def test_bmi_property_computed_correctly() -> None:
    """bmi property returns weight / height^2."""
    b = BodyParameters(height_m=1.75, weight_kg=70.0)
    assert b.bmi == pytest.approx(70.0 / (1.75 ** 2), rel=1e-4)


def test_bmi_updates_after_set_param_weight() -> None:
    """bmi is updated after calling set_param('weight_kg', …)."""
    b = BodyParameters(height_m=1.75, weight_kg=70.0)
    b.set_param("weight_kg", 90.0, propagate=False)
    assert b.bmi == pytest.approx(90.0 / (1.75 ** 2), rel=1e-3)
