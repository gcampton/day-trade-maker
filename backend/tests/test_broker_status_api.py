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
