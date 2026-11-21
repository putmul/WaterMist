"""Build preference vectors from anonymous choices or persisted user data."""

import math

from app.recommendation.similarity import feature_choice_vector, game_feature_vector


def build_profile_from_choices(genres=None, tags=None):
    return feature_choice_vector(genres=genres, tags=tags)


def _add_game_signal(profile, game, weight):
    for feature, value in game_feature_vector(game).items():
        profile[feature] = profile.get(feature, 0.0) + value * weight


def build_profile_from_user(user):
    """Build a profile from explicit preferences, favorites, and playtime.

    Steam-owned games are treated as weak signals when they have no playtime;
    this avoids treating every free or bundled game as a strong positive.
    """
    profile = {}
    for preference in user.preferences:
        key = f"{preference.feature_type}:{preference.feature_key.lower().strip()}"
        profile[key] = profile.get(key, 0.0) + max(
            0.0, preference.preference_score * preference.confidence
        )

    for favorite in user.favorites:
        _add_game_signal(profile, favorite.game, 1.0)

    playtimes = [max(0, owned.playtime_minutes or 0) for owned in user.owned_games]
    max_playtime = max(playtimes, default=0)
    for owned in user.owned_games:
        if owned.game is None:
            continue
        if max_playtime:
            weight = math.log1p(owned.playtime_minutes or 0) / math.log1p(
                max_playtime
            )
        else:
            weight = 0.05
        _add_game_signal(profile, owned.game, weight)

    # A favorite or a click is a positive signal, while dismiss is handled as
    # an exclusion by the ranking service rather than polluting the profile.
    for interaction in user.interactions:
        if interaction.interaction_type == "favorite":
            _add_game_signal(profile, interaction.game, 0.75)
        elif interaction.interaction_type == "click_deal":
            _add_game_signal(profile, interaction.game, 0.10)
        elif interaction.interaction_type == "view":
            _add_game_signal(profile, interaction.game, 0.03)

    return profile


__all__ = ["build_profile_from_choices", "build_profile_from_user"]
