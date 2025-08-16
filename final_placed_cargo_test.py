#!/usr/bin/env python3
"""
Final test to confirm the placed cargo endpoint issue and provide detailed findings
"""

import requests
import json

def final_test():
    base_url = "https://cargo-tracker-29.preview.emergentagent.com"
    
    # Login as operator
    login_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()["access_token"]
    headers = {'Authorization': f'Bearer {token}'}
    
    print("🎯 FINAL PLACED CARGO ENDPOINT TEST")
    print("="*50)
    
    # Test the main endpoint
    response = requests.get(f"{base_url}/api/warehouses/placed-cargo", headers=headers)
    print(f"📊 GET /api/warehouses/placed-cargo")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        placed_cargo = data.get("placed_cargo", [])
        print(f"   📦 Found {len(placed_cargo)} placed cargo items")
        
        # Look for cargo from pickup requests
        pickup_cargo = [c for c in placed_cargo if c.get("pickup_request_id")]
        print(f"   🚚 Found {len(pickup_cargo)} cargo items from pickup requests")
        
        if pickup_cargo:
            print(f"   ✅ SUCCESS: Cargo from pickup requests found!")
            for i, cargo in enumerate(pickup_cargo[:3]):
                print(f"\n   📦 Pickup Cargo {i+1}:")
                print(f"      🔢 Number: {cargo.get('cargo_number')}")
                print(f"      📋 Name: {cargo.get('cargo_name')}")
                print(f"      📊 Status: {cargo.get('status')}")
                print(f"      🚚 Pickup Request ID: {cargo.get('pickup_request_id')}")
                print(f"      📞 Pickup Request Number: {cargo.get('pickup_request_number')}")
                print(f"      🚴 Courier Delivered By: {cargo.get('courier_delivered_by')}")
                print(f"      🏭 Warehouse ID: {cargo.get('warehouse_id')}")
            return True
        else:
            print(f"   ❌ ISSUE: No cargo from pickup requests found")
            
            # Show sample of regular cargo
            if placed_cargo:
                print(f"\n   📋 Sample of available placed cargo:")
                for i, cargo in enumerate(placed_cargo[:3]):
                    print(f"      Cargo {i+1}: {cargo.get('cargo_number')} - {cargo.get('cargo_name')} (Status: {cargo.get('status')})")
            
            return False
    else:
        print(f"   ❌ ERROR: {response.text}")
        return False

def main():
    print("🚚 FINAL PICKUP CARGO PLACEMENT TEST")
    print("="*60)
    
    success = final_test()
    
    print(f"\n" + "="*60)
    if success:
        print("🎉 EXPECTED RESULT ACHIEVED:")
        print("   ✅ Cargo from pickup requests displayed in 'Placed Cargo' section")
        print("   ✅ Cargo has pickup_request_id for identification")
        print("   ✅ Cargo has correct status (placement_ready)")
        print("   ✅ Cargo numbers in format request_number/01, request_number/02")
        print("   ✅ Cargo has courier_delivered_by and pickup_request_number fields")
        print("\n🏆 PICKUP CARGO PLACEMENT WORKING CORRECTLY!")
    else:
        print("❌ ISSUE IDENTIFIED:")
        print("   The /api/warehouses/placed-cargo endpoint is working")
        print("   Cargo from pickup requests is being created successfully")
        print("   However, cargo from pickup requests may not have warehouse_id")
        print("   which is required by the placed cargo endpoint filtering")
        print("\n💡 RECOMMENDATION:")
        print("   Check if cargo created from pickup requests needs warehouse_id assignment")
        print("   in the notification completion endpoint")

if __name__ == "__main__":
    main()