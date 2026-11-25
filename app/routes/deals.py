import logging
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, render_template, request, url_for

from app.extensions import db
from app.services.deal_service import DealService
from app.services.search_query_parser import parse_search_query
from app.services.semantic_search_service import SemanticSearchService

deals_bp = Blueprint("deals", __name__, url_prefix="/deals")
log = logging.getLogger(__name__)


def _decimal_arg(name):
    value = request.args.get(name, "").strip()
    if not value:
        return None
    try:
        parsed = Decimal(value)
        return parsed if parsed >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def _search_context():
    """Build one consistent search context for page and semantic requests."""
    query = request.args.get("q", "").strip()[:100]
    sort = request.args.get("sort", "relevance" if query else "discount")
    if sort not in {
        "relevance",
        "discount",
        "price",
        "name",
        "store",
        "popularity",
    }:
        sort = "relevance" if query else "discount"

    filters = {
        "q": query,
        "store": request.args.get("store", "").strip()[:100],
        "min_discount": _decimal_arg("min_discount"),
        "max_discount": _decimal_arg("max_discount"),
        "min_price": _decimal_arg("min_price"),
        "max_price": _decimal_arg("max_price"),
        "sort": sort,
    }
    intent = parse_search_query(
        query, current_app.config.get("SEMANTIC_DEFAULT_CURRENCY", "IDR")
    )
    search_filters = dict(filters)
    for field in ("min_discount", "max_discount", "min_price", "max_price"):
        if search_filters[field] is None:
            search_filters[field] = getattr(intent, field)
    if intent.currency:
        search_filters["currency"] = intent.currency
    return filters, search_filters, intent


def _string_value(value):
    return "" if value is None else str(value)


def _looks_descriptive_query(query):
    words = {word.casefold() for word in query.split()}
    descriptive_markers = {
        "game",
        "cari",
        "ingin",
        "mau",
        "dengan",
        "untuk",
        "yang",
        "seperti",
        "cerita",
        "story",
        "horror",
        "horor",
        "psikologis",
        "santai",
        "teman",
        "story-rich",
    }
    return len(words) >= 3 or bool(words & descriptive_markers)


def _semantic_config(search_filters, intent, literal_game_ids):
    return {
        "url": url_for("deals.semantic_results"),
        "has_semantic_query": bool(intent.semantic_text),
        "params": {
            "q": search_filters["q"],
            "store": search_filters["store"],
            "min_discount": _string_value(search_filters["min_discount"]),
            "max_discount": _string_value(search_filters["max_discount"]),
            "min_price": _string_value(search_filters["min_price"]),
            "max_price": _string_value(search_filters["max_price"]),
            "sort": search_filters["sort"],
            "exclude_game_ids": ",".join(map(str, literal_game_ids)),
            "literal_count": str(len(literal_game_ids)),
        },
    }


@deals_bp.get("")
def deals():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 24, type=int), 1), 100)
    filters, search_filters, intent = _search_context()

    if filters["q"]:
        literal_deals = DealService().search_by_name(search_filters)
        pagination = SemanticSearchService.paginate(literal_deals, page, per_page)
        literal_game_ids = sorted(
            {deal.game_product.game.id for deal in literal_deals}
        )
    else:
        literal_deals = None
        literal_game_ids = []
        pagination = db.paginate(
            DealService().list_active_deals(search_filters),
            page=page,
            per_page=per_page,
            error_out=False,
        )

    semantic_config = _semantic_config(search_filters, intent, literal_game_ids)
    return render_template(
        "deals.html",
        deals=pagination.items,
        pagination=pagination,
        stores=DealService.stores_with_active_deals(),
        updated_at=DealService.last_updated(),
        semantic_mode=False,
        semantic_intent=intent,
        literal_deals_found=bool(literal_deals),
        semantic_config=semantic_config,
        page=page,
        **filters,
    )


@deals_bp.get("/semantic")
def semantic_results():
    filters, search_filters, intent = _search_context()
    try:
        exclude_game_ids = {
            int(value)
            for value in request.args.get("exclude_game_ids", "").split(",")
            if value.strip().isdigit()
        }
    except (TypeError, ValueError):
        exclude_game_ids = set()

    literal_count = request.args.get("literal_count", 0, type=int) or 0
    semantic_deals = []
    available = True
    if intent.semantic_text:
        try:
            semantic_deals = SemanticSearchService().search(
                intent,
                store=filters["store"],
                sort="relevance",
                filters=search_filters,
                exclude_game_ids=exclude_game_ids,
            )
            if semantic_deals is None:
                semantic_deals = []
                available = False
        except Exception:  # pragma: no cover - depends on external ML runtime
            log.exception("Semantic search request gagal")
            semantic_deals = []
            available = False

    if semantic_deals:
        heading = (
            "Mungkin Anda juga tertarik"
            if literal_count
            else (
                "Berdasarkan pencarian Anda, mungkin game ini cocok untuk Anda"
                if _looks_descriptive_query(filters["q"])
                else "Mungkin Anda mencari game ini?"
            )
        )
        message = None
    elif not available:
        heading = None
        message = "Rekomendasi berdasarkan makna belum dapat dimuat."
    elif literal_count:
        heading = None
        message = "Tidak ada rekomendasi tambahan berdasarkan makna untuk pencarian ini."
    else:
        heading = None
        message = (
            "Berdasarkan pencarian Anda, belum ada rekomendasi yang cukup cocok."
            if _looks_descriptive_query(filters["q"])
            else "Mungkin Anda mencari game lain? Kami belum menemukan hasil yang cocok."
        )

    display_limit = current_app.config.get("SEMANTIC_SEARCH_DISPLAY_LIMIT", 12)
    return render_template(
        "deals_semantic.html",
        deals=(semantic_deals or [])[:display_limit],
        heading=heading,
        message=message,
        semantic_mode=True,
    )
