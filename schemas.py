"""GigShield AI — Pydantic v2 / dataclass schemas (v3.0.0)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ────────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    VERY_LOW = "Very Low"
    LOW      = "Low"
    MEDIUM   = "Medium"
    HIGH     = "High"
    CRITICAL = "Critical"

class PlanTier(str, Enum):
    BASIC    = "Basic"
    STANDARD = "Standard"
    PREMIUM  = "Premium"

class FraudFlag(str, Enum):
    CLEAN      = "Clean"
    REVIEW     = "Review"
    SUSPICIOUS = "Suspicious"
    BLOCK      = "Block"

class DeliveryPlatform(str, Enum):
    BLINKIT = "Blinkit"
    ZEPTO   = "Zepto"


# ── GPS telemetry (for kinematic fraud check from consensus engine) ────────────

class GPSTelemetry(BaseModel):
    """GPS point for kinematic anomaly detection.
    Matches the GigShieldConsensusEngine telemetry payload format.
    """
    latitude:      float | None = None
    longitude:     float | None = None
    altitude:      float | None = None
    accuracy:      float | None = None
    speed:         float | None = None
    heading:       float | None = None
    timestamp_ms:  int | None = None   # Unix ms — checked for staleness


# ── Request ─────────────────────────────────────────────────────────────────────

class RiskPredictionRequest(BaseModel):
    """Input payload for weekly disruption risk prediction (v3).

    New in v3:
    - coverage_month: drives seasonal premium multiplier
    - telemetry / prior_telemetry: enables kinematic fraud detection
    """
    # Rider identity
    city:                      str
    avg_daily_income:          float = Field(..., ge=0)
    weekly_earnings:           float = Field(..., ge=0)
    avg_work_hours:            float = Field(..., ge=0, le=24)
    deliveries_per_day:        int = Field(..., ge=0)
    rainfall_forecast_mm:      float | None = Field(default=None, ge=0)
    temperature_forecast_c:    float | None = Field(default=None, ge=-20, le=60)
    flood_risk:                float | None = Field(default=None, ge=0, le=1)
    traffic_index:             float | None = Field(default=None, ge=0, le=1)
    historical_disruption_rate: float | None = Field(default=None, ge=0, le=1)

    # Defaults
    platform:              DeliveryPlatform = DeliveryPlatform.ZEPTO
    zone_id:               str | None    = None
    active_days_per_week:  int           = Field(default=6, ge=1, le=7)
    weeks_on_platform:     int | None    = Field(default=None, ge=0)
    curfew_risk:           float         = Field(default=0.0, ge=0, le=1)
    strike_risk:           float         = Field(default=0.0, ge=0, le=1)

    # v3 additions
    coverage_month:        int | None    = Field(default=None, ge=1, le=12)
    telemetry:             GPSTelemetry | None = None  # current GPS for kinematic check
    prior_telemetry:       GPSTelemetry | None = None  # previous GPS point

    @field_validator("platform", mode="before")
    @classmethod
    def validate_platform(cls, v: object) -> str:
        allowed = {p.value for p in DeliveryPlatform}
        if str(v) not in allowed:
            raise ValueError(
                f"Invalid platform '{v}'. Allowed values: {sorted(allowed)}. "
                "GigShield currently supports Zepto and Blinkit only."
            )
        return v


# ── Sub-response objects ─────────────────────────────────────────────────────────

class ComponentScores(BaseModel):
    """Explainability sub-scores (for audit trail only — not decision-driving)."""
    weather_risk:    float
    location_risk:   float
    historical_risk: float
    social_risk:     float

class FeatureContribution(BaseModel):
    """Pseudo-SHAP per-feature attribution."""
    feature:      str
    contribution: float
    label:        str
    direction:    str   # 'increasing' or 'decreasing'

class ConfidenceBand(BaseModel):
    """Statistical prediction confidence interval from CV std."""
    lower:  float
    upper:  float
    cv_std: float
    margin: float

class PremiumBreakdown(BaseModel):
    """Transparent premium decomposition (v3.1: adds zone_loading_inr)."""
    expected_loss_inr:   float
    risk_loading_inr:    float
    seasonal_loading_inr: float   # monsoon / seasonal adjustment
    zone_loading_inr:    float = 0.0  # hyper-local zone surcharge (₹1–₹5)
    platform_fee_inr:    float
    total_premium_inr:   int

class SeasonalPricingInfo(BaseModel):
    """Seasonal context for the premium calculation."""
    month:              int
    season:             str    # 'sw_monsoon', 'ne_monsoon', 'pre_monsoon', 'winter'
    premium_multiplier: float
    cap_multiplier:     float
    is_monsoon_season:  bool
    rationale:          str

class FraudAssessment(BaseModel):
    """Six-signal fraud assessment with named sub-scores."""
    anomaly_score:          float
    flag:                   FraudFlag
    signals:                dict[str, float]
    requires_manual_review: bool

class PolicyTerms(BaseModel):
    """IRDAI-compliant policy terms."""
    plan:                    PlanTier
    weekly_premium_inr:      int
    max_claims_per_week:     int
    rain_payout_inr:         int
    heavy_rain_payout_inr:   int
    curfew_payout_inr:       int
    emergency_payout_inr:    int
    covered_triggers:        list[str]
    explicit_exclusions:     list[str]
    weekly_aggregate_cap_inr: int
    irdai_sandbox_compliant: bool = True
    activation_wait_hours:   int  = 24
    free_look_period_hours:  int  = 6


# ── Full response ────────────────────────────────────────────────────────────────

class RiskPredictionResponse(BaseModel):
    """v3.1: ML is primary signal. Zone pricing + enhanced explainability."""
    # PRIMARY: ML output drives everything
    disruption_probability:  float       # GBM output — primary decision signal
    risk_level:              RiskLevel   # derived from ML probability
    # EXPLAINABILITY: heuristic score for audit and rider-facing breakdown
    explainability_score:    float       # heuristic weighted sum (audit trail only)
    component_scores:        ComponentScores
    feature_contributions:   list[FeatureContribution]
    confidence_band:         ConfidenceBand
    # Financial
    expected_loss_inr:       float
    premium_breakdown:       PremiumBreakdown
    seasonal_pricing:        SeasonalPricingInfo
    zone_pricing:            dict = {}   # hyper-local zone adjustment details
    # Policy
    policy_terms:            PolicyTerms
    # Fraud
    fraud:                   FraudAssessment
    fraud_score:             float
    fraud_flag:              FraudFlag
    # Traceability
    ml_probability:          float
    # Metadata
    city:                    str
    platform:                str
    model_version:           str = "3.1.0"


# ── Model and utility responses ───────────────────────────────────────────────────

class ClaimRequest(BaseModel):
    """Input payload for forensic claim submission."""
    city:         str
    platform:     str
    reason:       str
    evidence_url: str | None = None
    telemetry:    GPSTelemetry | None = None
    timestamp:    str | None = None  # ISO format UTC

class ClaimResponse(BaseModel):
    """Output for claim submission and ledger."""
    claim_id:      str
    status:        str  # 'PENDING', 'APPROVED', 'REJECTED'
    payout_amount: int
    audit_verdict: str
    city:          str
    platform:      str
    reason:        str
    timestamp:     str

class ModelMetricsResponse(BaseModel):
    version:              str
    n_samples:            int
    n_features:           int
    features:             list[str]
    r2_test:              float
    mae_test:             float
    rmse_test:            float
    cv_r2_mean:           float
    cv_r2_std:            float
    linear_baseline_r2:   float     # NEW: proves non-linearity
    nonlinearity_gap:     float     # GBM R² - Linear R²
    feature_importances:  dict[str, float]
    causal_nonlinearities: dict[str, str]
    gbm_params:           dict

class RetrainResponse(BaseModel):
    message:              str
    samples_used:         int
    model_path:           str
    r2_score:             float
    rmse_score:           float
    linear_baseline_r2:   float
    nonlinearity_gap:     float
    feature_importances:  dict[str, float]

class HealthResponse(BaseModel):
    status:        str
    model_loaded:  bool
    model_version: str

class RegExclusionsResponse(BaseModel):
    count:      int
    exclusions: list[str]
