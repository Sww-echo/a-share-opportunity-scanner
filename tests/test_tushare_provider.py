from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from src.data_provider import providers as provider_module
from src.data_provider.providers import TushareStockListProvider


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeDataFrame:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def to_dict(self, orient: str = "records") -> list[dict[str, object]]:
        if orient != "records":
            raise AssertionError(f"unexpected orient: {orient}")
        return self._rows


class _FakeTushareClient:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self._DataApi__http_url = "http://api.tushare.pro"
        self.stock_basic_calls: list[dict[str, object]] = []

    def stock_basic(self, **kwargs):
        self.stock_basic_calls.append(kwargs)
        return _FakeDataFrame(self._rows)


class _FakeTushareModule:
    def __init__(self, client: _FakeTushareClient) -> None:
        self._client = client
        self.pro_api_calls: list[str | None] = []

    def pro_api(self, token: str | None):
        self.pro_api_calls.append(token)
        return self._client


class TushareStockListProviderTests(unittest.TestCase):
    def test_fetch_stock_list_prefers_sdk_and_applies_http_url_override(self) -> None:
        client = _FakeTushareClient(
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol": "000001",
                    "name": "平安银行",
                    "area": "深圳",
                    "industry": "银行",
                    "market": "主板",
                    "exchange": "SZSE",
                    "list_status": "L",
                    "list_date": "19910403",
                    "is_hs": "N",
                },
                {
                    "ts_code": "600000.SH",
                    "symbol": "600000",
                    "name": "浦发银行",
                    "area": "上海",
                    "industry": "银行",
                    "market": "主板",
                    "exchange": "",
                    "list_status": "L",
                    "list_date": "19991110",
                    "is_hs": "H",
                },
            ]
        )
        tushare_module = _FakeTushareModule(client)
        provider = TushareStockListProvider(token="test-token", list_status="L")

        with patch.object(
            provider_module.importlib,
            "import_module",
            return_value=tushare_module,
        ):
            with patch.object(provider_module.request, "urlopen") as mock_urlopen:
                records = provider.fetch_stock_list()

        mock_urlopen.assert_not_called()
        self.assertEqual(tushare_module.pro_api_calls, ["test-token"])
        self.assertEqual(client._DataApi__http_url, "http://118.89.66.41:8010/")
        self.assertEqual(
            client.stock_basic_calls,
            [
                {
                    "exchange": "",
                    "list_status": "L",
                    "fields": (
                        "ts_code,symbol,name,area,industry,market,exchange,"
                        "list_status,list_date,is_hs"
                    ),
                }
            ],
        )
        self.assertEqual([record.symbol for record in records], ["000001", "600000"])
        self.assertEqual(records[0].exchange, "SZSE")
        self.assertEqual(records[1].exchange, "SSE")
        self.assertEqual(records[1].board, "主板")

    def test_fetch_stock_list_posts_stock_basic_request_and_normalizes_rows(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(request_obj, timeout: float):
            captured["url"] = request_obj.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request_obj.header_items())
            captured["body"] = json.loads(request_obj.data.decode("utf-8"))
            return _FakeHTTPResponse(
                {
                    "code": 0,
                    "msg": "",
                    "data": {
                        "fields": [
                            "ts_code",
                            "symbol",
                            "name",
                            "area",
                            "industry",
                            "market",
                            "exchange",
                            "list_status",
                            "list_date",
                            "is_hs",
                        ],
                        "items": [
                            [
                                "000001.SZ",
                                "000001",
                                "平安银行",
                                "深圳",
                                "银行",
                                "主板",
                                "SZSE",
                                "L",
                                "19910403",
                                "N",
                            ],
                            [
                                "600000.SH",
                                "600000",
                                "浦发银行",
                                "上海",
                                "银行",
                                "主板",
                                "",
                                "L",
                                "19991110",
                                "H",
                            ],
                        ],
                    },
                }
            )

        provider = TushareStockListProvider(token="test-token", list_status="L")

        with patch.object(
            provider_module.importlib,
            "import_module",
            side_effect=ModuleNotFoundError,
        ):
            with patch.object(provider_module.request, "urlopen", side_effect=fake_urlopen):
                records = provider.fetch_stock_list()

        self.assertEqual(captured["url"], "http://api.tushare.pro")
        self.assertEqual(captured["timeout"], 30.0)
        self.assertEqual(captured["headers"]["Content-type"], "application/json")
        self.assertEqual(
            captured["body"],
            {
                "api_name": "stock_basic",
                "token": "test-token",
                "params": {
                    "exchange": "",
                    "list_status": "L",
                },
                "fields": (
                    "ts_code,symbol,name,area,industry,market,exchange,"
                    "list_status,list_date,is_hs"
                ),
            },
        )
        self.assertEqual([record.symbol for record in records], ["000001", "600000"])
        self.assertEqual(records[0].exchange, "SZSE")
        self.assertEqual(records[1].exchange, "SSE")
        self.assertEqual(records[1].board, "主板")

    def test_fetch_stock_list_raises_runtime_error_on_tushare_error_code(self) -> None:
        provider = TushareStockListProvider(token="bad-token")

        with patch.object(
            provider_module.importlib,
            "import_module",
            side_effect=ModuleNotFoundError,
        ):
            with patch.object(
                provider_module.request,
                "urlopen",
                return_value=_FakeHTTPResponse({"code": 2002, "msg": "invalid token"}),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "Tushare stock_basic request failed with code 2002: invalid token",
                ):
                    provider.fetch_stock_list()
