"""Phase 2 hotfix — module_pathways modules shape backfill + module_responses unique constraint.

Phase 1 (commit fb840de) stored `module_pathways.modules` as a list of
full assembled module dicts. The rest of the system (PathwayRead schema,
modules.py router, frontend store) expects a list of module-id strings.
This migration:

  1. Backfills `module_pathways.modules` from list[dict] → list[str] for
     any rows already created on the broken shape.
  2. Dedups `module_responses` by (project_id, module_id) keeping the
     most recent row — required before adding the unique constraint.
  3. Adds UNIQUE(project_id, module_id) on `module_responses` so the
     race-safe ON CONFLICT upsert used by Phase 2 discovery extraction
     can apply field updates without duplicate-row pile-ups.

Revision ID: 030
Revises: 029
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op

revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill module_pathways.modules from list[dict] -> list[str].
    #    Only touches rows where the first element is an object (the
    #    broken Phase-1 shape). Rows already storing strings are skipped.
    op.execute("""
        UPDATE module_pathways
        SET modules = COALESCE(
            (SELECT jsonb_agg(elem->'module_id')
             FROM jsonb_array_elements(modules) elem
             WHERE jsonb_typeof(elem) = 'object'
               AND elem->'module_id' IS NOT NULL),
            modules
        )
        WHERE jsonb_typeof(modules) = 'array'
          AND jsonb_array_length(modules) > 0
          AND jsonb_typeof(modules->0) = 'object'
    """)

    # 2. Dedup module_responses by (project_id, module_id). Keep the row
    #    with the most recent created_at; delete older duplicates.
    #    Required so step 3's unique index can be created.
    op.execute("""
        DELETE FROM module_responses
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY project_id, module_id
                           ORDER BY created_at DESC, id DESC
                       ) AS rn
                FROM module_responses
            ) ranked
            WHERE rn > 1
        )
    """)

    # 3. Race-safe unique index for ON CONFLICT upsert.
    op.create_index(
        "ix_module_responses_project_module_unique",
        "module_responses",
        ["project_id", "module_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_module_responses_project_module_unique",
        table_name="module_responses",
    )
    # Cannot undo shape backfill or dedup — they are forward-only data fixes.
