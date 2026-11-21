import unittest
from datetime import date
from decimal import Decimal

from app.collectors.cheapshark_client import CheapSharkClient


class CheapSharkMetadataTests(unittest.TestCase):
    def setUp(self):
        self.client = CheapSharkClient(delay=0)
        self.client.stores = {"1": {"storeName": "Test Store"}}

    def test_normalize_extracts_review_metadata(self):
        record = self.client.normalize(
            {
                "title": "Review Game",
                "steamAppID": "123",
                "storeID": "1",
                "gameID": "456",
                "dealID": "789",
                "normalPrice": "20",
                "salePrice": "10",
                "savings": "50",
                "dealURL": "https://example.test/deal",
                "steamRatingPercent": "94",
                "steamRatingCount": "12000",
                "steamRatingText": "Very Positive",
                "releaseDate": "2024-05-12",
            }
        )

        self.assertEqual(record["steam_rating_percent"], 94)
        self.assertEqual(record["steam_rating_count"], 12000)
        self.assertEqual(record["steam_rating_text"], "Very Positive")
        self.assertEqual(record["release_date"], date(2024, 5, 12))

    def test_normalize_rejects_invalid_review_metadata(self):
        record = self.client.normalize(
            {
                "title": "Invalid Metadata",
                "storeID": "1",
                "gameID": "456",
                "dealID": "789",
                "normalPrice": "20",
                "salePrice": "10",
                "dealURL": "https://example.test/deal",
                "steamRatingPercent": "not-a-number",
                "steamRatingCount": "-10",
                "releaseDate": "not-a-date",
            }
        )

        self.assertIsNone(record["steam_rating_percent"])
        self.assertIsNone(record["steam_rating_count"])
        self.assertIsNone(record["release_date"])


if __name__ == "__main__":
    unittest.main()
