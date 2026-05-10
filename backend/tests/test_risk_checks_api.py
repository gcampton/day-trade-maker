from fastapi.testclient import TestClient

from day_trade_maker.api import app


def create_strategy_dataset_and_backtest(client: TestClient) -> tuple[int, int]:
    transcript_response = client.post(
        "/api/transcripts",
        json={
            "title": "Opening Range Breakout",
            "source_url": None,
            "creator": "Example Trader",
            "raw_text": (
                "I buy the first fifteen minute high breakout with volume "
                "and risk one percent."
            ),
            "symbols": ["AAPL"],
            "timeframes": ["5m"],
        },
    )
    transcript_id = transcript_response.json()["id"]
    strategy_response = client.post(f"/api/transcripts/{transcript_id}/extract-strategies")
    strategy_id = strategy_response.json()[0]["id"]

    dataset_response = client.post(
        "/api/market-data/import-csv",
        json={
            "symbol": "AAPL",
            "timeframe": "5m",
            "csv_text": """timestamp,open,high,low,close,volume
2026-05-10T14:30:00Z,100,101,99,100.5,100000
2026-05-10T14:35:00Z,100.5,102,100.25,101.5,180000
2026-05-10T14:40:00Z,101.5,103,101,102.5,220000
""",
        },
    )
    dataset_id = dataset_response.json()["id"]
    backtest_response = client.post(
        "/api/backtests",
        json={"strategy_id": strategy_id, "dataset_id": dataset_id, "starting_cash": 10_000},
    )
    backtest_id = backtest_response.json()["id"]
    return strategy_id, backtest_id


def test_risk_check_passes_for_approved_strategy_successful_backtest_and_paper_mode() -> None:
    client = TestClient(app)
    strategy_id, backtest_id = create_strategy_dataset_and_backtest(client)
    client.post(
        f"/api/strategies/{strategy_id}/approve",
        json={"approved_by": "Garratt", "notes": "Reviewed strategy and risk rule."},
    )

    response = client.post(
        "/api/risk-checks",
        json={
            "strategy_id": strategy_id,
            "backtest_id": backtest_id,
            "paper_mode": True,
            "max_risk_percent": 1,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "passed"
    assert body["strategy_id"] == strategy_id
    assert body["backtest_id"] == backtest_id
    assert body["paper_mode"] is True
    assert "approved strategy" in body["checks"]
    assert "paper mode enabled" in body["checks"]
    assert body["failures"] == []


def test_risk_check_fails_when_strategy_is_not_approved_or_paper_mode_is_off() -> None:
    client = TestClient(app)
    strategy_id, backtest_id = create_strategy_dataset_and_backtest(client)

    response = client.post(
        "/api/risk-checks",
        json={
            "strategy_id": strategy_id,
            "backtest_id": backtest_id,
            "paper_mode": False,
            "max_risk_percent": 1,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert "strategy must be approved before broker workflows" in body["failures"]
    assert "paper mode must be enabled" in body["failures"]


def test_risk_check_returns_404_for_unknown_strategy_or_backtest() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/risk-checks",
        json={
            "strategy_id": 999999,
            "backtest_id": 999999,
            "paper_mode": True,
            "max_risk_percent": 1,
        },
    )

    assert response.status_code == 404
