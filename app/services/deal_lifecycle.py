"""Shared deal lifecycle rules for Steam and CheapShark records."""

from datetime import timedelta

from app.utils.time import local_now


STEAM_SOURCE = "steam_scraper"
STEAM_FALLBACK_DAYS = 14


def _valid_datetime(value):
    return value if value is not None else None


def apply_deal_record(deal, record, now=None):
    """Apply a normalized deal record while preserving lifecycle timestamps."""
    now = now or local_now()
    incoming_on_sale = bool(record.get("is_on_sale", True))
    incoming_external_id = record.get("external_deal_id")
    external_id_changed = (
        incoming_external_id is not None
        and deal.external_deal_id is not None
        and str(incoming_external_id) != str(deal.external_deal_id)
    )
    new_cycle = deal.first_seen_at is None or not deal.is_active or external_id_changed

    if new_cycle:
        deal.first_seen_at = _valid_datetime(record.get("first_seen_at")) or now
        deal.ended_at = None
        deal.end_reason = None
    elif deal.first_seen_at is None:
        deal.first_seen_at = _valid_datetime(record.get("first_seen_at")) or now

    for field in (
        "normal_price",
        "sale_price",
        "discount_percent",
        "deal_url",
        "external_deal_id",
    ):
        value = record.get(field)
        if value is not None:
            setattr(deal, field, value)

    deal.fetched_at = now
    deal.last_seen_at = now
    deal.is_on_sale = incoming_on_sale

    if incoming_on_sale:
        deal.is_active = True
        deal.ended_at = None
        deal.end_reason = None
        source_end = record.get("deal_end_date")
        if source_end is not None:
            deal.deal_end_date = source_end
        elif deal.source == STEAM_SOURCE and (
            new_cycle or deal.deal_end_date is None
        ):
            deal.deal_end_date = deal.first_seen_at + timedelta(days=STEAM_FALLBACK_DAYS)
    else:
        end_deal(deal, "not_on_sale", now=now)

    return deal


def end_deal(deal, reason, now=None):
    """Mark a deal ended without overwriting the original end timestamp."""
    now = now or local_now()
    deal.is_active = False
    deal.is_on_sale = False
    if deal.ended_at is None:
        deal.ended_at = now
    deal.end_reason = reason
    return deal
