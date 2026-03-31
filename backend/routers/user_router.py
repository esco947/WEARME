"""User profile endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.models import User
from backend.schemas.auth import UserResponse

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)
