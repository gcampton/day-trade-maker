from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from day_trade_maker.market_data import Candle


class Trade(BaseModel):
    entry_timestamp: datetime
    exit_timestamp: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float


class BacktestMarker(BaseModel):
    timestamp: datetime
    price: float
    side: Literal["buy", "sell", "exit", "warning"]
    label: str


class BacktestResult(BaseModel):
    starting_cash: float
    ending_cash: float
    net_pnl: float
    total_trades: int
    win_rate: float
    trades: list[Trade]
    markers: list[BacktestMarker]


def run_opening_range_breakout_backtest(
    candles: list[Candle],
    starting_cash: float,
    quantity: float = 1,
) -> BacktestResult:
    if len(candles) < 2:
        return _empty_result(starting_cash)

    opening_range_high = candles[0].high
    entry_candle = next(
        (candle for candle in candles[1:] if candle.high > opening_range_high),
        None,
    )
    if entry_candle is None:
        return _empty_result(starting_cash)

    exit_candle = candles[-1]
    pnl = (exit_candle.close - entry_candle.close) * quantity
    ending_cash = starting_cash + pnl
    trade = Trade(
        entry_timestamp=entry_candle.timestamp,
        exit_timestamp=exit_candle.timestamp,
        entry_price=entry_candle.close,
        exit_price=exit_candle.close,
        quantity=quantity,
        pnl=pnl,
    )

    return BacktestResult(
        starting_cash=starting_cash,
        ending_cash=ending_cash,
        net_pnl=pnl,
        total_trades=1,
        win_rate=1 if pnl > 0 else 0,
        trades=[trade],
        markers=[
            BacktestMarker(
                timestamp=entry_candle.timestamp,
                price=entry_candle.close,
                side="buy",
                label="Buy breakout",
            ),
            BacktestMarker(
                timestamp=exit_candle.timestamp,
                price=exit_candle.close,
                side="exit",
                label="Exit close",
            ),
        ],
    )


def _empty_result(starting_cash: float) -> BacktestResult:
    return BacktestResult(
        starting_cash=starting_cash,
        ending_cash=starting_cash,
        net_pnl=0,
        total_trades=0,
        win_rate=0,
        trades=[],
        markers=[],
    )
