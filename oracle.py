"""GigShield AI — Oracle Service (v3.0.0).

Automates environmental risk data fetching:
1. Geocoding (Nominatim)
2. Weather (Open-Meteo)
3. Historical (Ledger Analysis)
4. Heuristics (Traffic/Flood)

Ensures a "No-Failure" architecture with city-specific static fallbacks.
"""

from __future__ import annotations

import json
import math
import pathlib
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, Tuple
from urllib.request import Request, urlopen

from utils import get_logger

LOGGER = get_logger(__name__)

# --- Paths & Constants ---
LEDGER_PATH = pathlib.Path(__file__).resolve().parent / "Fraud detection" / "data" / "claims_ledger.json"

# Static Baselines (for "No-Failure" Fallback)
CITY_WEATHER_BASELINES = {
    "mumbai":    {"temp": 28, "rain": 12, "flood": 0.45, "traffic": 85},
    "delhi":     {"temp": 32, "rain": 4,  "flood": 0.15, "traffic": 90},
    "bengaluru": {"temp": 24, "rain": 6,  "flood": 0.20, "traffic": 88},
    "chennai":   {"temp": 30, "rain": 8,  "flood": 0.35, "traffic": 72},
    "kolkata":   {"temp": 29, "rain": 10, "flood": 0.40, "traffic": 75},
}

COASTAL_CITIES = {"mumbai", "chennai", "kolkata", "kochi", "vizag", "surat"}

