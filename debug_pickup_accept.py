#!/usr/bin/env python3
"""
Debug script for pickup request acceptance issue
"""

import requests
import json

def debug_pickup_acceptance():
    base_url = "https://freight-hub-6.preview.emergentagent.com"
    
    # Login as courier
    courier_login = {
        "phone": "+79991234567",
        "password": "courier123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=courier_login)
    if response.status_code != 200:
        print(f"❌ Courier login failed: {response.status_code}")
        return
    
    courier_token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {courier_token}', 'Content-Type': 'application/json'}
    
    # Get new requests to find a pickup request
    response = requests.get(f"{base_url}/api/courier/requests/new", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to get new requests: {response.status_code}")
        return
    
    data = response.json()
    pickup_requests = data.get('pickup_requests', [])
    
    if not pickup_requests:
        print("❌ No pickup requests found")
        return
    
    # Use the first pickup request
    pickup_request = pickup_requests[0]
    request_id = pickup_request['id']
    
    print(f"🔍 Debugging pickup request: {request_id}")
    print(f"📋 Request status: {pickup_request.get('request_status')}")
    print(f"👤 Assigned courier: {pickup_request.get('assigned_courier_id')}")
    print(f"🏷️ Request type: {pickup_request.get('request_type')}")
    
    # Try to accept the request
    response = requests.post(f"{base_url}/api/courier/requests/{request_id}/accept", headers=headers)
    
    print(f"\n🎯 Acceptance attempt:")
    print(f"📊 Status code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ SUCCESS! Request accepted")
        print(f"📄 Response: {response.json()}")
    else:
        print("❌ FAILED to accept request")
        try:
            error_detail = response.json()
            print(f"📄 Error: {error_detail}")
        except:
            print(f"📄 Raw response: {response.text}")

if __name__ == "__main__":
    debug_pickup_acceptance()