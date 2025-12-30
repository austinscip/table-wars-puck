#!/usr/bin/env python3
"""
Server Health Check & API Tester
Tests if the Flask server is running and endpoints are working
"""

import requests
import json

BASE_URL = "http://localhost:5001"

def test_endpoint(name, url, method='GET', data=None):
    """Test a single endpoint"""
    try:
        if method == 'GET':
            r = requests.get(url, timeout=2)
        elif method == 'POST':
            r = requests.post(url, json=data, timeout=2)

        status = "✅" if r.status_code == 200 else "❌"
        print(f"{status} {name}: {r.status_code}")

        if r.status_code != 200:
            print(f"   Response: {r.text[:200]}")
        else:
            try:
                data = r.json()
                print(f"   Data: {json.dumps(data, indent=2)[:150]}...")
            except:
                print(f"   Text: {r.text[:150]}...")

        return r.status_code == 200

    except requests.exceptions.ConnectionError:
        print(f"❌ {name}: Server not running")
        return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

def main():
    print("=" * 60)
    print("TABLE WARS - Server Health Check")
    print("=" * 60)

    # Test basic endpoints
    test_endpoint("Health Check", f"{BASE_URL}/")
    test_endpoint("Stats API", f"{BASE_URL}/api/stats")
    test_endpoint("Bars API", f"{BASE_URL}/api/bars")
    test_endpoint("Recent Scores", f"{BASE_URL}/api/recent?limit=5")

    print("\n" + "=" * 60)
    print("Testing Score Submission (like ESP32 would)")
    print("=" * 60)

    # Test score submission
    test_data = {
        "puck_id": 1,
        "bar_id": 1,
        "game_id": 99,
        "game_type": "foosball",
        "score": 42,
        "session_id": "test-session-123"
    }

    success = test_endpoint(
        "Submit Score",
        f"{BASE_URL}/api/score",
        method='POST',
        data=test_data
    )

    if success:
        print("\n✅ Server is working! ESP32 should be able to submit scores.")
    else:
        print("\n❌ Server has issues. Check if it's running on port 5001.")

if __name__ == "__main__":
    main()
