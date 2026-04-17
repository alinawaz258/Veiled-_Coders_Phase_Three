# GigShield AI — Risk Prediction Microservice

> **Parametric micro-insurance for gig economy workers.**
> ML-driven disruption risk scoring · Dynamic premium pricing · Fraud detection · IRDAI compliance

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Service (app.py)                  │
│                                                              │
│  POST /risk/score ──┬── ML Model (model.py)                 │
│                     │   └─ GradientBoosting + 5-fold CV      │
│                     ├── Risk Engine (risk_engine.py)          │
│                     │   ├─ Weighted rule-based risk score     │
│                     │   ├─ Actuarial premium formula          │
│                     │   ├─ Multi-signal fraud detection       │
│                     │   └─ IRDAI regulatory policy terms      │
│                     └── Explainability                        │
│                         └─ Per-prediction feature contrib.    │
│                                                              │
│  GET  /model/metrics ─── Model lineage & performance         │
│  GET  /regulatory/exclusions ─── Coverage exclusion list     │
│  POST /model/retrain ─── Retrain with fresh synthetic data   │
│  GET  /health ─── Liveness check                             │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```text
gigshield_ai/
├── app.py               # FastAPI endpoints & lifespan
├── model.py             # ML model: training, CV, inference, explainability
├── risk_engine.py       # Risk scoring, premium, fraud, regulatory logic
├── schemas.py           # Pydantic request / response schemas
├── utils.py             # Shared helpers (logging, clamp, safe_ratio)
├── train_model.py       # Standalone training entrypoint
├── requirements.txt     # Python dependencies
└── saved_model/
    ├── risk_model.pkl           # Trained model artifact
    ├── feature_importance.csv   # Feature importance rankings
    └── model_meta.json          # Model version, metrics, hyperparams
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Train the model (optional — auto-trains on first startup)
python train_model.py

# Start the service
uvicorn app:app --reload --port 8000

# Interactive API docs
# → http://127.0.0.1:8000/docs
```

## API Endpoints

| Method | Endpoint                 | Description                                       |
|--------|--------------------------|---------------------------------------------------|
| GET    | `/health`                | Liveness check + model status                     |
| POST   | `/risk/score`            | **Primary** — risk prediction with full output     |
| POST   | `/model/retrain`         | Retrain model with fresh synthetic data            |
| GET    | `/model/metrics`         | Model lineage, metrics, feature importance         |
| GET    | `/regulatory/exclusions` | Coverage exclusions with IRDAI references          |

## Example Request

```bash
curl -X POST "http://127.0.0.1:8000/risk/score" \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Chennai",
    "gig_type": "delivery",
    "platform": "Swiggy",
    "avg_daily_income": 800,
    "weekly_earnings": 4800,
    "avg_work_hours": 8,
    "deliveries_per_day": 22,
    "rainfall_forecast_mm": 65,
    "temperature_forecast_c": 41,
    "aqi_forecast": 280,
    "flood_risk": 0.6,
    "traffic_index": 0.5,
    "historical_disruption_rate": 0.4,
    "claim_history_count": 1
  }'
```

## Example Response (abridged)

```json
{
  "disruption_probability": 0.4231,
  "risk_score": 0.4567,
  "risk_level": "Medium",
  "expected_loss": 710.81,
  "recommended_plan": "Standard",
  "weekly_premium": 42,
  "anomaly_score": 0.05,
  "feature_contributions": {
    "rainfall_forecast_mm": 0.1234,
    "flood_risk": 0.2100,
    "...": "..."
  },
  "fraud_assessment": {
    "anomaly_score": 0.05,
    "flag": "Clean",
    "signals": ["...5 signals with breakdown..."],
    "recommendation": "Auto-approve: no anomalies detected."
  },
  "policy_terms": {
    "irdai_sandbox_compliant": true,
    "activation_wait_hours": 24,
    "moratorium_period_days": 30,
    "coverage_exclusions": ["...10 exclusions..."],
    "regulatory_notes": ["..."]
  },
  "model_version": "2.0.0",
  "confidence_band": { "low": 0.38, "high": 0.47, "margin": 0.05 }
}
```

## AI / ML Approach

| Aspect              | Detail                                                       |
|---------------------|--------------------------------------------------------------|
| **Algorithm**       | GradientBoostingRegressor (sklearn) with tuned hyperparams   |
| **Validation**      | 5-fold cross-validation on training set                      |
| **Metrics**         | R², MAE, RMSE on held-out test set                           |
| **Explainability**  | Per-prediction feature contributions (importance × input)    |
| **Confidence**      | Confidence band derived from CV variance                     |
| **Training data**   | 6,000 synthetic samples with realistic feature distributions |
| **Versioning**      | model_meta.json with timestamp, metrics, hyperparams         |

## Fraud Detection

5 independent signals with composite scoring:

| Signal                           | Normal Range      | Weight |
|----------------------------------|-------------------|--------|
| Income per delivery ratio        | ₹30 – ₹100       | 25%    |
| Deliveries per hour consistency  | 1 – 6 per hour    | 20%    |
| High disruption + high earnings  | Rate < 0.7        | 20%    |
| Excessive work hours             | < 14 hours/day    | 15%    |
| Claim frequency                  | ≤ 4 past claims   | 20%    |

**Flags:** Clean → Review → Suspicious → Block

## Premium Formula

```
insured_loss  = weekly_earnings × 35%
expected_loss = disruption_probability × insured_loss
premium       = expected_loss × 1.30 + ₹5 platform fee
                clamped to ₹15 – ₹60
```

## Regulatory Compliance (IRDAI)

- Operates under **IRDAI Regulatory Sandbox** framework
- **24-hour activation wait** after policy purchase
- **30-day moratorium** for new subscribers
- **15-day free-look period** with full refund
- **10 explicit coverage exclusions** with IRDAI regulation references
- **Grievance redressal** via IRDAI IGMS portal

## Tech Stack

- **Python 3.10+** · FastAPI · scikit-learn · pandas · numpy
- No external API calls — fully offline capable
- Single `uvicorn` process — no infra dependencies
