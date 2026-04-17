"""FastAPI application exposing GigShield AI risk and premium APIs.

Phase 2 upgrades
────────────────
• Modern lifespan handler (replaces deprecated @app.on_event)
• /risk/score now returns feature contributions, fraud assessment,
  policy terms, confidence band, and model version
• New GET /model/metrics for model lineage and performance
• New GET /regulatory/exclusions for coverage exclusion listing
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from schemas import RiskPredictionRequest

BACKEND_BASE_URL = os.getenv("GIGSHIELD_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
APP_DIR = Path(__file__).resolve().parent
INDEX_PATH = APP_DIR / "index.html"

app = FastAPI(
    title="GigShield Client App",
    description="Frontend client that consumes gigshield_ai backend APIs.",
    version="1.0.0",
)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(INDEX_PATH)


async def _forward_request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    url = f"{BACKEND_BASE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, json=payload)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Backend unreachable: {exc}") from exc

    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}

    if response.status_code >= 400:
        return JSONResponse(status_code=response.status_code, content={"backend_error": body})

    return JSONResponse(status_code=response.status_code, content=body)


@app.get("/api/health")
async def api_health() -> Any:
    return await _forward_request("GET", "/health")


@app.post("/api/risk/score")
async def api_risk_score(payload: RiskPredictionRequest) -> Any:
    return await _forward_request("POST", "/risk/score", payload.model_dump(exclude_none=True))


@app.get("/api/model/metrics")
async def api_model_metrics() -> Any:
    return await _forward_request("GET", "/model/metrics")
