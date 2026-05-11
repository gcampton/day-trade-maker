from __future__ import annotations

import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

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
