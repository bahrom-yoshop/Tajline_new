#!/usr/bin/env python3
"""
Test the debug endpoint
"""

import requests
import json

def test_debug_endpoint():
    base_url = "https://qr-logistics-1.preview.emergentagent.com"
    
    print("🔧 TESTING DEBUG ENDPOINT")
    print("="*30)
    
    # Test existing tracking codes
    tracking_codes = [
        "TRK145988B6879B",
        "TRK146002930AC6", 
        "TRK145789C57BE4"
    ]
    
    for tracking_code in tracking_codes:
        print(f"\n🔍 Debug info for: {tracking_code}")
        
        response = requests.get(f"{base_url}/api/debug/tracking/{tracking_code}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   📄 Debug info:")
            print(f"      Tracking record found: {result.get('tracking_record') is not None}")
            if result.get('tracking_record'):
                print(f"      Cargo ID: {result['tracking_record']['cargo_id']}")
                print(f"      Cargo Number: {result['tracking_record']['cargo_number']}")
            print(f"      Cargo in 'cargo' collection: {result.get('cargo_in_cargo_collection')}")
            print(f"      Cargo in 'operator_cargo' collection: {result.get('cargo_in_operator_collection')}")
            print(f"      Cargo found overall: {result.get('cargo_found')}")
        else:
            print(f"   ❌ Error: {response.json()}")

if __name__ == "__main__":
    test_debug_endpoint()