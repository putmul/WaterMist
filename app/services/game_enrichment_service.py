"""Enrich Steam library games with metadata needed by recommendation profiles."""

import logging

from app.extensions import db
from app.models import Game, GameGenre, GameTag, Genre
from app.collectors.steam_release_bot import SteamReleaseBot


log = logging.getLogger(__name__)


class GameEnrichmentService:
    """Fetch and persist missing genre/tag/developer metadata per App ID."""

    def __init__(self, collector=None):
        self.collector = collector or SteamReleaseBot()

    def enrich_app_ids(self, app_ids):
        stats = {
            "requested": 0,
            "created_games": 0,
            "mapped_games": 0,
            "metadata_completed": 0,
            "metadata_skipped": 0,
            "failed": 0,
        }
        seen = set()
        for raw_app_id in app_ids or ():
            app_id = str(raw_app_id).strip()
            if not app_id.isdigit() or app_id in seen:
                continue
            seen.add(app_id)
            stats["requested"] += 1

            game = Game.query.filter_by(steam_app_id=app_id).one_or_none()
            if game is None:
                # This is a defensive fallback. SteamService normally creates
                # the basic record from GetOwnedGames first.
                game = Game(name=f"Steam App {app_id}", steam_app_id=app_id)
                db.session.add(game)
                db.session.flush()
                stats["created_games"] += 1
            stats["mapped_games"] += 1

            if self._has_recommendation_metadata(game):
                stats["metadata_skipped"] += 1
                continue

            try:
                record = self.collector.scrape_app_detail(
                    {"app_id": int(app_id), "url": f"https://store.steampowered.com/app/{app_id}/"}
                )
                if not record:
                    stats["failed"] += 1
                    continue
                with db.session.begin_nested():
                    self._apply_record(game, record)
                if self._has_recommendation_metadata(game):
                    stats["metadata_completed"] += 1
                else:
                    stats["metadata_skipped"] += 1
            except Exception as exc:
                stats["failed"] += 1
                log.warning("Enrichment Steam App %s gagal: %s", app_id, exc)

        db.session.flush()
        return stats

    @staticmethod
    def _has_recommendation_metadata(game):
        return bool(
            GameGenre.query.filter_by(game_id=game.id).first()
            or GameTag.query.filter_by(game_id=game.id).first()
            or game.developer
        )

    @staticmethod
    def _apply_record(game, record):
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

        for genre_name in record.get("genres", []):
            genre_name = str(genre_name).strip()
            if not genre_name:
                continue
            genre = Genre.query.filter_by(name=genre_name).one_or_none()
            if genre is None:
                genre = Genre(name=genre_name)
                db.session.add(genre)
                db.session.flush()
            exists = GameGenre.query.filter_by(
                game_id=game.id, genre_id=genre.id
            ).first()
            if exists is None:
                db.session.add(GameGenre(game_id=game.id, genre_id=genre.id))

        for tag_name in record.get("tags", []):
            tag_name = str(tag_name).strip()
            if not tag_name:
                continue
            exists = GameTag.query.filter_by(game_id=game.id, tag=tag_name).first()
            if exists is None:
                db.session.add(GameTag(game_id=game.id, tag=tag_name))

        db.session.flush()
        db.session.expire(game, ["genres", "tags"])


__all__ = ["GameEnrichmentService"]
