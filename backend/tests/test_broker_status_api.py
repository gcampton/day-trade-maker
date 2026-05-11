import socket

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


def test_get_broker_account_returns_read_only_empty_account_snapshot(monkeypatch) -> None:
    monkeypatch.delenv("DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_ENABLED", raising=False)
    client = TestClient(app)

    response = client.get("/api/broker/account")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "interactive_brokers"
    assert body["mode"] == "paper"
    assert body["read_only"] is True
    assert body["account_snapshot_enabled"] is False
    assert body["account_data_loaded"] is False
    assert body["positions"] == []
    assert body["balances"] == []
    assert body["order_submission_enabled"] is False
    assert body["message"] == (
        "IBKR account snapshot is read-only and disabled; no account or order operation "
        "was attempted."
    )


def test_get_broker_connectivity_probe_is_read_only_and_disabled_by_default(monkeypatch) -> None:
    def fail_if_socket_attempted(*_args, **_kwargs):
        raise AssertionError("socket probe must stay disabled unless explicitly enabled")

    monkeypatch.delenv("DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_ENABLED", raising=False)
    monkeypatch.setattr(socket, "create_connection", fail_if_socket_attempted)
    client = TestClient(app)

    response = client.get("/api/broker/connectivity-probe")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "interactive_brokers"
    assert body["probe_status"] == "unavailable"
    assert body["connection_status"] == "not_connected"
    assert body["read_only"] is True
    assert body["order_submission_enabled"] is False
    assert body["probe_enabled"] is False
    assert body["probe_attempted"] is False
    assert body["account_data_loaded"] is False
    assert body["host"] == "127.0.0.1"
    assert body["port"] == 4002
    assert body["timeout_seconds"] == 1.0
    assert body["message"] == (
        "Read-only IBKR connectivity probe is not enabled; no socket, account, "
        "or order operation was attempted."
    )


def test_get_broker_connectivity_probe_attempts_opt_in_read_only_socket_check(
    monkeypatch,
) -> None:
    socket_calls = []

    class FakeSocket:
        def close(self) -> None:
            socket_calls.append("closed")

    def fake_create_connection(address, timeout):
        socket_calls.append((address, timeout))
        return FakeSocket()

    monkeypatch.setenv("DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_ENABLED", "true")
    monkeypatch.setenv("DAY_TRADE_MAKER_IBKR_HOST", "192.0.2.10")
    monkeypatch.setenv("DAY_TRADE_MAKER_IBKR_PORT", "7497")
    monkeypatch.setenv("DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_TIMEOUT_SECONDS", "0.25")
    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    client = TestClient(app)

    response = client.get("/api/broker/connectivity-probe")

    assert response.status_code == 200
    body = response.json()
    assert body["probe_enabled"] is True
    assert body["probe_attempted"] is True
    assert body["probe_status"] == "connected"
    assert body["connection_status"] == "connected"
    assert body["read_only"] is True
    assert body["order_submission_enabled"] is False
    assert body["account_data_loaded"] is False
    assert body["host"] == "192.0.2.10"
    assert body["port"] == 7497
    assert body["timeout_seconds"] == 0.25
    assert body["message"] == (
        "Read-only IBKR socket reachability probe reached 192.0.2.10:7497; "
        "no account or order operation was attempted."
    )
    assert socket_calls == [(('192.0.2.10', 7497), 0.25), "closed"]


def test_get_broker_connectivity_probe_reports_opt_in_socket_failure(monkeypatch) -> None:
    def fake_create_connection(_address, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setenv("DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_ENABLED", "1")
    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    client = TestClient(app)

    response = client.get("/api/broker/connectivity-probe")

    assert response.status_code == 200
    body = response.json()
    assert body["probe_enabled"] is True
    assert body["probe_attempted"] is True
    assert body["probe_status"] == "not_connected"
    assert body["connection_status"] == "not_connected"
    assert body["read_only"] is True
    assert body["order_submission_enabled"] is False
    assert body["account_data_loaded"] is False
    assert body["message"] == (
        "Read-only IBKR socket reachability probe could not reach 127.0.0.1:4002; "
        "no account or order operation was attempted."
    )


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
