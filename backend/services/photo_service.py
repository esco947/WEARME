"""Photo-based avatar estimation service.

Uses Pillow + numpy (Python 3.14 compatible — no MediaPipe/cv2 required).
Detects body silhouette from front photo, estimates proportions,
maps to SMPL betas via the same semantic mapping as the frontend.
"""

from __future__ import annotations

import io
import logging

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Neutral SMPL reference ratios (widths relative to detected body height px)
# Measured empirically on the neutral .pkl at default betas (all zeros).
# ---------------------------------------------------------------------------

_NEUTRAL = {
    "shoulder": 0.202,
    "chest":    0.205,
    "waist":    0.167,
    "hip":      0.222,
}

# Fractions from *top of detected body* at which we sample width
_FRACTIONS = {
    "shoulder": 0.15,
    "chest":    0.28,
    "waist":    0.38,
    "hip":      0.50,
}


# ---------------------------------------------------------------------------
# Silhouette extraction
# ---------------------------------------------------------------------------


def _extract_widths(image_bytes: bytes) -> dict[str, float] | None:
    """Return normalised body-width ratios from a front photo, or None if
    the silhouette cannot be reliably detected."""
    from PIL import Image  # noqa: PLC0415 (lazy import — Pillow guaranteed available)

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        logger.warning("Could not open image for silhouette extraction")
        return None

    arr = np.array(img, dtype=np.float32)
    h_px, w_px = arr.shape[:2]

    if h_px < 100 or w_px < 50:
        return None

    # ── Background colour: median of the four 20×20 corners ──────────────
    corners = np.vstack([
        arr[:20, :20].reshape(-1, 3),
        arr[:20, -20:].reshape(-1, 3),
        arr[-20:, :20].reshape(-1, 3),
        arr[-20:, -20:].reshape(-1, 3),
    ])
    bg = np.median(corners, axis=0)  # shape (3,)

    # ── Binary mask: pixels that differ from background ───────────────────
    diff = np.abs(arr - bg).sum(axis=2)  # shape (h, w)
    mask = diff > 35  # True = body pixel

    # ── Vertical body bounds ──────────────────────────────────────────────
    row_has_body = mask.any(axis=1)
    body_rows = np.where(row_has_body)[0]
    if len(body_rows) < 60:
        logger.info("Silhouette too small or not detected (body rows: %d)", len(body_rows))
        return None

    y_top = int(body_rows[0])
    y_bot = int(body_rows[-1])
    body_h = y_bot - y_top

    # ── Width at each body fraction ───────────────────────────────────────
    widths: dict[str, float] = {}
    for name, frac in _FRACTIONS.items():
        y = y_top + int(frac * body_h)
        y = max(0, min(h_px - 1, y))
        row = mask[y]
        cols = np.where(row)[0]
        if len(cols) < 5:
            widths[name] = _NEUTRAL[name]  # fallback to neutral
        else:
            widths[name] = (int(cols[-1]) - int(cols[0])) / body_h

    return widths


# ---------------------------------------------------------------------------
# Semantic body params → SMPL betas (mirrors frontend bodyParamsMapping.ts)
# ---------------------------------------------------------------------------


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _clamp_beta(v: float) -> float:
    return _clamp(v, -3.5, 3.5)


def _body_params_to_betas(
    corpulence: float,
    musculature: float,
    shoulder_width: float,
    chest: float,
    belly: float,
    hips: float,
    arm_length: float,
    leg_length: float,
    leg_shape: float,
    height_m: float,
) -> list[float]:
    b = [0.0] * 10
    b[0] = (height_m - 1.75) * 2.5
    b[1] = -corpulence * 2.0 + musculature * 0.8
    b[2] = arm_length * 0.5 + leg_length * 0.4
    b[3] = chest * 0.7 + shoulder_width * 0.4
    b[4] = -hips * 0.5
    b[5] = -chest * 0.3 - shoulder_width * 0.3
    b[6] = belly * 0.8
    b[7] = -hips * 0.4 - leg_shape * 0.6
    b[8] = arm_length * 0.3
    b[9] = hips * 0.3
    return [_clamp_beta(v) for v in b]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def estimate_betas_from_photo(
    front_bytes: bytes,
    side_bytes: bytes | None,
    height_m: float,
    weight_kg: float,
) -> tuple[list[float], float, str]:
    """Estimate SMPL betas from a front (and optional side) photo.

    Returns:
        (betas, confidence, message)
        - betas: list[float] length 10
        - confidence: 0.0–1.0
        - message: human-readable status in French
    """
    widths = _extract_widths(front_bytes)

    if widths is None:
        # Silhouette not detected — return neutral defaults
        neutral_betas = _body_params_to_betas(
            corpulence=0, musculature=0, shoulder_width=0, chest=0,
            belly=0, hips=0, arm_length=0, leg_length=0, leg_shape=0,
            height_m=height_m,
        )
        return neutral_betas, 0.0, "Silhouette non détectée. Utilisez un fond uni et assurez-vous d'être visible en pied."

    # Compute relative deviations from neutral SMPL proportions
    def dev(key: str) -> float:
        ratio = widths.get(key, _NEUTRAL[key])
        neutral = _NEUTRAL[key]
        return (ratio - neutral) / neutral if neutral > 0 else 0.0

    d_shoulder = dev("shoulder")
    d_chest    = dev("chest")
    d_waist    = dev("waist")
    d_hip      = dev("hip")

    # Average body volume deviation → corpulence
    avg_volume = (d_chest + d_waist + d_hip) / 3.0
    corpulence = _clamp(avg_volume * 1.5)

    # Shoulder width relative to chest deviation
    shoulder_width = _clamp((d_shoulder - avg_volume) * 2.5)

    # Chest relative to average
    chest = _clamp((d_chest - avg_volume) * 2.0)

    # Belly: narrow waist relative to hips = negative belly, wide waist = positive
    belly = _clamp((d_waist - d_hip) * 2.0)

    # Hips relative to average
    hips = _clamp((d_hip - avg_volume) * 2.0)

    # Side photo: use depth at chest for belly/chest estimation if available
    if side_bytes:
        side_widths = _extract_widths(side_bytes)
        if side_widths:
            d_side_chest = dev("chest")  # reuse same fractions
            belly_boost = _clamp(d_side_chest * 1.5)
            belly = _clamp((belly + belly_boost) / 2)

    betas = _body_params_to_betas(
        corpulence=corpulence,
        musculature=0.0,    # cannot be inferred from silhouette alone
        shoulder_width=shoulder_width,
        chest=chest,
        belly=belly,
        hips=hips,
        arm_length=0.0,     # limb length unreliable from 2D silhouette
        leg_length=0.0,
        leg_shape=0.0,
        height_m=height_m,
    )

    # Confidence: based on how many body fractions had real detections
    real_detections = sum(
        1 for k in _FRACTIONS
        if abs(widths.get(k, _NEUTRAL[k]) - _NEUTRAL[k]) > 0.005
    )
    confidence = min(1.0, 0.3 + real_detections * 0.175)

    message = "Mannequin estimé depuis votre photo. Affinez avec les sliders si nécessaire."

    return betas, confidence, message
