#!/usr/bin/env python3
"""
Test with user cargo to see if the issue is collection-specific
"""

import requests
import json

def test_user_cargo_tracking():
    base_url = "https://cargo-system-debug.preview.emergentagent.com"
    
    # Login as regular user
    user_login = {
        "phone": "+79123456789",
        "password": "123456"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=user_login)
    if response.status_code != 200:
        print("Failed to login as user")
        return
    
    user_token = response.json()['access_token']
    user_headers = {'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'}
    
    # Login as admin
    admin_login = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=admin_login)
    admin_token = response.json()['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}
    
    print("🧪 TESTING USER CARGO TRACKING")
    print("="*40)
    
    # Create user cargo
    cargo_data = {
        "recipient_name": "User Test Recipient",
        "recipient_phone": "+992444555666",
        "route": "moscow_to_tajikistan",
        "weight": 10.0,
        "cargo_name": "User test cargo",
        "description": "Test cargo from user",
        "declared_value": 5000.0,
        "sender_address": "Moscow Test Address",
        "recipient_address": "Dushanbe Test Address"
    }
    
    print("\n1. Creating user cargo...")
    response = requests.post(f"{base_url}/api/cargo/create", json=cargo_data, headers=user_headers)
    if response.status_code != 200:
        print(f"Failed to create user cargo: {response.status_code}")
        return
    
    cargo_info = response.json()
    cargo_id = cargo_info['id']
    cargo_number = cargo_info['cargo_number']
    print(f"   ✅ Created user cargo ID: {cargo_id}")
    print(f"   📦 Cargo number: {cargo_number}")
    
    # Create tracking for user cargo
    tracking_data = {
        "cargo_number": cargo_number,
        "client_phone": "+992555666777"
    }
    
    print(f"\n2. Creating tracking for user cargo {cargo_number}...")
    response = requests.post(f"{base_url}/api/cargo/tracking/create", json=tracking_data, headers=admin_headers)
    if response.status_code != 200:
        print(f"Failed to create tracking: {response.status_code} - {response.json()}")
        return
    
    tracking_info = response.json()
    tracking_code = tracking_info['tracking_code']
    print(f"   ✅ Created tracking code: {tracking_code}")
    
    # Test public tracking for user cargo
    print(f"\n3. Testing public tracking for user cargo...")
    response = requests.get(f"{base_url}/api/cargo/track/{tracking_code}")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ SUCCESS! User cargo tracking works!")
        print(f"   Cargo: {result.get('cargo_number')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Sender: {result.get('sender_full_name')}")
        print(f"   Recipient: {result.get('recipient_full_name')}")
    else:
        error = response.json()
        print(f"   ❌ FAILED: {error}")

if __name__ == "__main__":
    test_user_cargo_tracking()