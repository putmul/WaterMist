"""Backward-compatible import for the migrated Steam release collector.

The application code now lives in ``app.collectors.steam_release_bot``.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.collectors.steam_release_bot import (  # noqa: E402,F401
    SteamReleaseBot,
    SteamScraper,
    is_base_game,
    nsfw_reason,
    parse_app_detail,
    parse_price,
    parse_search_page,
    parse_steam_date,
)

__all__ = [
    "SteamReleaseBot",
    "SteamScraper",
    "is_base_game",
    "nsfw_reason",
    "parse_app_detail",
    "parse_price",
    "parse_search_page",
    "parse_steam_date",
]
