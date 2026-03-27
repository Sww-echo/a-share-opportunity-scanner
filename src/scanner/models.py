from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

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
    "close_vs_sma20_rule",
    "sma20_vs_sma60_rule",
    "sma20_crossover_rule",
    "breakout_rule",
    "breakout_volume_rule",
    "pullback_support_rule",
    "pullback_volume_rule",
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
class RuleBasedScanConfig:
    min_total_market_cap_billion_cny: float = 100.0
    watch_buffer_ratio: float = 0.2
    max_close_above_sma20_ratio: float = 0.05
    min_breakout_volume_ratio: float = 1.2
    support_touch_tolerance_ratio: float = 0.01
    max_pullback_volume_ratio: float = 1.0

    def __post_init__(self) -> None:
        if self.min_total_market_cap_billion_cny <= 0:
            raise ValueError("min_total_market_cap_billion_cny must be positive")
        if not 0 <= self.watch_buffer_ratio < 1:
            raise ValueError("watch_buffer_ratio must be between 0 and 1")
        if self.max_close_above_sma20_ratio < 0:
            raise ValueError("max_close_above_sma20_ratio must be non-negative")
        if self.min_breakout_volume_ratio <= 0:
            raise ValueError("min_breakout_volume_ratio must be positive")
        if self.support_touch_tolerance_ratio < 0:
            raise ValueError("support_touch_tolerance_ratio must be non-negative")
        if self.max_pullback_volume_ratio <= 0:
            raise ValueError("max_pullback_volume_ratio must be positive")

    @property
    def watch_floor_billion_cny(self) -> float:
        return self.min_total_market_cap_billion_cny * (1 - self.watch_buffer_ratio)

    @property
    def max_score(self) -> int:
        return 10


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
    close_vs_sma20_rule: str
    sma20_vs_sma60_rule: str
    sma20_crossover_rule: str
    breakout_rule: str
    breakout_volume_rule: str
    pullback_support_rule: str
    pullback_volume_rule: str
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
            "close_vs_sma20_rule": self.close_vs_sma20_rule,
            "sma20_vs_sma60_rule": self.sma20_vs_sma60_rule,
            "sma20_crossover_rule": self.sma20_crossover_rule,
            "breakout_rule": self.breakout_rule,
            "breakout_volume_rule": self.breakout_volume_rule,
            "pullback_support_rule": self.pullback_support_rule,
            "pullback_volume_rule": self.pullback_volume_rule,
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
            "thresholds": {
                "candidate_min_total_market_cap_billion_cny": (
                    config.min_total_market_cap_billion_cny
                ),
                "watch_floor_total_market_cap_billion_cny": (
                    config.watch_floor_billion_cny
                ),
                "watch_buffer_ratio": config.watch_buffer_ratio,
                "max_close_above_sma20_ratio": config.max_close_above_sma20_ratio,
                "min_breakout_volume_ratio": config.min_breakout_volume_ratio,
                "support_touch_tolerance_ratio": config.support_touch_tolerance_ratio,
                "max_pullback_volume_ratio": config.max_pullback_volume_ratio,
            },
            "score_model": {
                "max_score": config.max_score,
                "components": {
                    "market_cap_candidate_band": 2,
                    "market_cap_watch_band": 1,
                    "close_at_or_above_sma20": 1,
                    "sma20_at_or_above_sma60": 1,
                    "confirmed_sma20_sma60_bullish_crossover": 1,
                    "breakout_level_confirmation": 1,
                    "breakout_volume_confirmation": 1,
                    "supported_pullback_confirmation": 1,
                    "pullback_volume_contraction": 1,
                    "no_chase_guard": 1,
                },
            },
            "score_distribution": {
                str(score): score_counts.get(score, 0)
                for score in range(config.max_score + 1)
            },
            "primary_reason_counts": dict(
                sorted(Counter(record.reason for record in self.records).items())
            ),
            "evaluated_rules": [
                "market-cap band gate",
                "close at or above SMA20 when technical snapshot is present",
                "SMA20 at or above SMA60 when technical snapshot is present",
                "fresh SMA20 bullish crossover above SMA60 when prior SMA values are present",
                "close at or above the prepared breakout level when breakout context is present",
                "breakout volume confirmation: volume_ratio_20d must meet the configured floor when breakout is used as the entry trigger",
                "supported pullback confirmation: low tests SMA20 within tolerance, close holds above SMA20, and close is not above the prior close",
                "pullback volume contraction: volume_ratio_20d must stay at or below the configured ceiling when supported pullback is used as the entry trigger",
                "no-chase guard: close must not exceed SMA20 by more than the configured ratio",
            ],
        }


MarketCapScanConfig = RuleBasedScanConfig
