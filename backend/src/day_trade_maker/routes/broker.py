import os

from fastapi import APIRouter, HTTPException, status

from day_trade_maker.schemas import (
    BrokerAccountSnapshot,
    BrokerCapabilities,
    BrokerConnectivityProbe,
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


def ibkr_host() -> str:
    return os.environ.get("DAY_TRADE_MAKER_IBKR_HOST", "127.0.0.1")


def ibkr_port() -> int:
    return int(os.environ.get("DAY_TRADE_MAKER_IBKR_PORT", "4002"))


def build_read_only_connectivity_probe() -> BrokerConnectivityProbe:
    return BrokerConnectivityProbe(
        host=ibkr_host(),
        port=ibkr_port(),
        message=(
            "Read-only IBKR connectivity probe is not enabled; no socket, account, "
            "or order operation was attempted."
        ),
    )


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
    host = ibkr_host()
    port = ibkr_port()
    client_id = int(os.environ.get("DAY_TRADE_MAKER_IBKR_CLIENT_ID", "1"))

    return BrokerStatus(
        configured_host=host,
        configured_port=port,
        configured_client_id=client_id,
        connection_diagnostic=(
            f"Configured for IBKR paper gateway at {host}:{port} with client id {client_id}; "
            "connection probing is read-only and not yet active."
        ),
        message="IBKR read-only scaffold is configured; no broker session is connected.",
    )


@router.get("/connectivity-probe", response_model=BrokerConnectivityProbe)
def get_broker_connectivity_probe() -> BrokerConnectivityProbe:
    return build_read_only_connectivity_probe()


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
