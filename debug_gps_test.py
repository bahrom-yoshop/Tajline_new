#!/usr/bin/env python3
"""
Debug GPS Tracking Issue - Focused test to identify the admin endpoint problem
"""

import requests
import json

def test_admin_gps_endpoint():
    base_url = "https://tajline-manager-1.preview.emergentagent.com"
    
    print("🔍 DEBUG: Testing Admin GPS Endpoint Issue")
    
    # Step 1: Login as courier and send GPS data
    print("\n1. Courier Login and GPS Update...")
    courier_login = {
        "phone": "+79991234567",
        "password": "courier123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=courier_login)
    if response.status_code != 200:
        print(f"❌ Courier login failed: {response.status_code}")
        return
    
    courier_token = response.json()['access_token']
    print("✅ Courier logged in")
    
    # Send GPS data
    gps_data = {
        "latitude": 55.7558,
        "longitude": 37.6176,
        "status": "online",
        "current_address": "Москва, Красная площадь"
    }
    
    headers = {'Authorization': f'Bearer {courier_token}', 'Content-Type': 'application/json'}
    response = requests.post(f"{base_url}/api/courier/location/update", json=gps_data, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ GPS update failed: {response.status_code}")
        print(f"Response: {response.text}")
        return
    
    print("✅ GPS data sent successfully")
    print(f"Response: {response.json()}")
    
    # Step 2: Login as admin
    print("\n2. Admin Login...")
    admin_login = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=admin_login)
    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.status_code}")
        return
    
    admin_token = response.json()['access_token']
    print("✅ Admin logged in")
    
    # Step 3: Test admin endpoint
    print("\n3. Testing Admin Courier Locations Endpoint...")
    headers = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}
    response = requests.get(f"{base_url}/api/admin/couriers/locations", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Text: {response.text}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✅ Success! Response: {json.dumps(data, indent=2)}")
        except:
            print(f"❌ Failed to parse JSON: {response.text}")
    else:
        print(f"❌ Failed with status {response.status_code}")
        try:
            error = response.json()
            print(f"Error details: {error}")
        except:
            print(f"Raw error: {response.text}")

if __name__ == "__main__":
    test_admin_gps_endpoint()