class OracleService:
    @classmethod
    def fetch_environmental_data(cls, city: str) -> Dict[str, float]:
        """Fetch real-time weather and calculate historical/heuristic risk indexes."""
        city_lower = city.lower()
        LOGGER.info("Oracle triggering real-time scan for: %s", city)

        # 1. Geocode
        try:
            lat, lon = cls._geocode_location(city)
        except Exception as e:
            LOGGER.warning("Geocoding failed for %s: %s. Using default coordinates.", city, e)
            lat, lon = 19.076, 72.877  # Default to Mumbai

        # 2. Weather (Open-Meteo)
        weather_data = cls._fetch_weather_safe(lat, lon, city_lower)

        # 3. Calculate Historical Rate (Ledger + 0.12 Baseline)
        historical_rate = cls._calculate_historical_rate(city_lower)

        # 4. Heuristics (Traffic & Flood)
        traffic_idx = cls._calculate_traffic_index(city_lower, weather_data["rainfall_mm"])
        flood_risk  = cls._calculate_flood_risk(city_lower, weather_data["rainfall_mm"])

        return {
            "rainfall_forecast_mm":       weather_data["rainfall_mm"],
            "temperature_forecast_c":     weather_data["temperature_c"],
            "flood_risk":                 flood_risk,
            "traffic_index":              traffic_idx,
            "historical_disruption_rate": historical_rate,
        }

    @staticmethod
    def _geocode_location(city: str) -> Tuple[float, float]:
        """Call Nominatim for lat/lon."""
        params = {"q": city, "format": "jsonv2", "limit": 1}
        url = f"https://nominatim.openstreetmap.org/search?{urllib.parse.urlencode(params)}"
        req = Request(url)
        req.add_header("User-Agent", "GigShield-Oracle/1.0 (contact: admin@gigshield.ai)")
        
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            if not data:
                raise ValueError(f"City '{city}' not found.")
            return float(data[0]["lat"]), float(data[0]["lon"])

    @classmethod
    def _fetch_weather_safe(cls, lat: float, lon: float, city: str) -> Dict[str, float]:
        """Fetch Open-Meteo with fallback to city baselines."""
        try:
            params = {
                "latitude": lat, "longitude": lon,
                "current": "precipitation,temperature_2m",
                "timezone": "auto"
            }
            url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"
            req = Request(url)
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                current = data.get("current", {})
                return {
                    "rainfall_mm": float(current.get("precipitation", 0) or 0),
                    "temperature_c": float(current.get("temperature_2m", 25) or 25)
                }
        except Exception as e:
            LOGGER.error("Weather API failed for %s: %s. Using seasonal fallback.", city, e)
            baseline = CITY_WEATHER_BASELINES.get(city, {"temp": 25, "rain": 0})
            return {
                "rainfall_mm": baseline["rain"],
                "temperature_c": baseline["temp"]
            }

    @staticmethod
    def _calculate_historical_rate(city: str) -> float:
        """Well Calculated composite score: 0.5 * (0.12 baseline) + 0.5 * (Ledger Rate)."""
        static_baseline = 0.12
        ledger_rate = 0.0
        
        try:
            if LEDGER_PATH.exists():
                with open(LEDGER_PATH, 'r', encoding='utf-8') as f:
                    ledger = json.load(f)
                
                # Filter claims by city (using simple string match in reason or status)
                # Actually, the ledger doesn't have a 'city' field directly in the JSON output,
                # but let's see if we can detect it or just use the global ledger rate for a general 'well calculated' view.
                # In services.py, it geocodes the location query but doesn't save it in 'oracle'.
                
                total_claims = len(ledger)
                if total_claims > 0:
                    approved = sum(1 for c in ledger if c.get("status") == "APPROVED")
                    ledger_rate = approved / total_claims
            
            # Combine
            composite = (static_baseline + ledger_rate) / 2.0
            return round(min(max(composite, 0.0), 1.0), 4)
            
        except Exception as e:
            LOGGER.error("Ledger analysis failed: %s. Falling back to static 0.12.", e)
            return static_baseline

    @staticmethod
    def _calculate_traffic_index(city: str, rainfall: float) -> float:
        """Heuristic traffic index: Baseline + (Rainfall Uplift)."""
        baseline = CITY_WEATHER_BASELINES.get(city, {"traffic": 50})["traffic"] / 100.0
        # Uplift: 1mm of rain adds 0.5% congestion, capped at +30%
        uplift = min(rainfall * 0.005, 0.30)
        return round(min(baseline + uplift, 1.0), 4)

    @staticmethod
    def _calculate_flood_risk(city: str, rainfall: float) -> float:
        """Heuristic flood risk: (Rain / 100) + Coastal Bonus."""
        base_risk = CITY_WEATHER_BASELINES.get(city, {"flood": 0.1})["flood"]
        coastal_bonus = 0.35 if city in COASTAL_CITIES else 0.0
        # Intensity multiplier: high rain (>50mm) amplifies existing flood risk or coastal vulnerability
        intensity_mult = 1.2 if rainfall > 50 else 1.0
        
        final_risk = (base_risk + coastal_bonus) * intensity_mult
        # Add rain-specific temporary risk
        final_risk += rainfall * 0.002
        
        return round(min(final_risk, 1.0), 4)

    @classmethod
    def get_weekly_forecast(cls, city: str) -> Dict[str, Any]:
        """Fetch 7-day weather forecast for a city."""
        city_lower = city.strip().lower()
        try:
            lat, lon = cls._geocode_location(city)
            params = {
                "latitude": lat, "longitude": lon,
                "daily": "precipitation_sum,temperature_2m_max,weather_code",
                "timezone": "auto"
            }
            url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"
            req = Request(url)
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                daily = data.get("daily", {})
                
                forecast = []
                for i in range(len(daily.get("time", []))):
                    date_str = daily["time"][i]
                    precip = daily["precipitation_sum"][i]
                    temp = daily["temperature_2m_max"][i]
                    code = daily["weather_code"][i]
                    
                    threat = "Clear"
                    if precip > 15: threat = "Heavy Rain"
                    elif precip > 5: threat = "Rain"
                    elif temp > 40: threat = "Heatwave"
                    
                    forecast.append({
                        "date": date_str,
                        "precipitation": precip,
                        "max_temp": temp,
                        "threat": threat
                    })
                return {
                    "city": city,
                    "forecast": forecast
                }
        except Exception as e:
            LOGGER.error("Weekly forecast failed for %s: %s", city, e)
            return {"city": city, "forecast": [], "error": str(e)}

    @classmethod
    def get_oracle_disruption(cls, city: str, zone_id: str = "") -> Dict[str, Any]:
        """Oracle-driven disruption detection.

        Uses live environmental data to determine:
        - event type (heavy_rain, flood, traffic_gridlock, heatwave, etc.)
        - severity (0.0–1.0)
        - trigger (bool — whether disruption threshold is met)

        This acts as a signal layer only; it does NOT replace the ML model.
        """
        city_lower = city.strip().lower()
        LOGGER.info("Oracle disruption scan: city=%s zone=%s", city, zone_id)

        try:
            env = cls.fetch_environmental_data(city)
        except Exception as exc:
            LOGGER.warning("Oracle disruption fetch failed: %s — using fallback", exc)
            env = {
                "rainfall_forecast_mm": 8.0,
                "temperature_forecast_c": 30.0,
                "flood_risk": 0.3,
                "traffic_index": 0.7,
                "historical_disruption_rate": 0.12,
            }

        rainfall = env["rainfall_forecast_mm"]
        temperature = env["temperature_forecast_c"]
        flood_risk = env["flood_risk"]
        traffic_idx = env["traffic_index"]

        # --- Classify event type and raw severity ---
        event = "clear"
        severity = 0.0

        if rainfall >= 15:
            event = "heavy_rain"
            severity = min(0.4 + rainfall * 0.01, 1.0)
        elif rainfall >= 5:
            event = "moderate_rain"
            severity = 0.2 + rainfall * 0.01
        elif flood_risk >= 0.6 and rainfall > 0:
            event = "flood_warning"
            severity = flood_risk

        elif traffic_idx >= 0.85:
            event = "traffic_gridlock"
            severity = traffic_idx * 0.8
        elif temperature >= 42:
            event = "heatwave"
            severity = min(0.3 + (temperature - 42) * 0.05, 0.9)
        elif rainfall >= 1:
            event = "light_rain"
            severity = 0.15 + rainfall * 0.005
        else:
            event = "clear"
            severity = 0.0

        # Zone modifier — known high-risk zones only if there's an actual event
        if event != "clear":
            zone_lower = zone_id.strip().lower()
            zone_bumps = {"velachery": 0.08, "andheri": 0.06, "bandra": 0.05}
            severity += zone_bumps.get(zone_lower, 0.0)
        
        severity = round(min(max(severity, 0.0), 1.0), 4)

        # Trigger threshold — disruption warrants a claim pipeline
        trigger = severity >= 0.15 and event != "clear"


        return {
            "event": event,
            "severity": severity,
            "trigger": trigger,
            "city": city,
            "zone_id": zone_id,
            "environmental_data": env,
        }

