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
    FullMeasurementsResponse,
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
    """Update one or more avatar parameters.

    Supports both legacy (betas/height_m/weight_kg) and Phase-2
    (params dict of anatomical measurements) update paths.
    """
    avatar = _get_avatar(current_user, db)

    if body.gender is not None:
        avatar.gender = body.gender

    # Phase 2: full anatomical update via params dict
    if body.params is not None or body.betas is not None or body.height_m is not None or body.weight_kg is not None:
        params = avatar_service._build_body_params(avatar)

        if body.gender is not None:
            params.gender = body.gender

        if body.betas is not None:
            import numpy as np  # noqa: PLC0415
            params.betas = np.array(body.betas, dtype=np.float64)

        if body.params is not None:
            # Apply anatomical params (height/weight propagate, others don't)
            height_val  = body.params.pop("height_m",  None) if isinstance(body.params, dict) else None
            weight_val  = body.params.pop("weight_kg", None) if isinstance(body.params, dict) else None
            for name, value in (body.params or {}).items():
                try:
                    params.set_param(name, float(value), propagate=False)
                except (KeyError, ValueError):
                    pass   # skip unknown / out-of-range params silently
            if weight_val is not None:
                params.set_param("weight_kg", float(weight_val), propagate=True)
            if height_val is not None:
                params.set_param("height_m",  float(height_val),  propagate=True)
        else:
            if body.height_m is not None:
                params.set_param("height_m",  body.height_m,  propagate=True)
            if body.weight_kg is not None:
                params.set_param("weight_kg", body.weight_kg, propagate=True)

        if body.locked is not None:
            for name in body.locked:
                params.lock(name)

        avatar_service._save_body_params(avatar, params, db)
    else:
        # Pure gender update (no body shape change)
        db.commit()

    db.refresh(avatar)
    return _avatar_to_schema(avatar)


@router.get("/measurements/full", response_model=FullMeasurementsResponse)
def get_full_measurements(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FullMeasurementsResponse:
    """Return complete garment-ready measurements from the 55-param system."""
    avatar = _get_avatar(current_user, db)
    try:
        m = avatar_service.get_full_measurements(avatar)
    except Exception as exc:
        logger.exception("Error computing full measurements")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute full measurements",
        ) from exc
    return FullMeasurementsResponse(
        height_m=m.height_m,
        chest_m=m.chest_m,
        underbust_m=m.underbust_m,
        waist_m=m.waist_m,
        abdomen_m=m.abdomen_m,
        hip_m=m.hip_m,
        hips_m=m.hip_m,
        neck_m=m.neck_m,
        shoulder_width_m=m.shoulder_width_m,
        arm_length_m=m.arm_length_m,
        upper_arm_m=m.upper_arm_m,
        forearm_m=m.forearm_m,
        wrist_m=m.wrist_m,
        inseam_m=m.inseam_m,
        outseam_m=m.outseam_m,
        thigh_m=m.thigh_m,
        calf_m=m.calf_m,
        ankle_m=m.ankle_m,
        front_length_m=m.front_length_m,
        back_length_m=m.back_length_m,
        dart_width_m=m.dart_width_m,
        chest_with_ease_m=m.chest_with_ease_m,
        waist_with_ease_m=m.waist_with_ease_m,
        hip_with_ease_m=m.hip_with_ease_m,
        eu_size_top=m.eu_size_top,
        eu_size_bottom=m.eu_size_bottom,
        us_size_top=m.us_size_top,
    )


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
