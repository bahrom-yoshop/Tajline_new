#!/usr/bin/env python3
"""
Debug the exact issue in cargo tracking
"""

import requests
import json

def debug_tracking_issue():
    base_url = "https://qr-logistics-1.preview.emergentagent.com"
    
    # Login as admin
    admin_login = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=admin_login)
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print("🐛 DEBUGGING CARGO TRACKING ISSUE")
    print("="*50)
    
    # Get existing cargo from operator list
    print("\n1. Getting existing cargo from operator list...")
    response = requests.get(f"{base_url}/api/operator/cargo/list", headers=headers)
    if response.status_code != 200:
        print("Failed to get cargo list")
        return
    
    cargo_list = response.json()
    if not cargo_list:
        print("No cargo found")
        return
    
    # Use the first cargo
    test_cargo = cargo_list[0]
    cargo_id = test_cargo['id']
    cargo_number = test_cargo['cargo_number']
    
    print(f"   Using existing cargo:")
    print(f"   ID: {cargo_id}")
    print(f"   Number: {cargo_number}")
    print(f"   Status: {test_cargo.get('status')}")
    
    # Check required fields
    print(f"\n2. Checking required fields in cargo:")
    required_fields = ['sender_full_name', 'recipient_full_name', 'created_at']
    for field in required_fields:
        value = test_cargo.get(field)
        print(f"   {field}: {value}")
        if not value:
            print(f"   ⚠️  Missing field: {field}")
    
    # Create tracking for this cargo
    tracking_data = {
        "cargo_number": cargo_number,
        "client_phone": "+992555666777"
    }
    
    print(f"\n3. Creating tracking for cargo {cargo_number}...")
    response = requests.post(f"{base_url}/api/cargo/tracking/create", json=tracking_data, headers=headers)
    if response.status_code != 200:
        print(f"Failed to create tracking: {response.status_code} - {response.json()}")
        return
    
    tracking_info = response.json()
    tracking_code = tracking_info['tracking_code']
    print(f"   ✅ Created tracking code: {tracking_code}")
    
    # Test public tracking
    print(f"\n4. Testing public tracking for {tracking_code}...")
    response = requests.get(f"{base_url}/api/cargo/track/{tracking_code}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ SUCCESS!")
        print(f"   Cargo: {result.get('cargo_number')}")
        print(f"   Status: {result.get('status')}")
    else:
        error = response.json()
        print(f"   ❌ FAILED: {error}")
        
        # Let's check what happens if we try to access the cargo directly
        print(f"\n5. Trying direct cargo access by number...")
        response = requests.get(f"{base_url}/api/cargo/track/{cargo_number}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Direct access works")
        else:
            print(f"   ❌ Direct access also fails: {response.json()}")

if __name__ == "__main__":
    debug_tracking_issue()