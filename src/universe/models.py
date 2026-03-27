from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _clean(value: object | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _parse_flag(value: object | None) -> bool:
    text = (_clean(value) or "").upper()
    return text in {"Y", "YES", "TRUE", "1"}


@dataclass(frozen=True, slots=True)
class UniverseBuildConfig:
    allowed_list_statuses: tuple[str, ...] = ("L",)
    exclude_st: bool = True


@dataclass(frozen=True, slots=True)
class UniverseRecord:
    ts_code: str
    symbol: str
    name: str
    exchange: str
    board: str
    list_status: str
    list_date: str | None
    area: str | None
    industry: str | None
    is_hs: str | None
    is_st: bool
    eligible: bool
    exclude_reason: str | None = None

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "UniverseRecord":
        ts_code = _clean(row.get("ts_code"))
        symbol = _clean(row.get("symbol"))
        name = _clean(row.get("name"))
        exchange = _clean(row.get("exchange"))
        board = _clean(row.get("board"))

        if not ts_code or not symbol or not name or not exchange or not board:
            raise ValueError(f"invalid universe row: {row}")

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
            is_st=_parse_flag(row.get("is_st")),
            eligible=_parse_flag(row.get("eligible")),
            exclude_reason=_clean(row.get("exclude_reason")),
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
            "is_st": "Y" if self.is_st else "N",
            "eligible": "Y" if self.eligible else "N",
            "exclude_reason": self.exclude_reason or "",
        }


@dataclass(slots=True)
class UniverseBuildResult:
    records: tuple[UniverseRecord, ...]
    eligible_count: int
    excluded_by_reason: dict[str, int]

    @property
    def total_count(self) -> int:
        return len(self.records)

    @property
    def excluded_count(self) -> int:
        return self.total_count - self.eligible_count

    @property
    def eligible_records(self) -> tuple[UniverseRecord, ...]:
        return tuple(record for record in self.records if record.eligible)

    @property
    def excluded_records(self) -> tuple[UniverseRecord, ...]:
        return tuple(record for record in self.records if not record.eligible)

    def to_summary(self) -> dict[str, Any]:
        return {
            "total_count": self.total_count,
            "eligible_count": self.eligible_count,
            "excluded_count": self.excluded_count,
            "excluded_by_reason": dict(sorted(self.excluded_by_reason.items())),
        }


@dataclass(frozen=True, slots=True)
class StockIndexRecord:
    canonical_code: str
    display_code: str
    name_zh: str
    aliases: tuple[str, ...]
    exchange: str
    board: str
    market: str = "CN"
    asset_type: str = "stock"
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonicalCode": self.canonical_code,
            "displayCode": self.display_code,
            "nameZh": self.name_zh,
            "aliases": list(self.aliases),
            "exchange": self.exchange,
            "board": self.board,
            "market": self.market,
            "assetType": self.asset_type,
            "active": self.active,
        }
