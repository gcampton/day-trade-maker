import csv
from datetime import datetime
from io import StringIO
from typing import Any

from pydantic import BaseModel, Field, model_validator

REQUIRED_CSV_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}


class Candle(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_ohlc_range(self) -> "Candle":
        highest_body_price = max(self.open, self.close)
        lowest_body_price = min(self.open, self.close)

        if self.high < highest_body_price:
            raise ValueError("high must be greater than or equal to open and close")
        if self.low > lowest_body_price:
            raise ValueError("low must be less than or equal to open and close")
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")

        return self


def parse_candles_csv(csv_text: str) -> list[Candle]:
    reader = csv.DictReader(StringIO(csv_text.strip()))
    fieldnames = set(reader.fieldnames or [])
    missing_columns = sorted(REQUIRED_CSV_COLUMNS - fieldnames)
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    candles = [_row_to_candle(row) for row in reader]
    return sorted(candles, key=lambda candle: candle.timestamp)


def _row_to_candle(row: dict[str, Any]) -> Candle:
    return Candle(
        timestamp=datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00")),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
    )
