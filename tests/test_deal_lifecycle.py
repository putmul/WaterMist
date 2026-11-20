import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app import create_app
from app.collectors.cheapshark_client import CheapSharkClient
from app.extensions import db
from app.models.deal import Deal
from app.models.game import Game, GameProduct
from app.models.store import Store
from app.services.deal_lifecycle import apply_deal_record, end_deal


class DealLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SCHEDULER_ENABLED": False,
            }
        )

    def setUp(self):
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_cheapshark_normalizes_sale_status_and_first_seen(self):
        client = CheapSharkClient(delay=0)
        client.stores = {"25": {"storeName": "Epic Games Store"}}

        record = client.normalize(
            {
                "title": "Test Game",
                "storeID": "25",
                "gameID": "123",
                "dealID": "deal-1",
                "normalPrice": "20",
                "salePrice": "10",
                "savings": "50",
                "isOnSale": "0",
                "firstSeenAt": "2026-11-18T10:00:00Z",
                "dealURL": "https://example.test/deal",
            }
        )

        self.assertFalse(record["is_on_sale"])
        self.assertEqual(record["first_seen_at"], datetime(2026, 11, 18, 17))

    def test_first_seen_is_preserved_and_ended_at_is_set(self):
        deal = Deal(
            normal_price=Decimal("20.00"),
            sale_price=Decimal("10.00"),
            discount_percent=Decimal("50"),
            deal_url="https://example.test/deal",
            source="cheapshark",
        )
        first_seen = datetime(2026, 11, 18, 17)
        first = apply_deal_record(
            deal,
            {
                "normal_price": Decimal("20.00"),
                "sale_price": Decimal("10.00"),
                "discount_percent": Decimal("50"),
                "deal_url": "https://example.test/deal",
                "external_deal_id": "deal-1",
                "is_on_sale": True,
                "first_seen_at": first_seen,
            },
            now=first_seen,
        )
        second_seen = first_seen + timedelta(days=1)
        apply_deal_record(
            deal,
            {
                "normal_price": Decimal("20.00"),
                "sale_price": Decimal("12.00"),
                "discount_percent": Decimal("40"),
                "deal_url": "https://example.test/deal",
                "external_deal_id": "deal-1",
                "is_on_sale": True,
            },
            now=second_seen,
        )

        self.assertEqual(first.first_seen_at, first_seen)
        end_time = second_seen + timedelta(hours=1)
        end_deal(deal, "not_on_sale", now=end_time)
        self.assertFalse(deal.is_active)
        self.assertFalse(deal.is_on_sale)
        self.assertEqual(deal.first_seen_at, first_seen)
        self.assertEqual(deal.ended_at, end_time)
        self.assertEqual(deal.end_reason, "not_on_sale")


if __name__ == "__main__":
    unittest.main()
