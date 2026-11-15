"""後端程式進入點。

啟動(在 backend-api/ 底下執行):
    uv run uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI

from app.device_api.router import router as device_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="智慧魚缸後端")
app.include_router(device_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
