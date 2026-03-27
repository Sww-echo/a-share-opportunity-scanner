from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .models import DECISION_SEQUENCE, DailyScanRecord

DECISION_ORDER = {decision: index for index, decision in enumerate(DECISION_SEQUENCE)}
CONFIRMED_TRIGGER_PRIORITY = (
    "supported_pullback",
    "volume_backed_breakout",
    "confirmed_crossover",
)
_CONFIRMED_TRIGGER_WEIGHTS = {
    "supported_pullback": 3,
    "volume_backed_breakout": 2,
    "confirmed_crossover": 1,
}
_CROSSOVER_QUALITY = {
    "confirmed_bullish_cross": 5,
    "crossed_but_close_not_above_prev_close": 4,
    "missing_price_confirmation_context": 3,
    "touching_sma60": 2,
    "already_above": 1,
    "fail": 0,
    "missing": -1,
}


@dataclass(frozen=True, slots=True)
class ScanRankingProfile:
    decision_rank: int
    major_risk_tier: int
    score: int
    confirmed_triggers: tuple[str, ...]
    confirmed_trigger_count: int
    confirmed_trigger_strength: int
    trigger_quality_score: int
    crossover_quality: int
    breakout_quality: int
    pullback_quality: int
    risk_flag_count: int
    circulating_market_cap_billion_cny: float | None
    total_market_cap_billion_cny: float | None
    symbol: str

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.decision_rank,
            self.major_risk_tier,
            -self.score,
            -self.confirmed_trigger_count,
            -self.confirmed_trigger_strength,
            -self.trigger_quality_score,
            self.risk_flag_count,
            -(self.circulating_market_cap_billion_cny or -1.0),
            -(self.total_market_cap_billion_cny or -1.0),
            self.symbol,
        )


def rank_scan_records(records: Sequence[DailyScanRecord]) -> tuple[DailyScanRecord, ...]:
    return tuple(sorted(records, key=lambda item: build_scan_ranking_profile(item).sort_key()))


def build_scan_ranking_profile(record: DailyScanRecord) -> ScanRankingProfile:
    confirmed_triggers = _build_confirmed_triggers(record)
    crossover_quality = _CROSSOVER_QUALITY[record.sma20_crossover_rule]
    breakout_quality = _breakout_quality(record)
    pullback_quality = _pullback_quality(record)

    return ScanRankingProfile(
        decision_rank=DECISION_ORDER[record.decision],
        major_risk_tier=_major_risk_tier(record),
        score=record.score,
        confirmed_triggers=confirmed_triggers,
        confirmed_trigger_count=len(confirmed_triggers),
        confirmed_trigger_strength=sum(
            _CONFIRMED_TRIGGER_WEIGHTS[trigger] for trigger in confirmed_triggers
        ),
        trigger_quality_score=(
            crossover_quality + breakout_quality + pullback_quality
        ),
        crossover_quality=crossover_quality,
        breakout_quality=breakout_quality,
        pullback_quality=pullback_quality,
        risk_flag_count=len(record.risk_flags),
        circulating_market_cap_billion_cny=record.circulating_market_cap_billion_cny,
        total_market_cap_billion_cny=record.total_market_cap_billion_cny,
        symbol=record.symbol,
    )


def describe_ranking_policy() -> dict[str, Any]:
    return {
        "decision_priority": list(DECISION_SEQUENCE),
        "ordering_dimensions": [
            "decision tier: candidate before watch before reject",
            "major risk tier ascending so hard reset or structural damage ranks below cleaner setups even when raw score is high",
            "score descending within the same decision/risk bucket",
            "confirmed trigger count descending",
            "confirmed trigger semantics descending: supported_pullback > volume_backed_breakout > confirmed_crossover",
            "trigger quality/freshness descending using current crossover/breakout/pullback rule states",
            "risk flag count ascending",
            "liquidity proxies descending: circulating market cap first, then total market cap",
            "symbol ascending as the final stable tie-breaker",
        ],
        "confirmed_trigger_priority": list(CONFIRMED_TRIGGER_PRIORITY),
        "trigger_quality_states": {
            "crossover": [
                "confirmed_bullish_cross",
                "crossed_but_close_not_above_prev_close",
                "missing_price_confirmation_context",
                "touching_sma60",
                "already_above",
                "fail",
                "missing",
            ],
            "breakout": [
                "pass+breakout_volume_rule=pass",
                "pass+breakout_volume_rule=missing",
                "pass+breakout_volume_rule=fail",
                "stale_above_breakout",
                "fail",
                "missing",
                "failed_breakout",
            ],
            "pullback": [
                "confirmed_supported_pullback+pullback_volume_rule=pass+pullback_freshness_rule=pass",
                "confirmed_supported_pullback+pullback_volume_rule=missing+pullback_freshness_rule=pass",
                "confirmed_supported_pullback+pullback_volume_rule=fail+pullback_freshness_rule=pass",
                "confirmed_supported_pullback with freshness downgrade or partial context",
                "support_retested_without_pullback_day",
                "support_not_tested",
                "missing",
                "closed_below_sma20 / undercut_sma20_support",
            ],
        },
        "major_risk_tiers": {
            "0": "clean or only ordinary waiting states",
            "1": "confirmation gap or missing context",
            "2": "stale trigger, watch-band market-cap/liquidity, or stale pullback freshness",
            "3": "trend break, support damage, or no-chase overextension",
            "4": "hard blocker or reset state such as failed breakout or below-watch-band liquidity",
        },
    }


