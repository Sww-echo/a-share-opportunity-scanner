from __future__ import annotations

from abc import ABC, abstractmethod

from .models import MarketCapSnapshotRecord


class MarketCapSnapshotProvider(ABC):
    """Fetches normalized market-cap snapshots for the decision-support scanner."""

    provider_name: str

    @abstractmethod
    def fetch_snapshot(self) -> list[MarketCapSnapshotRecord]:
        """Return normalized market-cap snapshot records."""
