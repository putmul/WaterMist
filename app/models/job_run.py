"""Background collector execution history."""

from datetime import datetime

from app.extensions import db

BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class JobRun(db.Model):
    __tablename__ = "job_runs"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    job_name = db.Column(db.String(100), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="running")
    records_fetched = db.Column(db.Integer, nullable=False, default=0)
    records_saved = db.Column(db.Integer, nullable=False, default=0)
    error_message = db.Column(db.Text)
