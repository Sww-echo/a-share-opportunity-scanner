from __future__ import annotations

from src.market_cap import MarketCapSnapshotRecord
from src.technical import TechnicalSnapshotRecord

from .config import RuleBasedScanConfig
from .reason_builder import ScanEvaluation, build_scan_evaluation
from .rules import evaluate_rule_states


def evaluate_scan(
    config: RuleBasedScanConfig,
    market_cap_snapshot: MarketCapSnapshotRecord | None,
    technical_snapshot: TechnicalSnapshotRecord | None,
) -> ScanEvaluation:
    return build_scan_evaluation(
        evaluate_rule_states(
            config,
            market_cap_snapshot,
            technical_snapshot,
        )
    )
