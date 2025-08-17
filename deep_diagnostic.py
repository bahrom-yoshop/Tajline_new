#!/usr/bin/env python3
"""
Deep Diagnostic for Cargo Tracking Issue
This will help us understand exactly what's happening with the cargo_id
"""

import requests
import json

def deep_diagnostic():
    base_url = "https://freight-hub-6.preview.emergentagent.com"
    
    # Login as admin
    admin_login = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=admin_login)
    if response.status_code != 200:
        print("Failed to login")
        return
    
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    print("🔍 DEEP DIAGNOSTIC FOR CARGO TRACKING")
    print("="*60)
    
    # Create a new cargo for testing
    cargo_data = {
        "sender_full_name": "Deep Diagnostic Test",
        "sender_phone": "+79111222333",
        "recipient_full_name": "Deep Diagnostic Recipient",
        "recipient_phone": "+992444555666",
        "recipient_address": "Test Address",
        "weight": 10.0,
        "cargo_name": "Deep diagnostic cargo",
        "declared_value": 5000.0,
        "description": "Cargo for deep diagnostic",
        "route": "moscow_to_tajikistan"
    }
    
    print("\n1. Creating test cargo...")
    response = requests.post(f"{base_url}/api/operator/cargo/accept", json=cargo_data, headers=headers)
    if response.status_code != 200:
        print(f"Failed to create cargo: {response.status_code}")
        return
    
    cargo_info = response.json()
    cargo_id = cargo_info['id']
    cargo_number = cargo_info['cargo_number']
    print(f"   ✅ Created cargo ID: {cargo_id}")
    print(f"   📦 Cargo number: {cargo_number}")
    
    # Create tracking
    tracking_data = {
        "cargo_number": cargo_number,
        "client_phone": "+992555666777"
    }
    
    print("\n2. Creating tracking code...")
    response = requests.post(f"{base_url}/api/cargo/tracking/create", json=tracking_data, headers=headers)
    if response.status_code != 200:
        print(f"Failed to create tracking: {response.status_code}")
        return
    
    tracking_info = response.json()
    tracking_code = tracking_info['tracking_code']
    print(f"   ✅ Created tracking code: {tracking_code}")
    
    # Now let's test the public tracking
    print("\n3. Testing public tracking...")
    response = requests.get(f"{base_url}/api/cargo/track/{tracking_code}")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ SUCCESS: {response.json()}")
    else:
        print(f"   ❌ FAILED: {response.json()}")
    
    # Let's also test direct cargo lookup by number
    print("\n4. Testing direct cargo lookup by number...")
    response = requests.get(f"{base_url}/api/cargo/track/{cargo_number}")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ SUCCESS: {response.json()}")
    else:
        print(f"   ❌ FAILED: {response.json()}")
    
    # Let's check if we can find the cargo in operator list
    print("\n5. Checking cargo in operator list...")
    response = requests.get(f"{base_url}/api/operator/cargo/list", headers=headers)
    if response.status_code == 200:
        cargo_list = response.json()
        found_cargo = None
        for cargo in cargo_list:
            if cargo.get('id') == cargo_id:
                found_cargo = cargo
                break
        
        if found_cargo:
            print(f"   ✅ Found cargo in operator list:")
            print(f"      ID: {found_cargo.get('id')}")
            print(f"      Number: {found_cargo.get('cargo_number')}")
            print(f"      Status: {found_cargo.get('status')}")
        else:
            print(f"   ❌ Cargo not found in operator list")
    else:
        print(f"   ❌ Failed to get operator cargo list: {response.status_code}")

if __name__ == "__main__":
    deep_diagnostic()