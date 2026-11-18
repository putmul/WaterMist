from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def dashboard():
    return render_template("dashboard.html")


@main_bp.get("/health")
def health():
    return {"status": "ok", "service": "watervapor"}
