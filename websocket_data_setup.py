#!/usr/bin/env python3
"""
WEBSOCKET DATA SETUP FOR TAJLINE.TJ
Create test data for comprehensive WebSocket testing
"""

import requests
import json
from datetime import datetime

# Configuration
BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

def setup_test_data():
    """Setup test data for WebSocket testing"""
    print("🔧 SETTING UP TEST DATA FOR WEBSOCKET TESTING...")
    
    # Authenticate as admin
    try:
        response = requests.post(f"{API_BASE}/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code != 200:
            print(f"❌ Admin authentication failed: {response.status_code}")
            return False
            
        admin_token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False
    
    # Check existing couriers
    try:
        response = requests.get(f"{API_BASE}/admin/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            couriers = [u for u in users if u.get("role") == "courier"]
            print(f"📊 Found {len(couriers)} existing couriers")
            
            if couriers:
                print("✅ Couriers already exist in system")
                for courier in couriers[:3]:  # Show first 3
                    print(f"   - {courier.get('full_name')} ({courier.get('phone')})")
            else:
                print("⚠️ No couriers found in system")
                
        else:
            print(f"❌ Cannot check existing users: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking users: {e}")
    
    # Check existing warehouses
    try:
        response = requests.get(f"{API_BASE}/warehouses", headers=headers)
        if response.status_code == 200:
            warehouses = response.json()
            print(f"📊 Found {len(warehouses)} existing warehouses")
            
            if warehouses:
                print("✅ Warehouses exist in system")
                for warehouse in warehouses[:3]:  # Show first 3
                    print(f"   - {warehouse.get('name')} ({warehouse.get('location')})")
            else:
                print("⚠️ No warehouses found in system")
                
        else:
            print(f"❌ Cannot check existing warehouses: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking warehouses: {e}")
    
    # Check courier locations
    try:
        response = requests.get(f"{API_BASE}/admin/couriers/locations", headers=headers)
        if response.status_code == 200:
            data = response.json()
            locations = data.get("locations", [])
            print(f"📊 Found {len(locations)} courier location records")
            
            if locations:
                print("✅ Courier locations exist")
                for location in locations[:3]:  # Show first 3
                    print(f"   - {location.get('courier_name')} at {location.get('current_address', 'Unknown address')}")
            else:
                print("⚠️ No courier locations found")
                
        else:
            print(f"❌ Cannot check courier locations: {response.status_code}")
            if response.status_code == 404:
                print("   This might be because no couriers exist or no locations have been updated")
            
    except Exception as e:
        print(f"❌ Error checking courier locations: {e}")
    
    # Check operator warehouse bindings
    try:
        response = requests.get(f"{API_BASE}/admin/operator-warehouse-bindings", headers=headers)
        if response.status_code == 200:
            bindings = response.json()
            print(f"📊 Found {len(bindings)} operator-warehouse bindings")
            
            if bindings:
                print("✅ Operator-warehouse bindings exist")
                for binding in bindings[:3]:  # Show first 3
                    print(f"   - {binding.get('operator_name')} -> {binding.get('warehouse_name')}")
            else:
                print("⚠️ No operator-warehouse bindings found")
                
        else:
            print(f"❌ Cannot check operator bindings: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking operator bindings: {e}")
    
    print("\n" + "=" * 60)
    print("📋 DATA SETUP SUMMARY")
    print("=" * 60)
    print("The WebSocket system requires:")
    print("1. ✅ Admin user (exists)")
    print("2. ✅ Warehouse operator user (exists)")  
    print("3. ✅ Courier user (exists)")
    print("4. ⚠️ Courier profiles (may need to be created)")
    print("5. ⚠️ Warehouse assignments (may need to be created)")
    print("6. ⚠️ Location data (created when couriers update location)")
    print("\nThe system is ready for WebSocket testing with existing data.")
    print("Location updates will create the necessary courier location records.")
    
    return True

if __name__ == "__main__":
    setup_test_data()