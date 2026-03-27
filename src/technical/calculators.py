from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .models import TechnicalSnapshotRecord
from .ohlcv_provider import OHLCVBar


@dataclass(frozen=True, slots=True)
class TechnicalSnapshotCalculationConfig:
    sma20_window: int = 20
    sma60_window: int = 60
    breakout_lookback_window: int = 20
    volume_ratio_window: int = 20


def calculate_technical_snapshot(
    history: Sequence[OHLCVBar],
    *,
    config: TechnicalSnapshotCalculationConfig | None = None,
) -> TechnicalSnapshotRecord:
    if not history:
        raise ValueError("ohlcv history is required")

    calculation_config = config or TechnicalSnapshotCalculationConfig()
    ordered_history = sorted(history, key=lambda item: item.trade_date)
    latest = ordered_history[-1]
    closes = [bar.close_price_cny for bar in ordered_history]
    highs = [bar.high_price_cny for bar in ordered_history]

    return TechnicalSnapshotRecord(
        ts_code=latest.ts_code,
        symbol=_last_non_empty(bar.symbol for bar in ordered_history)
        or _derive_symbol(latest.ts_code),
        name=_last_non_empty(bar.name for bar in ordered_history),
        close_price_cny=latest.close_price_cny,
        prev_close_price_cny=(
            ordered_history[-2].close_price_cny if len(ordered_history) >= 2 else None
        ),
        low_price_cny=latest.low_price_cny,
        sma20_cny=_trailing_average(closes, calculation_config.sma20_window),
        sma60_cny=_trailing_average(closes, calculation_config.sma60_window),
        prev_sma20_cny=_previous_trailing_average(
            closes,
            calculation_config.sma20_window,
        ),
        prev_sma60_cny=_previous_trailing_average(
            closes,
            calculation_config.sma60_window,
        ),
        breakout_level_cny=_previous_window_max(
            highs,
            calculation_config.breakout_lookback_window,
        ),
        volume_ratio_20d=_volume_ratio(
            ordered_history,
            calculation_config.volume_ratio_window,
        ),
        as_of_date=latest.trade_date,
    )


def _derive_symbol(ts_code: str) -> str:
    return ts_code.split(".", 1)[0]


def _last_non_empty(values: Iterable[str | None]) -> str | None:
    for value in reversed(tuple(values)):
        if value:
            return value
    return None


def _trailing_average(values: Sequence[float], window: int) -> float | None:
    if len(values) < window:
        return None

    trailing_values = values[-window:]
    return sum(trailing_values) / window


def _previous_trailing_average(values: Sequence[float], window: int) -> float | None:
    if len(values) < window + 1:
        return None

    trailing_values = values[-(window + 1) : -1]
    return sum(trailing_values) / window


def _previous_window_max(values: Sequence[float], window: int) -> float | None:
    if len(values) < window + 1:
        return None

    prior_values = values[-(window + 1) : -1]
    return max(prior_values)


def _volume_ratio(history: Sequence[OHLCVBar], window: int) -> float | None:
    if len(history) < window + 1:
        return None

    latest_volume = history[-1].volume
    prior_volumes = [bar.volume for bar in history[-(window + 1) : -1]]
    if latest_volume is None or any(volume is None for volume in prior_volumes):
        return None

    average_volume = sum(prior_volumes) / window
    if average_volume <= 0:
        return None

    return latest_volume / average_volume
