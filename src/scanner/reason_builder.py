from __future__ import annotations

from dataclasses import dataclass

from .rules import RuleStateSet


@dataclass(frozen=True, slots=True)
class ScanEvaluation:
    rules: RuleStateSet
    decision: str
    reason: str
    signal_reasons: tuple[str, ...]
    risk_flags: tuple[str, ...]

    @property
    def score(self) -> int:
        return self.rules.score


def build_scan_evaluation(rules: RuleStateSet) -> ScanEvaluation:
    signal_reasons = _build_signal_reasons(rules)
    risk_flags = _build_risk_flags(rules)

    if rules.market_cap_rule == "missing":
        return ScanEvaluation(
            rules=rules,
            decision="reject",
            reason="missing_market_cap_snapshot",
            signal_reasons=signal_reasons,
            risk_flags=risk_flags,
        )

    if rules.market_cap_rule == "below_watch_band":
        return ScanEvaluation(
            rules=rules,
            decision="reject",
            reason="below_watch_band",
            signal_reasons=signal_reasons,
            risk_flags=risk_flags,
        )

    if rules.circulating_market_cap_rule == "below_watch_band":
        return ScanEvaluation(
            rules=rules,
            decision="reject",
            reason="circulating_market_cap_below_watch_band",
            signal_reasons=signal_reasons,
            risk_flags=risk_flags,
        )

    if (
        rules.market_cap_rule == "candidate_band"
        and rules.circulating_market_cap_rule == "pass"
        and rules.base_trend_confirmed
        and rules.entry_trigger_confirmed
        and not rules.breakout_failure_active
        and rules.no_chase_rule == "pass"
    ):
        return ScanEvaluation(
            rules=rules,
            decision="candidate",
            reason=_build_candidate_reason(rules),
            signal_reasons=signal_reasons,
            risk_flags=risk_flags,
        )

    return ScanEvaluation(
        rules=rules,
        decision="watch",
        reason=_build_watch_reason(rules),
        signal_reasons=signal_reasons,
        risk_flags=risk_flags,
    )


def _build_candidate_reason(rules: RuleStateSet) -> str:
    if (
        rules.crossover_trigger_confirmed
        and rules.breakout_trigger_confirmed
        and rules.pullback_trigger_confirmed
    ):
        return (
            "candidate_setup_confirmed_with_crossover_breakout_and_supported_pullback"
        )
    if rules.crossover_trigger_confirmed and rules.breakout_trigger_confirmed:
        return "candidate_setup_confirmed_with_crossover_and_volume_backed_breakout"
    if rules.crossover_trigger_confirmed and rules.pullback_trigger_confirmed:
        return "candidate_setup_confirmed_with_crossover_and_supported_pullback"
    if rules.breakout_trigger_confirmed and rules.pullback_trigger_confirmed:
        return (
            "candidate_setup_confirmed_with_volume_backed_breakout_and_supported_pullback"
        )
    if rules.crossover_trigger_confirmed:
        return "candidate_setup_confirmed_with_crossover"
    if rules.breakout_trigger_confirmed:
        return "candidate_setup_confirmed_with_volume_backed_breakout"
    return "candidate_setup_confirmed_with_supported_pullback"


