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
    # Phase 2: anatomical params (subset of 55 keys)
    params: dict[str, float] | None = None
    locked: list[str] | None = None


class MeasurementsResponse(BaseModel):
    height_m: float
    chest_m: float
    waist_m: float
    hips_m: float


class FullMeasurementsResponse(BaseModel):
    """Complete garment-ready measurements from the 55-param system."""
    height_m:          float
    chest_m:           float
    underbust_m:       float
    waist_m:           float
    abdomen_m:         float
    hip_m:             float
    hips_m:            float   # alias for hip_m (backward compat)
    neck_m:            float
    shoulder_width_m:  float
    arm_length_m:      float
    upper_arm_m:       float
    forearm_m:         float
    wrist_m:           float
    inseam_m:          float
    outseam_m:         float
    thigh_m:           float
    calf_m:            float
    ankle_m:           float
    front_length_m:    float
    back_length_m:     float
    dart_width_m:      float
    chest_with_ease_m: float
    waist_with_ease_m: float
    hip_with_ease_m:   float
    eu_size_top:       str
    eu_size_bottom:    str
    us_size_top:       str


class PhotoEstimationResponse(BaseModel):
    id: str
    gender: str
    betas: list[float]
    height_m: float
    weight_kg: float
    confidence: float = Field(ge=0.0, le=1.0)
    message: str
