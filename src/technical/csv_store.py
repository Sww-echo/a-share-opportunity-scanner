from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from .models import TechnicalSnapshotRecord

TECHNICAL_SNAPSHOT_FIELDNAMES = (
    "ts_code",
    "symbol",
    "name",
    "close_price_cny",
    "prev_close_price_cny",
    "low_price_cny",
    "sma20_cny",
    "sma60_cny",
    "prev_sma20_cny",
    "prev_sma60_cny",
    "breakout_level_cny",
    "volume_ratio_20d",
    "as_of_date",
)


def load_technical_snapshot(path: Path) -> list[TechnicalSnapshotRecord]:
    if not path.exists():
        raise FileNotFoundError(f"technical snapshot not found: {path}")

    records: list[TechnicalSnapshotRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(TechnicalSnapshotRecord.from_mapping(row))

    return records


def write_technical_snapshot(
    path: Path,
    records: Sequence[TechnicalSnapshotRecord],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TECHNICAL_SNAPSHOT_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())
