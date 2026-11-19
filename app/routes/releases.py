from datetime import timedelta

from flask import Blueprint, current_app, render_template, request

from app.extensions import db
from app.models.game import Game
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
    query = db.select(Game).where(
        Game.release_date >= cutoff,
        Game.release_date <= latest_release_date,
    )
    if query_text:
        query = query.where(Game.name.ilike(f"%{query_text}%"))
    pagination = db.paginate(
        query.order_by(Game.release_date.desc(), Game.name.asc()),
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return render_template(
        "releases.html",
        games=pagination.items,
        pagination=pagination,
        days=days,
        q=query_text,
        per_page=per_page,
    )
