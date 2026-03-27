from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from .models import StockListRecord

STOCK_LIST_FIELDNAMES = (
    "ts_code",
    "symbol",
    "name",
    "exchange",
    "board",
    "list_status",
    "list_date",
    "area",
    "industry",
    "is_hs",
)


def load_stock_list(path: Path) -> list[StockListRecord]:
    if not path.exists():
        raise FileNotFoundError(f"stock list not found: {path}")

    records: list[StockListRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(StockListRecord.from_mapping(row))

    return records


def write_stock_list(path: Path, records: Sequence[StockListRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STOCK_LIST_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())
