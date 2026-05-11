from __future__ import annotations

import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from day_trade_maker.schemas import BrokerAccountSnapshot, BrokerConnectivityProbe, BrokerStatus


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
        )


def _env_flag_enabled(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes", "on"}


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
