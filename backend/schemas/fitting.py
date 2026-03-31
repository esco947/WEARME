"""Fitting response schema."""

from __future__ import annotations

from pydantic import BaseModel


class FittingMeasurements(BaseModel):
    height_cm: float
    chest_cm: float
    waist_cm: float
    hips_cm: float


class FittingResponse(BaseModel):
    garment_id: str
    garment_name: str
    garment_category: str
    recommended_size: str
    available_sizes: list[str]
    measurements: FittingMeasurements
    smpl_available: bool
