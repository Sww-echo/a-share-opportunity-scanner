#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.data_provider import create_stock_list_provider, write_stock_list
from src.market_cap import create_market_cap_snapshot_provider, write_market_cap_snapshot
from src.scanner import (
    DECISION_SEQUENCE,
    SCAN_RESULT_FIELDNAMES,
    RuleBasedScanConfig,
    RuleBasedScanner,
)
from src.technical import create_technical_snapshot_provider, write_technical_snapshot
from src.universe import (
    AShareUniverseBuilder,
    StockIndexBuilder,
    UniverseBuildConfig,
    write_universe_records,
)

DEFAULT_DATA_ROOT = REPO_ROOT / "data"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the current rule-based A-share flow end-to-end: stock list refresh, "
            "universe build, market-cap snapshot refresh, technical snapshot refresh, "
            "and daily scan."
        ),
        epilog=(
            "This command is decision-support only. It prepares files and scanner output, "
            "but never places orders or automates trades."
        ),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help=(
            "Root directory for generated raw/derived outputs. "
            f"Default: {DEFAULT_DATA_ROOT}"
        ),
    )
    parser.add_argument(
        "--stock-list-provider",
        choices=("sample", "csv"),
        default="sample",
        help="Stock-list provider for the end-to-end flow. Default: sample.",
    )
    parser.add_argument(
        "--stock-list-input",
        type=Path,
        help="Source stock-list CSV when --stock-list-provider=csv.",
    )
    parser.add_argument(
        "--market-cap-provider",
        choices=("sample", "csv"),
        default="sample",
        help="Market-cap snapshot provider for the end-to-end flow. Default: sample.",
    )
    parser.add_argument(
        "--market-cap-input",
        type=Path,
        help="Source market-cap CSV when --market-cap-provider=csv.",
    )
    parser.add_argument(
        "--technical-provider",
        choices=("sample", "csv"),
        default="sample",
        help="Technical snapshot provider for the end-to-end flow. Default: sample.",
    )
    parser.add_argument(
        "--technical-input",
        type=Path,
        help="Source technical snapshot CSV when --technical-provider=csv.",
    )
    parser.add_argument(
        "--include-st",
        action="store_true",
        help="Keep ST stocks in the eligible universe.",
    )
    parser.add_argument(
        "--min-total-market-cap-bn",
        type=float,
        default=100.0,
        help="Candidate threshold in billion CNY. Default: 100.0.",
    )
    parser.add_argument(
        "--watch-buffer-ratio",
        type=float,
        default=0.2,
        help=(
            "Percentage band below the candidate threshold that becomes watch "
            "instead of reject. Default: 0.2."
        ),
    )
    parser.add_argument(
        "--max-close-above-sma20-ratio",
        type=float,
        default=0.05,
        help=(
            "Maximum allowed close premium above SMA20 before the no-chase guard "
            "downgrades the setup to watch. Default: 0.05."
        ),
    )
    parser.add_argument(
        "--min-breakout-volume-ratio",
        type=float,
        default=1.2,
        help=(
            "Minimum volume_ratio_20d needed before a breakout can qualify as an "
            "entry trigger. Default: 1.2."
        ),
    )
    parser.add_argument(
        "--support-touch-tolerance-ratio",
        type=float,
        default=0.01,
        help=(
            "Maximum distance around SMA20 that still counts as an explicit support "
            "retest for pullback rules. Default: 0.01."
        ),
    )
    parser.add_argument(
        "--max-pullback-volume-ratio",
        type=float,
        default=1.0,
        help=(
            "Maximum volume_ratio_20d allowed when a supported pullback is used as "
            "the entry trigger. Default: 1.0."
        ),
    )

    args = parser.parse_args(argv)

    if args.stock_list_provider == "csv" and args.stock_list_input is None:
        parser.error("--stock-list-input is required when --stock-list-provider=csv")
    if args.market_cap_provider == "csv" and args.market_cap_input is None:
        parser.error("--market-cap-input is required when --market-cap-provider=csv")
    if args.technical_provider == "csv" and args.technical_input is None:
        parser.error("--technical-input is required when --technical-provider=csv")

    return args


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_scan_csv(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCAN_RESULT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)


def raw_output(data_root: Path, filename: str) -> Path:
    return data_root / "raw" / filename


def derived_output(data_root: Path, filename: str) -> Path:
    return data_root / "derived" / filename


