"""Population-based proportions registry for WEARME body system.

Defines PARAM_REGISTRY with ANSUR II / CAESAR-calibrated bounds and
sex-aware defaults for all 55 anatomical parameters. Provides scaling
functions for allometric height propagation and weight redistribution.

Usage::

    from wearme.body.proportions import (
        PARAM_REGISTRY, get_defaults, allometric_scale, weight_redistribute,
    )

    defaults = get_defaults("female")
    allometric_scale(defaults, new_height=1.70, locked=set())
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Parameter bounds registry ─────────────────────────────────────────────────

@dataclass(frozen=True)
class ParamBounds:
    """Bounds and population defaults for one anatomical parameter.

    Attributes:
        min_val: Minimum physiologically plausible value.
        max_val: Maximum physiologically plausible value.
        default_male: Population mean for male bodies (ANSUR II / CAESAR).
        default_female: Population mean for female bodies.
        default_neutral: Mean across sexes (used when gender="neutral").
        height_exponent: Allometric scaling exponent relative to height.
            0.0 = not height-scaled;
            1.0 = scales linearly with height (lengths, heights);
            0.50 = scales with sqrt(height) (widths);
            0.33 = scales with cube-root of height (circumferences,
                   proportional to cross-sectional area).
        read_only: If True the parameter is always derived and must not
            be set directly (e.g. ``bmi``).
    """
    min_val: float
    max_val: float
    default_male: float
    default_female: float
    default_neutral: float
    height_exponent: float
    read_only: bool = False


#: Complete registry of all 55 anatomical parameters + 1 derived param (bmi).
#: Bounds are calibrated from ANSUR II (US Army, 2012) and CAESAR (2002).
PARAM_REGISTRY: dict[str, ParamBounds] = {
    # ── Group 1: Global (2) ──────────────────────────────────────────────────
    "height_m":           ParamBounds(1.40, 2.20, 1.765, 1.626, 1.695, 0.00),
    "weight_kg":          ParamBounds(40.0, 200.0, 80.0, 65.0, 72.5,  0.00),
    # ── Group 2: Trunk circumferences (8) ───────────────────────────────────
    "chest_circ_m":       ParamBounds(0.70, 1.50, 0.980, 0.910, 0.945, 0.33),
    "underbust_circ_m":   ParamBounds(0.60, 1.30, 0.895, 0.820, 0.858, 0.33),
    "waist_circ_m":       ParamBounds(0.55, 1.40, 0.840, 0.730, 0.785, 0.33),
    "abdomen_circ_m":     ParamBounds(0.60, 1.50, 0.900, 0.810, 0.855, 0.33),
    "hip_circ_m":         ParamBounds(0.75, 1.50, 0.960, 1.000, 0.980, 0.33),
    "mid_hip_circ_m":     ParamBounds(0.70, 1.40, 0.920, 0.930, 0.925, 0.33),
    "neck_circ_m":        ParamBounds(0.28, 0.55, 0.380, 0.335, 0.358, 0.33),
    "shoulder_circ_m":    ParamBounds(0.90, 1.40, 1.130, 1.030, 1.080, 0.33),
    # ── Group 3: Trunk widths and depths (8) ────────────────────────────────
    "shoulder_width_m":   ParamBounds(0.30, 0.60, 0.415, 0.370, 0.393, 0.50),
    "chest_width_m":      ParamBounds(0.25, 0.50, 0.330, 0.300, 0.315, 0.50),
    "chest_depth_m":      ParamBounds(0.14, 0.40, 0.225, 0.205, 0.215, 0.33),
    "waist_width_m":      ParamBounds(0.20, 0.50, 0.290, 0.260, 0.275, 0.33),
    "waist_depth_m":      ParamBounds(0.14, 0.40, 0.215, 0.190, 0.203, 0.33),
    "hip_width_m":        ParamBounds(0.28, 0.55, 0.340, 0.350, 0.345, 0.50),
    "hip_depth_m":        ParamBounds(0.18, 0.42, 0.240, 0.245, 0.243, 0.33),
    "back_width_m":       ParamBounds(0.25, 0.50, 0.360, 0.320, 0.340, 0.50),
    # ── Group 4: Height landmarks (9) ───────────────────────────────────────
    "shoulder_height_m":  ParamBounds(1.10, 1.85, 1.450, 1.330, 1.390, 1.00),
    "bust_height_m":      ParamBounds(0.90, 1.50, 1.190, 1.095, 1.143, 1.00),
    "waist_height_m":     ParamBounds(0.85, 1.45, 1.080, 0.995, 1.038, 1.00),
    "hip_height_m":       ParamBounds(0.70, 1.20, 0.900, 0.830, 0.865, 1.00),
    "crotch_height_m":    ParamBounds(0.60, 1.05, 0.815, 0.745, 0.780, 1.00),
    "knee_height_m":      ParamBounds(0.40, 0.65, 0.490, 0.450, 0.470, 1.00),
    "ankle_height_m":     ParamBounds(0.04, 0.12, 0.075, 0.068, 0.072, 1.00),
    "neck_height_m":      ParamBounds(1.25, 2.00, 1.570, 1.440, 1.505, 1.00),
    "head_height_m":      ParamBounds(0.18, 0.28, 0.232, 0.221, 0.227, 0.50),
    # ── Group 5: Upper limbs (10) ────────────────────────────────────────────
    "arm_length_m":       ParamBounds(0.50, 0.90, 0.620, 0.570, 0.595, 1.00),
    "upper_arm_length_m": ParamBounds(0.28, 0.50, 0.360, 0.330, 0.345, 1.00),
    "forearm_length_m":   ParamBounds(0.20, 0.38, 0.270, 0.245, 0.258, 1.00),
    "upper_arm_circ_m":   ParamBounds(0.20, 0.55, 0.335, 0.305, 0.320, 0.33),
    "elbow_circ_m":       ParamBounds(0.20, 0.40, 0.275, 0.250, 0.263, 0.33),
    "forearm_circ_m":     ParamBounds(0.18, 0.40, 0.285, 0.255, 0.270, 0.33),
    "wrist_circ_m":       ParamBounds(0.13, 0.25, 0.170, 0.153, 0.162, 0.33),
    "hand_length_m":      ParamBounds(0.15, 0.25, 0.194, 0.175, 0.185, 0.50),
    "hand_width_m":       ParamBounds(0.06, 0.12, 0.086, 0.077, 0.082, 0.33),
    "shoulder_slope_deg": ParamBounds(10.0, 35.0, 21.0, 23.0, 22.0, 0.00),
    # ── Group 6: Lower limbs (10) ────────────────────────────────────────────
    "inseam_m":           ParamBounds(0.60, 1.00, 0.810, 0.745, 0.778, 1.00),
    "outseam_m":          ParamBounds(0.85, 1.20, 1.050, 0.975, 1.013, 1.00),
    "thigh_circ_m":       ParamBounds(0.40, 0.85, 0.565, 0.580, 0.573, 0.33),
    "mid_thigh_circ_m":   ParamBounds(0.30, 0.75, 0.490, 0.505, 0.498, 0.33),
    "knee_circ_m":        ParamBounds(0.28, 0.55, 0.380, 0.370, 0.375, 0.33),
    "calf_circ_m":        ParamBounds(0.28, 0.58, 0.375, 0.370, 0.373, 0.33),
    "ankle_circ_m":       ParamBounds(0.18, 0.35, 0.235, 0.220, 0.228, 0.33),
    "foot_length_m":      ParamBounds(0.20, 0.34, 0.268, 0.243, 0.256, 0.50),
    "foot_width_m":       ParamBounds(0.07, 0.14, 0.097, 0.089, 0.093, 0.33),
    "crotch_depth_m":     ParamBounds(0.20, 0.40, 0.275, 0.260, 0.268, 0.33),
    # ── Group 7: Garment surface (8 + 1 derived) ────────────────────────────
    "front_length_m":     ParamBounds(0.30, 0.55, 0.420, 0.395, 0.408, 1.00),
    "back_length_m":      ParamBounds(0.33, 0.58, 0.450, 0.415, 0.433, 1.00),
    "nape_to_waist_m":    ParamBounds(0.33, 0.58, 0.430, 0.400, 0.415, 1.00),
    "side_length_m":      ParamBounds(0.15, 0.35, 0.210, 0.200, 0.205, 1.00),
    "bust_span_m":        ParamBounds(0.10, 0.30, 0.170, 0.175, 0.173, 0.33),
    "dart_width_m":       ParamBounds(0.00, 0.12, 0.010, 0.040, 0.025, 0.33),
    "rise_front_m":       ParamBounds(0.20, 0.40, 0.290, 0.270, 0.280, 0.33),
    "rise_back_m":        ParamBounds(0.25, 0.50, 0.360, 0.340, 0.350, 0.33),
    # Derived — always recomputed, never set directly
    "bmi":                ParamBounds(13.0, 60.0, 25.6, 24.7, 25.1, 0.00, True),
}

_GENDER_KEY: dict[str, str] = {
    "male":    "default_male",
    "female":  "default_female",
    "neutral": "default_neutral",
}


# ── Params that scale with weight (circumferences, widths, depths) ────────────

_WEIGHT_SCALING_PARAMS: frozenset[str] = frozenset({
    "chest_circ_m", "underbust_circ_m", "waist_circ_m", "abdomen_circ_m",
    "hip_circ_m", "mid_hip_circ_m", "neck_circ_m", "shoulder_circ_m",
    "shoulder_width_m", "chest_width_m", "chest_depth_m",
    "waist_width_m", "waist_depth_m",
    "hip_width_m", "hip_depth_m", "back_width_m",
    "upper_arm_circ_m", "elbow_circ_m", "forearm_circ_m", "wrist_circ_m",
    "thigh_circ_m", "mid_thigh_circ_m", "knee_circ_m", "calf_circ_m", "ankle_circ_m",
    "crotch_depth_m", "bust_span_m", "dart_width_m",
})

# Sex-specific multipliers for weight redistribution.
# 1.0 = scales at the base cube-root rate.
# > 1.0 = this region carries disproportionately more of the weight change.
# < 1.0 = this region changes less than average.

_ANDROID_MULTIPLIERS: dict[str, float] = {   # male / android fat-gain pattern
    "waist_circ_m":     1.50,
    "abdomen_circ_m":   1.60,
    "waist_width_m":    1.40,
    "waist_depth_m":    1.40,
    "chest_circ_m":     1.20,
    "chest_depth_m":    1.20,
    "underbust_circ_m": 1.10,
    "hip_circ_m":       0.70,
    "thigh_circ_m":     0.60,
    "mid_thigh_circ_m": 0.60,
    "hip_width_m":      0.70,
    "hip_depth_m":      0.80,
}

_GYNOID_MULTIPLIERS: dict[str, float] = {    # female / gynoid fat-gain pattern
    "hip_circ_m":       1.50,
    "thigh_circ_m":     1.50,
    "mid_hip_circ_m":   1.40,
    "hip_width_m":      1.30,
    "hip_depth_m":      1.30,
    "calf_circ_m":      1.20,
    "mid_thigh_circ_m": 1.30,
    "waist_circ_m":     0.80,
    "abdomen_circ_m":   0.90,
    "chest_circ_m":     1.10,
    "dart_width_m":     1.20,
    "bust_span_m":      1.10,
}


# ── Public functions ──────────────────────────────────────────────────────────

def get_defaults(gender: str) -> dict[str, float]:
    """Return default param values for *gender*.

    Args:
        gender: One of ``"neutral"``, ``"male"``, ``"female"``.
            Unknown values fall back to ``"neutral"``.

    Returns:
        Dict mapping every param name (including ``"bmi"``) to its default.
    """
    key = _GENDER_KEY.get(gender, "default_neutral")
    return {name: float(getattr(b, key)) for name, b in PARAM_REGISTRY.items()}


def validate_param(name: str, value: float) -> None:
    """Raise if *value* is invalid for *name*.

    Args:
        name: Parameter name.
        value: Proposed value.

    Raises:
        KeyError: Unknown parameter name.
        ValueError: Value out of bounds, or parameter is read-only.
    """
    bounds = PARAM_REGISTRY[name]   # KeyError if unknown
    if bounds.read_only:
        raise ValueError(f"Parameter {name!r} is read-only (derived).")
    if not (bounds.min_val <= value <= bounds.max_val):
        raise ValueError(
            f"Parameter {name!r} = {value} is outside "
            f"[{bounds.min_val}, {bounds.max_val}]."
        )


def allometric_scale(
    params: dict[str, float],
    new_height: float,
    locked: set[str],
) -> dict[str, float]:
    """Re-scale height-dependent params after a height change.

    All params with ``height_exponent > 0`` are rescaled as::

        new_value = old_value * (new_height / old_height) ** exponent

    Params in *locked* are not modified.  ``"height_m"`` itself is always
    updated to *new_height*.

    Args:
        params: Param dict to mutate in-place and return.
        new_height: Target height in metres.
        locked: Names of params that must not be changed.

    Returns:
        The same *params* dict (mutated).
    """
    old_height = params.get("height_m", 1.695)
    if old_height <= 0.0:
        params["height_m"] = new_height
        return params
    if new_height == old_height:
        return params

    ratio = new_height / old_height
    for name, bounds in PARAM_REGISTRY.items():
        if bounds.height_exponent == 0.0 or bounds.read_only:
            continue
        if name == "height_m" or name in locked:
            continue
        old_val = params.get(name, bounds.default_neutral)
        new_val = old_val * (ratio ** bounds.height_exponent)
        params[name] = max(bounds.min_val, min(bounds.max_val, new_val))

    params["height_m"] = new_height
    weight = params.get("weight_kg", 72.5)
    if new_height > 0:
        params["bmi"] = weight / (new_height ** 2)
    return params


def weight_redistribute(
    params: dict[str, float],
    new_weight: float,
    gender: str,
    locked: set[str],
) -> dict[str, float]:
    """Re-scale circumferences and widths after a weight change.

    Base scaling uses the cube-root relationship (volume ∝ weight, so
    linear dimensions ∝ weight^⅓).  Sex-specific multipliers then skew
    the distribution towards android (waist/abdomen for males) or gynoid
    (hips/thighs for females) patterns.

    Args:
        params: Param dict to mutate in-place and return.
        new_weight: Target weight in kg.
        gender: ``"male"``, ``"female"``, or ``"neutral"``.
        locked: Names of params that must not be changed.

    Returns:
        The same *params* dict (mutated).
    """
    old_weight = params.get("weight_kg", 72.5)
    if old_weight <= 0.0:
        params["weight_kg"] = new_weight
        return params
    if new_weight == old_weight:
        return params

    base_scale = (new_weight / old_weight) ** (1.0 / 3.0)

    multipliers: dict[str, float]
    if gender == "male":
        multipliers = _ANDROID_MULTIPLIERS
    elif gender == "female":
        multipliers = _GYNOID_MULTIPLIERS
    else:
        multipliers = {}

    for name in _WEIGHT_SCALING_PARAMS:
        if name in locked or name not in params:
            continue
        bounds = PARAM_REGISTRY[name]
        m = multipliers.get(name, 1.0)
        # Effective scale: start from 1.0, amplify the change by multiplier
        scale = 1.0 + (base_scale - 1.0) * m
        old_val = params[name]
        params[name] = max(bounds.min_val, min(bounds.max_val, old_val * scale))

    params["weight_kg"] = new_weight
    height = params.get("height_m", 1.695)
    if height > 0:
        params["bmi"] = new_weight / (height ** 2)
    return params
