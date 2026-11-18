"""Common collector contract from the Foundation PRD."""

from abc import ABC, abstractmethod


class BaseCollector(ABC):
    """Every external source exposes fetch followed by normalize."""

    @abstractmethod
    def fetch(self, **kwargs):
        """Return raw records from the external source."""

    @abstractmethod
    def normalize(self, record):
        """Convert one raw record to the internal WaterVapor format."""