def _build_watch_reason(rules: RuleStateSet) -> str:
    if rules.market_cap_rule == "watch_band":
        return "market_cap_in_watch_band"
    if rules.circulating_market_cap_rule == "watch_band":
        return "circulating_market_cap_in_watch_band"
    if rules.circulating_market_cap_rule == "missing":
        return "circulating_market_cap_incomplete"
    if rules.close_vs_sma20_rule == "fail":
        if rules.pullback_support_rule == "closed_below_sma20":
            return "pullback_closed_below_sma20_support"
        return "close_below_sma20_trend_filter"
    if rules.sma20_vs_sma60_rule == "fail":
        return "sma20_below_sma60_trend_filter"
    if rules.close_vs_sma20_rule != "pass" or rules.sma20_vs_sma60_rule != "pass":
        return "trend_filter_incomplete"
    if rules.no_chase_rule == "overextended":
        return "overextended_no_chase_guard"
    if rules.no_chase_rule != "pass":
        return "no_chase_guard_incomplete"
    if rules.breakout_rule == "failed_breakout":
        if rules.pullback_trigger_confirmed:
            return "failed_breakout_recovered_at_sma20_support"
        return "breakout_failed_back_below_level"
    if rules.pullback_support_rule == "undercut_sma20_support":
        return "pullback_undercut_sma20_support"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule == "pass"
        and rules.breakout_volume_rule == "missing"
    ):
        return "breakout_needs_volume_confirmation"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule == "pass"
        and rules.breakout_volume_rule == "fail"
    ):
        return "breakout_volume_confirmation_failed"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule == "confirmed_supported_pullback"
        and rules.pullback_volume_rule == "missing"
    ):
        return "pullback_needs_volume_contraction_context"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule == "confirmed_supported_pullback"
        and rules.pullback_volume_rule == "fail"
    ):
        return "pullback_volume_pressure_risk"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule == "confirmed_supported_pullback"
        and rules.pullback_volume_rule == "pass"
        and rules.pullback_freshness_rule == "rebounded_too_far_above_sma20"
    ):
        return "pullback_rebounded_too_far_from_sma20"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule == "closed_below_sma20"
    ):
        return "pullback_closed_below_sma20_support"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule == "undercut_sma20_support"
    ):
        return "pullback_undercut_sma20_support"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule == "stale_above_breakout"
        and rules.pullback_support_rule != "confirmed_supported_pullback"
    ):
        return "breakout_above_level_but_not_fresh"
    if (
        rules.sma20_crossover_rule == "touching_sma60"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule != "confirmed_supported_pullback"
    ):
        return "crossover_touching_sma60_needs_clear_break"
    if (
        rules.sma20_crossover_rule == "crossed_but_close_not_above_prev_close"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule != "confirmed_supported_pullback"
    ):
        return "crossover_needs_price_confirmation"
    if (
        rules.sma20_crossover_rule == "missing_price_confirmation_context"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule != "confirmed_supported_pullback"
    ):
        return "crossover_price_confirmation_incomplete"
    if (
        rules.sma20_crossover_rule != "confirmed_bullish_cross"
        and rules.breakout_rule != "pass"
        and rules.pullback_support_rule != "confirmed_supported_pullback"
    ):
        return "waiting_for_crossover_breakout_or_supported_pullback"
    return "market_cap_passed_but_candidate_gate_not_met"


def _build_signal_reasons(rules: RuleStateSet) -> tuple[str, ...]:
    reasons: list[str] = []

    if rules.market_cap_rule == "candidate_band":
        reasons.append("market_cap_candidate_band")
    elif rules.market_cap_rule == "watch_band":
        reasons.append("market_cap_watch_band")
    if rules.circulating_market_cap_rule == "pass":
        reasons.append("circulating_market_cap_liquidity_passed")

    if rules.close_vs_sma20_rule == "pass":
        reasons.append("close_at_or_above_sma20")
    if rules.sma20_vs_sma60_rule == "pass":
        reasons.append("sma20_at_or_above_sma60")
    if rules.sma20_crossover_rule == "confirmed_bullish_cross":
        reasons.append("confirmed_sma20_bullish_crossover")
    elif rules.sma20_crossover_rule == "already_above":
        reasons.append("sma20_already_above_sma60")
    if rules.breakout_rule == "pass":
        reasons.append("fresh_breakout_level_cleared")
    elif rules.breakout_rule == "stale_above_breakout":
        reasons.append("price_still_above_breakout_level")
    elif (
        rules.breakout_rule == "failed_breakout"
        and rules.pullback_support_rule == "confirmed_supported_pullback"
    ):
        reasons.append("failed_breakout_recovered_at_sma20_support")
    if rules.breakout_volume_rule == "pass":
        reasons.append("breakout_volume_confirmed")
    if rules.pullback_support_rule == "confirmed_supported_pullback":
        reasons.append("supported_pullback_at_sma20")
    if rules.pullback_volume_rule == "pass":
        reasons.append("pullback_volume_contracted")
    if rules.pullback_freshness_rule == "pass":
        reasons.append("fresh_pullback_entry_near_sma20")
    if rules.no_chase_rule == "pass":
        reasons.append("no_chase_guard_passed")

    return tuple(reasons)


