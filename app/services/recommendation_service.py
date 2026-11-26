"""Recommendation orchestration for anonymous and authenticated profiles."""

import logging

from flask import current_app
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import (
    Game,
    Recommendation,
    RecommendationRun,
    User,
    UserFavorite,
    UserInteraction,
)
from app.recommendation.preference_builder import (
    build_profile_from_choices,
    build_profile_from_user,
)
from app.recommendation.ranking import rank_games
from app.recommendation.scoring import ALGORITHM_VERSION
from app.services.preference_service import PreferenceProfileService
from app.utils.time import local_now


log = logging.getLogger(__name__)


class RecommendationService:
    """Build, persist, and read explainable recommendation results."""

    def recommend(self, user=None, genres=None, tags=None, limit=12, candidates=None):
        if user is not None:
            profile = (
                build_profile_from_choices(genres=genres, tags=tags)
                if (genres or tags)
                else build_profile_from_user(user)
            )
            mode = "search" if (genres or tags) else user.preference_mode
            owned_ids = [owned.game_id for owned in user.owned_games if owned.game_id]
            dismissed_ids = [
                interaction.game_id
                for interaction in user.interactions
                if interaction.interaction_type == "dismiss_recommendation"
            ]
        else:
            profile = build_profile_from_choices(genres=genres, tags=tags)
            mode = "search"
            owned_ids = []
            dismissed_ids = []

        ranked = rank_games(
            list(candidates)
            if candidates is not None
            else Game.query.options(
                selectinload(Game.genres), selectinload(Game.tags)
            ).all(),
            profile,
            owned_game_ids=owned_ids,
            dismissed_game_ids=dismissed_ids,
            limit=limit,
            hidden_gem_config={
                "min_rating_percent": current_app.config.get(
                    "HIDDEN_GEM_MIN_RATING_PERCENT", 80
                ),
                "min_reviews": current_app.config.get("HIDDEN_GEM_MIN_REVIEWS", 25),
                "max_reviews": current_app.config.get(
                    "HIDDEN_GEM_MAX_REVIEWS", 10000
                ),
                "max_popularity_score": current_app.config.get(
                    "HIDDEN_GEM_MAX_POPULARITY_SCORE", 0.40
                ),
                "min_fit": current_app.config.get("HIDDEN_GEM_MIN_FIT", 0.05),
            },
        )
        ranked["mode"] = mode
        ranked["genres"] = list(genres or ())
        ranked["tags"] = list(tags or ())
        ranked["has_profile"] = bool(profile)
        return ranked

    def generate_for_user(self, user, limit=12):
        results = self.recommend(user=user, limit=limit)
        run = RecommendationRun(
            user_id=user.id,
            preference_mode=user.preference_mode,
            algorithm_version=ALGORITHM_VERSION,
            profile_version="v1",
            max_reviews=results["max_reviews"],
            generated_at=local_now(),
            status="success",
        )
        db.session.add(run)
        db.session.flush()

        for recommendation_type in ("popular", "hidden_gem"):
            key = "popular" if recommendation_type == "popular" else "hidden_gem"
            for position, item in enumerate(results[key], start=1):
                reason_code, reason_text = self._reason(
                    item, user.preference_mode, recommendation_type
                )
                db.session.add(
                    Recommendation(
                        run_id=run.id,
                        user_id=user.id,
                        game_id=item["game"].id,
                        recommendation_type=recommendation_type,
                        rank=position,
                        fit_score=item["fit_score"],
                        quality_score=item["quality_score"],
                        popularity_score=item["popularity_score"],
                        novelty_score=item["novelty_score"],
                        recommendation_score=item[f"{key}_score"],
                        reason_code=reason_code,
                        reason_text=reason_text,
                        algorithm_version=ALGORITHM_VERSION,
                        generated_at=run.generated_at,
                    )
                )
        db.session.commit()
        return run

    def latest_for_user(self, user, limit=12):
        run = (
            RecommendationRun.query.filter_by(user_id=user.id, status="success")
            .order_by(RecommendationRun.generated_at.desc())
            .first()
        )
        if run is None:
            return self.generate_for_user(user, limit=limit)
        return run

    def refresh_all_users(self, limit=12):
        count = 0
        for user in User.query.filter_by(status="active").all():
            try:
                self.generate_for_user(user, limit=limit)
                count += 1
            except Exception:
                db.session.rollback()
                log.exception("Gagal membuat recommendation untuk user %s", user.id)
        return count

    @staticmethod
    def record_interaction(user, game_id, interaction_type):
        allowed = {"view", "favorite", "click_deal", "dismiss_recommendation"}
        if interaction_type not in allowed:
            raise ValueError("interaction_type tidak valid")
        interaction = UserInteraction(
            user_id=user.id, game_id=game_id, interaction_type=interaction_type
        )
        db.session.add(interaction)
        if interaction_type == "favorite":
            favorite = UserFavorite.query.filter_by(
                user_id=user.id, game_id=game_id
            ).one_or_none()
            if favorite is None:
                db.session.add(UserFavorite(user_id=user.id, game_id=game_id))
        db.session.flush()
        PreferenceProfileService().rebuild_behavioral_preferences(user.id)
        db.session.commit()
        return interaction

    @staticmethod
    def _reason(item, mode, recommendation_type=None):
        if recommendation_type == "hidden_gem":
            game = item["game"]
            return (
                "hidden_gem_quality_low_popularity",
                (
                    f"Review positif {game.steam_rating_percent}% dengan "
                    f"{game.steam_rating_count:,} review, tetapi belum terlalu populer."
                ),
            )
        if mode == "steam":
            return (
                "steam_profile",
                "Cocok dengan genre dan tag dari game yang sering kamu mainkan di Steam.",
            )
        if mode == "quiz":
            return (
                "quiz_profile",
                "Cocok dengan preferensi genre dan tag yang kamu pilih.",
            )
        return (
            "search_preferences",
            "Cocok dengan pilihan genre dan tag pada pencarian ini.",
        )


__all__ = ["RecommendationService"]
