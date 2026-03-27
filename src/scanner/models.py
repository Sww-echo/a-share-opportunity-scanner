from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from .config import RuleBasedScanConfig

DECISION_SEQUENCE = ("candidate", "watch", "reject")
SCAN_RESULT_FIELDNAMES = (
    "ts_code",
    "symbol",
    "name",
    "exchange",
    "board",
    "total_market_cap_billion_cny",
    "circulating_market_cap_billion_cny",
    "market_cap_as_of_date",
    "close_price_cny",
    "prev_close_price_cny",
    "low_price_cny",
    "sma20_cny",
    "sma60_cny",
    "prev_sma20_cny",
    "prev_sma60_cny",
    "breakout_level_cny",
    "volume_ratio_20d",
    "technical_as_of_date",
    "score",
    "max_score",
    "market_cap_rule",
    "circulating_market_cap_rule",
    "close_vs_sma20_rule",
    "sma20_vs_sma60_rule",
    "sma20_crossover_rule",
    "breakout_rule",
    "breakout_volume_rule",
    "pullback_support_rule",
    "pullback_volume_rule",
    "pullback_freshness_rule",
    "no_chase_rule",
    "decision",
    "reason",
    "signal_reasons",
    "risk_flags",
)


def _format_number(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def _format_integer(value: int) -> str:
    return str(value)


def _format_codes(values: tuple[str, ...]) -> str:
    return "|".join(values)


@dataclass(frozen=True, slots=True)
class DailyScanRecord:
    ts_code: str
    symbol: str
    name: str
    exchange: str
    board: str
    total_market_cap_billion_cny: float | None
    circulating_market_cap_billion_cny: float | None
    market_cap_as_of_date: str | None
    close_price_cny: float | None
    prev_close_price_cny: float | None
    low_price_cny: float | None
    sma20_cny: float | None
    sma60_cny: float | None
    prev_sma20_cny: float | None
    prev_sma60_cny: float | None
    breakout_level_cny: float | None
    volume_ratio_20d: float | None
    technical_as_of_date: str | None
    score: int
    max_score: int
    market_cap_rule: str
    circulating_market_cap_rule: str
    close_vs_sma20_rule: str
    sma20_vs_sma60_rule: str
    sma20_crossover_rule: str
    breakout_rule: str
    breakout_volume_rule: str
    pullback_support_rule: str
    pullback_volume_rule: str
    pullback_freshness_rule: str
    no_chase_rule: str
    decision: str
    reason: str
    signal_reasons: tuple[str, ...]
    risk_flags: tuple[str, ...]

    def to_row(self) -> dict[str, str]:
        return {
            "ts_code": self.ts_code,
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "board": self.board,
            "total_market_cap_billion_cny": _format_number(
                self.total_market_cap_billion_cny
            ),
            "circulating_market_cap_billion_cny": _format_number(
                self.circulating_market_cap_billion_cny
            ),
            "market_cap_as_of_date": self.market_cap_as_of_date or "",
            "close_price_cny": _format_number(self.close_price_cny),
            "prev_close_price_cny": _format_number(self.prev_close_price_cny),
            "low_price_cny": _format_number(self.low_price_cny),
            "sma20_cny": _format_number(self.sma20_cny),
            "sma60_cny": _format_number(self.sma60_cny),
            "prev_sma20_cny": _format_number(self.prev_sma20_cny),
            "prev_sma60_cny": _format_number(self.prev_sma60_cny),
            "breakout_level_cny": _format_number(self.breakout_level_cny),
            "volume_ratio_20d": _format_number(self.volume_ratio_20d),
            "technical_as_of_date": self.technical_as_of_date or "",
            "score": _format_integer(self.score),
            "max_score": _format_integer(self.max_score),
            "market_cap_rule": self.market_cap_rule,
            "circulating_market_cap_rule": self.circulating_market_cap_rule,
            "close_vs_sma20_rule": self.close_vs_sma20_rule,
            "sma20_vs_sma60_rule": self.sma20_vs_sma60_rule,
            "sma20_crossover_rule": self.sma20_crossover_rule,
            "breakout_rule": self.breakout_rule,
            "breakout_volume_rule": self.breakout_volume_rule,
            "pullback_support_rule": self.pullback_support_rule,
            "pullback_volume_rule": self.pullback_volume_rule,
            "pullback_freshness_rule": self.pullback_freshness_rule,
            "no_chase_rule": self.no_chase_rule,
            "decision": self.decision,
            "reason": self.reason,
            "signal_reasons": _format_codes(self.signal_reasons),
            "risk_flags": _format_codes(self.risk_flags),
        }


@dataclass(slots=True)
class DailyScanResult:
    records: tuple[DailyScanRecord, ...]
    total_universe_count: int
    eligible_universe_count: int

    def to_summary(self, config: RuleBasedScanConfig) -> dict[str, Any]:
        from .ranking import describe_ranking_policy

        counts = Counter(record.decision for record in self.records)
        score_counts = Counter(record.score for record in self.records)
        return {
            "total_universe_count": self.total_universe_count,
            "eligible_universe_count": self.eligible_universe_count,
            "skipped_universe_count": self.total_universe_count
            - self.eligible_universe_count,
            "decision_counts": {
                decision: counts.get(decision, 0) for decision in DECISION_SEQUENCE
            },
            "thresholds": config.summary_thresholds(),
            "score_model": {
                "max_score": config.max_score,
                "components": {
                    "market_cap_candidate_band": 2,
                    "market_cap_watch_band": 1,
                    "circulating_market_cap_liquidity": 1,
                    "close_at_or_above_sma20": 1,
                    "sma20_at_or_above_sma60": 1,
                    "confirmed_sma20_sma60_bullish_crossover": 1,
                    "breakout_level_confirmation": 1,
                    "breakout_volume_confirmation": 1,
                    "supported_pullback_confirmation": 1,
                    "pullback_volume_contraction": 1,
                    "fresh_supported_pullback_entry": 1,
                    "no_chase_guard": 1,
                },
            },
            "ranking_model": describe_ranking_policy(),
            "score_distribution": {
                str(score): score_counts.get(score, 0)
                for score in range(config.max_score + 1)
            },
            "primary_reason_counts": dict(
                sorted(Counter(record.reason for record in self.records).items())
            ),
            "evaluated_rules": [
                "market-cap band gate",
                "circulating market-cap liquidity proxy: circulating_market_cap_billion_cny must meet the configured floor to qualify as candidate and drops to watch/reject when float liquidity is thin",
                "close at or above SMA20 when technical snapshot is present",
                "SMA20 at or above SMA60 when technical snapshot is present",
                "fresh SMA20 bullish crossover above SMA60 when prior SMA values are present and the crossover day also closes above the prior close; weak or missing price confirmation is surfaced explicitly",
                "fresh breakout confirmation: prev_close must be below the prepared breakout level and close must finish at or above it; stale-above and failed-breakout states are surfaced explicitly",
                "breakout volume confirmation: volume_ratio_20d must meet the configured floor when breakout is used as the entry trigger",
                "supported pullback confirmation: low tests SMA20 within tolerance, close holds above SMA20, and close is not above the prior close",
                "pullback volume contraction: volume_ratio_20d must stay at or below the configured ceiling when supported pullback is used as the entry trigger",
                "fresh pullback entry: after a confirmed supported pullback, close must still finish within the configured distance above SMA20 or the pullback trigger is treated as no longer fresh",
                "no-chase guard: close must not exceed SMA20 by more than the configured ratio",
                "ranking layer: within each decision bucket, hard reset or structural damage ranks below cleaner setups before score, then score, confirmed trigger mix, trigger freshness/quality, risk burden, and liquidity proxies break ties",
            ],
        }


MarketCapScanConfig = RuleBasedScanConfig
