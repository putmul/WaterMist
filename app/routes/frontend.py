"""Static assets for the primary frontend in ``/web``."""

from pathlib import Path

from flask import Blueprint

_WEB_STATIC = Path(__file__).resolve().parents[2] / "web" / "static"

frontend_bp = Blueprint(
    "frontend",
    __name__,
    static_folder=str(_WEB_STATIC),
    static_url_path="/web-static",
)
