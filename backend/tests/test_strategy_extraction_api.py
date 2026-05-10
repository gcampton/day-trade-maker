from fastapi.testclient import TestClient

from day_trade_maker.api import app


def create_breakout_transcript(client: TestClient) -> int:
    response = client.post(
        "/api/transcripts",
        json={
            "title": "Opening Range Breakout",
            "source_url": "https://www.youtube.com/watch?v=breakout",
            "creator": "Example Trader",
            "raw_text": (
                "I wait for the first fifteen minute high to break with volume. "
                "My stop goes below the opening range low and I risk one percent."
            ),
            "symbols": ["aapl"],
            "timeframes": ["15m"],
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_extract_strategies_returns_valid_auditable_strategy_spec() -> None:
    client = TestClient(app)
    transcript_id = create_breakout_transcript(client)

    response = client.post(f"/api/transcripts/{transcript_id}/extract-strategies")

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    strategy = body[0]
    assert strategy["id"] == 1
    assert strategy["transcript_id"] == transcript_id
    assert strategy["spec"]["name"] == "Opening Range Breakout With Volume"
    assert strategy["spec"]["symbols"] == ["AAPL"]
    assert strategy["spec"]["timeframe"] == "15m"
    assert strategy["spec"]["entry_rules"][0]["type"] == "price_breakout"
    assert strategy["spec"]["risk_rules"][0]["type"] == "max_risk_per_trade"
    assert strategy["spec"]["source_quotes"][0]["transcript_id"] == transcript_id
    assert strategy["status"] == "candidate"


def test_list_strategies_returns_extracted_candidates() -> None:
    client = TestClient(app)
    transcript_id = create_breakout_transcript(client)
    client.post(f"/api/transcripts/{transcript_id}/extract-strategies")

    response = client.get("/api/strategies")

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[-1]["transcript_id"] == transcript_id
    assert body[-1]["spec"]["source_quotes"][0]["transcript_id"] == transcript_id


def test_extract_strategies_returns_404_for_unknown_transcript() -> None:
    client = TestClient(app)

    response = client.post("/api/transcripts/999999/extract-strategies")

    assert response.status_code == 404
