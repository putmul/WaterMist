"""Materialize preference profiles from persisted user data."""

import math

from app.extensions import db
from app.models import UserFavorite, UserInteraction, UserOwnedGame, UserPreference
from app.recommendation.similarity import game_feature_vector


class PreferenceProfileService:
    """Rebuild source-specific preference signals in ``user_preferences``."""

    STEAM_SOURCE = "steam"

    def rebuild_steam_preferences(self, user_id):
        owned_games = UserOwnedGame.query.filter_by(user_id=user_id).all()
        mapped_games = [owned for owned in owned_games if owned.game is not None]
        raw_signals = {}
        playtimes = [max(0, owned.playtime_minutes or 0) for owned in mapped_games]
        max_playtime = max(playtimes, default=0)

        for owned in mapped_games:
            if max_playtime:
                weight = math.log1p(owned.playtime_minutes or 0) / math.log1p(
                    max_playtime
                )
            else:
                # An owned game with no playtime is weak evidence, not a strong
                # positive preference.
                weight = 0.05
            for feature, feature_weight in game_feature_vector(owned.game).items():
                raw_signals[feature] = raw_signals.get(feature, 0.0) + (
                    weight * feature_weight
                )

        UserPreference.query.filter_by(
            user_id=user_id, source=self.STEAM_SOURCE
        ).delete()

        if not raw_signals:
            return 0

        maximum = max(raw_signals.values()) or 1.0
        mapped_count = len(mapped_games)
        total_count = len(owned_games) or mapped_count or 1
        confidence = min(1.0, mapped_count / total_count)
        created = 0
        for feature, raw_score in sorted(
            raw_signals.items(), key=lambda item: item[1], reverse=True
        ):
            feature_type, feature_key = feature.split(":", 1)
            db.session.add(
                UserPreference(
                    user_id=user_id,
                    feature_type=feature_type,
                    feature_key=feature_key,
                    preference_score=min(1.0, raw_score / maximum),
                    source=self.STEAM_SOURCE,
                    confidence=confidence,
                    profile_version="v1",
                )
            )
            created += 1
        db.session.flush()
        return created

    def rebuild_behavioral_preferences(self, user_id):
        """Materialize favorite and interaction signals from database events."""
        favorites = UserFavorite.query.filter_by(user_id=user_id).all()
        interactions = UserInteraction.query.filter_by(user_id=user_id).all()
        signals = {"favorite": {}, "interaction": {}}

        for favorite in favorites:
            if favorite.game is None:
                continue
            for feature, weight in game_feature_vector(favorite.game).items():
                signals["favorite"][feature] = signals["favorite"].get(feature, 0.0) + weight

        interaction_weights = {
            "favorite": 0.75,
            "click_deal": 0.10,
            "view": 0.03,
        }
        for interaction in interactions:
            weight = interaction_weights.get(interaction.interaction_type, 0.0)
            if not weight or interaction.game is None:
                continue
            for feature, feature_weight in game_feature_vector(interaction.game).items():
                signals["interaction"][feature] = (
                    signals["interaction"].get(feature, 0.0)
                    + feature_weight * weight
                )

        created = 0
        for source, raw_signals in signals.items():
            UserPreference.query.filter_by(user_id=user_id, source=source).delete()
            if not raw_signals:
                continue
            maximum = max(raw_signals.values()) or 1.0
            for feature, raw_score in raw_signals.items():
                feature_type, feature_key = feature.split(":", 1)
                db.session.add(
                    UserPreference(
                        user_id=user_id,
                        feature_type=feature_type,
                        feature_key=feature_key,
                        preference_score=min(1.0, raw_score / maximum),
                        source=source,
                        confidence=1.0,
                        profile_version="v1",
                    )
                )
                created += 1
        db.session.flush()
        return created


__all__ = ["PreferenceProfileService"]
