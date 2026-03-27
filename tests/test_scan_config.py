from __future__ import annotations

import argparse
import unittest

from src.scanner import (
    DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION,
    RuleBasedScanConfig,
    add_rule_based_scan_arguments,
    add_text_summary_arguments,
    build_scan_config_from_args,
)


class RuleBasedScanConfigTests(unittest.TestCase):
    def test_parser_helpers_share_default_config(self) -> None:
        parser = argparse.ArgumentParser(add_help=False)
        add_rule_based_scan_arguments(parser)
        add_text_summary_arguments(parser, output_help="Optional text output.")

        args = parser.parse_args([])

        self.assertEqual(build_scan_config_from_args(args), RuleBasedScanConfig())
        self.assertEqual(
            args.text_summary_limit_per_decision,
            DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION,
        )

    def test_summary_thresholds_keep_derived_watch_floors_explicit(self) -> None:
        config = RuleBasedScanConfig(
            min_total_market_cap_billion_cny=150.0,
            min_circulating_market_cap_billion_cny=40.0,
            watch_buffer_ratio=0.25,
            max_close_above_sma20_ratio=0.04,
            min_breakout_volume_ratio=1.5,
            support_touch_tolerance_ratio=0.02,
            max_pullback_volume_ratio=0.9,
            max_pullback_close_above_sma20_ratio=0.03,
        )

        self.assertEqual(
            config.summary_thresholds(),
            {
                "candidate_min_total_market_cap_billion_cny": 150.0,
                "watch_floor_total_market_cap_billion_cny": 112.5,
                "candidate_min_circulating_market_cap_billion_cny": 40.0,
                "watch_floor_circulating_market_cap_billion_cny": 30.0,
                "watch_buffer_ratio": 0.25,
                "max_close_above_sma20_ratio": 0.04,
                "min_breakout_volume_ratio": 1.5,
                "support_touch_tolerance_ratio": 0.02,
                "max_pullback_volume_ratio": 0.9,
                "max_pullback_close_above_sma20_ratio": 0.03,
            },
        )


if __name__ == "__main__":
    unittest.main()
