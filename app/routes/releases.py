from datetime import timedelta

from flask import Blueprint, current_app, render_template, request

from app.auth import current_user
from app.extensions import db
from app.models.game import Game
from app.services.recommendation_service import RecommendationService
from app.services.semantic_search_service import SemanticSearchService
from app.utils.time import local_today

releases_bp = Blueprint("releases", __name__, url_prefix="/releases")


@releases_bp.get("")
def releases():
    days = current_app.config["RECENTLY_RELEASED_DAYS"]
    latest_release_date = local_today() - timedelta(days=1)
    cutoff = latest_release_date - timedelta(days=days - 1)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 24, type=int), 1), 100)
    query_text = request.args.get("q", "").strip()[:100]
    mode = request.args.get("mode", "latest").strip()
    if mode not in {"latest", "preference"}:
        mode = "latest"

    query = db.select(Game).where(
        Game.release_date >= cutoff,
        Game.release_date <= latest_release_date,
    )
    if query_text:
        query = query.where(Game.name.ilike(f"%{query_text}%"))

    user = current_user()
    personalized = False
    preference_message = None
    if mode == "preference" and user is not None:
        candidates = db.session.scalars(
            query.order_by(Game.release_date.desc(), Game.name.asc())
        ).all()
        result = RecommendationService().recommend(
            user=user,
            candidates=candidates,
            limit=max(len(candidates), 1),
        )
        if result["has_profile"]:
            ranked_games = result["popular"]
            pagination = SemanticSearchService.paginate(ranked_games, page, per_page)
            personalized = True
        else:
            preference_message = (
                "Lengkapi preferensi quiz atau hubungkan Steam untuk mendapatkan "
                "rekomendasi yang lebih personal."
            )

    if not personalized:
        if mode == "preference" and user is None:
            preference_message = "Login untuk melihat rekomendasi berdasarkan preferensimu."
        pagination = db.paginate(
            query.order_by(Game.release_date.desc(), Game.name.asc()),
            page=page,
            per_page=per_page,
            error_out=False,
        )

    return render_template(
        "new-releases.html",
        games=pagination.items,
        pagination=pagination,
        days=days,
        q=query_text,
        per_page=per_page,
        mode=mode,
        user=user,
        personalized=personalized,
        preference_message=preference_message,
    )
