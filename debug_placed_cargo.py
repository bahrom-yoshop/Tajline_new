#!/usr/bin/env python3
"""
Debug script to check placed cargo endpoint and operator_cargo collection
"""

import requests
import json

def test_placed_cargo():
    base_url = "https://cargo-talk.preview.emergentagent.com"
    
    # Login as operator
    login_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return
    
    token = response.json()["access_token"]
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test placed cargo endpoint
    print("🔍 Testing /api/warehouses/placed-cargo endpoint:")
    response = requests.get(f"{base_url}/api/warehouses/placed-cargo", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        placed_cargo = data.get("placed_cargo", [])
        print(f"Found {len(placed_cargo)} placed cargo items")
        
        for i, cargo in enumerate(placed_cargo[:3]):  # Show first 3
            print(f"\nCargo {i+1}:")
            print(f"  Number: {cargo.get('cargo_number')}")
            print(f"  Name: {cargo.get('cargo_name')}")
            print(f"  Status: {cargo.get('status')}")
            print(f"  Pickup Request ID: {cargo.get('pickup_request_id')}")
            print(f"  Pickup Request Number: {cargo.get('pickup_request_number')}")
            print(f"  Courier Delivered By: {cargo.get('courier_delivered_by')}")
    else:
        print(f"Error: {response.text}")
    
    # Test operator cargo list
    print("\n🔍 Testing /api/operator/cargo/list endpoint:")
    response = requests.get(f"{base_url}/api/operator/cargo/list", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        cargo_list = data.get("cargo", [])
        print(f"Found {len(cargo_list)} total cargo items")
        
        # Filter for placement_ready status
        placement_ready = [c for c in cargo_list if c.get('status') == 'placement_ready']
        print(f"Found {len(placement_ready)} placement_ready cargo items")
        
        for i, cargo in enumerate(placement_ready[:3]):  # Show first 3
            print(f"\nPlacement Ready Cargo {i+1}:")
            print(f"  Number: {cargo.get('cargo_number')}")
            print(f"  Name: {cargo.get('cargo_name')}")
            print(f"  Status: {cargo.get('status')}")
            print(f"  Pickup Request ID: {cargo.get('pickup_request_id')}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_placed_cargo()