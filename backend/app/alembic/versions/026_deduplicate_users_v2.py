"""Deduplicate user rows v2 — keep the row with clerk_user_id set, merge projects.

The previous dedup (023) kept the oldest row, but the race condition between
get_current_user (on-first-request fallback) and the Clerk webhook can create
new duplicates. This migration:
  1. Reassigns all child records (projects, inbox items, etc.) from duplicate
     rows to the canonical row (the one with clerk_user_id set, or oldest).
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


def upgrade() -> None:
    # Find duplicate emails and pick the "canonical" row per email:
    # prefer the row that has a clerk_user_id, then fall back to oldest.
    # Reassign child records from duplicate → canonical, then delete duplicates.
    op.execute("""
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
        -- Reassign projects
        UPDATE projects
        SET user_id = d.keep_id
        FROM duplicates d
        WHERE projects.user_id = d.dup_id
    """)

    op.execute("""
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
        -- Reassign inbox items
        UPDATE idea_inbox
        SET user_id = d.keep_id
        FROM duplicates d
        WHERE idea_inbox.user_id = d.dup_id
    """)

    op.execute("""
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
        -- Reassign user memory
        UPDATE user_memory
        SET user_id = d.keep_id
        FROM duplicates d
        WHERE user_memory.user_id = d.dup_id
    """)

    op.execute("""
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
        -- Reassign integrations
        UPDATE user_integrations
        SET user_id = d.keep_id
        FROM duplicates d
        WHERE user_integrations.user_id = d.dup_id
    """)

    op.execute("""
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
        -- Reassign project shares
        UPDATE project_shares
        SET user_id = d.keep_id
        FROM duplicates d
        WHERE project_shares.user_id = d.dup_id
    """)

    # Now delete the duplicate rows
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
