#!/usr/bin/env python3
"""
Extended test to verify cargo creation in different collections
"""

import requests
import json

def test_cargo_verification():
    base_url = "https://cargo-talk.preview.emergentagent.com"
    
    # Login as warehouse operator
    login_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    if response.status_code != 200:
        print("❌ Login failed")
        return
    
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # Test different endpoints to find the cargo
    cargo_number = "100058/01"
    
    print(f"🔍 Searching for cargo: {cargo_number}")
    
    # 1. Try cargo tracking endpoint
    response = requests.get(f"{base_url}/api/cargo/track/{cargo_number}", headers=headers)
    print(f"📋 /api/cargo/track/{cargo_number}: {response.status_code}")
    if response.status_code == 200:
        cargo_data = response.json()
        print(f"   ✅ Found cargo with status: {cargo_data.get('status')}")
        print(f"   📦 Cargo name: {cargo_data.get('cargo_name')}")
        print(f"   🏭 Warehouse ID: {cargo_data.get('warehouse_id')}")
        return
    
    # 2. Try operator cargo list
    response = requests.get(f"{base_url}/api/operator/cargo/list", headers=headers)
    print(f"📋 /api/operator/cargo/list: {response.status_code}")
    if response.status_code == 200:
        cargo_list = response.json()
        items = cargo_list.get('items', []) if isinstance(cargo_list, dict) else cargo_list
        
        found_cargo = None
        for cargo in items:
            if cargo.get('cargo_number') == cargo_number:
                found_cargo = cargo
                break
        
        if found_cargo:
            print(f"   ✅ Found cargo in operator list with status: {found_cargo.get('status')}")
            print(f"   📦 Processing status: {found_cargo.get('processing_status')}")
            return
        else:
            print(f"   ❌ Cargo {cargo_number} not found in operator cargo list")
    
    # 3. Try available for placement
    response = requests.get(f"{base_url}/api/operator/cargo/available-for-placement", headers=headers)
    print(f"📋 /api/operator/cargo/available-for-placement: {response.status_code}")
    if response.status_code == 200:
        placement_data = response.json()
        items = placement_data.get('items', []) if isinstance(placement_data, dict) else placement_data
        
        found_cargo = None
        for cargo in items:
            if cargo.get('cargo_number') == cargo_number:
                found_cargo = cargo
                break
        
        if found_cargo:
            print(f"   ✅ Found cargo in available for placement with status: {found_cargo.get('status')}")
            print(f"   📦 Processing status: {found_cargo.get('processing_status')}")
            return
        else:
            print(f"   ❌ Cargo {cargo_number} not found in available for placement")
    
    # 4. Try warehouses placed cargo
    response = requests.get(f"{base_url}/api/warehouses/placed-cargo", headers=headers)
    print(f"📋 /api/warehouses/placed-cargo: {response.status_code}")
    if response.status_code == 200:
        placed_data = response.json()
        items = placed_data.get('items', []) if isinstance(placed_data, dict) else placed_data
        
        found_cargo = None
        for cargo in items:
            if cargo.get('cargo_number') == cargo_number:
                found_cargo = cargo
                break
        
        if found_cargo:
            print(f"   ✅ Found cargo in placed cargo with status: {found_cargo.get('status')}")
            print(f"   📦 Processing status: {found_cargo.get('processing_status')}")
            return
        else:
            print(f"   ❌ Cargo {cargo_number} not found in placed cargo")
    
    print(f"❌ Cargo {cargo_number} not found in any endpoint")

if __name__ == "__main__":
    test_cargo_verification()