"""Application configuration loaded from environment variables."""

import os
from decimal import Decimal, InvalidOperation
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


def _as_exchange_rates(value, default=None):
    """Parse rates expressed as ``CURRENCY=base-currency value`` pairs."""
    rates = dict(default or {})
    if not value:
        return rates
    for item in value.split(","):
        if "=" not in item:
            continue
        currency, raw_rate = (part.strip().upper() for part in item.split("=", 1))
        if not currency:
            continue
        try:
            rate = Decimal(raw_rate)
        except (InvalidOperation, TypeError, ValueError):
            continue
        if rate > 0:
            rates[currency] = rate
    return rates


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
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _as_bool(os.getenv("SESSION_COOKIE_SECURE"), default=False)
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
    STEAM_API_KEY = os.getenv("STEAM_API_KEY", "")
    STEAM_API_BASE_URL = os.getenv(
        "STEAM_API_BASE_URL", "https://api.steampowered.com"
    )
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
    PRICE_COMPARISON_CURRENCY = os.getenv("PRICE_COMPARISON_CURRENCY", "IDR").upper()
    # Rates are expressed as base-currency units per one unit of the source
    # currency, e.g. USD=16000 means 1 USD = 16,000 IDR.
    PRICE_EXCHANGE_RATES = _as_exchange_rates(
        os.getenv("PRICE_EXCHANGE_RATES"),
        {"IDR": Decimal("1"), "USD": Decimal("16000")},
    )
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
    DEFAULT_NSFW_BLACKLIST = (
        "adult only",
        "sexual content",
        "nudity",
        "hentai",
        "nsfw",
        "pornography",
        "explicit sexual content",
    )
    NSFW_BLACKLIST = tuple(
        value.strip().lower()
        for value in os.getenv(
            "NSFW_BLACKLIST", ",".join(DEFAULT_NSFW_BLACKLIST)
        ).split(",")
        if value.strip()
    )
    SEMANTIC_SEARCH_ENABLED = _as_bool(
        os.getenv("SEMANTIC_SEARCH_ENABLED"), default=True
    )
    SEMANTIC_EMBEDDING_MODEL = os.getenv(
        "SEMANTIC_EMBEDDING_MODEL",
        "paraphrase-multilingual-MiniLM-L12-v2",
    )
    SEMANTIC_SEARCH_MIN_SCORE = float(
        os.getenv("SEMANTIC_SEARCH_MIN_SCORE", "0.35")
    )
    SEMANTIC_SEARCH_TOP_K = _as_int(os.getenv("SEMANTIC_SEARCH_TOP_K"), 100)
    SEMANTIC_SEARCH_DISPLAY_LIMIT = min(
        max(_as_int(os.getenv("SEMANTIC_SEARCH_DISPLAY_LIMIT"), 12), 10), 20
    )
    SEMANTIC_EMBEDDING_BATCH_SIZE = _as_int(
        os.getenv("SEMANTIC_EMBEDDING_BATCH_SIZE"), 32
    )
    SEMANTIC_DEFAULT_CURRENCY = os.getenv("SEMANTIC_DEFAULT_CURRENCY", STEAM_CURRENCY)
