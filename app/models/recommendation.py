"""Persisted recommendation runs and explainable ranked results."""

from app.extensions import db
from app.utils.time import local_now


BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class RecommendationRun(db.Model):
    __tablename__ = "recommendation_runs"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    preference_mode = db.Column(db.String(20), nullable=False)
    algorithm_version = db.Column(db.String(32), nullable=False)
    profile_version = db.Column(db.String(32), nullable=False)
    max_reviews = db.Column(BIGINT, nullable=False, default=0)
    generated_at = db.Column(db.DateTime, nullable=False, default=local_now, index=True)
    status = db.Column(db.String(20), nullable=False, default="success")

    recommendations = db.relationship(
        "Recommendation", back_populates="run", cascade="all, delete-orphan"
    )


class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    run_id = db.Column(
        BIGINT,
        db.ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_id = db.Column(
        BIGINT, db.ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recommendation_type = db.Column(db.String(20), nullable=False, index=True)
    rank = db.Column(db.Integer, nullable=False)
    fit_score = db.Column(db.Float, nullable=False)
    quality_score = db.Column(db.Float)
    popularity_score = db.Column(db.Float, nullable=False)
    novelty_score = db.Column(db.Float, nullable=False)
    recommendation_score = db.Column(db.Float, nullable=False)
    reason_code = db.Column(db.String(100))
    reason_text = db.Column(db.Text)
    algorithm_version = db.Column(db.String(32), nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, default=local_now)

    run = db.relationship("RecommendationRun", back_populates="recommendations")
    game = db.relationship("Game")


__all__ = ["RecommendationRun", "Recommendation"]
