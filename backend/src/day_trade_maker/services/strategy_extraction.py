from day_trade_maker.schemas import Transcript
from day_trade_maker.strategy_spec import StrategySpec


def extract_strategy_specs(transcript: Transcript) -> list[StrategySpec]:
    """Deterministic dev extractor until a real LLM adapter is wired in."""
    quote = transcript.raw_text.strip().split(".")[0].strip() or transcript.raw_text.strip()
    symbol = transcript.symbols[0] if transcript.symbols else "SPY"
    timeframe = transcript.timeframes[0] if transcript.timeframes else "15m"

    return [
        StrategySpec.model_validate(
            {
                "name": "Opening Range Breakout With Volume",
                "description": (
                    "Enter a long trade when price breaks above an opening range and volume "
                    "confirms participation. This is a transcript-derived hypothesis that must "
                    "be edited, backtested, and approved before any broker workflow."
                ),
                "market": "US equities",
                "symbols": [symbol],
                "timeframe": timeframe,
                "side": "long",
                "indicators": [
                    {"name": "opening_range", "parameters": {"minutes": 15}},
                    {"name": "volume", "parameters": {"relative_volume_min": 1.5}},
                ],
                "entry_rules": [
                    {
                        "type": "price_breakout",
                        "description": "Enter long when price breaks above the opening range high.",
                        "parameters": {"direction": "long", "confirmation": "volume"},
                    }
                ],
                "exit_rules": [
                    {
                        "type": "stop_loss",
                        "description": "Exit if price falls below the opening range low.",
                        "parameters": {"stop": "opening_range_low"},
                    },
                    {
                        "type": "take_profit",
                        "description": "Scale out when reward is at least two times initial risk.",
                        "parameters": {"risk_reward": 2},
                    },
                ],
                "risk_rules": [
                    {
                        "type": "max_risk_per_trade",
                        "description": "Risk no more than 1% of account equity per trade.",
                        "parameters": {"percent": 1},
                    }
                ],
                "invalidations": [
                    "Skip the trade if breakout volume is weak.",
                    "Skip if price immediately falls back inside the opening range.",
                ],
                "source_quotes": [
                    {
                        "transcript_id": transcript.id,
                        "quote": quote,
                        "start_seconds": None,
                    }
                ],
            }
        )
    ]
