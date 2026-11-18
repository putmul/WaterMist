from datetime import date, timedelta
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, render_template, request

from app.extensions import db
from app.models.game import Game

releases_bp = Blueprint("releases", __name__, url_prefix="/releases")


@releases_bp.get("")
def releases():
    days = current_app.config["RECENTLY_RELEASED_DAYS"]
    today = datetime.now(ZoneInfo(current_app.config["TIMEZONE"])).date()
    cutoff = today - timedelta(days=days - 1)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 24, type=int), 1), 100)
    pagination = db.paginate(
        db.select(Game)
        .where(Game.release_date >= cutoff)
        .order_by(Game.release_date.desc(), Game.name.asc()),
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return render_template(
        "releases.html", games=pagination.items, pagination=pagination, days=days
    )
