"""Parse natural-language search constraints used by semantic deal search."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


_PRICE_RE = re.compile(
    r"(?P<prefix>di\s+bawah|di\s+atas|kurang\s+dari|lebih\s+dari|"
    r"maks(?:imal)?|minimum|min(?:imal)?|under|below|less\s+than|"
    r"more\s+than|above|up\s+to|hingga|sampai)?\s*"
    r"(?P<currency>rp|idr|rupiah|\$|usd|dollar|€|eur|euro|£|gbp|pound)?\s*"
    r"(?P<number>\d[\d.,]*)\s*"
    r"(?P<unit>ribu|rb|k|juta|jt|million|m)?",
    re.IGNORECASE,
)
_DISCOUNT_RE = re.compile(
    r"(?P<prefix>diskon|min(?:imal)?|minimum|at\s+least|discount)?\s*"
    r"(?P<number>\d+(?:[.,]\d+)?)\s*%\s*(?:discount|diskon)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SearchIntent:
    semantic_text: str
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    currency: str | None = None
    min_discount: Decimal | None = None
    max_discount: Decimal | None = None
    sort: str = "relevance"

    @property
    def has_structured_constraints(self):
        return any(
            value is not None
            for value in (
                self.min_price,
                self.max_price,
                self.min_discount,
                self.max_discount,
            )
        ) or self.sort != "relevance"


def _parse_number(value, unit=""):
    value = (value or "").strip()
    unit = (unit or "").lower()
    if not value:
        return None

    try:
        if "." in value and "," in value:
            if value.rfind(",") > value.rfind("."):
                value = value.replace(".", "").replace(",", ".")
            else:
                value = value.replace(",", "")
        elif "." in value:
            tail = value.rsplit(".", 1)[1]
            value = value.replace(".", "") if len(tail) == 3 else value
        elif "," in value:
            tail = value.rsplit(",", 1)[1]
            value = value.replace(",", "") if len(tail) == 3 else value.replace(",", ".")
        number = Decimal(value)
    except InvalidOperation:
        return None

    if unit in {"ribu", "rb", "k"}:
        number *= 1000
    elif unit in {"juta", "jt", "million", "m"}:
        number *= 1000000
    return number.quantize(Decimal("0.01"))


def _currency(value, default_currency):
    value = (value or "").lower()
    if value in {"rp", "idr", "rupiah"}:
        return "IDR"
    if value in {"$", "usd", "dollar"}:
        return "USD"
    if value in {"€", "eur", "euro"}:
        return "EUR"
    if value in {"£", "gbp", "pound"}:
        return "GBP"
    return default_currency


def _number(value):
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def parse_search_query(query, default_currency="IDR"):
    """Return semantic text and hard constraints extracted from free text."""
    original = " ".join((query or "").split())[:200]
    if not original:
        return SearchIntent(semantic_text="")

    semantic_text = original
    min_price = max_price = None
    currency = None
    min_discount = max_discount = None

    for match in _PRICE_RE.finditer(original):
        if not any(
            match.group(name)
            for name in ("prefix", "currency", "unit")
        ):
            continue
        number = _parse_number(match.group("number"), match.group("unit"))
        if number is None:
            continue
        prefix = (match.group("prefix") or "").lower()
        parsed_currency = _currency(match.group("currency"), default_currency)
        currency = currency or parsed_currency
        if prefix in {"di atas", "lebih dari", "more than", "above"}:
            min_price = number
        else:
            max_price = number
        semantic_text = semantic_text.replace(match.group(0), " ")

    for match in _DISCOUNT_RE.finditer(original):
        number = _number(match.group("number"))
        if number is None or number < 0 or number > 100:
            continue
        prefix = (match.group("prefix") or "").lower()
        if prefix in {"min", "minimal", "minimum", "at least"}:
            min_discount = number
        else:
            max_discount = number
        semantic_text = semantic_text.replace(match.group(0), " ")

    lowered = original.lower()
    sort = "relevance"
    sort_phrases = ()
    if any(token in lowered for token in ("diskon terbesar", "best discount", "highest discount")):
        sort = "discount"
        sort_phrases = ("diskon terbesar", "best discount", "highest discount")
    elif any(token in lowered for token in ("termurah", "harga terendah", "cheapest", "lowest price")):
        sort = "price"
        sort_phrases = ("termurah", "harga terendah", "cheapest", "lowest price")
    for phrase in sort_phrases:
        semantic_text = re.sub(re.escape(phrase), " ", semantic_text, flags=re.IGNORECASE)
    normalized = " ".join(semantic_text.split())

    return SearchIntent(
        semantic_text=normalized,
        min_price=min_price,
        max_price=max_price,
        currency=currency,
        min_discount=min_discount,
        max_discount=max_discount,
        sort=sort,
    )


__all__ = ["SearchIntent", "parse_search_query"]
