# GigShield AI Forensic Auditor (Level 0)

GigShield is a production-oriented forensic platform for gig workers. It validates weather disruption claims using a multi-source **Consensus Engine** and executes transparent, parametric payouts.

## Stack

- **Backend:** FastAPI on port `8000`
- **Consensus oracles:**
  - Nominatim (geospatial claim-location validation)
  - Open-Meteo Archive API (historical hourly precipitation, wind, snowfall)
- **Frontend:** Multi-page cockpit UI with Vanilla HTML/CSS/JS
- **Visualization:** Chart.js risk telemetry

## Modules

1. **Forensic Dashboard**
   - Real-time risk score (0-100)
   - Volatility, traffic density proxy, forensic history risk
   - Driver strike state and restriction status
2. **Automated Payout Engine**
   - Blizzard: `$15/hr`
   - Heavy Rain: `$5/hr`
   - Clear: `$0/hr`
3. **3-Strike Fraud Policy**
   - Failed consensus checks add strikes
   - Third strike hard-restricts account
4. **Policy Transparency**
   - Human-readable rendering of enforcement logic

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000
```

Then open:
- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/claims`
- `http://127.0.0.1:8000/policy`
