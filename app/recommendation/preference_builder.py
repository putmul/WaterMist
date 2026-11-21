"""Build preference vectors from anonymous choices or persisted user data."""

from app.recommendation.similarity import feature_choice_vector
from app.models import UserPreference


def build_profile_from_choices(genres=None, tags=None):
    return feature_choice_vector(genres=genres, tags=tags)


def build_profile_from_user(user):
    """Build a vector only from materialized preference rows.

    Steam playtime is converted into ``user_preferences`` by
    ``PreferenceProfileService`` before this function is called. Keeping this
    function database-row based makes recommendation results reproducible.
    """
    profile = {}
    active_sources = {"favorite", "interaction"}
    active_sources.add("steam" if user.preference_mode == "steam" else "quiz")
    preferences = UserPreference.query.filter(
        UserPreference.user_id == user.id,
        UserPreference.source.in_(active_sources),
    ).all()
    for preference in preferences:
        key = f"{preference.feature_type}:{preference.feature_key.lower().strip()}"
        profile[key] = profile.get(key, 0.0) + max(
            0.0, preference.preference_score * preference.confidence
        )
    return profile


__all__ = ["build_profile_from_choices", "build_profile_from_user"]
