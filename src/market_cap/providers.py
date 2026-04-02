from __future__ import annotations

import importlib
import json
import os
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from urllib import error, request
from zoneinfo import ZoneInfo

from .csv_store import load_market_cap_snapshot
from .interfaces import MarketCapSnapshotProvider
from .models import MarketCapSnapshotRecord

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_MARKET_CAP_SNAPSHOT_PATH = (
    REPO_ROOT / "data" / "seeds" / "sample_market_cap_snapshot_cn.csv"
)
TUSHARE_PRO_API_URL = "http://api.tushare.pro"
TUSHARE_SDK_HTTP_URL_OVERRIDE = "http://118.89.66.41:8010/"
TUSHARE_DAILY_BASIC_FIELDS = "ts_code,trade_date,total_mv,circ_mv"
TUSHARE_TRADE_CAL_FIELDS = "cal_date,is_open"
WAN_CNY_PER_BILLION_CNY = 100000.0
CHINA_TZ = ZoneInfo("Asia/Shanghai")
YIYUAN_CNY_PER_BILLION_CNY = 10.0


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
    except ValueError as exc:
        raise ValueError(f"invalid Tushare numeric value: {value}") from exc


def _sdk_result_to_rows(result: object) -> list[dict[str, object]]:
    if result is None:
        return []

    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]

    to_dict = getattr(result, "to_dict", None)
    if not callable(to_dict):
        return []

    try:
        rows = to_dict(orient="records")
    except TypeError:
        rows = to_dict("records")

    if not isinstance(rows, list):
        return []

    return [item for item in rows if isinstance(item, dict)]


def _symbol_from_ts_code(ts_code: str) -> str:
    return ts_code.split(".", 1)[0]


def _market_cap_billion_cny(value: object | None) -> float | None:
    amount_wan = _clean_float(value)
    if amount_wan is None:
        return None
    return amount_wan / WAN_CNY_PER_BILLION_CNY


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


class SampleMarketCapSnapshotProvider(MarketCapSnapshotProvider):
    provider_name = "sample"

    def __init__(self, sample_path: Path | None = None) -> None:
        self._sample_path = sample_path or DEFAULT_SAMPLE_MARKET_CAP_SNAPSHOT_PATH

    def fetch_snapshot(self) -> list[MarketCapSnapshotRecord]:
        return load_market_cap_snapshot(self._sample_path)


class CSVMarketCapSnapshotProvider(MarketCapSnapshotProvider):
    provider_name = "csv"

    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path

    def fetch_snapshot(self) -> list[MarketCapSnapshotRecord]:
        return load_market_cap_snapshot(self._source_path)


