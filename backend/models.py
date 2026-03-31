"""SQLAlchemy ORM models: User, Avatar, Garment."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    avatar: Mapped[Avatar | None] = relationship("Avatar", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"


# ---------------------------------------------------------------------------
# Avatar
# ---------------------------------------------------------------------------


class Avatar(Base):
    __tablename__ = "avatars"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False, default="neutral")
    betas: Mapped[str] = mapped_column(Text, nullable=False, default=json.dumps([0.0] * 10))
    height_m: Mapped[float] = mapped_column(Float, nullable=False, default=1.75)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False, default=70.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship("User", back_populates="avatar")

    def __repr__(self) -> str:
        return f"<Avatar id={self.id!r} user_id={self.user_id!r} gender={self.gender!r}>"


# ---------------------------------------------------------------------------
# Garment
# ---------------------------------------------------------------------------


class Garment(Base):
    __tablename__ = "garments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sizes: Mapped[str] = mapped_column(Text, nullable=False, default=json.dumps(["XS", "S", "M", "L", "XL"]))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Garment id={self.id!r} name={self.name!r}>"
