#!/usr/bin/env python3
"""
Check the actual pickup request data in the database
"""

import requests
import json

BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

WAREHOUSE_OPERATOR = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

def authenticate_operator():
    response = requests.post(f"{BACKEND_URL}/auth/login", json=WAREHOUSE_OPERATOR)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    return None

def check_recent_pickup_requests(token):
    """Check recent pickup requests to see their data"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get warehouse notifications to find recent pickup requests
    response = requests.get(f"{BACKEND_URL}/operator/warehouse-notifications", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])
        
        print(f"Found {len(notifications)} notifications")
        
        for notification in notifications[:3]:  # Check first 3
            pickup_request_id = notification.get("pickup_request_id")
            if pickup_request_id:
                print(f"\n🔍 Checking pickup request: {pickup_request_id}")
                
                # Get the pickup request details
                response = requests.get(f"{BACKEND_URL}/operator/pickup-requests/{pickup_request_id}", headers=headers)
                
                if response.status_code == 200:
                    pickup_data = response.json()
                    full_request = pickup_data.get("full_request", {})
                    
                    print(f"📋 Pickup Request {pickup_request_id} data:")
                    print(f"   - recipient_full_name: '{full_request.get('recipient_full_name')}'")
                    print(f"   - recipient_phone: '{full_request.get('recipient_phone')}'")
                    print(f"   - recipient_address: '{full_request.get('recipient_address')}'")
                    print(f"   - sender_full_name: '{full_request.get('sender_full_name')}'")
                    print(f"   - sender_phone: '{full_request.get('sender_phone')}'")
                    print(f"   - route: '{full_request.get('route')}'")
                    print(f"   - destination: '{full_request.get('destination')}'")
                    
                    # Check if any recipient fields are None or empty
                    recipient_name = full_request.get('recipient_full_name')
                    recipient_phone = full_request.get('recipient_phone')
                    recipient_address = full_request.get('recipient_address')
                    
                    if not recipient_name or not recipient_phone or not recipient_address:
                        print(f"   ⚠️ WARNING: Some recipient fields are empty!")
                        print(f"      - recipient_full_name is empty: {not recipient_name}")
                        print(f"      - recipient_phone is empty: {not recipient_phone}")
                        print(f"      - recipient_address is empty: {not recipient_address}")
                    else:
                        print(f"   ✅ All recipient fields have values")
                else:
                    print(f"   ❌ Error getting pickup request: {response.status_code}")
    else:
        print(f"❌ Error getting notifications: {response.status_code} - {response.text}")

def main():
    print("🔍 CHECKING RECENT PICKUP REQUEST DATA")
    print("=" * 60)
    
    token = authenticate_operator()
    if not token:
        print("❌ Authentication failed")
        return
    
    check_recent_pickup_requests(token)

if __name__ == "__main__":
    main()