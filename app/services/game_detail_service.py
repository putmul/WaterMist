"""Read-only data preparation for the game detail and deal comparison page."""

from decimal import Decimal, InvalidOperation

from flask import current_app

from app.extensions import db
from app.models.game import Game, GameProduct, PriceHistory
from app.services.deal_service import DealService
from app.utils.time import local_today


class GameDetailService:
    """Build a game detail view from the locally persisted data."""

    @staticmethod
    def _convert_price(amount, currency, base_currency):
        currency = (currency or "").upper()
        if currency == base_currency:
            return Decimal(amount).quantize(Decimal("0.01"))
        rates = current_app.config.get("PRICE_EXCHANGE_RATES", {})
        try:
            source_rate = Decimal(str(rates.get(currency)))
            base_rate = Decimal(str(rates.get(base_currency)))
        except (InvalidOperation, TypeError, ValueError):
            return None
        if source_rate <= 0 or base_rate <= 0:
            return None
        return (Decimal(amount) * source_rate / base_rate).quantize(Decimal("0.01"))

    @staticmethod
    def _comparison_price(deal):
        currency = (deal.game_product.currency or "").upper()
        base_currency = current_app.config.get(
            "PRICE_COMPARISON_CURRENCY", "IDR"
        ).upper()
        if currency == base_currency:
            return Decimal(deal.sale_price).quantize(Decimal("0.01"))

        rates = current_app.config.get("PRICE_EXCHANGE_RATES", {})
        try:
            source_rate = Decimal(str(rates.get(currency)))
            base_rate = Decimal(str(rates.get(base_currency)))
        except (InvalidOperation, TypeError, ValueError):
            return None
        if source_rate <= 0 or base_rate <= 0:
            return None
        return (Decimal(deal.sale_price) * source_rate / base_rate).quantize(
            Decimal("0.01")
        )

    @classmethod
    def _price_history(cls, game_id, base_currency):
        rows = (
            db.session.query(PriceHistory, GameProduct.currency)
            .join(GameProduct, PriceHistory.game_product_id == GameProduct.id)
            .filter(GameProduct.game_id == game_id)
            .order_by(PriceHistory.recorded_date.asc())
            .all()
        )
        today = local_today()
        months = []
        year, month = today.year, today.month
        for _ in range(12):
            months.append((year, month))
            month -= 1
            if month == 0:
                year -= 1
                month = 12
        months.reverse()

        prices_by_month = {key: [] for key in months}
        for snapshot, currency in rows:
            key = (snapshot.recorded_date.year, snapshot.recorded_date.month)
            if key not in prices_by_month:
                continue
            converted = cls._convert_price(snapshot.price, currency, base_currency)
            if converted is not None:
                prices_by_month[key].append(converted)

        monthly_prices = [min(values) for values in prices_by_month.values() if values]
        if not monthly_prices:
            return {"history": [], "history_low": None, "history_average": None, "history_current": None}

        low = min(monthly_prices)
        highest = max(monthly_prices)
        history = []
        for (year, month), values in prices_by_month.items():
            price = min(values) if values else None
            history.append({
                "label": f"{month:02d}/{str(year)[-2:]}",
                "price": price,
                "height": max(8, int(price / highest * 100)) if price is not None and highest else 8,
                "is_low": price == low,
            })
        return {
            "history": history,
            "history_low": low,
            "history_average": (sum(monthly_prices) / len(monthly_prices)).quantize(Decimal("0.01")),
            "history_current": next((point["price"] for point in reversed(history) if point["price"] is not None), None),
        }

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

        base_currency = current_app.config.get(
            "PRICE_COMPARISON_CURRENCY", "IDR"
        ).upper()
        history_data = cls._price_history(game_id, base_currency)
        return {
            "game": game,
            "offers": offers,
            "cheapest_offers": [
                offer for offer in offers if offer["is_cheapest"]
            ],
            "comparison_currency": base_currency,
            "comparison_available": comparison_available,
            "history_data": history_data,
            "steam_rating_percent": game.steam_rating_percent,
            "steam_rating_count": game.steam_rating_count,
        }


__all__ = ["GameDetailService"]
