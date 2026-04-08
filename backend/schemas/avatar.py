"""Avatar request/response schemas (v2 — betas as truth)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AvatarResponse(BaseModel):
    id: str
    gender: str
    betas: list[float]
    measurements: dict[str, float]

    model_config = {"from_attributes": True}


class GenderUpdateRequest(BaseModel):
    gender: str = Field(..., pattern="^(male|female)$")


class SlidersUpdateRequest(BaseModel):
    """Target measurements in metres, keyed by slider key."""
    targets: dict[str, float]


class MeasurementsResponse(BaseModel):
    measurements: dict[str, float]
