from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request

from app.extensions import db
from app.services.deal_service import DealService

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
    sort = request.args.get("sort", "discount")
    if sort not in {"discount", "price", "name", "store"}:
        sort = "discount"
    filters = {
        "q": request.args.get("q", "").strip()[:100],
        "store": request.args.get("store", "").strip()[:100],
        "min_discount": decimal_arg("min_discount"),
        "max_discount": decimal_arg("max_discount"),
        "min_price": decimal_arg("min_price"),
        "max_price": decimal_arg("max_price"),
        "sort": sort,
    }
    pagination = db.paginate(
        DealService().list_active_deals(filters),
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
        **filters,
    )
