"""Store Steam review metadata on games."""

from alembic import op
import sqlalchemy as sa


revision = "0005_game_review_metadata"
down_revision = "0004_backfill_deal_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("games", sa.Column("steam_rating_percent", sa.Integer(), nullable=True))
    op.add_column("games", sa.Column("steam_rating_count", sa.BigInteger(), nullable=True))
    op.add_column("games", sa.Column("steam_rating_text", sa.String(length=100), nullable=True))
    op.add_column("games", sa.Column("review_source", sa.String(length=64), nullable=True))
    op.add_column("games", sa.Column("review_updated_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("games", "review_updated_at")
    op.drop_column("games", "review_source")
    op.drop_column("games", "steam_rating_text")
    op.drop_column("games", "steam_rating_count")
    op.drop_column("games", "steam_rating_percent")
