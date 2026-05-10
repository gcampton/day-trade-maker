from fastapi.testclient import TestClient

from day_trade_maker.api import app


def create_transcript_strategy_and_dataset(client: TestClient) -> tuple[int, int]:
    transcript_response = client.post(
        "/api/transcripts",
        json={
            "title": "Opening Range Breakout",
            "source_url": None,
            "creator": "Example Trader",
            "raw_text": "I buy the first fifteen minute high breakout with volume.",
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
    return strategy_id, dataset_id


def test_create_backtest_returns_metrics_trades_and_markers() -> None:
    client = TestClient(app)
    strategy_id, dataset_id = create_transcript_strategy_and_dataset(client)

    response = client.post(
        "/api/backtests",
        json={"strategy_id": strategy_id, "dataset_id": dataset_id, "starting_cash": 10_000},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["strategy_id"] == strategy_id
    assert body["dataset_id"] == dataset_id
    assert body["result"]["total_trades"] == 1
    assert body["result"]["net_pnl"] == 1
    assert body["result"]["markers"][0]["label"] == "Buy breakout"
    assert body["result"]["markers"][1]["label"] == "Exit close"


def test_create_backtest_returns_404_for_unknown_strategy_or_dataset() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/backtests",
        json={"strategy_id": 999999, "dataset_id": 999999, "starting_cash": 10_000},
    )

    assert response.status_code == 404
