"""SQLAlchemy model exports."""

from .game import Game, GameGenre, GameProduct, GameTag, Genre, PriceHistory
from .deal import Deal
from .job_run import JobRun
from .store import Store
from .user import (
    User,
    UserFavorite,
    UserInteraction,
    UserOwnedGame,
    UserPreference,
    UserQuizAnswer,
    UserSteamProfile,
)
from .recommendation import Recommendation, RecommendationRun

__all__ = [
    "Game",
    "Deal",
    "GameGenre",
    "GameProduct",
    "GameTag",
    "Genre",
    "JobRun",
    "PriceHistory",
    "Store",
    "User",
    "UserSteamProfile",
    "UserOwnedGame",
    "UserFavorite",
    "UserInteraction",
    "UserQuizAnswer",
    "UserPreference",
    "Recommendation",
    "RecommendationRun",
]
