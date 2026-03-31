"""Avatar endpoints: GET/PUT params, measurements, GLB mesh."""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import User
from backend.schemas.avatar import (
    AvatarResponse,
    AvatarUpdateRequest,
    MeasurementsResponse,
    PhotoEstimationResponse,
)
from backend.services import avatar_service, photo_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/avatar", tags=["avatar"])


def _get_avatar(current_user: User, db: Session):
    """Return the current user's avatar, raising 404 if missing."""
    if current_user.avatar is None:
        db.refresh(current_user)
    avatar = current_user.avatar
    if avatar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")
    return avatar


def _avatar_to_schema(avatar) -> AvatarResponse:
    return AvatarResponse(
        id=avatar.id,
        gender=avatar.gender,
        betas=json.loads(avatar.betas),
        height_m=avatar.height_m,
        weight_kg=avatar.weight_kg,
    )


@router.get("", response_model=AvatarResponse)
def get_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AvatarResponse:
    """Return the current user's avatar parameters."""
    avatar = _get_avatar(current_user, db)
    return _avatar_to_schema(avatar)


@router.put("", response_model=AvatarResponse)
def update_avatar(
    body: AvatarUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AvatarResponse:
    """Update one or more avatar parameters."""
    avatar = _get_avatar(current_user, db)

    if body.gender is not None:
        avatar.gender = body.gender
    if body.betas is not None:
        avatar.betas = json.dumps(body.betas)
    if body.height_m is not None:
        avatar.height_m = body.height_m
    if body.weight_kg is not None:
        avatar.weight_kg = body.weight_kg

    db.commit()
    db.refresh(avatar)
    return _avatar_to_schema(avatar)


@router.get("/measurements", response_model=MeasurementsResponse)
def get_measurements(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MeasurementsResponse:
    """Compute body measurements from the avatar's SMPL parameters."""
    avatar = _get_avatar(current_user, db)
    try:
        result = avatar_service.get_measurements(avatar)
    except Exception as exc:
        logger.exception("Error computing measurements")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to compute measurements") from exc
    return MeasurementsResponse(**result)


@router.post("/from-photo", response_model=PhotoEstimationResponse)
async def avatar_from_photo(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    front_photo: Annotated[UploadFile, File(description="Photo de face (fond uni)")],
    side_photo: Annotated[UploadFile | None, File(description="Photo de profil (optionnel)")] = None,
    height_m: Annotated[float, Form(ge=1.4, le=2.2)] = 1.75,
    weight_kg: Annotated[float, Form(ge=40.0, le=200.0)] = 70.0,
) -> PhotoEstimationResponse:
    """Estimate avatar body shape from a front photo (and optional side photo)."""
    front_bytes = await front_photo.read()
    side_bytes  = await side_photo.read() if side_photo else None

    betas, confidence, message = photo_service.estimate_betas_from_photo(
        front_bytes, side_bytes, height_m, weight_kg
    )

    avatar = _get_avatar(current_user, db)
    avatar.betas     = json.dumps(betas)
    avatar.height_m  = height_m
    avatar.weight_kg = weight_kg
    db.commit()
    db.refresh(avatar)

    return PhotoEstimationResponse(
        id=avatar.id,
        gender=avatar.gender,
        betas=betas,
        height_m=height_m,
        weight_kg=weight_kg,
        confidence=confidence,
        message=message,
    )


@router.get("/mesh")
def get_mesh(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Return the avatar SMPL mesh as a GLB binary."""
    avatar = _get_avatar(current_user, db)
    try:
        glb_bytes = avatar_service.get_glb_bytes(avatar)
    except Exception as exc:
        logger.exception("Error generating GLB mesh")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate mesh") from exc
    return Response(content=glb_bytes, media_type="model/gltf-binary")
