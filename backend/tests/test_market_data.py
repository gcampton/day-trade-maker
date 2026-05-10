from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from day_trade_maker.market_data import Candle, parse_candles_csv


def test_candle_accepts_valid_ohlcv_data() -> None:
    candle = Candle(
        timestamp=datetime(2026, 5, 10, 14, 30, tzinfo=UTC),
        open=100,
        high=102,
        low=99.5,
        close=101.25,
        volume=150_000,
    )

    assert candle.high == 102
    assert candle.volume == 150_000


def test_candle_rejects_invalid_ohlc_ranges() -> None:
    with pytest.raises(ValidationError):
        Candle(
            timestamp=datetime(2026, 5, 10, 14, 30, tzinfo=UTC),
            open=100,
            high=99,
            low=98,
            close=101,
            volume=150_000,
        )

    with pytest.raises(ValidationError):
        Candle(
            timestamp=datetime(2026, 5, 10, 14, 30, tzinfo=UTC),
            open=100,
            high=102,
            low=101,
            close=99,
            volume=150_000,
        )


def test_parse_candles_csv_returns_timestamp_sorted_candles() -> None:
    csv_text = """timestamp,open,high,low,close,volume
2026-05-10T14:35:00Z,101,103,100.5,102,200000
2026-05-10T14:30:00Z,100,101.5,99.5,101,150000
"""

    candles = parse_candles_csv(csv_text)

    assert [candle.close for candle in candles] == [101, 102]
    assert candles[0].timestamp < candles[1].timestamp


def test_parse_candles_csv_rejects_missing_required_columns() -> None:
    csv_text = """timestamp,open,high,low,close
2026-05-10T14:30:00Z,100,101.5,99.5,101
"""

    with pytest.raises(ValueError, match="Missing required columns: volume"):
        parse_candles_csv(csv_text)
