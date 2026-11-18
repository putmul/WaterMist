"""Create WaterMist foundation tables."""

from alembic import op
import sqlalchemy as sa

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "games",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("steam_app_id", sa.String(length=32), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("cover_image", sa.Text(), nullable=True),
        sa.Column("developer", sa.String(length=255), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("steam_app_id"),
    )
    op.create_index("ix_games_name", "games", ["name"])
    op.create_index("ix_games_release_date", "games", ["release_date"])
    op.create_index("ix_games_steam_app_id", "games", ["steam_app_id"])

    op.create_table(
        "stores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("external_store_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_stores_external_store_id", "stores", ["external_store_id"])
    op.create_index("ix_stores_source", "stores", ["source"])

    op.create_table(
        "genres",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "game_products",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("external_product_id", sa.String(length=128), nullable=False),
        sa.Column("product_url", sa.Text(), nullable=True),
        sa.Column("region", sa.String(length=16), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_id", "external_product_id", "region", name="uq_game_product_identity"
        ),
    )
    op.create_index("ix_game_products_game_id", "game_products", ["game_id"])
    op.create_index("ix_game_products_store_id", "game_products", ["store_id"])

    op.create_table(
        "game_genres",
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("genre_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id", "genre_id"),
    )

    op.create_table(
        "game_tags",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("tag", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "tag", name="uq_game_tag"),
    )
    op.create_index("ix_game_tags_game_id", "game_tags", ["game_id"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("game_product_id", sa.BigInteger(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("regular_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("recorded_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["game_product_id"], ["game_products.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_product_id", "recorded_date", name="uq_price_history_daily_snapshot"
        ),
    )
    op.create_index("ix_price_history_game_product_id", "price_history", ["game_product_id"])

    op.create_table(
        "job_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("records_fetched", sa.Integer(), nullable=False),
        sa.Column("records_saved", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"])


def downgrade():
    op.drop_index("ix_job_runs_job_name", table_name="job_runs")
    op.drop_table("job_runs")
    op.drop_index("ix_price_history_game_product_id", table_name="price_history")
    op.drop_table("price_history")
    op.drop_index("ix_game_tags_game_id", table_name="game_tags")
    op.drop_table("game_tags")
    op.drop_table("game_genres")
    op.drop_index("ix_game_products_store_id", table_name="game_products")
    op.drop_index("ix_game_products_game_id", table_name="game_products")
    op.drop_table("game_products")
    op.drop_table("genres")
    op.drop_index("ix_stores_source", table_name="stores")
    op.drop_index("ix_stores_external_store_id", table_name="stores")
    op.drop_table("stores")
    op.drop_index("ix_games_steam_app_id", table_name="games")
    op.drop_index("ix_games_release_date", table_name="games")
    op.drop_index("ix_games_name", table_name="games")
    op.drop_table("games")
