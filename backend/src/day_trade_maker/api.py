from fastapi import FastAPI

from day_trade_maker.routes.transcripts import router as transcripts_router

app = FastAPI(title="Day Trade Maker API")
app.include_router(transcripts_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
