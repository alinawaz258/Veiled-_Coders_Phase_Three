from __future__ import annotations

import time
from pathlib import Path
from urllib.request import Request, urlopen
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .models import ClaimSubmission, DashboardSnapshot, PolicyDocument
from .services import GigShieldConsensusEngine

app = FastAPI(
    title="GigShield AI Forensic Auditor",
    description="Level 0 production forensic consensus and payout platform for gig workers",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LEDGER_PATH = DATA_DIR / "claims_ledger.json"

engine = GigShieldConsensusEngine(ledger_path=LEDGER_PATH)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "index.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "dashboard.html")


@app.get("/claims", include_in_schema=False)
def claims_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "claims.html")


@app.get("/policy", include_in_schema=False)
def policy_page() -> FileResponse:
    return FileResponse(PAGES_DIR / "policy.html")


@app.get("/api/dashboard", response_model=DashboardSnapshot)
def dashboard_data() -> DashboardSnapshot:
    return engine.dashboard_snapshot()


@app.get("/api/drivers")
def driver_data():
    return engine.list_drivers()


@app.get("/api/claims")
def claim_feed():
    return engine.recent_claims()


@app.get("/api/claims/ledger")
def claims_ledger():
    """Return the full persisted claims ledger from disk."""
    if not LEDGER_PATH.exists():
        return JSONResponse(content=[])
    try:
        data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        return JSONResponse(content=data)
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Ledger read error: {exc}") from exc


@app.post("/api/claims/submit")
def submit_claim(claim: ClaimSubmission):
    try:
        return engine.process_claim(claim)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/policy", response_model=PolicyDocument)
def policy_data() -> PolicyDocument:
    return engine.policy_document()


@app.post("/api/drivers/reset/{driver_id}")
def reset_driver(driver_id: str):
    try:
        return engine.reset_driver(driver_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/realtime/scan")
def realtime_scan(location: str):
    """Pull LIVE current weather for a location and return detected conditions."""
    try:
        return engine.realtime_scan(location)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Oracle scan failed: {str(exc)}") from exc


def _probe_url(url: str, timeout: int = 6) -> dict:
    """Probe a URL and return status, latency in ms, and whether it is alive."""
    try:
        t0 = time.monotonic()
        req = Request(url, headers={"User-Agent": "GigShield-HealthCheck/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            resp.read(512)  # consume a small slice to confirm transport
            latency_ms = round((time.monotonic() - t0) * 1000, 1)
            return {"online": True, "latency_ms": latency_ms, "http_status": resp.status}
    except Exception as exc:
        return {"online": False, "latency_ms": None, "error": str(exc)}


@app.get("/api/health/oracles")
def oracle_health():
    """
    Live-probe Open-Meteo and Nominatim oracles and return real uptime/latency.
    Also returns a live weather snapshot for New Delhi as default cockpit context.
    """
    open_meteo = _probe_url(
        "https://api.open-meteo.com/v1/forecast?latitude=28.6139&longitude=77.2090"
        "&current=precipitation&timezone=auto"
    )
    nominatim = _probe_url(
        "https://nominatim.openstreetmap.org/search?q=Delhi&format=jsonv2&limit=1"
    )

    # Live context scan for New Delhi so the dashboard has real numbers on boot
    context_scan = None
    try:
        context_scan = engine.realtime_scan("New Delhi, India")
    except Exception as exc:
        context_scan = {"error": str(exc)}

    all_online = open_meteo["online"] and nominatim["online"]
    avg_latency = None
    latencies = [v for v in [open_meteo.get("latency_ms"), nominatim.get("latency_ms")] if v is not None]
    if latencies:
        avg_latency = round(sum(latencies) / len(latencies), 1)

    return {
        "all_oracles_online": all_online,
        "avg_latency_ms": avg_latency,
        "oracles": {
            "open_meteo": open_meteo,
            "nominatim": nominatim,
        },
        "context_scan": context_scan,
    }