def _build_confirmed_triggers(record: DailyScanRecord) -> tuple[str, ...]:
    triggers: list[str] = []
    if _is_pullback_trigger_confirmed(record):
        triggers.append("supported_pullback")
    if _is_breakout_trigger_confirmed(record):
        triggers.append("volume_backed_breakout")
    if _is_crossover_trigger_confirmed(record):
        triggers.append("confirmed_crossover")
    return tuple(triggers)


def _is_crossover_trigger_confirmed(record: DailyScanRecord) -> bool:
    return record.sma20_crossover_rule == "confirmed_bullish_cross"


def _is_breakout_trigger_confirmed(record: DailyScanRecord) -> bool:
    return record.breakout_rule == "pass" and record.breakout_volume_rule == "pass"


def _is_pullback_trigger_confirmed(record: DailyScanRecord) -> bool:
    return (
        record.pullback_support_rule == "confirmed_supported_pullback"
        and record.pullback_volume_rule == "pass"
        and record.pullback_freshness_rule == "pass"
    )


def _breakout_quality(record: DailyScanRecord) -> int:
    if record.breakout_rule == "pass":
        return {
            "pass": 5,
            "missing": 4,
            "fail": 3,
        }.get(record.breakout_volume_rule, 2)
    return {
        "stale_above_breakout": 2,
        "fail": 1,
        "missing": 0,
        "failed_breakout": -1,
    }.get(record.breakout_rule, 0)


def _pullback_quality(record: DailyScanRecord) -> int:
    if record.pullback_support_rule == "confirmed_supported_pullback":
        if record.pullback_volume_rule == "pass":
            if record.pullback_freshness_rule == "pass":
                return 5
            if record.pullback_freshness_rule == "rebounded_too_far_above_sma20":
                return 2
            return 1
        if record.pullback_volume_rule == "missing":
            return 4 if record.pullback_freshness_rule == "pass" else 1
        if record.pullback_volume_rule == "fail":
            return 3 if record.pullback_freshness_rule == "pass" else 1
        return 1
    return {
        "support_retested_without_pullback_day": 1,
        "support_not_tested": 0,
        "missing": -1,
        "closed_below_sma20": -2,
        "undercut_sma20_support": -2,
    }.get(record.pullback_support_rule, 0)


def _major_risk_tier(record: DailyScanRecord) -> int:
    if record.market_cap_rule in {"missing", "below_watch_band"}:
        return 4
    if record.circulating_market_cap_rule == "below_watch_band":
        return 4
    if record.breakout_rule == "failed_breakout":
        return 4

    if record.close_vs_sma20_rule == "fail":
        return 3
    if record.sma20_vs_sma60_rule == "fail":
        return 3
    if record.pullback_support_rule in {"closed_below_sma20", "undercut_sma20_support"}:
        return 3
    if record.no_chase_rule == "overextended":
        return 3

    if record.market_cap_rule == "watch_band":
        return 2
    if record.circulating_market_cap_rule in {"watch_band", "missing"}:
        return 2
    if record.breakout_rule == "stale_above_breakout":
        return 2
    if record.pullback_freshness_rule == "rebounded_too_far_above_sma20":
        return 2

    if record.close_vs_sma20_rule == "missing":
        return 1
    if record.sma20_vs_sma60_rule == "missing":
        return 1
    if record.sma20_crossover_rule in {
        "touching_sma60",
        "crossed_but_close_not_above_prev_close",
        "missing_price_confirmation_context",
        "missing",
    }:
        return 1
    if record.breakout_rule == "pass" and record.breakout_volume_rule in {"missing", "fail"}:
        return 1
    if record.breakout_rule == "missing":
        return 1
    if (
        record.pullback_support_rule == "confirmed_supported_pullback"
        and record.pullback_volume_rule in {"missing", "fail"}
    ):
        return 1
    if record.pullback_support_rule == "missing":
        return 1
    if record.no_chase_rule == "missing":
        return 1

    return 0
