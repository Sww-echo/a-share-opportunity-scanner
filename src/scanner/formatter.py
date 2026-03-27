from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .config import DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION, RuleBasedScanConfig
from .models import DECISION_SEQUENCE, DailyScanRecord, DailyScanResult
from .ranking import build_scan_ranking_profile


def format_daily_scan_text_summary(
    result: DailyScanResult,
    config: RuleBasedScanConfig,
    *,
    technical_snapshot_row_count: int | None = None,
    csv_output_path: str | None = None,
    summary_output_path: str | None = None,
    text_output_path: str | None = None,
    limit_per_decision: int = DEFAULT_TEXT_SUMMARY_LIMIT_PER_DECISION,
) -> str:
    if limit_per_decision < 0:
        raise ValueError("limit_per_decision must be non-negative")

    summary = result.to_summary(config)
    decision_counts = summary["decision_counts"]
    threshold_parts = config.threshold_summary_parts()

    lines = [
        "Daily Scan Review",
        _join_summary_parts(
            [
                f"Universe: total={result.total_universe_count}",
                f"eligible={result.eligible_universe_count}",
                f"skipped={result.total_universe_count - result.eligible_universe_count}",
                (
                    f"technical_rows={technical_snapshot_row_count}"
                    if technical_snapshot_row_count is not None
                    else None
                ),
            ]
        ),
        _join_summary_parts(
            [
                f"Decisions: candidate={decision_counts['candidate']}",
                f"watch={decision_counts['watch']}",
                f"reject={decision_counts['reject']}",
            ]
        ),
        _join_summary_parts(
            [f"Thresholds: {threshold_parts[0]}", *threshold_parts[1:]]
        ),
        (
            "Ranking: candidate > watch > reject | lower risk tier | higher score | "
            "more/fresher confirmed triggers | fewer risks | more liquidity"
        ),
    ]

    records_by_decision = {
        decision: [record for record in result.records if record.decision == decision]
        for decision in DECISION_SEQUENCE
    }
    for decision in DECISION_SEQUENCE:
        lines.extend(
            _format_decision_section(
                decision=decision,
                records=records_by_decision[decision],
                limit_per_decision=limit_per_decision,
            )
        )

    output_parts: list[str] = []
    if csv_output_path is not None:
        output_parts.append(f"csv={csv_output_path}")
    if summary_output_path is not None:
        output_parts.append(f"json={summary_output_path}")
    if text_output_path is not None:
        output_parts.append(f"text={text_output_path}")
    if output_parts:
        lines.extend(["", _join_summary_parts([f"Outputs: {output_parts[0]}", *output_parts[1:]])])

    lines.append("Mode: decision-support only")
    return "\n".join(lines) + "\n"


def _format_decision_section(
    *,
    decision: str,
    records: list[DailyScanRecord],
    limit_per_decision: int,
) -> list[str]:
    lines = ["", f"{decision.title()} ({len(records)})"]
    if not records:
        lines.append("none")
        return lines

    lines.append(f"Top reasons: {_format_top_counts(record.reason for record in records)}")
    lines.append(
        f"Top signals: {_format_top_counts(_flatten(record.signal_reasons for record in records))}"
    )
    lines.append(
        f"Top risks: {_format_top_counts(_flatten(record.risk_flags for record in records))}"
    )

    display_records = records if limit_per_decision == 0 else records[:limit_per_decision]
    for index, record in enumerate(display_records, start=1):
        ranking_profile = build_scan_ranking_profile(record)
        lines.extend(
            [
                _join_summary_parts(
                    [
                        f"{index}. {record.symbol} {record.name} ({record.ts_code})",
                        f"score={record.score}/{record.max_score}",
                        f"risk_tier={ranking_profile.major_risk_tier}",
                        (
                            "confirmed_triggers="
                            f"{','.join(ranking_profile.confirmed_triggers) or 'none'}"
                        ),
                        f"total_cap={_format_market_cap(record.total_market_cap_billion_cny)}",
                        (
                            "float_cap="
                            f"{_format_market_cap(record.circulating_market_cap_billion_cny)}"
                        ),
                    ]
                ),
                f"   reason: {record.reason}",
                (
                    "   signals: "
                    f"{', '.join(record.signal_reasons) if record.signal_reasons else 'none'}"
                ),
                (
                    "   risks: "
                    f"{', '.join(record.risk_flags) if record.risk_flags else 'none'}"
                ),
            ]
        )

    hidden_count = len(records) - len(display_records)
    if hidden_count > 0:
        lines.append(
            (
                f"... {hidden_count} more ranked {decision} rows not shown; "
                "set limit_per_decision=0 to include all rows"
            )
        )
    return lines


def _flatten(groups: Iterable[tuple[str, ...]]) -> Iterable[str]:
    for group in groups:
        yield from group


def _format_top_counts(values: Iterable[str], *, limit: int = 3) -> str:
    counts = Counter(values)
    if not counts:
        return "none"
    ranked_items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{value}({count})" for value, count in ranked_items[:limit])


def _join_summary_parts(parts: Iterable[str | None]) -> str:
    return " | ".join(part for part in parts if part)


def _format_market_cap(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f} bn"
