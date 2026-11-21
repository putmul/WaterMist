import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Game, GameGenre, Genre, User, UserInteraction, UserOwnedGame
from app.services.recommendation_service import RecommendationService
from app.services.steam_service import SteamProfilePrivateError, SteamService


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _SteamHTTP:
    def __init__(self, payload):
        self.payload = payload

    def get(self, url, params, timeout):
        return _Response(self.payload)


class PersonalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "STEAM_API_KEY": "test-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SCHEDULER_ENABLED": False,
            }
        )

    def setUp(self):
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        genre = Genre(name="RPG")
        game = Game(
            name="RPG Test",
            steam_app_id="123",
            steam_rating_percent=90,
            steam_rating_count=1000,
        )
        db.session.add_all([genre, game])
        db.session.flush()
        db.session.add(GameGenre(game_id=game.id, genre_id=genre.id))
        db.session.commit()
        self.game = game

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_anonymous_choice_matches_game_features(self):
        result = RecommendationService().recommend(genres=["RPG"])
        self.assertEqual(result["mode"], "search")
        self.assertEqual(result["popular"][0]["game"].name, "RPG Test")
        self.assertGreater(result["popular"][0]["fit_score"], 0)

    def test_user_recommendations_exclude_owned_and_dismissed_games(self):
        user = User(email="user@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        db.session.add(
            UserOwnedGame(
                user_id=user.id,
                game_id=self.game.id,
                steam_app_id=self.game.steam_app_id,
                playtime_minutes=10,
            )
        )
        db.session.add(
            UserInteraction(
                user_id=user.id,
                game_id=self.game.id,
                interaction_type="dismiss_recommendation",
            )
        )
        db.session.commit()
        result = RecommendationService().recommend(user=user, genres=["RPG"])
        self.assertEqual(result["popular"], [])

    def test_steam_public_library_is_saved_and_sets_mode(self):
        user = User(email="steam@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        service = SteamService(
            _SteamHTTP(
                {
                    "response": {
                        "games": [
                            {
                                "appid": 123,
                                "playtime_forever": 120,
                                "playtime_2weeks": 30,
                            }
                        ]
                    }
                }
            )
        )
        profile = service.link_profile(user, "76561198000000000")
        self.assertEqual(profile.sync_status, "success")
        self.assertEqual(user.preference_mode, "steam")
        self.assertEqual(len(user.owned_games), 1)
        self.assertEqual(user.owned_games[0].game_id, self.game.id)

    def test_private_steam_library_falls_back_without_deleting_account(self):
        user = User(email="private@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        service = SteamService(_SteamHTTP({"response": {}}))
        with self.assertRaises(SteamProfilePrivateError):
            service.link_profile(user, "76561198000000000")
        self.assertEqual(user.preference_mode, "quiz")
        self.assertEqual(user.steam_profile.sync_status, "failed")

    def test_register_and_quiz_routes(self):
        client = self.app.test_client()
        response = client.post(
            "/auth/register",
            data={"email": "route@example.com", "password": "password123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        response = client.post(
            "/onboarding/quiz",
            data={"genres": "RPG", "tags": "exploration"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"RPG Test", response.data)

    def test_steam_connect_refreshes_recommendations_immediately(self):
        client = self.app.test_client()
        client.post(
            "/auth/register",
            data={"email": "steam-route@example.com", "password": "password123"},
        )
        with patch("app.routes.auth.SteamService") as steam_class, patch.object(
            RecommendationService, "generate_for_user"
        ) as generate:
            response = client.post(
                "/auth/steam/connect",
                data={"steam_profile": "76561198000000000"},
            )
        self.assertEqual(response.status_code, 302)
        steam_class.return_value.link_profile.assert_called_once()
        generate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
