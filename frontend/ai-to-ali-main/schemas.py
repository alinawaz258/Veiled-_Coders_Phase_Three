"""Pydantic schemas for request/response payloads.

Defines the API contract between the GigShield AI microservice and
the Node.js backend. All new Phase-2 fields are *additive* so the
existing frontend / backend integration continues to work.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FraudFlag(str, Enum):
    CLEAN = "Clean"
    REVIEW = "Review"
    SUSPICIOUS = "Suspicious"
    BLOCK = "Block"


class RiskPredictionRequest(BaseModel):
    city: str
    avg_daily_income: float = Field(..., ge=0)
    weekly_earnings: float = Field(..., ge=0)
    avg_work_hours: float = Field(..., ge=0, le=24)
    deliveries_per_day: int = Field(..., ge=0)
    rainfall_forecast_mm: float = Field(..., ge=0)
    temperature_forecast_c: float = Field(..., ge=-20, le=60)
    aqi_forecast: float = Field(..., ge=0)
    flood_risk: float = Field(..., ge=0, le=1)
    traffic_index: float = Field(..., ge=0, le=1)
    historical_disruption_rate: float = Field(..., ge=0, le=1)

    platform: str = "Other"
    zone_id: str | None = None
    active_days_per_week: int = Field(default=6, ge=1, le=7)
    weeks_on_platform: int | None = Field(default=None, ge=0)
    curfew_risk: float = Field(default=0.0, ge=0, le=1)
    strike_risk: float = Field(default=0.0, ge=0, le=1)
    coverage_month: int | None = Field(default=None, ge=1, le=12)


class RiskPredictionResponse(BaseModel):
    disruption_probability: float
    ml_probability: float
    risk_level: str
    expected_loss_inr: float
    fraud_score: float
    fraud_flag: FraudFlag
    model_version: str
