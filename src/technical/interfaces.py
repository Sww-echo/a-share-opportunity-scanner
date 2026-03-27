from __future__ import annotations

from abc import ABC, abstractmethod

from .models import TechnicalSnapshotRecord


class TechnicalSnapshotProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def fetch_snapshot(self) -> list[TechnicalSnapshotRecord]:
        """Fetch normalized technical facts for scanner input."""
