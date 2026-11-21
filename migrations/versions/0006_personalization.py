"""Add user identity, preference, and recommendation persistence."""

from alembic import op
import sqlalchemy as sa


revision = "0006_personalization"
down_revision = "0005_game_review_metadata"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("auth_provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("preference_mode", sa.String(length=20), nullable=False),
        sa.Column("onboarding_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "user_steam_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("steam_id", sa.String(length=32), nullable=False),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.Column("visibility_status", sa.String(length=20), nullable=False),
        sa.Column("sync_status", sa.String(length=20), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("connected_at", sa.DateTime(), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("steam_id"),
    )
    op.create_index("ix_user_steam_profiles_steam_id", "user_steam_profiles", ["steam_id"])

    op.create_table(
        "user_owned_games",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=True),
        sa.Column("steam_app_id", sa.String(length=32), nullable=False),
        sa.Column("playtime_minutes", sa.BigInteger(), nullable=False),
        sa.Column("recent_playtime_minutes", sa.BigInteger(), nullable=False),
        sa.Column("last_played_at", sa.DateTime(), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "steam_app_id", name="uq_user_owned_steam_app"),
    )
    op.create_index("ix_user_owned_games_user_id", "user_owned_games", ["user_id"])
    op.create_index("ix_user_owned_games_game_id", "user_owned_games", ["game_id"])

    op.create_table(
        "user_favorites",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "game_id", name="uq_user_favorite_game"),
    )
    op.create_index("ix_user_favorites_user_id", "user_favorites", ["user_id"])
    op.create_index("ix_user_favorites_game_id", "user_favorites", ["game_id"])

    op.create_table(
        "user_interactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("interaction_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_interactions_user_id", "user_interactions", ["user_id"])
    op.create_index("ix_user_interactions_game_id", "user_interactions", ["game_id"])
    op.create_index(
        "ix_user_interactions_interaction_type",
        "user_interactions",
        ["interaction_type"],
    )
    op.create_index("ix_user_interactions_created_at", "user_interactions", ["created_at"])

    op.create_table(
        "user_quiz_answers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("question_key", sa.String(length=100), nullable=False),
        sa.Column("answer_value", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_key", name="uq_user_quiz_question"),
    )
    op.create_index("ix_user_quiz_answers_user_id", "user_quiz_answers", ["user_id"])

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_type", sa.String(length=30), nullable=False),
        sa.Column("feature_key", sa.String(length=255), nullable=False),
        sa.Column("preference_score", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("profile_version", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "feature_type", "feature_key", "source",
            name="uq_user_preference_signal",
        ),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])

    op.create_table(
        "recommendation_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("preference_mode", sa.String(length=20), nullable=False),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("profile_version", sa.String(length=32), nullable=False),
        sa.Column("max_reviews", sa.BigInteger(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendation_runs_user_id", "recommendation_runs", ["user_id"])
    op.create_index(
        "ix_recommendation_runs_generated_at", "recommendation_runs", ["generated_at"]
    )

    op.create_table(
        "recommendations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("recommendation_type", sa.String(length=20), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("fit_score", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("popularity_score", sa.Float(), nullable=False),
        sa.Column("novelty_score", sa.Float(), nullable=False),
        sa.Column("recommendation_score", sa.Float(), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=True),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["recommendation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_run_id", "recommendations", ["run_id"])
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])
    op.create_index("ix_recommendations_game_id", "recommendations", ["game_id"])
    op.create_index(
        "ix_recommendations_recommendation_type",
        "recommendations",
        ["recommendation_type"],
    )


def downgrade():
    op.drop_index("ix_recommendations_recommendation_type", table_name="recommendations")
    op.drop_index("ix_recommendations_game_id", table_name="recommendations")
    op.drop_index("ix_recommendations_user_id", table_name="recommendations")
    op.drop_index("ix_recommendations_run_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_recommendation_runs_generated_at", table_name="recommendation_runs")
    op.drop_index("ix_recommendation_runs_user_id", table_name="recommendation_runs")
    op.drop_table("recommendation_runs")
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
    op.drop_index("ix_user_quiz_answers_user_id", table_name="user_quiz_answers")
    op.drop_table("user_quiz_answers")
    op.drop_index("ix_user_interactions_created_at", table_name="user_interactions")
    op.drop_index("ix_user_interactions_interaction_type", table_name="user_interactions")
    op.drop_index("ix_user_interactions_game_id", table_name="user_interactions")
    op.drop_index("ix_user_interactions_user_id", table_name="user_interactions")
    op.drop_table("user_interactions")
    op.drop_index("ix_user_favorites_game_id", table_name="user_favorites")
    op.drop_index("ix_user_favorites_user_id", table_name="user_favorites")
    op.drop_table("user_favorites")
    op.drop_index("ix_user_owned_games_game_id", table_name="user_owned_games")
    op.drop_index("ix_user_owned_games_user_id", table_name="user_owned_games")
    op.drop_table("user_owned_games")
    op.drop_index("ix_user_steam_profiles_steam_id", table_name="user_steam_profiles")
    op.drop_table("user_steam_profiles")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
