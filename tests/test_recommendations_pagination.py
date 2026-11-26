import unittest

from app import create_app
from app.extensions import db
from app.models import Game


class RecommendationPaginationTests(unittest.TestCase):
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
        db.session.add_all(Game(name=f"Recommendation Game {i:02}") for i in range(15))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_popular_recommendations_have_independent_server_pagination(self):
        response = self.app.test_client().get(
            "/recommendations?popular_page=2&gems_page=1&tab=popular"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"2 / 2", response.data)
        self.assertIn(b"Recommendation Game 12", response.data)
        self.assertNotIn(b"Recommendation Game 00", response.data)


if __name__ == "__main__":
    unittest.main()
