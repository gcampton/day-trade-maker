from fastapi.testclient import TestClient

from day_trade_maker.api import app


def create_audited_order_intent(client: TestClient) -> dict:
    transcript_response = client.post(
        "/api/transcripts",
        json={
            "title": "Opening Range Breakout Audit Export",
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
    client.post(
        f"/api/strategies/{strategy_id}/approve",
        json={"approved_by": "Garratt", "notes": "Reviewed strategy and risk rule."},
    )
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
    risk_check_response = client.post(
        "/api/risk-checks",
        json={
            "strategy_id": strategy_id,
            "backtest_id": backtest_id,
            "paper_mode": True,
            "max_risk_percent": 1,
        },
    )
    risk_check_id = risk_check_response.json()["id"]
    order_intent_response = client.post(
        "/api/broker/order-intents",
        json={
            "strategy_id": strategy_id,
            "risk_check_id": risk_check_id,
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 10,
            "order_type": "market",
            "paper_mode": True,
            "user_confirmed": True,
        },
    )
    return order_intent_response.json()


def test_export_audit_snapshot_includes_all_research_and_order_intent_artifacts() -> None:
    client = TestClient(app)
    order_intent = create_audited_order_intent(client)

    response = client.get("/api/audit/export")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["exported_at"]
    assert any(
        transcript["title"] == "Opening Range Breakout Audit Export"
        for transcript in body["transcripts"]
    )
    assert any(strategy["id"] == order_intent["strategy_id"] for strategy in body["strategies"])
    assert any(
        dataset["symbol"] == "AAPL" and len(dataset["candles"]) == 3
        for dataset in body["market_data"]
    )
    assert any(backtest["id"] for backtest in body["backtests"])
    assert any(
        risk_check["id"] == order_intent["risk_check_id"]
        for risk_check in body["risk_checks"]
    )
    assert any(intent["id"] == order_intent["id"] for intent in body["paper_order_intents"])
    assert all(intent["submitted_to_broker"] is False for intent in body["paper_order_intents"])


def test_import_audit_snapshot_replaces_in_memory_audit_state() -> None:
    client = TestClient(app)
    create_audited_order_intent(client)
    snapshot = client.get("/api/audit/export").json()
    snapshot["transcripts"][0]["title"] = "Restored audit snapshot"
    snapshot["paper_order_intents"][0]["symbol"] = "MSFT"

    response = client.post("/api/audit/import", json=snapshot)

    assert response.status_code == 200
    body = response.json()
    assert body["transcript_count"] == len(snapshot["transcripts"])
    assert body["paper_order_intent_count"] == len(snapshot["paper_order_intents"])
    assert client.get("/api/transcripts").json()[0]["title"] == "Restored audit snapshot"
    assert client.get("/api/broker/order-intents").json()[0]["symbol"] == "MSFT"
