"""SQLAlchemy ORM models: User, Avatar.

Garment and Fitting tables are removed — this app is now avatar-only.

Avatar schema (v2):
    - betas:              JSON array of 10 SMPL shape floats (source of truth)
    - measurements_cache: JSON dict of last measured values (recalculated on update)
    - gender:             "male" | "female" only (no neutral)
    - No height_m, weight_kg, body_data columns — measurements come from mesh.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    avatar: Mapped[Avatar | None] = relationship(
        "Avatar", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"


class Avatar(Base):
    __tablename__ = "avatars"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )
    gender: Mapped[str] = mapped_column(
        String(10), nullable=False, default="male"
    )  # "male" | "female" only
    betas: Mapped[str] = mapped_column(
        Text, nullable=False, default=lambda: json.dumps([0.0] * 10)
    )  # JSON array of 10 floats — SMPL shape coefficients, source of truth
    measurements_cache: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )  # JSON dict of last measure_mesh() output; recalculated on every update
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="avatar")

    def __repr__(self) -> str:
        return f"<Avatar id={self.id!r} user_id={self.user_id!r} gender={self.gender!r}>"
