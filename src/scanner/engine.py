from __future__ import annotations

from typing import Sequence, TypeVar

from src.market_cap import MarketCapSnapshotRecord
from src.technical import TechnicalSnapshotRecord
from src.universe import UniverseRecord

from .config import RuleBasedScanConfig
from .evaluation import evaluate_scan
from .models import DailyScanResult
from .ranking import rank_scan_records
from .record_builder import build_daily_scan_record

_RecordT = TypeVar("_RecordT", MarketCapSnapshotRecord, TechnicalSnapshotRecord)


class RuleBasedScanner:
    """Apply explicit market-cap, trigger, and no-chase rules on the eligible universe."""

    def __init__(self, config: RuleBasedScanConfig | None = None) -> None:
        self._config = config or RuleBasedScanConfig()

    @property
    def config(self) -> RuleBasedScanConfig:
        return self._config

    def scan(
        self,
        *,
        universe_records: Sequence[UniverseRecord],
        market_cap_records: Sequence[MarketCapSnapshotRecord],
        technical_records: Sequence[TechnicalSnapshotRecord] | None = None,
    ) -> DailyScanResult:
        snapshot_by_code = self._build_lookup(
            market_cap_records,
            duplicate_label="market-cap snapshot",
        )
        technical_by_code = self._build_lookup(
            technical_records or (),
            duplicate_label="technical snapshot",
        )
        eligible_universe = [record for record in universe_records if record.eligible]

        scan_records = []
        for universe_record in sorted(eligible_universe, key=lambda item: item.symbol):
            market_cap_snapshot = snapshot_by_code.get(universe_record.ts_code)
            technical_snapshot = technical_by_code.get(universe_record.ts_code)
            evaluation = evaluate_scan(
                self._config,
                market_cap_snapshot,
                technical_snapshot,
            )
            scan_records.append(
                build_daily_scan_record(
                    universe_record=universe_record,
                    market_cap_snapshot=market_cap_snapshot,
                    technical_snapshot=technical_snapshot,
                    evaluation=evaluation,
                    max_score=self._config.max_score,
                )
            )

        return DailyScanResult(
            records=rank_scan_records(scan_records),
            total_universe_count=len(universe_records),
            eligible_universe_count=len(eligible_universe),
        )

    def _build_lookup(
        self,
        records: Sequence[_RecordT],
        *,
        duplicate_label: str,
    ) -> dict[str, _RecordT]:
        records_by_code: dict[str, _RecordT] = {}
        for record in records:
            if record.ts_code in records_by_code:
                raise ValueError(
                    f"duplicate {duplicate_label} record for {record.ts_code}"
                )
            records_by_code[record.ts_code] = record
        return records_by_code


MarketCapThresholdScanner = RuleBasedScanner
