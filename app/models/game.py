"""Core game, product, metadata, and price history models."""

from datetime import date

from app.extensions import db
from app.models.store import Store
from app.utils.time import local_now

BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    steam_app_id = db.Column(db.String(32), unique=True, index=True)
    description = db.Column(db.Text)
    release_date = db.Column(db.Date, index=True)
    cover_image = db.Column(db.Text)
    developer = db.Column(db.String(255))
    publisher = db.Column(db.String(255))
    steam_rating_percent = db.Column(db.Integer)
    steam_rating_count = db.Column(BIGINT)
    steam_rating_text = db.Column(db.String(100))
    review_source = db.Column(db.String(64))
    review_updated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=local_now, onupdate=local_now
    )

    products = db.relationship(
        "GameProduct", back_populates="game", cascade="all, delete-orphan"
    )
    genres = db.relationship("Genre", secondary="game_genres", back_populates="games")
    tags = db.relationship("GameTag", back_populates="game", cascade="all, delete-orphan")


class GameProduct(db.Model):
    __tablename__ = "game_products"
    __table_args__ = (
        db.UniqueConstraint(
            "store_id", "external_product_id", "region", name="uq_game_product_identity"
        ),
    )

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    game_id = db.Column(
        BIGINT, db.ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    store_id = db.Column(
        BIGINT, db.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    external_product_id = db.Column(db.String(128), nullable=False)
    product_url = db.Column(db.Text)
    region = db.Column(db.String(16), nullable=False, default="ID")
    currency = db.Column(db.String(8), nullable=False, default="IDR")

    game = db.relationship("Game", back_populates="products")
    store = db.relationship("Store")
    prices = db.relationship(
        "PriceHistory", back_populates="game_product", cascade="all, delete-orphan"
    )
    deals = db.relationship(
        "Deal", back_populates="game_product", cascade="all, delete-orphan"
    )


class PriceHistory(db.Model):
    __tablename__ = "price_history"
    __table_args__ = (
        db.UniqueConstraint(
            "game_product_id", "recorded_date", name="uq_price_history_daily_snapshot"
        ),
    )

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    game_product_id = db.Column(
        BIGINT,
        db.ForeignKey("game_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price = db.Column(db.Numeric(12, 2), nullable=False)
    regular_price = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(8), nullable=False)
    recorded_at = db.Column(db.DateTime, nullable=False, default=local_now)
    recorded_date = db.Column(db.Date, nullable=False, default=date.today)
    source = db.Column(db.String(64), nullable=False)

    game_product = db.relationship("GameProduct", back_populates="prices")


class Genre(db.Model):
    __tablename__ = "genres"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    games = db.relationship("Game", secondary="game_genres", back_populates="genres")


class GameGenre(db.Model):
    __tablename__ = "game_genres"

    game_id = db.Column(
        BIGINT, db.ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id = db.Column(
        BIGINT, db.ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class GameTag(db.Model):
    __tablename__ = "game_tags"
    __table_args__ = (db.UniqueConstraint("game_id", "tag", name="uq_game_tag"),)

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    game_id = db.Column(
        BIGINT, db.ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    tag = db.Column(db.String(100), nullable=False)
    game = db.relationship("Game", back_populates="tags")
