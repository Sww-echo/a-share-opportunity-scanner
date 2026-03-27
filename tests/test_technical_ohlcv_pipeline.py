from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from src.technical import OHLCVCSVTechnicalSnapshotProvider

REPO_ROOT = Path(__file__).resolve().parents[1]
REFRESH_FROM_OHLCV_SCRIPT = (
    REPO_ROOT / "scripts" / "refresh_technical_snapshot_from_ohlcv.py"
)


def build_ohlcv_rows(
    *,
    ts_code: str = "000001.SZ",
    symbol: str | None = "000001",
    name: str | None = "平安银行",
    row_count: int = 61,
    include_volume: bool = True,
) -> list[dict[str, object]]:
    start_date = date(2025, 1, 1)
    rows: list[dict[str, object]] = []

    for index in range(1, row_count + 1):
        close_price = float(index)
        row: dict[str, object] = {
            "ts_code": ts_code,
            "trade_date": (start_date + timedelta(days=index - 1)).isoformat(),
            "high": close_price + 0.4,
            "low": close_price - 0.5,
            "close": close_price,
        }
        if symbol is not None:
            row["symbol"] = symbol
        if name is not None:
            row["name"] = name
        if include_volume:
            row["volume"] = close_price * 100
        rows.append(row)

    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("rows are required")

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class OHLCVTechnicalSnapshotProviderTests(unittest.TestCase):
    def test_provider_computes_required_snapshot_fields_from_local_ohlcv_csv(
        self,
    ) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        source_path = Path(tempdir.name) / "ohlcv.csv"
        write_csv(source_path, build_ohlcv_rows())

        provider = OHLCVCSVTechnicalSnapshotProvider(source_path)
        records = provider.fetch_snapshot()

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.ts_code, "000001.SZ")
        self.assertEqual(record.symbol, "000001")
        self.assertEqual(record.name, "平安银行")
        self.assertEqual(record.close_price_cny, 61.0)
        self.assertEqual(record.prev_close_price_cny, 60.0)
        self.assertEqual(record.low_price_cny, 60.5)
        self.assertEqual(record.sma20_cny, 51.5)
        self.assertEqual(record.sma60_cny, 31.5)
        self.assertEqual(record.prev_sma20_cny, 50.5)
        self.assertEqual(record.prev_sma60_cny, 30.5)
        self.assertEqual(record.breakout_level_cny, 60.4)
        self.assertAlmostEqual(record.volume_ratio_20d or 0.0, 61.0 / 50.5, places=6)
        self.assertEqual(record.as_of_date, "20250302")

    def test_provider_keeps_volume_ratio_blank_when_volume_column_is_missing(
        self,
    ) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        source_path = Path(tempdir.name) / "ohlcv-no-volume.csv"
        write_csv(
            source_path,
            build_ohlcv_rows(
                ts_code="600000.SH",
                symbol=None,
                name=None,
                row_count=21,
                include_volume=False,
            ),
        )

        provider = OHLCVCSVTechnicalSnapshotProvider(source_path)
        records = provider.fetch_snapshot()

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.ts_code, "600000.SH")
        self.assertEqual(record.symbol, "600000")
        self.assertIsNone(record.name)
        self.assertEqual(record.close_price_cny, 21.0)
        self.assertEqual(record.prev_close_price_cny, 20.0)
        self.assertEqual(record.low_price_cny, 20.5)
        self.assertEqual(record.sma20_cny, 11.5)
        self.assertIsNone(record.sma60_cny)
        self.assertEqual(record.prev_sma20_cny, 10.5)
        self.assertIsNone(record.prev_sma60_cny)
        self.assertEqual(record.breakout_level_cny, 20.4)
        self.assertIsNone(record.volume_ratio_20d)
        self.assertEqual(record.as_of_date, "20250121")


class RefreshTechnicalSnapshotFromOHLCVCliTests(unittest.TestCase):
    def load_csv_rows(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_cli_writes_snapshot_and_metadata_from_local_ohlcv_csv(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        source_path = Path(tempdir.name) / "ohlcv.csv"
        output_path = Path(tempdir.name) / "technical_snapshot.csv"
        metadata_path = Path(tempdir.name) / "technical_snapshot.meta.json"
        write_csv(source_path, build_ohlcv_rows())

        completed = subprocess.run(
            [
                sys.executable,
                str(REFRESH_FROM_OHLCV_SCRIPT),
                "--input",
                str(source_path),
                "--output",
                str(output_path),
                "--metadata-output",
                str(metadata_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}",
        )

        rows = self.load_csv_rows(output_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ts_code"], "000001.SZ")
        self.assertEqual(rows[0]["close_price_cny"], "61.00")
        self.assertEqual(rows[0]["prev_close_price_cny"], "60.00")
        self.assertEqual(rows[0]["low_price_cny"], "60.50")
        self.assertEqual(rows[0]["sma20_cny"], "51.50")
        self.assertEqual(rows[0]["sma60_cny"], "31.50")
        self.assertEqual(rows[0]["prev_sma20_cny"], "50.50")
        self.assertEqual(rows[0]["prev_sma60_cny"], "30.50")
        self.assertEqual(rows[0]["breakout_level_cny"], "60.40")
        self.assertEqual(rows[0]["volume_ratio_20d"], "1.21")
        self.assertEqual(rows[0]["as_of_date"], "20250302")

        self.assertEqual(metadata["provider"], "ohlcv_csv")
        self.assertEqual(metadata["record_count"], 1)
        self.assertEqual(metadata["source_path"], str(source_path))
        self.assertEqual(metadata["as_of_dates"], ["20250302"])
        self.assertEqual(metadata["calculation_windows"]["sma20_window"], 20)
        self.assertEqual(metadata["calculation_windows"]["sma60_window"], 60)
        self.assertEqual(metadata["output_path"], str(output_path))
        self.assertTrue(metadata["decision_support_only"])


if __name__ == "__main__":
    unittest.main()
