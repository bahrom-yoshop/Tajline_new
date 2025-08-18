#!/usr/bin/env python3
"""
Debug test to investigate notification system responses
"""

import requests
import json
from datetime import datetime

def debug_notifications():
    base_url = "https://cargo-system-debug.preview.emergentagent.com"
    
    # Login as operator
    print("🔍 Logging in as operator...")
    operator_login = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=operator_login)
    if response.status_code == 200:
        operator_token = response.json()['access_token']
        print("✅ Operator logged in successfully")
    else:
        print("❌ Operator login failed")
        return
    
    # Check warehouse notifications
    print("\n🔔 Checking warehouse notifications...")
    headers = {'Authorization': f'Bearer {operator_token}'}
    response = requests.get(f"{base_url}/api/operator/warehouse-notifications", headers=headers)
    
    if response.status_code == 200:
        notifications_data = response.json()
        print(f"✅ Notifications endpoint working")
        print(f"📄 Full response: {json.dumps(notifications_data, indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ Notifications endpoint failed: {response.status_code}")
        print(f"📄 Error: {response.text}")
    
    # Check pickup requests
    print("\n📋 Checking pickup requests...")
    response = requests.get(f"{base_url}/api/operator/pickup-requests", headers=headers)
    
    if response.status_code == 200:
        pickup_data = response.json()
        print(f"✅ Pickup requests endpoint working")
        print(f"📄 Full response: {json.dumps(pickup_data, indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ Pickup requests endpoint failed: {response.status_code}")
        print(f"📄 Error: {response.text}")

if __name__ == "__main__":
    debug_notifications()