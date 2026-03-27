from __future__ import annotations

from dataclasses import dataclass

from src.market_cap import MarketCapSnapshotRecord
from src.technical import TechnicalSnapshotRecord

from .config import RuleBasedScanConfig


@dataclass(frozen=True, slots=True)
class RuleStateSet:
    score: int
    technical_snapshot_present: bool
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

    @property
    def base_trend_confirmed(self) -> bool:
        return (
            self.close_vs_sma20_rule == "pass"
            and self.sma20_vs_sma60_rule == "pass"
        )

    @property
    def crossover_trigger_confirmed(self) -> bool:
        return self.sma20_crossover_rule == "confirmed_bullish_cross"

    @property
    def breakout_trigger_confirmed(self) -> bool:
        return self.breakout_rule == "pass" and self.breakout_volume_rule == "pass"

    @property
    def pullback_trigger_confirmed(self) -> bool:
        return (
            self.pullback_support_rule == "confirmed_supported_pullback"
            and self.pullback_volume_rule == "pass"
            and self.pullback_freshness_rule == "pass"
        )

    @property
    def entry_trigger_confirmed(self) -> bool:
        return (
            self.crossover_trigger_confirmed
            or self.breakout_trigger_confirmed
            or self.pullback_trigger_confirmed
        )

    @property
    def breakout_failure_active(self) -> bool:
        return self.breakout_rule == "failed_breakout"


def evaluate_rule_states(
    config: RuleBasedScanConfig,
    market_cap_snapshot: MarketCapSnapshotRecord | None,
    technical_snapshot: TechnicalSnapshotRecord | None,
) -> RuleStateSet:
    market_cap_rule, market_cap_points = _evaluate_market_cap_rule(
        config,
        market_cap_snapshot,
    )
    circulating_market_cap_rule, circulating_market_cap_points = (
        _evaluate_circulating_market_cap_rule(config, market_cap_snapshot)
    )
    close_vs_sma20_rule, close_vs_sma20_points = _evaluate_close_vs_sma20_rule(
        technical_snapshot
    )
    sma20_vs_sma60_rule, sma20_vs_sma60_points = _evaluate_sma20_vs_sma60_rule(
        technical_snapshot
    )
    sma20_crossover_rule, sma20_crossover_points = _evaluate_sma20_crossover_rule(
        technical_snapshot
    )
    breakout_rule, breakout_points = _evaluate_breakout_rule(technical_snapshot)
    breakout_volume_rule, breakout_volume_points = _evaluate_breakout_volume_rule(
        config,
        technical_snapshot,
        breakout_rule=breakout_rule,
    )
    pullback_support_rule, pullback_support_points = _evaluate_pullback_support_rule(
        config,
        technical_snapshot,
    )
    pullback_volume_rule, pullback_volume_points = _evaluate_pullback_volume_rule(
        config,
        technical_snapshot,
        pullback_support_rule=pullback_support_rule,
    )
    pullback_freshness_rule, pullback_freshness_points = (
        _evaluate_pullback_freshness_rule(
            config,
            technical_snapshot,
            pullback_support_rule=pullback_support_rule,
        )
    )
    no_chase_rule, no_chase_points = _evaluate_no_chase_rule(config, technical_snapshot)

    return RuleStateSet(
        score=(
            market_cap_points
            + circulating_market_cap_points
            + close_vs_sma20_points
            + sma20_vs_sma60_points
            + sma20_crossover_points
            + breakout_points
            + breakout_volume_points
            + pullback_support_points
            + pullback_volume_points
            + pullback_freshness_points
            + no_chase_points
        ),
        technical_snapshot_present=technical_snapshot is not None,
        market_cap_rule=market_cap_rule,
        circulating_market_cap_rule=circulating_market_cap_rule,
        close_vs_sma20_rule=close_vs_sma20_rule,
        sma20_vs_sma60_rule=sma20_vs_sma60_rule,
        sma20_crossover_rule=sma20_crossover_rule,
        breakout_rule=breakout_rule,
        breakout_volume_rule=breakout_volume_rule,
        pullback_support_rule=pullback_support_rule,
        pullback_volume_rule=pullback_volume_rule,
        pullback_freshness_rule=pullback_freshness_rule,
        no_chase_rule=no_chase_rule,
    )


