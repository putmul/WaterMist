import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from app import create_app
from app.collectors.steam_release_bot import parse_app_detail, parse_price
from app.extensions import db
from app.models.game import Game, GameProduct, PriceHistory
from app.services.game_service import GameService


class FakeCollector:
    def __init__(self, records=None, error=None):
        self.records = records or []
        self.error = error

    def fetch(self, **kwargs):
        if self.error:
            raise self.error
        return self.records

    def normalize(self, record):
        return record


def release_record(app_id="10", name="Test Game", release_date=None):
    return {
        "steam_app_id": app_id,
        "external_product_id": app_id,
        "name": name,
        "description": "A test game",
        "release_date": release_date or date.today(),
        "cover_image": "https://example.test/cover.jpg",
        "developer": "Test Studio",
        "publisher": "Test Publisher",
        "genres": ["Action"],
        "tags": ["Singleplayer"],
        "product_url": f"https://store.steampowered.com/app/{app_id}/",
        "region": "ID",
        "currency": "IDR",
        "regular_price": Decimal("100000.00"),
        "sale_price": Decimal("100000.00"),
        "discount_percent": 0,
        "source": "steam_release_bot",
    }


class RecentlyReleasedTests(unittest.TestCase):
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

    def test_parser_extracts_metadata_and_price(self):
        html = """
        <div class="release_date"><div class="date">19 Nov, 2026</div></div>
        <div class="apphub_AppName">Parser Game</div>
        <div id="genresAndManufacturer"><a href="/genre/Action">Action</a></div>
        <div class="glance_tags"><a class="app_tag">+Singleplayer</a></div>
        <div class="game_purchase_price">Rp 12.500,00</div>
        """
        record = parse_app_detail(html, app_id=123, url="https://steam.test/app/123/")

        self.assertEqual(record["name"], "Parser Game")
        self.assertEqual(record["app_id"], 123)
        self.assertEqual(record["genres"], ["Action"])
        self.assertEqual(record["tags"], ["Singleplayer"])
        self.assertEqual(parse_price("Rp 12.500,00"), Decimal("12500.00"))

    def test_sync_is_idempotent(self):
        collector = FakeCollector([release_record()])

        first = GameService().sync_recently_released(collector=collector)
        second = GameService().sync_recently_released(collector=collector)

        self.assertEqual(first["records_saved"], 1)
        self.assertEqual(second["records_saved"], 1)
        self.assertEqual(Game.query.count(), 1)
        self.assertEqual(GameProduct.query.count(), 1)
        self.assertEqual(PriceHistory.query.count(), 1)

    def test_failed_sync_keeps_existing_data(self):
        GameService().sync_recently_released(
            collector=FakeCollector([release_record(app_id="20")])
        )

        result = GameService().sync_recently_released(
            collector=FakeCollector(error=RuntimeError("Steam unavailable"))
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(Game.query.filter_by(steam_app_id="20").count(), 1)

    def test_release_page_applies_fixed_window_and_search(self):
        db.session.add_all(
            [
                Game(
                    name="Visible Game",
                    steam_app_id="1",
                    release_date=date.today() - timedelta(days=1),
                ),
                Game(name="Today Game", steam_app_id="4", release_date=date.today()),
                Game(
                    name="Old Game",
                    steam_app_id="2",
                    release_date=date.today() - timedelta(days=30),
                ),
                Game(
                    name="Future Game",
                    steam_app_id="3",
                    release_date=date.today() + timedelta(days=1),
                ),
            ]
        )
        db.session.commit()

        response = self.app.test_client().get("/releases?q=Visible")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Visible Game", response.data)
        self.assertNotIn(b"Today Game", response.data)
        self.assertNotIn(b"Old Game", response.data)
        self.assertNotIn(b"Future Game", response.data)

    @patch("app.routes.main.GameService.sync_recently_released")
    def test_dashboard_can_trigger_release_sync(self, sync_recently_released):
        sync_recently_released.return_value = {
            "status": "success",
            "records_saved": 3,
        }

        response = self.app.test_client().post("/sync/releases")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        sync_recently_released.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
