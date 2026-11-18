from flask import Blueprint, render_template

deals_bp = Blueprint("deals", __name__, url_prefix="/deals")


@deals_bp.get("")
def deals():
    return render_template("deals.html")
