from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ClaimCondition(str, Enum):
    clear = "Clear"
    heavy_rain = "Heavy Rain"
    storm = "Storm"
    cyclone = "Cyclone"


class DisruptionCategory(str, Enum):
    rain = "Extreme Rain Alert"
    traffic = "Severe Traffic Gridlock"
    social = "Social Disruption / Active Event"


class ClaimStatus(str, Enum):
    approved = "APPROVED"
    denied = "DENIED"
    review = "REVIEW"


class GPSTelemetry(BaseModel):
    latitude: float
    longitude: float
    altitude: float | None = None
    accuracy: float | None = None
    altitudeAccuracy: float | None = None
    heading: float | None = None
    speed: float | None = None
    timestamp: int | None = None


class DriverProfile(BaseModel):
    driver_id: str
    display_name: str
    home_base: str


class ClaimSubmission(BaseModel):
    driver_id: str = Field(min_length=3)
    location_query: str = Field(min_length=3, description="Human-readable address/city")
    category: DisruptionCategory
    photo_b64: str | None = None
    telemetry: GPSTelemetry | None = None
    is_webdriver: bool = False
    payout_account: str | None = None
    demo_payout_override: float | None = None
    demo_reason_override: str | None = None
    weekly_earnings: float | None = None
    disruption_probability: float | None = None
    rider_note: str | None = None
    rider_note_lang: str | None = None
    rider_note_en: str | None = None


class OracleSnapshot(BaseModel):
    latitude: float
    longitude: float
    precipitation_mm: float
    wind_speed_kmh: float
    snowfall_cm: float
    observed_condition: ClaimCondition
    social_disruption_score: float = 0.0
    traffic_congestion_score: float = 0.0


class ClaimDecision(BaseModel):
    claim_id: str
    driver_id: str
    status: ClaimStatus
    approved_hours: float
    payout_inr: float
    reason: str
    rider_note: str | None = None
    rider_note_lang: str | None = None
    rider_note_en: str | None = None
    strikes_after_decision: int
    restricted: bool
    oracle: OracleSnapshot
    processed_at: datetime
    is_settled: bool = False
    transaction_id: str | None = None
    location_query: str | None = None
    fraud_flag: str = "OK"
    fraud_score: float = 0.0


class DriverForensicState(BaseModel):
    driver_id: str
    display_name: str
    strikes: int
    approved_claims: int
    denied_claims: int
    restricted: bool
    forensic_history_score: float
    last_lat: float | None = None
    last_lon: float | None = None
    last_gps_time: int | None = None


class DashboardSnapshot(BaseModel):
    generated_at: datetime
    total_claims: int
    approval_rate: float
    local_volatility: float
    traffic_density: float
    forensic_history_risk: float
    real_time_risk_score: float
    risk_trend: list[float]
    payout_exposure_inr: float


class PolicyRule(BaseModel):
    title: str
    detail: str


class PolicyDocument(BaseModel):
    generated_at: datetime
    payout_rules: dict[str, float]
    strike_policy: list[PolicyRule]
    consensus_description: list[PolicyRule]


class PayoutTransferRequest(BaseModel):
    claim_id: str
    payout_account: str
