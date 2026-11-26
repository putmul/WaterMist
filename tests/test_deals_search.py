import unittest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import Deal, Game, GameProduct, GameTag, Store
from app.services.deal_service import DealService


class DealsSearchTests(unittest.TestCase):
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

    def _deal(self, name, price=100000):
        game = Game(name=name)
        store = Store.query.filter_by(name="Steam").one_or_none()
        if store is None:
            store = Store(name="Steam")
            db.session.add(store)
        db.session.add(game)
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
        db.session.add(
            Deal(
                game_product_id=product.id,
                normal_price=Decimal("200000"),
                sale_price=Decimal(str(price)),
                discount_percent=Decimal("50"),
                deal_url="https://example.test/deal",
                source="steam_scraper",
            )
        )
        return game

    def test_literal_search_prioritizes_exact_name(self):
        exact = self._deal("Final Fantasy")
        self._deal("Final Fantasy XVI")
        self._deal("The Final Fantasy Collection")
        db.session.commit()

        results = DealService().search_by_name(
            {"q": "Final Fantasy", "sort": "relevance"}
        )

        self.assertEqual(results[0].game_product.game.id, exact.id)
        self.assertEqual(len(results), 3)

    def test_literal_search_paginates_in_database_and_returns_all_matching_ids(self):
        first = self._deal("Final Fantasy")
        second = self._deal("Final Fantasy XVI")
        third = self._deal("The Final Fantasy Collection")
        db.session.commit()

        service = DealService()
        page = service.paginate_search_by_name(
            {"q": "Final Fantasy", "sort": "relevance"}, page=2, per_page=1
        )

        self.assertEqual(page.total, 3)
        self.assertEqual(page.page, 2)
        self.assertEqual(len(page.items), 1)
        self.assertEqual(
            set(service.literal_game_ids({"q": "Final Fantasy", "sort": "relevance"})),
            {first.id, second.id, third.id},
        )

    def test_deals_page_renders_literal_section_without_semantic_blocking(self):
        self._deal("Final Fantasy XVI")
        db.session.commit()

        response = self.app.test_client().get(
            "/deals", query_string={"q": "Final Fantasy"}
        )

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Hasil berdasarkan nama", body)
        self.assertIn("Mencari rekomendasi berdasarkan makna", body)
        self.assertNotIn("Belum ada deal yang sesuai dengan filter", body)

    def test_nsfw_tagged_games_are_excluded_from_literal_search(self):
        safe = self._deal("Safe Horror Game")
        nsfw = self._deal("Adult Horror Game")
        db.session.add(GameTag(game_id=nsfw.id, tag="Sexual Content"))
        db.session.commit()

        results = DealService().search_by_name(
            {"q": "horror game", "sort": "relevance"}
        )

        result_ids = [deal.game_product.game.id for deal in results]
        self.assertIn(safe.id, result_ids)
        self.assertNotIn(nsfw.id, result_ids)

    def test_popularity_sort_orders_by_review_count(self):
        less_popular = self._deal("Less Popular Game")
        most_popular = self._deal("Most Popular Game")
        less_popular.steam_rating_count = 100
        most_popular.steam_rating_count = 10000
        db.session.commit()

        response = self.app.test_client().get(
            "/deals", query_string={"sort": "popularity"}
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertLess(body.index("Most Popular Game"), body.index("Less Popular Game"))


if __name__ == "__main__":
    unittest.main()
