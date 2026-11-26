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

    def test_extracts_indonesian_reference_game_and_preserves_price_filter(self):
        intent = parse_search_query("game seperti Call of Duty di bawah 100000")

        self.assertEqual(intent.reference_game_name, "Call of Duty")
        self.assertEqual(intent.max_price, Decimal("100000.00"))
        self.assertEqual(intent.currency, "IDR")

    def test_parses_compound_dibawah_spelling(self):
        intent = parse_search_query("game seperti Call of Duty dibawah 100000")

        self.assertEqual(intent.reference_game_name, "Call of Duty")
        self.assertEqual(intent.semantic_text, "game seperti Call of Duty")
        self.assertEqual(intent.max_price, Decimal("100000.00"))

    def test_extracts_english_reference_game(self):
        intent = parse_search_query("games similar to Call of Duty under $10")

        self.assertEqual(intent.reference_game_name, "Call of Duty")
        self.assertEqual(intent.max_price, Decimal("10.00"))
        self.assertEqual(intent.currency, "USD")


if __name__ == "__main__":
    unittest.main()
