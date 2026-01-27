from fastapi.testclient import TestClient
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_server import app

def test_422_repro():
    client = TestClient(app)
    
    # Mimic the payload from StockCard.vue
    record_request = {
        "ts_code": "600519.SH",
        "selected_candidate": "A",
        "selected_premises": ["Trend: UP", "RSI: 50.00"],
        "selected_risk_checks": [],
        "constraints": {
            "price": 1800.5,
            "analysis_date": "2026-01-27T14:55:59Z"
        },
        "validation_period_days": 7
    }
    
    print(f"Sending payload: {record_request}")
    resp = client.post("/api/journal", json=record_request)
    
    if resp.status_code == 422:
        print("❌ Reproduced 422!")
        print(f"Detail: {resp.json()}")
    else:
        print(f"✅ Success (or other status): {resp.status_code}")
        if resp.status_code == 200:
            print(f"Response: {resp.json()}")
        else:
            print(f"Error: {resp.text}")

if __name__ == "__main__":
    test_422_repro()
