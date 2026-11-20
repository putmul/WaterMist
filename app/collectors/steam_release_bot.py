"""Steam recently-released collector."""

import logging
import random
import re
import time
from datetime import date, datetime, time as datetime_time, timedelta
from decimal import Decimal, InvalidOperation
from urllib import robotparser
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from config import Config
from app.utils.time import local_today

from .base import BaseCollector

log = logging.getLogger(__name__)


def parse_steam_date(text):
    value = " ".join((text or "").replace("\xa0", " ").split())
    for pattern in (
        "%d %b, %Y",
        "%b %d, %Y",
        "%d %b %Y",
        "%b %d %Y",
        "%d %B, %Y",
        "%B %d, %Y",
        "%d %B %Y",
        "%B %d %Y",
    ):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def parse_discount_end_date(text, reference_date=None):
    """Parse Steam's discount expiration text into a local naive datetime."""
    value = " ".join((text or "").replace("\xa0", " ").split())
    if not value:
        return None

    month_pattern = (
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    )
    full_date_match = re.search(
        rf"(?:\d{{1,2}}\s+{month_pattern},?\s+\d{{4}}|"
        rf"{month_pattern}\s+\d{{1,2}},?\s+\d{{4}})",
        value,
        re.IGNORECASE,
    )
    date_text = full_date_match.group(0) if full_date_match else None
    parsed = parse_steam_date(date_text) if date_text else None

    if parsed is None:
        short_date_match = re.search(
            rf"(?:\d{{1,2}}\s+{month_pattern}|"
            rf"{month_pattern}\s+\d{{1,2}})(?!\s*,?\s+\d{{4}})",
            value,
            re.IGNORECASE,
        )
        if not short_date_match:
            return None
        date_text = short_date_match.group(0).replace(",", "")
        today = reference_date or local_today()
        if isinstance(today, datetime):
            today = today.date()
        for year in (today.year, today.year + 1):
            for pattern in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
                try:
                    candidate = datetime.strptime(
                        f"{date_text} {year}", pattern
                    ).date()
                except ValueError:
                    continue
                if candidate >= today or year == today.year + 1:
                    parsed = candidate
                    break
            if parsed is not None:
                break

    if parsed is None:
        return None
    # Steam exposes the expiration as a date without a time. Treat the offer
    # as valid through the end of that local calendar day.
    return datetime.combine(parsed, datetime_time(23, 59, 59))


