from threading import Event, Thread

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from day_trade_maker.api import app
from day_trade_maker.broker_orders import BrokerPaperOrderResult
from day_trade_maker.routes import broker as broker_routes
from day_trade_maker.schemas import (
    AuditSnapshot,
    BrokerOrderSubmissionCapability,
    PaperBrokerOrderSubmission,
    PaperBrokerOrderSubmissionCreate,
    PaperOrderIntent,
)


def test_paper_broker_submission_schema_is_separate_from_audit_only_intent() -> None:
    create_payload = PaperBrokerOrderSubmissionCreate(
        order_intent_id=7,
        user_confirmed=True,
        confirmation_phrase="SUBMIT IBKR PAPER ORDER",
    )

    submission = PaperBrokerOrderSubmission(
        id=3,
        order_intent_id=create_payload.order_intent_id,
        broker_order_id="12345",
        broker_response={"order_id": "12345", "status": "Submitted"},
        checks=["paper broker submission enabled", "live broker submission disabled"],
        message="IBKR paper order submitted; live trading remains disabled.",
    )

    assert submission.status == "submitted_to_paper_broker"
    assert submission.submitted_to_broker is True
    assert submission.current_execution_mode == "paper_broker"
    assert submission.paper_broker_submission_enabled is True
    assert submission.live_broker_submission_enabled is False

    intent = PaperOrderIntent(
        id=1,
        strategy_id=2,
        risk_check_id=3,
        symbol="AAPL",
        side="buy",
        quantity=10,
        order_type="market",
        paper_mode=True,
        user_confirmed=True,
        checks=["broker order submission disabled"],
        message="Paper order intent recorded for audit only; no IBKR order was submitted.",
    )
    assert intent.current_execution_mode == "audit_only"
    assert intent.submitted_to_broker is False


def test_audit_snapshot_defaults_include_empty_paper_broker_submission_history() -> None:
    snapshot = AuditSnapshot()

    assert snapshot.paper_broker_order_submissions == []


def test_paper_broker_submission_requires_non_empty_confirmation_phrase() -> None:
    try:
        PaperBrokerOrderSubmissionCreate(
            order_intent_id=1,
            user_confirmed=True,
            confirmation_phrase="",
        )
    except ValidationError as exc:
        assert "confirmation_phrase" in str(exc)
    else:
        raise AssertionError("empty confirmation phrase should fail validation")


def create_audit_only_order_intent(client: TestClient, *, reset: bool = True) -> dict:
    if reset:
        client.post("/api/audit/reset", json={"confirmation": "RESET LOCAL AUDIT STATE"})
    transcript_response = client.post(
        "/api/transcripts",
        json={
            "title": "Opening Range Breakout Paper Submit",
            "source_url": None,
            "creator": "Example Trader",
            "raw_text": (
                "I buy the first fifteen minute high breakout with volume "
                "and risk one percent."
            ),
            "symbols": ["AAPL"],
            "timeframes": ["5m"],
        },
    )
    transcript_id = transcript_response.json()["id"]
    strategy_response = client.post(f"/api/transcripts/{transcript_id}/extract-strategies")
    strategy_id = strategy_response.json()[0]["id"]
    client.post(
        f"/api/strategies/{strategy_id}/approve",
        json={"approved_by": "Garratt", "notes": "Reviewed strategy and risk rule."},
    )
    dataset_response = client.post(
        "/api/market-data/import-csv",
        json={
            "symbol": "AAPL",
            "timeframe": "5m",
            "csv_text": """timestamp,open,high,low,close,volume
2026-05-10T14:30:00Z,100,101,99,100.5,100000
2026-05-10T14:35:00Z,100.5,102,100.25,101.5,180000
2026-05-10T14:40:00Z,101.5,103,101,102.5,220000
""",
        },
    )
    backtest_response = client.post(
        "/api/backtests",
        json={
            "strategy_id": strategy_id,
            "dataset_id": dataset_response.json()["id"],
            "starting_cash": 10_000,
        },
    )
    risk_check_response = client.post(
        "/api/risk-checks",
        json={
            "strategy_id": strategy_id,
            "backtest_id": backtest_response.json()["id"],
            "paper_mode": True,
            "max_risk_percent": 1,
        },
    )
    order_intent_response = client.post(
        "/api/broker/order-intents",
        json={
            "strategy_id": strategy_id,
            "risk_check_id": risk_check_response.json()["id"],
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
            "order_type": "market",
            "paper_mode": True,
            "user_confirmed": True,
        },
    )
    assert order_intent_response.status_code == 201
    return order_intent_response.json()


def test_submit_paper_broker_order_rejects_default_disabled_capability() -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": True,
            "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "IBKR paper order submission is not enabled"


def test_submit_paper_broker_order_requires_confirmation() -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": False,
            "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Explicit user confirmation is required for paper broker submission"
    )


def test_submit_paper_broker_order_requires_exact_confirmation_phrase() -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": True,
            "confirmation_phrase": "submit",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Confirmation phrase must be SUBMIT IBKR PAPER ORDER"


