"""Backfill lifecycle status for deals that were already inactive."""

from alembic import op


revision = "0004_backfill_deal_lifecycle"
down_revision = "0003_deal_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE deals SET is_on_sale = 0 "
        "WHERE is_active = 0 AND is_on_sale <> 0"
    )
    op.execute(
        "UPDATE deals SET ended_at = fetched_at, end_reason = 'legacy_inactive' "
        "WHERE is_active = 0 AND ended_at IS NULL"
    )


def downgrade():
    op.execute(
        "UPDATE deals SET is_on_sale = 1 "
        "WHERE end_reason = 'legacy_inactive'"
    )
    op.execute(
        "UPDATE deals SET ended_at = NULL, end_reason = NULL "
        "WHERE end_reason = 'legacy_inactive'"
    )
