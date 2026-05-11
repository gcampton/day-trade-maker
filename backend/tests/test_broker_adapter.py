import os
from collections.abc import Iterator
from contextlib import contextmanager

from day_trade_maker.broker import (
    EnvBrokerSettings,
    IbkrReadOnlyAccountSnapshotReader,
    SocketConnectivityProbe,
    StaticAccountSnapshotReader,
    build_account_snapshot_reader,
    build_order_submission_capability,
    build_read_only_broker_status,
)
from day_trade_maker.schemas import BrokerAccountSnapshot


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
    assert settings.account_snapshot_reader == "static"
    assert settings.paper_order_submission_enabled is False
    assert settings.paper_order_submission_confirmation_phrase == "SUBMIT IBKR PAPER ORDER"
    assert settings.paper_account_id is None


def test_env_broker_settings_reads_opt_in_probe_configuration() -> None:
    with patched_environ(
        {
            "DAY_TRADE_MAKER_IBKR_HOST": "192.0.2.10",
            "DAY_TRADE_MAKER_IBKR_PORT": "7497",
            "DAY_TRADE_MAKER_IBKR_CLIENT_ID": "17",
            "DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_ENABLED": "yes",
            "DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_TIMEOUT_SECONDS": "0.25",
            "DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_ENABLED": "true",
            "DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_READER": "ib_async",
            "DAY_TRADE_MAKER_IBKR_PAPER_ORDER_SUBMISSION_ENABLED": "true",
            "DAY_TRADE_MAKER_IBKR_PAPER_ORDER_CONFIRMATION_PHRASE": "TYPE PAPER SUBMIT",
            "DAY_TRADE_MAKER_IBKR_PAPER_ACCOUNT_ID": "DU1234567",
        }
    ):
        settings = EnvBrokerSettings.from_environment()

    assert settings.host == "192.0.2.10"
    assert settings.port == 7497
    assert settings.client_id == 17
    assert settings.connectivity_probe_enabled is True
    assert settings.connectivity_probe_timeout_seconds == 0.25
    assert settings.account_snapshot_enabled is True
    assert settings.account_snapshot_reader == "ib_async"
    assert settings.paper_order_submission_enabled is True
    assert settings.paper_order_submission_confirmation_phrase == "TYPE PAPER SUBMIT"
    assert settings.paper_account_id == "DU1234567"


def test_order_submission_capability_disabled_default_stays_audit_only() -> None:
    capability = build_order_submission_capability(EnvBrokerSettings())

    assert capability.current_execution_mode == "audit_only"
    assert capability.order_intents_supported is True
    assert capability.paper_broker_submission_implemented is False
    assert capability.paper_broker_submission_enabled is False
    assert capability.live_broker_submission_implemented is False
    assert capability.live_broker_submission_enabled is False
    assert capability.broker_order_operation_available is False
    assert capability.message == (
        "IBKR paper order submission is not implemented or enabled; "
        "this app only records audit-only paper order intents."
    )


def test_order_submission_capability_requires_loaded_ib_async_account_snapshot() -> None:
    settings = EnvBrokerSettings(
        paper_order_submission_enabled=True,
        account_snapshot_enabled=False,
        account_snapshot_reader="static",
    )

    capability = build_order_submission_capability(settings)

    assert capability.current_execution_mode == "audit_only"
    assert capability.paper_broker_submission_implemented is True
    assert capability.paper_broker_submission_enabled is False
    assert capability.broker_order_operation_available is False
    assert capability.live_broker_submission_enabled is False
    assert capability.message == (
        "IBKR paper order submission is configured but unavailable because a loaded "
        "ib_async account snapshot is required; no broker order operation is available."
    )


def test_order_submission_capability_reports_available_only_for_loaded_paper_account() -> None:
    settings = EnvBrokerSettings(
        paper_order_submission_enabled=True,
        account_snapshot_enabled=True,
        account_snapshot_reader="ib_async",
        paper_account_id="DU1234567",
    )
    account_snapshot = BrokerAccountSnapshot(
        account_snapshot_enabled=True,
        account_data_loaded=True,
        account_reader="ib_async",
        ibkr_client_dependency_available=True,
        account_id="DU1234567",
        message=(
            "Read-only IBKR account snapshot loaded via ib_async; "
            "no order operation was attempted."
        ),
    )

    capability = build_order_submission_capability(settings, account_snapshot)

    assert capability.current_execution_mode == "paper_broker"
    assert capability.paper_broker_submission_implemented is True
    assert capability.paper_broker_submission_enabled is True
    assert capability.broker_order_operation_available is True
    assert capability.live_broker_submission_implemented is False
    assert capability.live_broker_submission_enabled is False
    assert capability.message == (
        "IBKR paper order submission is enabled for the configured paper account; "
        "live trading remains disabled."
    )


