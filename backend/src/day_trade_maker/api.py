from fastapi import FastAPI

app = FastAPI(title="Day Trade Maker API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