def _build_risk_flags(rules: RuleStateSet) -> tuple[str, ...]:
    flags: list[str] = []

    if rules.market_cap_rule == "missing":
        flags.append("missing_market_cap_snapshot")
    elif rules.market_cap_rule == "below_watch_band":
        flags.append("below_watch_band")
    elif rules.market_cap_rule == "watch_band":
        flags.append("market_cap_only_watch_band")

    if rules.circulating_market_cap_rule == "missing":
        flags.append("missing_circulating_market_cap")
    elif rules.circulating_market_cap_rule == "watch_band":
        flags.append("circulating_market_cap_only_watch_band")
    elif rules.circulating_market_cap_rule == "below_watch_band":
        flags.append("circulating_market_cap_below_watch_band")

    if not rules.technical_snapshot_present:
        flags.append("technical_snapshot_missing")
        return tuple(flags)

    if rules.close_vs_sma20_rule == "fail":
        flags.append("close_below_sma20")
    elif rules.close_vs_sma20_rule == "missing":
        flags.append("missing_close_or_sma20")

    if rules.sma20_vs_sma60_rule == "fail":
        flags.append("sma20_below_sma60")
    elif rules.sma20_vs_sma60_rule == "missing":
        flags.append("missing_sma20_or_sma60")

    if rules.no_chase_rule == "overextended":
        flags.append("overextended_above_sma20")
    elif rules.no_chase_rule == "missing":
        flags.append("missing_no_chase_context")

    if rules.pullback_support_rule == "closed_below_sma20":
        flags.append("pullback_closed_below_sma20_support")
    elif rules.pullback_support_rule == "undercut_sma20_support":
        flags.append("pullback_undercut_sma20_support")

    if rules.breakout_rule == "pass" and rules.breakout_volume_rule == "missing":
        flags.append("breakout_missing_volume_confirmation")
    elif rules.breakout_rule == "pass" and rules.breakout_volume_rule == "fail":
        flags.append("breakout_volume_below_threshold")

    if (
        rules.pullback_support_rule == "confirmed_supported_pullback"
        and rules.pullback_volume_rule == "missing"
    ):
        flags.append("pullback_missing_volume_contraction")
    elif (
        rules.pullback_support_rule == "confirmed_supported_pullback"
        and rules.pullback_volume_rule == "fail"
    ):
        flags.append("pullback_volume_above_threshold")

    if rules.breakout_rule == "failed_breakout":
        flags.append("breakout_failed_back_below_level")
        if rules.crossover_trigger_confirmed or rules.pullback_trigger_confirmed:
            flags.append("breakout_failure_requires_reset")

    if not rules.entry_trigger_confirmed:
        if rules.sma20_crossover_rule == "missing":
            flags.append("missing_crossover_context")
        elif rules.sma20_crossover_rule == "touching_sma60":
            flags.append("crossover_touching_sma60")
        elif rules.sma20_crossover_rule == "crossed_but_close_not_above_prev_close":
            flags.append("crossover_price_confirmation_failed")
        elif rules.sma20_crossover_rule == "missing_price_confirmation_context":
            flags.append("missing_crossover_price_confirmation")
        if rules.breakout_rule == "missing":
            flags.append("missing_breakout_context")
        elif rules.breakout_rule == "fail":
            flags.append("breakout_not_confirmed")
        elif rules.breakout_rule == "stale_above_breakout":
            flags.append("breakout_trigger_not_fresh")
        if rules.pullback_support_rule == "missing":
            flags.append("missing_pullback_context")
        elif rules.pullback_support_rule == "support_not_tested":
            flags.append("pullback_support_not_tested")
        elif rules.pullback_support_rule == "support_retested_without_pullback_day":
            flags.append("pullback_day_not_confirmed")
        elif (
            rules.pullback_support_rule == "confirmed_supported_pullback"
            and rules.pullback_volume_rule == "pass"
            and rules.pullback_freshness_rule == "rebounded_too_far_above_sma20"
        ):
            flags.append("pullback_trigger_not_fresh")

    return tuple(flags)