def test_order_submission_capability_requires_ib_async_dependency_available() -> None:
    settings = EnvBrokerSettings(
        paper_order_submission_enabled=True,
        account_snapshot_enabled=True,
        account_snapshot_reader="ib_async",
        paper_account_id="DU1234567",
    )
    account_snapshot = BrokerAccountSnapshot(
        account_snapshot_enabled=True,
        account_data_loaded=True,
        account_reader="ib_async",
        ibkr_client_dependency_available=False,
        account_id="DU1234567",
        message=(
            "Read-only IBKR account snapshot loaded via ib_async; "
            "no order operation was attempted."
        ),
    )

    capability = build_order_submission_capability(settings, account_snapshot)

    assert capability.current_execution_mode == "audit_only"
    assert capability.paper_broker_submission_implemented is True
    assert capability.paper_broker_submission_enabled is False
    assert capability.broker_order_operation_available is False
    assert capability.live_broker_submission_enabled is False
    assert capability.message == (
        "IBKR paper order submission is configured but unavailable because a loaded "
        "ib_async account snapshot is required; no broker order operation is available."
    )


def test_order_submission_capability_requires_verified_paper_account_identity() -> None:
    settings = EnvBrokerSettings(
        paper_order_submission_enabled=True,
        account_snapshot_enabled=True,
        account_snapshot_reader="ib_async",
        paper_account_id="DU1234567",
    )

    for account_id in [None, "U1234567", "DU7654321"]:
        account_snapshot = BrokerAccountSnapshot(
            account_snapshot_enabled=True,
            account_data_loaded=True,
            account_reader="ib_async",
            ibkr_client_dependency_available=True,
            account_id=account_id,
            message=(
                "Read-only IBKR account snapshot loaded via ib_async; "
                "no order operation was attempted."
            ),
        )

        capability = build_order_submission_capability(settings, account_snapshot)

        assert capability.current_execution_mode == "audit_only"
        assert capability.paper_broker_submission_enabled is False
        assert capability.broker_order_operation_available is False
        assert capability.live_broker_submission_enabled is False
        assert capability.message == (
            "IBKR paper order submission is configured but unavailable because the "
            "loaded account is not the configured IBKR paper account; no broker order "
            "operation is available."
        )


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
    assert snapshot.account_reader == "static"
    assert snapshot.ibkr_client_dependency_available is False
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
    assert snapshot.account_reader == "static"
    assert snapshot.ibkr_client_dependency_available is False
    assert snapshot.read_only is True
    assert snapshot.order_submission_enabled is False
    assert snapshot.account_id == "DU1234567"
    assert snapshot.balances == [{"tag": "NetLiquidation", "value": 25000.0, "currency": "USD"}]
    assert snapshot.positions == [{"symbol": "AAPL", "quantity": 10, "market_value": 1900.0}]
    assert snapshot.message == (
        "Read-only IBKR account snapshot loaded from the configured account reader; "
        "no order operation was attempted."
    )


def test_ibkr_read_only_account_reader_disabled_does_not_create_client() -> None:
    def fail_if_called():
        raise AssertionError(
            "IBKR client should not be created when account snapshots are disabled"
        )

    settings = EnvBrokerSettings(account_snapshot_enabled=False)
    reader = IbkrReadOnlyAccountSnapshotReader(ib_client_factory=fail_if_called)

    snapshot = reader.read(settings)

    assert snapshot.account_snapshot_enabled is False
    assert snapshot.account_data_loaded is False
    assert snapshot.account_reader == "ib_async"
    assert snapshot.ibkr_client_dependency_available is False
    assert snapshot.read_only is True
    assert snapshot.order_submission_enabled is False
    assert snapshot.balances == []
    assert snapshot.positions == []


