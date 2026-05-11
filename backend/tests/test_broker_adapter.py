import os
from collections.abc import Iterator
from contextlib import contextmanager

from day_trade_maker.broker import (
    EnvBrokerSettings,
    SocketConnectivityProbe,
    StaticAccountSnapshotReader,
    build_read_only_broker_status,
)


@contextmanager
def patched_environ(values: dict[str, str]) -> Iterator[None]:
    original = os.environ.copy()
    os.environ.clear()
    os.environ.update(values)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


def test_env_broker_settings_reads_safe_defaults() -> None:
    with patched_environ({}):
        settings = EnvBrokerSettings.from_environment()

    assert settings.host == "127.0.0.1"
    assert settings.port == 4002
    assert settings.client_id == 1
    assert settings.connectivity_probe_enabled is False
    assert settings.connectivity_probe_timeout_seconds == 1.0
    assert settings.account_snapshot_enabled is False


def test_env_broker_settings_reads_opt_in_probe_configuration() -> None:
    with patched_environ(
        {
            "DAY_TRADE_MAKER_IBKR_HOST": "192.0.2.10",
            "DAY_TRADE_MAKER_IBKR_PORT": "7497",
            "DAY_TRADE_MAKER_IBKR_CLIENT_ID": "17",
            "DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_ENABLED": "yes",
            "DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_TIMEOUT_SECONDS": "0.25",
            "DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_ENABLED": "true",
        }
    ):
        settings = EnvBrokerSettings.from_environment()

    assert settings.host == "192.0.2.10"
    assert settings.port == 7497
    assert settings.client_id == 17
    assert settings.connectivity_probe_enabled is True
    assert settings.connectivity_probe_timeout_seconds == 0.25
    assert settings.account_snapshot_enabled is True


def test_socket_connectivity_probe_disabled_default_never_calls_socket_factory() -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("socket factory should not be called when probe is disabled")

    settings = EnvBrokerSettings(connectivity_probe_enabled=False)
    probe = SocketConnectivityProbe(socket_factory=fail_if_called)

    result = probe.check(settings)

    assert result.probe_enabled is False
    assert result.probe_attempted is False
    assert result.probe_status == "unavailable"
    assert result.connection_status == "not_connected"
    assert result.read_only is True
    assert result.order_submission_enabled is False
    assert result.account_data_loaded is False


def test_socket_connectivity_probe_enabled_closes_reachable_socket() -> None:
    calls = []

    class FakeSocket:
        def close(self) -> None:
            calls.append("closed")

    def fake_socket_factory(address, timeout):
        calls.append((address, timeout))
        return FakeSocket()

    settings = EnvBrokerSettings(
        host="192.0.2.10",
        port=7497,
        connectivity_probe_enabled=True,
        connectivity_probe_timeout_seconds=0.25,
    )
    probe = SocketConnectivityProbe(socket_factory=fake_socket_factory)

    result = probe.check(settings)

    assert result.probe_enabled is True
    assert result.probe_attempted is True
    assert result.probe_status == "connected"
    assert result.connection_status == "connected"
    assert result.read_only is True
    assert result.order_submission_enabled is False
    assert result.account_data_loaded is False
    assert calls == [(('192.0.2.10', 7497), 0.25), "closed"]


def test_socket_connectivity_probe_enabled_reports_unreachable_without_raising() -> None:
    def fake_socket_factory(_address, timeout):
        raise TimeoutError("timed out")

    settings = EnvBrokerSettings(connectivity_probe_enabled=True)
    probe = SocketConnectivityProbe(socket_factory=fake_socket_factory)

    result = probe.check(settings)

    assert result.probe_enabled is True
    assert result.probe_attempted is True
    assert result.probe_status == "not_connected"
    assert result.connection_status == "not_connected"
    assert result.read_only is True
    assert result.order_submission_enabled is False
    assert result.account_data_loaded is False


def test_static_account_snapshot_reader_disabled_returns_empty_read_only_snapshot() -> None:
    settings = EnvBrokerSettings(account_snapshot_enabled=False)
    reader = StaticAccountSnapshotReader()

    snapshot = reader.read(settings)

    assert snapshot.account_snapshot_enabled is False
    assert snapshot.account_data_loaded is False
    assert snapshot.read_only is True
    assert snapshot.order_submission_enabled is False
    assert snapshot.account_id is None
    assert snapshot.balances == []
    assert snapshot.positions == []
    assert snapshot.message == (
        "IBKR account snapshot is read-only and disabled; no account or order operation "
        "was attempted."
    )


def test_static_account_snapshot_reader_enabled_returns_read_only_fixture_snapshot() -> None:
    settings = EnvBrokerSettings(account_snapshot_enabled=True)
    reader = StaticAccountSnapshotReader(
        account_id="DU1234567",
        balances=[{"tag": "NetLiquidation", "value": 25000.0, "currency": "USD"}],
        positions=[{"symbol": "AAPL", "quantity": 10, "market_value": 1900.0}],
    )

    snapshot = reader.read(settings)

    assert snapshot.account_snapshot_enabled is True
    assert snapshot.account_data_loaded is True
    assert snapshot.read_only is True
    assert snapshot.order_submission_enabled is False
    assert snapshot.account_id == "DU1234567"
    assert snapshot.balances == [{"tag": "NetLiquidation", "value": 25000.0, "currency": "USD"}]
    assert snapshot.positions == [{"symbol": "AAPL", "quantity": 10, "market_value": 1900.0}]
    assert snapshot.message == (
        "Read-only IBKR account snapshot loaded from the configured account reader; "
        "no order operation was attempted."
    )


def test_build_read_only_broker_status_uses_settings_without_probe_side_effects() -> None:
    settings = EnvBrokerSettings(host="192.0.2.10", port=7497, client_id=17)

    status = build_read_only_broker_status(settings)

    assert status.configured_host == "192.0.2.10"
    assert status.configured_port == 7497
    assert status.configured_client_id == 17
    assert status.connection_status == "not_connected"
    assert status.read_only is True
    assert status.order_submission_enabled is False
    assert status.connection_diagnostic == (
        "Configured for IBKR paper gateway at 192.0.2.10:7497 with client id 17; "
        "connection probing is read-only and not yet active."
    )
