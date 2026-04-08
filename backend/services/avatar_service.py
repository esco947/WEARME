"""Avatar service — bridge between Avatar ORM model and core SMPL engine.

Design principle: SMPL betas are the single source of truth.
Measurements are always derived from the mesh, never from a parameter matrix.

Workflow:
    1. Parse betas from avatar.betas (JSON)
    2. Run model.forward(betas) → vertices
    3. Run measure_mesh(vertices, faces, joints) → measurements dict
    4. Cache measurements in avatar.measurements_cache
    5. Export GLB via vertices_to_glb(vertices, faces)
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
# Model cache
# ---------------------------------------------------------------------------


def get_model(gender: str):
    """Return a cached :class:`~core.smpl_model.SMPLModel` for *gender*.

    Args:
        gender: ``"male"`` or ``"female"``.

    Returns:
        :class:`~core.smpl_model.SMPLModel` instance (loaded once, cached).
    """
    from core.smpl_model import load_smpl  # noqa: PLC0415
    return load_smpl(gender)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_betas(avatar: Avatar) -> np.ndarray:
    """Parse the avatar's JSON betas field into a numpy array."""
    return np.array(json.loads(avatar.betas), dtype=np.float64)


def compute_and_cache(
    avatar: Avatar,
    betas: np.ndarray,
    db: Session,
) -> dict[str, float]:
    """Run the forward pass, measure the mesh, and save to DB.

    Args:
        avatar: Avatar ORM instance to update.
        betas:  New SMPL betas ``(10,)``.
        db:     SQLAlchemy session.

    Returns:
        Measurements dict from ``measure_mesh()``.
    """
    from core.mesh_measurements import measure_mesh  # noqa: PLC0415

    model  = get_model(avatar.gender)
    verts  = model.forward(betas)
    joints = model.get_joints(betas)
    m      = measure_mesh(verts, model.faces, joints)

    avatar.betas              = json.dumps(betas.tolist())
    avatar.measurements_cache = json.dumps(m)
    db.commit()
    db.refresh(avatar)
    return m


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def update_from_sliders(
    avatar: Avatar,
    targets: dict[str, float],
    db: Session,
) -> dict[str, float]:
    """Optimise betas to match *targets* and persist.

    Args:
        avatar:  Avatar ORM instance.
        targets: Dict ``{measurement_key: target_metres}``.
        db:      SQLAlchemy session.

    Returns:
        Measurements dict of the resulting mesh.
    """
    from core.slider_optimizer import optimize_betas_from_targets  # noqa: PLC0415

    model         = get_model(avatar.gender)
    current_betas = get_betas(avatar)
    new_betas     = optimize_betas_from_targets(model, targets, current_betas, gender=avatar.gender)
    return compute_and_cache(avatar, new_betas, db)


def update_from_photos(
    avatar: Avatar,
    front_bytes: bytes,
    side_bytes: bytes,
    height_m: float,
    gender: str,
    db: Session,
) -> dict[str, float]:
    """Optimise betas from front and side photos and persist.

    Args:
        avatar:      Avatar ORM instance.
        front_bytes: Raw bytes of the front photo.
        side_bytes:  Raw bytes of the side photo.
        height_m:    Known standing height in metres.
        gender:      ``"male"`` or ``"female"``.
        db:          SQLAlchemy session.

    Returns:
        Measurements dict of the resulting mesh.
    """
    import cv2  # noqa: PLC0415

    from core.photo_optimizer import optimize_betas_from_photos  # noqa: PLC0415

    front = cv2.imdecode(np.frombuffer(front_bytes, np.uint8), cv2.IMREAD_COLOR)
    side  = cv2.imdecode(np.frombuffer(side_bytes,  np.uint8), cv2.IMREAD_COLOR)

    if front is None:
        raise ValueError("Could not decode front image")
    if side is None:
        raise ValueError("Could not decode side image")

    # Update gender if changed
    if avatar.gender != gender:
        avatar.gender = gender

    model         = get_model(gender)
    current_betas = get_betas(avatar)
    new_betas     = optimize_betas_from_photos(
        model, front, side, height_m, current_betas
    )
    return compute_and_cache(avatar, new_betas, db)


def get_glb(avatar: Avatar) -> bytes:
    """Generate a GLB binary from the avatar's current betas.

    Returns:
        Raw GLB bytes suitable for a ``model/gltf-binary`` HTTP response.
    """
    from core.glb_export import vertices_to_glb  # noqa: PLC0415

    model  = get_model(avatar.gender)
    betas  = get_betas(avatar)
    verts  = model.forward(betas)
    return vertices_to_glb(verts, model.faces)


def get_measurements(avatar: Avatar) -> dict[str, float]:
    """Return measurements from cache or recompute from betas.

    Returns:
        Measurements dict (keys from ``measure_mesh()``).
    """
    if avatar.measurements_cache:
        return json.loads(avatar.measurements_cache)

    from core.mesh_measurements import measure_mesh  # noqa: PLC0415

    model  = get_model(avatar.gender)
    betas  = get_betas(avatar)
    verts  = model.forward(betas)
    joints = model.get_joints(betas)
    return measure_mesh(verts, model.faces, joints)
