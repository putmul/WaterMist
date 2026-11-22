from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, render_template, request

from app.extensions import db
from app.services.deal_service import DealService
from app.services.search_query_parser import parse_search_query
from app.services.semantic_search_service import SemanticSearchService

deals_bp = Blueprint("deals", __name__, url_prefix="/deals")


@deals_bp.get("")
def deals():
    def decimal_arg(name):
        value = request.args.get(name, "").strip()
        if not value:
            return None
        try:
            parsed = Decimal(value)
            return parsed if parsed >= 0 else None
        except (InvalidOperation, ValueError):
            return None

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 24, type=int), 1), 100)
    query = request.args.get("q", "").strip()[:100]
    sort = request.args.get("sort", "relevance" if query else "discount")
    if sort not in {"relevance", "discount", "price", "name", "store"}:
        sort = "relevance" if query else "discount"
    filters = {
        "q": query,
        "store": request.args.get("store", "").strip()[:100],
        "min_discount": decimal_arg("min_discount"),
        "max_discount": decimal_arg("max_discount"),
        "min_price": decimal_arg("min_price"),
        "max_price": decimal_arg("max_price"),
        "sort": sort,
    }
    semantic_mode = False
    intent = parse_search_query(
        filters["q"], current_app.config.get("SEMANTIC_DEFAULT_CURRENCY", "IDR")
    )
    if filters["q"]:
        semantic_deals = SemanticSearchService().search(
            intent, store=filters["store"], sort=sort
        )
    else:
        semantic_deals = None

    if semantic_deals is not None:
        semantic_mode = True
        pagination = SemanticSearchService.paginate(semantic_deals, page, per_page)
    else:
        fallback_filters = dict(filters)
        if intent.has_structured_constraints:
            fallback_filters.update(
                {
                    "q": intent.semantic_text,
                    "min_price": intent.min_price,
                    "max_price": intent.max_price,
                    "min_discount": intent.min_discount,
                    "max_discount": intent.max_discount,
                    "sort": intent.sort if intent.sort != "relevance" else sort,
                    "currency": intent.currency,
                }
            )
        pagination = db.paginate(
            DealService().list_active_deals(fallback_filters),
            page=page,
            per_page=per_page,
            error_out=False,
        )
    return render_template(
        "deals.html",
        deals=pagination.items,
        pagination=pagination,
        stores=DealService.stores_with_active_deals(),
        updated_at=DealService.last_updated(),
        semantic_mode=semantic_mode,
        semantic_intent=intent,
        **filters,
    )
