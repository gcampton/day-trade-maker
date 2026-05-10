from fastapi import APIRouter, HTTPException, status

from day_trade_maker.market_data import parse_candles_csv
from day_trade_maker.schemas import CandleResponse, MarketDataDatasetSummary, MarketDataImport
from day_trade_maker.stores import market_data_store

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.post(
    "/import-csv",
    response_model=MarketDataDatasetSummary,
    status_code=status.HTTP_201_CREATED,
)
def import_market_data_csv(payload: MarketDataImport) -> MarketDataDatasetSummary:
    candles = parse_candles_csv(payload.csv_text)
    dataset = market_data_store.create(
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        candles=candles,
    )
    return MarketDataDatasetSummary(
        id=dataset.id,
        symbol=dataset.symbol,
        timeframe=dataset.timeframe,
        candle_count=dataset.candle_count,
        created_at=dataset.created_at,
    )


@router.get("/{dataset_id}/candles", response_model=list[CandleResponse])
def get_market_data_candles(dataset_id: int) -> list[CandleResponse]:
    dataset = market_data_store.get(dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Market dataset not found",
        )

    return [CandleResponse.model_validate(candle.model_dump()) for candle in dataset.candles]
