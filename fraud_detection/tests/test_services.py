from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta

from fraud_detection.app.models import ClaimCondition, ClaimSubmission, OracleSnapshot, DisruptionCategory, GPSTelemetry
from fraud_detection.app.services import GigShieldConsensusEngine


def test_consensus_approves_when_observed_matches(monkeypatch) -> None:
    engine = GigShieldConsensusEngine()

    def fake_scan(*args, **kwargs):
        return {
            "latitude": 41.0,
            "longitude": -87.0,
            "precipitation_mm": 10.0,
            "wind_speed_kmh": 40.0,
            "snowfall_cm": 0.0,
            "weather_code": 65, # Heavy rain WMO code
            "social_disruption_score": 50.0,
            "traffic_congestion_score": 80.0,
            "detected_condition": ClaimCondition.heavy_rain.value,
        }

    monkeypatch.setattr(engine, "realtime_scan", fake_scan)
    
    current_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    decision = engine.process_claim(
        ClaimSubmission(
            driver_id="DRV-100",
            location_query="Chicago, IL",
            category=DisruptionCategory.rain,
            telemetry=GPSTelemetry(
                latitude=41.0, longitude=-87.0, 
                altitude=10.0, accuracy=5.0, heading=90.0, speed=10.0,
                timestamp=current_ms
            )
        )
    )

    assert decision.status.value == "APPROVED"
    assert decision.payout_inr > 0.0


def test_three_strikes_restricts_account(monkeypatch) -> None:
    engine = GigShieldConsensusEngine()

    def fake_scan(*args, **kwargs):
        return {
            "latitude": 41.0,
            "longitude": -87.0,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 5.0,
            "snowfall_cm": 0.0,
            "weather_code": 0, # Clear
            "social_disruption_score": 10.0,
            "traffic_congestion_score": 20.0,
            "detected_condition": ClaimCondition.clear.value,
        }

    monkeypatch.setattr(engine, "realtime_scan", fake_scan)

    for _ in range(3):
        decision = engine.process_claim(
            ClaimSubmission(
                driver_id="DRV-220",
                location_query="Boston, MA",
                category=DisruptionCategory.rain,
                telemetry=GPSTelemetry(
                    latitude=42.0, longitude=-71.0, 
                    altitude=10.0, accuracy=5.0, heading=90.0, speed=10.0,
                    timestamp=int(datetime.now(timezone.utc).timestamp() * 1000)
                )
            )
        )

    assert decision.restricted is True
    assert decision.strikes_after_decision == 3


def test_headless_bot_rejected() -> None:
    engine = GigShieldConsensusEngine()
    
    decision = engine.process_claim(
        ClaimSubmission(
            driver_id="DRV-BOT",
            location_query="Seattle, WA",
            category=DisruptionCategory.rain,
            is_webdriver=True,
        )
    )
    
    assert decision.status.value == "DENIED"
    assert "WebDriver" in decision.reason


def test_temporal_spoofing_rejected() -> None:
    engine = GigShieldConsensusEngine()
    
    # 20 minutes ago (stale payload)
    stale_time_ms = int((datetime.now(timezone.utc) - timedelta(minutes=20)).timestamp() * 1000)
    
    decision = engine.process_claim(
        ClaimSubmission(
            driver_id="DRV-STALE",
            location_query="Miami, FL",
            category=DisruptionCategory.rain,
            telemetry=GPSTelemetry(
                latitude=25.0, longitude=-80.0, 
                altitude=10.0, accuracy=5.0, heading=90.0, speed=10.0,
                timestamp=stale_time_ms
            )
        )
    )
    
    assert decision.status.value == "DENIED"
    assert "Temporal Spoofing" in decision.reason


def test_teleportation_spoofed() -> None:
    engine = GigShieldConsensusEngine()
    
    driver_id = "DRV-TELEPORT"
    current_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    five_min_ago_ms = current_ms - (5 * 60 * 1000)
    
    # First valid claim to set last position
    decision1 = engine.process_claim(
        ClaimSubmission(
            driver_id=driver_id,
            location_query="Austin, TX",
            category=DisruptionCategory.rain,
            telemetry=GPSTelemetry(
                latitude=30.2672, longitude=-97.7431, # Austin center
                altitude=10.0, accuracy=5.0, heading=90.0, speed=10.0,
                timestamp=five_min_ago_ms
            )
        )
    )
    # Don't care if denied due to clear weather, GPS state is still saved
    
    # Second claim 25km away but only 5 minutes later (implies 300 km/h)
    
    decision2 = engine.process_claim(
        ClaimSubmission(
            driver_id=driver_id,
            location_query="Round Rock, TX",
            category=DisruptionCategory.rain,
            telemetry=GPSTelemetry(
                latitude=30.5083, longitude=-97.6789, # Round rock (~25-30 km away)
                altitude=10.0, accuracy=5.0, heading=90.0, speed=10.0,
                timestamp=current_ms
            )
        )
    )
    
    assert decision2.status.value == "DENIED"
    assert "Teleportation" in decision2.reason
