"""Pure scoring functions used by the recommendation pipeline.

The functions in this module deliberately have no database dependency. That
makes the scoring contract easy to test and keeps score changes independent
from the Flask request lifecycle.
"""

import math


ALGORITHM_VERSION = "personalized-v2-hidden-gem"


def _bounded(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def _non_negative_integer(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def calculate_popularity_score(total_reviews, max_reviews):
    """Return log-normalized popularity in the range 0..1."""
    reviews = _non_negative_integer(total_reviews)
    maximum = _non_negative_integer(max_reviews)
    if reviews is None or maximum is None or maximum == 0:
        return 0.0
    return _bounded(math.log1p(reviews) / math.log1p(maximum))


def calculate_quality_score(rating_percent, total_reviews):
    """Return a review score shrunk toward neutral for small samples.

    Missing review metadata returns ``None`` rather than silently becoming a
    zero-quality game.
    """
    if rating_percent is None:
        return None
    try:
        rating = float(rating_percent)
    except (TypeError, ValueError):
        return None
    reviews = _non_negative_integer(total_reviews)
    if reviews is None or not 0 <= rating <= 100:
        return None

    review_score = rating / 100.0
    shrinkage = 2 ** (-math.log10(reviews + 1))
    score = review_score - (review_score - 0.5) * shrinkage
    return _bounded(score)


def calculate_final_score(popularity_score, quality_score):
    """Return the legacy non-personalized quality/popularity score."""
    popularity = _bounded(popularity_score or 0.0)
    quality = 0.5 if quality_score is None else _bounded(quality_score)
    return _bounded(0.5 * popularity + 0.5 * quality)


def calculate_novelty_score(popularity_score):
    return _bounded(1.0 - _bounded(popularity_score or 0.0))


def is_hidden_gem(
    rating_percent,
    total_reviews,
    popularity_score,
    *,
    min_rating_percent=80,
    min_reviews=25,
    max_reviews=10000,
    max_popularity_score=0.40,
):
    """Return whether review quality and low popularity meet the policy.

    The raw rating threshold prevents a high quality score from being enough
    on its own, while the minimum review count avoids promoting games based on
    only a handful of reviews.  Popularity is checked both relatively and by
    an absolute cap so the result remains understandable to users.
    """
    try:
        rating = float(rating_percent)
    except (TypeError, ValueError):
        return False

    reviews = _non_negative_integer(total_reviews)
    try:
        popularity = float(popularity_score)
    except (TypeError, ValueError):
        return False

    if reviews is None or not 0 <= rating <= 100:
        return False
    if reviews < int(min_reviews) or reviews > int(max_reviews):
        return False
    return rating >= float(min_rating_percent) and popularity <= float(
        max_popularity_score
    )


def calculate_personalized_score(
    fit_score,
    quality_score,
    popularity_score,
    recommendation_type="popular",
):
    """Combine explainable components for a recommendation category."""
    fit = _bounded(fit_score or 0.0)
    quality = 0.5 if quality_score is None else _bounded(quality_score)
    popularity = _bounded(popularity_score or 0.0)
    novelty = calculate_novelty_score(popularity)

    if recommendation_type == "hidden_gem":
        score = 0.70 * fit + 0.20 * quality + 0.10 * novelty
    elif recommendation_type == "hidden_gem_generic":
        score = 0.70 * quality + 0.30 * novelty
    else:
        score = 0.60 * fit + 0.25 * quality + 0.15 * popularity
    return _bounded(score)


__all__ = [
    "ALGORITHM_VERSION",
    "calculate_popularity_score",
    "calculate_quality_score",
    "calculate_final_score",
    "calculate_novelty_score",
    "calculate_personalized_score",
    "is_hidden_gem",
]
