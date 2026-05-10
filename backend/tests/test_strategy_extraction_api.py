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
    assert isinstance(strategy["id"], int)
    assert strategy["id"] > 0
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


def test_approve_strategy_marks_candidate_reviewed_and_approved() -> None:
    client = TestClient(app)
    transcript_id = create_breakout_transcript(client)
    strategy_response = client.post(f"/api/transcripts/{transcript_id}/extract-strategies")
    strategy_id = strategy_response.json()[0]["id"]

    response = client.post(
        f"/api/strategies/{strategy_id}/approve",
        json={
            "approved_by": "Garratt",
            "notes": "Reviewed source quote, entry, exit, and 1% risk rule.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == strategy_id
    assert body["status"] == "approved"
    assert body["approved_by"] == "Garratt"
    assert body["approval_notes"] == "Reviewed source quote, entry, exit, and 1% risk rule."
    assert body["approved_at"] is not None


def test_approve_strategy_returns_404_for_unknown_strategy() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/strategies/999999/approve",
        json={"approved_by": "Garratt", "notes": "No matching candidate."},
    )

    assert response.status_code == 404


def test_extract_strategies_returns_404_for_unknown_transcript() -> None:
    client = TestClient(app)

    response = client.post("/api/transcripts/999999/extract-strategies")

    assert response.status_code == 404
