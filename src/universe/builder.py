from __future__ import annotations

import re
from collections import Counter
from typing import Sequence

from src.data_provider import StockListRecord

from .models import UniverseBuildConfig, UniverseBuildResult, UniverseRecord

ST_PATTERN = re.compile(r"^\*?ST", re.IGNORECASE)


def is_st_stock(name: str) -> bool:
    return bool(ST_PATTERN.match((name or "").strip()))


def is_supported_a_share_code(ts_code: str) -> bool:
    if "." not in ts_code:
        return False

    symbol, suffix = ts_code.split(".", 1)
    suffix = suffix.upper()

    if not symbol.isdigit() or len(symbol) != 6:
        return False

    if suffix == "SH":
        return symbol.startswith(("600", "601", "603", "605", "688"))
    if suffix == "SZ":
        return symbol.startswith(("000", "001", "002", "003", "300", "301"))
    if suffix == "BJ":
        return True
    return False


class AShareUniverseBuilder:
    """Builds the first explicit A-share universe from stock-list metadata."""

    def __init__(self, config: UniverseBuildConfig | None = None) -> None:
        self._config = config or UniverseBuildConfig()

    def build(self, stock_list: Sequence[StockListRecord]) -> UniverseBuildResult:
        records: list[UniverseRecord] = []
        excluded_by_reason: Counter[str] = Counter()

        for stock in sorted(stock_list, key=lambda item: item.symbol):
            exclude_reason = self._get_exclude_reason(stock)
            eligible = exclude_reason is None

            record = UniverseRecord(
                ts_code=stock.ts_code,
                symbol=stock.symbol,
                name=stock.name,
                exchange=stock.exchange,
                board=stock.board,
                list_status=stock.list_status,
                list_date=stock.list_date,
                area=stock.area,
                industry=stock.industry,
                is_hs=stock.is_hs,
                is_st=is_st_stock(stock.name),
                eligible=eligible,
                exclude_reason=exclude_reason,
            )
            records.append(record)

            if exclude_reason is not None:
                excluded_by_reason[exclude_reason] += 1

        eligible_count = sum(1 for record in records if record.eligible)
        return UniverseBuildResult(
            records=tuple(records),
            eligible_count=eligible_count,
            excluded_by_reason=dict(excluded_by_reason),
        )

    def _get_exclude_reason(self, stock: StockListRecord) -> str | None:
        if not is_supported_a_share_code(stock.ts_code):
            return "non_a_share_code"

        if stock.list_status.upper() not in self._config.allowed_list_statuses:
            return "inactive_listing"

        if self._config.exclude_st and is_st_stock(stock.name):
            return "st_stock"

        return None
