from flask import Blueprint, render_template

recommendations_bp = Blueprint(
    "recommendations", __name__, url_prefix="/recommendations"
)


@recommendations_bp.get("")
def recommendations():
    return render_template("recommendations.html")
