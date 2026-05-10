from fastapi import FastAPI

from day_trade_maker.routes.market_data import router as market_data_router
from day_trade_maker.routes.strategies import router as strategies_router
from day_trade_maker.routes.transcripts import router as transcripts_router

app = FastAPI(title="Day Trade Maker API")
app.include_router(transcripts_router)
app.include_router(strategies_router)
app.include_router(market_data_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
