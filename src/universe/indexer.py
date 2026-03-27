from __future__ import annotations

import re
from typing import Sequence

from .models import StockIndexRecord, UniverseRecord

SPECIAL_NAME_PREFIX = re.compile(r"^\*?ST", re.IGNORECASE)
COMMON_ALIAS_MAP = {
    "贵州茅台": ("茅台",),
    "平安银行": ("平银",),
    "宁德时代": ("宁德",),
    "比亚迪": ("比亚迪汽车",),
    "中信证券": ("中信",),
    "中芯国际": ("中芯",),
}


def _strip_special_prefix(name: str) -> str:
    return SPECIAL_NAME_PREFIX.sub("", name).strip()


def _build_aliases(record: UniverseRecord) -> tuple[str, ...]:
    aliases: list[str] = []

    normalized_name = _strip_special_prefix(record.name)
    if normalized_name and normalized_name != record.name:
        aliases.append(normalized_name)

    aliases.extend(COMMON_ALIAS_MAP.get(normalized_name or record.name, ()))

    deduplicated: list[str] = []
    for alias in aliases:
        if alias and alias not in deduplicated:
            deduplicated.append(alias)
    return tuple(deduplicated)


class StockIndexBuilder:
    """Builds a small static stock index for future scanning and lookup flows."""

    def build(self, universe_records: Sequence[UniverseRecord]) -> tuple[StockIndexRecord, ...]:
        index_records: list[StockIndexRecord] = []

        for record in universe_records:
            if not record.eligible:
                continue

            index_records.append(
                StockIndexRecord(
                    canonical_code=record.ts_code,
                    display_code=record.symbol,
                    name_zh=record.name,
                    aliases=_build_aliases(record),
                    exchange=record.exchange,
                    board=record.board,
                )
            )

        return tuple(sorted(index_records, key=lambda item: item.display_code))
