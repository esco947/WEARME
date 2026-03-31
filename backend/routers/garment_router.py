"""Garment catalogue endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.garment import GarmentListResponse, GarmentResponse
from backend.services import garment_service

router = APIRouter(prefix="/api/garments", tags=["garments"])


@router.get("", response_model=GarmentListResponse)
def list_garments(db: Annotated[Session, Depends(get_db)]) -> GarmentListResponse:
    """Return the full garment catalogue."""
    items = garment_service.list_garments(db)
    return GarmentListResponse(items=items, total=len(items))


@router.get("/{garment_id}", response_model=GarmentResponse)
def get_garment(garment_id: str, db: Annotated[Session, Depends(get_db)]) -> GarmentResponse:
    """Return a single garment by id."""
    return garment_service.get_garment(garment_id, db)
