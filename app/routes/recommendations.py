from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import current_user
from app.models import Game
from app.services.recommendation_service import RecommendationService
from app.services.semantic_search_service import SemanticSearchService

recommendations_bp = Blueprint(
    "recommendations", __name__, url_prefix="/recommendations"
)


@recommendations_bp.get("")
def recommendations():
    user = current_user()
    genres = _query_values("genres")
    tags = _query_values("tags")
    service = RecommendationService()
    result = service.recommend(user=user, genres=genres, tags=tags, limit=60)
    page_size = 12
    popular_pagination = SemanticSearchService.paginate(
        result["popular"], max(request.args.get("popular_page", 1, type=int), 1), page_size
    )
    gems_pagination = SemanticSearchService.paginate(
        result["hidden_gem"], max(request.args.get("gems_page", 1, type=int), 1), page_size
    )
    active_tab = request.args.get("tab", "popular")
    if active_tab not in {"popular", "gems"}:
        active_tab = "popular"
    result["popular"] = popular_pagination.items
    result["hidden_gem"] = gems_pagination.items
    return render_template(
        "recommendations.html",
        result=result,
        user=user,
        popular_pagination=popular_pagination,
        gems_pagination=gems_pagination,
        active_tab=active_tab,
    )


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
