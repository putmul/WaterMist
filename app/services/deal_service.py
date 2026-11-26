"""Deal synchronization, matching, persistence, and query services."""

import logging
from decimal import Decimal

from flask import current_app
from sqlalchemy import and_, case, func, not_, or_
from sqlalchemy.orm import aliased, joinedload

from app.collectors.cheapshark_client import CheapSharkClient
from app.collectors.steam_scraper import SteamDealsCollector
from app.extensions import db
from app.models.deal import Deal
from app.models.game import Game, GameProduct, GameTag, PriceHistory
from app.models.job_run import JobRun
from app.models.store import Store
from app.services.deal_lifecycle import apply_deal_record, end_deal
from app.services.game_service import normalize_game_name
from app.utils.time import local_now, local_today

log = logging.getLogger(__name__)


def validate_deal_record(record):
    errors = []
    for field in ("name", "external_product_id", "store_name", "deal_url", "source"):
        if not record.get(field):
            errors.append(f"{field} wajib diisi")
    for field in ("normal_price", "sale_price"):
        value = record.get(field)
        if not isinstance(value, Decimal) or value < 0:
            errors.append(f"{field} harus berupa harga >= 0")
    discount = record.get("discount_percent")
    if not isinstance(discount, (int, float, Decimal)) or not 0 <= discount <= 100:
        errors.append("discount_percent harus berada di antara 0 dan 100")
    if not record.get("region") or not record.get("currency"):
        errors.append("region dan currency wajib diisi")
    return errors


