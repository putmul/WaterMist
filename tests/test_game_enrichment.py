import unittest

from app import create_app
from app.extensions import db
from app.models import Game, GameTag, Genre, User
from app.services.game_enrichment_service import GameEnrichmentService


class _Collector:
    def scrape_app_detail(self, candidate):
        return {
            "app_id": candidate["app_id"],
            "name": "Enriched Game",
            "genres": ["RPG"],
            "tags": ["Story Rich"],
            "developer": "Test Developer",
            "publisher": "Test Publisher",
        }


class GameEnrichmentTests(unittest.TestCase):
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

    def test_enrichment_persists_game_features(self):
        game = Game(name="Placeholder", steam_app_id="123")
        db.session.add(game)
        db.session.commit()

        stats = GameEnrichmentService(collector=_Collector()).enrich_app_ids(["123"])
        db.session.commit()

        refreshed = db.session.get(Game, game.id)
        self.assertEqual(stats["metadata_completed"], 1)
        self.assertEqual(refreshed.developer, "Test Developer")
        self.assertEqual([genre.name for genre in refreshed.genres], ["RPG"])
        self.assertEqual([tag.tag for tag in refreshed.tags], ["Story Rich"])

    def test_enrichment_skips_complete_game(self):
        game = Game(name="Complete", steam_app_id="456", developer="Existing")
        db.session.add(game)
        db.session.commit()

        stats = GameEnrichmentService(collector=_Collector()).enrich_app_ids(["456"])
        self.assertEqual(stats["metadata_skipped"], 1)
        self.assertEqual(stats["metadata_completed"], 0)


if __name__ == "__main__":
    unittest.main()
