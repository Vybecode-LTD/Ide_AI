"""Add flow_version to projects.

Distinguishes legacy ("v1") projects that follow the old
Discovery → PathwayReview → PathwayExecute → per-module sessions flow
from new ("v2") projects that use the unified Discovery → Design Kit flow.

Default is v2. Existing rows are backfilled to v1 so their PathwayReview
/ Execute experience continues unchanged.

Revision ID: 029
Revises: 028
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "flow_version",
            sa.String(10),
            server_default="v2",
            nullable=False,
        ),
    )
    # Backfill all PRE-existing rows to v1 (legacy flow).
    # New rows created after this migration use the server_default of v2.
    op.execute("UPDATE projects SET flow_version = 'v1'")
    op.create_index("ix_projects_flow_version", "projects", ["flow_version"])


def downgrade() -> None:
    op.drop_index("ix_projects_flow_version", table_name="projects")
    op.drop_column("projects", "flow_version")
