"""Add Stripe subscription state columns to users.

Tracks the full subscription lifecycle so the entitlement service can
make plan-limit decisions from local state without extra Stripe API calls.

Revision ID: 032
Revises: 031
"""
from alembic import op
import sqlalchemy as sa

revision: str = "032"
down_revision: str = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("subscription_status", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("subscription_price_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("subscription_current_period_end", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_users_stripe_subscription_id", "users", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_stripe_subscription_id", "users", type_="unique")
    op.drop_column("users", "subscription_current_period_end")
    op.drop_column("users", "subscription_price_id")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