def parse_price(text):
    value = (text or "").strip().lower()
    if not value or "free" in value or "gratis" in value:
        return Decimal("0.00") if value else None
    value = (
        value.replace("idr", "")
        .replace("rp", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace(" ", "")
    )
    match = re.search(r"[\d.,]+", value)
    if not match:
        return None
    number = match.group()
    if "," in number and "." in number:
        if number.rfind(",") > number.rfind("."):
            number = number.replace(".", "").replace(",", ".")
        else:
            number = number.replace(",", "")
    elif "," in number:
        after = number.rsplit(",", 1)[1]
        number = number.replace(",", "." if len(after) == 2 else "")
    elif "." in number and len(number.rsplit(".", 1)[1]) != 2:
        number = number.replace(".", "")
    try:
        return Decimal(number).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _text(node):
    return node.get_text(" ", strip=True) if node else ""


def _unique(values):
    result = []
    seen = set()
    for value in values:
        value = " ".join(value.split())
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _app_id_from_url(url):
    match = re.search(r"/app/(\d+)", url or "")
    return int(match.group(1)) if match else None


def parse_search_page(html, page_url=""):
    soup = BeautifulSoup(html or "", "html.parser")
    records = []
    for row in soup.select("a.search_result_row"):
        href = urljoin(page_url, row.get("href", ""))
        app_id = row.get("data-ds-appid") or _app_id_from_url(href)
        if not app_id:
            continue
        try:
            app_id = int(str(app_id).split(",")[0])
        except ValueError:
            continue
        records.append(
            {
                "app_id": app_id,
                "name": _text(row.select_one(".search_name"))
                or _text(row.select_one(".title")),
                "release_date": parse_steam_date(_text(row.select_one(".search_released"))),
                "url": href or Config.STEAM_DETAIL_URL.format(app_id=app_id),
            }
        )
    return records


def parse_app_detail(html, app_id=None, url=""):
    soup = BeautifulSoup(html or "", "html.parser")
    app_id = app_id or _app_id_from_url(url)
    release_text = _text(soup.select_one(".release_date .date")) or _text(
        soup.select_one(".date")
    )
    genres = [
        _text(node)
        for node in soup.select(
            '#genresAndManufacturer a[href*="/genre/"], '
            '.details_block a[href*="/genre/"]'
        )
    ]
    tags = [
        _text(node).lstrip("+").strip()
        for node in soup.select(".glance_tags .app_tag, .popular_tags .app_tag, a.app_tag")
    ]
    original_text = _text(soup.select_one(".discount_original_price"))
    final_text = _text(soup.select_one(".discount_final_price"))
    expiration_text = _text(
        soup.select_one(
            ".discount_expiration, .game_purchase_discount_countdown"
        )
    )
    if not original_text:
        original_text = _text(soup.select_one(".game_purchase_price"))
    if not final_text:
        final_text = _text(soup.select_one(".game_purchase_price"))
    discount_match = re.search(r"\d+", _text(soup.select_one(".discount_pct")))
    developer_nodes = soup.select("#developers_list a, .dev_row a")
    publisher_node = soup.select_one("#publishers_list a")
    image = soup.select_one("img.game_header_image_full, img.game_header_image")
    return {
        "app_id": int(app_id) if app_id is not None else None,
        "name": _text(soup.select_one(".apphub_AppName, #appHubAppName")),
        "release_date": parse_steam_date(release_text),
        "genres": _unique(genres),
        "tags": _unique(tags),
        "discount_percent": int(discount_match.group()) if discount_match else 0,
        "regular_price": parse_price(original_text),
        "sale_price": parse_price(final_text),
        "deal_end_date": parse_discount_end_date(expiration_text),
        "product_url": url or Config.STEAM_DETAIL_URL.format(app_id=app_id),
        "cover_image": image.get("src", "") if image else "",
        "description": _text(
            soup.select_one(".game_description_snippet, #game_area_description")
        ),
        "developer": _text(developer_nodes[0]) if developer_nodes else "",
        "publisher": _text(publisher_node),
        "content_type": _text(
            soup.select_one("#app_type, .app_type, .game_area_details_specs")
        ),
        "mature_content": _text(soup.select_one(".mature_content, #mature_content")),
    }


def is_base_game(record):
    text = " ".join(
        str(record.get(key, "")) for key in ("name", "description", "content_type")
    ).lower()
    if "this content requires the base application" in text:
        return False
    return not any(keyword in text for keyword in Config.NON_BASE_KEYWORDS)


def nsfw_reason(record):
    for field in ("tags", "genres", "mature_content"):
        value = str(record.get(field, "")).lower()
        for keyword in Config.NSFW_BLACKLIST:
            if keyword in value:
                return f"{field}: {keyword}"
    return None


class SteamReleaseBot(BaseCollector):
    """Fetch Steam games released within the configured 30-day window."""

    def __init__(self, session=None, delay=None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": Config.USER_AGENT})
        self.delay = Config.REQUEST_DELAY_SECONDS if delay is None else delay
        self.robots = None
        self.request_count = 0
        self.failed_urls = []
        self.last_request_at = None

    def _throttle(self):
        """Ensure at least the configured delay between Steam request starts."""
        if not self.delay:
            return
        now = time.monotonic()
        if self.last_request_at is not None:
            remaining = self.delay - (now - self.last_request_at)
            if remaining > 0:
                time.sleep(remaining)
        self.last_request_at = time.monotonic()

    def check_robots_txt(self):
        if self.robots is not None:
            return self.robots
        self._throttle()
        response = self.session.get(
            Config.STEAM_ROBOTS_URL, timeout=Config.REQUEST_TIMEOUT_SECONDS
        )
        self.request_count += 1
        response.raise_for_status()
        parser = robotparser.RobotFileParser()
        parser.set_url(Config.STEAM_ROBOTS_URL)
        parser.parse(response.text.splitlines())
        self.robots = parser
        return parser

    def _get_html(self, url):
        if not self.check_robots_txt().can_fetch(Config.USER_AGENT, url):
            raise PermissionError(f"robots.txt melarang URL: {url}")
        for attempt in range(1, Config.REQUEST_MAX_RETRIES + 1):
            try:
                self._throttle()
                response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT_SECONDS)
                self.request_count += 1
                if response.status_code == 429:
                    raise RequestException("429 Too Many Requests")
                response.raise_for_status()
                response.encoding = "utf-8"
                return response.text
            except RequestException as exc:
                if attempt == Config.REQUEST_MAX_RETRIES:
                    break
                log.warning("Steam request gagal (%d): %s", attempt, exc)
                if "429" in str(exc):
                    backoff = Config.STEAM_429_BACKOFF_SECONDS * attempt
                else:
                    backoff = 2**attempt
                time.sleep(backoff + random.random())
        self.failed_urls.append(url)
        log.error("Gagal mengambil URL Steam: %s", url)
        return None

    def find_release_candidates(self, start_date, end_date):
        self.check_robots_txt()
        for page in range(1, Config.STEAM_MAX_PAGES + 1):
            url = Config.STEAM_SEARCH_URL.format(page=page)
            html = self._get_html(url)
            if html is None:
                break
            candidates = parse_search_page(html, url)
            if not candidates:
                break
            reached_older_records = False
            for candidate in candidates:
                release_date = candidate["release_date"]
                if release_date is None:
                    continue
                if release_date < start_date:
                    reached_older_records = True
                    break
                if release_date <= end_date:
                    yield candidate
            if reached_older_records:
                break

    def scrape_app_detail(self, candidate):
        app_id = candidate["app_id"]
        url = (
            candidate.get("url")
            or candidate.get("product_url")
            or Config.STEAM_DETAIL_URL.format(app_id=app_id)
        )
        html = self._get_html(url)
        return parse_app_detail(html, app_id=app_id, url=url) if html else None

    def fetch(self, days=30, limit=None):
        self.failed_urls = []
        # Deliberately stop at yesterday: Steam's current-day release list can
        # still change during the day and should not enter the finalized feed.
        end_date = local_today() - timedelta(days=1)
        start_date = end_date - timedelta(days=days - 1)
        records = []
        seen = set()
        for candidate in self.find_release_candidates(start_date, end_date):
            app_id = candidate["app_id"]
            if app_id in seen:
                continue
            seen.add(app_id)
            try:
                record = self.scrape_app_detail(candidate)
            except Exception as exc:
                log.warning("Detail Steam App %s gagal diproses: %s", app_id, exc)
                self.failed_urls.append(candidate.get("url") or str(app_id))
                continue
            # The search result has a usable release date even when the detail
            # page omits it (for example, because Steam returns an age gate).
            # Keep that date so a valid detail response is not discarded only
            # because the detail markup is incomplete.
            if record and not record.get("release_date"):
                record["release_date"] = candidate.get("release_date")
            release_date = record.get("release_date") if record else None
            if not record or not release_date or not (start_date <= release_date <= end_date):
                continue
            if not is_base_game(record) or nsfw_reason(record):
                continue
            records.append(record)
            if limit and len(records) >= limit:
                break
        return records

    def normalize(self, record):
        sale_price = record.get("sale_price")
        regular_price = record.get("regular_price")
        if sale_price is None:
            sale_price = regular_price
        if regular_price is None:
            regular_price = sale_price
        return {
            "steam_app_id": str(record.get("app_id")) if record.get("app_id") else None,
            "name": (record.get("name") or "").strip(),
            "description": record.get("description") or None,
            "release_date": record.get("release_date"),
            "cover_image": record.get("cover_image") or None,
            "developer": record.get("developer") or None,
            "publisher": record.get("publisher") or None,
            "genres": _unique(record.get("genres", [])),
            "tags": _unique(record.get("tags", [])),
            "product_url": record.get("product_url"),
            "external_product_id": str(record.get("app_id")) if record.get("app_id") else None,
            "region": Config.STEAM_REGION,
            "currency": Config.STEAM_CURRENCY,
            "regular_price": regular_price,
            "sale_price": sale_price,
            "discount_percent": record.get("discount_percent", 0),
            "deal_end_date": record.get("deal_end_date"),
            "source": "steam_release_bot",
        }


SteamScraper = SteamReleaseBot
