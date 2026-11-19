"""Steam discount collector."""

import re
from urllib.parse import urljoin

from config import Config

from .steam_release_bot import (
    SteamReleaseBot,
    _app_id_from_url,
    _text,
    is_base_game,
    nsfw_reason,
    parse_price,
)

def parse_discount_page(html, page_url=""):
    """Parse one Steam search page into raw discount records."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    records = []
    for row in soup.select("a.search_result_row"):
        href = urljoin(page_url, row.get("href", ""))
        app_id = row.get("data-ds-appid") or _app_id_from_url(href)
        if not app_id:
            continue
        try:
            app_id = int(str(app_id).split(",")[0])
        except (TypeError, ValueError):
            continue

        discount_text = _text(
            row.select_one(".search_discount_pct, .discount_pct")
        )
        match = re.search(r"(\d+)", discount_text)
        discount = int(match.group(1)) if match else 0
        if discount <= 0:
            continue

        image = row.select_one(".search_capsule img") or row.select_one("img")
        records.append(
            {
                "app_id": app_id,
                "name": _text(row.select_one(".search_name"))
                or _text(row.select_one(".title")),
                "regular_price": parse_price(
                    _text(row.select_one(".discount_original_price"))
                ),
                "sale_price": parse_price(
                    _text(row.select_one(".discount_final_price"))
                ),
                "discount_percent": discount,
                "product_url": href
                or Config.STEAM_DETAIL_URL.format(app_id=app_id),
                "cover_image": image.get("src", "") if image else "",
            }
        )
    return records


class SteamDealsCollector(SteamReleaseBot):
    """Fetch discounted base games from Steam search results."""

    def __init__(self, session=None, delay=None):
        super().__init__(session=session, delay=delay)
        self.last_fetch_complete = False

    def fetch(self, limit=None, max_pages=None, **kwargs):
        max_pages = max_pages or Config.STEAM_DEALS_MAX_PAGES
        records = []
        seen = set()
        self.last_fetch_complete = False

        self.check_robots_txt()
        for page in range(1, max_pages + 1):
            url = Config.STEAM_DEALS_SEARCH_URL.format(page=page)
            html = self._get_html(url)
            if html is None:
                return records
            page_records = parse_discount_page(html, url)
            if not page_records:
                self.last_fetch_complete = True
                break
            for record in page_records:
                if record["app_id"] in seen:
                    continue
                if not is_base_game(record) or nsfw_reason(record):
                    continue
                seen.add(record["app_id"])
                records.append(record)
                if limit and len(records) >= limit:
                    self.last_fetch_complete = False
                    return records
        else:
            self.last_fetch_complete = False
        return records

    def normalize(self, record):
        regular_price = record.get("regular_price")
        sale_price = record.get("sale_price")
        if sale_price is None:
            sale_price = regular_price
        if regular_price is None:
            regular_price = sale_price
        return {
            "steam_app_id": str(record.get("app_id")) if record.get("app_id") else None,
            "name": (record.get("name") or "").strip(),
            "external_product_id": str(record.get("app_id"))
            if record.get("app_id")
            else None,
            "external_deal_id": None,
            "store_external_id": "steam",
            "store_name": "Steam",
            "product_url": record.get("product_url"),
            "deal_url": record.get("product_url"),
            "cover_image": record.get("cover_image") or None,
            "normal_price": regular_price,
            "sale_price": sale_price,
            "discount_percent": record.get("discount_percent", 0),
            "deal_end_date": record.get("deal_end_date"),
            "region": Config.STEAM_REGION,
            "currency": Config.STEAM_CURRENCY,
            "source": "steam_scraper",
        }
