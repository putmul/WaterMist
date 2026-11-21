"""WaterMist Flask application factory."""

import logging

from flask import Flask

from config import Config

from .extensions import db, migrate


def create_app(config_object=None, start_scheduler=False):
    app = Flask(__name__)
    if isinstance(config_object, dict):
        app.config.from_object(Config)
        app.config.from_mapping(config_object)
    else:
        app.config.from_object(config_object or Config)
    logging.basicConfig(
        level=getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db.init_app(app)
    migrate.init_app(app, db)

    from . import models  # noqa: F401
    from .routes.deals import deals_bp
    from .routes.auth import auth_bp, onboarding_bp
    from .routes.main import main_bp
    from .routes.profile import profile_bp
    from .routes.recommendations import recommendations_bp
    from .routes.releases import releases_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(deals_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(releases_bp)
    app.register_blueprint(recommendations_bp)

    if start_scheduler and app.config.get("SCHEDULER_ENABLED", True):
        from .services.scheduler_service import start_scheduler as start_scheduler_service

        start_scheduler_service(app)
    return app
