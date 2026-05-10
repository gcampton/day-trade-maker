from fastapi.testclient import TestClient

from day_trade_maker.api import app


def create_approved_strategy_backtest_and_risk_check(client: TestClient) -> tuple[int, int]:
    transcript_response = client.post(
        "/api/transcripts",
        json={
            "title": "Opening Range Breakout",
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
    dataset_id = dataset_response.json()["id"]
    backtest_response = client.post(
        "/api/backtests",
        json={"strategy_id": strategy_id, "dataset_id": dataset_id, "starting_cash": 10_000},
    )
    backtest_id = backtest_response.json()["id"]
    risk_check_response = client.post(
        "/api/risk-checks",
        json={
            "strategy_id": strategy_id,
            "backtest_id": backtest_id,
            "paper_mode": True,
            "max_risk_percent": 1,
        },
    )
    risk_check_id = risk_check_response.json()["id"]
    return strategy_id, risk_check_id


def test_create_paper_order_intent_records_audit_artifact_without_broker_submission() -> None:
    client = TestClient(app)
    strategy_id, risk_check_id = create_approved_strategy_backtest_and_risk_check(client)

    response = client.post(
        "/api/broker/order-intents",
        json={
            "strategy_id": strategy_id,
            "risk_check_id": risk_check_id,
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
            "order_type": "market",
            "paper_mode": True,
            "user_confirmed": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "created_not_submitted"
    assert body["strategy_id"] == strategy_id
    assert body["risk_check_id"] == risk_check_id
    assert body["symbol"] == "AAPL"
    assert body["side"] == "buy"
    assert body["quantity"] == 10
    assert body["paper_mode"] is True
    assert body["user_confirmed"] is True
    assert body["submitted_to_broker"] is False
    assert body["order_submission_enabled"] is False
    assert "approved strategy" in body["checks"]
    assert "passed risk check" in body["checks"]
    assert "explicit user confirmation" in body["checks"]
    assert body["message"] == (
        "Paper order intent recorded for audit only; no IBKR order was submitted."
    )


def test_order_intent_rejects_missing_confirmation_before_audit_creation() -> None:
    client = TestClient(app)
    strategy_id, risk_check_id = create_approved_strategy_backtest_and_risk_check(client)

    response = client.post(
        "/api/broker/order-intents",
        json={
            "strategy_id": strategy_id,
            "risk_check_id": risk_check_id,
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
            "order_type": "market",
            "paper_mode": True,
            "user_confirmed": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Explicit user confirmation is required for order intents"


def test_order_intent_rejects_unknown_or_failed_safety_gate() -> None:
    client = TestClient(app)
    strategy_id, _risk_check_id = create_approved_strategy_backtest_and_risk_check(client)

    response = client.post(
        "/api/broker/order-intents",
        json={
            "strategy_id": strategy_id,
            "risk_check_id": 999999,
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
            "order_type": "market",
            "paper_mode": True,
            "user_confirmed": True,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Risk check not found"


def test_list_order_intents_returns_audit_history_without_broker_submission() -> None:
    client = TestClient(app)
    strategy_id, risk_check_id = create_approved_strategy_backtest_and_risk_check(client)
    client.post(
        "/api/broker/order-intents",
        json={
            "strategy_id": strategy_id,
            "risk_check_id": risk_check_id,
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
            "order_type": "market",
            "paper_mode": True,
            "user_confirmed": True,
        },
    )
    client.post(
        "/api/broker/order-intents",
        json={
            "strategy_id": strategy_id,
            "risk_check_id": risk_check_id,
            "symbol": "TSLA",
            "side": "sell",
            "quantity": 3,
            "order_type": "market",
            "paper_mode": True,
            "user_confirmed": True,
        },
    )

    response = client.get("/api/broker/order-intents")

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2
    assert body[-2]["symbol"] == "AAPL"
    assert body[-1]["symbol"] == "TSLA"
    assert body[-1]["submitted_to_broker"] is False
    assert body[-1]["order_submission_enabled"] is False
