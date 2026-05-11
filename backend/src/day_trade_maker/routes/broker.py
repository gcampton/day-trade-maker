from fastapi import APIRouter, HTTPException, status

from day_trade_maker.broker import (
    EnvBrokerSettings,
    SocketConnectivityProbe,
    build_account_snapshot_reader,
    build_read_only_broker_status,
)
from day_trade_maker.schemas import (
    BrokerAccountSnapshot,
    BrokerCapabilities,
    BrokerConnectivityProbe,
    BrokerOrderSubmissionCapability,
    BrokerSafetySummary,
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
connectivity_probe = SocketConnectivityProbe()


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


@router.get(
    "/order-submission-capability",
    response_model=BrokerOrderSubmissionCapability,
)
def get_broker_order_submission_capability() -> BrokerOrderSubmissionCapability:
    return BrokerOrderSubmissionCapability(
        message=(
            "IBKR paper order submission is not implemented or enabled; "
            "this app only records audit-only paper order intents."
        )
    )


@router.get("/status", response_model=BrokerStatus)
def get_broker_status() -> BrokerStatus:
    return build_read_only_broker_status(EnvBrokerSettings.from_environment())


@router.get("/safety-summary", response_model=BrokerSafetySummary)
def get_broker_safety_summary() -> BrokerSafetySummary:
    settings = EnvBrokerSettings.from_environment()
    status_snapshot = build_read_only_broker_status(settings)
    account_snapshot = build_account_snapshot_reader(settings).read(settings)
    connectivity_snapshot = connectivity_probe.check(settings)
    capabilities_snapshot = get_broker_capabilities()
    order_submission_capability = get_broker_order_submission_capability()
    order_submission_enabled = any(
        [
            status_snapshot.order_submission_enabled,
            account_snapshot.order_submission_enabled,
            connectivity_snapshot.order_submission_enabled,
            capabilities_snapshot.order_submission_enabled,
            order_submission_capability.paper_broker_submission_enabled,
            order_submission_capability.live_broker_submission_enabled,
            order_submission_capability.broker_order_operation_available,
        ]
    )

    return BrokerSafetySummary(
        connection_status=status_snapshot.connection_status,
        read_only=(
            status_snapshot.read_only
            and account_snapshot.read_only
            and connectivity_snapshot.read_only
        ),
        order_submission_enabled=order_submission_enabled,
        order_intents_supported=order_submission_capability.order_intents_supported,
        paper_broker_submission_implemented=(
            order_submission_capability.paper_broker_submission_implemented
        ),
        paper_broker_submission_enabled=(
            order_submission_capability.paper_broker_submission_enabled
        ),
        live_broker_submission_implemented=(
            order_submission_capability.live_broker_submission_implemented
        ),
        live_broker_submission_enabled=order_submission_capability.live_broker_submission_enabled,
        broker_order_operation_available=(
            order_submission_capability.broker_order_operation_available
        ),
        account_snapshot_enabled=account_snapshot.account_snapshot_enabled,
        account_data_loaded=account_snapshot.account_data_loaded,
        account_reader=account_snapshot.account_reader,
        ibkr_client_dependency_available=account_snapshot.ibkr_client_dependency_available,
        account_id=account_snapshot.account_id,
        balances_count=len(account_snapshot.balances),
        positions_count=len(account_snapshot.positions),
        connectivity_probe_status=connectivity_snapshot.probe_status,
        connectivity_probe_enabled=connectivity_snapshot.probe_enabled,
        connectivity_probe_attempted=connectivity_snapshot.probe_attempted,
        configured_host=status_snapshot.configured_host,
        configured_port=status_snapshot.configured_port,
        configured_client_id=status_snapshot.configured_client_id,
        connectivity_timeout_seconds=connectivity_snapshot.timeout_seconds,
        status=status_snapshot,
        account=account_snapshot,
        connectivity_probe=connectivity_snapshot,
        capabilities=capabilities_snapshot,
        order_submission_capability=order_submission_capability,
        message=(
            "Broker safety summary is read-only and audit-only; no IBKR account, "
            "connectivity, or order-submission state permits broker orders."
        ),
    )


@router.get("/connectivity-probe", response_model=BrokerConnectivityProbe)
def get_broker_connectivity_probe() -> BrokerConnectivityProbe:
    return connectivity_probe.check(EnvBrokerSettings.from_environment())


@router.get("/account", response_model=BrokerAccountSnapshot)
def get_broker_account() -> BrokerAccountSnapshot:
    settings = EnvBrokerSettings.from_environment()
    return build_account_snapshot_reader(settings).read(settings)


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

    order_submission_capability = get_broker_order_submission_capability()
    if (
        order_submission_capability.paper_broker_submission_enabled
        or order_submission_capability.live_broker_submission_enabled
        or order_submission_capability.broker_order_operation_available
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audit-only order intents require broker order submission to be unavailable",
        )

    return paper_order_intent_store.create(
        payload=payload,
        checks=[
            "approved strategy",
            "passed risk check",
            "paper mode enabled",
            "explicit user confirmation",
            "broker order submission disabled",
        ],
        order_submission_capability=order_submission_capability,
    )
