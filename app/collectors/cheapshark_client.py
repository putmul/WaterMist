"""Reserved CheapShark adapter for Module 02."""

from .base import BaseCollector


class CheapSharkClient(BaseCollector):
    def fetch(self, **kwargs):
        raise NotImplementedError("CheapShark integration belongs to Module 02")

    def normalize(self, record):
        raise NotImplementedError("CheapShark integration belongs to Module 02")
