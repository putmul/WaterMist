"""Authenticated user profile and personalization settings."""

import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import current_user, login_required
from app.extensions import db
from app.models import UserFavorite, UserOwnedGame, UserPreference
from app.services.recommendation_service import RecommendationService
from app.services.steam_service import SteamProfilePrivateError, SteamService, SteamServiceError


log = logging.getLogger(__name__)
profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.get("")
@login_required
def profile():
    user = current_user()
    owned_games = UserOwnedGame.query.filter_by(user_id=user.id).all()
    mapped_games = [owned for owned in owned_games if owned.game is not None]
    metadata_ready = sum(
        bool(owned.game.genres or owned.game.tags or owned.game.developer)
        for owned in mapped_games
    )
    preferences = (
        UserPreference.query.filter(
            UserPreference.user_id == user.id,
            UserPreference.source.in_({"quiz", "steam", "favorite", "interaction"}),
        )
        .order_by(UserPreference.source, UserPreference.preference_score.desc())
        .all()
    )
    favorite_rows = (
        UserFavorite.query.filter_by(user_id=user.id)
        .order_by(UserFavorite.created_at.desc())
        .limit(4)
        .all()
    )
    favorite_games = [favorite.game for favorite in favorite_rows if favorite.game]
    genre_scores = {}
    for preference in preferences:
        if preference.feature_type.lower() in {"genre", "genres"}:
            genre_scores[preference.feature_key] = genre_scores.get(
                preference.feature_key, 0
            ) + max(preference.preference_score, 0)
    genre_preferences = sorted(
        genre_scores.items(), key=lambda item: item[1], reverse=True
    )[:4]
    genre_total = sum(score for _, score in genre_preferences)
    if genre_total:
        genre_chart = [
            {
                "label": label,
                "percent": round(score / genre_total * 100),
            }
            for label, score in genre_preferences
        ]
    else:
        genre_chart = []
    return render_template(
        "profile.html",
        user=user,
        preferences=preferences,
        owned_total=len(owned_games),
        mapped_total=len(mapped_games),
        metadata_ready=metadata_ready,
        steam_preference_total=sum(
            preference.source == "steam" for preference in preferences
        ),
        favorite_games=favorite_games,
        genre_chart=genre_chart,
    )


@profile_bp.post("/steam/connect")
@login_required
def connect_steam():
    user = current_user()
    try:
        SteamService().link_profile(user, request.form.get("steam_profile", ""))
    except SteamProfilePrivateError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("profile.profile"))
    except SteamServiceError as exc:
        flash(str(exc), "error")
        return redirect(url_for("profile.profile"))

    try:
        RecommendationService().generate_for_user(user)
    except Exception:
        db.session.rollback()
        log.exception("Recommendation awal gagal setelah Steam terhubung untuk user %s", user.id)
        flash(
            "Steam berhasil ditautkan. Recommendation akan diperbarui pada sinkronisasi berikutnya.",
            "warning",
        )
    else:
        flash("Steam berhasil ditautkan dan recommendation langsung diperbarui.", "success")
    return redirect(url_for("profile.profile"))


@profile_bp.post("/steam/disconnect")
@login_required
def disconnect_steam():
    user = current_user()
    SteamService().disconnect(user)
    try:
        RecommendationService().generate_for_user(user)
    except Exception:
        db.session.rollback()
        log.exception("Recommendation gagal setelah Steam diputus untuk user %s", user.id)
        flash("Steam diputus. Recommendation akan diperbarui pada sinkronisasi berikutnya.", "warning")
    else:
        flash("Steam diputus dan recommendation kembali memakai profil quiz.", "success")
    return redirect(url_for("profile.profile"))