class TushareMarketCapSnapshotProvider(MarketCapSnapshotProvider):
    provider_name = "tushare"

    def __init__(
        self,
        token: str | None = None,
        trade_date: str | None = None,
        api_url: str = TUSHARE_PRO_API_URL,
        sdk_http_url_override: str | None = TUSHARE_SDK_HTTP_URL_OVERRIDE,
        timeout_seconds: float = 30.0,
        calendar_lookback_days: int = 20,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._token = token or os.getenv("TUSHARE_TOKEN")
        self._trade_date = trade_date
        self._api_url = api_url
        self._sdk_http_url_override = sdk_http_url_override
        self._timeout_seconds = timeout_seconds
        self._calendar_lookback_days = calendar_lookback_days
        self._now_provider = now_provider

    def _get_china_now(self) -> datetime:
        if self._now_provider is not None:
            return self._now_provider()
        return datetime.now(CHINA_TZ)

    def _create_tushare_pro_client(self) -> object | None:
        try:
            tushare = importlib.import_module("tushare")
        except ModuleNotFoundError:
            return None

        pro_client = tushare.pro_api(self._token)
        if self._sdk_http_url_override and hasattr(pro_client, "_DataApi__http_url"):
            pro_client._DataApi__http_url = self._sdk_http_url_override
        return pro_client

    def _fetch_rows_from_sdk(
        self,
        pro_client: object,
        api_name: str,
        params: dict[str, object],
        fields: str,
    ) -> list[dict[str, object]]:
        api_method = getattr(pro_client, api_name, None)
        if not callable(api_method):
            raise RuntimeError(
                f"official tushare SDK client does not expose {api_name}."
            )

        call_kwargs = dict(params)
        if fields:
            call_kwargs["fields"] = fields

        try:
            result = api_method(**call_kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"failed to fetch Tushare {api_name} via official SDK: {exc}"
            ) from exc

        return _sdk_result_to_rows(result)

    def _fetch_rows_from_http(
        self,
        api_name: str,
        params: dict[str, object],
        fields: str,
    ) -> list[dict[str, object]]:
        payload = {
            "api_name": api_name,
            "token": self._token,
            "params": params,
            "fields": fields,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self._api_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                response_text = response.read().decode("utf-8")
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"failed to reach Tushare {api_name} endpoint at {self._api_url}: {exc}"
            ) from exc

        try:
            response_payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Tushare {api_name} response was not valid JSON."
            ) from exc

        code = response_payload.get("code")
        if code != 0:
            message = response_payload.get("msg") or "unknown error"
            raise RuntimeError(
                f"Tushare {api_name} request failed with code {code}: {message}"
            )

        data = response_payload.get("data")
        if not isinstance(data, dict):
            return []

        response_fields = data.get("fields")
        items = data.get("items")
        if not isinstance(response_fields, list) or not isinstance(items, list):
            return []

        rows: list[dict[str, object]] = []
        for item in items:
            if not isinstance(item, list):
                continue
            rows.append(dict(zip(response_fields, item)))
        return rows

    def _fetch_rows(
        self,
        api_name: str,
        params: dict[str, object],
        fields: str,
        pro_client: object | None,
    ) -> list[dict[str, object]]:
        if pro_client is not None:
            return self._fetch_rows_from_sdk(pro_client, api_name, params, fields)
        return self._fetch_rows_from_http(api_name, params, fields)

    def _resolve_trade_date(self, pro_client: object | None) -> str:
        if self._trade_date:
            return self._trade_date

        china_now = self._get_china_now().astimezone(CHINA_TZ)
        end_date = china_now.strftime("%Y%m%d")
        start_date = (china_now - timedelta(days=self._calendar_lookback_days)).strftime(
            "%Y%m%d"
        )
        rows = self._fetch_rows(
            "trade_cal",
            {
                "exchange": "SSE",
                "start_date": start_date,
                "end_date": end_date,
            },
            TUSHARE_TRADE_CAL_FIELDS,
            pro_client,
        )

        open_dates = sorted(
            {
                cal_date
                for row in rows
                if _clean(row.get("is_open")) == "1"
                for cal_date in [_clean(row.get("cal_date"))]
                if cal_date
            },
            reverse=True,
        )
        if not open_dates:
            raise RuntimeError("Tushare trade_cal returned no open trade dates.")

        today = china_now.strftime("%Y%m%d")
        if open_dates[0] != today:
            return open_dates[0]

        if china_now.strftime("%H:%M") < "17:00" and len(open_dates) > 1:
            return open_dates[1]
        return open_dates[0]

    def fetch_snapshot(self) -> list[MarketCapSnapshotRecord]:
        if not self._token:
            raise RuntimeError("TUSHARE_TOKEN is required when provider=tushare.")

        pro_client = self._create_tushare_pro_client()
        trade_date = self._resolve_trade_date(pro_client)
        rows = self._fetch_rows(
            "daily_basic",
            {"trade_date": trade_date},
            TUSHARE_DAILY_BASIC_FIELDS,
            pro_client,
        )

        records: list[MarketCapSnapshotRecord] = []
        for row in rows:
            ts_code = _clean(row.get("ts_code"))
            total_market_cap_billion_cny = _market_cap_billion_cny(row.get("total_mv"))
            if not ts_code or total_market_cap_billion_cny is None:
                continue

            records.append(
                MarketCapSnapshotRecord(
                    ts_code=ts_code,
                    symbol=_symbol_from_ts_code(ts_code),
                    total_market_cap_billion_cny=total_market_cap_billion_cny,
                    circulating_market_cap_billion_cny=_market_cap_billion_cny(
                        row.get("circ_mv")
                    ),
                    as_of_date=_clean(row.get("trade_date")) or trade_date,
                )
            )

        return sorted(records, key=lambda item: item.symbol or item.ts_code)


