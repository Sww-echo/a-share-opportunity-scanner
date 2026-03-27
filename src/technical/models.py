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
        raise ValueError(f"invalid technical value: {value}") from exc


def _format_number(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


@dataclass(frozen=True, slots=True)
class TechnicalSnapshotRecord:
    ts_code: str
    close_price_cny: float | None = None
    prev_close_price_cny: float | None = None
    low_price_cny: float | None = None
    sma20_cny: float | None = None
    sma60_cny: float | None = None
    prev_sma20_cny: float | None = None
    prev_sma60_cny: float | None = None
    breakout_level_cny: float | None = None
    volume_ratio_20d: float | None = None
    as_of_date: str | None = None
    symbol: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        if not self.ts_code.strip():
            raise ValueError("ts_code is required")

        for field_name in (
            "close_price_cny",
            "prev_close_price_cny",
            "low_price_cny",
            "sma20_cny",
            "sma60_cny",
            "prev_sma20_cny",
            "prev_sma60_cny",
            "breakout_level_cny",
        ):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                raise ValueError(f"{field_name} must be positive when provided")

        if self.volume_ratio_20d is not None and self.volume_ratio_20d < 0:
            raise ValueError("volume_ratio_20d must be non-negative when provided")

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "TechnicalSnapshotRecord":
        ts_code = _clean(row.get("ts_code"))
        if not ts_code:
            raise ValueError(f"invalid technical snapshot row: {row}")

        return cls(
            ts_code=ts_code,
            close_price_cny=_clean_float(row.get("close_price_cny")),
            prev_close_price_cny=_clean_float(row.get("prev_close_price_cny")),
            low_price_cny=_clean_float(row.get("low_price_cny")),
            sma20_cny=_clean_float(row.get("sma20_cny")),
            sma60_cny=_clean_float(row.get("sma60_cny")),
            prev_sma20_cny=_clean_float(row.get("prev_sma20_cny")),
            prev_sma60_cny=_clean_float(row.get("prev_sma60_cny")),
            breakout_level_cny=_clean_float(row.get("breakout_level_cny")),
            volume_ratio_20d=_clean_float(row.get("volume_ratio_20d")),
            as_of_date=_clean(row.get("as_of_date")),
            symbol=_clean(row.get("symbol")),
            name=_clean(row.get("name")),
        )

    def to_row(self) -> dict[str, str]:
        return {
            "ts_code": self.ts_code,
            "symbol": self.symbol or "",
            "name": self.name or "",
            "close_price_cny": _format_number(self.close_price_cny),
            "prev_close_price_cny": _format_number(self.prev_close_price_cny),
            "low_price_cny": _format_number(self.low_price_cny),
            "sma20_cny": _format_number(self.sma20_cny),
            "sma60_cny": _format_number(self.sma60_cny),
            "prev_sma20_cny": _format_number(self.prev_sma20_cny),
            "prev_sma60_cny": _format_number(self.prev_sma60_cny),
            "breakout_level_cny": _format_number(self.breakout_level_cny),
            "volume_ratio_20d": _format_number(self.volume_ratio_20d),
            "as_of_date": self.as_of_date or "",
        }
