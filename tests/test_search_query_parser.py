import unittest
from decimal import Decimal

from app.services.search_query_parser import parse_search_query


class SearchQueryParserTests(unittest.TestCase):
    def test_parses_indonesian_price_constraint(self):
        intent = parse_search_query("game horor psikologis di bawah 100 ribu")

        self.assertEqual(intent.semantic_text, "game horor psikologis")
        self.assertEqual(intent.max_price, Decimal("100000.00"))
        self.assertEqual(intent.currency, "IDR")

    def test_parses_english_currency_and_discount(self):
        intent = parse_search_query("story rich RPG under $10 with at least 50% discount")

        self.assertEqual(intent.semantic_text, "story rich RPG with")
        self.assertEqual(intent.max_price, Decimal("10.00"))
        self.assertEqual(intent.currency, "USD")
        self.assertEqual(intent.min_discount, Decimal("50"))

    def test_parses_sort_preference(self):
        intent = parse_search_query("game RPG termurah")

        self.assertEqual(intent.sort, "price")
        self.assertEqual(intent.semantic_text, "game RPG")


if __name__ == "__main__":
    unittest.main()
