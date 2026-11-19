"""Timezone-aware application clock helpers.

Database timestamp columns are currently timezone-naive. We therefore store
the configured local time as a naive value instead of using UTC, which keeps
the values displayed by MySQL and the Flask UI consistent.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context

from config import Config


def _timezone():
    timezone_name = (
        current_app.config.get("TIMEZONE", Config.TIMEZONE)
        if has_app_context()
        else Config.TIMEZONE
    )
    return ZoneInfo(timezone_name)


def local_now():
    """Return configured local time as a naive datetime for DB columns."""
    return datetime.now(_timezone()).replace(tzinfo=None)


def local_today():
    """Return today's date in the configured application timezone."""
    return datetime.now(_timezone()).date()
