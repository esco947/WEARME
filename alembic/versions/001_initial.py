"""Initial schema — users, avatars, garments.

Revision ID: 001
Revises:
Create Date: 2026-03-29

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "avatars",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("gender", sa.String(10), nullable=False, server_default="neutral"),
        sa.Column("betas", sa.Text, nullable=False, server_default="[0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]"),
        sa.Column("height_m", sa.Float, nullable=False, server_default="1.75"),
        sa.Column("weight_kg", sa.Float, nullable=False, server_default="70.0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "garments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("sizes", sa.Text, nullable=False, server_default='["XS","S","M","L","XL"]'),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("garments")
    op.drop_table("avatars")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
