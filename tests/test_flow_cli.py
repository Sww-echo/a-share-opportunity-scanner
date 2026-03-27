from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FLOW_SCRIPT = REPO_ROOT / "scripts" / "run_rule_based_flow.py"
SEED_STOCK_LIST = REPO_ROOT / "data" / "seeds" / "sample_stock_list_cn.csv"
SEED_MARKET_CAP = REPO_ROOT / "data" / "seeds" / "sample_market_cap_snapshot_cn.csv"
SEED_TECHNICAL = REPO_ROOT / "data" / "seeds" / "sample_technical_snapshot_cn.csv"


class RuleBasedFlowCliTests(unittest.TestCase):
    def run_flow(self, *extra_args: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        data_root = Path(tempdir.name) / "data"
        completed = subprocess.run(
            [
                sys.executable,
                str(FLOW_SCRIPT),
                "--data-root",
                str(data_root),
                *extra_args,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return completed, data_root

    def load_json(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_sample_flow_runs_end_to_end(self) -> None:
        completed, data_root = self.run_flow()

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}",
        )

        summary = self.load_json(data_root / "derived" / "daily_scan_summary_cn.json")
        self.assertEqual(
            summary["decision_counts"],
            {
                "candidate": 2,
                "watch": 4,
                "reject": 1,
            },
        )
        self.assertEqual(summary["score_model"]["max_score"], 10)
        self.assertEqual(
            summary["thresholds"]["max_close_above_sma20_ratio"],
            0.05,
        )
        self.assertEqual(summary["thresholds"]["min_breakout_volume_ratio"], 1.2)
        self.assertEqual(summary["thresholds"]["support_touch_tolerance_ratio"], 0.01)
        self.assertEqual(summary["thresholds"]["max_pullback_volume_ratio"], 1.0)
        self.assertTrue((data_root / "raw" / "technical_snapshot_cn.csv").exists())
        self.assertTrue((data_root / "derived" / "daily_scan_cn.csv").exists())

    def test_csv_flow_runs_end_to_end_from_seed_contracts(self) -> None:
        completed, data_root = self.run_flow(
            "--stock-list-provider",
            "csv",
            "--stock-list-input",
            str(SEED_STOCK_LIST),
            "--market-cap-provider",
            "csv",
            "--market-cap-input",
            str(SEED_MARKET_CAP),
            "--technical-provider",
            "csv",
            "--technical-input",
            str(SEED_TECHNICAL),
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}",
        )

        stock_list_meta = self.load_json(data_root / "raw" / "stock_list_cn.meta.json")
        market_cap_meta = self.load_json(
            data_root / "raw" / "market_cap_snapshot_cn.meta.json"
        )
        technical_meta = self.load_json(
            data_root / "raw" / "technical_snapshot_cn.meta.json"
        )
        scan_summary = self.load_json(data_root / "derived" / "daily_scan_summary_cn.json")

        self.assertEqual(stock_list_meta["provider"], "csv")
        self.assertEqual(market_cap_meta["provider"], "csv")
        self.assertEqual(technical_meta["provider"], "csv")
        self.assertEqual(
            scan_summary["decision_counts"],
            {
                "candidate": 2,
                "watch": 4,
                "reject": 1,
            },
        )
        self.assertEqual(scan_summary["score_model"]["max_score"], 10)