def metadata_output(csv_path: Path) -> Path:
    return csv_path.with_suffix(".meta.json")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    data_root = args.data_root

    stock_list_output = raw_output(data_root, "stock_list_cn.csv")
    stock_list_metadata_output = metadata_output(stock_list_output)
    market_cap_output = raw_output(data_root, "market_cap_snapshot_cn.csv")
    market_cap_metadata_output = metadata_output(market_cap_output)
    technical_output = raw_output(data_root, "technical_snapshot_cn.csv")
    technical_metadata_output = metadata_output(technical_output)
    universe_output = derived_output(data_root, "universe_cn.csv")
    index_output = derived_output(data_root, "stock_index_cn.json")
    universe_summary_output = derived_output(data_root, "universe_summary_cn.json")
    scan_output = derived_output(data_root, "daily_scan_cn.csv")
    scan_summary_output = derived_output(data_root, "daily_scan_summary_cn.json")

    stock_list_provider = create_stock_list_provider(
        args.stock_list_provider,
        source_path=args.stock_list_input,
    )
    stock_list_records = stock_list_provider.fetch_stock_list()
    write_stock_list(stock_list_output, stock_list_records)
    write_json(
        stock_list_metadata_output,
        {
            "provider": stock_list_provider.provider_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(stock_list_records),
            "output_path": str(stock_list_output),
            "decision_support_only": True,
        },
    )

    universe_builder = AShareUniverseBuilder(
        UniverseBuildConfig(exclude_st=not args.include_st)
    )
    universe_result = universe_builder.build(stock_list_records)
    index_records = StockIndexBuilder().build(universe_result.eligible_records)
    write_universe_records(universe_output, universe_result.records)
    write_json(index_output, [record.to_dict() for record in index_records])
    write_json(
        universe_summary_output,
        {
            **universe_result.to_summary(),
            "source_path": str(stock_list_output),
            "universe_output_path": str(universe_output),
            "index_output_path": str(index_output),
            "decision_support_only": True,
        },
    )

    market_cap_provider = create_market_cap_snapshot_provider(
        args.market_cap_provider,
        source_path=args.market_cap_input,
    )
    market_cap_records = market_cap_provider.fetch_snapshot()
    write_market_cap_snapshot(market_cap_output, market_cap_records)
    write_json(
        market_cap_metadata_output,
        {
            "provider": market_cap_provider.provider_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(market_cap_records),
            "as_of_dates": sorted(
                {record.as_of_date for record in market_cap_records if record.as_of_date}
            ),
            "normalized_unit": "billion_cny",
            "output_path": str(market_cap_output),
            "decision_support_only": True,
        },
    )

    technical_provider = create_technical_snapshot_provider(
        args.technical_provider,
        source_path=args.technical_input,
    )
    technical_records = technical_provider.fetch_snapshot()
    write_technical_snapshot(technical_output, technical_records)
    write_json(
        technical_metadata_output,
        {
            "provider": technical_provider.provider_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(technical_records),
            "as_of_dates": sorted(
                {record.as_of_date for record in technical_records if record.as_of_date}
            ),
            "evaluated_fields": [
                "close_price_cny",
                "prev_close_price_cny",
                "low_price_cny",
                "sma20_cny",
                "sma60_cny",
                "prev_sma20_cny",
                "prev_sma60_cny",
                "breakout_level_cny",
                "volume_ratio_20d",
            ],
            "output_path": str(technical_output),
            "decision_support_only": True,
        },
    )

    config = RuleBasedScanConfig(
        min_total_market_cap_billion_cny=args.min_total_market_cap_bn,
        watch_buffer_ratio=args.watch_buffer_ratio,
        max_close_above_sma20_ratio=args.max_close_above_sma20_ratio,
        min_breakout_volume_ratio=args.min_breakout_volume_ratio,
        support_touch_tolerance_ratio=args.support_touch_tolerance_ratio,
        max_pullback_volume_ratio=args.max_pullback_volume_ratio,
    )
    scan_result = RuleBasedScanner(config).scan(
        universe_records=universe_result.records,
        market_cap_records=market_cap_records,
        technical_records=technical_records,
    )
    write_scan_csv(scan_output, [record.to_row() for record in scan_result.records])
    write_json(
        scan_summary_output,
        {
            **scan_result.to_summary(config),
            "universe_input_path": str(universe_output),
            "market_cap_input_path": str(market_cap_output),
            "technical_input_path": str(technical_output),
            "output_path": str(scan_output),
            "decision_support_only": True,
        },
    )

    print(
        "stage 1/5 stock list:"
        f" provider={stock_list_provider.provider_name}"
        f" records={len(stock_list_records)}"
        f" output={stock_list_output}"
    )
    print(
        "stage 2/5 universe:"
        f" eligible={universe_result.eligible_count}"
        f" total={universe_result.total_count}"
        f" output={universe_output}"
    )
    if universe_result.excluded_by_reason:
        print("excluded by reason:")
        for reason, count in sorted(universe_result.excluded_by_reason.items()):
            print(f"  - {reason}: {count}")
    print(
        "stage 3/5 market-cap snapshot:"
        f" provider={market_cap_provider.provider_name}"
        f" records={len(market_cap_records)}"
        f" output={market_cap_output}"
    )
    print(
        "stage 4/5 technical snapshot:"
        f" provider={technical_provider.provider_name}"
        f" records={len(technical_records)}"
        f" output={technical_output}"
    )
    print(
        "stage 5/5 daily scan:"
        f" thresholds=candidate>={config.min_total_market_cap_billion_cny:.2f} bn,"
        f" watch>={config.watch_floor_billion_cny:.2f} bn,"
        f" max_close_above_sma20={config.max_close_above_sma20_ratio:.2%},"
        f" breakout_volume>={config.min_breakout_volume_ratio:.2f}x"
    )
    for decision in DECISION_SEQUENCE:
        count = sum(1 for record in scan_result.records if record.decision == decision)
        print(f"  - {decision}: {count}")
    print(f"scan output: {scan_output}")
    print(f"scan summary output: {scan_summary_output}")
    print("mode: decision-support only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
