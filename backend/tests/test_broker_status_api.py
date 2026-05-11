from fastapi.testclient import TestClient

from day_trade_maker.api import app


def test_get_broker_status_exposes_safe_env_driven_ibkr_connection_config(monkeypatch) -> None:
    monkeypatch.setenv("DAY_TRADE_MAKER_IBKR_HOST", "127.0.0.1")
    monkeypatch.setenv("DAY_TRADE_MAKER_IBKR_PORT", "4002")
    monkeypatch.setenv("DAY_TRADE_MAKER_IBKR_CLIENT_ID", "17")
    client = TestClient(app)

    response = client.get("/api/broker/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured_host"] == "127.0.0.1"
    assert body["configured_port"] == 4002
    assert body["configured_client_id"] == 17
    assert body["connection_diagnostic"] == (
        "Configured for IBKR paper gateway at 127.0.0.1:4002 with client id 17; "
        "connection probing is read-only and not yet active."
    )
    assert body["read_only"] is True
    assert body["order_submission_enabled"] is False


def test_get_broker_status_returns_read_only_ibkr_paper_snapshot() -> None:
    client = TestClient(app)

    response = client.get("/api/broker/status")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "interactive_brokers"
    assert body["mode"] == "paper"
    assert body["connection_status"] == "not_connected"
    assert body["read_only"] is True
    assert body["order_submission_enabled"] is False
    assert body["account_id"] is None
    assert body["net_liquidation"] is None
    assert body["currency"] == "USD"
    assert body["configured_host"] == "127.0.0.1"
    assert body["configured_port"] == 4002
    assert body["configured_client_id"] == 1
    assert body["message"] == (
        "IBKR read-only scaffold is configured; no broker session is connected."
    )


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
