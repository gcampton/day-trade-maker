import pytest

from day_trade_maker.broker import EnvBrokerSettings
from day_trade_maker.broker_orders import (
    BrokerPaperOrderRequest,
    IbAsyncPaperOrderSubmitter,
    PaperOrderSubmissionUnavailable,
    UnavailablePaperOrderSubmitter,
)


def market_request() -> BrokerPaperOrderRequest:
    return BrokerPaperOrderRequest(
        symbol="AAPL",
        side="buy",
        quantity=10,
        order_type="market",
        limit_price=None,
    )


def test_unavailable_submitter_raises_before_any_broker_operation() -> None:
    submitter = UnavailablePaperOrderSubmitter()

    with pytest.raises(PaperOrderSubmissionUnavailable, match="not available"):
        submitter.submit(EnvBrokerSettings(), market_request())


def test_ib_async_submitter_refuses_when_paper_submission_disabled_before_client_creation() -> None:
    def fail_if_client_created():
        raise AssertionError("IBKR client must not be created while paper submission is disabled")

    submitter = IbAsyncPaperOrderSubmitter(ib_client_factory=fail_if_client_created)

    with pytest.raises(PaperOrderSubmissionUnavailable, match="disabled"):
        submitter.submit(EnvBrokerSettings(paper_order_submission_enabled=False), market_request())


def test_ib_async_submitter_refuses_without_verified_paper_account_before_client_creation() -> None:
    def fail_if_client_created():
        raise AssertionError("IBKR client must not be created without a verified paper account")

    submitter = IbAsyncPaperOrderSubmitter(ib_client_factory=fail_if_client_created)

    for account_id in [None, "U1234567"]:
        with pytest.raises(PaperOrderSubmissionUnavailable, match="paper account"):
            submitter.submit(
                EnvBrokerSettings(
                    paper_order_submission_enabled=True,
                    paper_account_id=account_id,
                ),
                market_request(),
            )


def test_ib_async_submitter_maps_market_order_and_disconnects() -> None:
    calls = []

    class FakeTrade:
        class order:
            orderId = 12345

        class orderStatus:
            status = "Submitted"

    class FakeIbClient:
        def connect(self, host, port, clientId, readonly, timeout):
            calls.append(("connect", host, port, clientId, readonly, timeout))

        def placeOrder(self, contract, order):
            calls.append(("placeOrder", contract, order))
            return FakeTrade()

        def disconnect(self):
            calls.append(("disconnect",))

    def fake_stock(symbol, exchange, currency):
        return {"symbol": symbol, "exchange": exchange, "currency": currency}

    def fake_market_order(action, quantity):
        return {"type": "market", "action": action, "quantity": quantity}

    submitter = IbAsyncPaperOrderSubmitter(
        ib_client_factory=FakeIbClient,
        stock_factory=fake_stock,
        market_order_factory=fake_market_order,
    )

    result = submitter.submit(
        EnvBrokerSettings(
            host="192.0.2.10",
            port=7497,
            client_id=17,
            connectivity_probe_timeout_seconds=0.25,
            paper_order_submission_enabled=True,
            paper_account_id="DU1234567",
        ),
        market_request(),
    )

    assert result.broker_order_id == "12345"
    assert result.status == "Submitted"
    assert result.raw_response == {"broker_order_id": "12345", "status": "Submitted"}
    assert calls == [
        ("connect", "192.0.2.10", 7497, 17, False, 0.25),
        (
            "placeOrder",
            {"symbol": "AAPL", "exchange": "SMART", "currency": "USD"},
            {"type": "market", "action": "BUY", "quantity": 10, "account": "DU1234567"},
        ),
        ("disconnect",),
    ]


