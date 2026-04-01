"""Add body_data JSON column to avatars.

Stores the full 55-parameter anatomical body profile as a JSON text blob.
Legacy columns (betas, height_m, weight_kg) are kept and kept in sync
for backward compatibility during Phase 2.

Revision ID: 002
Revises: 001
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "avatars",
        sa.Column(
            "body_data",
            sa.Text,
            nullable=True,
            server_default=None,
        ),
    )


def downgrade() -> None:
    op.drop_column("avatars", "body_data")
