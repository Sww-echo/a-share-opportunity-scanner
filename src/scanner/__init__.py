"""Minimal scanner for rule-based candidate/watch/reject daily outputs."""

from .config import (
    DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION,
    MarketCapScanConfig,
    RuleBasedScanConfig,
    add_rule_based_scan_arguments,
    add_text_summary_arguments,
    build_scan_config_from_args,
    validate_text_summary_limit,
)
from .engine import MarketCapThresholdScanner, RuleBasedScanner
from .formatter import format_daily_scan_text_summary
from .models import (
    DECISION_SEQUENCE,
    SCAN_RESULT_FIELDNAMES,
    DailyScanRecord,
    DailyScanResult,
)
from .ranking import ScanRankingProfile, build_scan_ranking_profile, rank_scan_records

__all__ = [
    "add_rule_based_scan_arguments",
    "add_text_summary_arguments",
    "build_scan_config_from_args",
    "DECISION_SEQUENCE",
    "DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION",
    "DailyScanRecord",
    "DailyScanResult",
    "MarketCapScanConfig",
    "MarketCapThresholdScanner",
    "RuleBasedScanConfig",
    "RuleBasedScanner",
    "SCAN_RESULT_FIELDNAMES",
    "ScanRankingProfile",
    "validate_text_summary_limit",
    "build_scan_ranking_profile",
    "format_daily_scan_text_summary",
    "rank_scan_records",
]
