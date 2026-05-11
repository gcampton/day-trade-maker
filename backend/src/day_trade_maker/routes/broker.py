from threading import Lock

from fastapi import APIRouter, HTTPException, status

from day_trade_maker.broker import (
    EnvBrokerSettings,
    SocketConnectivityProbe,
    build_account_snapshot_reader,
    build_order_submission_capability,
    build_read_only_broker_status,
)
from day_trade_maker.broker_orders import (
    BrokerPaperOrderRequest,
    IbAsyncPaperOrderSubmitter,
    PaperOrderSubmissionUnavailable,
)
from day_trade_maker.schemas import (
    BrokerAccountSnapshot,
    BrokerCapabilities,
    BrokerConnectivityProbe,
    BrokerOrderSubmissionCapability,
    BrokerSafetySummary,
    BrokerStatus,
    PaperBrokerOrderSubmission,
    PaperBrokerOrderSubmissionCreate,
    PaperOrderIntent,
    PaperOrderIntentCreate,
)
from day_trade_maker.stores import (
    paper_broker_order_submission_store,
    paper_order_intent_store,
    risk_check_store,
    strategy_candidate_store,
)

router = APIRouter(prefix="/api/broker", tags=["broker"])
connectivity_probe = SocketConnectivityProbe()
paper_order_submitter = IbAsyncPaperOrderSubmitter()
_submission_locks_guard = Lock()
_submission_locks: dict[int, Lock] = {}


@router.get("/order-intents", response_model=list[PaperOrderIntent])
def list_paper_order_intents() -> list[PaperOrderIntent]:
    return paper_order_intent_store.list()


@router.get("/paper-order-submissions", response_model=list[PaperBrokerOrderSubmission])
def list_paper_broker_order_submissions() -> list[PaperBrokerOrderSubmission]:
    return paper_broker_order_submission_store.list()


@router.post(
    "/paper-order-submissions",
    response_model=PaperBrokerOrderSubmission,
    status_code=status.HTTP_201_CREATED,
)
def create_paper_broker_order_submission(
    payload: PaperBrokerOrderSubmissionCreate,
) -> PaperBrokerOrderSubmission:
    settings = EnvBrokerSettings.from_environment()
    order_intent = paper_order_intent_store.get(payload.order_intent_id)
    if order_intent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order intent not found")

    if not payload.user_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit user confirmation is required for paper broker submission",
        )

    if payload.confirmation_phrase != settings.paper_order_submission_confirmation_phrase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Confirmation phrase must be "
                f"{settings.paper_order_submission_confirmation_phrase}"
            ),
        )

    with _submission_lock(order_intent.id):
        return _create_paper_broker_order_submission_with_lock(settings, order_intent)


def _create_paper_broker_order_submission_with_lock(
    settings: EnvBrokerSettings,
    order_intent: PaperOrderIntent,
) -> PaperBrokerOrderSubmission:
    _validate_source_order_intent_for_paper_broker_submission(order_intent)
    if any(
        submission.order_intent_id == order_intent.id
        for submission in paper_broker_order_submission_store.list()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper broker submission already exists for this order intent",
        )

    account_snapshot = None
    if settings.paper_order_submission_enabled:
        account_snapshot = build_account_snapshot_reader(settings).read(settings)
    capability = build_order_submission_capability(settings, account_snapshot)
    if capability.live_broker_submission_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Live broker submission must remain disabled",
        )
    if not (
        capability.paper_broker_submission_enabled
        and capability.broker_order_operation_available
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="IBKR paper order submission is not enabled",
        )

    request = _build_validated_broker_paper_order_request(order_intent)
    broker_request_snapshot = {
        "symbol": request.symbol,
        "side": request.side,
        "quantity": request.quantity,
        "order_type": request.order_type,
        "limit_price": request.limit_price,
    }
    try:
        broker_result = paper_order_submitter.submit(settings, request)
    except PaperOrderSubmissionUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return paper_broker_order_submission_store.create(
        order_intent_id=order_intent.id,
        broker_order_id=broker_result.broker_order_id,
        broker_response=broker_result.raw_response,
        order_intent_snapshot=order_intent,
        capability_snapshot=capability,
        broker_request=broker_request_snapshot,
        checks=[
            "approved strategy",
            "passed risk check",
            "source order intent confirmed audit-only",
            "paper broker submission enabled",
            "live broker submission disabled",
        ],
        message="IBKR paper order submitted; live trading remains disabled.",
    )


def _submission_lock(order_intent_id: int) -> Lock:
    with _submission_locks_guard:
        if order_intent_id not in _submission_locks:
            _submission_locks[order_intent_id] = Lock()
        return _submission_locks[order_intent_id]


