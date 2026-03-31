"""Fitting endpoint — size recommendation for an avatar + garment."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Garment, User
from backend.schemas.fitting import FittingResponse
from backend.services import fitting_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fitting", tags=["fitting"])


@router.post("/{garment_id}", response_model=FittingResponse)
def fit_garment(
    garment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FittingResponse:
    """Compute recommended size for the user's avatar and a given garment."""
    garment = db.get(Garment, garment_id)
    if garment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garment not found")

    avatar = current_user.avatar
    if avatar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")

    result = fitting_service.compute_fitting(avatar, garment)
    return FittingResponse(
        garment_id=result["garment_id"],
        garment_name=result["garment_name"],
        garment_category=result["garment_category"],
        recommended_size=result["recommended_size"],
        available_sizes=result["available_sizes"],
        measurements=result["measurements"],
        smpl_available=result["smpl_available"],
    )
