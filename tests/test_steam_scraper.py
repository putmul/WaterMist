import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.collectors.steam_release_bot import (
    SteamReleaseBot,
    parse_app_detail,
    parse_discount_end_date,
)
from app.collectors.steam_scraper import SteamDealsCollector, parse_discount_page
from app.models.deal import Deal
from app.services.deal_lifecycle import apply_deal_record


class SteamDiscountParserTests(unittest.TestCase):
    def test_parse_discount_end_date(self):
        self.assertEqual(
            parse_discount_end_date("Offer ends 30 Nov, 2026"),
            datetime(2026, 11, 30, 23, 59, 59),
        )

    def test_parse_discount_end_date_returns_none_for_invalid_text(self):
        self.assertIsNone(parse_discount_end_date("Offer ends soon"))

    def test_parse_discount_end_date_infers_year_for_short_steam_text(self):
        self.assertEqual(
            parse_discount_end_date(
                "SPECIAL PROMOTION! Offer ends 2 December",
                reference_date=date(2026, 11, 20),
            ),
            datetime(2026, 12, 2, 23, 59, 59),
        )

    def test_parse_app_detail_extracts_discount_end_date(self):
        html = """
        <p class="game_purchase_discount_countdown">
            SPECIAL PROMOTION! Offer ends 30 Nov, 2026
        </p>
        <div class="apphub_AppName">Discount Game</div>
        """

        record = parse_app_detail(html, app_id=123)

        self.assertEqual(
            record["deal_end_date"],
            datetime(2026, 11, 30, 23, 59, 59),
        )

    def test_discount_page_supports_expiration_when_present(self):
        html = """
        <a class="search_result_row" data-ds-appid="123"
           href="https://steam.test/app/123/">
            <div class="search_name">Discount Game</div>
            <div class="search_discount_pct">-25%</div>
            <div class="discount_original_price">$20.00</div>
            <div class="discount_final_price">$15.00</div>
            <div class="search_discount_expiration">Offer ends 30 Nov, 2026</div>
        </a>
        """

        records = parse_discount_page(html)

        self.assertEqual(
            records[0]["deal_end_date"], datetime(2026, 11, 30, 23, 59, 59)
        )

    def test_collector_enriches_discount_from_detail_page(self):
        search_html = """
        <a class="search_result_row" data-ds-appid="123"
           href="https://steam.test/app/123/">
            <div class="search_name">Discount Game</div>
            <div class="search_discount_pct">-25%</div>
            <div class="discount_original_price">$20.00</div>
            <div class="discount_final_price">$15.00</div>
        </a>
        """
        detail_html = """
        <div class="discount_expiration">Offer ends 30 Nov, 2026</div>
        <div class="apphub_AppName">Discount Game</div>
        """

        collector = SteamDealsCollector(delay=0)
        collector.robots = type(
            "AllowedRobots", (), {"can_fetch": lambda self, agent, url: True}
        )()
        collector._get_html = lambda url: (
            search_html if "search" in url else detail_html
        )

        records = collector.fetch(max_pages=1)

        self.assertEqual(
            records[0]["deal_end_date"], datetime(2026, 11, 30, 23, 59, 59)
        )

    def test_source_end_date_takes_precedence_over_fallback(self):
        source_end = datetime(2026, 11, 30, 23, 59, 59)
        deal = Deal(source="steam_scraper")
        record = {
            "normal_price": Decimal("20.00"),
            "sale_price": Decimal("15.00"),
            "discount_percent": Decimal("25"),
            "deal_url": "https://steam.test/app/123/",
            "external_deal_id": None,
            "deal_end_date": source_end,
            "is_on_sale": True,
        }

        apply_deal_record(deal, record, now=datetime(2026, 11, 20, 12))

        self.assertEqual(deal.deal_end_date, source_end)

    def test_release_normalize_keeps_discount_end_date(self):
        source_end = datetime(2026, 11, 30, 23, 59, 59)
        collector = SteamReleaseBot(delay=0)

        normalized = collector.normalize(
            {
                "app_id": 123,
                "name": "Discount Game",
                "deal_end_date": source_end,
            }
        )

        self.assertEqual(normalized["deal_end_date"], source_end)

    def test_fallback_is_used_when_steam_has_no_end_date(self):
        now = datetime(2026, 11, 20, 12)
        deal = Deal(source="steam_scraper")
        record = {
            "normal_price": Decimal("20.00"),
            "sale_price": Decimal("15.00"),
            "discount_percent": Decimal("25"),
            "deal_url": "https://steam.test/app/123/",
            "external_deal_id": None,
            "deal_end_date": None,
            "is_on_sale": True,
        }

        apply_deal_record(deal, record, now=now)

        self.assertEqual(deal.deal_end_date, now + timedelta(days=14))


if __name__ == "__main__":
    unittest.main()
