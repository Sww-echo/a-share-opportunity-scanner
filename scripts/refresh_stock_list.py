#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.data_provider import create_stock_list_provider, write_stock_list

DEFAULT_OUTPUT = REPO_ROOT / "data" / "raw" / "stock_list_cn.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the normalized A-share stock list used by the decision-support scanner.",
        epilog="This command only refreshes metadata. It does not execute, simulate, or automate trades.",
    )
    parser.add_argument(
        "--provider",
        choices=("sample", "csv", "tushare"),
        default="sample",
        help="Stock-list provider. Default: sample.",
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
        "--list-status",
        default="L",
        help="Tushare list_status filter when --provider=tushare. Default: L.",
    )
    return parser.parse_args()


def resolve_metadata_path(output_path: Path, metadata_output: Path | None) -> Path:
    return metadata_output or output_path.with_suffix(".meta.json")


def main() -> int:
    args = parse_args()
    provider = create_stock_list_provider(
        args.provider,
        source_path=args.input,
        token=args.tushare_token,
        list_status=args.list_status,
    )

    records = provider.fetch_stock_list()
    write_stock_list(args.output, records)

    metadata_path = resolve_metadata_path(args.output, args.metadata_output)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "provider": provider.provider_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "record_count": len(records),
                "output_path": str(args.output),
                "decision_support_only": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"refreshed stock list: {len(records)} records")
    print(f"csv output: {args.output}")
    print(f"metadata output: {metadata_path}")
    print("mode: decision-support only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
