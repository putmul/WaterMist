"""Daily APScheduler integration without a separate jobs directory."""

import atexit
import logging

from app.services.game_service import GameService
from app.services.deal_service import DealService
from app.services.recommendation_service import RecommendationService
from app.services.steam_service import SteamService

log = logging.getLogger(__name__)
_scheduler = None


def start_scheduler(app):
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    from apscheduler.schedulers.background import BackgroundScheduler

    _scheduler = BackgroundScheduler(timezone=app.config["TIMEZONE"])

    def run_daily_sync():
        with app.app_context():
            release_result = GameService().sync_recently_released()
            if app.config.get("DEALS_ENABLED", True):
                deal_result = DealService().sync_daily()
                log.info(
                    "Daily sync selesai: releases=%s deals=%s",
                    release_result.get("status"),
                    deal_result.get("status"),
                )
            steam_result = SteamService().sync_all_users()
            refreshed = RecommendationService().refresh_all_users()
            log.info(
                "Steam library sync selesai: synced=%s failed=%s",
                steam_result["synced"],
                steam_result["failed"],
            )
            log.info("Recommendation refresh selesai: %s user", refreshed)

    _scheduler.add_job(
        run_daily_sync,
        trigger="cron",
        hour=app.config["SCHEDULER_HOUR"],
        minute=app.config["SCHEDULER_MINUTE"],
        id="watermist_daily_sync",
        replace_existing=True,
        misfire_grace_time=app.config["SCHEDULER_MISFIRE_GRACE_TIME"],
        max_instances=1,
    )
    _scheduler.start()
    atexit.register(
        lambda: _scheduler.shutdown(wait=False) if _scheduler.running else None
    )
    log.info(
        "Scheduler aktif: daily sync setiap hari %02d:%02d %s",
        app.config["SCHEDULER_HOUR"],
        app.config["SCHEDULER_MINUTE"],
        app.config["TIMEZONE"],
    )
    return _scheduler
