from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import current_user
from app.models import Game
from app.services.recommendation_service import RecommendationService

recommendations_bp = Blueprint(
    "recommendations", __name__, url_prefix="/recommendations"
)


@recommendations_bp.get("")
def recommendations():
    user = current_user()
    genres = _query_values("genres")
    tags = _query_values("tags")
    service = RecommendationService()

    if user is not None and not (genres or tags):
        run = service.latest_for_user(user)
        popular = [
            recommendation
            for recommendation in run.recommendations
            if recommendation.recommendation_type == "popular"
        ]
        hidden = [
            recommendation
            for recommendation in run.recommendations
            if recommendation.recommendation_type == "hidden_gem"
        ]
        result = {
            "mode": user.preference_mode,
            "popular": popular,
            "hidden_gem": hidden,
            "genres": [],
            "tags": [],
        }
    else:
        result = service.recommend(
            user=user, genres=genres, tags=tags, limit=12
        )
    return render_template("recommendations.html", result=result, user=user)


@recommendations_bp.post("/interactions")
def record_interaction():
    user = current_user()
    if user is None:
        flash("Login diperlukan untuk menyimpan interaksi.", "error")
        return redirect(url_for("auth.login"))
    try:
        game_id = int(request.form.get("game_id", ""))
    except ValueError:
        flash("Game tidak valid.", "error")
        return redirect(url_for("recommendations.recommendations"))
    if Game.query.get(game_id) is None:
        flash("Game tidak ditemukan.", "error")
        return redirect(url_for("recommendations.recommendations"))
    try:
        RecommendationService.record_interaction(
            user, game_id, request.form.get("interaction_type", "")
        )
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("recommendations.recommendations"))


def _query_values(field):
    raw = request.args.get(field, "")
    return [value.strip() for value in raw.split(",") if value.strip()][:30]
