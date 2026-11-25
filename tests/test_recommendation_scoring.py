import unittest

from app.recommendation.scoring import (
    calculate_final_score,
    calculate_personalized_score,
    calculate_popularity_score,
    calculate_quality_score,
    is_hidden_gem,
)


class RecommendationScoringTests(unittest.TestCase):
    def test_popularity_is_log_normalized_and_bounded(self):
        self.assertEqual(calculate_popularity_score(0, 0), 0.0)
        self.assertEqual(calculate_popularity_score(100, 100), 1.0)
        self.assertGreater(calculate_popularity_score(10, 100), 0.0)
        self.assertLessEqual(calculate_popularity_score(1000, 100), 1.0)

    def test_quality_missing_metadata_is_not_zero(self):
        self.assertIsNone(calculate_quality_score(None, 100))
        self.assertAlmostEqual(calculate_quality_score(50, 0), 0.5)
        self.assertGreater(calculate_quality_score(100, 10000), 0.5)

    def test_legacy_final_score_uses_neutral_quality_when_missing(self):
        self.assertEqual(calculate_final_score(0, None), 0.25)
        self.assertEqual(calculate_final_score(1, 1), 1.0)

    def test_personal_fit_has_more_weight_than_popularity(self):
        matching = calculate_personalized_score(1, 0.5, 0, "popular")
        popular = calculate_personalized_score(0, 0.5, 1, "popular")
        self.assertGreater(matching, popular)

    def test_hidden_gem_requires_positive_reviews_and_enough_reviews(self):
        self.assertTrue(is_hidden_gem(80, 25, 0.40))
        self.assertFalse(is_hidden_gem(79, 100, 0.10))
        self.assertFalse(is_hidden_gem(100, 24, 0.10))
        self.assertFalse(is_hidden_gem(100, 100, 0.41))
        self.assertFalse(is_hidden_gem(None, 100, 0.10))

    def test_hidden_gem_has_absolute_review_cap(self):
        self.assertFalse(is_hidden_gem(95, 10001, 0.10))


if __name__ == "__main__":
    unittest.main()
