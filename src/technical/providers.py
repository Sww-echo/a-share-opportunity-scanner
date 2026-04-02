from __future__ import annotations

import importlib
from pathlib import Path

from .calculators import calculate_technical_snapshot
from .csv_store import load_technical_snapshot
from .interfaces import TechnicalSnapshotProvider
from .models import TechnicalSnapshotRecord
from .ohlcv_provider import OHLCVBar

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_TECHNICAL_SNAPSHOT_PATH = (
    REPO_ROOT / "data" / "seeds" / "sample_technical_snapshot_cn.csv"
)


def _clean(value: object | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _clean_float(value: object | None) -> float | None:
    text = _clean(value)
    if text is None:
        return None

    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def _infer_ts_code_from_symbol(symbol: str) -> str:
    normalized = symbol.strip()
    if not normalized:
        raise ValueError("symbol is required")

    if normalized.startswith(("6", "9")) or normalized.startswith(("50", "51", "58")):
        suffix = "SH"
    elif normalized.startswith(("8", "4")):
        suffix = "BJ"
    else:
        suffix = "SZ"
    return f"{normalized}.{suffix}"


class SampleTechnicalSnapshotProvider(TechnicalSnapshotProvider):
    provider_name = "sample"

    def __init__(self, sample_path: Path | None = None) -> None:
        self._sample_path = sample_path or DEFAULT_SAMPLE_TECHNICAL_SNAPSHOT_PATH

    def fetch_snapshot(self) -> list[TechnicalSnapshotRecord]:
        return load_technical_snapshot(self._sample_path)


class CSVTechnicalSnapshotProvider(TechnicalSnapshotProvider):
    provider_name = "csv"

    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path

    def fetch_snapshot(self) -> list[TechnicalSnapshotRecord]:
        return load_technical_snapshot(self._source_path)


class AKShareTechnicalSnapshotProvider(TechnicalSnapshotProvider):
    provider_name = "akshare"

    def __init__(self, lookback_days: int = 120) -> None:
        self._lookback_days = lookback_days

    def _fetch_spot_rows(self, akshare: object) -> list[dict[str, object]]:
        fetcher = getattr(akshare, "stock_zh_a_spot_em", None)
        if not callable(fetcher):
            raise RuntimeError("AKShare does not expose stock_zh_a_spot_em in this environment.")
        try:
            frame = fetcher()
        except Exception as exc:
            raise RuntimeError(f"failed to fetch A-share spot list from AKShare: {exc}") from exc

        to_dict = getattr(frame, "to_dict", None)
        if not callable(to_dict):
            return []

        try:
            rows = to_dict(orient="records")
        except TypeError:
            rows = to_dict("records")
        return [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []

    def _fetch_history_rows(
        self,
        akshare: object,
        symbol: str,
    ) -> list[dict[str, object]]:
        fetcher = getattr(akshare, "stock_zh_a_hist", None)
        if not callable(fetcher):
            raise RuntimeError("AKShare does not expose stock_zh_a_hist in this environment.")

        try:
            frame = fetcher(symbol=symbol, period="daily", adjust="qfq")
        except Exception as exc:
            raise RuntimeError(f"failed to fetch AKShare history for {symbol}: {exc}") from exc

        to_dict = getattr(frame, "to_dict", None)
        if not callable(to_dict):
            return []

        try:
            rows = to_dict(orient="records")
        except TypeError:
            rows = to_dict("records")
        if not isinstance(rows, list):
            return []
        return [item for item in rows if isinstance(item, dict)]

    def fetch_snapshot(self) -> list[TechnicalSnapshotRecord]:
        try:
            akshare = importlib.import_module("akshare")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "akshare is required when provider=akshare. Install it in the project environment first."
            ) from exc

        spot_rows = self._fetch_spot_rows(akshare)
        if not spot_rows:
            raise RuntimeError("AKShare stock_zh_a_spot_em returned no rows.")

        records: list[TechnicalSnapshotRecord] = []
        for row in spot_rows:
            symbol = _clean(row.get("代码") or row.get("code") or row.get("symbol"))
            name = _clean(row.get("名称") or row.get("name"))
            if not symbol:
                continue

            history_rows = self._fetch_history_rows(akshare, symbol)
            bars: list[OHLCVBar] = []
            for item in history_rows[-self._lookback_days :]:
                trade_date = _clean(item.get("日期") or item.get("date") or item.get("trade_date"))
                high_price = _clean_float(item.get("最高") or item.get("high"))
                low_price = _clean_float(item.get("最低") or item.get("low"))
                close_price = _clean_float(item.get("收盘") or item.get("close"))
                volume = _clean_float(item.get("成交量") or item.get("volume") or item.get("vol"))
                if not trade_date or high_price is None or low_price is None or close_price is None:
                    continue

                digits = "".join(ch for ch in trade_date if ch.isdigit())
                if len(digits) < 8:
                    continue

                bars.append(
                    OHLCVBar(
                        ts_code=_infer_ts_code_from_symbol(symbol),
                        trade_date=digits[:8],
                        high_price_cny=high_price,
                        low_price_cny=low_price,
                        close_price_cny=close_price,
                        volume=volume,
                        symbol=symbol,
                        name=name,
                    )
                )

            if not bars:
                continue
            records.append(calculate_technical_snapshot(bars))

        return sorted(records, key=lambda item: item.symbol or item.ts_code)


def create_technical_snapshot_provider(
    name: str,
    *,
    source_path: Path | None = None,
    sample_path: Path | None = None,
) -> TechnicalSnapshotProvider:
    """Create a normalized technical snapshot provider."""

    normalized_name = name.strip().lower()

    if normalized_name == "sample":
        return SampleTechnicalSnapshotProvider(sample_path=sample_path)
    if normalized_name == "csv":
        if source_path is None:
            raise ValueError("source_path is required when provider=csv")
        return CSVTechnicalSnapshotProvider(source_path=source_path)
    if normalized_name == "akshare":
        return AKShareTechnicalSnapshotProvider()

    raise ValueError(f"unsupported technical snapshot provider: {name}")
