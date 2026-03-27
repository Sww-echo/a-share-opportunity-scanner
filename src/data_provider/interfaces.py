from __future__ import annotations

from abc import ABC, abstractmethod

from .models import StockListRecord


class StockListProvider(ABC):
    """Fetches stock-list metadata for the decision-support scanner."""

    provider_name: str

    @abstractmethod
    def fetch_stock_list(self) -> list[StockListRecord]:
        """Return normalized stock-list records."""
