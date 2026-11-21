import unittest
from datetime import date

from app import create_app
from app.collectors.cheapshark_client import CheapSharkClient
from app.extensions import db
from app.models.game import Game
from app.services.deal_service import DealService


class ReviewMetadataPersistenceTests(unittest.TestCase):
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

    def test_deal_sync_persists_review_metadata_on_game(self):
        client = CheapSharkClient(delay=0)
        client.stores = {"1": {"storeName": "Test Store"}}
        record = client.normalize(
            {
                "title": "Persisted Game",
                "steamAppID": "123",
                "storeID": "1",
                "gameID": "456",
                "dealID": "789",
                "normalPrice": "20",
                "salePrice": "10",
                "savings": "50",
                "dealURL": "https://example.test/deal",
                "steamRatingPercent": "91",
                "steamRatingCount": "5000",
                "steamRatingText": "Very Positive",
                "releaseDate": "2023-06-01",
            }
        )

        DealService()._upsert_record(record, client)
        db.session.commit()

        game = Game.query.one()
        self.assertEqual(game.steam_rating_percent, 91)
        self.assertEqual(game.steam_rating_count, 5000)
        self.assertEqual(game.steam_rating_text, "Very Positive")
        self.assertEqual(game.release_date, date(2023, 6, 1))
        self.assertEqual(game.review_source, "cheapshark")
        self.assertIsNotNone(game.review_updated_at)

    def test_missing_review_values_do_not_overwrite_existing_values(self):
        game = Game(
            name="Existing Game",
            steam_app_id="123",
            steam_rating_percent=90,
            steam_rating_count=1000,
            steam_rating_text="Very Positive",
            review_source="cheapshark",
        )
        db.session.add(game)
        db.session.commit()

        DealService._update_game_review_metadata(
            game,
            {
                "steam_rating_percent": None,
                "steam_rating_count": None,
                "steam_rating_text": None,
                "release_date": None,
            },
        )
        db.session.commit()

        refreshed = db.session.get(Game, game.id)
        self.assertEqual(refreshed.steam_rating_percent, 90)
        self.assertEqual(refreshed.steam_rating_count, 1000)
        self.assertEqual(refreshed.steam_rating_text, "Very Positive")
        self.assertEqual(refreshed.review_source, "cheapshark")


if __name__ == "__main__":
    unittest.main()
