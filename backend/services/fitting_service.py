"""Fitting service — size recommendation from avatar measurements."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models import Avatar, Garment

# Chest circumference (cm) → size for tops/dresses/hoodies
_CHEST_SIZES = [
    (88,  "XS"),
    (92,  "S"),
    (96,  "M"),
    (100, "L"),
    (104, "XL"),
    (float("inf"), "XXL"),
]

# Waist circumference (cm) → size for pants (European numeric)
_WAIST_PANTS = [
    (72,  "36"),
    (76,  "38"),
    (80,  "40"),
    (84,  "42"),
    (88,  "44"),
    (92,  "46"),
    (float("inf"), "48"),
]


def _recommend_size(category: str, chest_cm: float, waist_cm: float, hips_cm: float) -> str:
    if category == "pants":
        for limit, size in _WAIST_PANTS:
            if waist_cm <= limit:
                return size
        return "48"

    # Default: use chest
    measure = chest_cm
    if category == "dress":
        measure = max(chest_cm, hips_cm)

    for limit, size in _CHEST_SIZES:
        if measure <= limit:
            return size
    return "XXL"


def compute_fitting(avatar: Avatar, garment: Garment) -> dict:
    """Return size recommendation and fit score for avatar + garment.

    Returns measurements in cm and recommended size.
    Falls back gracefully if SMPL model unavailable.
    """
    from backend.services import avatar_service  # noqa: PLC0415

    try:
        meas = avatar_service.get_measurements(avatar)
        chest_cm  = meas["chest_m"]  * 100
        waist_cm  = meas["waist_m"]  * 100
        hips_cm   = meas["hips_m"]   * 100
        height_cm = meas["height_m"] * 100
        smpl_ok = True
    except Exception:  # noqa: BLE001
        # SMPL model not available — use stored height/weight as approximation
        chest_cm  = 86.0 + (avatar.weight_kg - 60) * 0.3
        waist_cm  = 72.0 + (avatar.weight_kg - 60) * 0.25
        hips_cm   = 90.0 + (avatar.weight_kg - 60) * 0.3
        height_cm = avatar.height_m * 100
        smpl_ok = False

    import json  # noqa: PLC0415
    available = json.loads(garment.sizes)
    recommended = _recommend_size(garment.category, chest_cm, waist_cm, hips_cm)

    # Clamp to available sizes
    if recommended not in available and available:
        recommended = available[len(available) // 2]

    return {
        "garment_id":       garment.id,
        "garment_name":     garment.name,
        "garment_category": garment.category,
        "recommended_size": recommended,
        "available_sizes":  available,
        "measurements": {
            "height_cm": round(height_cm, 1),
            "chest_cm":  round(chest_cm,  1),
            "waist_cm":  round(waist_cm,  1),
            "hips_cm":   round(hips_cm,   1),
        },
        "smpl_available": smpl_ok,
    }