def _build_validated_broker_paper_order_request(
    order_intent: PaperOrderIntent,
) -> BrokerPaperOrderRequest:
    if order_intent.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paper order quantity must be positive",
        )
    if (
        order_intent.order_type == "limit"
        and (order_intent.limit_price is None or order_intent.limit_price <= 0)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit paper orders require a positive limit price",
        )
    if order_intent.order_type == "market" and order_intent.limit_price is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Market paper orders must not include a limit price",
        )
    return BrokerPaperOrderRequest(
        symbol=order_intent.symbol,
        side=order_intent.side,
        quantity=order_intent.quantity,
        order_type=order_intent.order_type,
        limit_price=order_intent.limit_price,
    )


def _validate_source_order_intent_for_paper_broker_submission(
    order_intent: PaperOrderIntent,
) -> None:
    if not order_intent.paper_mode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source order intent must be paper mode",
        )
    if order_intent.submitted_to_broker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source order intent has already been submitted to a broker",
        )

    strategy = strategy_candidate_store.get(order_intent.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if strategy.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy must be approved before paper broker submission",
        )

    risk_check = risk_check_store.get(order_intent.risk_check_id)
    if risk_check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk check not found")
    if risk_check.strategy_id != strategy.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk check must match the selected strategy",
        )
    if risk_check.status != "passed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passed risk check is required for paper broker submission",
        )


@router.get("/capabilities", response_model=BrokerCapabilities)
def get_broker_capabilities() -> BrokerCapabilities:
    settings = EnvBrokerSettings.from_environment()
    account_snapshot = None
    if settings.paper_order_submission_enabled:
        account_snapshot = build_account_snapshot_reader(settings).read(settings)
    order_submission_capability = build_order_submission_capability(settings, account_snapshot)
    return _broker_capabilities_from_order_submission(order_submission_capability)


def _broker_capabilities_from_order_submission(
    order_submission_capability: BrokerOrderSubmissionCapability,
) -> BrokerCapabilities:
    if order_submission_capability.paper_broker_submission_enabled:
        return BrokerCapabilities(
            current_execution_mode=order_submission_capability.current_execution_mode,
            supports_paper_broker_submission=True,
            supports_live_broker_submission=(
                order_submission_capability.live_broker_submission_enabled
            ),
            order_submission_enabled=True,
            message=(
                "Current broker mode permits IBKR paper-account order submission only; "
                "live trading remains disabled."
            ),
        )
    return BrokerCapabilities(
        current_execution_mode=order_submission_capability.current_execution_mode,
        supports_paper_broker_submission=False,
        supports_live_broker_submission=False,
        order_submission_enabled=False,
        message=(
            "Current broker mode records audit-only paper order intents; "
            "no IBKR orders are submitted."
        ),
    )


@router.get(
    "/order-submission-capability",
    response_model=BrokerOrderSubmissionCapability,
)
def get_broker_order_submission_capability() -> BrokerOrderSubmissionCapability:
    settings = EnvBrokerSettings.from_environment()
    account_snapshot = None
    if settings.paper_order_submission_enabled:
        account_snapshot = build_account_snapshot_reader(settings).read(settings)
    return build_order_submission_capability(settings, account_snapshot)


@router.get("/status", response_model=BrokerStatus)
def get_broker_status() -> BrokerStatus:
    return build_read_only_broker_status(EnvBrokerSettings.from_environment())


@router.get("/safety-summary", response_model=BrokerSafetySummary)
def get_broker_safety_summary() -> BrokerSafetySummary:
    settings = EnvBrokerSettings.from_environment()
    status_snapshot = build_read_only_broker_status(settings)
    account_snapshot = build_account_snapshot_reader(settings).read(settings)
    connectivity_snapshot = connectivity_probe.check(settings)
    order_submission_capability = build_order_submission_capability(settings, account_snapshot)
    capabilities_snapshot = _broker_capabilities_from_order_submission(order_submission_capability)
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
    if order_submission_capability.paper_broker_submission_enabled:
        summary_message = (
            "Broker safety summary permits IBKR paper-account order submission only; "
            "live trading remains disabled."
        )
    else:
        summary_message = (
            "Broker safety summary is read-only and audit-only; no IBKR account, "
            "connectivity, or order-submission state permits broker orders."
        )
    read_only = (
        status_snapshot.read_only
        and account_snapshot.read_only
        and connectivity_snapshot.read_only
        and not order_submission_capability.broker_order_operation_available
        and not order_submission_capability.paper_broker_submission_enabled
        and not order_submission_capability.live_broker_submission_enabled
    )

    return BrokerSafetySummary(
        current_execution_mode=order_submission_capability.current_execution_mode,
        connection_status=status_snapshot.connection_status,
        read_only=read_only,
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
        message=summary_message,
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
