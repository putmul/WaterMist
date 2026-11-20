"""Track deal lifecycle and sale status."""

from alembic import op
import sqlalchemy as sa


revision = "0003_deal_lifecycle"
down_revision = "0002_game_deals"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "deals",
        sa.Column("is_on_sale", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "deals",
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
    )
    op.add_column("deals", sa.Column("ended_at", sa.DateTime(), nullable=True))
    op.add_column("deals", sa.Column("end_reason", sa.String(length=32), nullable=True))
    op.execute("UPDATE deals SET first_seen_at = fetched_at WHERE first_seen_at IS NULL")
    op.create_index("ix_deals_is_on_sale", "deals", ["is_on_sale"])
    op.create_index("ix_deals_first_seen_at", "deals", ["first_seen_at"])
    op.create_index("ix_deals_ended_at", "deals", ["ended_at"])


def downgrade():
    op.drop_index("ix_deals_ended_at", table_name="deals")
    op.drop_index("ix_deals_first_seen_at", table_name="deals")
    op.drop_index("ix_deals_is_on_sale", table_name="deals")
    op.drop_column("deals", "end_reason")
    op.drop_column("deals", "ended_at")
    op.drop_column("deals", "first_seen_at")
    op.drop_column("deals", "is_on_sale")
