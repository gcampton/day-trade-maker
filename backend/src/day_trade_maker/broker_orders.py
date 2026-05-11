from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from day_trade_maker.broker import EnvBrokerSettings

BrokerResponseValue = str | int | float | bool | None


@dataclass(frozen=True)
class BrokerPaperOrderRequest:
    symbol: str
    side: str
    quantity: int
    order_type: str
    limit_price: float | None = None


@dataclass(frozen=True)
class BrokerPaperOrderResult:
    broker_order_id: str | None
    status: str
    raw_response: dict[str, BrokerResponseValue]


class PaperOrderSubmitter(Protocol):
    def submit(
        self,
        settings: EnvBrokerSettings,
        request: BrokerPaperOrderRequest,
    ) -> BrokerPaperOrderResult: ...


class PaperOrderSubmissionUnavailable(RuntimeError):
    pass


class UnavailablePaperOrderSubmitter:
    def submit(
        self,
        settings: EnvBrokerSettings,
        request: BrokerPaperOrderRequest,
    ) -> BrokerPaperOrderResult:
        raise PaperOrderSubmissionUnavailable(
            "IBKR paper order submission is not available; no broker order operation was attempted."
        )


class IbAsyncPaperOrderSubmitter:
    def __init__(
        self,
        ib_client_factory: Callable[[], Any] | None = None,
        stock_factory: Callable[[str, str, str], Any] | None = None,
        market_order_factory: Callable[[str, int], Any] | None = None,
        limit_order_factory: Callable[[str, int, float], Any] | None = None,
    ) -> None:
        self.ib_client_factory = ib_client_factory
        self.stock_factory = stock_factory
        self.market_order_factory = market_order_factory
        self.limit_order_factory = limit_order_factory

    def submit(
        self,
        settings: EnvBrokerSettings,
        request: BrokerPaperOrderRequest,
    ) -> BrokerPaperOrderResult:
        if not settings.paper_order_submission_enabled:
            raise PaperOrderSubmissionUnavailable(
                "IBKR paper order submission is disabled; no broker order operation was attempted."
            )
        if not _is_configured_paper_account(settings.paper_account_id):
            raise PaperOrderSubmissionUnavailable(
                "IBKR paper order submission requires a configured IBKR paper account; "
                "no broker order operation was attempted."
            )
        _validate_broker_paper_order_request(request)

        ib_client = self._build_client()
        connected = False
        try:
            ib_client.connect(
                settings.host,
                settings.port,
                clientId=settings.client_id,
                readonly=False,
                timeout=settings.connectivity_probe_timeout_seconds,
            )
            connected = True
            contract = self._build_stock_contract(request.symbol)
            order = self._build_order(request)
            _assign_order_account(order, settings.paper_account_id)
            trade = ib_client.placeOrder(contract, order)
            broker_order_id = _extract_broker_order_id(trade)
            status = _extract_order_status(trade)
            return BrokerPaperOrderResult(
                broker_order_id=broker_order_id,
                status=status,
                raw_response={"broker_order_id": broker_order_id, "status": status},
            )
        finally:
            if connected:
                ib_client.disconnect()

    def _build_client(self) -> Any:
        if self.ib_client_factory is not None:
            return self.ib_client_factory()
        try:
            from ib_async import IB
        except ImportError as exc:
            raise PaperOrderSubmissionUnavailable(
                "IBKR paper order submission requires optional ib_async; "
                "no broker order operation was attempted."
            ) from exc
        return IB()

    def _build_stock_contract(self, symbol: str) -> Any:
        if self.stock_factory is not None:
            return self.stock_factory(symbol.upper(), "SMART", "USD")
        try:
            from ib_async import Stock
        except ImportError as exc:
            raise PaperOrderSubmissionUnavailable(
                "IBKR paper order submission requires optional ib_async; "
                "no broker order operation was attempted."
            ) from exc
        return Stock(symbol.upper(), "SMART", "USD")

    def _build_order(self, request: BrokerPaperOrderRequest) -> Any:
        action = _ib_action(request.side)
        if request.order_type == "market":
            if self.market_order_factory is not None:
                return self.market_order_factory(action, request.quantity)
            try:
                from ib_async import MarketOrder
            except ImportError as exc:
                raise PaperOrderSubmissionUnavailable(
                    "IBKR paper order submission requires optional ib_async; "
                    "no broker order operation was attempted."
                ) from exc
            return MarketOrder(action, request.quantity)

        if request.order_type == "limit":
            if request.limit_price is None:
                raise ValueError("limit_price is required for limit paper orders")
            if self.limit_order_factory is not None:
                return self.limit_order_factory(action, request.quantity, request.limit_price)
            try:
                from ib_async import LimitOrder
            except ImportError as exc:
                raise PaperOrderSubmissionUnavailable(
                    "IBKR paper order submission requires optional ib_async; "
                    "no broker order operation was attempted."
                ) from exc
            return LimitOrder(action, request.quantity, request.limit_price)

        raise ValueError(f"unsupported paper order type: {request.order_type}")


def _validate_broker_paper_order_request(request: BrokerPaperOrderRequest) -> None:
    if request.side.lower() not in {"buy", "sell"}:
        raise ValueError(f"unsupported paper order side: {request.side}")
    if request.order_type not in {"market", "limit"}:
        raise ValueError(f"unsupported paper order type: {request.order_type}")
    if request.quantity <= 0:
        raise ValueError("quantity must be positive for paper orders")
    if request.order_type == "limit" and (request.limit_price is None or request.limit_price <= 0):
        raise ValueError("limit_price is required for limit paper orders")
    if request.order_type == "market" and request.limit_price is not None:
        raise ValueError("limit_price is not allowed for market paper orders")


def _is_configured_paper_account(account_id: str | None) -> bool:
    return account_id is not None and account_id.strip().upper().startswith("DU")


def _assign_order_account(order: Any, account_id: str | None) -> None:
    if account_id is None:
        return
    paper_account_id = account_id.strip().upper()
    if isinstance(order, dict):
        order["account"] = paper_account_id
        return
    order.account = paper_account_id


def _ib_action(side: str) -> str:
    match side.lower():
        case "buy":
            return "BUY"
        case "sell":
            return "SELL"
        case _:
            raise ValueError(f"unsupported paper order side: {side}")


def _extract_broker_order_id(trade: Any) -> str | None:
    order = getattr(trade, "order", None)
    order_id = getattr(order, "orderId", None)
    if order_id is None:
        return None
    return str(order_id)


def _extract_order_status(trade: Any) -> str:
    order_status = getattr(trade, "orderStatus", None)
    status = getattr(order_status, "status", None)
    if status is None:
        return "submitted"
    return str(status)
