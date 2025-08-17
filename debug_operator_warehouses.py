#!/usr/bin/env python3
"""
Debug operator warehouse bindings and cargo filtering
"""

import requests
import json

def debug_operator_warehouses():
    base_url = "https://tajline-manager-1.preview.emergentagent.com"
    
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
    
    # Check operator warehouses
    print("🔍 Checking operator warehouses:")
    response = requests.get(f"{base_url}/api/operator/warehouses", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        warehouses = response.json()
        print(f"Found {len(warehouses)} warehouses for operator")
        
        for i, wh in enumerate(warehouses):
            print(f"\nWarehouse {i+1}:")
            print(f"  ID: {wh.get('id')}")
            print(f"  Name: {wh.get('name')}")
            print(f"  Location: {wh.get('location')}")
    else:
        print(f"Error: {response.text}")
    
    # Check cargo available for placement
    print("\n🔍 Checking cargo available for placement:")
    response = requests.get(f"{base_url}/api/operator/cargo/available-for-placement", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        print(f"Found {len(items)} cargo items available for placement")
        
        for i, cargo in enumerate(items[:5]):  # Show first 5
            print(f"\nCargo {i+1}:")
            print(f"  Number: {cargo.get('cargo_number')}")
            print(f"  Name: {cargo.get('cargo_name')}")
            print(f"  Status: {cargo.get('status')}")
            print(f"  Warehouse ID: {cargo.get('warehouse_id')}")
            print(f"  Pickup Request ID: {cargo.get('pickup_request_id')}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    debug_operator_warehouses()