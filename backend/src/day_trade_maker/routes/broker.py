from fastapi import APIRouter, HTTPException, status

from day_trade_maker.schemas import (
    BrokerAccountSnapshot,
    BrokerCapabilities,
    BrokerStatus,
    PaperOrderIntent,
    PaperOrderIntentCreate,
)
from day_trade_maker.stores import (
    paper_order_intent_store,
    risk_check_store,
    strategy_candidate_store,
)

router = APIRouter(prefix="/api/broker", tags=["broker"])


@router.get("/order-intents", response_model=list[PaperOrderIntent])
def list_paper_order_intents() -> list[PaperOrderIntent]:
    return paper_order_intent_store.list()


@router.get("/capabilities", response_model=BrokerCapabilities)
def get_broker_capabilities() -> BrokerCapabilities:
    return BrokerCapabilities(
        message=(
            "Current broker mode records audit-only paper order intents; "
            "no IBKR orders are submitted."
        )
    )


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


@router.post(
    "/order-intents",
    response_model=PaperOrderIntent,
    status_code=status.HTTP_201_CREATED,
)
def create_paper_order_intent(payload: PaperOrderIntentCreate) -> PaperOrderIntent:
    strategy = strategy_candidate_store.get(payload.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    risk_check = risk_check_store.get(payload.risk_check_id)
    if risk_check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk check not found")

    if not payload.user_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit user confirmation is required for order intents",
        )

    if not payload.paper_mode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paper mode is required for order intents",
        )

    if strategy.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy must be approved before order intents",
        )

    if risk_check.strategy_id != strategy.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk check must match the selected strategy",
        )

    if risk_check.status != "passed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passed risk check is required for order intents",
        )

    return paper_order_intent_store.create(
        payload=payload,
        checks=[
            "approved strategy",
            "passed risk check",
            "paper mode enabled",
            "explicit user confirmation",
        ],
    )