def _evaluate_market_cap_rule(
    config: RuleBasedScanConfig,
    snapshot: MarketCapSnapshotRecord | None,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0

    total_market_cap = snapshot.total_market_cap_billion_cny
    if total_market_cap >= config.min_total_market_cap_billion_cny:
        return "candidate_band", 2
    if total_market_cap >= config.watch_floor_billion_cny:
        return "watch_band", 1
    return "below_watch_band", 0


def _evaluate_circulating_market_cap_rule(
    config: RuleBasedScanConfig,
    snapshot: MarketCapSnapshotRecord | None,
) -> tuple[str, int]:
    if snapshot is None or snapshot.circulating_market_cap_billion_cny is None:
        return "missing", 0

    circulating_market_cap = snapshot.circulating_market_cap_billion_cny
    if circulating_market_cap >= config.min_circulating_market_cap_billion_cny:
        return "pass", 1
    if circulating_market_cap >= config.circulating_market_cap_watch_floor_billion_cny:
        return "watch_band", 0
    return "below_watch_band", 0


def _evaluate_close_vs_sma20_rule(
    snapshot: TechnicalSnapshotRecord | None,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if snapshot.close_price_cny is None or snapshot.sma20_cny is None:
        return "missing", 0
    if snapshot.close_price_cny >= snapshot.sma20_cny:
        return "pass", 1
    return "fail", 0


def _evaluate_sma20_vs_sma60_rule(
    snapshot: TechnicalSnapshotRecord | None,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if snapshot.sma20_cny is None or snapshot.sma60_cny is None:
        return "missing", 0
    if snapshot.sma20_cny >= snapshot.sma60_cny:
        return "pass", 1
    return "fail", 0


def _evaluate_sma20_crossover_rule(
    snapshot: TechnicalSnapshotRecord | None,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if (
        snapshot.prev_sma20_cny is None
        or snapshot.prev_sma60_cny is None
        or snapshot.sma20_cny is None
        or snapshot.sma60_cny is None
    ):
        return "missing", 0
    if (
        snapshot.prev_sma20_cny <= snapshot.prev_sma60_cny
        and snapshot.sma20_cny > snapshot.sma60_cny
    ):
        if snapshot.close_price_cny is None or snapshot.prev_close_price_cny is None:
            return "missing_price_confirmation_context", 0
        if snapshot.close_price_cny > snapshot.prev_close_price_cny:
            return "confirmed_bullish_cross", 1
        return "crossed_but_close_not_above_prev_close", 0
    if snapshot.sma20_cny == snapshot.sma60_cny:
        return "touching_sma60", 0
    if snapshot.sma20_cny > snapshot.sma60_cny:
        return "already_above", 0
    return "fail", 0


def _evaluate_breakout_rule(
    snapshot: TechnicalSnapshotRecord | None,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if (
        snapshot.close_price_cny is None
        or snapshot.prev_close_price_cny is None
        or snapshot.breakout_level_cny is None
    ):
        return "missing", 0
    if snapshot.close_price_cny >= snapshot.breakout_level_cny:
        if snapshot.prev_close_price_cny < snapshot.breakout_level_cny:
            return "pass", 1
        return "stale_above_breakout", 0
    if snapshot.prev_close_price_cny >= snapshot.breakout_level_cny:
        return "failed_breakout", 0
    return "fail", 0


def _evaluate_breakout_volume_rule(
    config: RuleBasedScanConfig,
    snapshot: TechnicalSnapshotRecord | None,
    *,
    breakout_rule: str,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if breakout_rule != "pass":
        return "not_applicable", 0
    if snapshot.volume_ratio_20d is None:
        return "missing", 0
    if snapshot.volume_ratio_20d >= config.min_breakout_volume_ratio:
        return "pass", 1
    return "fail", 0


def _evaluate_no_chase_rule(
    config: RuleBasedScanConfig,
    snapshot: TechnicalSnapshotRecord | None,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if snapshot.close_price_cny is None or snapshot.sma20_cny is None:
        return "missing", 0
    if snapshot.close_price_cny < snapshot.sma20_cny:
        return "not_applicable", 0
    max_allowed_close = snapshot.sma20_cny * (1 + config.max_close_above_sma20_ratio)
    if snapshot.close_price_cny <= max_allowed_close:
        return "pass", 1
    return "overextended", 0


def _evaluate_pullback_support_rule(
    config: RuleBasedScanConfig,
    snapshot: TechnicalSnapshotRecord | None,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if (
        snapshot.close_price_cny is None
        or snapshot.prev_close_price_cny is None
        or snapshot.low_price_cny is None
        or snapshot.sma20_cny is None
    ):
        return "missing", 0
    if snapshot.close_price_cny < snapshot.sma20_cny:
        return "closed_below_sma20", 0

    support_floor = snapshot.sma20_cny * (1 - config.support_touch_tolerance_ratio)
    support_ceiling = snapshot.sma20_cny * (1 + config.support_touch_tolerance_ratio)

    if snapshot.low_price_cny < support_floor:
        return "undercut_sma20_support", 0
    if snapshot.low_price_cny > support_ceiling:
        return "support_not_tested", 0
    if snapshot.close_price_cny <= snapshot.prev_close_price_cny:
        return "confirmed_supported_pullback", 1
    return "support_retested_without_pullback_day", 0


def _evaluate_pullback_volume_rule(
    config: RuleBasedScanConfig,
    snapshot: TechnicalSnapshotRecord | None,
    *,
    pullback_support_rule: str,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if pullback_support_rule != "confirmed_supported_pullback":
        return "not_applicable", 0
    if snapshot.volume_ratio_20d is None:
        return "missing", 0
    if snapshot.volume_ratio_20d <= config.max_pullback_volume_ratio:
        return "pass", 1
    return "fail", 0


def _evaluate_pullback_freshness_rule(
    config: RuleBasedScanConfig,
    snapshot: TechnicalSnapshotRecord | None,
    *,
    pullback_support_rule: str,
) -> tuple[str, int]:
    if snapshot is None:
        return "missing", 0
    if pullback_support_rule != "confirmed_supported_pullback":
        return "not_applicable", 0
    if snapshot.close_price_cny is None or snapshot.sma20_cny is None:
        return "missing", 0

    max_fresh_pullback_close = snapshot.sma20_cny * (
        1 + config.max_pullback_close_above_sma20_ratio
    )
    if snapshot.close_price_cny <= max_fresh_pullback_close:
        return "pass", 1
    return "rebounded_too_far_above_sma20", 0
