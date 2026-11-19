"""Current deals collected from Steam and CheapShark."""

from datetime import datetime

from app.extensions import db

BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class Deal(db.Model):
    __tablename__ = "deals"
    __table_args__ = (
        db.UniqueConstraint(
            "game_product_id", "source", name="uq_deal_product_source"
        ),
    )

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    game_product_id = db.Column(
        BIGINT,
        db.ForeignKey("game_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normal_price = db.Column(db.Numeric(12, 2), nullable=False)
    sale_price = db.Column(db.Numeric(12, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False)
    deal_url = db.Column(db.Text, nullable=False)
    deal_end_date = db.Column(db.DateTime)
    source = db.Column(db.String(64), nullable=False, index=True)
    fetched_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    external_deal_id = db.Column(db.String(128), index=True)

    game_product = db.relationship("GameProduct", back_populates="deals")


__all__ = ["Deal"]
