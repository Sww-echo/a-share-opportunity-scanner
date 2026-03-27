from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


def _clean(value: object | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


@dataclass(frozen=True, slots=True)
class StockListRecord:
    ts_code: str
    symbol: str
    name: str
    exchange: str
    board: str
    list_status: str = "L"
    list_date: str | None = None
    area: str | None = None
    industry: str | None = None
    is_hs: str | None = None

    def __post_init__(self) -> None:
        if not self.ts_code.strip():
            raise ValueError("ts_code is required")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not self.name.strip():
            raise ValueError("name is required")
        if not self.exchange.strip():
            raise ValueError("exchange is required")
        if not self.board.strip():
            raise ValueError("board is required")

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "StockListRecord":
        ts_code = _clean(row.get("ts_code"))
        symbol = _clean(row.get("symbol"))
        name = _clean(row.get("name"))
        exchange = _clean(row.get("exchange"))
        board = _clean(row.get("board"))

        if not ts_code or not symbol or not name or not exchange or not board:
            raise ValueError(f"invalid stock-list row: {row}")

        return cls(
            ts_code=ts_code,
            symbol=symbol,
            name=name,
            exchange=exchange,
            board=board,
            list_status=_clean(row.get("list_status")) or "L",
            list_date=_clean(row.get("list_date")),
            area=_clean(row.get("area")),
            industry=_clean(row.get("industry")),
            is_hs=_clean(row.get("is_hs")),
        )

    def to_row(self) -> dict[str, str]:
        return {
            "ts_code": self.ts_code,
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "board": self.board,
            "list_status": self.list_status,
            "list_date": self.list_date or "",
            "area": self.area or "",
            "industry": self.industry or "",
            "is_hs": self.is_hs or "",
        }
