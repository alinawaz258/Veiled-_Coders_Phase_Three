import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print("Testing /api/health/oracles...")
    try:
        resp = requests.get(f"{BASE_URL}/api/health/oracles")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        assert resp.status_code == 200
        assert resp.json()["open_meteo_satellite"] == "ONLINE"
    except Exception as e:
        print(f"Health check failed: {e}")

def test_dashboard():
    print("\nTesting /api/dashboard...")
    try:
        resp = requests.get(f"{BASE_URL}/api/dashboard")
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Risk Score: {data['real_time_risk_score']}")
        assert resp.status_code == 200
        assert "real_time_risk_score" in data
    except Exception as e:
        print(f"Dashboard test failed: {e}")

def test_claim_submission():
    print("\nTesting /api/claims/submit...")
    payload = {
        "driver_id": "TEST-DRV-PYTHON",
        "location_query": "Delhi, India",
        "category": "Extreme Rain Alert",
        "telemetry": {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "altitude": 210.0,
            "accuracy": 5.0,
            "heading": 0.0,
            "speed": 0.0,
            "timestamp": int(time.time() * 1000)
        }
    }
    try:
        resp = requests.post(f"{BASE_URL}/api/claims/submit", json=payload)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Decision: {data['status']}")
        print(f"Reason: {data['reason']}")
        assert resp.status_code == 200
        assert data["status"] in ["APPROVED", "DENIED"]
    except Exception as e:
        print(f"Claim submission failed: {e}")

if __name__ == "__main__":
    test_health()
    test_dashboard()
    test_claim_submission()
