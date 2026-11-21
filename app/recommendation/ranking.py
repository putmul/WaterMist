"""Candidate filtering and explainable recommendation ranking."""

from app.recommendation.scoring import (
    calculate_novelty_score,
    calculate_personalized_score,
    calculate_popularity_score,
    calculate_quality_score,
)
from app.recommendation.similarity import cosine_similarity, game_feature_vector


def rank_games(games, profile, owned_game_ids=None, dismissed_game_ids=None, limit=20):
    """Return scored game dictionaries for both recommendation categories."""
    owned = set(owned_game_ids or ())
    dismissed = set(dismissed_game_ids or ())
    candidates = [
        game for game in games if game.id not in owned and game.id not in dismissed
    ]
    max_reviews = max(
        (game.steam_rating_count or 0 for game in candidates), default=0
    )
    scored = []
    for game in candidates:
        popularity = calculate_popularity_score(game.steam_rating_count, max_reviews)
        quality = calculate_quality_score(
            game.steam_rating_percent, game.steam_rating_count
        )
        fit = cosine_similarity(profile, game_feature_vector(game))
        scored.append(
            {
                "game": game,
                "fit_score": fit,
                "quality_score": quality,
                "popularity_score": popularity,
                "novelty_score": calculate_novelty_score(popularity),
                "popular_score": calculate_personalized_score(
                    fit, quality, popularity, "popular"
                ),
                "hidden_gem_score": calculate_personalized_score(
                    fit, quality, popularity, "hidden_gem"
                ),
            }
        )

    popular = sorted(
        scored, key=lambda item: item["popular_score"], reverse=True
    )[:limit]
    hidden_candidates = [
        item
        for item in scored
        if item["popularity_score"] <= 0.40
        and item["fit_score"] >= 0.05
        and item["quality_score"] is not None
        and item["quality_score"] >= 0.55
    ]
    hidden = sorted(
        hidden_candidates, key=lambda item: item["hidden_gem_score"], reverse=True
    )[:limit]
    return {"popular": popular, "hidden_gem": hidden, "max_reviews": max_reviews}


__all__ = ["rank_games"]
