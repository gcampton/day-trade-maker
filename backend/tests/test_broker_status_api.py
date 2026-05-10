from fastapi.testclient import TestClient

from day_trade_maker.api import app


def test_get_broker_status_returns_read_only_ibkr_paper_snapshot() -> None:
    client = TestClient(app)

    response = client.get("/api/broker/status")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "provider": "interactive_brokers",
        "mode": "paper",
        "connection_status": "not_connected",
        "read_only": True,
        "order_submission_enabled": False,
        "account_id": None,
        "net_liquidation": None,
        "currency": "USD",
        "message": "IBKR read-only scaffold is configured; no broker session is connected.",
    }


def test_get_broker_account_returns_read_only_empty_account_snapshot() -> None:
    client = TestClient(app)

    response = client.get("/api/broker/account")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "interactive_brokers"
    assert body["mode"] == "paper"
    assert body["read_only"] is True
    assert body["positions"] == []
    assert body["balances"] == []
    assert body["order_submission_enabled"] is False


def test_get_broker_capabilities_separates_audit_intents_from_future_execution() -> None:
    client = TestClient(app)

    response = client.get("/api/broker/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "interactive_brokers"
    assert body["current_execution_mode"] == "audit_only"
    assert body["supports_order_intents"] is True
    assert body["supports_paper_broker_submission"] is False
    assert body["supports_live_broker_submission"] is False
    assert body["order_submission_enabled"] is False
    assert body["message"] == (
        "Current broker mode records audit-only paper order intents; no IBKR orders are submitted."
    )
