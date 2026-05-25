"""Add scope_module_ids to sessions for mini-Discovery scoping.

When non-null, the session is scoped to only the listed module IDs
(e.g. modules added via the Design Kit's Add Modules flow). Main-flow
resume logic excludes scoped sessions so they don't hijack the primary
discovery.

Revision ID: 031
Revises: 030
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "031"
down_revision: str = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("scope_module_ids", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "scope_module_ids")
