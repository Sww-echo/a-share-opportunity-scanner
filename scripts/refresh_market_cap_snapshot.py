#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.market_cap import create_market_cap_snapshot_provider, write_market_cap_snapshot

DEFAULT_OUTPUT = REPO_ROOT / "data" / "raw" / "market_cap_snapshot_cn.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the normalized market-cap snapshot used by the decision-support scanner.",
        epilog="This command only prepares fact data. It does not execute, simulate, or automate trades.",
    )
    parser.add_argument(
        "--provider",
        choices=("sample", "csv", "tushare"),
        default="sample",
        help="Market-cap snapshot provider. Default: sample.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Source CSV path when --provider=csv.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        help="Optional metadata JSON output. Default: <output>.meta.json",
    )
    parser.add_argument(
        "--tushare-token",
        help="Optional Tushare token override. Default: use TUSHARE_TOKEN.",
    )
    parser.add_argument(
        "--trade-date",
        help=(
            "Optional Tushare trade date (YYYYMMDD). Default: auto-pick the most "
            "practical recent open date via trade_cal."
        ),
    )
    return parser.parse_args()


def resolve_metadata_path(output_path: Path, metadata_output: Path | None) -> Path:
    return metadata_output or output_path.with_suffix(".meta.json")


def main() -> int:
    args = parse_args()
    provider = create_market_cap_snapshot_provider(
        args.provider,
        source_path=args.input,
        token=args.tushare_token,
        trade_date=args.trade_date,
    )

    records = provider.fetch_snapshot()
    write_market_cap_snapshot(args.output, records)

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
                "normalized_unit": "billion_cny",
                "output_path": str(args.output),
                "decision_support_only": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"refreshed market-cap snapshot: {len(records)} records")
    print(f"csv output: {args.output}")
    print(f"metadata output: {metadata_path}")
    print("normalized unit: billion_cny")
    print("mode: decision-support only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
