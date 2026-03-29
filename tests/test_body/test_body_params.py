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
    """to_dict() includes all expected keys."""
    d = BodyParameters().to_dict()
    assert set(d.keys()) == {"gender", "betas", "pose", "trans", "height_m", "weight_kg"}


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


def test_from_dict_validates_on_load() -> None:
    """from_dict() raises ValueError if data contains invalid values."""
    d = BodyParameters().to_dict()
    d["gender"] = "robot"
    with pytest.raises(ValueError, match="Invalid gender"):
        BodyParameters.from_dict(d)


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
