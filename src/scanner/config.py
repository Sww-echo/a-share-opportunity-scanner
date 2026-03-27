from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION = 5


@dataclass(frozen=True, slots=True)
class RuleBasedScanConfig:
    min_total_market_cap_billion_cny: float = 100.0
    min_circulating_market_cap_billion_cny: float = 30.0
    watch_buffer_ratio: float = 0.2
    max_close_above_sma20_ratio: float = 0.05
    min_breakout_volume_ratio: float = 1.2
    support_touch_tolerance_ratio: float = 0.01
    max_pullback_volume_ratio: float = 1.0
    max_pullback_close_above_sma20_ratio: float = 0.02

    def __post_init__(self) -> None:
        if self.min_total_market_cap_billion_cny <= 0:
            raise ValueError("min_total_market_cap_billion_cny must be positive")
        if self.min_circulating_market_cap_billion_cny <= 0:
            raise ValueError("min_circulating_market_cap_billion_cny must be positive")
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
        if self.max_pullback_close_above_sma20_ratio < 0:
            raise ValueError("max_pullback_close_above_sma20_ratio must be non-negative")

    @property
    def watch_floor_billion_cny(self) -> float:
        return self.min_total_market_cap_billion_cny * (1 - self.watch_buffer_ratio)

    @property
    def circulating_market_cap_watch_floor_billion_cny(self) -> float:
        return self.min_circulating_market_cap_billion_cny * (
            1 - self.watch_buffer_ratio
        )

    @property
    def max_score(self) -> int:
        return 12

    def summary_thresholds(self) -> dict[str, float]:
        return {
            "candidate_min_total_market_cap_billion_cny": (
                self.min_total_market_cap_billion_cny
            ),
            "watch_floor_total_market_cap_billion_cny": self.watch_floor_billion_cny,
            "candidate_min_circulating_market_cap_billion_cny": (
                self.min_circulating_market_cap_billion_cny
            ),
            "watch_floor_circulating_market_cap_billion_cny": (
                self.circulating_market_cap_watch_floor_billion_cny
            ),
            "watch_buffer_ratio": self.watch_buffer_ratio,
            "max_close_above_sma20_ratio": self.max_close_above_sma20_ratio,
            "min_breakout_volume_ratio": self.min_breakout_volume_ratio,
            "support_touch_tolerance_ratio": self.support_touch_tolerance_ratio,
            "max_pullback_volume_ratio": self.max_pullback_volume_ratio,
            "max_pullback_close_above_sma20_ratio": (
                self.max_pullback_close_above_sma20_ratio
            ),
        }

    def threshold_summary_parts(self) -> tuple[str, ...]:
        return (
            f"total>={self.min_total_market_cap_billion_cny:.2f} bn",
            f"watch>={self.watch_floor_billion_cny:.2f} bn",
            f"float>={self.min_circulating_market_cap_billion_cny:.2f} bn",
            (
                "float_watch>="
                f"{self.circulating_market_cap_watch_floor_billion_cny:.2f} bn"
            ),
            f"no_chase<={self.max_close_above_sma20_ratio:.2%}",
            f"breakout_volume>={self.min_breakout_volume_ratio:.2f}x",
            f"support_touch={self.support_touch_tolerance_ratio:.2%}",
            f"pullback_volume<={self.max_pullback_volume_ratio:.2f}x",
            f"pullback_close<={self.max_pullback_close_above_sma20_ratio:.2%}",
        )


MarketCapScanConfig = RuleBasedScanConfig

_DEFAULT_SCAN_CONFIG = RuleBasedScanConfig()


