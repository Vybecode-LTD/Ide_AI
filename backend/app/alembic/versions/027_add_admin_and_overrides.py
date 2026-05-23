"""Add is_admin flag and entitlement_overrides to users.

is_admin gates the /admin API surface. entitlement_overrides is a per-user
JSONB column that, when set, overrides PLAN_LIMITS keys at lookup time —
used for granting comps, beta access, or per-account caps.

Schema of entitlement_overrides (all keys optional, null means unlimited):
    {
        "projects": int | null,
        "prompt_packages": int | null,
        "market_analysis": int | null,
        "sprint_plans": int | null
    }

Revision ID: 027
Revises: 026
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("entitlement_overrides", JSONB(), nullable=True),
    )
    op.create_index("ix_users_is_admin", "users", ["is_admin"])


def downgrade() -> None:
    op.drop_index("ix_users_is_admin", table_name="users")
    op.drop_column("users", "entitlement_overrides")
    op.drop_column("users", "is_admin")
