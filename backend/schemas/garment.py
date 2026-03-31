"""Garment request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class GarmentResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str
    sizes: list[str]
    thumbnail_url: str | None = None

    model_config = {"from_attributes": True}


class GarmentListResponse(BaseModel):
    items: list[GarmentResponse]
    total: int