def test_submit_paper_broker_order_rejects_confirmation_phrase_with_extra_whitespace() -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": True,
            "confirmation_phrase": " SUBMIT IBKR PAPER ORDER ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Confirmation phrase must be SUBMIT IBKR PAPER ORDER"


def test_submit_paper_broker_order_rejects_unknown_order_intent() -> None:
    client = TestClient(app)
    client.post("/api/audit/reset", json={"confirmation": "RESET LOCAL AUDIT STATE"})

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": 999999,
            "user_confirmed": True,
            "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order intent not found"


def test_submit_paper_broker_order_rejects_if_live_submission_is_enabled(monkeypatch) -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)

    def live_enabled_capability(*_args, **_kwargs) -> BrokerOrderSubmissionCapability:
        return BrokerOrderSubmissionCapability(
            current_execution_mode="paper_broker",
            paper_broker_submission_implemented=True,
            paper_broker_submission_enabled=True,
            live_broker_submission_enabled=True,
            broker_order_operation_available=True,
            message="Unsafe live capability should be rejected.",
        )

    monkeypatch.setattr(broker_routes, "build_order_submission_capability", live_enabled_capability)

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": True,
            "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Live broker submission must remain disabled"


def test_submit_paper_broker_order_rejects_limit_order_without_limit_price(
    monkeypatch,
) -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)
    snapshot = client.get("/api/audit/export").json()
    snapshot["paper_order_intents"][0]["order_type"] = "limit"
    snapshot["paper_order_intents"][0]["limit_price"] = None
    client.post("/api/audit/import", json=snapshot)

    def enabled_capability(*_args, **_kwargs) -> BrokerOrderSubmissionCapability:
        return BrokerOrderSubmissionCapability(
            current_execution_mode="paper_broker",
            paper_broker_submission_implemented=True,
            paper_broker_submission_enabled=True,
            broker_order_operation_available=True,
            message=(
                "IBKR paper order submission is enabled for the configured paper account; "
                "live trading remains disabled."
            ),
        )

    class FailIfCalledSubmitter:
        def submit(self, settings, request):
            raise AssertionError("invalid broker request must be rejected before submit")

    monkeypatch.setattr(broker_routes, "build_order_submission_capability", enabled_capability)
    monkeypatch.setattr(broker_routes, "paper_order_submitter", FailIfCalledSubmitter())

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": True,
            "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Limit paper orders require a positive limit price"


def test_submit_paper_broker_order_rejects_market_order_with_limit_price(monkeypatch) -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)
    snapshot = client.get("/api/audit/export").json()
    snapshot["paper_order_intents"][0]["order_type"] = "market"
    snapshot["paper_order_intents"][0]["limit_price"] = 100.25
    client.post("/api/audit/import", json=snapshot)

    def enabled_capability(*_args, **_kwargs) -> BrokerOrderSubmissionCapability:
        return BrokerOrderSubmissionCapability(
            current_execution_mode="paper_broker",
            paper_broker_submission_implemented=True,
            paper_broker_submission_enabled=True,
            broker_order_operation_available=True,
            message=(
                "IBKR paper order submission is enabled for the configured paper account; "
                "live trading remains disabled."
            ),
        )

    class FailIfCalledSubmitter:
        def submit(self, settings, request):
            raise AssertionError("invalid broker request must be rejected before submit")

    monkeypatch.setattr(broker_routes, "build_order_submission_capability", enabled_capability)
    monkeypatch.setattr(broker_routes, "paper_order_submitter", FailIfCalledSubmitter())

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": True,
            "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Market paper orders must not include a limit price"


