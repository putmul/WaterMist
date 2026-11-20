"""Application configuration loaded from environment variables."""

import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value, default):
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _database_uri():
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url
    user = quote_plus(os.getenv("DB_USER", "root"))
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "watermist")
    credentials = f"{user}:{password}@" if password else f"{user}@"
    return f"mysql+pymysql://{credentials}{host}:{port}/{name}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")
    # The UI keeps a 30-day display window, while the daily release scraper
    # only collects games released yesterday.
    RECENTLY_RELEASED_DAYS = _as_int(os.getenv("RECENTLY_RELEASED_DAYS"), 30)
    RECENTLY_RELEASED_SCRAPE_DAYS = _as_int(
        os.getenv("RECENTLY_RELEASED_SCRAPE_DAYS"), 1
    )
    SCHEDULER_ENABLED = _as_bool(os.getenv("SCHEDULER_ENABLED"), default=True)
    SCHEDULER_HOUR = _as_int(os.getenv("SCHEDULER_HOUR"), 2)
    SCHEDULER_MINUTE = _as_int(os.getenv("SCHEDULER_MINUTE"), 0)
    SCHEDULER_MISFIRE_GRACE_TIME = _as_int(
        os.getenv("SCHEDULER_MISFIRE_GRACE_TIME"), 3600
    )

    REQUEST_TIMEOUT_SECONDS = _as_int(os.getenv("TIMEOUT_DETIK"), 15)
    REQUEST_MAX_RETRIES = _as_int(os.getenv("MAKS_COBA"), 3)
    REQUEST_DELAY_SECONDS = float(os.getenv("JEDA_DETIK", "1.0"))
    USER_AGENT = os.getenv(
        "USER_AGENT", "WaterMist/1.0 (academic project; contact: local-project)"
    )
    STEAM_429_BACKOFF_SECONDS = _as_int(
        os.getenv("STEAM_429_BACKOFF_SECONDS"), 5
    )

    STEAM_ROBOTS_URL = "https://store.steampowered.com/robots.txt"
    STEAM_SEARCH_URL = (
        "https://store.steampowered.com/search/?sort_by=Released_DESC"
        "&category1=998&page={page}"
    )
    STEAM_DETAIL_URL = "https://store.steampowered.com/app/{app_id}/"
    STEAM_MAX_PAGES = _as_int(os.getenv("STEAM_MAX_PAGES"), 100)
    STEAM_REGION = os.getenv("STEAM_REGION", "ID")
    STEAM_CURRENCY = os.getenv("STEAM_CURRENCY", "IDR")
    STEAM_DEALS_SEARCH_URL = os.getenv(
        "STEAM_DEALS_SEARCH_URL",
        "https://store.steampowered.com/search/?specials=1&category1=998&page={page}",
    )
    STEAM_DEALS_MAX_PAGES = _as_int(os.getenv("STEAM_DEALS_MAX_PAGES"), 100)
    CHEAPSHARK_ENABLED = _as_bool(os.getenv("CHEAPSHARK_ENABLED"), default=True)
    CHEAPSHARK_BASE_URL = os.getenv(
        "CHEAPSHARK_BASE_URL", "https://www.cheapshark.com/api/1.0"
    )
    CHEAPSHARK_MAX_PAGES = _as_int(os.getenv("CHEAPSHARK_MAX_PAGES"), 20)
    CHEAPSHARK_PAGE_SIZE = _as_int(os.getenv("CHEAPSHARK_PAGE_SIZE"), 60)
    CHEAPSHARK_REGION = os.getenv("CHEAPSHARK_REGION", "US")
    CHEAPSHARK_CURRENCY = os.getenv("CHEAPSHARK_CURRENCY", "USD")
    DEALS_ENABLED = _as_bool(os.getenv("DEALS_ENABLED"), default=True)
    NON_BASE_KEYWORDS = (
        "soundtrack",
        "dlc",
        "downloadable content",
        "demo",
        "playtest",
        "tool",
        "software",
        "video",
    )
    NSFW_BLACKLIST = tuple(
        value.strip().lower()
        for value in os.getenv("NSFW_BLACKLIST", "").split(",")
        if value.strip()
    )
