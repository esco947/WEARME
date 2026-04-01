"""Avatar service — bridge between Avatar ORM model and wearme.body engine.

Phase 2 changes:
* ``_build_body_params``: reads ``body_data`` JSON if present; falls back to
  legacy betas/height_m/weight_kg path for old rows.
* ``_save_body_params``: writes ``body_data``, keeps legacy columns in sync.
* ``get_full_measurements``: new — returns ``GarmentMeasurements`` from params.
* ``get_measurements``: unchanged 4-key dict API (backward compat).
* ``get_glb_bytes``: unchanged; calls ``update_smpl_betas`` before generating mesh.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from backend.models import Avatar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SMPL model cache (loaded once per gender on first use)
# ---------------------------------------------------------------------------

_model_cache: dict = {}

_PKL_FALLBACK = {"female": "neutral"}


def _get_model(gender: str):
    """Return (and cache) the SMPLModelData for *gender*.

    Falls back to "neutral" when the requested gender's .pkl is absent.
    """
    resolved = _PKL_FALLBACK.get(gender, gender)
    if resolved not in _model_cache:
        from wearme.body.smpl_bridge import load_model_data  # noqa: PLC0415

        logger.info("Loading SMPL model for gender=%r (first request)", resolved)
        try:
            _model_cache[resolved] = load_model_data(resolved)
        except FileNotFoundError:
            if resolved != "neutral":
                logger.warning(
                    "SMPL .pkl not found for gender=%r, falling back to neutral", resolved
                )
                _model_cache[resolved] = load_model_data("neutral")
            else:
                raise
    return _model_cache[resolved]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_body_params(avatar: Avatar):
    """Build a BodyParameters instance from an Avatar ORM row.

    * **New path** (``body_data`` present): deserialise full 55-param JSON.
    * **Legacy path** (``body_data`` is NULL): reconstruct from betas/height/weight
      using ``smpl_mapping.betas_to_anatomical``.
    """
    from wearme.body.body_params import BodyParameters  # noqa: PLC0415

    if avatar.body_data:
        data   = json.loads(avatar.body_data)
        params = BodyParameters.from_dict(data)
        return params

    # Legacy path — convert SMPL betas to anatomical params
    from wearme.body.smpl_mapping import betas_to_anatomical  # noqa: PLC0415

    betas = np.array(json.loads(avatar.betas), dtype=np.float64)
    anat  = betas_to_anatomical(betas, avatar.height_m, avatar.weight_kg, avatar.gender)

    params = BodyParameters(
        gender=avatar.gender,
        betas=betas,
        height_m=avatar.height_m,
        weight_kg=avatar.weight_kg,
    )
    # Overwrite _params with the estimated anatomical values
    for name, value in anat.items():
        params._params[name] = value

    return params


def _save_body_params(avatar: Avatar, params, db: Session) -> None:
    """Persist *params* to the Avatar row and commit.

    Ensures betas are current (calls ``update_smpl_betas``), writes
    ``body_data``, and keeps legacy columns in sync.
    """
    from wearme.body.smpl_mapping import update_smpl_betas  # noqa: PLC0415

    update_smpl_betas(params)   # recompute betas from anatomical params

    avatar.body_data  = json.dumps(params.to_dict())
    avatar.betas      = json.dumps(params.betas.tolist())
    avatar.height_m   = params.height_m
    avatar.weight_kg  = params.weight_kg
    db.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_measurements(avatar: Avatar) -> dict[str, float]:
    """Compute the four standard body measurements.

    Fast path: uses ``measurements_from_params`` (no SMPL model needed)
    when ``body_data`` is present.  Falls back to mesh-based measurement
    for legacy avatars.

    Returns:
        Dict with keys ``height_m``, ``chest_m``, ``waist_m``, ``hips_m``.
    """
    from wearme.body.measurements import compute_measurements  # noqa: PLC0415

    params = _build_body_params(avatar)

    if avatar.body_data:
        # Fast param path — no SMPL required
        result = compute_measurements(params, model_data=None)
    else:
        model_data = _get_model(avatar.gender)
        result     = compute_measurements(params, model_data)

    return {
        "height_m": result["height_m"],
        "chest_m":  result["chest_m"],
        "waist_m":  result["waist_m"],
        "hips_m":   result["hips_m"],
    }


def get_full_measurements(avatar: Avatar):
    """Return complete garment-ready measurements as a ``GarmentMeasurements`` object.

    Always uses the fast param path — no SMPL model required.

    Returns:
        :class:`~wearme.body.measurements.GarmentMeasurements` instance.
    """
    from wearme.body.measurements import measurements_from_params  # noqa: PLC0415

    params = _build_body_params(avatar)
    return measurements_from_params(params)


def get_glb_bytes(avatar: Avatar) -> bytes:
    """Generate a GLB binary of the avatar's SMPL mesh.

    The raw SMPL output is scaled to match ``avatar.height_m`` exactly.

    Returns:
        Raw GLB bytes suitable for a ``model/gltf-binary`` HTTP response.
    """
    import trimesh  # noqa: PLC0415

    from wearme.body.smpl_bridge import generate_vertices  # noqa: PLC0415
    from wearme.body.smpl_mapping import update_smpl_betas  # noqa: PLC0415

    params     = _build_body_params(avatar)
    update_smpl_betas(params)   # ensure betas reflect anatomical state

    model_data = _get_model(avatar.gender)
    vertices   = generate_vertices(params, model_data)

    # Scale mesh so its height matches the requested height_m
    y_min       = float(vertices[:, 1].min())
    y_max       = float(vertices[:, 1].max())
    mesh_height = y_max - y_min
    if mesh_height > 0 and avatar.height_m > 0:
        scale    = avatar.height_m / mesh_height
        vertices = vertices * scale

    mesh = trimesh.Trimesh(vertices=vertices, faces=model_data.faces, process=False)
    return bytes(mesh.export(file_type="glb"))
