from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.market_cap import MarketCapSnapshotRecord
from src.technical import TechnicalSnapshotRecord
from src.universe import UniverseRecord

from .models import (
    DECISION_SEQUENCE,
    DailyScanRecord,
    DailyScanResult,
    RuleBasedScanConfig,
)

DECISION_ORDER = {decision: index for index, decision in enumerate(DECISION_SEQUENCE)}


@dataclass(frozen=True, slots=True)
class _RuleEvaluation:
    score: int
    decision: str
    reason: str
    market_cap_rule: str
    close_vs_sma20_rule: str
    sma20_vs_sma60_rule: str
    sma20_crossover_rule: str
    breakout_rule: str
    breakout_volume_rule: str
    pullback_support_rule: str
    pullback_volume_rule: str
    no_chase_rule: str
    signal_reasons: tuple[str, ...]
    risk_flags: tuple[str, ...]


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
        snapshot_by_code = self._build_snapshot_lookup(market_cap_records)
        technical_by_code = self._build_technical_lookup(technical_records or ())
        eligible_universe = [record for record in universe_records if record.eligible]

        scan_records: list[DailyScanRecord] = []
        for record in sorted(eligible_universe, key=lambda item: item.symbol):
            market_cap_snapshot = snapshot_by_code.get(record.ts_code)
            technical_snapshot = technical_by_code.get(record.ts_code)
            evaluation = self._evaluate(market_cap_snapshot, technical_snapshot)
            scan_records.append(
                DailyScanRecord(
                    ts_code=record.ts_code,
                    symbol=record.symbol,
                    name=record.name,
                    exchange=record.exchange,
                    board=record.board,
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
                        technical_snapshot.prev_close_price_cny
                        if technical_snapshot
                        else None
                    ),
                    low_price_cny=(
                        technical_snapshot.low_price_cny if technical_snapshot else None
                    ),
                    sma20_cny=(
                        technical_snapshot.sma20_cny if technical_snapshot else None
                    ),
                    sma60_cny=(
                        technical_snapshot.sma60_cny if technical_snapshot else None
                    ),
                    prev_sma20_cny=(
                        technical_snapshot.prev_sma20_cny
                        if technical_snapshot
                        else None
                    ),
                    prev_sma60_cny=(
                        technical_snapshot.prev_sma60_cny
                        if technical_snapshot
                        else None
                    ),
                    breakout_level_cny=(
                        technical_snapshot.breakout_level_cny
                        if technical_snapshot
                        else None
                    ),
                    volume_ratio_20d=(
                        technical_snapshot.volume_ratio_20d
                        if technical_snapshot
                        else None
                    ),
                    technical_as_of_date=(
                        technical_snapshot.as_of_date if technical_snapshot else None
                    ),
                    score=evaluation.score,
                    max_score=self._config.max_score,
                    market_cap_rule=evaluation.market_cap_rule,
                    close_vs_sma20_rule=evaluation.close_vs_sma20_rule,
                    sma20_vs_sma60_rule=evaluation.sma20_vs_sma60_rule,
                    sma20_crossover_rule=evaluation.sma20_crossover_rule,
                    breakout_rule=evaluation.breakout_rule,
                    breakout_volume_rule=evaluation.breakout_volume_rule,
                    pullback_support_rule=evaluation.pullback_support_rule,
                    pullback_volume_rule=evaluation.pullback_volume_rule,
                    no_chase_rule=evaluation.no_chase_rule,
                    decision=evaluation.decision,
                    reason=evaluation.reason,
                    signal_reasons=evaluation.signal_reasons,
                    risk_flags=evaluation.risk_flags,
                )
            )

        ordered_records = tuple(
            sorted(
                scan_records,
                key=lambda item: (
                    DECISION_ORDER[item.decision],
                    -item.score,
                    -(item.total_market_cap_billion_cny or -1.0),
                    item.symbol,
                ),
            )
        )
        return DailyScanResult(
            records=ordered_records,
            total_universe_count=len(universe_records),
            eligible_universe_count=len(eligible_universe),
        )

    def _build_snapshot_lookup(
        self,
        market_cap_records: Sequence[MarketCapSnapshotRecord],
    ) -> dict[str, MarketCapSnapshotRecord]:
        snapshot_by_code: dict[str, MarketCapSnapshotRecord] = {}
        for record in market_cap_records:
            if record.ts_code in snapshot_by_code:
                raise ValueError(
                    f"duplicate market-cap snapshot record for {record.ts_code}"
                )
            snapshot_by_code[record.ts_code] = record
        return snapshot_by_code

    def _build_technical_lookup(
        self,
        technical_records: Sequence[TechnicalSnapshotRecord],
    ) -> dict[str, TechnicalSnapshotRecord]:
        technical_by_code: dict[str, TechnicalSnapshotRecord] = {}
        for record in technical_records:
            if record.ts_code in technical_by_code:
                raise ValueError(
                    f"duplicate technical snapshot record for {record.ts_code}"
                )
            technical_by_code[record.ts_code] = record
        return technical_by_code

    def _evaluate(
        self,
        market_cap_snapshot: MarketCapSnapshotRecord | None,
        technical_snapshot: TechnicalSnapshotRecord | None,
    ) -> _RuleEvaluation:
        market_cap_rule, market_cap_points = self._evaluate_market_cap_rule(
            market_cap_snapshot
        )
        close_vs_sma20_rule, close_vs_sma20_points = self._evaluate_close_vs_sma20_rule(
            technical_snapshot
        )
        sma20_vs_sma60_rule, sma20_vs_sma60_points = self._evaluate_sma20_vs_sma60_rule(
            technical_snapshot
        )
        sma20_crossover_rule, sma20_crossover_points = (
            self._evaluate_sma20_crossover_rule(technical_snapshot)
        )
        breakout_rule, breakout_points = self._evaluate_breakout_rule(
            technical_snapshot
        )
        breakout_volume_rule, breakout_volume_points = (
            self._evaluate_breakout_volume_rule(
                technical_snapshot,
                breakout_rule=breakout_rule,
            )
        )
        pullback_support_rule, pullback_support_points = (
            self._evaluate_pullback_support_rule(technical_snapshot)
        )
        pullback_volume_rule, pullback_volume_points = (
            self._evaluate_pullback_volume_rule(
                technical_snapshot,
                pullback_support_rule=pullback_support_rule,
            )
        )
        no_chase_rule, no_chase_points = self._evaluate_no_chase_rule(
            technical_snapshot
        )

        score = (
            market_cap_points
            + close_vs_sma20_points
            + sma20_vs_sma60_points
            + sma20_crossover_points
            + breakout_points
            + breakout_volume_points
            + pullback_support_points
            + pullback_volume_points
            + no_chase_points
        )

        crossover_trigger_confirmed = (
            sma20_crossover_rule == "confirmed_bullish_cross"
        )
        breakout_trigger_confirmed = (
            breakout_rule == "pass" and breakout_volume_rule == "pass"
        )
        pullback_trigger_confirmed = (
            pullback_support_rule == "confirmed_supported_pullback"
            and pullback_volume_rule == "pass"
        )

        signal_reasons = self._build_signal_reasons(
            market_cap_rule=market_cap_rule,
            close_vs_sma20_rule=close_vs_sma20_rule,
            sma20_vs_sma60_rule=sma20_vs_sma60_rule,
            sma20_crossover_rule=sma20_crossover_rule,
            breakout_rule=breakout_rule,
            breakout_volume_rule=breakout_volume_rule,
            pullback_support_rule=pullback_support_rule,
            pullback_volume_rule=pullback_volume_rule,
            no_chase_rule=no_chase_rule,
        )
        risk_flags = self._build_risk_flags(
            market_cap_rule=market_cap_rule,
            technical_snapshot=technical_snapshot,
            close_vs_sma20_rule=close_vs_sma20_rule,
            sma20_vs_sma60_rule=sma20_vs_sma60_rule,
            sma20_crossover_rule=sma20_crossover_rule,
            breakout_rule=breakout_rule,
            breakout_volume_rule=breakout_volume_rule,
            pullback_support_rule=pullback_support_rule,
            pullback_volume_rule=pullback_volume_rule,
            no_chase_rule=no_chase_rule,
            crossover_trigger_confirmed=crossover_trigger_confirmed,
            breakout_trigger_confirmed=breakout_trigger_confirmed,
            pullback_trigger_confirmed=pullback_trigger_confirmed,
        )

        if market_cap_rule == "missing":
            return _RuleEvaluation(
                score=score,
                decision="reject",
                reason="missing_market_cap_snapshot",
                market_cap_rule=market_cap_rule,
                close_vs_sma20_rule=close_vs_sma20_rule,
                sma20_vs_sma60_rule=sma20_vs_sma60_rule,
                sma20_crossover_rule=sma20_crossover_rule,
                breakout_rule=breakout_rule,
                breakout_volume_rule=breakout_volume_rule,
                pullback_support_rule=pullback_support_rule,
                pullback_volume_rule=pullback_volume_rule,
                no_chase_rule=no_chase_rule,
                signal_reasons=signal_reasons,
                risk_flags=risk_flags,
            )

        if market_cap_rule == "below_watch_band":
            return _RuleEvaluation(
                score=score,
                decision="reject",
                reason="below_watch_band",
                market_cap_rule=market_cap_rule,
                close_vs_sma20_rule=close_vs_sma20_rule,
                sma20_vs_sma60_rule=sma20_vs_sma60_rule,
                sma20_crossover_rule=sma20_crossover_rule,
                breakout_rule=breakout_rule,
                breakout_volume_rule=breakout_volume_rule,
                pullback_support_rule=pullback_support_rule,
                pullback_volume_rule=pullback_volume_rule,
                no_chase_rule=no_chase_rule,
                signal_reasons=signal_reasons,
                risk_flags=risk_flags,
            )

        base_trend_confirmed = (
            close_vs_sma20_rule == "pass" and sma20_vs_sma60_rule == "pass"
        )
        entry_trigger_confirmed = (
            crossover_trigger_confirmed
            or breakout_trigger_confirmed
            or pullback_trigger_confirmed
        )

        if (
            market_cap_rule == "candidate_band"
            and base_trend_confirmed
            and entry_trigger_confirmed
            and no_chase_rule == "pass"
        ):
            return _RuleEvaluation(
                score=score,
                decision="candidate",
                reason=self._build_candidate_reason(
                    crossover_trigger_confirmed=crossover_trigger_confirmed,
                    breakout_trigger_confirmed=breakout_trigger_confirmed,
                    pullback_trigger_confirmed=pullback_trigger_confirmed,
                ),
                market_cap_rule=market_cap_rule,
                close_vs_sma20_rule=close_vs_sma20_rule,
                sma20_vs_sma60_rule=sma20_vs_sma60_rule,
                sma20_crossover_rule=sma20_crossover_rule,
                breakout_rule=breakout_rule,
                breakout_volume_rule=breakout_volume_rule,
                pullback_support_rule=pullback_support_rule,
                pullback_volume_rule=pullback_volume_rule,
                no_chase_rule=no_chase_rule,
                signal_reasons=signal_reasons,
                risk_flags=risk_flags,
            )

        return _RuleEvaluation(
            score=score,
            decision="watch",
            reason=self._build_watch_reason(
                market_cap_rule=market_cap_rule,
                close_vs_sma20_rule=close_vs_sma20_rule,
                sma20_vs_sma60_rule=sma20_vs_sma60_rule,
                sma20_crossover_rule=sma20_crossover_rule,
                breakout_rule=breakout_rule,
                breakout_volume_rule=breakout_volume_rule,
                pullback_support_rule=pullback_support_rule,
                pullback_volume_rule=pullback_volume_rule,
                no_chase_rule=no_chase_rule,
            ),
            market_cap_rule=market_cap_rule,
            close_vs_sma20_rule=close_vs_sma20_rule,
            sma20_vs_sma60_rule=sma20_vs_sma60_rule,
            sma20_crossover_rule=sma20_crossover_rule,
            breakout_rule=breakout_rule,
            breakout_volume_rule=breakout_volume_rule,
            pullback_support_rule=pullback_support_rule,
            pullback_volume_rule=pullback_volume_rule,
            no_chase_rule=no_chase_rule,
            signal_reasons=signal_reasons,
            risk_flags=risk_flags,
        )

    def _evaluate_market_cap_rule(
        self,
        snapshot: MarketCapSnapshotRecord | None,
    ) -> tuple[str, int]:
        if snapshot is None:
            return "missing", 0

        total_market_cap = snapshot.total_market_cap_billion_cny
        if total_market_cap >= self._config.min_total_market_cap_billion_cny:
            return "candidate_band", 2
        if total_market_cap >= self._config.watch_floor_billion_cny:
            return "watch_band", 1
        return "below_watch_band", 0

    def _evaluate_close_vs_sma20_rule(
        self,
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
        self,
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
        self,
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
            and snapshot.sma20_cny >= snapshot.sma60_cny
        ):
            return "confirmed_bullish_cross", 1
        if snapshot.sma20_cny >= snapshot.sma60_cny:
            return "already_above", 0
        return "fail", 0

    def _evaluate_breakout_rule(
        self,
        snapshot: TechnicalSnapshotRecord | None,
    ) -> tuple[str, int]:
        if snapshot is None:
            return "missing", 0
        if snapshot.close_price_cny is None or snapshot.breakout_level_cny is None:
            return "missing", 0
        if snapshot.close_price_cny >= snapshot.breakout_level_cny:
            return "pass", 1
        return "fail", 0

    def _evaluate_breakout_volume_rule(
        self,
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
        if snapshot.volume_ratio_20d >= self._config.min_breakout_volume_ratio:
            return "pass", 1
        return "fail", 0

    def _evaluate_no_chase_rule(
        self,
        snapshot: TechnicalSnapshotRecord | None,
    ) -> tuple[str, int]:
        if snapshot is None:
            return "missing", 0
        if snapshot.close_price_cny is None or snapshot.sma20_cny is None:
            return "missing", 0
        if snapshot.close_price_cny < snapshot.sma20_cny:
            return "not_applicable", 0
        max_allowed_close = snapshot.sma20_cny * (
            1 + self._config.max_close_above_sma20_ratio
        )
        if snapshot.close_price_cny <= max_allowed_close:
            return "pass", 1
        return "overextended", 0

    def _evaluate_pullback_support_rule(
        self,
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

        support_floor = snapshot.sma20_cny * (
            1 - self._config.support_touch_tolerance_ratio
        )
        support_ceiling = snapshot.sma20_cny * (
            1 + self._config.support_touch_tolerance_ratio
        )

        if snapshot.low_price_cny < support_floor:
            return "undercut_sma20_support", 0
        if snapshot.low_price_cny > support_ceiling:
            return "support_not_tested", 0
        if snapshot.close_price_cny <= snapshot.prev_close_price_cny:
            return "confirmed_supported_pullback", 1
        return "support_retested_without_pullback_day", 0

    def _evaluate_pullback_volume_rule(
        self,
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
        if snapshot.volume_ratio_20d <= self._config.max_pullback_volume_ratio:
            return "pass", 1
        return "fail", 0

    def _build_candidate_reason(
        self,
        *,
        crossover_trigger_confirmed: bool,
        breakout_trigger_confirmed: bool,
        pullback_trigger_confirmed: bool,
    ) -> str:
        if (
            crossover_trigger_confirmed
            and breakout_trigger_confirmed
            and pullback_trigger_confirmed
        ):
            return (
                "candidate_setup_confirmed_with_crossover_breakout_and_supported_pullback"
            )
        if crossover_trigger_confirmed and breakout_trigger_confirmed:
            return "candidate_setup_confirmed_with_crossover_and_volume_backed_breakout"
        if crossover_trigger_confirmed and pullback_trigger_confirmed:
            return "candidate_setup_confirmed_with_crossover_and_supported_pullback"
        if breakout_trigger_confirmed and pullback_trigger_confirmed:
            return (
                "candidate_setup_confirmed_with_volume_backed_breakout_and_supported_pullback"
            )
        if crossover_trigger_confirmed:
            return "candidate_setup_confirmed_with_crossover"
        if breakout_trigger_confirmed:
            return "candidate_setup_confirmed_with_volume_backed_breakout"
        return "candidate_setup_confirmed_with_supported_pullback"

    def _build_watch_reason(
        self,
        *,
        market_cap_rule: str,
        close_vs_sma20_rule: str,
        sma20_vs_sma60_rule: str,
        sma20_crossover_rule: str,
        breakout_rule: str,
        breakout_volume_rule: str,
        pullback_support_rule: str,
        pullback_volume_rule: str,
        no_chase_rule: str,
    ) -> str:
        if market_cap_rule == "watch_band":
            return "market_cap_in_watch_band"
        if close_vs_sma20_rule == "fail":
            if pullback_support_rule == "closed_below_sma20":
                return "pullback_closed_below_sma20_support"
            return "close_below_sma20_trend_filter"
        if sma20_vs_sma60_rule == "fail":
            return "sma20_below_sma60_trend_filter"
        if close_vs_sma20_rule != "pass" or sma20_vs_sma60_rule != "pass":
            return "trend_filter_incomplete"
        if no_chase_rule == "overextended":
            return "overextended_no_chase_guard"
        if no_chase_rule != "pass":
            return "no_chase_guard_incomplete"
        if pullback_support_rule == "undercut_sma20_support":
            return "pullback_undercut_sma20_support"
        if (
            sma20_crossover_rule != "confirmed_bullish_cross"
            and breakout_rule == "pass"
            and breakout_volume_rule == "missing"
        ):
            return "breakout_needs_volume_confirmation"
        if (
            sma20_crossover_rule != "confirmed_bullish_cross"
            and breakout_rule == "pass"
            and breakout_volume_rule == "fail"
        ):
            return "breakout_volume_confirmation_failed"
        if (
            sma20_crossover_rule != "confirmed_bullish_cross"
            and breakout_rule != "pass"
            and pullback_support_rule == "confirmed_supported_pullback"
            and pullback_volume_rule == "missing"
        ):
            return "pullback_needs_volume_contraction_context"
        if (
            sma20_crossover_rule != "confirmed_bullish_cross"
            and breakout_rule != "pass"
            and pullback_support_rule == "confirmed_supported_pullback"
            and pullback_volume_rule == "fail"
        ):
            return "pullback_volume_pressure_risk"
        if (
            sma20_crossover_rule != "confirmed_bullish_cross"
            and breakout_rule != "pass"
            and pullback_support_rule == "closed_below_sma20"
        ):
            return "pullback_closed_below_sma20_support"
        if (
            sma20_crossover_rule != "confirmed_bullish_cross"
            and breakout_rule != "pass"
            and pullback_support_rule == "undercut_sma20_support"
        ):
            return "pullback_undercut_sma20_support"
        if (
            sma20_crossover_rule != "confirmed_bullish_cross"
            and breakout_rule != "pass"
            and pullback_support_rule != "confirmed_supported_pullback"
        ):
            return "waiting_for_crossover_breakout_or_supported_pullback"
        return "market_cap_passed_but_candidate_gate_not_met"

    def _build_signal_reasons(
        self,
        *,
        market_cap_rule: str,
        close_vs_sma20_rule: str,
        sma20_vs_sma60_rule: str,
        sma20_crossover_rule: str,
        breakout_rule: str,
        breakout_volume_rule: str,
        pullback_support_rule: str,
        pullback_volume_rule: str,
        no_chase_rule: str,
    ) -> tuple[str, ...]:
        reasons: list[str] = []

        if market_cap_rule == "candidate_band":
            reasons.append("market_cap_candidate_band")
        elif market_cap_rule == "watch_band":
            reasons.append("market_cap_watch_band")

        if close_vs_sma20_rule == "pass":
            reasons.append("close_at_or_above_sma20")
        if sma20_vs_sma60_rule == "pass":
            reasons.append("sma20_at_or_above_sma60")
        if sma20_crossover_rule == "confirmed_bullish_cross":
            reasons.append("confirmed_sma20_bullish_crossover")
        elif sma20_crossover_rule == "already_above":
            reasons.append("sma20_already_above_sma60")
        if breakout_rule == "pass":
            reasons.append("breakout_level_cleared")
        if breakout_volume_rule == "pass":
            reasons.append("breakout_volume_confirmed")
        if pullback_support_rule == "confirmed_supported_pullback":
            reasons.append("supported_pullback_at_sma20")
        if pullback_volume_rule == "pass":
            reasons.append("pullback_volume_contracted")
        if no_chase_rule == "pass":
            reasons.append("no_chase_guard_passed")

        return tuple(reasons)

    def _build_risk_flags(
        self,
        *,
        market_cap_rule: str,
        technical_snapshot: TechnicalSnapshotRecord | None,
        close_vs_sma20_rule: str,
        sma20_vs_sma60_rule: str,
        sma20_crossover_rule: str,
        breakout_rule: str,
        breakout_volume_rule: str,
        pullback_support_rule: str,
        pullback_volume_rule: str,
        no_chase_rule: str,
        crossover_trigger_confirmed: bool,
        breakout_trigger_confirmed: bool,
        pullback_trigger_confirmed: bool,
    ) -> tuple[str, ...]:
        flags: list[str] = []

        if market_cap_rule == "missing":
            flags.append("missing_market_cap_snapshot")
        elif market_cap_rule == "below_watch_band":
            flags.append("below_watch_band")
        elif market_cap_rule == "watch_band":
            flags.append("market_cap_only_watch_band")

        if technical_snapshot is None:
            flags.append("technical_snapshot_missing")
            return tuple(flags)

        if close_vs_sma20_rule == "fail":
            flags.append("close_below_sma20")
        elif close_vs_sma20_rule == "missing":
            flags.append("missing_close_or_sma20")

        if sma20_vs_sma60_rule == "fail":
            flags.append("sma20_below_sma60")
        elif sma20_vs_sma60_rule == "missing":
            flags.append("missing_sma20_or_sma60")

        if no_chase_rule == "overextended":
            flags.append("overextended_above_sma20")
        elif no_chase_rule == "missing":
            flags.append("missing_no_chase_context")

        if pullback_support_rule == "closed_below_sma20":
            flags.append("pullback_closed_below_sma20_support")
        elif pullback_support_rule == "undercut_sma20_support":
            flags.append("pullback_undercut_sma20_support")

        if breakout_rule == "pass" and breakout_volume_rule == "missing":
            flags.append("breakout_missing_volume_confirmation")
        elif breakout_rule == "pass" and breakout_volume_rule == "fail":
            flags.append("breakout_volume_below_threshold")

        if (
            pullback_support_rule == "confirmed_supported_pullback"
            and pullback_volume_rule == "missing"
        ):
            flags.append("pullback_missing_volume_contraction")
        elif (
            pullback_support_rule == "confirmed_supported_pullback"
            and pullback_volume_rule == "fail"
        ):
            flags.append("pullback_volume_above_threshold")

        if not (
            crossover_trigger_confirmed
            or breakout_trigger_confirmed
            or pullback_trigger_confirmed
        ):
            if sma20_crossover_rule == "missing":
                flags.append("missing_crossover_context")
            if breakout_rule == "missing":
                flags.append("missing_breakout_context")
            elif breakout_rule == "fail":
                flags.append("breakout_not_confirmed")
            if pullback_support_rule == "missing":
                flags.append("missing_pullback_context")
            elif pullback_support_rule == "support_not_tested":
                flags.append("pullback_support_not_tested")
            elif pullback_support_rule == "support_retested_without_pullback_day":
                flags.append("pullback_day_not_confirmed")

        return tuple(flags)


MarketCapThresholdScanner = RuleBasedScanner
