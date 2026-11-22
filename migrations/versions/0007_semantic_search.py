"""Store multilingual game embeddings for semantic search."""

from alembic import op
import sqlalchemy as sa


revision = "0007_semantic_search"
down_revision = "0006_personalization"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("games", sa.Column("semantic_embedding", sa.Text(), nullable=True))
    op.add_column(
        "games", sa.Column("semantic_embedding_model", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "games", sa.Column("semantic_embedding_updated_at", sa.DateTime(), nullable=True)
    )


def downgrade():
    op.drop_column("games", "semantic_embedding_updated_at")
    op.drop_column("games", "semantic_embedding_model")
    op.drop_column("games", "semantic_embedding")
