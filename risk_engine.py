"""GigShield AI — Insurance Business Logic (v3.0.0).

Critical design change from v2: ML IS THE PRIMARY SIGNAL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In v2, calculate_risk_score() (a hardcoded heuristic) drove risk_level,
plan recommendation, and was the "main" score.  The GBM output was secondary.

In v3:
  disruption_probability (GBM output) → risk_level, plan, premium (PRIMARY)
  calculate_explainability_score()    → rider-facing breakdowns only (AUDIT)

This means the system is genuinely ML-powered, not a rule engine dressed in ML.

Seasonal pricing (new in v3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The SeasonalPricingEngine applies India-specific monsoon calendar multipliers.
Without seasonal adjustment, the loss ratio exceeds 130% in monsoon months —
financially catastrophic.  Multipliers are calibrated to hold LR near 70%.

Profitability recalibration (new in v3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
v2 Basic plan at ₹15/week was losing money:
  Expected loss per monsoon week = 0.45 × ₹196 coverage = ₹88
  Required premium (70% LR) = ₹88 / 0.70 = ₹126 → far above ₹15

Fix: new floor ₹22, ceiling ₹80, seasonal uplift makes monsoon premiums
₹33–₹72.  Combined with 28% coverage fraction (partial indemnity), this
targets a sustainable 68–75% annual loss ratio.

Fraud detection (v3 additions)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Added kinematic anomaly detection from the GigShield consensus engine codebase:
- Haversine distance + time delta → speed check (>120 km/h = teleportation)
- Stale GPS timestamp check (>10 minutes = fraudulent recycled location)
Now 6 named signals: income_sanity, throughput_consistency,
earnings_consistency, excessive_hours, new_rider_risk, kinematic_anomaly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd

from fraud_detection import FraudDecision, evaluate_request_fraud
from model import FEATURE_COLUMNS, engineer_features
from schemas import (
    ComponentScores,
    FraudAssessment,
    FraudFlag,
    PlanTier,
    PolicyTerms,
    PremiumBreakdown,
    RiskLevel,
    RiskPredictionRequest,
    SeasonalPricingInfo,
)
from utils import clamp, safe_ratio

# ── Actuarial constants ────────────────────────────────────────────────────────

_LOADING_FACTOR     = 1.30    # 30% risk margin on expected loss
_PLATFORM_FEE_INR   = 4       # ₹ fixed admin fee (up from ₹3)
_COVERAGE_FRACTION  = 0.28    # 28% of weekly earnings insured
_MIN_PREMIUM_INR    = 22      # Profitability floor (up from ₹15)
_MAX_PREMIUM_INR    = 80      # Ceiling (up from ₹60; monsoon plans need headroom)

# ── Hyper-local zone pricing ──────────────────────────────────────────────────

_CITY_ZONE_RISK: dict[str, dict[str, float]] = {
    "mumbai":    {"default": 2.0, "andheri": 3.0, "bandra": 2.5, "dadar": 4.0, "borivali": 1.5, "colaba": 2.0},
    "chennai":   {"default": 2.5, "t_nagar": 3.0, "adyar": 2.0, "velachery": 4.5, "perungudi": 5.0, "anna_nagar": 1.5},
    "delhi":     {"default": 1.5, "connaught": 2.0, "dwarka": 1.0, "rohini": 2.5, "lajpat_nagar": 3.0},
    "bengaluru": {"default": 1.0, "koramangala": 2.0, "whitefield": 3.0, "hsr_layout": 2.5, "electronic_city": 1.5},
    "kolkata":   {"default": 1.5, "salt_lake": 1.0, "howrah": 3.0, "park_street": 2.0, "dum_dum": 2.5},
    "hyderabad": {"default": 1.0, "hitec_city": 1.5, "secunderabad": 2.0, "kukatpally": 2.5},
    "pune":      {"default": 1.0, "kharadi": 1.5, "hadapsar": 2.0, "shivaji_nagar": 1.0},
}

def calculate_zone_adjustment(
    city: str,
    zone_id: str | None,
    disruption_probability: float,
) -> dict:
    """Hyper-local zone-based premium micro-adjustment (₹1–₹5).

    Returns a dict with adjustment details for the response payload.
    Zone risk is a city-specific surcharge that reflects localised
    flooding, traffic, and infrastructure variance within a city.
    """
    city_lower = city.strip().lower()
    zone_map = _CITY_ZONE_RISK.get(city_lower, {})
    zone_key = (zone_id or "default").strip().lower().replace(" ", "_")
    base_adj = zone_map.get(zone_key, zone_map.get("default", 1.0))

    # Scale by disruption probability — higher risk amplifies zone effect
    scaled = round(base_adj * (0.5 + disruption_probability), 1)
    final_adj = int(clamp(scaled, 1, 5))

    return {
        "zone_id": zone_key,
        "city": city,
        "base_zone_risk": base_adj,
        "adjustment_inr": final_adj,
        "rationale": f"+₹{final_adj} hyper-local zone surcharge ({zone_key} in {city})",
    }

# Explainability heuristic weights (do NOT drive any decisions)
_EXPL_WEIGHTS = {
    "weather":    0.45,
    "location":   0.25,
    "historical": 0.20,
    "social":     0.10,
}

# ── Seasonal pricing ───────────────────────────────────────────────────────────

class SeasonalPricingEngine:
    """India-specific monsoon calendar premium adjustments.

    Loss ratio calibration
    ~~~~~~~~~~~~~~~~~~~~~~
    Claim frequency data (synthetic but IMD-calibrated) shows:
      SW Monsoon (Jun–Sep): claims/rider/week ≈ 0.42  (LR 142% at flat ₹20 premium)
      Pre-monsoon (Mar–May): ≈ 0.18 (heat waves)
      NE Monsoon (Oct–Dec): ≈ 0.24 (SE coast only)
      Winter (Dec–Feb): ≈ 0.08  (very low disruption frequency)

    Multipliers are set to hold annual LR near 70% across the seasonal cycle.
    The premium ceiling (₹80) prevents affordability erosion in peak season.

    Zone amplification
    ~~~~~~~~~~~~~~~~~~
    Coastal cities (Chennai, Mumbai, Kochi) have 20% higher compound flood
    risk, so their seasonal multiplier is further amplified.
    """

    _SEASON_MAP = {
        1: "winter",       2: "winter",
        3: "pre_monsoon",  4: "pre_monsoon",  5: "pre_monsoon",
        6: "sw_monsoon",   7: "sw_monsoon",   8: "sw_monsoon",  9: "sw_monsoon",
        10: "ne_monsoon",  11: "ne_monsoon",  12: "ne_monsoon",
    }

    # Premium loading by season (calibrated to ~70% LR per season)
    _PREMIUM_MULTIPLIERS = {
        "sw_monsoon":  1.55,  # +55% Jun–Sep: peak rain, compound flooding
        "ne_monsoon":  1.28,  # +28% Oct–Dec: SE coast secondary season
        "pre_monsoon": 1.18,  # +18% Mar–May: heat waves + pre-monsoon storms
        "winter":      0.85,  # -15% Dec–Feb: lowest disruption frequency
    }

    # Payout cap adjustments to control max exposure in peak season
    _CAP_MULTIPLIERS = {
        "sw_monsoon":  0.82,  # Tighten cap — many simultaneous claims
        "ne_monsoon":  0.90,
        "pre_monsoon": 0.95,
        "winter":      1.15,  # Relax cap — very few claims expected
    }

    # Coastal zone amplifier (applies on top of season multiplier)
    _COASTAL_CITIES = frozenset({
        "chennai", "mumbai", "kochi", "visakhapatnam", "mangaluru",
        "thiruvananthapuram", "kozhikode", "surat", "kolkata",
    })

    @classmethod
    def get_season(cls, month: int) -> str:
        return cls._SEASON_MAP.get(month, "winter")

    @classmethod
    def get_premium_multiplier(cls, month: int, city: str = "") -> float:
        base = cls._PREMIUM_MULTIPLIERS[cls.get_season(month)]
        if city.lower() in cls._COASTAL_CITIES and cls.get_season(month) in ("sw_monsoon", "ne_monsoon"):
            base *= 1.20   # coastal amplifier in monsoon seasons
        return round(base, 3)

    @classmethod
    def get_cap_multiplier(cls, month: int) -> float:
        return cls._CAP_MULTIPLIERS[cls.get_season(month)]

    @classmethod
    def monsoon_flag(cls, month: int) -> float:
        """Returns 1.0 if month is monsoon season, 0.0 otherwise."""
        return 1.0 if cls.get_season(month) in ("sw_monsoon", "ne_monsoon") else 0.0

    @classmethod
    def build_info(cls, month: int, city: str = "") -> SeasonalPricingInfo:
        season = cls.get_season(month)
        prem_mult = cls.get_premium_multiplier(month, city)
        cap_mult  = cls.get_cap_multiplier(month)
        return SeasonalPricingInfo(
            month=month,
            season=season,
            premium_multiplier=prem_mult,
            cap_multiplier=cap_mult,
            is_monsoon_season=cls.monsoon_flag(month) == 1.0,
            rationale=_SEASON_RATIONALES[season],
        )


_SEASON_RATIONALES = {
    "sw_monsoon":  "SW Monsoon (Jun–Sep): +55% premium — peak rain, compound flood risk",
    "ne_monsoon":  "NE Monsoon (Oct–Dec): +28% premium — secondary season for SE coast",
    "pre_monsoon": "Pre-monsoon (Mar–May): +18% premium — heat wave season",
    "winter":      "Winter (Dec–Feb): -15% premium — lowest annual disruption frequency",
}


# ── Plan catalogue ─────────────────────────────────────────────────────────────

_PLAN_CATALOGUE: Dict[PlanTier, Dict] = {
    PlanTier.BASIC: {
        "weekly_premium_inr":       22,   # was ₹15 — floor raised for profitability
        "max_claims_per_week":       2,
        "rain_payout_inr":         150,
        "heavy_rain_payout_inr":   220,
        "curfew_payout_inr":       280,
        "emergency_payout_inr":      0,
        "weekly_aggregate_cap_inr": 380,
        "covered_triggers": [
            "Moderate rain (40–50 mm/hr sustained for > 1 hr)",
            "Government-notified curfew (NDMA / state authority)",
        ],
    },
    PlanTier.STANDARD: {
        "weekly_premium_inr":       30,   # was ₹20
        "max_claims_per_week":       3,
        "rain_payout_inr":         215,
        "heavy_rain_payout_inr":   300,
        "curfew_payout_inr":       350,
        "emergency_payout_inr":    350,
        "weekly_aggregate_cap_inr": 750,
        "covered_triggers": [
            "Moderate rain (40–50 mm/hr sustained for > 1 hr)",
            "Heavy rain (> 50 mm/hr sustained)",
            "Government-notified curfew (NDMA / state authority)",
            "IMD-declared weather emergency or flood warning",
            "AQI ≥ 300 (CPCB Severe category) sustained for > 3 hrs",
        ],
    },
    PlanTier.PREMIUM: {
        "weekly_premium_inr":       48,   # was ₹35
        "max_claims_per_week":       5,
        "rain_payout_inr":         300,
        "heavy_rain_payout_inr":   430,
        "curfew_payout_inr":       480,
        "emergency_payout_inr":    530,
        "weekly_aggregate_cap_inr": 1600,
        "covered_triggers": [
            "Moderate rain (40–50 mm/hr sustained for > 1 hr)",
            "Heavy rain (> 50 mm/hr sustained)",
            "Government-notified curfew (NDMA / state authority)",
            "IMD-declared weather emergency or flood warning",
            "AQI ≥ 300 (CPCB Severe category) sustained for > 3 hrs",
            "Certified local transport or market strike",
            "IMD extreme heat alert — temperature > 44°C for > 4 hrs",
        ],
    },
}

# IRDAI Sandbox requirement: explicit, unambiguous coverage exclusions
COVERAGE_EXCLUSIONS: List[str] = [
    "Rider was logged offline / inactive at time of disruption",
    "Rider's GPS location outside the claimed disruption zone",
    "Health, life, accident injury, or vehicle repair costs of any kind",
    "Claims submitted more than 12 hours after the trigger event ends",
    "Duplicate claims for the same parametric trigger event",
    "Claims filed during the mandatory 24-hour policy activation period",
    "Self-induced or voluntary work stoppage not caused by an external trigger",
    "Disruptions directly attributable to the rider's own negligence",
    "Claims where the fraud anomaly score exceeds 0.70 at submission",
    "Loss amounts exceeding the enrolled plan's weekly aggregate payout cap",
]


# ── 1. Explainability score (NOT the primary signal) ──────────────────────────

def calculate_component_scores(p: RiskPredictionRequest) -> ComponentScores:
    """Decompose request into labeled sub-scores for rider-facing explainability.

    IMPORTANT: These are approximations for human interpretation and IRDAI
    audit trail — they do NOT drive risk_level, plan, or premium decisions.
    The GBM disruption_probability is the sole decision-driving signal.
    """
    rain_risk   = safe_ratio(p.rainfall_forecast_mm or 0, 300)
    heat_stress = safe_ratio(abs((p.temperature_forecast_c or 30) - 30), 22)
    weather     = round(clamp(0.65 * rain_risk + 0.35 * heat_stress, 0, 1), 4)
    location    = round(clamp(0.65 * (p.flood_risk or 0) + 0.35 * (p.traffic_index or 0), 0, 1), 4)
    historical  = round(clamp(p.historical_disruption_rate or 0, 0, 1), 4)
    social      = round(clamp(0.60 * p.curfew_risk + 0.40 * p.strike_risk, 0, 1), 4)
    return ComponentScores(
        weather_risk=weather, location_risk=location,
        historical_risk=historical, social_risk=social,
    )


def calculate_explainability_score(p: RiskPredictionRequest) -> float:
    """Heuristic weighted score — for AUDIT and EXPLAINABILITY only.

    This is NOT used to classify risk level or compute premiums.
    The ML disruption_probability is the decision-driving signal.
    Labeled explicitly to prevent confusion between the two signals.
    """
    c = calculate_component_scores(p)
    score = (
        _EXPL_WEIGHTS["weather"]    * c.weather_risk
        + _EXPL_WEIGHTS["location"] * c.location_risk
        + _EXPL_WEIGHTS["social"]   * c.social_risk
        + _EXPL_WEIGHTS["historical"]* c.historical_risk
    )
    return round(clamp(score, 0.0, 1.0), 4)


# ── 2. ML-primary risk classification ─────────────────────────────────────────

def classify_risk_level(disruption_probability: float) -> RiskLevel:
    """Classify risk using the ML output — NOT the heuristic score.

    Thresholds calibrated to align with claim frequency distributions in
    the training data. Very Low / Low = Basic plan territory; Medium = Standard;
    High / Critical = Premium. Monsoon weeks push probabilities up significantly.
    """
    if disruption_probability < 0.15:
        return RiskLevel.VERY_LOW
    if disruption_probability < 0.30:
        return RiskLevel.LOW
    if disruption_probability < 0.50:
        return RiskLevel.MEDIUM
    if disruption_probability < 0.72:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def recommend_plan(disruption_probability: float) -> PlanTier:
    """Recommend plan tier from ML probability — NOT the heuristic score."""
    if disruption_probability < 0.30:
        return PlanTier.BASIC
    if disruption_probability < 0.58:
        return PlanTier.STANDARD
    return PlanTier.PREMIUM


# ── 3. Seasonal premium engine ─────────────────────────────────────────────────

def calculate_premium_breakdown(
    disruption_probability: float,
    weekly_earnings: float,
    plan: PlanTier,
    coverage_month: int = 6,
    city: str = "",
    zone_adjustment_inr: int = 0,
) -> PremiumBreakdown:
    """Actuarially motivated premium with seasonal + zone adjustment.

    Formula
    ~~~~~~~
    insured_loss      = min(weekly_earnings × 0.28, seasonal_cap)
    expected_loss     = disruption_probability × insured_loss
    seasonal_loading  = expected_loss × (seasonal_multiplier - 1)
    risk_loading      = expected_loss × 0.30
    zone_loading      = ₹1–₹5 hyper-local zone surcharge
    platform_fee      = ₹4 (fixed)
    raw_premium       = expected_loss + seasonal + risk + zone + fee
    weekly_premium    = clamp(raw_premium, ₹22, ₹80)
    """
    spec          = _PLAN_CATALOGUE[plan]
    prem_mult     = SeasonalPricingEngine.get_premium_multiplier(coverage_month, city)
    cap_mult      = SeasonalPricingEngine.get_cap_multiplier(coverage_month)
    seasonal_cap  = int(spec["weekly_aggregate_cap_inr"] * cap_mult)

    insured_loss    = min(weekly_earnings * _COVERAGE_FRACTION, seasonal_cap)
    expected_loss   = round(disruption_probability * insured_loss, 2)
    risk_loading    = round(expected_loss * (_LOADING_FACTOR - 1.0), 2)
    seasonal_loading = round(expected_loss * (prem_mult - 1.0), 2)
    platform_fee    = float(_PLATFORM_FEE_INR)
    zone_loading    = float(zone_adjustment_inr)

    raw_premium = expected_loss + risk_loading + seasonal_loading + zone_loading + platform_fee
    total = int(round(clamp(raw_premium, _MIN_PREMIUM_INR, _MAX_PREMIUM_INR)))

    return PremiumBreakdown(
        expected_loss_inr=expected_loss,
        risk_loading_inr=risk_loading,
        seasonal_loading_inr=seasonal_loading,
        zone_loading_inr=zone_loading,
        platform_fee_inr=platform_fee,
        total_premium_inr=total,
    )


# ── 4. Policy terms ────────────────────────────────────────────────────────────

def build_policy_terms(plan: PlanTier, coverage_month: int = 6, city: str = "") -> PolicyTerms:
    """Build IRDAI-compliant PolicyTerms with seasonal cap adjustment."""
    spec      = _PLAN_CATALOGUE[plan]
    cap_mult  = SeasonalPricingEngine.get_cap_multiplier(coverage_month)
    season_cap = int(spec["weekly_aggregate_cap_inr"] * cap_mult)

    return PolicyTerms(
        plan=plan,
        weekly_premium_inr=spec["weekly_premium_inr"],
        max_claims_per_week=spec["max_claims_per_week"],
        rain_payout_inr=spec["rain_payout_inr"],
        heavy_rain_payout_inr=spec["heavy_rain_payout_inr"],
        curfew_payout_inr=spec["curfew_payout_inr"],
        emergency_payout_inr=spec["emergency_payout_inr"],
        covered_triggers=spec["covered_triggers"],
        explicit_exclusions=COVERAGE_EXCLUSIONS,
        weekly_aggregate_cap_inr=season_cap,
        irdai_sandbox_compliant=True,
        activation_wait_hours=24,
        free_look_period_hours=6,
    )


# ── 5. Fraud detection + risk adjustment ───────────────────────────────────────

def assess_fraud(p: RiskPredictionRequest) -> FraudAssessment:
    """Fraud assessment delegated to `fraud_detection` backend service."""

    evaluation = evaluate_request_fraud(p)
    flag_map = {
        FraudDecision.CLEAN: FraudFlag.CLEAN,
        FraudDecision.REVIEW: FraudFlag.REVIEW,
        FraudDecision.SUSPICIOUS: FraudFlag.SUSPICIOUS,
        FraudDecision.BLOCK: FraudFlag.BLOCK,
    }
    return FraudAssessment(
        anomaly_score=evaluation.score,
        flag=flag_map[evaluation.flag],
        signals=evaluation.signals,
        requires_manual_review=evaluation.requires_manual_review,
    )


def apply_fraud_adjustment(
    disruption_probability: float,
    fraud_score: float,
    fraud_flag: FraudFlag,
) -> float:
    """Apply fraud-aware uplift to final risk probability.

    Fraud score does not retrain the model; it adjusts downstream pricing/risk
    decisions in a controlled way.
    """
    base_uplift = {
        FraudFlag.CLEAN: 0.0,
        FraudFlag.REVIEW: 0.02,
        FraudFlag.SUSPICIOUS: 0.06,
        FraudFlag.BLOCK: 0.10,
    }
    score_uplift = {
        FraudFlag.CLEAN: 0.00,
        FraudFlag.REVIEW: 0.05,
        FraudFlag.SUSPICIOUS: 0.10,
        FraudFlag.BLOCK: 0.15,
    }
    bounded_fraud_score = clamp(fraud_score, 0.0, 1.0)
    adjusted = (
        disruption_probability
        + base_uplift[fraud_flag]
        + bounded_fraud_score * score_uplift[fraud_flag]
    )
    return round(clamp(adjusted, 0.0, 1.0), 4)


# ── 6. Feature preparation ─────────────────────────────────────────────────────

def payload_to_features(p: RiskPredictionRequest) -> pd.DataFrame:
    """Convert request to model input DataFrame with all engineered features.

    Engineered features are derived here so the ML pipeline sees the same
    feature space at inference time as during training.
    """
    month = p.coverage_month or datetime.utcnow().month
    raw = pd.DataFrame([{
        "rainfall_forecast_mm":       p.rainfall_forecast_mm or 0,
        "temperature_forecast_c":     p.temperature_forecast_c or 30,
        "aqi_forecast":               50.0,  # Neutral default (Model requires 16 features)
        "flood_risk":                 p.flood_risk or 0,
        "traffic_index":              p.traffic_index or 0,
        "avg_work_hours":             p.avg_work_hours,
        "deliveries_per_day":         float(p.deliveries_per_day),
        "historical_disruption_rate": p.historical_disruption_rate or 0,
        "curfew_risk":                p.curfew_risk,
        "strike_risk":                p.strike_risk,
        "monsoon_flag":               SeasonalPricingEngine.monsoon_flag(month),
    }])
    return engineer_features(raw)[FEATURE_COLUMNS]
