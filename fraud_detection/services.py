from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING

from .models import FraudDecision, FraudEvaluation

if TYPE_CHECKING:
    from schemas import RiskPredictionRequest


_INCOME_PER_DEL_MAX = 80.0
_INCOME_MAX_DAILY_INR = 2500.0
_MAX_RIDER_SPEED_KMH = 120.0
_GPS_STALE_MINUTES = 10


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _safe_ratio(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return _clamp(value / max_value, 0.0, 1.0)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(max(a, 0)))


def _kinematic_anomaly_score(payload: "RiskPredictionRequest") -> float:
    telemetry = payload.telemetry
    prior = payload.prior_telemetry
    if not telemetry:
        return 0.0

    score = 0.0

    if telemetry.timestamp_ms:
        now_ms = datetime.utcnow().timestamp() * 1000
        age_min = abs(now_ms - telemetry.timestamp_ms) / 60_000
        if age_min > _GPS_STALE_MINUTES:
            score = max(score, min(age_min / 60.0, 1.0))

    if (
        telemetry
        and prior
        and telemetry.latitude is not None
        and telemetry.longitude is not None
        and prior.latitude is not None
        and prior.longitude is not None
    ):
        dist_km = _haversine(prior.latitude, prior.longitude, telemetry.latitude, telemetry.longitude)
        delta_ms = abs((telemetry.timestamp_ms or 0) - (prior.timestamp_ms or 0))
        delta_hours = delta_ms / 3_600_000.0
        if 0.001 < delta_hours < 5.0:
            speed = dist_km / delta_hours
            if speed > _MAX_RIDER_SPEED_KMH:
                score = max(score, _clamp((speed - _MAX_RIDER_SPEED_KMH) / 200.0, 0.0, 1.0))

    return round(score, 4)


def evaluate_request_fraud(payload: "RiskPredictionRequest") -> FraudEvaluation:
    """Evaluate fraud risk for a pricing request.

    Reuses the fraud subsystem strategy (kinematic checks and telemetry-age checks)
    and combines it with pricing-request consistency signals.
    """
    signals: dict[str, float] = {}

    income_per_delivery = payload.avg_daily_income / max(payload.deliveries_per_day, 1)
    signals["income_sanity"] = round(
        _clamp(
            max(
                _safe_ratio(income_per_delivery, _INCOME_PER_DEL_MAX),
                _safe_ratio(max(payload.avg_daily_income - _INCOME_MAX_DAILY_INR, 0), _INCOME_MAX_DAILY_INR),
            ),
            0.0,
            1.0,
        ),
        4,
    )

    expected_max_deliveries = payload.avg_work_hours * 4.0
    signals["throughput_consistency"] = round(
        _clamp(payload.deliveries_per_day / max(expected_max_deliveries, 1) - 1.0, 0.0, 1.0),
        4,
    )

    implied_weekly = payload.avg_daily_income * payload.active_days_per_week
    signals["earnings_consistency"] = round(
        _clamp(abs(payload.weekly_earnings - implied_weekly) / max(implied_weekly, 1), 0.0, 1.0),
        4,
    )

    signals["excessive_hours"] = round(_safe_ratio(max(payload.avg_work_hours - 12, 0), 4), 4)

    weeks = payload.weeks_on_platform
    signals["new_rider_risk"] = round(
        0.80 if weeks is not None and weeks < 2
        else 0.35 if weeks is not None and weeks < 8
        else 0.30 if weeks is None
        else 0.00,
        4,
    )

    signals["kinematic_anomaly"] = _kinematic_anomaly_score(payload)

    weights = {
        "income_sanity": 0.32,
        "throughput_consistency": 0.28,
        "earnings_consistency": 0.18,
        "excessive_hours": 0.09,
        "new_rider_risk": 0.05,
        "kinematic_anomaly": 0.08,
    }
    score = round(_clamp(sum(signals[k] * w for k, w in weights.items()), 0.0, 1.0), 4)

    if score < 0.35:
        flag = FraudDecision.CLEAN
    elif score < 0.55:
        flag = FraudDecision.REVIEW
    elif score < 0.70:
        flag = FraudDecision.SUSPICIOUS
    else:
        flag = FraudDecision.BLOCK

    return FraudEvaluation(
        score=score,
        flag=flag,
        signals=signals,
        requires_manual_review=flag is not FraudDecision.CLEAN,
    )
