"""Garment catalogue service."""

from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models import Garment
from backend.schemas.garment import GarmentResponse


def _to_schema(garment: Garment) -> GarmentResponse:
    return GarmentResponse(
        id=garment.id,
        name=garment.name,
        category=garment.category,
        description=garment.description,
        sizes=json.loads(garment.sizes),
        thumbnail_url=garment.thumbnail_url,
    )


def list_garments(db: Session) -> list[GarmentResponse]:
    garments = db.query(Garment).order_by(Garment.name).all()
    return [_to_schema(g) for g in garments]


def get_garment(garment_id: str, db: Session) -> GarmentResponse:
    garment = db.get(Garment, garment_id)
    if garment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garment not found")
    return _to_schema(garment)
