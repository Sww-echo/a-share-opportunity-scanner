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
    RuleBasedScanner,
    add_rule_based_scan_arguments,
    add_text_summary_arguments,
    build_scan_config_from_args,
    format_daily_scan_text_summary,
    validate_text_summary_limit,
)
from src.technical import load_technical_snapshot
from src.universe import load_universe_records

DEFAULT_UNIVERSE_INPUT = REPO_ROOT / "data" / "derived" / "universe_cn.csv"
DEFAULT_MARKET_CAP_INPUT = REPO_ROOT / "data" / "raw" / "market_cap_snapshot_cn.csv"
DEFAULT_TECHNICAL_INPUT = REPO_ROOT / "data" / "raw" / "technical_snapshot_cn.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "derived" / "daily_scan_cn.csv"
DEFAULT_SUMMARY_OUTPUT = REPO_ROOT / "data" / "derived" / "daily_scan_summary_cn.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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
    add_text_summary_arguments(
        parser,
        output_help="Optional human-readable text review output path.",
    )
    add_rule_based_scan_arguments(parser)
    args = parser.parse_args(argv)
    validate_text_summary_limit(parser, args)
    return args


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


def main() -> int:
    args = parse_args()
    universe_records = load_universe_records(args.universe_input)
    market_cap_records = load_market_cap_snapshot(args.market_cap_input)
    technical_records = load_technical_snapshot(args.technical_input)

    config = build_scan_config_from_args(args)
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

    text_summary = format_daily_scan_text_summary(
        result,
        config,
        technical_snapshot_row_count=len(technical_records),
        csv_output_path=str(args.output),
        summary_output_path=str(args.summary_output),
        text_output_path=(
            str(args.text_summary_output) if args.text_summary_output is not None else None
        ),
        limit_per_decision=args.text_summary_limit_per_decision,
    )
    if args.text_summary_output is not None:
        args.text_summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.text_summary_output.write_text(text_summary, encoding="utf-8")
    print(text_summary, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
