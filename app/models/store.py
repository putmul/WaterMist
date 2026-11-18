"""Store model."""

from app.extensions import db

BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    website_url = db.Column(db.Text)
    external_store_id = db.Column(db.String(64), index=True)
    source = db.Column(db.String(64), index=True)

__all__ = ["Store"]
