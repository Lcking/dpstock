"""
End-to-End User Flow Simulation
模拟完整用户流程: Watchlist -> Judgment -> Verify -> Review
使用 TestClient 进行进程内模拟，无需启动服务器
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_server import app

def run_e2e_flow():
    print("🚀 Starting E2E User Flow Simulation (TestClient)...")
    
    # Check database existence (required for integration)
    if not os.path.exists('data/stocks.db'):
        print("⚠️  Database 'data/stocks.db' not found. This test requires an initialized DB.")
        print("    Please run the application at least once or run migrations.")
        return

    client = TestClient(app)
    
    # 1. Initialize User (Get Cookie)
    print("\n[1] Initializing User...")
    resp = client.get("/api/watchlists")
    assert resp.status_code == 200
    # TestClient manages cookies automatically
    cookies = client.cookies
    user_cookie = cookies.get("aguai_uid")
    print(f"    User initialized. Cookie: {user_cookie}")
    
    # 2. Create Watchlist
    print("\n[2] Creating Watchlist...")
    resp = client.post(
        "/api/watchlists",
        json={"name": "E2E Portfolio", "description": "Automated Test"}
    )
    if resp.status_code != 200:
        print(f"❌ Failed to create watchlist: {resp.text}")
        return
        
    watchlist_id = resp.json()["id"]
    print(f"    Watchlist created. ID: {watchlist_id}")
    
    # 3. Add Stock
    stock_code = "600519.SH"
    print(f"\n[3] Adding Stock {stock_code}...")
    resp = client.post(
        f"/api/watchlists/{watchlist_id}/symbols",
        json={"ts_codes": [stock_code]}
    )
    assert resp.status_code == 200
    print("    Stock added.")
    
    # 4. Fetch Summary
    print(f"\n[4] Fetching Watchlist Summary...")
    try:
        resp = client.get(f"/api/watchlists/{watchlist_id}/summary")
        if resp.status_code == 200:
            summary = resp.json()
            print(f"    Summary fetched. Items: {len(summary.get('items', []))}")
        else:
            print(f"    Summary fetch returned {resp.status_code} (Expected if no market data)")
    except Exception as e:
        print(f"    Summary fetch failed: {e}")
        
    # 5. Create Judgment (Journal)
    print("\n[5] Creating Judgment Record...")
    judgment_data = {
        "ts_code": stock_code,
        "selected_candidate": "A",
        "selected_premises": ["Trend is UP", "Volume supports"],
        "selected_risk_checks": [],
        "constraints": {},
        "validation_period_days": 7
    }
    resp = client.post("/api/journal", json=judgment_data)
    if resp.status_code != 200:
         print(f"❌ Failed to create judgment: {resp.text}")
         return
         
    record = resp.json()
    record_id = record.get("id") or record.get("record_id")
    
    # Fallback to list if ID undefined
    if not record_id:
        resp = client.get("/api/journal")
        records = resp.json()["records"]
        if records:
            record_id = records[0]["id"]
            
    print(f"    Judgment created. ID: {record_id}")
    
    if not record_id:
        print("❌ Could not determine record ID, aborting.")
        return
    
    # 6. Verify Active Status
    print("\n[6] Verifying Journal Status...")
    resp = client.get(f"/api/journal/{record_id}")
    assert resp.status_code == 200
    record_detail = resp.json()
    print(f"    Status: {record_detail['status']}")
    assert record_detail['status'] == 'active'
    
    # 7. Check Due Count
    print("\n[7] Checking Due Count...")
    resp = client.get("/api/journal/due-count")
    assert resp.status_code == 200
    due_count = resp.json()['due_count']
    print(f"    Due Count: {due_count}")
    
    print("\n✅ E2E User Flow Walkthrough Completed (TestClient)")

if __name__ == "__main__":
    run_e2e_flow()
