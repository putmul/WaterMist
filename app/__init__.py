"""WaterMist Flask application factory."""

import logging
from pathlib import Path

from flask import Flask
from jinja2 import ChoiceLoader, FileSystemLoader

from config import Config

from .extensions import db, migrate


def create_app(config_object=None, start_scheduler=False):
    app = Flask(__name__)
    if isinstance(config_object, dict):
        app.config.from_object(Config)
        app.config.from_mapping(config_object)
    else:
        app.config.from_object(config_object or Config)
    # Prefer the primary /web templates while retaining app/templates as a
    # fallback for auth, profile, and prototype pages that are out of scope.
    web_templates = Path(app.root_path).parent / "web" / "template"
    app.jinja_loader = ChoiceLoader(
        [FileSystemLoader(str(web_templates)), app.jinja_loader]
    )
    logging.basicConfig(
        level=getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db.init_app(app)
    migrate.init_app(app, db)

    from .utils.money import format_idr

    app.jinja_env.filters["idr"] = format_idr

    @app.context_processor
    def inject_auth_user():
        from .auth import current_user

        return {"auth_user": current_user()}

    from . import models  # noqa: F401
    from .routes.deals import deals_bp
    from .routes.frontend import frontend_bp
    from .routes.games import games_bp
    from .routes.auth import auth_bp, onboarding_bp
    from .routes.main import main_bp
    from .routes.profile import profile_bp
    from .routes.recommendations import recommendations_bp
    from .routes.releases import releases_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(frontend_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(deals_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(releases_bp)
    app.register_blueprint(recommendations_bp)

    if start_scheduler and app.config.get("SCHEDULER_ENABLED", True):
        from .services.scheduler_service import start_scheduler as start_scheduler_service

        start_scheduler_service(app)
    return app
