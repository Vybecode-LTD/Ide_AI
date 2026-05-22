"""Deduplicate user rows v2 — keep the row with clerk_user_id set, merge children.

The previous dedup (023) kept the oldest row, but the race condition between
get_current_user (on-first-request fallback) and the Clerk webhook can create
new duplicates. This migration:
  1. Reassigns all child records from duplicate rows to the canonical row
     (the one with clerk_user_id set, falling back to oldest).
  2. Deletes the duplicate rows.

Revision ID: 026
Revises: 025
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All tables with a user_id FK → users.id (or created_by → users.id).
# Format: (table_name, fk_column_name)
_CHILD_TABLES = [
    ("projects", "user_id"),
    ("idea_inbox", "user_id"),
    ("user_memories", "user_id"),
    ("external_integrations", "user_id"),
    ("market_analyses", "user_id"),
    ("project_snapshots", "user_id"),
    ("sprint_plans", "user_id"),
    ("concept_branches", "created_by"),
    ("project_shares", "created_by"),
]

# Reusable CTE that ranks users per email (clerk_user_id preferred, then oldest).
_RANKED_CTE = """
    WITH ranked AS (
        SELECT id, email,
               ROW_NUMBER() OVER (
                   PARTITION BY email
                   ORDER BY
                       CASE WHEN clerk_user_id IS NOT NULL THEN 0 ELSE 1 END,
                       created_at ASC
               ) AS rn
        FROM users
    ),
    canonical AS (
        SELECT id AS keep_id, email
        FROM ranked
        WHERE rn = 1
    ),
    duplicates AS (
        SELECT r.id AS dup_id, c.keep_id
        FROM ranked r
        JOIN canonical c ON c.email = r.email
        WHERE r.rn > 1
    )
"""


def upgrade() -> None:
    # Reassign child records from duplicate user rows to the canonical row.
    for table, col in _CHILD_TABLES:
        op.execute(
            f"{_RANKED_CTE}"
            f"UPDATE {table} "
            f"SET {col} = d.keep_id "
            f"FROM duplicates d "
            f"WHERE {table}.{col} = d.dup_id"
        )

    # Delete the duplicate rows
    op.execute("""
        DELETE FROM users
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY email
                           ORDER BY
                               CASE WHEN clerk_user_id IS NOT NULL THEN 0 ELSE 1 END,
                               created_at ASC
                       ) AS rn
                FROM users
            ) ranked
            WHERE rn > 1
        )
    """)


def downgrade() -> None:
    # Cannot undo data merge/deletion
    pass
