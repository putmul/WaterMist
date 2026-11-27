"""Normalize preference feature keys independent of case and whitespace."""

from collections import defaultdict

from alembic import op
import sqlalchemy as sa


revision = "0008_normalize_preference_features"
down_revision = "0007_semantic_search"
branch_labels = None
depends_on = None


def upgrade():
    preferences = sa.table(
        "user_preferences",
        sa.column("id", sa.BigInteger),
        sa.column("user_id", sa.BigInteger),
        sa.column("feature_type", sa.String),
        sa.column("feature_key", sa.String),
        sa.column("source", sa.String),
        sa.column("preference_score", sa.Float),
        sa.column("confidence", sa.Float),
        sa.column("profile_version", sa.String),
        sa.column("updated_at", sa.DateTime),
    )
    bind = op.get_bind()
    rows = bind.execute(sa.select(preferences)).mappings().all()
    groups = defaultdict(list)
    for row in rows:
        feature_type = row["feature_type"].strip().casefold()
        feature_type = {"genres": "genre", "tags": "tag"}.get(
            feature_type, feature_type
        )
        key = (
            row["user_id"],
            feature_type,
            row["feature_key"].strip().casefold(),
            row["source"],
        )
        groups[key].append(row)

    # Delete colliding rows first, then canonicalize each surviving row so the
    # existing per-source unique constraint remains valid on every DB backend.
    winners = []
    duplicate_ids = []
    for key, group in groups.items():
        winner = min(group, key=lambda row: row["id"])
        winners.append((key, group, winner))
        duplicate_ids.extend(row["id"] for row in group if row["id"] != winner["id"])

    if duplicate_ids:
        bind.execute(
            preferences.delete().where(preferences.c.id.in_(duplicate_ids))
        )

    for key, group, winner in winners:
        latest = max(group, key=lambda row: row["updated_at"] or winner["updated_at"])
        bind.execute(
            preferences.update()
            .where(preferences.c.id == winner["id"])
            .values(
                feature_type=key[1],
                feature_key=key[2],
                # Duplicate case variants represent one signal; retain the
                # strongest score rather than inflating it by summation.
                preference_score=max(row["preference_score"] for row in group),
                confidence=max(row["confidence"] for row in group),
                profile_version=latest["profile_version"],
                updated_at=latest["updated_at"],
            )
        )

    quiz_answers = sa.table(
        "user_quiz_answers",
        sa.column("id", sa.BigInteger),
        sa.column("answer_value", sa.String),
    )
    for row in bind.execute(sa.select(quiz_answers)).mappings():
        normalized_values = []
        seen_values = set()
        for value in row["answer_value"].split(","):
            value = value.strip().casefold()
            if value and value not in seen_values:
                normalized_values.append(value)
                seen_values.add(value)
        bind.execute(
            quiz_answers.update()
            .where(quiz_answers.c.id == row["id"])
            .values(answer_value=",".join(normalized_values))
        )


def downgrade():
    # Original capitalization and duplicate rows cannot be reconstructed.
    pass
