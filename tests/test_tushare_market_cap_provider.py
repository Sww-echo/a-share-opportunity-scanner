from __future__ import annotations

import json
import unittest
from datetime import datetime
from unittest.mock import patch

from src.market_cap import providers as provider_module
from src.market_cap.providers import TushareMarketCapSnapshotProvider


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
    def __init__(
        self,
        *,
        trade_cal_rows: list[dict[str, object]] | None = None,
        daily_basic_rows: list[dict[str, object]] | None = None,
    ) -> None:
        self._DataApi__http_url = "http://api.tushare.pro"
        self._trade_cal_rows = trade_cal_rows or []
        self._daily_basic_rows = daily_basic_rows or []
        self.trade_cal_calls: list[dict[str, object]] = []
        self.daily_basic_calls: list[dict[str, object]] = []

    def trade_cal(self, **kwargs):
        self.trade_cal_calls.append(kwargs)
        return _FakeDataFrame(self._trade_cal_rows)

    def daily_basic(self, **kwargs):
        self.daily_basic_calls.append(kwargs)
        return _FakeDataFrame(self._daily_basic_rows)


class _FakeTushareModule:
    def __init__(self, client: _FakeTushareClient) -> None:
        self._client = client
        self.pro_api_calls: list[str | None] = []

    def pro_api(self, token: str | None):
        self.pro_api_calls.append(token)
        return self._client


class TushareMarketCapSnapshotProviderTests(unittest.TestCase):
    def test_fetch_snapshot_prefers_sdk_and_applies_http_url_override(self) -> None:
        client = _FakeTushareClient(
            daily_basic_rows=[
                {
                    "ts_code": "000001.SZ",
                    "trade_date": "20260326",
                    "total_mv": "12050000",
                    "circ_mv": "11920000",
                },
                {
                    "ts_code": "600519.SH",
                    "trade_date": "20260326",
                    "total_mv": "223000000",
                    "circ_mv": "223000000",
                },
            ]
        )
        tushare_module = _FakeTushareModule(client)
        provider = TushareMarketCapSnapshotProvider(
            token="test-token",
            trade_date="20260326",
        )

        with patch.object(
            provider_module.importlib,
            "import_module",
            return_value=tushare_module,
        ):
            with patch.object(provider_module.request, "urlopen") as mock_urlopen:
                records = provider.fetch_snapshot()

        mock_urlopen.assert_not_called()
        self.assertEqual(tushare_module.pro_api_calls, ["test-token"])
        self.assertEqual(client._DataApi__http_url, "http://118.89.66.41:8010/")
        self.assertEqual(client.trade_cal_calls, [])
        self.assertEqual(
            client.daily_basic_calls,
            [
                {
                    "trade_date": "20260326",
                    "fields": "ts_code,trade_date,total_mv,circ_mv",
                }
            ],
        )
        self.assertEqual([record.symbol for record in records], ["000001", "600519"])
        self.assertEqual(records[0].total_market_cap_billion_cny, 120.5)
        self.assertEqual(records[0].circulating_market_cap_billion_cny, 119.2)
        self.assertEqual(records[1].total_market_cap_billion_cny, 2230.0)

    def test_fetch_snapshot_uses_trade_cal_to_pick_previous_open_date_before_evening(
        self,
    ) -> None:
        captured_bodies: list[dict[str, object]] = []
        responses = iter(
            [
                {
                    "code": 0,
                    "msg": "",
                    "data": {
                        "fields": ["cal_date", "is_open"],
                        "items": [
                            ["20260325", "1"],
                            ["20260326", "1"],
                            ["20260327", "1"],
                        ],
                    },
                },
                {
                    "code": 0,
                    "msg": "",
                    "data": {
                        "fields": ["ts_code", "trade_date", "total_mv", "circ_mv"],
                        "items": [
                            ["000001.SZ", "20260326", "12050000", "11920000"],
                            ["600519.SH", "20260326", "223000000", "223000000"],
                            ["688981.SH", "20260326", None, "16500000"],
                        ],
                    },
                },
            ]
        )

        def fake_urlopen(request_obj, timeout: float):
            self.assertEqual(timeout, 30.0)
            captured_bodies.append(json.loads(request_obj.data.decode("utf-8")))
            return _FakeHTTPResponse(next(responses))

        provider = TushareMarketCapSnapshotProvider(
            token="test-token",
            now_provider=lambda: datetime(2026, 3, 27, 11, 0, tzinfo=provider_module.CHINA_TZ),
        )

        with patch.object(
            provider_module.importlib,
            "import_module",
            side_effect=ModuleNotFoundError,
        ):
            with patch.object(provider_module.request, "urlopen", side_effect=fake_urlopen):
                records = provider.fetch_snapshot()

        self.assertEqual(
            captured_bodies[0],
            {
                "api_name": "trade_cal",
                "token": "test-token",
                "params": {
                    "exchange": "SSE",
                    "start_date": "20260307",
                    "end_date": "20260327",
                },
                "fields": "cal_date,is_open",
            },
        )
        self.assertEqual(
            captured_bodies[1],
            {
                "api_name": "daily_basic",
                "token": "test-token",
                "params": {
                    "trade_date": "20260326",
                },
                "fields": "ts_code,trade_date,total_mv,circ_mv",
            },
        )
        self.assertEqual([record.ts_code for record in records], ["000001.SZ", "600519.SH"])
        self.assertTrue(all(record.as_of_date == "20260326" for record in records))
        self.assertEqual(records[0].total_market_cap_billion_cny, 120.5)
        self.assertEqual(records[1].total_market_cap_billion_cny, 2230.0)

    def test_fetch_snapshot_raises_runtime_error_on_tushare_error_code(self) -> None:
        provider = TushareMarketCapSnapshotProvider(
            token="bad-token",
            trade_date="20260326",
        )

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
                    "Tushare daily_basic request failed with code 2002: invalid token",
                ):
                    provider.fetch_snapshot()
