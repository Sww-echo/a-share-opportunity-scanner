from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from .models import MarketCapSnapshotRecord

MARKET_CAP_SNAPSHOT_FIELDNAMES = (
    "ts_code",
    "symbol",
    "name",
    "total_market_cap_billion_cny",
    "circulating_market_cap_billion_cny",
    "as_of_date",
)


def load_market_cap_snapshot(path: Path) -> list[MarketCapSnapshotRecord]:
    if not path.exists():
        raise FileNotFoundError(f"market-cap snapshot not found: {path}")

    records: list[MarketCapSnapshotRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(MarketCapSnapshotRecord.from_mapping(row))

    return records


def write_market_cap_snapshot(
    path: Path,
    records: Sequence[MarketCapSnapshotRecord],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MARKET_CAP_SNAPSHOT_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())
