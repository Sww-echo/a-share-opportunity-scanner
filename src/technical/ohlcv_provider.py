from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .interfaces import TechnicalSnapshotProvider

_REQUIRED_COLUMNS = {
    "ts_code": ("ts_code",),
    "trade_date": ("trade_date", "date"),
    "high_price_cny": ("high", "high_price_cny"),
    "low_price_cny": ("low", "low_price_cny"),
    "close_price_cny": ("close", "close_price_cny"),
}
_OPTIONAL_COLUMNS = {
    "symbol": ("symbol", "code"),
    "name": ("name",),
    "volume": ("volume", "vol", "volume_shares", "turnover_volume"),
}


def _clean_text(value: object | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _parse_trade_date(value: object | None) -> str:
    text = _clean_text(value)
    if text is None:
        raise ValueError("trade_date is required")

    digits = "".join(character for character in text if character.isdigit())
    if len(digits) < 8:
        raise ValueError(f"invalid trade_date: {value}")

    return digits[:8]


def _parse_positive_float(value: object | None, field_name: str) -> float:
    text = _clean_text(value)
    if text is None:
        raise ValueError(f"{field_name} is required")

    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {value}") from exc

    if number <= 0:
        raise ValueError(f"{field_name} must be positive")
    return number


def _parse_optional_non_negative_float(value: object | None) -> float | None:
    text = _clean_text(value)
    if text is None:
        return None

    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(f"invalid volume: {value}") from exc

    if number < 0:
        raise ValueError("volume must be non-negative when provided")
    return number


def _normalize_header(header: str) -> str:
    return header.strip().lower()


@dataclass(frozen=True, slots=True)
class OHLCVBar:
    ts_code: str
    trade_date: str
    high_price_cny: float
    low_price_cny: float
    close_price_cny: float
    volume: float | None = None
    symbol: str | None = None
    name: str | None = None


def load_ohlcv_bars(path: Path) -> list[OHLCVBar]:
    if not path.exists():
        raise FileNotFoundError(f"ohlcv csv not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        resolved_columns = _resolve_columns(reader.fieldnames)
        records: list[OHLCVBar] = []

        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(_parse_bar(row, resolved_columns))

    return records


def _resolve_columns(fieldnames: list[str] | None) -> dict[str, str]:
    normalized_lookup = {
        _normalize_header(fieldname): fieldname for fieldname in fieldnames or []
    }
    resolved: dict[str, str] = {}
    missing: list[str] = []

    for target, aliases in _REQUIRED_COLUMNS.items():
        actual = _find_column(normalized_lookup, aliases)
        if actual is None:
            missing.append("/".join(aliases))
            continue
        resolved[target] = actual

    if missing:
        raise ValueError(
            "missing required OHLCV columns: " + ", ".join(sorted(missing))
        )

    for target, aliases in _OPTIONAL_COLUMNS.items():
        actual = _find_column(normalized_lookup, aliases)
        if actual is not None:
            resolved[target] = actual

    return resolved


def _find_column(
    normalized_lookup: dict[str, str],
    aliases: tuple[str, ...],
) -> str | None:
    for alias in aliases:
        actual = normalized_lookup.get(alias)
        if actual is not None:
            return actual
    return None


def _parse_bar(row: dict[str, str], columns: dict[str, str]) -> OHLCVBar:
    ts_code = _clean_text(row.get(columns["ts_code"]))
    if ts_code is None:
        raise ValueError(f"invalid OHLCV row missing ts_code: {row}")

    symbol = _clean_text(row.get(columns["symbol"])) if "symbol" in columns else None
    name = _clean_text(row.get(columns["name"])) if "name" in columns else None
    volume = (
        _parse_optional_non_negative_float(row.get(columns["volume"]))
        if "volume" in columns
        else None
    )

    return OHLCVBar(
        ts_code=ts_code,
        trade_date=_parse_trade_date(row.get(columns["trade_date"])),
        high_price_cny=_parse_positive_float(
            row.get(columns["high_price_cny"]),
            "high",
        ),
        low_price_cny=_parse_positive_float(
            row.get(columns["low_price_cny"]),
            "low",
        ),
        close_price_cny=_parse_positive_float(
            row.get(columns["close_price_cny"]),
            "close",
        ),
        volume=volume,
        symbol=symbol,
        name=name,
    )


def group_bars_by_ts_code(bars: list[OHLCVBar]) -> dict[str, list[OHLCVBar]]:
    grouped: dict[str, list[OHLCVBar]] = defaultdict(list)
    seen_dates: dict[str, set[str]] = defaultdict(set)

    for bar in bars:
        if bar.trade_date in seen_dates[bar.ts_code]:
            raise ValueError(
                f"duplicate OHLCV row for {bar.ts_code} on {bar.trade_date}"
            )
        seen_dates[bar.ts_code].add(bar.trade_date)
        grouped[bar.ts_code].append(bar)

    for history in grouped.values():
        history.sort(key=lambda item: item.trade_date)

    return dict(grouped)


class OHLCVCSVTechnicalSnapshotProvider(TechnicalSnapshotProvider):
    provider_name = "ohlcv_csv"

    def __init__(
        self,
        source_path: Path,
        *,
        calculation_config: "TechnicalSnapshotCalculationConfig | None" = None,
    ) -> None:
        self._source_path = source_path
        self._calculation_config = calculation_config

    def fetch_snapshot(self) -> list["TechnicalSnapshotRecord"]:
        from .calculators import calculate_technical_snapshot

        grouped = group_bars_by_ts_code(load_ohlcv_bars(self._source_path))
        return [
            calculate_technical_snapshot(
                grouped[ts_code],
                config=self._calculation_config,
            )
            for ts_code in sorted(grouped)
        ]
