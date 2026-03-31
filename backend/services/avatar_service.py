"""Avatar service — bridge between Avatar ORM model and wearme.body SMPL engine."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from backend.models import Avatar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SMPL model cache (loaded once per gender on first use)
# ---------------------------------------------------------------------------

_model_cache: dict = {}


_PKL_FALLBACK = {"female": "neutral"}


def _get_model(gender: str):
    """Return (and cache) the SMPLModelData for *gender*.

    Falls back to "neutral" when the requested gender's .pkl file is absent
    (e.g. the female model is not distributed in this repo).
    """
    resolved = _PKL_FALLBACK.get(gender, gender)
    if resolved not in _model_cache:
        from wearme.body.smpl_bridge import load_model_data  # noqa: PLC0415

        logger.info("Loading SMPL model for gender=%r (first request)", resolved)
        try:
            _model_cache[resolved] = load_model_data(resolved)
        except FileNotFoundError:
            if resolved != "neutral":
                logger.warning("SMPL .pkl not found for gender=%r, falling back to neutral", resolved)
                _model_cache[resolved] = load_model_data("neutral")
            else:
                raise
    return _model_cache[resolved]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_body_params(avatar: Avatar):
    """Build a BodyParameters instance from an Avatar ORM row."""
    from wearme.body.body_params import BodyParameters  # noqa: PLC0415

    betas = np.array(json.loads(avatar.betas), dtype=np.float64)
    return BodyParameters(
        gender=avatar.gender,
        betas=betas,
        height_m=avatar.height_m,
        weight_kg=avatar.weight_kg,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_measurements(avatar: Avatar) -> dict[str, float]:
    """Compute body measurements from the avatar's SMPL parameters.

    Returns:
        Dict with keys ``height_m``, ``chest_m``, ``waist_m``, ``hips_m``.
    """
    from wearme.body.measurements import compute_measurements  # noqa: PLC0415

    params = _build_body_params(avatar)
    model_data = _get_model(avatar.gender)
    result = compute_measurements(params, model_data)
    return {
        "height_m": result["height_m"],
        "chest_m": result["chest_m"],
        "waist_m": result["waist_m"],
        "hips_m": result["hips_m"],
    }


def get_glb_bytes(avatar: Avatar) -> bytes:
    """Generate a GLB binary of the avatar's SMPL mesh.

    The raw SMPL output is scaled to match ``avatar.height_m`` exactly,
    since ``generate_vertices`` produces vertices at model-natural scale
    (determined by betas, ≈ 1.7 m for zero betas) without absolute height.

    Returns:
        Raw GLB bytes suitable for a ``model/gltf-binary`` HTTP response.
    """
    import trimesh  # noqa: PLC0415

    from wearme.body.smpl_bridge import generate_vertices  # noqa: PLC0415

    params = _build_body_params(avatar)
    model_data = _get_model(avatar.gender)
    vertices = generate_vertices(params, model_data)

    # Scale mesh so its height matches the requested height_m.
    # SMPL Y-axis is up; height = max_y − min_y.
    y_min = float(vertices[:, 1].min())
    y_max = float(vertices[:, 1].max())
    mesh_height = y_max - y_min
    if mesh_height > 0 and avatar.height_m > 0:
        scale = avatar.height_m / mesh_height
        vertices = vertices * scale

    mesh = trimesh.Trimesh(vertices=vertices, faces=model_data.faces, process=False)
    return bytes(mesh.export(file_type="glb"))
