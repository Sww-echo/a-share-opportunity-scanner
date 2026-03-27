from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from .models import UniverseRecord

UNIVERSE_FIELDNAMES = (
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
    "is_st",
    "eligible",
    "exclude_reason",
)


def load_universe_records(path: Path) -> list[UniverseRecord]:
    if not path.exists():
        raise FileNotFoundError(f"universe CSV not found: {path}")

    records: list[UniverseRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not any((value or "").strip() for value in row.values()):
                continue
            records.append(UniverseRecord.from_mapping(row))

    return records


def write_universe_records(path: Path, records: Sequence[UniverseRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=UNIVERSE_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())
