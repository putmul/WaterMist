import unittest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import Deal, Game, GameProduct, GameTag, Store
from app.services.game_detail_service import GameDetailService


class GameDetailComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SCHEDULER_ENABLED": False,
                "PRICE_COMPARISON_CURRENCY": "IDR",
                "PRICE_EXCHANGE_RATES": {
                    "IDR": Decimal("1"),
                    "USD": Decimal("16000"),
                },
            }
        )

    def setUp(self):
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

        self.game = Game(
            name="Comparison Game",
            description="A short game description.",
            developer="Studio A",
            publisher="Publisher A",
        )
        db.session.add(self.game)
        db.session.flush()
        db.session.add(GameTag(game_id=self.game.id, tag="Action"))

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def add_offer(self, store_name, price, currency="IDR", active=True):
        store = Store(name=store_name)
        db.session.add(store)
        db.session.flush()
        product = GameProduct(
            game_id=self.game.id,
            store_id=store.id,
            external_product_id=f"{store_name}-product",
            region="ID" if currency == "IDR" else "US",
            currency=currency,
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(
            Deal(
                game_product_id=product.id,
                normal_price=Decimal("300000"),
                sale_price=Decimal(str(price)),
                discount_percent=Decimal("50"),
                deal_url=f"https://{store_name.lower()}.test/deal",
                source="steam_scraper" if store_name == "Steam" else "cheapshark",
                is_active=active,
            )
        )

    def test_detail_selects_cheapest_distributor_after_currency_conversion(self):
        self.add_offer("Steam", "180000")
        self.add_offer("Epic Games", "12", currency="USD")
        self.add_offer("GOG", "200000")
        db.session.commit()

        view = GameDetailService.get_game_detail(self.game.id)

        self.assertEqual([offer["store_name"] for offer in view["offers"]], ["Steam", "Epic Games", "GOG"])
        self.assertEqual(view["cheapest_offers"][0]["store_name"], "Steam")
        self.assertEqual(view["cheapest_offers"][0]["comparison_price"], Decimal("180000.00"))

    def test_detail_excludes_inactive_offers_and_renders_metadata(self):
        self.add_offer("Steam", "180000")
        self.add_offer("Old Store", "50000", active=False)
        db.session.commit()

        response = self.app.test_client().get(f"/games/{self.game.id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Comparison Game", response.data)
        self.assertIn(b"Studio A", response.data)
        self.assertIn(b"Publisher A", response.data)
        self.assertIn(b"Action", response.data)
        self.assertIn(b"Harga termurah", response.data)
        self.assertNotIn(b"Old Store", response.data)

    def test_unknown_game_returns_not_found(self):
        response = self.app.test_client().get("/games/99999")

        self.assertEqual(response.status_code, 404)

    def test_missing_exchange_rate_does_not_claim_global_cheapest(self):
        self.add_offer("Steam", "180000")
        self.add_offer("Unknown Store", "10", currency="EUR")
        db.session.commit()
        original_rates = self.app.config["PRICE_EXCHANGE_RATES"]
        self.app.config["PRICE_EXCHANGE_RATES"] = {"IDR": Decimal("1")}
        try:
            view = GameDetailService.get_game_detail(self.game.id)
        finally:
            self.app.config["PRICE_EXCHANGE_RATES"] = original_rates

        self.assertFalse(view["comparison_available"])
        self.assertEqual(view["cheapest_offers"], [])


if __name__ == "__main__":
    unittest.main()
