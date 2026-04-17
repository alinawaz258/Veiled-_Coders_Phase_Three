import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

def submit_claim(driver_id, city, category, lat, lon, is_bot=False):
    print(f"\nSubmitting claim for {driver_id} in {city} (Category: {category})...")
    payload = {
        "driver_id": driver_id,
        "location_query": f"{city}, India",
        "category": category,
        "is_webdriver": is_bot,
        "telemetry": {
            "latitude": lat,
            "longitude": lon,
            "altitude": 10.0,
            "accuracy": 5.0,
            "heading": 0.0,
            "speed": 0.0,
            "timestamp": int(time.time() * 1000)
        }
    }
    try:
        resp = requests.post(f"{BASE_URL}/api/claims/submit", json=payload)
        data = resp.json()
        print(f"Status: {data['status']}")
        print(f"Reason: {data['reason']}")
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    # Test Data Matrix
    scenarios = [
        {"driver": "DRV-TEST-001", "city": "Mumbai", "category": "Extreme Rain Alert", "lat": 19.0760, "lon": 72.8777},
        {"driver": "DRV-TEST-002", "city": "Delhi", "category": "Severe Traffic Gridlock", "lat": 28.6139, "lon": 77.2090},
        {"driver": "DRV-TEST-003", "city": "Bengaluru", "category": "Extreme Rain Alert", "lat": 12.9716, "lon": 77.5946},
        {"driver": "DRV-TEST-004", "city": "Chennai", "category": "Social Disruption / Active Event", "lat": 13.0827, "lon": 80.2707},
        {"driver": "DRV-TEST-005", "city": "Kolkata", "category": "Extreme Rain Alert", "lat": 22.5726, "lon": 88.3639, "is_bot": True}
    ]

    results = []
    for s in scenarios:
        res = submit_claim(s["driver"], s["city"], s["category"], s["lat"], s["lon"], s.get("is_bot", False))
        results.append(res)
        time.sleep(1) # Gap to avoid rate limits on nominatim/open-meteo

    print("\n--- Final Dashboard Snapshot ---")
    dashboard = requests.get(f"{BASE_URL}/api/dashboard").json()
    print(json.dumps(dashboard, indent=2))
