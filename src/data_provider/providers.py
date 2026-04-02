from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from urllib import error, request

from .csv_store import load_stock_list
from .interfaces import StockListProvider
from .models import StockListRecord

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_STOCK_LIST_PATH = REPO_ROOT / "data" / "seeds" / "sample_stock_list_cn.csv"
TUSHARE_PRO_API_URL = "http://api.tushare.pro"
TUSHARE_SDK_HTTP_URL_OVERRIDE = "http://118.89.66.41:8010/"
TUSHARE_STOCK_BASIC_FIELDS = (
    "ts_code,symbol,name,area,industry,market,exchange,"
    "list_status,list_date,is_hs"
)


def _clean(value: object | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _exchange_from_ts_code(ts_code: str) -> str:
    suffix = ts_code.split(".")[-1].upper()
    mapping = {
        "SH": "SSE",
        "SZ": "SZSE",
        "BJ": "BSE",
    }
    return mapping.get(suffix, "UNKNOWN")


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


class SampleStockListProvider(StockListProvider):
    provider_name = "sample"

    def __init__(self, sample_path: Path | None = None) -> None:
        self._sample_path = sample_path or DEFAULT_SAMPLE_STOCK_LIST_PATH

    def fetch_stock_list(self) -> list[StockListRecord]:
        return load_stock_list(self._sample_path)


class CSVStockListProvider(StockListProvider):
    provider_name = "csv"

    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path

    def fetch_stock_list(self) -> list[StockListRecord]:
        return load_stock_list(self._source_path)


class TushareStockListProvider(StockListProvider):
    provider_name = "tushare"

    def __init__(
        self,
        token: str | None = None,
        list_status: str = "L",
        api_url: str = TUSHARE_PRO_API_URL,
        sdk_http_url_override: str | None = TUSHARE_SDK_HTTP_URL_OVERRIDE,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._token = token or os.getenv("TUSHARE_TOKEN")
        self._list_status = list_status
        self._api_url = api_url
        self._sdk_http_url_override = sdk_http_url_override
        self._timeout_seconds = timeout_seconds

    def _create_tushare_pro_client(self) -> object | None:
        try:
            tushare = importlib.import_module("tushare")
        except ModuleNotFoundError:
            return None

        pro_client = tushare.pro_api(self._token)
        if self._sdk_http_url_override and hasattr(pro_client, "_DataApi__http_url"):
            pro_client._DataApi__http_url = self._sdk_http_url_override
        return pro_client

    def _fetch_stock_basic_rows_from_sdk(self, pro_client: object) -> list[dict[str, object]]:
        stock_basic = getattr(pro_client, "stock_basic", None)
        if not callable(stock_basic):
            raise RuntimeError("official tushare SDK client does not expose stock_basic.")

        try:
            result = stock_basic(
                exchange="",
                list_status=self._list_status,
                fields=TUSHARE_STOCK_BASIC_FIELDS,
            )
        except Exception as exc:
            raise RuntimeError(
                f"failed to fetch Tushare stock_basic via official SDK: {exc}"
            ) from exc

        return _sdk_result_to_rows(result)

    def _fetch_stock_basic_rows_from_http(self) -> list[dict[str, object]]:
        payload = {
            "api_name": "stock_basic",
            "token": self._token,
            "params": {
                "exchange": "",
                "list_status": self._list_status,
            },
            "fields": TUSHARE_STOCK_BASIC_FIELDS,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self._api_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(
                http_request,
                timeout=self._timeout_seconds,
            ) as response:
                response_text = response.read().decode("utf-8")
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"failed to reach Tushare stock_basic endpoint at {self._api_url}: {exc}"
            ) from exc

        try:
            response_payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Tushare stock_basic response was not valid JSON."
            ) from exc

        code = response_payload.get("code")
        if code != 0:
            message = response_payload.get("msg") or "unknown error"
            raise RuntimeError(
                f"Tushare stock_basic request failed with code {code}: {message}"
            )

        data = response_payload.get("data")
        if not isinstance(data, dict):
            return []

        fields = data.get("fields")
        items = data.get("items")
        if not isinstance(fields, list) or not isinstance(items, list):
            return []

        rows: list[dict[str, object]] = []
        for item in items:
            if not isinstance(item, list):
                continue
            rows.append(dict(zip(fields, item)))
        return rows

    def _fetch_stock_basic_rows(self) -> list[dict[str, object]]:
        pro_client = self._create_tushare_pro_client()
        if pro_client is not None:
            return self._fetch_stock_basic_rows_from_sdk(pro_client)

        return self._fetch_stock_basic_rows_from_http()

    def fetch_stock_list(self) -> list[StockListRecord]:
        if not self._token:
            raise RuntimeError("TUSHARE_TOKEN is required when provider=tushare.")

        rows = self._fetch_stock_basic_rows()
        records: list[StockListRecord] = []
        for row in rows:
            ts_code = _clean(row.get("ts_code"))
            symbol = _clean(row.get("symbol"))
            name = _clean(row.get("name"))
            board = _clean(row.get("market")) or "未分类"

            if not ts_code or not symbol or not name:
                continue

            exchange = _clean(row.get("exchange")) or _exchange_from_ts_code(ts_code)
            records.append(
                StockListRecord(
                    ts_code=ts_code,
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    board=board,
                    list_status=_clean(row.get("list_status")) or self._list_status,
                    list_date=_clean(row.get("list_date")),
                    area=_clean(row.get("area")),
                    industry=_clean(row.get("industry")),
                    is_hs=_clean(row.get("is_hs")),
                )
            )

        return sorted(records, key=lambda item: item.symbol)


class AKShareStockListProvider(StockListProvider):
    provider_name = "akshare"

    def fetch_stock_list(self) -> list[StockListRecord]:
        try:
            akshare = importlib.import_module("akshare")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "akshare is required when provider=akshare. Install it in the project environment first."
            ) from exc

        fetchers = [
            getattr(akshare, "stock_info_a_code_name", None),
            getattr(akshare, "stock_zh_a_spot_em", None),
        ]

        rows: list[dict[str, object]] = []
        for fetcher in fetchers:
            if not callable(fetcher):
                continue
            try:
                frame = fetcher()
            except Exception:
                continue
            rows = _sdk_result_to_rows(frame)
            if rows:
                break

        if not rows:
            raise RuntimeError("failed to fetch A-share stock list from AKShare.")

        records: list[StockListRecord] = []
        seen: set[str] = set()
        for row in rows:
            symbol = _clean(row.get("code") or row.get("代码") or row.get("symbol"))
            name = _clean(row.get("name") or row.get("名称"))
            if not symbol or not name:
                continue

            ts_code = _infer_ts_code_from_symbol(symbol)
            if ts_code in seen:
                continue
            seen.add(ts_code)

            exchange = _exchange_from_ts_code(ts_code)
            board = "主板"
            if symbol.startswith(("300", "301")):
                board = "创业板"
            elif symbol.startswith("688"):
                board = "科创板"
            elif symbol.startswith(("8", "4")):
                board = "北交所"

            records.append(
                StockListRecord(
                    ts_code=ts_code,
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    board=board,
                    list_status="L",
                )
            )

        return sorted(records, key=lambda item: item.symbol)


def create_stock_list_provider(
    name: str,
    *,
    source_path: Path | None = None,
    sample_path: Path | None = None,
    token: str | None = None,
    list_status: str = "L",
) -> StockListProvider:
    normalized_name = name.strip().lower()

    if normalized_name == "sample":
        return SampleStockListProvider(sample_path=sample_path)
    if normalized_name == "csv":
        if source_path is None:
            raise ValueError("source_path is required when provider=csv")
        return CSVStockListProvider(source_path=source_path)
    if normalized_name == "tushare":
        return TushareStockListProvider(token=token, list_status=list_status)
    if normalized_name == "akshare":
        return AKShareStockListProvider()

    raise ValueError(f"unsupported stock-list provider: {name}")