def test_ibkr_read_only_account_reader_connects_reads_and_disconnects_without_orders() -> None:
    calls = []

    class AccountValue:
        account = "DU1234567"
        tag = "NetLiquidation"
        value = "25000.00"
        currency = "USD"

    class Contract:
        symbol = "AAPL"
        secType = "STK"
        exchange = "SMART"
        currency = "USD"

    class Position:
        account = "DU1234567"
        contract = Contract()
        position = 10
        avgCost = 190.5

    class FakeIbClient:
        def connect(self, host, port, clientId, readonly, timeout):
            calls.append(("connect", host, port, clientId, readonly, timeout))

        def managedAccounts(self):
            calls.append(("managedAccounts",))
            return ["DU1234567"]

        def accountSummary(self):
            calls.append(("accountSummary",))
            return [AccountValue()]

        def positions(self):
            calls.append(("positions",))
            return [Position()]

        def disconnect(self):
            calls.append(("disconnect",))

    settings = EnvBrokerSettings(
        host="192.0.2.10",
        port=7497,
        client_id=17,
        connectivity_probe_timeout_seconds=0.25,
        account_snapshot_enabled=True,
    )
    reader = IbkrReadOnlyAccountSnapshotReader(ib_client_factory=FakeIbClient)

    snapshot = reader.read(settings)

    assert snapshot.account_snapshot_enabled is True
    assert snapshot.account_data_loaded is True
    assert snapshot.account_reader == "ib_async"
    assert snapshot.ibkr_client_dependency_available is True
    assert snapshot.read_only is True
    assert snapshot.order_submission_enabled is False
    assert snapshot.account_id == "DU1234567"
    assert snapshot.balances == [
        {"account": "DU1234567", "tag": "NetLiquidation", "value": "25000.00", "currency": "USD"}
    ]
    assert snapshot.positions == [
        {
            "account": "DU1234567",
            "symbol": "AAPL",
            "security_type": "STK",
            "exchange": "SMART",
            "currency": "USD",
            "quantity": 10.0,
            "average_cost": 190.5,
        }
    ]
    assert snapshot.message == (
        "Read-only IBKR account snapshot loaded via ib_async; no order operation was attempted."
    )
    assert calls == [
        ("connect", "192.0.2.10", 7497, 17, True, 0.25),
        ("managedAccounts",),
        ("accountSummary",),
        ("positions",),
        ("disconnect",),
    ]


def test_ibkr_read_only_account_reader_disconnects_after_read_error() -> None:
    calls = []

    class FakeIbClient:
        def connect(self, host, port, clientId, readonly, timeout):
            calls.append(("connect", readonly))

        def managedAccounts(self):
            calls.append(("managedAccounts",))
            raise RuntimeError("account summary failed")

        def disconnect(self):
            calls.append(("disconnect",))

    settings = EnvBrokerSettings(account_snapshot_enabled=True)
    reader = IbkrReadOnlyAccountSnapshotReader(ib_client_factory=FakeIbClient)

    snapshot = reader.read(settings)

    assert snapshot.account_snapshot_enabled is True
    assert snapshot.account_data_loaded is False
    assert snapshot.account_reader == "ib_async"
    assert snapshot.ibkr_client_dependency_available is True
    assert snapshot.read_only is True
    assert snapshot.order_submission_enabled is False
    assert snapshot.balances == []
    assert snapshot.positions == []
    assert "could not load" in snapshot.message
    assert calls == [("connect", True), ("managedAccounts",), ("disconnect",)]


def test_ibkr_read_only_account_reader_reports_missing_optional_dependency() -> None:
    class MissingDependencyReader(IbkrReadOnlyAccountSnapshotReader):
        def _build_client(self):
            raise ImportError("ib_async missing")

    settings = EnvBrokerSettings(account_snapshot_enabled=True)
    reader = MissingDependencyReader()

    snapshot = reader.read(settings)

    assert snapshot.account_snapshot_enabled is True
    assert snapshot.account_data_loaded is False
    assert snapshot.account_reader == "ib_async"
    assert snapshot.ibkr_client_dependency_available is False
    assert snapshot.read_only is True
    assert snapshot.order_submission_enabled is False
    assert "requires optional ib_async" in snapshot.message


def test_build_account_snapshot_reader_selects_optional_ibkr_reader() -> None:
    static_settings = EnvBrokerSettings(account_snapshot_reader="static")
    ibkr_settings = EnvBrokerSettings(account_snapshot_reader="ib_async")

    assert isinstance(build_account_snapshot_reader(static_settings), StaticAccountSnapshotReader)
    assert isinstance(
        build_account_snapshot_reader(ibkr_settings), IbkrReadOnlyAccountSnapshotReader
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
