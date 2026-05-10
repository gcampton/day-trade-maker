from fastapi import APIRouter, HTTPException, status

from day_trade_maker.backtest import run_opening_range_breakout_backtest
from day_trade_maker.schemas import BacktestCreate, BacktestRun
from day_trade_maker.stores import backtest_store, market_data_store, strategy_candidate_store

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


@router.post("", response_model=BacktestRun, status_code=status.HTTP_201_CREATED)
def create_backtest(payload: BacktestCreate) -> BacktestRun:
    strategy = strategy_candidate_store.get(payload.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    dataset = market_data_store.get(payload.dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market dataset not found",
        )

    result = run_opening_range_breakout_backtest(
        candles=dataset.candles,
        starting_cash=payload.starting_cash,
    )
    return backtest_store.create(
        strategy_id=strategy.id,
        dataset_id=dataset.id,
        result=result,
    )