def add_rule_based_scan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--min-total-market-cap-bn",
        type=float,
        default=_DEFAULT_SCAN_CONFIG.min_total_market_cap_billion_cny,
        help=(
            "Candidate threshold in billion CNY. Default: "
            f"{_DEFAULT_SCAN_CONFIG.min_total_market_cap_billion_cny}"
        ),
    )
    parser.add_argument(
        "--watch-buffer-ratio",
        type=float,
        default=_DEFAULT_SCAN_CONFIG.watch_buffer_ratio,
        help=(
            "Percentage band below the candidate threshold that becomes watch "
            "instead of reject. Default: "
            f"{_DEFAULT_SCAN_CONFIG.watch_buffer_ratio}"
        ),
    )
    parser.add_argument(
        "--min-circulating-market-cap-bn",
        type=float,
        default=_DEFAULT_SCAN_CONFIG.min_circulating_market_cap_billion_cny,
        help=(
            "Circulating market-cap liquidity floor in billion CNY. Default: "
            f"{_DEFAULT_SCAN_CONFIG.min_circulating_market_cap_billion_cny}"
        ),
    )
    parser.add_argument(
        "--max-close-above-sma20-ratio",
        type=float,
        default=_DEFAULT_SCAN_CONFIG.max_close_above_sma20_ratio,
        help=(
            "Maximum allowed close premium above SMA20 before the no-chase guard "
            "downgrades the setup to watch. Default: "
            f"{_DEFAULT_SCAN_CONFIG.max_close_above_sma20_ratio}"
        ),
    )
    parser.add_argument(
        "--min-breakout-volume-ratio",
        type=float,
        default=_DEFAULT_SCAN_CONFIG.min_breakout_volume_ratio,
        help=(
            "Minimum volume_ratio_20d needed before a breakout can qualify as an "
            "entry trigger. Default: "
            f"{_DEFAULT_SCAN_CONFIG.min_breakout_volume_ratio}"
        ),
    )
    parser.add_argument(
        "--support-touch-tolerance-ratio",
        type=float,
        default=_DEFAULT_SCAN_CONFIG.support_touch_tolerance_ratio,
        help=(
            "Maximum distance around SMA20 that still counts as an explicit support "
            "retest for pullback rules. Default: "
            f"{_DEFAULT_SCAN_CONFIG.support_touch_tolerance_ratio}"
        ),
    )
    parser.add_argument(
        "--max-pullback-volume-ratio",
        type=float,
        default=_DEFAULT_SCAN_CONFIG.max_pullback_volume_ratio,
        help=(
            "Maximum volume_ratio_20d allowed when a supported pullback is used as "
            "the entry trigger. Default: "
            f"{_DEFAULT_SCAN_CONFIG.max_pullback_volume_ratio}"
        ),
    )
    parser.add_argument(
        "--max-pullback-close-above-sma20-ratio",
        type=float,
        default=_DEFAULT_SCAN_CONFIG.max_pullback_close_above_sma20_ratio,
        help=(
            "Maximum allowed close premium above SMA20 when a supported pullback is "
            "used as the entry trigger. Default: "
            f"{_DEFAULT_SCAN_CONFIG.max_pullback_close_above_sma20_ratio}"
        ),
    )


def build_scan_config_from_args(args: argparse.Namespace) -> RuleBasedScanConfig:
    return RuleBasedScanConfig(
        min_total_market_cap_billion_cny=args.min_total_market_cap_bn,
        min_circulating_market_cap_billion_cny=args.min_circulating_market_cap_bn,
        watch_buffer_ratio=args.watch_buffer_ratio,
        max_close_above_sma20_ratio=args.max_close_above_sma20_ratio,
        min_breakout_volume_ratio=args.min_breakout_volume_ratio,
        support_touch_tolerance_ratio=args.support_touch_tolerance_ratio,
        max_pullback_volume_ratio=args.max_pullback_volume_ratio,
        max_pullback_close_above_sma20_ratio=(
            args.max_pullback_close_above_sma20_ratio
        ),
    )


def add_text_summary_arguments(
    parser: argparse.ArgumentParser,
    *,
    output_help: str,
) -> None:
    parser.add_argument(
        "--text-summary-output",
        type=Path,
        help=output_help,
    )
    parser.add_argument(
        "--text-summary-limit-per-decision",
        type=int,
        default=DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION,
        help=(
            "How many ranked rows to show per decision bucket in the text review. "
            "Use 0 to show all rows. "
            f"Default: {DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION}"
        ),
    )


def validate_text_summary_limit(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    if args.text_summary_limit_per_decision < 0:
        parser.error("--text-summary-limit-per-decision must be >= 0")
