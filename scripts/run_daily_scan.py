#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.market_cap import load_market_cap_snapshot
from src.scanner import (
    SCAN_RESULT_FIELDNAMES,
    DECISION_SEQUENCE,
    RuleBasedScanConfig,
    RuleBasedScanner,
)
from src.technical import load_technical_snapshot
from src.universe import load_universe_records

DEFAULT_UNIVERSE_INPUT = REPO_ROOT / "data" / "derived" / "universe_cn.csv"
DEFAULT_MARKET_CAP_INPUT = REPO_ROOT / "data" / "raw" / "market_cap_snapshot_cn.csv"
DEFAULT_TECHNICAL_INPUT = REPO_ROOT / "data" / "raw" / "technical_snapshot_cn.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "derived" / "daily_scan_cn.csv"
DEFAULT_SUMMARY_OUTPUT = REPO_ROOT / "data" / "derived" / "daily_scan_summary_cn.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the daily rule-based scan using the built universe, market-cap snapshot, and technical snapshot.",
        epilog="This command is decision-support only. It never places orders or automates trades.",
    )
    parser.add_argument(
        "--universe-input",
        type=Path,
        default=DEFAULT_UNIVERSE_INPUT,
        help=f"Universe CSV input path. Default: {DEFAULT_UNIVERSE_INPUT}",
    )
    parser.add_argument(
        "--market-cap-input",
        type=Path,
        default=DEFAULT_MARKET_CAP_INPUT,
        help=f"Market-cap snapshot CSV input path. Default: {DEFAULT_MARKET_CAP_INPUT}",
    )
    parser.add_argument(
        "--technical-input",
        type=Path,
        default=DEFAULT_TECHNICAL_INPUT,
        help=f"Technical snapshot CSV input path. Default: {DEFAULT_TECHNICAL_INPUT}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Scan result CSV output path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Scan summary JSON output path. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )
    parser.add_argument(
        "--min-total-market-cap-bn",
        type=float,
        default=100.0,
        help="Candidate threshold in billion CNY. Default: 100.0",
    )
    parser.add_argument(
        "--watch-buffer-ratio",
        type=float,
        default=0.2,
        help=(
            "Percentage band below the candidate threshold that becomes watch "
            "instead of reject. Default: 0.2"
        ),
    )
    parser.add_argument(
        "--max-close-above-sma20-ratio",
        type=float,
        default=0.05,
        help=(
            "Maximum allowed close premium above SMA20 before the no-chase guard "
            "downgrades the setup to watch. Default: 0.05"
        ),
    )
    parser.add_argument(
        "--min-breakout-volume-ratio",
        type=float,
        default=1.2,
        help=(
            "Minimum volume_ratio_20d needed before a breakout can qualify as an "
            "entry trigger. Default: 1.2"
        ),
    )
    parser.add_argument(
        "--support-touch-tolerance-ratio",
        type=float,
        default=0.01,
        help=(
            "Maximum distance around SMA20 that still counts as an explicit support "
            "retest for pullback rules. Default: 0.01"
        ),
    )
    parser.add_argument(
        "--max-pullback-volume-ratio",
        type=float,
        default=1.0,
        help=(
            "Maximum volume_ratio_20d allowed when a supported pullback is used as "
            "the entry trigger. Default: 1.0"
        ),
    )
    return parser.parse_args()


def write_scan_csv(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCAN_RESULT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _format_market_cap(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} bn"


def main() -> int:
    args = parse_args()
    universe_records = load_universe_records(args.universe_input)
    market_cap_records = load_market_cap_snapshot(args.market_cap_input)
    technical_records = load_technical_snapshot(args.technical_input)

    config = RuleBasedScanConfig(
        min_total_market_cap_billion_cny=args.min_total_market_cap_bn,
        watch_buffer_ratio=args.watch_buffer_ratio,
        max_close_above_sma20_ratio=args.max_close_above_sma20_ratio,
        min_breakout_volume_ratio=args.min_breakout_volume_ratio,
        support_touch_tolerance_ratio=args.support_touch_tolerance_ratio,
        max_pullback_volume_ratio=args.max_pullback_volume_ratio,
    )
    result = RuleBasedScanner(config).scan(
        universe_records=universe_records,
        market_cap_records=market_cap_records,
        technical_records=technical_records,
    )

    write_scan_csv(
        args.output,
        [record.to_row() for record in result.records],
    )
    write_json(
        args.summary_output,
        {
            **result.to_summary(config),
            "universe_input_path": str(args.universe_input),
            "market_cap_input_path": str(args.market_cap_input),
            "technical_input_path": str(args.technical_input),
            "output_path": str(args.output),
            "decision_support_only": True,
        },
    )

    print(f"total universe rows: {result.total_universe_count}")
    print(f"eligible universe rows scanned: {result.eligible_universe_count}")
    print(f"technical snapshot rows loaded: {len(technical_records)}")
    print(
        "thresholds:"
        f" candidate>={config.min_total_market_cap_billion_cny:.2f} bn,"
        f" watch>={config.watch_floor_billion_cny:.2f} bn,"
        f" max_close_above_sma20={config.max_close_above_sma20_ratio:.2%},"
        f" breakout_volume>={config.min_breakout_volume_ratio:.2f}x,"
        f" support_touch_tolerance={config.support_touch_tolerance_ratio:.2%},"
        f" pullback_volume<={config.max_pullback_volume_ratio:.2f}x"
    )
    print(
        "score model: market_cap_candidate_band=2, market_cap_watch_band=1, "
        "close>=SMA20=1, SMA20>=SMA60=1, confirmed_SMA20_cross=1, "
        "breakout_confirmation=1, breakout_volume_confirmation=1, "
        "supported_pullback_confirmation=1, pullback_volume_contraction=1, "
        "no_chase_guard=1"
    )
    print(f"scan output: {args.output}")
    print(f"summary output: {args.summary_output}")
    print("mode: decision-support only")

    for decision in DECISION_SEQUENCE:
        matching = [record for record in result.records if record.decision == decision]
        print(f"{decision}: {len(matching)}")
        for record in matching:
            print(
                "  - "
                f"{record.symbol} {record.name} | "
                f"score={record.score}/{record.max_score} | "
                f"total_cap={_format_market_cap(record.total_market_cap_billion_cny)} | "
                f"market_cap_rule={record.market_cap_rule} | "
                f"close_vs_sma20={record.close_vs_sma20_rule} | "
                f"sma20_vs_sma60={record.sma20_vs_sma60_rule} | "
                f"sma20_crossover={record.sma20_crossover_rule} | "
                f"breakout={record.breakout_rule} | "
                f"breakout_volume={record.breakout_volume_rule} | "
                f"pullback_support={record.pullback_support_rule} | "
                f"pullback_volume={record.pullback_volume_rule} | "
                f"no_chase={record.no_chase_rule} | "
                f"reason={record.reason} | "
                f"signals={','.join(record.signal_reasons) or 'none'} | "
                f"risks={','.join(record.risk_flags) or 'none'}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
