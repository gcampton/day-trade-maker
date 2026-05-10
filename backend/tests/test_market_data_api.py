from fastapi.testclient import TestClient

from day_trade_maker.api import app


def test_import_market_data_csv_returns_dataset_with_candles() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/market-data/import-csv",
        json={
            "symbol": "aapl",
            "timeframe": "5m",
            "csv_text": """timestamp,open,high,low,close,volume
2026-05-10T14:35:00Z,101,103,100.5,102,200000
2026-05-10T14:30:00Z,100,101.5,99.5,101,150000
""",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["id"] > 0
    assert body["symbol"] == "AAPL"
    assert body["timeframe"] == "5m"
    assert body["candle_count"] == 2


def test_get_market_data_candles_returns_imported_candles() -> None:
    client = TestClient(app)
    import_response = client.post(
        "/api/market-data/import-csv",
        json={
            "symbol": "SPY",
            "timeframe": "1m",
            "csv_text": """timestamp,open,high,low,close,volume
2026-05-10T14:30:00Z,500,501,499,500.5,500000
""",
        },
    )
    dataset_id = import_response.json()["id"]

    response = client.get(f"/api/market-data/{dataset_id}/candles")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["close"] == 500.5
    assert body[0]["timestamp"] == "2026-05-10T14:30:00Z"


def test_get_market_data_candles_returns_404_for_unknown_dataset() -> None:
    client = TestClient(app)

    response = client.get("/api/market-data/999999/candles")

    assert response.status_code == 404
