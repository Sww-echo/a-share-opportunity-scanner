from __future__ import annotations

import unittest

from src.market_cap import MarketCapSnapshotRecord
from src.scanner import RuleBasedScanConfig, RuleBasedScanner
from src.technical import TechnicalSnapshotRecord
from src.universe import UniverseRecord

_USE_DEFAULT_CIRCULATING = object()


def make_universe_record(
    *,
    ts_code: str = "000001.SZ",
    symbol: str = "000001",
    name: str = "示例股份",
) -> UniverseRecord:
    return UniverseRecord(
        ts_code=ts_code,
        symbol=symbol,
        name=name,
        exchange="SZSE",
        board="主板",
        list_status="L",
        list_date="20200101",
        area="深圳",
        industry="示例",
        is_hs="N",
        is_st=False,
        eligible=True,
        exclude_reason=None,
    )


def make_market_cap_snapshot(
    *,
    ts_code: str = "000001.SZ",
    total_market_cap_billion_cny: float = 120.0,
    circulating_market_cap_billion_cny: float | None | object = _USE_DEFAULT_CIRCULATING,
) -> MarketCapSnapshotRecord:
    return MarketCapSnapshotRecord(
        ts_code=ts_code,
        total_market_cap_billion_cny=total_market_cap_billion_cny,
        circulating_market_cap_billion_cny=(
            total_market_cap_billion_cny * 0.9
            if circulating_market_cap_billion_cny is _USE_DEFAULT_CIRCULATING
            else circulating_market_cap_billion_cny
        ),
    )


def make_technical_snapshot(
    *,
    ts_code: str = "000001.SZ",
    close_price_cny: float | None = 10.20,
    prev_close_price_cny: float | None = 10.00,
    low_price_cny: float | None = 10.08,
    sma20_cny: float | None = 10.00,
    sma60_cny: float | None = 9.80,
    prev_sma20_cny: float | None = 9.60,
    prev_sma60_cny: float | None = 9.90,
    breakout_level_cny: float | None = 10.10,
    volume_ratio_20d: float | None = 1.30,
) -> TechnicalSnapshotRecord:
    return TechnicalSnapshotRecord(
        ts_code=ts_code,
        close_price_cny=close_price_cny,
        prev_close_price_cny=prev_close_price_cny,
        low_price_cny=low_price_cny,
        sma20_cny=sma20_cny,
        sma60_cny=sma60_cny,
        prev_sma20_cny=prev_sma20_cny,
        prev_sma60_cny=prev_sma60_cny,
        breakout_level_cny=breakout_level_cny,
        volume_ratio_20d=volume_ratio_20d,
    )


class RuleBasedScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scanner = RuleBasedScanner(
            RuleBasedScanConfig(
                min_total_market_cap_billion_cny=100.0,
                min_circulating_market_cap_billion_cny=30.0,
                watch_buffer_ratio=0.2,
                max_close_above_sma20_ratio=0.05,
                min_breakout_volume_ratio=1.2,
                support_touch_tolerance_ratio=0.01,
                max_pullback_volume_ratio=1.0,
                max_pullback_close_above_sma20_ratio=0.02,
            )
        )
        self.universe_records = [make_universe_record()]

    def test_candidate_requires_trend_trigger_and_no_chase_guard(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[make_technical_snapshot()],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "candidate")
        self.assertEqual(record.score, 9)
        self.assertEqual(record.market_cap_rule, "candidate_band")
        self.assertEqual(record.circulating_market_cap_rule, "pass")
        self.assertEqual(record.close_vs_sma20_rule, "pass")
        self.assertEqual(record.sma20_vs_sma60_rule, "pass")
        self.assertEqual(record.sma20_crossover_rule, "confirmed_bullish_cross")
        self.assertEqual(record.breakout_rule, "pass")
        self.assertEqual(record.breakout_volume_rule, "pass")
        self.assertEqual(
            record.pullback_support_rule, "support_retested_without_pullback_day"
        )
        self.assertEqual(record.pullback_volume_rule, "not_applicable")
        self.assertEqual(record.pullback_freshness_rule, "not_applicable")
        self.assertEqual(record.no_chase_rule, "pass")
        self.assertEqual(
            record.reason,
            "candidate_setup_confirmed_with_crossover_and_volume_backed_breakout",
        )
        self.assertIn("market_cap_candidate_band", record.signal_reasons)
        self.assertIn(
            "circulating_market_cap_liquidity_passed",
            record.signal_reasons,
        )
        self.assertEqual(record.risk_flags, ())

    def test_breakout_can_confirm_candidate_without_fresh_crossover_when_volume_confirms(
        self,
    ) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    prev_sma20_cny=9.90,
                    prev_sma60_cny=9.40,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "candidate")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.sma20_crossover_rule, "already_above")
        self.assertEqual(record.breakout_rule, "pass")
        self.assertEqual(record.breakout_volume_rule, "pass")
        self.assertEqual(
            record.reason,
            "candidate_setup_confirmed_with_volume_backed_breakout",
        )

    def test_crossover_must_finish_above_sma60_to_count_as_fresh_trigger(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    sma20_cny=9.80,
                    sma60_cny=9.80,
                    prev_sma20_cny=9.60,
                    prev_sma60_cny=9.90,
                    breakout_level_cny=10.30,
                    low_price_cny=10.05,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 6)
        self.assertEqual(record.sma20_vs_sma60_rule, "pass")
        self.assertEqual(record.sma20_crossover_rule, "touching_sma60")
        self.assertEqual(
            record.reason,
            "crossover_touching_sma60_needs_clear_break",
        )
        self.assertIn("crossover_touching_sma60", record.risk_flags)

    def test_flat_prior_cross_can_still_confirm_when_sma20_clears_above_sma60(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    prev_sma20_cny=9.80,
                    prev_sma60_cny=9.80,
                    breakout_level_cny=10.30,
                    low_price_cny=10.05,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "candidate")
        self.assertEqual(record.score, 7)
        self.assertEqual(record.sma20_crossover_rule, "confirmed_bullish_cross")
        self.assertEqual(record.reason, "candidate_setup_confirmed_with_crossover")

    def test_crossover_needs_price_confirmation_on_the_trigger_day(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.20,
                    prev_close_price_cny=10.28,
                    low_price_cny=10.12,
                    prev_sma20_cny=9.80,
                    prev_sma60_cny=9.90,
                    breakout_level_cny=10.40,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 6)
        self.assertEqual(
            record.sma20_crossover_rule,
            "crossed_but_close_not_above_prev_close",
        )
        self.assertEqual(record.reason, "crossover_needs_price_confirmation")
        self.assertIn("crossover_price_confirmation_failed", record.risk_flags)

    def test_crossover_price_confirmation_context_must_be_present(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    prev_close_price_cny=None,
                    low_price_cny=10.12,
                    prev_sma20_cny=9.80,
                    prev_sma60_cny=9.90,
                    breakout_level_cny=10.40,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 6)
        self.assertEqual(
            record.sma20_crossover_rule,
            "missing_price_confirmation_context",
        )
        self.assertEqual(record.reason, "crossover_price_confirmation_incomplete")
        self.assertIn("missing_crossover_price_confirmation", record.risk_flags)

    def test_supported_pullback_can_confirm_candidate_without_breakout_or_crossover(
        self,
    ) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.02,
                    prev_close_price_cny=10.18,
                    low_price_cny=10.00,
                    prev_sma20_cny=10.20,
                    prev_sma60_cny=9.80,
                    breakout_level_cny=10.30,
                    volume_ratio_20d=0.92,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "candidate")
        self.assertEqual(record.score, 9)
        self.assertEqual(record.circulating_market_cap_rule, "pass")
        self.assertEqual(record.sma20_crossover_rule, "already_above")
        self.assertEqual(record.breakout_rule, "fail")
        self.assertEqual(record.pullback_support_rule, "confirmed_supported_pullback")
        self.assertEqual(record.pullback_volume_rule, "pass")
        self.assertEqual(record.pullback_freshness_rule, "pass")
        self.assertEqual(
            record.reason,
            "candidate_setup_confirmed_with_supported_pullback",
        )
        self.assertEqual(
            record.signal_reasons,
            (
                "market_cap_candidate_band",
                "circulating_market_cap_liquidity_passed",
                "close_at_or_above_sma20",
                "sma20_at_or_above_sma60",
                "sma20_already_above_sma60",
                "supported_pullback_at_sma20",
                "pullback_volume_contracted",
                "fresh_pullback_entry_near_sma20",
                "no_chase_guard_passed",
            ),
        )

    def test_breakout_only_setup_waits_for_volume_confirmation(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    prev_sma20_cny=9.90,
                    prev_sma60_cny=9.40,
                    volume_ratio_20d=None,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 7)
        self.assertEqual(record.sma20_crossover_rule, "already_above")
        self.assertEqual(record.breakout_rule, "pass")
        self.assertEqual(record.breakout_volume_rule, "missing")
        self.assertEqual(record.reason, "breakout_needs_volume_confirmation")
        self.assertIn("breakout_missing_volume_confirmation", record.risk_flags)

    def test_breakout_only_setup_with_weak_volume_is_downgraded_to_watch(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    prev_sma20_cny=9.90,
                    prev_sma60_cny=9.40,
                    volume_ratio_20d=1.05,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 7)
        self.assertEqual(record.breakout_rule, "pass")
        self.assertEqual(record.breakout_volume_rule, "fail")
        self.assertEqual(record.reason, "breakout_volume_confirmation_failed")
        self.assertIn("breakout_volume_below_threshold", record.risk_flags)

    def test_breakout_must_be_fresh_to_confirm_candidate(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    prev_close_price_cny=10.18,
                    prev_sma20_cny=9.90,
                    prev_sma60_cny=9.40,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 6)
        self.assertEqual(record.breakout_rule, "stale_above_breakout")
        self.assertEqual(record.breakout_volume_rule, "not_applicable")
        self.assertEqual(record.reason, "breakout_above_level_but_not_fresh")
        self.assertIn("price_still_above_breakout_level", record.signal_reasons)
        self.assertIn("breakout_trigger_not_fresh", record.risk_flags)

    def test_failed_breakout_is_explicitly_downgraded(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.05,
                    prev_close_price_cny=10.20,
                    low_price_cny=9.95,
                    sma20_cny=9.80,
                    sma60_cny=9.50,
                    prev_sma20_cny=9.90,
                    prev_sma60_cny=9.40,
                    breakout_level_cny=10.10,
                    volume_ratio_20d=1.30,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 6)
        self.assertEqual(record.breakout_rule, "failed_breakout")
        self.assertEqual(record.breakout_volume_rule, "not_applicable")
        self.assertEqual(record.reason, "breakout_failed_back_below_level")
        self.assertIn("breakout_failed_back_below_level", record.risk_flags)

    def test_failed_breakout_recovery_stays_watch_even_when_pullback_quality_is_good(
        self,
    ) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.02,
                    prev_close_price_cny=10.18,
                    low_price_cny=10.00,
                    sma20_cny=10.00,
                    sma60_cny=9.80,
                    prev_sma20_cny=10.20,
                    prev_sma60_cny=9.80,
                    breakout_level_cny=10.10,
                    volume_ratio_20d=0.92,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 9)
        self.assertEqual(record.breakout_rule, "failed_breakout")
        self.assertEqual(record.pullback_support_rule, "confirmed_supported_pullback")
        self.assertEqual(record.pullback_volume_rule, "pass")
        self.assertEqual(record.pullback_freshness_rule, "pass")
        self.assertEqual(
            record.reason,
            "failed_breakout_recovered_at_sma20_support",
        )
        self.assertIn(
            "failed_breakout_recovered_at_sma20_support",
            record.signal_reasons,
        )
        self.assertIn("breakout_failed_back_below_level", record.risk_flags)
        self.assertIn("breakout_failure_requires_reset", record.risk_flags)

    def test_supported_pullback_needs_volume_contraction_context(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.02,
                    prev_close_price_cny=10.18,
                    low_price_cny=10.00,
                    prev_sma20_cny=10.20,
                    prev_sma60_cny=9.80,
                    breakout_level_cny=10.30,
                    volume_ratio_20d=None,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.pullback_support_rule, "confirmed_supported_pullback")
        self.assertEqual(record.pullback_volume_rule, "missing")
        self.assertEqual(record.pullback_freshness_rule, "pass")
        self.assertEqual(
            record.reason,
            "pullback_needs_volume_contraction_context",
        )
        self.assertIn("pullback_missing_volume_contraction", record.risk_flags)

    def test_supported_pullback_with_heavy_volume_is_downgraded(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.02,
                    prev_close_price_cny=10.18,
                    low_price_cny=10.00,
                    prev_sma20_cny=10.20,
                    prev_sma60_cny=9.80,
                    breakout_level_cny=10.30,
                    volume_ratio_20d=1.15,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.pullback_support_rule, "confirmed_supported_pullback")
        self.assertEqual(record.pullback_volume_rule, "fail")
        self.assertEqual(record.pullback_freshness_rule, "pass")
        self.assertEqual(record.reason, "pullback_volume_pressure_risk")
        self.assertIn("pullback_volume_above_threshold", record.risk_flags)

    def test_supported_pullback_must_still_be_fresh_to_confirm_candidate(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.24,
                    prev_close_price_cny=10.30,
                    low_price_cny=10.00,
                    prev_sma20_cny=10.20,
                    prev_sma60_cny=9.80,
                    breakout_level_cny=10.40,
                    volume_ratio_20d=0.92,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.pullback_support_rule, "confirmed_supported_pullback")
        self.assertEqual(record.pullback_volume_rule, "pass")
        self.assertEqual(
            record.pullback_freshness_rule,
            "rebounded_too_far_above_sma20",
        )
        self.assertEqual(record.reason, "pullback_rebounded_too_far_from_sma20")
        self.assertIn("pullback_trigger_not_fresh", record.risk_flags)

    def test_intraday_undercut_of_sma20_support_is_explicitly_downgraded(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.05,
                    prev_close_price_cny=10.18,
                    low_price_cny=9.85,
                    prev_sma20_cny=10.20,
                    prev_sma60_cny=9.80,
                    breakout_level_cny=10.30,
                    volume_ratio_20d=0.94,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 6)
        self.assertEqual(record.pullback_support_rule, "undercut_sma20_support")
        self.assertEqual(record.reason, "pullback_undercut_sma20_support")
        self.assertIn("pullback_undercut_sma20_support", record.risk_flags)

    def test_confirmed_crossover_can_still_be_candidate_without_breakout_volume(
        self,
    ) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    volume_ratio_20d=None,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "candidate")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.sma20_crossover_rule, "confirmed_bullish_cross")
        self.assertEqual(record.breakout_rule, "pass")
        self.assertEqual(record.breakout_volume_rule, "missing")
        self.assertEqual(record.reason, "candidate_setup_confirmed_with_crossover")

    def test_old_minimal_technical_snapshot_now_stays_watch_until_trigger_arrives(
        self,
    ) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.40,
                    prev_close_price_cny=None,
                    low_price_cny=None,
                    prev_sma20_cny=None,
                    prev_sma60_cny=None,
                    breakout_level_cny=None,
                    volume_ratio_20d=None,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 6)
        self.assertEqual(record.sma20_crossover_rule, "missing")
        self.assertEqual(record.breakout_rule, "missing")
        self.assertEqual(record.breakout_volume_rule, "not_applicable")
        self.assertEqual(record.pullback_support_rule, "missing")
        self.assertEqual(record.pullback_volume_rule, "not_applicable")
        self.assertEqual(record.pullback_freshness_rule, "not_applicable")
        self.assertEqual(record.no_chase_rule, "pass")
        self.assertEqual(
            record.reason,
            "waiting_for_crossover_breakout_or_supported_pullback",
        )
        self.assertIn("missing_pullback_context", record.risk_flags)

    def test_overextended_setup_is_downgraded_to_watch(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[
                make_technical_snapshot(
                    close_price_cny=10.80,
                    breakout_level_cny=10.40,
                )
            ],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.breakout_rule, "pass")
        self.assertEqual(record.breakout_volume_rule, "pass")
        self.assertEqual(
            record.pullback_support_rule, "support_retested_without_pullback_day"
        )
        self.assertEqual(record.no_chase_rule, "overextended")
        self.assertEqual(record.reason, "overextended_no_chase_guard")
        self.assertIn("overextended_above_sma20", record.risk_flags)

    def test_circulating_market_cap_watch_band_blocks_candidate_upgrade(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[
                make_market_cap_snapshot(circulating_market_cap_billion_cny=25.0)
            ],
            technical_records=[make_technical_snapshot()],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.market_cap_rule, "candidate_band")
        self.assertEqual(record.circulating_market_cap_rule, "watch_band")
        self.assertEqual(record.reason, "circulating_market_cap_in_watch_band")
        self.assertIn("circulating_market_cap_only_watch_band", record.risk_flags)

    def test_missing_circulating_market_cap_keeps_otherwise_good_setup_on_watch(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[
                make_market_cap_snapshot(circulating_market_cap_billion_cny=None)
            ],
            technical_records=[make_technical_snapshot()],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.market_cap_rule, "candidate_band")
        self.assertEqual(record.circulating_market_cap_rule, "missing")
        self.assertEqual(record.reason, "circulating_market_cap_incomplete")
        self.assertIn("missing_circulating_market_cap", record.risk_flags)

    def test_thin_circulating_market_cap_rejects_even_with_good_technical_shape(
        self,
    ) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[
                make_market_cap_snapshot(circulating_market_cap_billion_cny=20.0)
            ],
            technical_records=[make_technical_snapshot()],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "reject")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.market_cap_rule, "candidate_band")
        self.assertEqual(record.circulating_market_cap_rule, "below_watch_band")
        self.assertEqual(record.reason, "circulating_market_cap_below_watch_band")
        self.assertIn("circulating_market_cap_below_watch_band", record.risk_flags)

    def test_market_cap_watch_band_stays_watch_even_with_full_confirmation(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[
                make_market_cap_snapshot(total_market_cap_billion_cny=95.0)
            ],
            technical_records=[make_technical_snapshot()],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 8)
        self.assertEqual(record.market_cap_rule, "watch_band")
        self.assertEqual(record.reason, "market_cap_in_watch_band")
        self.assertIn("market_cap_only_watch_band", record.risk_flags)

    def test_below_watch_band_stays_reject_even_with_good_technical_shape(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[
                make_market_cap_snapshot(total_market_cap_billion_cny=70.0)
            ],
            technical_records=[make_technical_snapshot()],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "reject")
        self.assertEqual(record.score, 7)
        self.assertEqual(record.market_cap_rule, "below_watch_band")
        self.assertEqual(record.reason, "below_watch_band")
        self.assertIn("below_watch_band", record.risk_flags)

    def test_missing_technical_snapshot_keeps_market_cap_pass_as_watch(self) -> None:
        result = self.scanner.scan(
            universe_records=self.universe_records,
            market_cap_records=[make_market_cap_snapshot()],
            technical_records=[],
        )

        record = result.records[0]
        self.assertEqual(record.decision, "watch")
        self.assertEqual(record.score, 3)
        self.assertEqual(record.market_cap_rule, "candidate_band")
        self.assertEqual(record.circulating_market_cap_rule, "pass")
        self.assertEqual(record.close_vs_sma20_rule, "missing")
        self.assertEqual(record.sma20_vs_sma60_rule, "missing")
        self.assertEqual(record.sma20_crossover_rule, "missing")
        self.assertEqual(record.breakout_rule, "missing")
        self.assertEqual(record.breakout_volume_rule, "missing")
        self.assertEqual(record.pullback_support_rule, "missing")
        self.assertEqual(record.pullback_volume_rule, "missing")
        self.assertEqual(record.pullback_freshness_rule, "missing")
        self.assertEqual(record.no_chase_rule, "missing")
        self.assertEqual(record.reason, "trend_filter_incomplete")
        self.assertIn("technical_snapshot_missing", record.risk_flags)

    def test_scan_uses_ranking_layer_for_same_score_watch_ordering(self) -> None:
        universe_records = [
            make_universe_record(ts_code="000001.SZ", symbol="000001", name="弱量突破"),
            make_universe_record(ts_code="000002.SZ", symbol="000002", name="缺量突破"),
        ]

        result = self.scanner.scan(
            universe_records=universe_records,
            market_cap_records=[
                make_market_cap_snapshot(ts_code="000001.SZ"),
                make_market_cap_snapshot(ts_code="000002.SZ"),
            ],
            technical_records=[
                make_technical_snapshot(
                    ts_code="000001.SZ",
                    prev_sma20_cny=9.90,
                    prev_sma60_cny=9.40,
                    volume_ratio_20d=1.05,
                ),
                make_technical_snapshot(
                    ts_code="000002.SZ",
                    prev_sma20_cny=9.90,
                    prev_sma60_cny=9.40,
                    volume_ratio_20d=None,
                ),
            ],
        )

        self.assertEqual(
            [(record.ts_code, record.breakout_volume_rule) for record in result.records[:2]],
            [
                ("000002.SZ", "missing"),
                ("000001.SZ", "fail"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
