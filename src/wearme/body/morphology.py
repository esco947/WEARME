"""Body morphology analysis — silhouette, somatotype, fat distribution.

Provides analytical functions that characterise the shape and composition
of a body described by ``BodyParameters._params``.  No SMPL model is
required — all computations are purely algebraic.

Silhouette classification uses industry-standard ratio thresholds.
Somatotype uses a simplified Heath-Carter method.
Fat distribution uses WHR-driven android/gynoid blending.

Usage::

    from wearme.body.morphology import build_morphology_profile
    from wearme.body.body_params import BodyParameters

    params = BodyParameters(gender="female", height_m=1.65, weight_kg=60.0)
    profile = build_morphology_profile(params)
    print(profile.silhouette, profile.somatotype.ectomorphy)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wearme.body.body_params import BodyParameters


# ── Data structures ───────────────────────────────────────────────────────────

class SilhouetteType(str, Enum):
    """Standard garment-industry body silhouette classification."""
    HOURGLASS          = "hourglass"           # chest ≈ hips, narrow waist
    PEAR               = "pear"                # hips notably wider than chest
    APPLE              = "apple"               # waist-dominant, abdomen-forward
    RECTANGLE          = "rectangle"           # chest ≈ waist ≈ hips
    INVERTED_TRIANGLE  = "inverted_triangle"   # chest notably wider than hips


@dataclass(frozen=True)
class SomatotypeRatings:
    """Heath-Carter somatotype ratings, each on a 1–7 scale.

    Attributes:
        endomorphy: Fatness / roundness component (1=lean, 7=very fat).
        mesomorphy: Musculo-skeletal robustness (1=slight, 7=very muscular).
        ectomorphy:  Linearity / slenderness (1=stocky, 7=very linear).
    """
    endomorphy: float
    mesomorphy: float
    ectomorphy: float


@dataclass(frozen=True)
class MorphologyProfile:
    """Complete morphology snapshot for one body.

    Attributes:
        silhouette:      Body outline type.
        somatotype:      Heath-Carter component ratings.
        whr:             Waist-to-hip ratio (waist_circ / hip_circ).
        whr_blend:       0.0 = fully gynoid; 1.0 = fully android fat pattern.
        fat_distribution: Descriptive label ``"android"`` | ``"gynoid"`` | ``"mixed"``.
    """
    silhouette:       SilhouetteType
    somatotype:       SomatotypeRatings
    whr:              float
    whr_blend:        float
    fat_distribution: str


# ── Internal helpers ──────────────────────────────────────────────────────────

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ── Public functions ──────────────────────────────────────────────────────────

def classify_silhouette(params: BodyParameters) -> SilhouetteType:
    """Classify body silhouette from chest / waist / hip circumferences.

    Uses industry-standard thresholds (all in metres):

    * **Hourglass**:  |chest − hips| < 0.05 m  AND
                      (chest + hips)/2 − waist > 0.09 m
    * **Pear**:       hips − chest > 0.05 m
    * **Inverted triangle**: chest − hips > 0.05 m
    * **Apple**:      waist ≥ chest × 0.85  AND  waist ≥ hips × 0.85
    * **Rectangle**:  everything else

    Args:
        params: Body parameters with ``_params`` populated.

    Returns:
        :class:`SilhouetteType` value.
    """
    p = params._params
    chest = p.get("chest_circ_m", 0.945)
    waist = p.get("waist_circ_m", 0.785)
    hips  = p.get("hip_circ_m",   0.980)

    chest_hip_diff = chest - hips
    avg_bust_hip   = (chest + hips) / 2.0

    if abs(chest_hip_diff) < 0.05 and avg_bust_hip - waist > 0.09:
        return SilhouetteType.HOURGLASS
    if hips - chest > 0.05:
        return SilhouetteType.PEAR
    if chest_hip_diff > 0.05:
        return SilhouetteType.INVERTED_TRIANGLE
    if waist >= chest * 0.85 and waist >= hips * 0.85:
        return SilhouetteType.APPLE
    return SilhouetteType.RECTANGLE


def compute_somatotype(params: BodyParameters) -> SomatotypeRatings:
    """Compute a simplified Heath-Carter somatotype rating.

    * **Ectomorphy**: Height-weight ratio (HWR = height_m / weight_kg^⅓).
      HWR ≥ 40.75 → ecto = 0.732 × HWR − 28.58; clipped to [1, 7].
    * **Endomorphy**: Derived from BMI deviation from population mean (25).
      bmi_dev = (BMI − 25) / 10; endo = 1 + 3 × clamp(bmi_dev, 0, 2).
    * **Mesomorphy**: Based on shoulder width relative to height.
      shoulder_ratio = shoulder_width / height; meso reflects musculo-skeletal
      breadth — higher for wider shoulders.

    All ratings are clipped to [1, 7].

    Args:
        params: Body parameters.

    Returns:
        :class:`SomatotypeRatings`.
    """
    p           = params._params
    height_m    = p.get("height_m",  1.695)
    weight_kg   = p.get("weight_kg", 72.5)
    bmi         = p.get("bmi",       25.0)
    shl_width   = p.get("shoulder_width_m", 0.393)

    # Ectomorphy — slenderness via HWR
    hwr = height_m / max(weight_kg, 0.1) ** (1.0 / 3.0)
    if hwr >= 40.75:
        ecto = 0.732 * hwr - 28.58
    elif hwr >= 38.25:
        ecto = 0.463 * hwr - 17.63
    else:
        ecto = 1.0
    ecto = _clamp(ecto, 1.0, 7.0)

    # Endomorphy — fatness
    bmi_dev = (bmi - 25.0) / 10.0
    endo = 1.0 + 3.0 * _clamp(bmi_dev, 0.0, 2.0)
    if bmi_dev < 0:
        endo = max(1.0, 1.0 + 3.0 * bmi_dev)
    endo = _clamp(endo, 1.0, 7.0)

    # Mesomorphy — shoulder breadth relative to height
    shoulder_ratio = shl_width / max(height_m, 0.1)
    # Population reference: shoulder_ratio ≈ 0.232 for neutral body
    ref_ratio = 0.232
    meso = 4.0 + (shoulder_ratio - ref_ratio) / ref_ratio * 8.0
    meso = _clamp(meso, 1.0, 7.0)

    return SomatotypeRatings(
        endomorphy=round(endo, 2),
        mesomorphy=round(meso, 2),
        ectomorphy=round(ecto, 2),
    )


def compute_whr_blend(params: BodyParameters) -> float:
    """Return android/gynoid blend factor from waist-to-hip ratio.

    * WHR ≤ 0.75 → blend = 0.0 (fully gynoid / female fat pattern)
    * WHR ≥ 0.95 → blend = 1.0 (fully android / male fat pattern)
    * Linear interpolation between those limits.

    Args:
        params: Body parameters.

    Returns:
        Blend factor in [0.0, 1.0].
    """
    p     = params._params
    waist = p.get("waist_circ_m", 0.785)
    hips  = p.get("hip_circ_m",   0.980)
    whr   = waist / max(hips, 0.01)
    return _clamp((whr - 0.75) / 0.20, 0.0, 1.0)


def build_morphology_profile(params: BodyParameters) -> MorphologyProfile:
    """Build a complete morphology profile for *params*.

    Combines silhouette classification, somatotype rating, and WHR-based
    fat distribution label.

    Args:
        params: Body parameters.

    Returns:
        :class:`MorphologyProfile`.
    """
    silhouette = classify_silhouette(params)
    somatotype = compute_somatotype(params)
    whr_blend  = compute_whr_blend(params)

    p   = params._params
    whr = p.get("waist_circ_m", 0.785) / max(p.get("hip_circ_m", 0.980), 0.01)

    if whr_blend >= 0.7:
        fat_dist = "android"
    elif whr_blend <= 0.3:
        fat_dist = "gynoid"
    else:
        fat_dist = "mixed"

    return MorphologyProfile(
        silhouette=silhouette,
        somatotype=somatotype,
        whr=round(whr, 3),
        whr_blend=round(whr_blend, 3),
        fat_distribution=fat_dist,
    )


def adjust_fat_distribution(
    params: BodyParameters,
    delta_weight_kg: float,
) -> dict[str, float]:
    """Compute circumference deltas for a weight change.

    Uses the WHR blend from *params* to determine whether added/removed
    weight follows android (waist-first) or gynoid (hip-first) distribution.

    Args:
        params:           Current body parameters.
        delta_weight_kg:  Weight change in kg (positive = gain, negative = loss).

    Returns:
        Dict mapping param names to the recommended delta in metres.
        The caller is responsible for applying these deltas via
        ``params.set_param`` if desired.
    """
    if abs(delta_weight_kg) < 0.01:
        return {}

    whr_blend = compute_whr_blend(params)
    p         = params._params

    # Rough empirical rates: how much does each circumference change per kg?
    # Values calibrated so +10 kg ≈ +2–4 cm change in major circumferences.
    _ANDROID_RATES: dict[str, float] = {
        "waist_circ_m":     0.003,
        "abdomen_circ_m":   0.004,
        "chest_circ_m":     0.002,
        "chest_depth_m":    0.001,
        "hip_circ_m":       0.001,
    }
    _GYNOID_RATES: dict[str, float] = {
        "hip_circ_m":       0.003,
        "thigh_circ_m":     0.003,
        "mid_hip_circ_m":   0.002,
        "waist_circ_m":     0.001,
        "chest_circ_m":     0.001,
    }

    result: dict[str, float] = {}
    all_names = set(_ANDROID_RATES) | set(_GYNOID_RATES)
    for name in all_names:
        android_rate = _ANDROID_RATES.get(name, 0.0)
        gynoid_rate  = _GYNOID_RATES.get(name, 0.0)
        blended_rate = android_rate * whr_blend + gynoid_rate * (1.0 - whr_blend)
        delta        = blended_rate * delta_weight_kg
        if abs(delta) > 1e-5:
            result[name] = round(delta, 5)
    return result
