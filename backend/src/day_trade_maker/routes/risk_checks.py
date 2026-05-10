from fastapi import APIRouter, HTTPException, status

from day_trade_maker.schemas import RiskCheckCreate, RiskCheckRun
from day_trade_maker.stores import backtest_store, risk_check_store, strategy_candidate_store

router = APIRouter(prefix="/api/risk-checks", tags=["risk-checks"])


@router.post("", response_model=RiskCheckRun, status_code=status.HTTP_201_CREATED)
def create_risk_check(payload: RiskCheckCreate) -> RiskCheckRun:
    strategy = strategy_candidate_store.get(payload.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    backtest = backtest_store.get(payload.backtest_id)
    if backtest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest not found")

    checks: list[str] = []
    failures: list[str] = []

    if strategy.status == "approved":
        checks.append("approved strategy")
    else:
        failures.append("strategy must be approved before broker workflows")

    if backtest.strategy_id == strategy.id:
        checks.append("backtest matches strategy")
    else:
        failures.append("backtest must match the selected strategy")

    if backtest.result.total_trades > 0:
        checks.append("backtest produced trades")
    else:
        failures.append("backtest must produce at least one trade")

    if payload.paper_mode:
        checks.append("paper mode enabled")
    else:
        failures.append("paper mode must be enabled")

    if payload.max_risk_percent <= 1:
        checks.append("max risk within 1% limit")

    return risk_check_store.create(
        strategy_id=strategy.id,
        backtest_id=backtest.id,
        paper_mode=payload.paper_mode,
        max_risk_percent=payload.max_risk_percent,
        checks=checks,
        failures=failures,
    )
