from datetime import UTC, datetime

from day_trade_maker.backtest import run_opening_range_breakout_backtest
from day_trade_maker.market_data import Candle


def test_opening_range_breakout_backtest_buys_breakout_and_exits_last_close() -> None:
    candles = [
        Candle(
            timestamp=datetime(2026, 5, 10, 14, 30, tzinfo=UTC),
            open=100,
            high=101,
            low=99,
            close=100.5,
            volume=100_000,
        ),
        Candle(
            timestamp=datetime(2026, 5, 10, 14, 35, tzinfo=UTC),
            open=100.5,
            high=102,
            low=100.25,
            close=101.5,
            volume=180_000,
        ),
        Candle(
            timestamp=datetime(2026, 5, 10, 14, 40, tzinfo=UTC),
            open=101.5,
            high=103,
            low=101,
            close=102.5,
            volume=220_000,
        ),
    ]

    result = run_opening_range_breakout_backtest(candles=candles, starting_cash=10_000)

    assert result.starting_cash == 10_000
    assert result.ending_cash == 10_001
    assert result.net_pnl == 1
    assert result.total_trades == 1
    assert result.win_rate == 1
    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 101.5
    assert result.trades[0].exit_price == 102.5
    assert result.markers[0].label == "Buy breakout"
    assert result.markers[1].label == "Exit close"


def test_opening_range_breakout_backtest_returns_no_trade_when_no_breakout() -> None:
    candles = [
        Candle(
            timestamp=datetime(2026, 5, 10, 14, 30, tzinfo=UTC),
            open=100,
            high=101,
            low=99,
            close=100.5,
            volume=100_000,
        ),
        Candle(
            timestamp=datetime(2026, 5, 10, 14, 35, tzinfo=UTC),
            open=100.5,
            high=100.75,
            low=99.25,
            close=100,
            volume=90_000,
        ),
    ]

    result = run_opening_range_breakout_backtest(candles=candles, starting_cash=10_000)

    assert result.total_trades == 0
    assert result.ending_cash == 10_000
    assert result.net_pnl == 0
    assert result.markers == []
