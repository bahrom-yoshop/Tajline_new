#!/usr/bin/env python3
"""
Minimal test to isolate the exact issue in tracking
"""

import requests
import json

def minimal_tracking_test():
    base_url = "https://cargo-tracker-29.preview.emergentagent.com"
    
    # Login as admin
    admin_login = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=admin_login)
    admin_token = response.json()['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}
    
    print("🔬 MINIMAL TRACKING TEST")
    print("="*30)
    
    # Get an existing tracking code from previous tests
    existing_tracking_codes = [
        "TRK145988B6879B",  # From previous test
        "TRK146002930AC6",  # From user cargo test
        "TRK145789C57BE4"   # From first diagnostic
    ]
    
    for tracking_code in existing_tracking_codes:
        print(f"\n🔍 Testing tracking code: {tracking_code}")
        
        # Test the tracking endpoint directly
        response = requests.get(f"{base_url}/api/cargo/track/{tracking_code}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ SUCCESS!")
            print(f"   Cargo: {result.get('cargo_number')}")
            break
        else:
            error = response.json()
            print(f"   ❌ FAILED: {error}")
    
    # Let's also test a non-existent tracking code to see the difference
    print(f"\n🔍 Testing non-existent tracking code...")
    response = requests.get(f"{base_url}/api/cargo/track/INVALID123")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")

if __name__ == "__main__":
    minimal_tracking_test()