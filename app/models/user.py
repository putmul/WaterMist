"""User identity, preference, Steam, and interaction models."""

from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.utils.time import local_now


BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    auth_provider = db.Column(db.String(32), nullable=False, default="local")
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    preference_mode = db.Column(db.String(20), nullable=False, default="quiz")
    onboarding_status = db.Column(
        db.String(30), nullable=False, default="not_started"
    )
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=local_now, onupdate=local_now
    )
    last_login_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)

    steam_profile = db.relationship(
        "UserSteamProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    preferences = db.relationship(
        "UserPreference", back_populates="user", cascade="all, delete-orphan"
    )
    quiz_answers = db.relationship(
        "UserQuizAnswer", back_populates="user", cascade="all, delete-orphan"
    )
    owned_games = db.relationship(
        "UserOwnedGame", back_populates="user", cascade="all, delete-orphan"
    )
    favorites = db.relationship(
        "UserFavorite", back_populates="user", cascade="all, delete-orphan"
    )
    interactions = db.relationship(
        "UserInteraction", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return bool(self.password_hash) and check_password_hash(
            self.password_hash, password
        )


class UserSteamProfile(db.Model):
    __tablename__ = "user_steam_profiles"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    steam_id = db.Column(db.String(32), nullable=False, unique=True, index=True)
    profile_url = db.Column(db.Text)
    visibility_status = db.Column(db.String(20), nullable=False, default="unknown")
    sync_status = db.Column(db.String(20), nullable=False, default="pending")
    last_synced_at = db.Column(db.DateTime)
    last_sync_error = db.Column(db.Text)
    connected_at = db.Column(db.DateTime, nullable=False, default=local_now)
    disconnected_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="steam_profile")


class UserOwnedGame(db.Model):
    __tablename__ = "user_owned_games"
    __table_args__ = (
        UniqueConstraint("user_id", "steam_app_id", name="uq_user_owned_steam_app"),
    )

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_id = db.Column(
        BIGINT, db.ForeignKey("games.id", ondelete="SET NULL"), nullable=True, index=True
    )
    steam_app_id = db.Column(db.String(32), nullable=False)
    playtime_minutes = db.Column(BIGINT, nullable=False, default=0)
    recent_playtime_minutes = db.Column(BIGINT, nullable=False, default=0)
    last_played_at = db.Column(db.DateTime)
    synced_at = db.Column(db.DateTime, nullable=False, default=local_now)

    user = db.relationship("User", back_populates="owned_games")
    game = db.relationship("Game")


class UserFavorite(db.Model):
    __tablename__ = "user_favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_user_favorite_game"),
    )

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_id = db.Column(
        BIGINT, db.ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)

    user = db.relationship("User", back_populates="favorites")
    game = db.relationship("Game")


class UserInteraction(db.Model):
    __tablename__ = "user_interactions"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_id = db.Column(
        BIGINT, db.ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interaction_type = db.Column(db.String(32), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now, index=True)

    user = db.relationship("User", back_populates="interactions")
    game = db.relationship("Game")


class UserQuizAnswer(db.Model):
    __tablename__ = "user_quiz_answers"
    __table_args__ = (
        UniqueConstraint("user_id", "question_key", name="uq_user_quiz_question"),
    )

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_key = db.Column(db.String(100), nullable=False)
    answer_value = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=local_now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=local_now, onupdate=local_now
    )

    user = db.relationship("User", back_populates="quiz_answers")


class UserPreference(db.Model):
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "feature_type", "feature_key", "source",
            name="uq_user_preference_signal",
        ),
    )

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        BIGINT, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_type = db.Column(db.String(30), nullable=False)
    feature_key = db.Column(db.String(255), nullable=False)
    preference_score = db.Column(db.Float, nullable=False, default=0.0)
    source = db.Column(db.String(30), nullable=False)
    confidence = db.Column(db.Float, nullable=False, default=1.0)
    profile_version = db.Column(db.String(32), nullable=False, default="v1")
    updated_at = db.Column(db.DateTime, nullable=False, default=local_now, onupdate=local_now)

    user = db.relationship("User", back_populates="preferences")


__all__ = [
    "User",
    "UserSteamProfile",
    "UserOwnedGame",
    "UserFavorite",
    "UserInteraction",
    "UserQuizAnswer",
    "UserPreference",
]