class DealService:
    job_name = "game_deals_daily"

    def __init__(self):
        # Reused only during one service instance / sync batch.
        self._game_name_cache = None

    @staticmethod
    def _idr_price_expression():
        rates = current_app.config.get("PRICE_EXCHANGE_RATES", {})
        idr_rate = Decimal(str(rates.get("IDR", 1)))
        converted = {
            str(currency).upper(): Deal.sale_price * (Decimal(str(rate)) / idr_rate)
            for currency, rate in rates.items()
            if rate and idr_rate
        }
        return case(
            converted,
            value=func.upper(GameProduct.currency),
            else_=None,
        )

    def sync_daily(self, steam_collector=None, cheapshark_client=None):
        """Run both sources while keeping each source isolated on failure."""
        self._game_name_cache = {
            normalize_game_name(name): game_id
            for game_id, name in db.session.query(Game.id, Game.name).all()
            if normalize_game_name(name)
        }
        job_run = JobRun(job_name=self.job_name, status="running")
        db.session.add(job_run)
        db.session.commit()

        fetched = 0
        saved = 0
        errors = []
        steam_collector = steam_collector or SteamDealsCollector()
        cheapshark_client = cheapshark_client or CheapSharkClient()

        if current_app.config.get("CHEAPSHARK_ENABLED", True):
            try:
                self._sync_stores(cheapshark_client)
                db.session.commit()
            except Exception as exc:  # pragma: no cover - exercised with integration failures
                errors.append(f"stores: {exc}")
                db.session.rollback()
                log.exception("Sinkronisasi stores CheapShark gagal")

        source_specs = [("steam_scraper", steam_collector)]
        if current_app.config.get("CHEAPSHARK_ENABLED", True):
            source_specs.append(("cheapshark", cheapshark_client))

        for source, collector in source_specs:
            try:
                raw_records = collector.fetch()
                normalized_records = [collector.normalize(record) for record in raw_records]
                fetched += len(normalized_records)
                seen_product_ids = set()
                invalid = 0
                for record in normalized_records:
                    if record.get("is_on_sale") is False:
                        try:
                            ended_deal = self._end_existing_record(record)
                            if ended_deal:
                                seen_product_ids.add(ended_deal.game_product_id)
                                saved += 1
                        except Exception:
                            invalid += 1
                            log.exception(
                                "Gagal mengakhiri deal %s", record.get("name")
                            )
                        continue
                    validation_errors = validate_deal_record(record)
                    if validation_errors:
                        invalid += 1
                        log.warning(
                            "Deal %s dilewati: %s",
                            record.get("name"),
                            "; ".join(validation_errors),
                        )
                        continue
                    try:
                        with db.session.begin_nested():
                            deal = self._upsert_record(record, cheapshark_client)
                        seen_product_ids.add(deal.game_product_id)
                        saved += 1
                    except Exception as exc:
                        invalid += 1
                        log.exception("Gagal menyimpan deal %s", record.get("name"))
                        continue

                if invalid:
                    errors.append(f"{source}: {invalid} record invalid/gagal disimpan")
                # An empty or entirely invalid response can indicate a parser
                # change or an upstream problem. Never deactivate the complete
                # previous source snapshot in that situation.
                if (
                    getattr(collector, "last_fetch_complete", False)
                    and normalized_records
                    and seen_product_ids
                ):
                    self._mark_missing_deals_inactive(source, seen_product_ids)
                if normalized_records and not getattr(collector, "failed_urls", []):
                    self._expire_deals(source)
                # Commit each source independently so a later source failure cannot
                # roll back data that was already collected successfully.
                db.session.commit()
            except Exception as exc:
                errors.append(f"{source}: {exc}")
                db.session.rollback()
                log.exception("Sinkronisasi %s gagal", source)

        try:
            self._save_price_snapshots()
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            errors.append(f"price_history: {exc}")
            log.exception("Snapshot harga gagal disimpan")

        job_run = db.session.get(JobRun, job_run.id)
        job_run.finished_at = local_now()
        job_run.records_fetched = fetched
        job_run.records_saved = saved
        job_run.status = "failed" if not saved and errors else "partial" if errors else "success"
        job_run.error_message = " | ".join(errors)[:4000] if errors else None
        db.session.commit()
        return {
            "status": job_run.status,
            "records_fetched": fetched,
            "records_saved": saved,
            "errors": errors,
        }

    def _sync_stores(self, client):
        for record in client.fetch_stores():
            external_id = str(record.get("storeID"))
            name = (record.get("storeName") or f"CheapShark Store {external_id}").strip()
            store = Store.query.filter_by(name=name).one_or_none()
            if store is None:
                store = Store(name=name)
                db.session.add(store)
            store.external_store_id = external_id
            store.source = "cheapshark"
            store.website_url = record.get("storeLink") or store.website_url
        db.session.flush()

    def _get_or_create_store(self, record):
        name = record["store_name"]
        source = record["source"]
        if name.casefold() == "steam":
            store = Store.query.filter(func.lower(Store.name) == "steam").one_or_none()
        else:
            store = None
            if record.get("store_external_id"):
                store = Store.query.filter_by(
                    external_store_id=str(record["store_external_id"]), source="cheapshark"
                ).one_or_none()
            if store is None:
                store = Store.query.filter_by(name=name).one_or_none()
        if store is None:
            store = Store(
                name=name,
                external_store_id=record.get("store_external_id"),
                source="steam" if source == "steam_scraper" else "cheapshark",
                website_url=(
                    "https://store.steampowered.com/"
                    if name.casefold() == "steam"
                    else None
                ),
            )
            db.session.add(store)
            db.session.flush()
        return store

    def _find_game(self, record, store, cheapshark_client):
        steam_app_id = record.get("steam_app_id")
        if steam_app_id:
            game = Game.query.filter_by(steam_app_id=str(steam_app_id)).one_or_none()
            if game:
                return game

        product = GameProduct.query.filter_by(
            store_id=store.id,
            external_product_id=str(record["external_product_id"]),
            region=record["region"],
        ).one_or_none()
        if product:
            return product.game

        normalized_name = normalize_game_name(record["name"])
        if self._game_name_cache is None:
            self._game_name_cache = {
                normalize_game_name(name): game_id
                for game_id, name in db.session.query(Game.id, Game.name).all()
                if normalize_game_name(name)
            }
        cached_id = self._game_name_cache.get(normalized_name)
        if cached_id is not None:
            game = db.session.get(Game, cached_id)
            if game is not None:
                return game

        if record["source"] == "cheapshark" and normalized_name:
            try:
                suggestions = cheapshark_client.fetch_games_by_title(record["name"])
                for suggestion in suggestions:
                    suggestion_name = suggestion.get("title") or ""
                    if normalize_game_name(suggestion_name) != normalized_name:
                        continue
                    suggestion_app_id = suggestion.get("steamAppID")
                    if suggestion_app_id:
                        game = Game.query.filter_by(
                            steam_app_id=str(suggestion_app_id)
                        ).one_or_none()
                        if game:
                            return game
                        record["steam_app_id"] = str(suggestion_app_id)
                    break
            except Exception as exc:
                log.warning("Fallback matching CheapShark gagal untuk %s: %s", record["name"], exc)

        game = Game(name=record["name"], steam_app_id=record.get("steam_app_id"))
        db.session.add(game)
        db.session.flush()
        if normalized_name:
            self._game_name_cache[normalized_name] = game.id
        return game

    def _upsert_record(self, record, cheapshark_client):
        store = self._get_or_create_store(record)
        game = self._find_game(record, store, cheapshark_client)
        if record.get("cover_image") and not game.cover_image:
            game.cover_image = record["cover_image"]
        self._update_game_review_metadata(game, record)

        product = GameProduct.query.filter_by(
            store_id=store.id,
            external_product_id=str(record["external_product_id"]),
            region=record["region"],
        ).one_or_none()
        if product is None:
            product = GameProduct(
                game_id=game.id,
                store_id=store.id,
                external_product_id=str(record["external_product_id"]),
                product_url=record.get("product_url"),
                region=record["region"],
                currency=record["currency"],
            )
            db.session.add(product)
            db.session.flush()
        else:
            product.game_id = game.id
            product.product_url = record.get("product_url") or product.product_url
            product.currency = record["currency"]

        now = local_now()
        deal = Deal.query.filter_by(game_product_id=product.id, source=record["source"]).one_or_none()
        if deal is None:
            deal = Deal(game_product_id=product.id, source=record["source"])
            db.session.add(deal)
        apply_deal_record(deal, record, now=now)
        db.session.flush()
        return deal

    @staticmethod
    def _update_game_review_metadata(game, record):
        """Update review metadata only when the deal source has valid values."""
        review_metadata = {
            "steam_rating_percent": record.get("steam_rating_percent"),
            "steam_rating_count": record.get("steam_rating_count"),
            "steam_rating_text": record.get("steam_rating_text"),
        }
        updated = False
        for field, value in review_metadata.items():
            if value is not None and value != "":
                setattr(game, field, value)
                updated = True
        release_date = record.get("release_date")
        if release_date is not None:
            game.release_date = release_date
        if updated:
            game.review_source = record.get("review_source") or record.get("source")
            game.review_updated_at = local_now()

    def _end_existing_record(self, record):
        store = self._get_or_create_store(record)
        product = GameProduct.query.filter_by(
            store_id=store.id,
            external_product_id=str(record["external_product_id"]),
            region=record["region"],
        ).one_or_none()
        if product is None:
            return None
        deal = Deal.query.filter_by(
            game_product_id=product.id, source=record["source"]
        ).one_or_none()
        if deal is not None:
            end_deal(deal, "not_on_sale")
            db.session.flush()
        return deal

    @staticmethod
    def _mark_missing_deals_inactive(source, seen_product_ids):
        for deal in Deal.query.filter_by(source=source, is_active=True).all():
            if deal.game_product_id not in seen_product_ids:
                end_deal(deal, "not_found")

    @staticmethod
    def _expire_deals(source):
        now = local_now()
        reason = "fallback_14_days" if source == "steam_scraper" else "expired"
        for deal in Deal.query.filter(
            Deal.source == source,
            Deal.is_active.is_(True),
            Deal.deal_end_date.is_not(None),
            Deal.deal_end_date <= now,
        ).all():
            end_deal(deal, reason, now=now)

    def _save_price_snapshots(self):
        today = local_today()
        products = (
            GameProduct.query.join(Deal)
            .filter(Deal.is_active.is_(True))
            .distinct()
            .all()
        )
        for product in products:
            active_deals = [deal for deal in product.deals if deal.is_active]
            if not active_deals:
                continue
            deal = sorted(
                active_deals,
                key=lambda item: 0 if item.source == "steam_scraper" else 1,
            )[0]
            snapshot = PriceHistory.query.filter_by(
                game_product_id=product.id, recorded_date=today
            ).one_or_none()
            if snapshot is None:
                snapshot = PriceHistory(
                    game_product_id=product.id,
                    recorded_date=today,
                )
                db.session.add(snapshot)
            snapshot.price = deal.sale_price
            snapshot.regular_price = deal.normal_price
            snapshot.currency = product.currency
            snapshot.source = deal.source

    def list_active_deals(self, filters=None):
        filters = filters or {}
        stmt = (
            db.select(Deal)
            .join(Deal.game_product)
            .join(GameProduct.game)
            .join(GameProduct.store)
            .where(Deal.is_active.is_(True))
            .options(
                joinedload(Deal.game_product).joinedload(GameProduct.game),
                joinedload(Deal.game_product).joinedload(GameProduct.store),
            )
        )
        steam_deal = aliased(Deal)
        steam_product = aliased(GameProduct)
        steam_store = aliased(Store)
        steam_deal_exists = (
            db.select(steam_deal.id)
            .join(steam_product, steam_deal.game_product_id == steam_product.id)
            .join(steam_store, steam_product.store_id == steam_store.id)
            .where(
                steam_product.game_id == GameProduct.game_id,
                func.lower(steam_store.name) == "steam",
                steam_deal.source == "steam_scraper",
                steam_deal.is_active.is_(True),
            )
            .exists()
        )
        stmt = stmt.where(
            not_(
                and_(
                    Deal.source == "cheapshark",
                    func.lower(Store.name) == "steam",
                    steam_deal_exists,
                )
            )
        )
        nsfw_keywords = current_app.config.get("NSFW_BLACKLIST", ())
        if nsfw_keywords:
            nsfw_tag_exists = (
                db.select(GameTag.id)
                .where(
                    GameTag.game_id == Game.id,
                    or_(
                        *(
                            func.lower(GameTag.tag).like(
                                f"%{keyword.casefold()}%"
                            )
                            for keyword in nsfw_keywords
                            if keyword
                        )
                    ),
                )
                .exists()
            )
            stmt = stmt.where(not_(nsfw_tag_exists))
        if filters.get("q"):
            stmt = stmt.where(Game.name.ilike(f"%{filters['q']}%"))
        for token in filters.get("name_tokens", ()):
            if token:
                stmt = stmt.where(Game.name.ilike(f"%{token}%"))
        if filters.get("store"):
            stmt = stmt.where(Store.name == filters["store"])
        if filters.get("min_discount") is not None:
            stmt = stmt.where(Deal.discount_percent >= filters["min_discount"])
        if filters.get("max_discount") is not None:
            stmt = stmt.where(Deal.discount_percent <= filters["max_discount"])
        idr_price = self._idr_price_expression()
        if filters.get("min_price") is not None:
            stmt = stmt.where(idr_price.is_not(None), idr_price >= filters["min_price"])
        if filters.get("max_price") is not None:
            stmt = stmt.where(idr_price.is_not(None), idr_price <= filters["max_price"])
        if filters.get("currency"):
            stmt = stmt.where(GameProduct.currency == filters["currency"])

        # Keep one representative offer per game in listing/search results;
        # the detail page still exposes all active store offers.
        game_rank = func.row_number().over(
            partition_by=Game.id,
            order_by=(
                idr_price.is_(None).asc(),
                idr_price.asc(),
                case((Deal.source == "steam_scraper", 0), else_=1),
                Deal.id.asc(),
            ),
        ).label("game_rank")
        ranked_ids = stmt.with_only_columns(Deal.id, game_rank).order_by(None).subquery()
        stmt = stmt.where(
            Deal.id.in_(
                db.select(ranked_ids.c.id).where(ranked_ids.c.game_rank == 1)
            )
        )

        sort = filters.get("sort", "discount")
        if sort == "price":
            stmt = stmt.order_by(idr_price.is_(None).asc(), idr_price.asc(), Game.name.asc())
        elif sort == "name":
            stmt = stmt.order_by(Game.name.asc(), Deal.sale_price.asc())
        elif sort == "store":
            stmt = stmt.order_by(Store.name.asc(), Game.name.asc())
        elif sort == "popularity":
            # Review count is the popularity signal currently available on Game.
            # Put games without review metadata after games with a known count.
            stmt = stmt.order_by(
                Game.steam_rating_count.is_(None),
                Game.steam_rating_count.desc(),
                Game.name.asc(),
            )
        else:
            stmt = stmt.order_by(Deal.discount_percent.desc(), Game.name.asc())
        return stmt

    def search_by_name(self, filters=None):
        """Return active deals ranked by literal game-name relevance."""
        filters = dict(filters or {})
        query = (filters.get("q") or "").strip()
        if not query:
            return []

        stmt = self._literal_search_statement(filters)
        return db.session.scalars(stmt).unique().all()

    def _literal_search_statement(self, filters):
        query = (filters.get("q") or "").strip()
        stmt = self.list_active_deals(filters)
        has_matches = db.session.execute(
            stmt.order_by(None).limit(1)
        ).first()
        if not has_matches:
            tokens = tuple(dict.fromkeys(query.split()))
            if len(tokens) > 1:
                token_filters = dict(filters)
                token_filters["q"] = ""
                token_filters["name_tokens"] = tokens
                stmt = self.list_active_deals(token_filters)

        name = func.lower(Game.name)
        normalized_query = query.casefold()
        relevance = case(
            (name == normalized_query, 0),
            (name.like(f"{normalized_query}%"), 1),
            (name.like(f"%{normalized_query}%"), 2),
            else_=3,
        )
        sort = filters.get("sort", "relevance")
        if sort == "price":
            secondary = (Deal.sale_price.asc(), Game.name.asc())
        elif sort == "discount":
            secondary = (Deal.discount_percent.desc(), Game.name.asc())
        elif sort == "store":
            secondary = (func.lower(Store.name).asc(), Game.name.asc())
        elif sort == "popularity":
            secondary = (
                Game.steam_rating_count.is_(None),
                Game.steam_rating_count.desc(),
                Game.name.asc(),
            )
        else:
            secondary = (Game.name.asc(), Deal.sale_price.asc())
        return stmt.order_by(None).order_by(relevance, *secondary)

    def paginate_search_by_name(self, filters, page, per_page):
        stmt = self._literal_search_statement(filters)
        total = db.session.scalar(
            db.select(func.count()).select_from(stmt.order_by(None).subquery())
        ) or 0
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(max(page, 1), pages)
        items = db.session.scalars(
            stmt.offset((page - 1) * per_page).limit(per_page)
        ).unique().all()
        from app.services.semantic_search_service import SearchPagination

        return SearchPagination(items, page, per_page, total)

    def literal_game_ids(self, filters):
        stmt = self._literal_search_statement(filters)
        return db.session.scalars(
            stmt.with_only_columns(Game.id).distinct().order_by(None)
        ).unique().all()

    @staticmethod
    def stores_with_active_deals():
        return (
            Store.query.join(GameProduct, Store.id == GameProduct.store_id)
            .join(Deal, GameProduct.id == Deal.game_product_id)
            .filter(Deal.is_active.is_(True))
            .distinct()
            .order_by(Store.name.asc())
            .all()
        )

    @staticmethod
    def get_active_deals_for_game(game_id):
        """Return current, UI-visible deals for a Game Detail page."""
        deals = (
            Deal.query.join(GameProduct)
            .filter(GameProduct.game_id == game_id, Deal.is_active.is_(True))
            .join(GameProduct.store)
            .order_by(Deal.sale_price.asc())
            .all()
        )
        has_steam_scraper = any(
            deal.source == "steam_scraper"
            and deal.game_product.store.name.casefold() == "steam"
            for deal in deals
        )
        if not has_steam_scraper:
            return deals
        return [
            deal
            for deal in deals
            if not (
                deal.source == "cheapshark"
                and deal.game_product.store.name.casefold() == "steam"
            )
        ]

    @staticmethod
    def get_price_history(game_product_id):
        return PriceHistory.query.filter_by(game_product_id=game_product_id).order_by(
            PriceHistory.recorded_date.asc()
        ).all()

    @staticmethod
    def last_updated():
        return db.session.scalar(
            db.select(func.max(Deal.fetched_at)).where(Deal.is_active.is_(True))
        )
