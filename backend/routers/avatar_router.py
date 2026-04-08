"""Avatar endpoints (v2 — betas as truth).

Endpoints:
    GET  /api/avatar              → {gender, betas[10], measurements}
    PUT  /api/avatar/gender       → {gender} → reset betas, recompute → AvatarResponse
    PUT  /api/avatar/sliders      → {targets} → optimize betas → AvatarResponse
    POST /api/avatar/photo-fit    → multipart → optimize betas → AvatarResponse
    GET  /api/avatar/mesh         → GLB binary
    GET  /api/avatar/measurements → measurements dict (cached or computed)
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Avatar, User
from backend.schemas.avatar import AvatarResponse, GenderUpdateRequest, MeasurementsResponse, SlidersUpdateRequest
from backend.services import avatar_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/avatar", tags=["avatar"])

_VALID_GENDERS = frozenset({"male", "female"})


def _get_or_create_avatar(current_user: User, db: Session) -> Avatar:
    """Return the user's avatar, creating a default one if absent."""
    if current_user.avatar is None:
        db.refresh(current_user)
    if current_user.avatar is None:
        avatar = Avatar(user_id=current_user.id)
        db.add(avatar)
        db.commit()
        db.refresh(current_user)
    return current_user.avatar


def _to_response(avatar: Avatar) -> AvatarResponse:
    measurements = (
        json.loads(avatar.measurements_cache)
        if avatar.measurements_cache
        else {}
    )
    return AvatarResponse(
        id=avatar.id,
        gender=avatar.gender,
        betas=json.loads(avatar.betas),
        measurements=measurements,
    )


@router.get("", response_model=AvatarResponse)
def get_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AvatarResponse:
    """Return the current user's avatar parameters and cached measurements."""
    avatar = _get_or_create_avatar(current_user, db)
    return _to_response(avatar)


@router.put("/gender", response_model=AvatarResponse)
def update_gender(
    body: GenderUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AvatarResponse:
    """Change avatar gender and reset betas to zero, recomputing measurements."""
    if body.gender not in _VALID_GENDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gender must be 'male' or 'female', got {body.gender!r}",
        )

    import numpy as np  # noqa: PLC0415

    avatar = _get_or_create_avatar(current_user, db)
    avatar.gender = body.gender

    try:
        avatar_service.compute_and_cache(avatar, np.zeros(10), db)
    except Exception as exc:
        logger.exception("Error computing measurements after gender update")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute measurements",
        ) from exc

    db.refresh(avatar)
    return _to_response(avatar)


@router.put("/sliders", response_model=AvatarResponse)
def update_sliders(
    body: SlidersUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AvatarResponse:
    """Optimise SMPL betas to match target measurements.

    ``targets`` keys must match ``core.body_schema.SLIDER_KEYS``:
    ``height``, ``chest_circumference``, ``waist_circumference``,
    ``hip_circumference``, ``shoulder_width``, ``inseam``.
    Values are in metres.
    """
    avatar = _get_or_create_avatar(current_user, db)
    try:
        avatar_service.update_from_sliders(avatar, body.targets, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Error in slider optimisation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Slider optimisation failed",
        ) from exc

    db.refresh(avatar)
    return _to_response(avatar)


@router.post("/photo-fit", response_model=AvatarResponse)
async def photo_fit(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    front: Annotated[UploadFile, File(description="Front photo (required)")],
    side: Annotated[UploadFile, File(description="Side photo (required)")],
    height_m: Annotated[float, Form(ge=1.4, le=2.2)],
    gender: Annotated[str, Form()],
) -> AvatarResponse:
    """Estimate body shape from front and side photos.

    Both photos are required. The fitting runs a silhouette-IoU + landmark
    reprojection optimiser (scipy L-BFGS-B, ~10-30s on CPU).
    """
    if gender not in _VALID_GENDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gender must be 'male' or 'female', got {gender!r}",
        )

    front_bytes = await front.read()
    side_bytes  = await side.read()

    avatar = _get_or_create_avatar(current_user, db)
    try:
        avatar_service.update_from_photos(
            avatar, front_bytes, side_bytes, height_m, gender, db
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Error in photo fitting")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Photo fitting failed",
        ) from exc

    db.refresh(avatar)
    return _to_response(avatar)


@router.get("/mesh")
def get_mesh(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Return the avatar SMPL mesh as a GLB binary."""
    avatar = _get_or_create_avatar(current_user, db)
    try:
        glb_bytes = avatar_service.get_glb(avatar)
    except Exception as exc:
        logger.exception("Error generating GLB mesh")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate mesh",
        ) from exc
    return Response(content=glb_bytes, media_type="model/gltf-binary")


@router.get("/measurements", response_model=MeasurementsResponse)
def get_measurements(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MeasurementsResponse:
    """Return current body measurements (from cache or recomputed)."""
    avatar = _get_or_create_avatar(current_user, db)
    try:
        m = avatar_service.get_measurements(avatar)
    except Exception as exc:
        logger.exception("Error computing measurements")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute measurements",
        ) from exc
    return MeasurementsResponse(measurements=m)
