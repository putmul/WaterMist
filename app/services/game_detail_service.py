"""Read-only data preparation for the game detail and deal comparison page."""

from app.extensions import db
from app.models.game import Game
from app.services.deal_service import DealService
from app.utils.money import to_idr


class GameDetailService:
    """Build a game detail view from the locally persisted data."""

    @staticmethod
    def _comparison_price(deal):
        return to_idr(deal.sale_price, deal.game_product.currency)

    @classmethod
    def _offer(cls, deal):
        product = deal.game_product
        store = product.store
        return {
            "deal": deal,
            "store_name": store.name,
            "currency": product.currency,
            "region": product.region,
            "normal_price": deal.normal_price,
            "sale_price": deal.sale_price,
            "normal_price_idr": to_idr(deal.normal_price, product.currency),
            "sale_price_idr": to_idr(deal.sale_price, product.currency),
            "discount_percent": deal.discount_percent,
            "comparison_price": cls._comparison_price(deal),
            "deal_end_date": deal.deal_end_date,
            "deal_url": deal.deal_url,
            "is_cheapest": False,
        }

    @staticmethod
    def _best_offer_per_store(offers):
        grouped = {}
        for offer in offers:
            key = offer["deal"].game_product.store_id
            grouped.setdefault(key, []).append(offer)

        selected = []
        for store_offers in grouped.values():
            selected.append(
                min(
                    store_offers,
                    key=lambda offer: (
                        offer["comparison_price"] is None,
                        offer["comparison_price"]
                        if offer["comparison_price"] is not None
                        else offer["sale_price"],
                    ),
                )
            )
        return sorted(
            selected,
            key=lambda offer: (
                offer["comparison_price"] is None,
                offer["comparison_price"]
                if offer["comparison_price"] is not None
                else offer["sale_price"],
                offer["store_name"].casefold(),
            ),
        )

    @classmethod
    def get_game_detail(cls, game_id):
        game = db.session.get(Game, game_id)
        if game is None:
            return None

        offers = cls._best_offer_per_store(
            [
                cls._offer(deal)
                for deal in DealService.get_active_deals_for_game(game_id)
            ]
        )
        comparable = [
            offer for offer in offers if offer["comparison_price"] is not None
        ]
        comparison_available = bool(offers) and len(comparable) == len(offers)
        cheapest_price = (
            min(offer["comparison_price"] for offer in comparable)
            if comparison_available
            else None
        )
        if comparison_available:
            for offer in comparable:
                offer["is_cheapest"] = offer["comparison_price"] == cheapest_price

        return {
            "game": game,
            "offers": offers,
            "cheapest_offers": [
                offer for offer in offers if offer["is_cheapest"]
            ],
            "comparison_currency": "IDR",
            "comparison_available": comparison_available,
            "steam_rating_percent": game.steam_rating_percent,
            "steam_rating_count": game.steam_rating_count,
        }


__all__ = ["GameDetailService"]
