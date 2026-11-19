"""Add current game deals table."""

from alembic import op
import sqlalchemy as sa


revision = "0002_game_deals"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("game_product_id", sa.BigInteger(), nullable=False),
        sa.Column("normal_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sale_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "discount_percent", sa.Numeric(precision=5, scale=2), nullable=False
        ),
        sa.Column("deal_url", sa.Text(), nullable=False),
        sa.Column("deal_end_date", sa.DateTime(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("external_deal_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["game_product_id"], ["game_products.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_product_id", "source", name="uq_deal_product_source"
        ),
    )
    op.create_index("ix_deals_game_product_id", "deals", ["game_product_id"])
    op.create_index("ix_deals_source", "deals", ["source"])
    op.create_index("ix_deals_is_active", "deals", ["is_active"])
    op.create_index("ix_deals_external_deal_id", "deals", ["external_deal_id"])


def downgrade():
    op.drop_index("ix_deals_external_deal_id", table_name="deals")
    op.drop_index("ix_deals_is_active", table_name="deals")
    op.drop_index("ix_deals_source", table_name="deals")
    op.drop_index("ix_deals_game_product_id", table_name="deals")
    op.drop_table("deals")
