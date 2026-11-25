import unittest
from types import SimpleNamespace

from app.recommendation.ranking import rank_games


def _game(game_id, name, rating, reviews, genres=()):
    return SimpleNamespace(
        id=game_id,
        name=name,
        steam_rating_percent=rating,
        steam_rating_count=reviews,
        genres=[SimpleNamespace(name=genre) for genre in genres],
        tags=[],
        developer=None,
    )


class HiddenGemRankingTests(unittest.TestCase):
    def test_anonymous_hidden_gem_list_uses_quality_and_low_popularity(self):
        hidden = _game(1, "Small but Great", 92, 50)
        popular = _game(2, "Popular Game", 95, 100000)
        low_quality = _game(3, "Unpopular Poor Game", 65, 50)

        result = rank_games([hidden, popular, low_quality], profile={})

        self.assertEqual([item["game"].id for item in result["hidden_gem"]], [1])

    def test_personal_hidden_gem_requires_profile_fit(self):
        matching = _game(1, "Matching Gem", 90, 50, genres=["RPG"])
        unrelated = _game(2, "Unrelated Gem", 90, 50, genres=["Strategy"])
        popular_anchor = _game(3, "Popular Anchor", 95, 1000000)

        result = rank_games(
            [matching, unrelated, popular_anchor],
            profile={"genre:rpg": 1.0},
        )

        self.assertEqual([item["game"].id for item in result["hidden_gem"]], [1])

    def test_hidden_gems_respect_owned_and_dismissed_filters(self):
        first = _game(1, "First Gem", 90, 50)
        second = _game(2, "Second Gem", 90, 60)

        result = rank_games(
            [first, second],
            profile={},
            owned_game_ids=[first.id],
            dismissed_game_ids=[second.id],
        )

        self.assertEqual(result["hidden_gem"], [])


if __name__ == "__main__":
    unittest.main()
