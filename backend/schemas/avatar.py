"""Avatar request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AvatarResponse(BaseModel):
    id: str
    gender: str
    betas: list[float]
    height_m: float
    weight_kg: float

    model_config = {"from_attributes": True}


class AvatarUpdateRequest(BaseModel):
    gender: str | None = Field(None, pattern="^(neutral|male|female)$")
    betas: list[float] | None = Field(None, min_length=10, max_length=10)
    height_m: float | None = Field(None, ge=1.4, le=2.2)
    weight_kg: float | None = Field(None, ge=40.0, le=200.0)


class MeasurementsResponse(BaseModel):
    height_m: float
    chest_m: float
    waist_m: float
    hips_m: float


class PhotoEstimationResponse(BaseModel):
    id: str
    gender: str
    betas: list[float]
    height_m: float
    weight_kg: float
    confidence: float = Field(ge=0.0, le=1.0)
    message: str
