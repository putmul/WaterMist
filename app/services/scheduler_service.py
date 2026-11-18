"""Daily APScheduler integration without a separate jobs directory."""

import atexit
import logging

from app.services.game_service import GameService

log = logging.getLogger(__name__)
_scheduler = None


def start_scheduler(app):
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    from apscheduler.schedulers.background import BackgroundScheduler

    _scheduler = BackgroundScheduler(timezone=app.config["TIMEZONE"])

    def run_release_sync():
        with app.app_context():
            GameService().sync_recently_released()

    _scheduler.add_job(
        run_release_sync,
        trigger="cron",
        hour=app.config["SCHEDULER_HOUR"],
        minute=app.config["SCHEDULER_MINUTE"],
        id="steam_releases",
        replace_existing=True,
        misfire_grace_time=app.config["SCHEDULER_MISFIRE_GRACE_TIME"],
        max_instances=1,
    )
    _scheduler.start()
    atexit.register(
        lambda: _scheduler.shutdown(wait=False) if _scheduler.running else None
    )
    log.info(
        "Scheduler aktif: Steam releases setiap hari %02d:%02d %s",
        app.config["SCHEDULER_HOUR"],
        app.config["SCHEDULER_MINUTE"],
        app.config["TIMEZONE"],
    )
    return _scheduler
