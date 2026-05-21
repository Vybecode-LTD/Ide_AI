"""Add provider_event_id to idea_inbox for webhook idempotency.

Revision ID: 025
Revises: 024
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "idea_inbox",
        sa.Column("provider_event_id", sa.String(255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_idea_inbox_provider_event_id",
        "idea_inbox",
        ["provider_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_idea_inbox_provider_event_id", "idea_inbox", type_="unique")
    op.drop_column("idea_inbox", "provider_event_id")
