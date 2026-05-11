from __future__ import annotations

import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from day_trade_maker.schemas import (
    BrokerAccountSnapshot,
    BrokerConnectivityProbe,
    BrokerOrderSubmissionCapability,
    BrokerStatus,
)


class ClosableSocket(Protocol):
    def close(self) -> None: ...


SocketFactory = Callable[[tuple[str, int], float], ClosableSocket]


@dataclass(frozen=True)
class EnvBrokerSettings:
    host: str = "127.0.0.1"
    port: int = 4002
    client_id: int = 1
    connectivity_probe_enabled: bool = False
    connectivity_probe_timeout_seconds: float = 1.0
    account_snapshot_enabled: bool = False
    account_snapshot_reader: str = "static"
    paper_order_submission_enabled: bool = False
    paper_order_submission_confirmation_phrase: str = "SUBMIT IBKR PAPER ORDER"
    paper_order_submission_max_safety_summary_age_seconds: float = 60.0
    paper_account_id: str | None = None

    @classmethod
    def from_environment(cls) -> EnvBrokerSettings:
        return cls(
            host=os.environ.get("DAY_TRADE_MAKER_IBKR_HOST", "127.0.0.1"),
            port=int(os.environ.get("DAY_TRADE_MAKER_IBKR_PORT", "4002")),
            client_id=int(os.environ.get("DAY_TRADE_MAKER_IBKR_CLIENT_ID", "1")),
            connectivity_probe_enabled=_env_flag_enabled(
                "DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_ENABLED"
            ),
            connectivity_probe_timeout_seconds=float(
                os.environ.get("DAY_TRADE_MAKER_IBKR_CONNECTIVITY_PROBE_TIMEOUT_SECONDS", "1.0")
            ),
            account_snapshot_enabled=_env_flag_enabled(
                "DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_ENABLED"
            ),
            account_snapshot_reader=os.environ.get(
                "DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_READER", "static"
            ),
            paper_order_submission_enabled=_env_flag_enabled(
                "DAY_TRADE_MAKER_IBKR_PAPER_ORDER_SUBMISSION_ENABLED"
            ),
            paper_order_submission_confirmation_phrase=os.environ.get(
                "DAY_TRADE_MAKER_IBKR_PAPER_ORDER_CONFIRMATION_PHRASE",
                "SUBMIT IBKR PAPER ORDER",
            ),
            paper_order_submission_max_safety_summary_age_seconds=float(
                os.environ.get(
                    "DAY_TRADE_MAKER_IBKR_PAPER_ORDER_MAX_SAFETY_SUMMARY_AGE_SECONDS",
                    "60.0",
                )
            ),
            paper_account_id=_optional_env("DAY_TRADE_MAKER_IBKR_PAPER_ACCOUNT_ID"),
        )


def _env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


def _optional_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip().upper()
    return stripped or None


def _is_verified_ibkr_paper_account(
    settings: EnvBrokerSettings,
    account_snapshot: BrokerAccountSnapshot,
) -> bool:
    configured_account = settings.paper_account_id
    if account_snapshot.account_id:
        loaded_account = account_snapshot.account_id.strip().upper()
    else:
        loaded_account = None
    return (
        configured_account is not None
        and configured_account.startswith("DU")
        and loaded_account is not None
        and loaded_account.startswith("DU")
        and loaded_account == configured_account
    )


def build_read_only_broker_status(settings: EnvBrokerSettings) -> BrokerStatus:
    return BrokerStatus(
        configured_host=settings.host,
        configured_port=settings.port,
        configured_client_id=settings.client_id,
        connection_diagnostic=(
            f"Configured for IBKR paper gateway at {settings.host}:{settings.port} "
            f"with client id {settings.client_id}; "
            "connection probing is read-only and not yet active."
        ),
        message="IBKR read-only scaffold is configured; no broker session is connected.",
    )


def build_order_submission_capability(
    settings: EnvBrokerSettings,
    account_snapshot: BrokerAccountSnapshot | None = None,
) -> BrokerOrderSubmissionCapability:
    if not settings.paper_order_submission_enabled:
        return BrokerOrderSubmissionCapability(
            message=(
                "IBKR paper order submission is not implemented or enabled; "
                "this app only records audit-only paper order intents."
            )
        )

    if (
        not settings.account_snapshot_enabled
        or settings.account_snapshot_reader != "ib_async"
        or account_snapshot is None
        or not account_snapshot.account_data_loaded
        or account_snapshot.account_reader != "ib_async"
        or not account_snapshot.ibkr_client_dependency_available
    ):
        return BrokerOrderSubmissionCapability(
            paper_broker_submission_implemented=True,
            message=(
                "IBKR paper order submission is configured but unavailable because a loaded "
                "ib_async account snapshot is required; no broker order operation is available."
            ),
        )

    if not _is_verified_ibkr_paper_account(settings, account_snapshot):
        return BrokerOrderSubmissionCapability(
            paper_broker_submission_implemented=True,
            message=(
                "IBKR paper order submission is configured but unavailable because the "
                "loaded account is not the configured IBKR paper account; no broker order "
                "operation is available."
            ),
        )

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


