"""Game normalization, validation, matching, and persistence services."""

import logging
import re
from datetime import date
from decimal import Decimal

from flask import current_app

from app.collectors.steam_release_bot import SteamReleaseBot
from app.extensions import db
from app.models.game import Game, GameGenre, GameProduct, GameTag, Genre, PriceHistory
from app.models.job_run import JobRun
from app.models.store import Store
from app.utils.time import local_now, local_today

log = logging.getLogger(__name__)


def normalize_game_name(value):
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(
        r"\b(standard|deluxe|gold|ultimate|edition|game of the year)\b", " ", value
    )
    return re.sub(r"\s+", " ", value).strip()


def validate_release_record(record):
    errors = []
    if not record.get("steam_app_id"):
        errors.append("steam_app_id wajib diisi")
    if not record.get("name"):
        errors.append("name wajib diisi")
    if not isinstance(record.get("release_date"), date):
        errors.append("release_date tidak valid")
    for field in ("regular_price", "sale_price"):
        value = record.get(field)
        if value is not None and (not isinstance(value, Decimal) or value < 0):
            errors.append(f"{field} harus berupa harga >= 0")
    discount = record.get("discount_percent", 0)
    if not isinstance(discount, (int, float, Decimal)) or not 0 <= discount <= 100:
        errors.append("discount_percent harus berada di antara 0 dan 100")
    if not record.get("currency"):
        errors.append("currency wajib diisi")
    return errors


class GameService:
    job_name = "steam_releases"

    def sync_recently_released(self, days=None, limit=None, collector=None):
        days = days or current_app.config["RECENTLY_RELEASED_DAYS"]
        collector = collector or SteamReleaseBot()
        job_run = JobRun(job_name=self.job_name, status="running")
        db.session.add(job_run)
        db.session.commit()

        try:
            raw_records = collector.fetch(days=days, limit=limit)
            normalized_records = [collector.normalize(record) for record in raw_records]
            job_run.records_fetched = len(normalized_records)
            saved = 0
            errors = []
            failed_urls = getattr(collector, "failed_urls", [])
            if failed_urls:
                errors.append(
                    f"{len(failed_urls)} request Steam gagal; data yang berhasil "
                    "diambil tetap diproses"
                )
            for record in normalized_records:
                validation_errors = validate_release_record(record)
                if validation_errors:
                    message = "; ".join(validation_errors)
                    log.warning("Record Steam dilewati: %s", message)
                    errors.append(f"{record.get('name') or 'unknown'}: {message}")
                    continue
                try:
                    # Isolate one bad record so a constraint or malformed
                    # value does not roll back all valid releases in the job.
                    with db.session.begin_nested():
                        self._upsert_release_record(record)
                    saved += 1
                except Exception as exc:
                    message = f"{record.get('name') or 'unknown'}: {exc}"
                    errors.append(message)
                    log.exception("Gagal menyimpan release %s", record.get("name"))

            db.session.commit()
            job_run.finished_at = local_now()
            job_run.status = "success"
            job_run.records_saved = saved
            if errors and saved:
                job_run.status = "partial"
                job_run.error_message = " | ".join(errors)[:4000]
            elif errors and not saved:
                job_run.status = "failed"
                job_run.error_message = " | ".join(errors)[:4000]
            db.session.commit()
            return {
                "status": job_run.status,
                "records_fetched": len(normalized_records),
                "records_saved": saved,
                "errors": errors,
            }
        except Exception as exc:
            db.session.rollback()
            failed_run = db.session.get(JobRun, job_run.id)
            if failed_run:
                failed_run.finished_at = local_now()
                failed_run.status = "failed"
                failed_run.error_message = str(exc)[:4000]
                db.session.commit()
            log.exception("Job %s gagal", self.job_name)
            return {
                "status": "failed",
                "records_fetched": 0,
                "records_saved": 0,
                "errors": [str(exc)],
            }

    def _upsert_release_record(self, record):
        app_id = record["steam_app_id"]
        game = Game.query.filter_by(steam_app_id=app_id).one_or_none()
        if game is None:
            game = Game(steam_app_id=app_id, name=record["name"])
            db.session.add(game)
            db.session.flush()

        for field in (
            "name",
            "description",
            "release_date",
            "cover_image",
            "developer",
            "publisher",
        ):
            value = record.get(field)
            if value not in (None, ""):
                setattr(game, field, value)

        store = Store.query.filter_by(name="Steam").one_or_none()
        if store is None:
            store = Store(
                name="Steam",
                website_url="https://store.steampowered.com/",
                external_store_id="steam",
                source="steam",
            )
            db.session.add(store)
            db.session.flush()

        product = GameProduct.query.filter_by(
            store_id=store.id,
            external_product_id=record["external_product_id"],
            region=record["region"],
        ).one_or_none()
        if product is None:
            product = GameProduct(
                game_id=game.id,
                store_id=store.id,
                external_product_id=record["external_product_id"],
                region=record["region"],
                currency=record["currency"],
            )
            db.session.add(product)
            db.session.flush()
        product.game_id = game.id
        product.product_url = record.get("product_url")
        product.currency = record["currency"]

        for genre_name in record.get("genres", []):
            genre = Genre.query.filter_by(name=genre_name).one_or_none()
            if genre is None:
                genre = Genre(name=genre_name)
                db.session.add(genre)
                db.session.flush()
            if GameGenre.query.filter_by(game_id=game.id, genre_id=genre.id).first() is None:
                db.session.add(GameGenre(game_id=game.id, genre_id=genre.id))

        for tag_name in record.get("tags", []):
            if GameTag.query.filter_by(game_id=game.id, tag=tag_name).first() is None:
                db.session.add(GameTag(game_id=game.id, tag=tag_name))

        if record.get("sale_price") is not None and record.get("regular_price") is not None:
            today = local_today()
            snapshot = PriceHistory.query.filter_by(
                game_product_id=product.id, recorded_date=today
            ).one_or_none()
            if snapshot is None:
                db.session.add(
                    PriceHistory(
                        game_product_id=product.id,
                        price=record["sale_price"],
                        regular_price=record["regular_price"],
                        currency=record["currency"],
                        recorded_date=today,
                        source=record["source"],
                    )
                )
