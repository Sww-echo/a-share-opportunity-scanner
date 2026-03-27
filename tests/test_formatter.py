from __future__ import annotations

import textwrap
import unittest

from src.scanner import (
    DailyScanRecord,
    DailyScanResult,
    RuleBasedScanConfig,
    format_daily_scan_text_summary,
)


def make_scan_record(
    *,
    ts_code: str,
    symbol: str,
    name: str,
    decision: str,
    score: int,
    total_market_cap_billion_cny: float | None,
    circulating_market_cap_billion_cny: float | None,
    market_cap_rule: str,
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
    reason: str,
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


class ScanFormatterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = RuleBasedScanConfig()

    def test_text_summary_renders_ranked_sections_with_review_fields(self) -> None:
        result = DailyScanResult(
            records=(
                make_scan_record(
                    ts_code="000001.SZ",
                    symbol="000001",
                    name="候选一号",
                    decision="candidate",
                    score=9,
                    total_market_cap_billion_cny=120.0,
                    circulating_market_cap_billion_cny=60.0,
                    market_cap_rule="candidate_band",
                    sma20_crossover_rule="confirmed_bullish_cross",
                    breakout_rule="pass",
                    breakout_volume_rule="pass",
                    reason="candidate_setup_confirmed_with_crossover_and_volume_backed_breakout",
                    signal_reasons=(
                        "market_cap_candidate_band",
                        "circulating_market_cap_liquidity_passed",
                        "fresh_breakout_level_cleared",
                        "breakout_volume_confirmed",
                    ),
                ),
                make_scan_record(
                    ts_code="000002.SZ",
                    symbol="000002",
                    name="观察二号",
                    decision="watch",
                    score=7,
                    total_market_cap_billion_cny=110.0,
                    circulating_market_cap_billion_cny=55.0,
                    market_cap_rule="candidate_band",
                    sma20_crossover_rule="already_above",
                    breakout_rule="pass",
                    breakout_volume_rule="missing",
                    reason="breakout_needs_volume_confirmation",
                    signal_reasons=("fresh_breakout_level_cleared",),
                    risk_flags=("breakout_missing_volume_confirmation",),
                ),
                make_scan_record(
                    ts_code="000003.SZ",
                    symbol="000003",
                    name="剔除三号",
                    decision="reject",
                    score=1,
                    total_market_cap_billion_cny=60.0,
                    circulating_market_cap_billion_cny=20.0,
                    market_cap_rule="below_watch_band",
                    circulating_market_cap_rule="below_watch_band",
                    close_vs_sma20_rule="missing",
                    sma20_vs_sma60_rule="missing",
                    sma20_crossover_rule="missing",
                    breakout_rule="missing",
                    breakout_volume_rule="missing",
                    pullback_support_rule="missing",
                    pullback_volume_rule="missing",
                    pullback_freshness_rule="missing",
                    no_chase_rule="missing",
                    reason="below_watch_band",
                    risk_flags=("market_cap_below_watch_band",),
                ),
            ),
            total_universe_count=4,
            eligible_universe_count=3,
        )

        rendered = format_daily_scan_text_summary(
            result,
            self.config,
            technical_snapshot_row_count=3,
            csv_output_path="/tmp/scan.csv",
            summary_output_path="/tmp/summary.json",
            text_output_path="/tmp/review.txt",
        )

        self.assertEqual(
            rendered,
            textwrap.dedent(
                """\
                Daily Scan Review
                Universe: total=4 | eligible=3 | skipped=1 | technical_rows=3
                Decisions: candidate=1 | watch=1 | reject=1
                Thresholds: total>=100.00 bn | watch>=80.00 bn | float>=30.00 bn | float_watch>=24.00 bn | no_chase<=5.00% | breakout_volume>=1.20x | support_touch=1.00% | pullback_volume<=1.00x | pullback_close<=2.00%
                Ranking: candidate > watch > reject | lower risk tier | higher score | more/fresher confirmed triggers | fewer risks | more liquidity

                Candidate (1)
                Top reasons: candidate_setup_confirmed_with_crossover_and_volume_backed_breakout(1)
                Top signals: breakout_volume_confirmed(1), circulating_market_cap_liquidity_passed(1), fresh_breakout_level_cleared(1)
                Top risks: none
                1. 000001 候选一号 (000001.SZ) | score=9/12 | risk_tier=0 | confirmed_triggers=volume_backed_breakout,confirmed_crossover | total_cap=120.00 bn | float_cap=60.00 bn
                   reason: candidate_setup_confirmed_with_crossover_and_volume_backed_breakout
                   signals: market_cap_candidate_band, circulating_market_cap_liquidity_passed, fresh_breakout_level_cleared, breakout_volume_confirmed
                   risks: none

                Watch (1)
                Top reasons: breakout_needs_volume_confirmation(1)
                Top signals: fresh_breakout_level_cleared(1)
                Top risks: breakout_missing_volume_confirmation(1)
                1. 000002 观察二号 (000002.SZ) | score=7/12 | risk_tier=1 | confirmed_triggers=none | total_cap=110.00 bn | float_cap=55.00 bn
                   reason: breakout_needs_volume_confirmation
                   signals: fresh_breakout_level_cleared
                   risks: breakout_missing_volume_confirmation

                Reject (1)
                Top reasons: below_watch_band(1)
                Top signals: none
                Top risks: market_cap_below_watch_band(1)
                1. 000003 剔除三号 (000003.SZ) | score=1/12 | risk_tier=4 | confirmed_triggers=none | total_cap=60.00 bn | float_cap=20.00 bn
                   reason: below_watch_band
                   signals: none
                   risks: market_cap_below_watch_band

                Outputs: csv=/tmp/scan.csv | json=/tmp/summary.json | text=/tmp/review.txt
                Mode: decision-support only
                """
            ),
        )

    def test_text_summary_limit_hides_extra_ranked_rows(self) -> None:
        result = DailyScanResult(
            records=(
                make_scan_record(
                    ts_code="000010.SZ",
                    symbol="000010",
                    name="观察十号",
                    decision="watch",
                    score=7,
                    total_market_cap_billion_cny=120.0,
                    circulating_market_cap_billion_cny=60.0,
                    market_cap_rule="candidate_band",
                    breakout_rule="pass",
                    breakout_volume_rule="missing",
                    reason="breakout_needs_volume_confirmation",
                    risk_flags=("breakout_missing_volume_confirmation",),
                ),
                make_scan_record(
                    ts_code="000011.SZ",
                    symbol="000011",
                    name="观察十一号",
                    decision="watch",
                    score=6,
                    total_market_cap_billion_cny=118.0,
                    circulating_market_cap_billion_cny=58.0,
                    market_cap_rule="candidate_band",
                    breakout_rule="stale_above_breakout",
                    reason="breakout_above_level_but_not_fresh",
                    risk_flags=("breakout_trigger_not_fresh",),
                ),
            ),
            total_universe_count=2,
            eligible_universe_count=2,
        )

        rendered = format_daily_scan_text_summary(
            result,
            self.config,
            limit_per_decision=1,
        )

        self.assertIn(
            "... 1 more ranked watch rows not shown; set limit_per_decision=0 to include all rows",
            rendered,
        )
        self.assertIn("000010 观察十号", rendered)
        self.assertNotIn("000011 观察十一号", rendered)

    def test_text_summary_rejects_negative_limit(self) -> None:
        result = DailyScanResult(records=(), total_universe_count=0, eligible_universe_count=0)

        with self.assertRaisesRegex(ValueError, "limit_per_decision must be non-negative"):
            format_daily_scan_text_summary(
                result,
                self.config,
                limit_per_decision=-1,
            )


if __name__ == "__main__":
    unittest.main()
