"""CheapShark REST API adapter."""

import logging
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, unquote

import requests
from requests.exceptions import RequestException

from config import Config
from app.utils.time import parse_local_datetime

from .base import BaseCollector


class CheapSharkClient(BaseCollector):
    def __init__(self, session=None, delay=None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": Config.USER_AGENT})
        self.delay = Config.REQUEST_DELAY_SECONDS if delay is None else delay
        self.stores = {}
        self.last_fetch_complete = False

    def _request(self, path, params=None):
        url = f"{Config.CHEAPSHARK_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        for attempt in range(1, Config.REQUEST_MAX_RETRIES + 1):
            try:
                if self.delay:
                    time.sleep(self.delay)
                response = self.session.get(
                    url, params=params, timeout=Config.REQUEST_TIMEOUT_SECONDS
                )
                if response.status_code == 429:
                    raise RequestException("429 Too Many Requests")
                response.raise_for_status()
                return response.json()
            except (RequestException, ValueError) as exc:
                if attempt == Config.REQUEST_MAX_RETRIES:
                    raise RuntimeError(f"CheapShark request gagal: {url}") from exc
                logging.getLogger(__name__).warning(
                    "CheapShark request gagal (%d): %s", attempt, exc
                )
                time.sleep(2**attempt)

    @staticmethod
    def _price(value):
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            return None

    @staticmethod
    def _non_negative_integer(value):
        if value in (None, "") or isinstance(value, bool):
            return None
        try:
            parsed = int(str(value).strip())
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    @classmethod
    def _rating_percent(cls, value):
        parsed = cls._non_negative_integer(value)
        return min(parsed, 100) if parsed is not None else None

    @staticmethod
    def _release_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if value in (None, ""):
            return None

        text = str(value).strip()
        for format_value in ("%Y-%m-%d", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(text, format_value).date()
            except ValueError:
                continue

        try:
            timestamp = int(text)
            return datetime.fromtimestamp(timestamp).date()
        except (TypeError, ValueError, OverflowError, OSError):
            return None

    def fetch_stores(self):
        records = self._request("stores")
        self.stores = {
            str(record.get("storeID")): record
            for record in records
            if record.get("storeID") is not None
        }
        return records

    def fetch_deals(self, page=0, page_size=None, sort_by="Savings"):
        return self._request(
            "deals",
            {
                "pageNumber": page,
                "pageSize": page_size or Config.CHEAPSHARK_PAGE_SIZE,
                "sortBy": sort_by,
            },
        )

    def fetch_games_by_title(self, title):
        return self._request("games", {"title": title})

    def fetch_games_by_steam_app_id(self, app_id):
        return self._request("games", {"steamAppID": app_id})

    def fetch_game_deals(self, game_id):
        return self._request("games", {"id": game_id})

    def fetch_deal(self, deal_id):
        # CheapShark returns deal IDs already percent-encoded. Decode once so
        # requests does not encode the percent signs a second time.
        return self._request("deals", {"id": unquote(str(deal_id))})

    def fetch(self, **kwargs):
        page_size = kwargs.get("page_size") or Config.CHEAPSHARK_PAGE_SIZE
        max_pages = kwargs.get("max_pages") or Config.CHEAPSHARK_MAX_PAGES
        records = []
        self.last_fetch_complete = False
        for page in range(max_pages):
            page_records = self.fetch_deals(page=page, page_size=page_size)
            if not page_records:
                self.last_fetch_complete = True
                break
            records.extend(page_records)
            if len(page_records) < page_size:
                self.last_fetch_complete = True
                break
        return records

    def normalize(self, record):
        store_id = str(record.get("storeID")) if record.get("storeID") is not None else None
        store = self.stores.get(store_id, {})
        deal_id = record.get("dealID")
        deal_url = record.get("dealURL") or record.get("dealUrl")
        if not deal_url and deal_id:
            deal_url = (
                "https://www.cheapshark.com/redirect?dealID="
                + quote(unquote(str(deal_id)), safe="")
            )
        normal_price = self._price(record.get("normalPrice"))
        sale_price = self._price(record.get("salePrice"))
        savings = self._price(record.get("savings"))
        if savings is not None:
            savings = max(Decimal("0"), min(Decimal("100"), savings))
        if savings is None and normal_price and normal_price > 0 and sale_price is not None:
            savings = ((normal_price - sale_price) / normal_price * 100).quantize(
                Decimal("0.01")
            )
        is_on_sale = record.get("isOnSale", record.get("is_on_sale", True))
        if isinstance(is_on_sale, str):
            is_on_sale = is_on_sale.strip().lower() in {"1", "true", "yes", "on"}
        else:
            is_on_sale = bool(is_on_sale)
        return {
            "name": (record.get("title") or "").strip(),
            "steam_app_id": str(record.get("steamAppID"))
            if record.get("steamAppID")
            else None,
            "external_product_id": str(record.get("gameID"))
            if record.get("gameID") is not None
            else None,
            "external_deal_id": str(record.get("dealID"))
            if record.get("dealID") is not None
            else None,
            "store_external_id": store_id,
            "store_name": store.get("storeName") or f"CheapShark Store {store_id}",
            "product_url": deal_url,
            "deal_url": deal_url,
            "cover_image": record.get("thumb"),
            "steam_rating_percent": self._rating_percent(
                record.get("steamRatingPercent", record.get("steam_rating_percent"))
            ),
            "steam_rating_count": self._non_negative_integer(
                record.get("steamRatingCount", record.get("steam_rating_count"))
            ),
            "steam_rating_text": (
                record.get("steamRatingText") or record.get("steam_rating_text")
            ),
            "release_date": self._release_date(
                record.get("releaseDate", record.get("release_date"))
            ),
            "normal_price": normal_price,
            "sale_price": sale_price,
            "discount_percent": savings or Decimal("0"),
            "deal_end_date": parse_local_datetime(
                record.get("dealEndDate") or record.get("deal_end_date")
            ),
            "first_seen_at": parse_local_datetime(
                record.get("firstSeenAt")
                or record.get("first_seen_at")
                or record.get("firstSeen")
            ),
            "is_on_sale": is_on_sale,
            "region": Config.CHEAPSHARK_REGION,
            "currency": Config.CHEAPSHARK_CURRENCY,
            "source": "cheapshark",
        }
