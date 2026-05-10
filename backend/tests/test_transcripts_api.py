from fastapi.testclient import TestClient

from day_trade_maker.api import app


def test_create_transcript_returns_saved_record() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/transcripts",
        json={
            "title": "Opening Range Breakout Explained",
            "source_url": "https://www.youtube.com/watch?v=example",
            "creator": "Example Trader",
            "raw_text": "Wait for the first 15 minute range, then buy the breakout with volume.",
            "symbols": ["AAPL", "TSLA"],
            "timeframes": ["15m"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["id"] > 0
    assert body["title"] == "Opening Range Breakout Explained"
    assert body["creator"] == "Example Trader"
    assert body["symbols"] == ["AAPL", "TSLA"]
    assert body["timeframes"] == ["15m"]
    assert body["raw_text"].startswith("Wait for the first 15 minute range")
    assert "created_at" in body


def test_list_transcripts_returns_saved_records() -> None:
    client = TestClient(app)

    client.post(
        "/api/transcripts",
        json={
            "title": "VWAP Pullback Setup",
            "source_url": None,
            "creator": "Example Trader",
            "raw_text": "I wait for price to reclaim VWAP and hold a higher low.",
            "symbols": ["SPY"],
            "timeframes": ["5m"],
        },
    )

    response = client.get("/api/transcripts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[-1]["title"] == "VWAP Pullback Setup"


def test_rejects_empty_transcript_text() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/transcripts",
        json={
            "title": "Empty",
            "source_url": None,
            "creator": "Example Trader",
            "raw_text": "   ",
            "symbols": [],
            "timeframes": [],
        },
    )

    assert response.status_code == 422