class StaticAccountSnapshotReader:
    def __init__(
        self,
        account_id: str | None = None,
        balances: list[dict[str, str | float]] | None = None,
        positions: list[dict[str, str | float]] | None = None,
    ) -> None:
        self.account_id = account_id
        self.balances = balances or []
        self.positions = positions or []

    def read(self, settings: EnvBrokerSettings) -> BrokerAccountSnapshot:
        if not settings.account_snapshot_enabled:
            return BrokerAccountSnapshot(
                message=(
                    "IBKR account snapshot is read-only and disabled; no account or "
                    "order operation was attempted."
                ),
            )

        return BrokerAccountSnapshot(
            account_snapshot_enabled=True,
            account_data_loaded=True,
            account_reader="static",
            ibkr_client_dependency_available=False,
            account_id=self.account_id,
            balances=self.balances,
            positions=self.positions,
            message=(
                "Read-only IBKR account snapshot loaded from the configured account reader; "
                "no order operation was attempted."
            ),
        )


class IbkrReadOnlyAccountSnapshotReader:
    def __init__(self, ib_client_factory: Callable[[], Any] | None = None) -> None:
        self.ib_client_factory = ib_client_factory

    def read(self, settings: EnvBrokerSettings) -> BrokerAccountSnapshot:
        if not settings.account_snapshot_enabled:
            return BrokerAccountSnapshot(
                account_reader="ib_async",
                ibkr_client_dependency_available=False,
                message=(
                    "IBKR account snapshot is read-only and disabled; no account or "
                    "order operation was attempted."
                ),
            )

        try:
            ib_client = self._build_client()
        except ImportError:
            return BrokerAccountSnapshot(
                account_snapshot_enabled=True,
                account_reader="ib_async",
                ibkr_client_dependency_available=False,
                message=(
                    "Read-only IBKR account snapshot reader requires optional ib_async; "
                    "no account or order operation was attempted."
                ),
            )

        connected = False
        try:
            ib_client.connect(
                settings.host,
                settings.port,
                clientId=settings.client_id,
                readonly=True,
                timeout=settings.connectivity_probe_timeout_seconds,
            )
            connected = True
            accounts = list(ib_client.managedAccounts())
            balances = [_account_value_to_dict(value) for value in ib_client.accountSummary()]
            positions = [_position_to_dict(position) for position in ib_client.positions()]
            return BrokerAccountSnapshot(
                account_snapshot_enabled=True,
                account_data_loaded=True,
                account_reader="ib_async",
                ibkr_client_dependency_available=True,
                account_id=accounts[0] if accounts else None,
                balances=balances,
                positions=positions,
                message=(
                    "Read-only IBKR account snapshot loaded via ib_async; "
                    "no order operation was attempted."
                ),
            )
        except Exception:
            return BrokerAccountSnapshot(
                account_snapshot_enabled=True,
                account_reader="ib_async",
                ibkr_client_dependency_available=True,
                message=(
                    "Read-only IBKR account snapshot could not load account data; "
                    "no order operation was attempted."
                ),
            )
        finally:
            if connected:
                ib_client.disconnect()

    def _build_client(self) -> Any:
        if self.ib_client_factory is not None:
            return self.ib_client_factory()
        from ib_async import IB

        return IB()


def _account_value_to_dict(value: Any) -> dict[str, str | float]:
    return {
        "account": str(getattr(value, "account", "")),
        "tag": str(getattr(value, "tag", "")),
        "value": str(getattr(value, "value", "")),
        "currency": str(getattr(value, "currency", "")),
    }


def _position_to_dict(position: Any) -> dict[str, str | float]:
    contract = getattr(position, "contract", None)
    return {
        "account": str(getattr(position, "account", "")),
        "symbol": str(getattr(contract, "symbol", "")),
        "security_type": str(getattr(contract, "secType", "")),
        "exchange": str(getattr(contract, "exchange", "")),
        "currency": str(getattr(contract, "currency", "")),
        "quantity": float(getattr(position, "position", 0.0)),
        "average_cost": float(getattr(position, "avgCost", 0.0)),
    }


def build_account_snapshot_reader(settings: EnvBrokerSettings):
    if settings.account_snapshot_reader == "ib_async":
        return IbkrReadOnlyAccountSnapshotReader()
    return StaticAccountSnapshotReader()


class SocketConnectivityProbe:
    def __init__(self, socket_factory: SocketFactory | None = None) -> None:
        self.socket_factory = socket_factory

    def check(self, settings: EnvBrokerSettings) -> BrokerConnectivityProbe:
        if not settings.connectivity_probe_enabled:
            return BrokerConnectivityProbe(
                host=settings.host,
                port=settings.port,
                timeout_seconds=settings.connectivity_probe_timeout_seconds,
                message=(
                    "Read-only IBKR connectivity probe is not enabled; no socket, account, "
                    "or order operation was attempted."
                ),
            )

        probe_socket = None
        try:
            socket_factory = self.socket_factory or socket.create_connection
            probe_socket = socket_factory(
                (settings.host, settings.port),
                settings.connectivity_probe_timeout_seconds,
            )
        except OSError:
            return BrokerConnectivityProbe(
                probe_status="not_connected",
                connection_status="not_connected",
                probe_enabled=True,
                probe_attempted=True,
                host=settings.host,
                port=settings.port,
                timeout_seconds=settings.connectivity_probe_timeout_seconds,
                message=(
                    "Read-only IBKR socket reachability probe could not reach "
                    f"{settings.host}:{settings.port}; no account or order operation was attempted."
                ),
            )
        finally:
            if probe_socket is not None:
                probe_socket.close()

        return BrokerConnectivityProbe(
            probe_status="connected",
            connection_status="connected",
            probe_enabled=True,
            probe_attempted=True,
            host=settings.host,
            port=settings.port,
            timeout_seconds=settings.connectivity_probe_timeout_seconds,
            message=(
                "Read-only IBKR socket reachability probe reached "
                f"{settings.host}:{settings.port}; no account or order operation was attempted."
            ),
        )