def test_ib_async_submitter_maps_limit_order_price() -> None:
    calls = []

    class FakeTrade:
        class order:
            orderId = 55

        class orderStatus:
            status = "PreSubmitted"

    class FakeIbClient:
        def connect(self, *args, **kwargs):
            calls.append(("connect", args, kwargs))

        def placeOrder(self, contract, order):
            calls.append(("placeOrder", contract, order))
            return FakeTrade()

        def disconnect(self):
            calls.append(("disconnect",))

    submitter = IbAsyncPaperOrderSubmitter(
        ib_client_factory=FakeIbClient,
        stock_factory=lambda symbol, exchange, currency: (symbol, exchange, currency),
        limit_order_factory=lambda action, quantity, limit_price: {
            "action": action,
            "quantity": quantity,
            "limit_price": limit_price,
        },
    )

    result = submitter.submit(
        EnvBrokerSettings(
            paper_order_submission_enabled=True,
            paper_account_id="DU1234567",
        ),
        BrokerPaperOrderRequest(
            symbol="MSFT",
            side="sell",
            quantity=3,
            order_type="limit",
            limit_price=411.25,
        ),
    )

    assert result.broker_order_id == "55"
    assert (
        "placeOrder",
        ("MSFT", "SMART", "USD"),
        {"action": "SELL", "quantity": 3, "limit_price": 411.25, "account": "DU1234567"},
    ) in calls


def test_ib_async_submitter_rejects_limit_order_without_limit_price() -> None:
    submitter = IbAsyncPaperOrderSubmitter(ib_client_factory=lambda: object())

    with pytest.raises(ValueError, match="limit_price"):
        submitter.submit(
            EnvBrokerSettings(
                paper_order_submission_enabled=True,
                paper_account_id="DU1234567",
            ),
            BrokerPaperOrderRequest(
                symbol="MSFT",
                side="sell",
                quantity=3,
                order_type="limit",
                limit_price=None,
            ),
        )


def test_ib_async_submitter_rejects_unsupported_side_before_client_creation() -> None:
    def fail_if_client_created():
        raise AssertionError("IBKR client must not be created for invalid paper order side")

    submitter = IbAsyncPaperOrderSubmitter(ib_client_factory=fail_if_client_created)

    with pytest.raises(ValueError, match="unsupported paper order side"):
        submitter.submit(
            EnvBrokerSettings(
                paper_order_submission_enabled=True,
                paper_account_id="DU1234567",
            ),
            BrokerPaperOrderRequest(
                symbol="MSFT",
                side="hold",
                quantity=3,
                order_type="market",
                limit_price=None,
            ),
        )


def test_ib_async_submitter_rejects_unsupported_order_type_before_client_creation() -> None:
    def fail_if_client_created():
        raise AssertionError("IBKR client must not be created for invalid paper order type")

    submitter = IbAsyncPaperOrderSubmitter(ib_client_factory=fail_if_client_created)

    with pytest.raises(ValueError, match="unsupported paper order type"):
        submitter.submit(
            EnvBrokerSettings(
                paper_order_submission_enabled=True,
                paper_account_id="DU1234567",
            ),
            BrokerPaperOrderRequest(
                symbol="MSFT",
                side="sell",
                quantity=3,
                order_type="stop",
                limit_price=None,
            ),
        )


def test_ib_async_submitter_disconnects_after_place_order_error() -> None:
    calls = []

    class FakeIbClient:
        def connect(self, *args, **kwargs):
            calls.append(("connect", args, kwargs))

        def placeOrder(self, contract, order):
            calls.append(("placeOrder", contract, order))
            raise RuntimeError("broker rejected order")

        def disconnect(self):
            calls.append(("disconnect",))

    submitter = IbAsyncPaperOrderSubmitter(
        ib_client_factory=FakeIbClient,
        stock_factory=lambda symbol, exchange, currency: (symbol, exchange, currency),
        market_order_factory=lambda action, quantity: {
            "action": action,
            "quantity": quantity,
        },
    )

    with pytest.raises(RuntimeError, match="broker rejected order"):
        submitter.submit(
            EnvBrokerSettings(
                paper_order_submission_enabled=True,
                paper_account_id="DU1234567",
            ),
            market_request(),
        )

    assert calls[-1] == ("disconnect",)
