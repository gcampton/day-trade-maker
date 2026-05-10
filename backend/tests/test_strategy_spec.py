import pytest
from pydantic import ValidationError

from day_trade_maker.strategy_spec import StrategySpec


def valid_strategy_payload() -> dict:
    return {
        "name": "Opening Range Breakout With Volume",
        "description": "Buy a break above the first 15 minute range when relative volume confirms.",
        "market": "US equities",
        "symbols": ["aapl", "tsla"],
        "timeframe": "15m",
        "indicators": [
            {"name": "opening_range", "parameters": {"minutes": 15}},
            {"name": "volume", "parameters": {"relative_volume_min": 1.5}},
        ],
        "entry_rules": [
            {
                "type": "price_breakout",
                "description": "Enter long when price breaks above the opening range high.",
                "parameters": {"direction": "long"},
            }
        ],
        "exit_rules": [
            {
                "type": "stop_loss",
                "description": "Exit if price falls back inside the opening range.",
                "parameters": {"stop": "opening_range_low"},
            }
        ],
        "risk_rules": [
            {
                "type": "max_risk_per_trade",
                "description": "Risk no more than 1% of account equity per trade.",
                "parameters": {"percent": 1},
            }
        ],
        "invalidations": ["Skip if the breakout candle has below-average volume."],
        "source_quotes": [
            {
                "transcript_id": 7,
                "quote": "I wait for the first fifteen minute high to break with volume.",
                "start_seconds": 123.4,
            }
        ],
    }


def test_strategy_spec_accepts_valid_transcript_derived_strategy() -> None:
    spec = StrategySpec.model_validate(valid_strategy_payload())

    assert spec.name == "Opening Range Breakout With Volume"
    assert spec.symbols == ["AAPL", "TSLA"]
    assert spec.timeframe == "15m"
    assert spec.source_quotes[0].transcript_id == 7


def test_strategy_spec_requires_source_quotes_for_auditability() -> None:
    payload = valid_strategy_payload()
    payload["source_quotes"] = []

    with pytest.raises(ValidationError, match="source_quotes"):
        StrategySpec.model_validate(payload)


def test_strategy_spec_rejects_generated_code_fields() -> None:
    payload = valid_strategy_payload()
    payload["python_code"] = "ib.placeOrder(contract, order)"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        StrategySpec.model_validate(payload)


def test_strategy_spec_requires_at_least_one_entry_exit_and_risk_rule() -> None:
    payload = valid_strategy_payload()
    payload["entry_rules"] = []
    payload["exit_rules"] = []
    payload["risk_rules"] = []

    with pytest.raises(ValidationError):
        StrategySpec.model_validate(payload)
