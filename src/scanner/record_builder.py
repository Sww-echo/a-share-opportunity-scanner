from __future__ import annotations

from src.market_cap import MarketCapSnapshotRecord
from src.technical import TechnicalSnapshotRecord
from src.universe import UniverseRecord

from .models import DailyScanRecord
from .reason_builder import ScanEvaluation


def build_daily_scan_record(
    *,
    universe_record: UniverseRecord,
    market_cap_snapshot: MarketCapSnapshotRecord | None,
    technical_snapshot: TechnicalSnapshotRecord | None,
    evaluation: ScanEvaluation,
    max_score: int,
) -> DailyScanRecord:
    rules = evaluation.rules
    return DailyScanRecord(
        ts_code=universe_record.ts_code,
        symbol=universe_record.symbol,
        name=universe_record.name,
        exchange=universe_record.exchange,
        board=universe_record.board,
        total_market_cap_billion_cny=(
            market_cap_snapshot.total_market_cap_billion_cny
            if market_cap_snapshot
            else None
        ),
        circulating_market_cap_billion_cny=(
            market_cap_snapshot.circulating_market_cap_billion_cny
            if market_cap_snapshot
            else None
        ),
        market_cap_as_of_date=(
            market_cap_snapshot.as_of_date if market_cap_snapshot else None
        ),
        close_price_cny=(
            technical_snapshot.close_price_cny if technical_snapshot else None
        ),
        prev_close_price_cny=(
            technical_snapshot.prev_close_price_cny if technical_snapshot else None
        ),
        low_price_cny=technical_snapshot.low_price_cny if technical_snapshot else None,
        sma20_cny=technical_snapshot.sma20_cny if technical_snapshot else None,
        sma60_cny=technical_snapshot.sma60_cny if technical_snapshot else None,
        prev_sma20_cny=(
            technical_snapshot.prev_sma20_cny if technical_snapshot else None
        ),
        prev_sma60_cny=(
            technical_snapshot.prev_sma60_cny if technical_snapshot else None
        ),
        breakout_level_cny=(
            technical_snapshot.breakout_level_cny if technical_snapshot else None
        ),
        volume_ratio_20d=(
            technical_snapshot.volume_ratio_20d if technical_snapshot else None
        ),
        technical_as_of_date=(
            technical_snapshot.as_of_date if technical_snapshot else None
        ),
        score=rules.score,
        max_score=max_score,
        market_cap_rule=rules.market_cap_rule,
        circulating_market_cap_rule=rules.circulating_market_cap_rule,
        close_vs_sma20_rule=rules.close_vs_sma20_rule,
        sma20_vs_sma60_rule=rules.sma20_vs_sma60_rule,
        sma20_crossover_rule=rules.sma20_crossover_rule,
        breakout_rule=rules.breakout_rule,
        breakout_volume_rule=rules.breakout_volume_rule,
        pullback_support_rule=rules.pullback_support_rule,
        pullback_volume_rule=rules.pullback_volume_rule,
        pullback_freshness_rule=rules.pullback_freshness_rule,
        no_chase_rule=rules.no_chase_rule,
        decision=evaluation.decision,
        reason=evaluation.reason,
        signal_reasons=evaluation.signal_reasons,
        risk_flags=evaluation.risk_flags,
    )
