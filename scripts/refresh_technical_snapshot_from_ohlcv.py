#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.technical import (
    OHLCVCSVTechnicalSnapshotProvider,
    TechnicalSnapshotCalculationConfig,
    write_technical_snapshot,
)

DEFAULT_OUTPUT = REPO_ROOT / "data" / "raw" / "technical_snapshot_cn.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the normalized technical snapshot used by the scanner from "
            "a local OHLCV-style CSV."
        ),
        epilog=(
            "This command only produces decision-support fact data. "
            "It never places orders or automates trades."
        ),
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help=(
            "Local OHLCV CSV input path. Required columns: ts_code, trade_date/date, "
            "high, low, close. Optional columns: symbol, name, volume/vol."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output technical snapshot CSV. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        help="Optional metadata JSON output. Default: <output>.meta.json",
    )
    return parser.parse_args()


def resolve_metadata_path(output_path: Path, metadata_output: Path | None) -> Path:
    return metadata_output or output_path.with_suffix(".meta.json")


def main() -> int:
    args = parse_args()
    config = TechnicalSnapshotCalculationConfig()
    provider = OHLCVCSVTechnicalSnapshotProvider(
        args.input,
        calculation_config=config,
    )

    records = provider.fetch_snapshot()
    write_technical_snapshot(args.output, records)

    metadata_path = resolve_metadata_path(args.output, args.metadata_output)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    as_of_dates = sorted({record.as_of_date for record in records if record.as_of_date})
    metadata_path.write_text(
        json.dumps(
            {
                "provider": provider.provider_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "record_count": len(records),
                "as_of_dates": as_of_dates,
                "source_path": str(args.input),
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
                "calculation_contract": {
                    "sma20_cny": "trailing mean of the latest 20 closes",
                    "sma60_cny": "trailing mean of the latest 60 closes",
                    "prev_sma20_cny": (
                        "trailing mean of the prior 20 closes ending on the "
                        "previous session"
                    ),
                    "prev_sma60_cny": (
                        "trailing mean of the prior 60 closes ending on the "
                        "previous session"
                    ),
                    "breakout_level_cny": (
                        "highest high across the prior 20 sessions, excluding "
                        "the latest session"
                    ),
                    "volume_ratio_20d": (
                        "latest volume divided by the mean volume of the prior "
                        "20 sessions when volume data is available"
                    ),
                },
                "calculation_windows": {
                    "sma20_window": config.sma20_window,
                    "sma60_window": config.sma60_window,
                    "breakout_lookback_window": config.breakout_lookback_window,
                    "volume_ratio_window": config.volume_ratio_window,
                },
                "output_path": str(args.output),
                "decision_support_only": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"generated technical snapshot from OHLCV: {len(records)} records")
    print(f"ohlcv input: {args.input}")
    print(f"csv output: {args.output}")
    print(f"metadata output: {metadata_path}")
    print(
        "calculation windows:"
        f" sma20={config.sma20_window},"
        f" sma60={config.sma60_window},"
        f" breakout={config.breakout_lookback_window},"
        f" volume_ratio={config.volume_ratio_window}"
    )
    print("mode: decision-support only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
