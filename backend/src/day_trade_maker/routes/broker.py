from fastapi import APIRouter

from day_trade_maker.schemas import BrokerAccountSnapshot, BrokerStatus

router = APIRouter(prefix="/api/broker", tags=["broker"])


@router.get("/status", response_model=BrokerStatus)
def get_broker_status() -> BrokerStatus:
    return BrokerStatus(
        message="IBKR read-only scaffold is configured; no broker session is connected.",
    )


@router.get("/account", response_model=BrokerAccountSnapshot)
def get_broker_account() -> BrokerAccountSnapshot:
    return BrokerAccountSnapshot(
        message="IBKR account snapshot is read-only and empty until a broker session is connected.",
    )