class AKShareMarketCapSnapshotProvider(MarketCapSnapshotProvider):
    provider_name = "akshare"

    def fetch_snapshot(self) -> list[MarketCapSnapshotRecord]:
        try:
            akshare = importlib.import_module("akshare")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "akshare is required when provider=akshare. Install it in the project environment first."
            ) from exc

        fetcher = getattr(akshare, "stock_zh_a_spot_em", None)
        if not callable(fetcher):
            raise RuntimeError("AKShare does not expose stock_zh_a_spot_em in this environment.")

        try:
            frame = fetcher()
        except Exception as exc:
            raise RuntimeError(f"failed to fetch A-share spot snapshot from AKShare: {exc}") from exc

        rows = _sdk_result_to_rows(frame)
        if not rows:
            raise RuntimeError("AKShare stock_zh_a_spot_em returned no rows.")

        records: list[MarketCapSnapshotRecord] = []
        seen: set[str] = set()
        for row in rows:
            symbol = _clean(row.get("代码") or row.get("code") or row.get("symbol"))
            if not symbol:
                continue
            ts_code = _infer_ts_code_from_symbol(symbol)
            if ts_code in seen:
                continue

            total_market_cap_yi = _clean_float(row.get("总市值") or row.get("总市值-动态") or row.get("total_market_cap"))
            if total_market_cap_yi is None:
                continue

            circ_market_cap_yi = _clean_float(
                row.get("流通市值") or row.get("circulating_market_cap")
            )
            as_of_date = _clean(row.get("最新行情时间") or row.get("更新时间") or row.get("latest_time"))
            if as_of_date:
                digits = "".join(ch for ch in as_of_date if ch.isdigit())
                as_of_date = digits[:8] if len(digits) >= 8 else None

            records.append(
                MarketCapSnapshotRecord(
                    ts_code=ts_code,
                    symbol=symbol,
                    name=_clean(row.get("名称") or row.get("name")),
                    total_market_cap_billion_cny=total_market_cap_yi / YIYUAN_CNY_PER_BILLION_CNY,
                    circulating_market_cap_billion_cny=(
                        circ_market_cap_yi / YIYUAN_CNY_PER_BILLION_CNY
                        if circ_market_cap_yi is not None
                        else None
                    ),
                    as_of_date=as_of_date,
                )
            )
            seen.add(ts_code)

        return sorted(records, key=lambda item: item.symbol or item.ts_code)


def create_market_cap_snapshot_provider(
    name: str,
    *,
    source_path: Path | None = None,
    sample_path: Path | None = None,
    token: str | None = None,
    trade_date: str | None = None,
) -> MarketCapSnapshotProvider:
    """
    Create a normalized market-cap snapshot provider.

    Future real-data providers should plug in here after they normalize to the
    shared CSV contract in `MarketCapSnapshotRecord`.
    """

    normalized_name = name.strip().lower()

    if normalized_name == "sample":
        return SampleMarketCapSnapshotProvider(sample_path=sample_path)
    if normalized_name == "csv":
        if source_path is None:
            raise ValueError("source_path is required when provider=csv")
        return CSVMarketCapSnapshotProvider(source_path=source_path)
    if normalized_name == "tushare":
        return TushareMarketCapSnapshotProvider(
            token=token,
            trade_date=trade_date,
        )
    if normalized_name == "akshare":
        return AKShareMarketCapSnapshotProvider()

    raise ValueError(f"unsupported market-cap snapshot provider: {name}")
