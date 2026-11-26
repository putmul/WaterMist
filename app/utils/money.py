"""Currency conversion and display helpers."""

from decimal import Decimal, InvalidOperation

from flask import current_app


def to_idr(amount, currency):
    """Convert a price to IDR using configured rates; return None if unavailable."""
    try:
        amount = Decimal(str(amount))
        currency = (currency or "").upper()
        rates = current_app.config.get("PRICE_EXCHANGE_RATES", {})
        source_rate = Decimal(str(rates.get(currency)))
        idr_rate = Decimal(str(rates.get("IDR")))
        if source_rate <= 0 or idr_rate <= 0:
            return None
        return (amount * source_rate / idr_rate).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def format_idr(amount, currency="IDR"):
    converted = to_idr(amount, currency)
    return f"Rp {converted:,.0f}".replace(",", ".") if converted is not None else None