def test_submit_paper_broker_order_success_creates_separate_audit_artifact(monkeypatch) -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)
    submitted_requests = []

    def enabled_capability(*_args, **_kwargs) -> BrokerOrderSubmissionCapability:
        return BrokerOrderSubmissionCapability(
            current_execution_mode="paper_broker",
            paper_broker_submission_implemented=True,
            paper_broker_submission_enabled=True,
            broker_order_operation_available=True,
            message=(
                "IBKR paper order submission is enabled for the configured paper account; "
                "live trading remains disabled."
            ),
        )

    class FakeSubmitter:
        def submit(self, settings, request):
            submitted_requests.append(request)
            return BrokerPaperOrderResult(
                broker_order_id="12345",
                status="Submitted",
                raw_response={"broker_order_id": "12345", "status": "Submitted"},
            )

    monkeypatch.setattr(broker_routes, "build_order_submission_capability", enabled_capability)
    monkeypatch.setattr(broker_routes, "paper_order_submitter", FakeSubmitter())

    response = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": True,
            "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["order_intent_id"] == order_intent["id"]
    assert body["submitted_to_broker"] is True
    assert body["broker_order_id"] == "12345"
    assert body["current_execution_mode"] == "paper_broker"
    assert body["paper_broker_submission_enabled"] is True
    assert body["live_broker_submission_enabled"] is False
    assert body["broker_response"] == {"broker_order_id": "12345", "status": "Submitted"}
    assert body["order_intent_snapshot"]["id"] == order_intent["id"]
    assert body["order_intent_snapshot"]["submitted_to_broker"] is False
    assert body["capability_snapshot"]["current_execution_mode"] == "paper_broker"
    assert body["capability_snapshot"]["live_broker_submission_enabled"] is False
    assert body["broker_request"] == {
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 10,
        "order_type": "market",
        "limit_price": None,
    }
    assert "approved strategy" in body["checks"]
    assert body["message"] == "IBKR paper order submitted; live trading remains disabled."
    assert submitted_requests[0].symbol == "AAPL"
    assert submitted_requests[0].side == "buy"

    history = client.get("/api/broker/paper-order-submissions").json()
    assert history[-1]["broker_order_id"] == "12345"
    assert history[-1]["order_intent_id"] == order_intent["id"]

    duplicate = client.post(
        "/api/broker/paper-order-submissions",
        json={
            "order_intent_id": order_intent["id"],
            "user_confirmed": True,
            "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == (
        "Paper broker submission already exists for this order intent"
    )


def test_concurrent_paper_broker_submissions_for_same_intent_call_submitter_once(
    monkeypatch,
) -> None:
    client = TestClient(app)
    order_intent = create_audit_only_order_intent(client)
    submit_started = Event()
    release_submit = Event()
    submitted_requests = []

    def enabled_capability(*_args, **_kwargs) -> BrokerOrderSubmissionCapability:
        return BrokerOrderSubmissionCapability(
            current_execution_mode="paper_broker",
            paper_broker_submission_implemented=True,
            paper_broker_submission_enabled=True,
            broker_order_operation_available=True,
            message=(
                "IBKR paper order submission is enabled for the configured paper account; "
                "live trading remains disabled."
            ),
        )

    class SlowFakeSubmitter:
        def submit(self, settings, request):
            submitted_requests.append(request)
            submit_started.set()
            assert release_submit.wait(timeout=2)
            return BrokerPaperOrderResult(
                broker_order_id="12345",
                status="Submitted",
                raw_response={"broker_order_id": "12345", "status": "Submitted"},
            )

    monkeypatch.setattr(broker_routes, "build_order_submission_capability", enabled_capability)
    monkeypatch.setattr(broker_routes, "paper_order_submitter", SlowFakeSubmitter())

    responses = []

    def post_submission() -> None:
        try:
            result = broker_routes.create_paper_broker_order_submission(
                PaperBrokerOrderSubmissionCreate(
                    order_intent_id=order_intent["id"],
                    user_confirmed=True,
                    confirmation_phrase="SUBMIT IBKR PAPER ORDER",
                )
            )
            responses.append((201, result))
        except HTTPException as exc:
            responses.append((exc.status_code, exc.detail))

    first_thread = Thread(target=post_submission)
    second_thread = Thread(target=post_submission)
    first_thread.start()
    assert submit_started.wait(timeout=2)
    second_thread.start()
    release_submit.set()
    first_thread.join(timeout=2)
    second_thread.join(timeout=2)

    assert len(submitted_requests) == 1
    assert sorted(status_code for status_code, _body in responses) == [201, 409]
    assert (
        409,
        "Paper broker submission already exists for this order intent",
    ) in responses


def test_list_paper_broker_submissions_returns_history_in_creation_order(monkeypatch) -> None:
    client = TestClient(app)
    first_intent = create_audit_only_order_intent(client)
    second_intent = create_audit_only_order_intent(client, reset=False)
    next_order_id = iter(["A-100", "B-200"])

    def enabled_capability(*_args, **_kwargs) -> BrokerOrderSubmissionCapability:
        return BrokerOrderSubmissionCapability(
            current_execution_mode="paper_broker",
            paper_broker_submission_implemented=True,
            paper_broker_submission_enabled=True,
            broker_order_operation_available=True,
            message=(
                "IBKR paper order submission is enabled for the configured paper account; "
                "live trading remains disabled."
            ),
        )

    class FakeSubmitter:
        def submit(self, settings, request):
            broker_order_id = next(next_order_id)
            return BrokerPaperOrderResult(
                broker_order_id=broker_order_id,
                status="Submitted",
                raw_response={"broker_order_id": broker_order_id, "status": "Submitted"},
            )

    monkeypatch.setattr(broker_routes, "build_order_submission_capability", enabled_capability)
    monkeypatch.setattr(broker_routes, "paper_order_submitter", FakeSubmitter())

    for order_intent in [first_intent, second_intent]:
        response = client.post(
            "/api/broker/paper-order-submissions",
            json={
                "order_intent_id": order_intent["id"],
                "user_confirmed": True,
                "confirmation_phrase": "SUBMIT IBKR PAPER ORDER",
            },
        )
        assert response.status_code == 201

    history = client.get("/api/broker/paper-order-submissions").json()

    assert [submission["order_intent_id"] for submission in history] == [
        first_intent["id"],
        second_intent["id"],
    ]
    assert [submission["broker_order_id"] for submission in history] == ["A-100", "B-200"]
    assert all(submission["current_execution_mode"] == "paper_broker" for submission in history)
    assert all(submission["live_broker_submission_enabled"] is False for submission in history)
