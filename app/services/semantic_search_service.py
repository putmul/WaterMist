"""Multilingual semantic search over active game deals."""

import json
import logging
import math
from dataclasses import dataclass, replace

from flask import current_app

from app.extensions import db
from app.models import Game
from app.services.deal_service import DealService
from app.services.search_query_parser import SearchIntent
from app.utils.time import local_now

log = logging.getLogger(__name__)


@dataclass
class SearchPagination:
    items: list
    page: int
    per_page: int
    total: int

    @property
    def pages(self):
        return max(math.ceil(self.total / self.per_page), 1)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1


class SemanticSearchService:
    _model = None
    _model_name = None
    _load_failed = False

    def __init__(self, encoder=None):
        self.encoder = encoder

    @classmethod
    def _load_model(cls):
        model_name = current_app.config["SEMANTIC_EMBEDDING_MODEL"]
        if cls._model is not None and cls._model_name == model_name:
            return cls._model
        if cls._load_failed and cls._model_name == model_name:
            return None
        try:
            from sentence_transformers import SentenceTransformer

            cls._model = SentenceTransformer(model_name)
            cls._model_name = model_name
            cls._load_failed = False
            return cls._model
        except Exception as exc:  # pragma: no cover - depends on local ML install
            cls._model_name = model_name
            cls._load_failed = True
            log.warning("Model semantic search tidak tersedia: %s", exc)
            return None

    @staticmethod
    def game_text(game):
        genres = " ".join(genre.name for genre in game.genres)
        tags = " ".join(tag.tag for tag in game.tags)
        return " ".join(
            value
            for value in (
                game.name,
                game.description,
                genres,
                tags,
                game.developer,
                game.publisher,
            )
            if value
        )

    def _encode(self, texts):
        if self.encoder is not None:
            values = self.encoder(texts)
        else:
            model = self._load_model()
            if model is None:
                return None
            values = model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=current_app.config["SEMANTIC_EMBEDDING_BATCH_SIZE"],
            )
        return [list(map(float, value)) for value in values]

    @staticmethod
    def _decode(value):
        if not value:
            return None
        try:
            decoded = json.loads(value)
            return list(map(float, decoded)) if decoded else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def cosine_similarity(left, right):
        if not left or not right or len(left) != len(right):
            return 0.0
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)

    @staticmethod
    def _sort_by_relevance(deals):
        """Sort semantic results by similarity before applying tie-breakers."""
        return sorted(
            deals,
            key=lambda deal: (
                -(deal.semantic_score or 0),
                -float(deal.discount_percent or 0),
                float(deal.sale_price or 0),
                deal.game_product.game.name.casefold(),
            ),
        )

    def rebuild_stale_embeddings(self, limit=None):
        if not current_app.config.get("SEMANTIC_SEARCH_ENABLED", True):
            return {"updated": 0, "failed": 0, "available": False}
        model_name = current_app.config["SEMANTIC_EMBEDDING_MODEL"]
        query = Game.query.filter(
            (Game.semantic_embedding.is_(None))
            | (Game.semantic_embedding_model != model_name)
            | (
                Game.semantic_embedding_updated_at.is_(None)
            )
            | (Game.semantic_embedding_updated_at < Game.updated_at)
        )
        if limit:
            query = query.limit(limit)
        games = query.all()
        if not games:
            return {"updated": 0, "failed": 0, "available": True}
        vectors = self._encode([self.game_text(game) for game in games])
        if vectors is None:
            return {"updated": 0, "failed": len(games), "available": False}
        now = local_now()
        for game, vector in zip(games, vectors):
            game.semantic_embedding = json.dumps(vector, separators=(",", ":"))
            game.semantic_embedding_model = model_name
            game.semantic_embedding_updated_at = now
        db.session.commit()
        return {"updated": len(games), "failed": 0, "available": True}

    def search(
        self,
        intent: SearchIntent,
        store=None,
        sort=None,
        filters=None,
        exclude_game_ids=None,
    ):
        """Return ranked active deals, or None when semantic encoding is unavailable."""
        if not current_app.config.get("SEMANTIC_SEARCH_ENABLED", True):
            return None
        requested_sort = sort or intent.sort
        if requested_sort == "relevance" and intent.sort != "relevance":
            requested_sort = intent.sort
        ranking_intent = replace(intent, sort=requested_sort)
        search_filters = {
            "q": "",
            "store": store,
            "min_discount": intent.min_discount,
            "max_discount": intent.max_discount,
            "min_price": intent.min_price,
            "max_price": intent.max_price,
            "currency": intent.currency,
            "sort": "discount",
        }
        for field in (
            "store",
            "min_discount",
            "max_discount",
            "min_price",
            "max_price",
            "currency",
        ):
            if filters and filters.get(field) is not None:
                search_filters[field] = filters[field]

        deals = db.session.scalars(
            DealService().list_active_deals(search_filters)
        ).unique().all()
        if intent.currency:
            deals = [
                deal
                for deal in deals
                if deal.game_product.currency.upper() == intent.currency.upper()
            ]
        exclude_game_ids = set(exclude_game_ids or ())
        if exclude_game_ids:
            deals = [
                deal
                for deal in deals
                if deal.game_product.game.id not in exclude_game_ids
            ]

        if not intent.semantic_text:
            for deal in deals:
                deal.semantic_score = None
            return self._sort_structured(deals, ranking_intent)

        query_vector = self._encode([intent.semantic_text])
        if not query_vector:
            return None
        query_vector = query_vector[0]
        games = []
        seen = set()
        for deal in deals:
            game = deal.game_product.game
            if game.id not in seen:
                seen.add(game.id)
                games.append(game)

        missing = [
            game
            for game in games
            if not game.semantic_embedding
            or game.semantic_embedding_model
            != current_app.config["SEMANTIC_EMBEDDING_MODEL"]
        ]
        missing_vectors = self._encode([self.game_text(game) for game in missing]) if missing else []
        vector_by_game = {
            game.id: self._decode(game.semantic_embedding)
            for game in games
            if game not in missing
        }
        vector_by_game.update(
            {game.id: vector for game, vector in zip(missing, missing_vectors or [])}
        )

        minimum = current_app.config["SEMANTIC_SEARCH_MIN_SCORE"]
        ranked = []
        for deal in deals:
            score = self.cosine_similarity(
                query_vector, vector_by_game.get(deal.game_product.game.id)
            )
            if score < minimum:
                continue
            deal.semantic_score = score
            ranked.append(deal)
        ranked = self._sort_by_relevance(ranked)
        return ranked[: current_app.config["SEMANTIC_SEARCH_TOP_K"]]

    @staticmethod
    def _sort_structured(deals, intent):
        if intent.sort == "price":
            return sorted(deals, key=lambda deal: (float(deal.sale_price), deal.game_product.game.name.casefold()))
        return sorted(
            deals,
            key=lambda deal: (-float(deal.discount_percent or 0), deal.game_product.game.name.casefold()),
        )

    @staticmethod
    def paginate(items, page, per_page):
        total = len(items)
        pages = max(math.ceil(total / per_page), 1)
        page = min(max(page, 1), pages)
        start = (page - 1) * per_page
        return SearchPagination(items[start : start + per_page], page, per_page, total)


__all__ = ["SearchPagination", "SemanticSearchService"]
