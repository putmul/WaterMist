from flask import Blueprint, abort, render_template

from app.services.game_detail_service import GameDetailService


games_bp = Blueprint("games", __name__)


@games_bp.get("/games/<int:game_id>")
def detail(game_id):
    view = GameDetailService.get_game_detail(game_id)
    if view is None:
        abort(404)
    return render_template("game_detail.html", **view)
