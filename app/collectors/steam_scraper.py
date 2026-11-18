"""Reserved collector for Steam discount data (Module 02)."""

from .base import BaseCollector


class SteamDealsCollector(BaseCollector):
    def fetch(self, **kwargs):
        raise NotImplementedError("Steam deals collector belongs to Module 02")

    def normalize(self, record):
        raise NotImplementedError("Steam deals collector belongs to Module 02")
