from __future__ import annotations

import unittest

from src.scanner import DailyScanRecord
from src.scanner.ranking import (
    build_scan_ranking_profile,
    describe_ranking_policy,
    rank_scan_records,
)


def make_scan_record(
    *,
    ts_code: str,
    symbol: str,
    name: str = "示例股份",
    decision: str = "candidate",
    score: int = 9,
    total_market_cap_billion_cny: float | None = 120.0,
    circulating_market_cap_billion_cny: float | None = 60.0,
    market_cap_rule: str = "candidate_band",
    circulating_market_cap_rule: str = "pass",
    close_vs_sma20_rule: str = "pass",
    sma20_vs_sma60_rule: str = "pass",
    sma20_crossover_rule: str = "already_above",
    breakout_rule: str = "fail",
    breakout_volume_rule: str = "not_applicable",
    pullback_support_rule: str = "support_not_tested",
    pullback_volume_rule: str = "not_applicable",
    pullback_freshness_rule: str = "not_applicable",
    no_chase_rule: str = "pass",
    reason: str = "test_reason",
    signal_reasons: tuple[str, ...] = (),
    risk_flags: tuple[str, ...] = (),
) -> DailyScanRecord:
    return DailyScanRecord(
        ts_code=ts_code,
        symbol=symbol,
        name=name,
        exchange="SZSE",
        board="主板",
        total_market_cap_billion_cny=total_market_cap_billion_cny,
        circulating_market_cap_billion_cny=circulating_market_cap_billion_cny,
        market_cap_as_of_date="20260327",
        close_price_cny=10.2,
        prev_close_price_cny=10.0,
        low_price_cny=10.0,
        sma20_cny=10.0,
        sma60_cny=9.8,
        prev_sma20_cny=9.8,
        prev_sma60_cny=9.7,
        breakout_level_cny=10.1,
        volume_ratio_20d=1.3,
        technical_as_of_date="20260327",
        score=score,
        max_score=12,
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
        decision=decision,
        reason=reason,
        signal_reasons=signal_reasons,
        risk_flags=risk_flags,
    )


class ScanRankingTests(unittest.TestCase):
    def test_profile_reports_confirmed_trigger_mix(self) -> None:
        record = make_scan_record(
            ts_code="000001.SZ",
            symbol="000001",
            sma20_crossover_rule="confirmed_bullish_cross",
            breakout_rule="pass",
            breakout_volume_rule="pass",
            reason="candidate_setup_confirmed_with_crossover_and_volume_backed_breakout",
        )

        profile = build_scan_ranking_profile(record)

        self.assertEqual(
            profile.confirmed_triggers,
            ("volume_backed_breakout", "confirmed_crossover"),
        )
        self.assertEqual(profile.confirmed_trigger_count, 2)
        self.assertEqual(profile.confirmed_trigger_strength, 3)
        self.assertEqual(profile.major_risk_tier, 0)

    def test_candidates_with_same_score_prefer_more_confirmations_then_pullback_semantics(
        self,
    ) -> None:
        records = (
            make_scan_record(
                ts_code="000001.SZ",
                symbol="000001",
                score=9,
                sma20_crossover_rule="confirmed_bullish_cross",
                breakout_rule="pass",
                breakout_volume_rule="pass",
                reason="candidate_setup_confirmed_with_crossover_and_volume_backed_breakout",
            ),
            make_scan_record(
                ts_code="000002.SZ",
                symbol="000002",
                score=9,
                pullback_support_rule="confirmed_supported_pullback",
                pullback_volume_rule="pass",
                pullback_freshness_rule="pass",
                reason="candidate_setup_confirmed_with_supported_pullback",
            ),
            make_scan_record(
                ts_code="000003.SZ",
                symbol="000003",
                score=9,
                breakout_rule="pass",
                breakout_volume_rule="pass",
                reason="candidate_setup_confirmed_with_volume_backed_breakout",
            ),
        )

        ordered = rank_scan_records(records)

        self.assertEqual(
            [record.ts_code for record in ordered],
            ["000001.SZ", "000002.SZ", "000003.SZ"],
        )

    def test_watchs_prefer_fresher_confirmation_gap_over_stale_or_reset_damage(
        self,
    ) -> None:
        records = (
            make_scan_record(
                ts_code="000001.SZ",
                symbol="000001",
                decision="watch",
                score=7,
                breakout_rule="pass",
                breakout_volume_rule="missing",
                reason="breakout_needs_volume_confirmation",
                risk_flags=("breakout_missing_volume_confirmation",),
            ),
            make_scan_record(
                ts_code="000002.SZ",
                symbol="000002",
                decision="watch",
                score=7,
                breakout_rule="stale_above_breakout",
                breakout_volume_rule="not_applicable",
                reason="breakout_above_level_but_not_fresh",
                risk_flags=("breakout_trigger_not_fresh",),
            ),
            make_scan_record(
                ts_code="000003.SZ",
                symbol="000003",
                decision="watch",
                score=7,
                breakout_rule="failed_breakout",
                breakout_volume_rule="not_applicable",
                pullback_support_rule="confirmed_supported_pullback",
                pullback_volume_rule="pass",
                pullback_freshness_rule="pass",
                reason="failed_breakout_recovered_at_sma20_support",
                risk_flags=(
                    "breakout_failed_back_below_level",
                    "breakout_failure_requires_reset",
                ),
            ),
        )

        ordered = rank_scan_records(records)

        self.assertEqual(
            [record.ts_code for record in ordered],
            ["000001.SZ", "000002.SZ", "000003.SZ"],
        )

    def test_liquidity_proxy_breaks_final_tie(self) -> None:
        low_liquidity = make_scan_record(
            ts_code="000001.SZ",
            symbol="000001",
            decision="watch",
            score=7,
            breakout_rule="pass",
            breakout_volume_rule="missing",
            circulating_market_cap_billion_cny=35.0,
            total_market_cap_billion_cny=110.0,
            risk_flags=("breakout_missing_volume_confirmation",),
        )
        high_liquidity = make_scan_record(
            ts_code="000002.SZ",
            symbol="000002",
            decision="watch",
            score=7,
            breakout_rule="pass",
            breakout_volume_rule="missing",
            circulating_market_cap_billion_cny=80.0,
            total_market_cap_billion_cny=130.0,
            risk_flags=("breakout_missing_volume_confirmation",),
        )

        ordered = rank_scan_records((low_liquidity, high_liquidity))

        self.assertEqual([record.ts_code for record in ordered], ["000002.SZ", "000001.SZ"])

    def test_policy_description_exposes_public_ordering_contract(self) -> None:
        policy = describe_ranking_policy()

        self.assertEqual(
            policy["decision_priority"],
            ["candidate", "watch", "reject"],
        )
        self.assertEqual(
            policy["confirmed_trigger_priority"],
            [
                "supported_pullback",
                "volume_backed_breakout",
                "confirmed_crossover",
            ],
        )
        self.assertIn(
            "major risk tier ascending so hard reset or structural damage ranks below cleaner setups even when raw score is high",
            policy["ordering_dimensions"],
        )


if __name__ == "__main__":
    unittest.main()
