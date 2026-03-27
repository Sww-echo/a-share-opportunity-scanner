#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.data_provider import load_stock_list
from src.universe import (
    AShareUniverseBuilder,
    StockIndexBuilder,
    UniverseBuildConfig,
    write_universe_records,
)

DEFAULT_INPUT = REPO_ROOT / "data" / "raw" / "stock_list_cn.csv"
DEFAULT_UNIVERSE_OUTPUT = REPO_ROOT / "data" / "derived" / "universe_cn.csv"
DEFAULT_INDEX_OUTPUT = REPO_ROOT / "data" / "derived" / "stock_index_cn.json"
DEFAULT_SUMMARY_OUTPUT = REPO_ROOT / "data" / "derived" / "universe_summary_cn.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the first usable A-share universe and static stock index.",
        epilog="This command prepares lookup data for scanning. It does not place or automate trades.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Normalized stock-list CSV path. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--universe-output",
        type=Path,
        default=DEFAULT_UNIVERSE_OUTPUT,
        help=f"Universe CSV output path. Default: {DEFAULT_UNIVERSE_OUTPUT}",
    )
    parser.add_argument(
        "--index-output",
        type=Path,
        default=DEFAULT_INDEX_OUTPUT,
        help=f"Stock index JSON output path. Default: {DEFAULT_INDEX_OUTPUT}",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Universe summary JSON output path. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )
    parser.add_argument(
        "--include-st",
        action="store_true",
        help="Keep ST stocks in the eligible universe.",
    )
    return parser.parse_args()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    stock_list = load_stock_list(args.input)

    universe_builder = AShareUniverseBuilder(
        UniverseBuildConfig(exclude_st=not args.include_st)
    )
    universe_result = universe_builder.build(stock_list)
    index_records = StockIndexBuilder().build(universe_result.eligible_records)

    write_universe_records(
        args.universe_output,
        universe_result.records,
    )
    write_json(
        args.index_output,
        [record.to_dict() for record in index_records],
    )
    write_json(
        args.summary_output,
        {
            **universe_result.to_summary(),
            "source_path": str(args.input),
            "universe_output_path": str(args.universe_output),
            "index_output_path": str(args.index_output),
            "decision_support_only": True,
        },
    )

    print(f"loaded stock list: {len(stock_list)} records")
    print(f"eligible universe size: {universe_result.eligible_count}")
    print(f"index size: {len(index_records)}")
    print(f"universe output: {args.universe_output}")
    print(f"index output: {args.index_output}")
    print(f"summary output: {args.summary_output}")
    print("mode: decision-support only")

    if universe_result.excluded_by_reason:
        print("excluded by reason:")
        for reason, count in sorted(universe_result.excluded_by_reason.items()):
            print(f"  - {reason}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
