import unittest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import Deal, Game, GameProduct, GameTag, Store
from app.services.search_query_parser import SearchIntent
from app.services.semantic_search_service import SemanticSearchService


class SemanticSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SCHEDULER_ENABLED": False,
                "SEMANTIC_SEARCH_MIN_SCORE": 0.1,
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

    @staticmethod
    def _encoder(texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append([1.0, 0.0] if any(word in lowered for word in ("horror", "horor")) else [0.0, 1.0])
        return vectors

    def _deal(self, name, tags, price):
        game = Game(name=name)
        db.session.add(game)
        db.session.flush()
        for tag in tags:
            db.session.add(GameTag(game_id=game.id, tag=tag))
        store = Store(name=f"Store {name}")
        db.session.add(store)
        db.session.flush()
        product = GameProduct(
            game_id=game.id,
            store_id=store.id,
            external_product_id=name,
            region="ID",
            currency="IDR",
        )
        db.session.add(product)
        db.session.flush()
        deal = Deal(
            game_product_id=product.id,
            normal_price=Decimal("200000"),
            sale_price=Decimal(str(price)),
            discount_percent=Decimal("50"),
            deal_url="https://example.test/deal",
            source="test",
        )
        db.session.add(deal)
        return game, deal

    def test_semantic_query_ranks_conceptually_relevant_game(self):
        relevant, _ = self._deal("Dark Psychological Horror", ["Horror"], 80000)
        unrelated, _ = self._deal("Bright Puzzle", ["Puzzle"], 50000)
        db.session.commit()

        results = SemanticSearchService(encoder=self._encoder).search(
            SearchIntent("game horor psikologis", max_price=Decimal("100000"))
        )

        self.assertEqual([deal.game_product.game.id for deal in results], [relevant.id])
        self.assertGreater(results[0].semantic_score, 0.9)
        self.assertEqual(results[0].sale_price, Decimal("80000.00"))
        self.assertNotIn(unrelated.id, [deal.game_product.game.id for deal in results])

    def test_structured_query_without_semantic_text_still_filters_deals(self):
        cheap, _ = self._deal("Cheap Game", [], 50000)
        self._deal("Expensive Game", [], 150000)
        db.session.commit()

        results = SemanticSearchService(encoder=self._encoder).search(
            SearchIntent("", max_price=Decimal("100000"))
        )

        self.assertEqual([deal.game_product.game.id for deal in results], [cheap.id])


if __name__ == "__main__":
    unittest.main()
