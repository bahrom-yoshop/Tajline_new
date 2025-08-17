#!/usr/bin/env python3
"""
DEBUG TEST: Check if recipient data is being saved and retrieved correctly
"""

import requests
import json

BACKEND_URL = "https://tajline-manager-1.preview.emergentagent.com/api"

WAREHOUSE_OPERATOR = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

PICKUP_REQUEST_DATA = {
    "sender_full_name": "Debug Отправитель",
    "sender_phone": "+79991112233",
    "pickup_address": "Москва, ул. Debug, 123",
    "pickup_date": "2025-01-20",
    "pickup_time_from": "10:00",
    "pickup_time_to": "18:00",
    "route": "moscow_to_tajikistan",
    "courier_fee": 500.0,
    "destination": "Debug груз",
    # КРИТИЧЕСКИЕ ПОЛЯ ПОЛУЧАТЕЛЯ
    "recipient_full_name": "Debug Получатель",
    "recipient_phone": "+992900123456",
    "recipient_address": "Душанбе, ул. Debug, 456"
}

def authenticate_operator():
    response = requests.post(f"{BACKEND_URL}/auth/login", json=WAREHOUSE_OPERATOR)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    return None

def create_pickup_request(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BACKEND_URL}/admin/courier/pickup-request", 
                           json=PICKUP_REQUEST_DATA, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("request_id")
    else:
        print(f"Error creating request: {response.status_code} - {response.text}")
        return None

def check_pickup_request_data(token, request_id):
    """Check the pickup request data directly from the database via API"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to get the pickup request details
    response = requests.get(f"{BACKEND_URL}/operator/pickup-requests/{request_id}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Pickup request data retrieved successfully")
        print(json.dumps(data, indent=2))
        
        # Check if recipient data is present
        recipient_data = data.get("recipient_data", {})
        if recipient_data:
            print(f"\n📋 RECIPIENT DATA FOUND:")
            print(f"   - recipient_full_name: {recipient_data.get('recipient_full_name')}")
            print(f"   - recipient_phone: {recipient_data.get('recipient_phone')}")
            print(f"   - recipient_address: {recipient_data.get('recipient_address')}")
            return True
        else:
            print("❌ No recipient_data section found")
            return False
    else:
        print(f"❌ Error getting pickup request: {response.status_code} - {response.text}")
        return False

def main():
    print("🔍 DEBUG TEST: Checking recipient data storage and retrieval")
    print("=" * 80)
    
    # 1. Authenticate
    token = authenticate_operator()
    if not token:
        print("❌ Authentication failed")
        return
    print("✅ Authentication successful")
    
    # 2. Create pickup request
    request_id = create_pickup_request(token)
    if not request_id:
        print("❌ Failed to create pickup request")
        return
    print(f"✅ Pickup request created: {request_id}")
    
    # 3. Check pickup request data
    data_found = check_pickup_request_data(token, request_id)
    
    if data_found:
        print("\n🎉 SUCCESS: Recipient data is being stored and retrieved correctly!")
    else:
        print("\n❌ PROBLEM: Recipient data is not being stored or retrieved correctly!")

if __name__ == "__main__":
    main()