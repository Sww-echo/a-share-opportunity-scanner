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


def _clean_float(value: object | None) -> float | None:
    text = _clean(value)
    if text is None:
        return None

    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"invalid market-cap value: {value}") from exc


def _format_number(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


@dataclass(frozen=True, slots=True)
class MarketCapSnapshotRecord:
    ts_code: str
    total_market_cap_billion_cny: float
    circulating_market_cap_billion_cny: float | None = None
    as_of_date: str | None = None
    symbol: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        if not self.ts_code.strip():
            raise ValueError("ts_code is required")
        if self.total_market_cap_billion_cny <= 0:
            raise ValueError("total_market_cap_billion_cny must be positive")
        if self.circulating_market_cap_billion_cny is not None:
            if self.circulating_market_cap_billion_cny < 0:
                raise ValueError(
                    "circulating_market_cap_billion_cny cannot be negative"
                )

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "MarketCapSnapshotRecord":
        ts_code = _clean(row.get("ts_code"))
        total_market_cap = _clean_float(row.get("total_market_cap_billion_cny"))

        if not ts_code or total_market_cap is None:
            raise ValueError(f"invalid market-cap snapshot row: {row}")

        return cls(
            ts_code=ts_code,
            total_market_cap_billion_cny=total_market_cap,
            circulating_market_cap_billion_cny=_clean_float(
                row.get("circulating_market_cap_billion_cny")
            ),
            as_of_date=_clean(row.get("as_of_date")),
            symbol=_clean(row.get("symbol")),
            name=_clean(row.get("name")),
        )

    def to_row(self) -> dict[str, str]:
        return {
            "ts_code": self.ts_code,
            "symbol": self.symbol or "",
            "name": self.name or "",
            "total_market_cap_billion_cny": _format_number(
                self.total_market_cap_billion_cny
            ),
            "circulating_market_cap_billion_cny": _format_number(
                self.circulating_market_cap_billion_cny
            ),
            "as_of_date": self.as_of_date or "",
        }
