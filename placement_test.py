#!/usr/bin/env python3
"""
TEST: Send pickup request to placement with recipient data
"""

import requests
import json

BACKEND_URL = "https://tajline-manager-1.preview.emergentagent.com/api"

WAREHOUSE_OPERATOR = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

COURIER = {
    "phone": "+79991234567", 
    "password": "courier123"
}

def authenticate_user(phone, password):
    response = requests.post(f"{BACKEND_URL}/auth/login", json={
        "phone": phone,
        "password": password
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    return None

def create_pickup_request_with_recipient(operator_token):
    """Create pickup request with recipient data"""
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    request_data = {
        "sender_full_name": "Placement Test Отправитель",
        "sender_phone": "+79991112233",
        "pickup_address": "Москва, ул. Placement Test, 123",
        "pickup_date": "2025-01-20",
        "pickup_time_from": "10:00",
        "pickup_time_to": "18:00",
        "route": "moscow_to_tajikistan",
        "courier_fee": 500.0,
        "destination": "Placement Test груз",
        # RECIPIENT DATA
        "recipient_full_name": "Placement Test Получатель",
        "recipient_phone": "+992900123456",
        "recipient_address": "Душанбе, ул. Placement Test, 456"
    }
    
    response = requests.post(f"{BACKEND_URL}/admin/courier/pickup-request", 
                           json=request_data, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("request_id")
    else:
        print(f"Error creating request: {response.status_code} - {response.text}")
        return None

def complete_courier_workflow(courier_token, request_id):
    """Complete the courier workflow"""
    headers = {"Authorization": f"Bearer {courier_token}"}
    
    # Accept request
    response = requests.post(f"{BACKEND_URL}/courier/requests/{request_id}/accept", headers=headers)
    if response.status_code != 200:
        print(f"Error accepting request: {response.status_code} - {response.text}")
        return False
    
    # Pickup cargo
    response = requests.post(f"{BACKEND_URL}/courier/requests/{request_id}/pickup", headers=headers)
    if response.status_code != 200:
        print(f"Error picking up cargo: {response.status_code} - {response.text}")
        return False
    
    # Deliver to warehouse
    response = requests.post(f"{BACKEND_URL}/courier/requests/{request_id}/deliver-to-warehouse", headers=headers)
    if response.status_code != 200:
        print(f"Error delivering to warehouse: {response.status_code} - {response.text}")
        return False
    
    return True

def find_notification(operator_token, request_number):
    """Find warehouse notification for the request"""
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.get(f"{BACKEND_URL}/operator/warehouse-notifications", headers=headers)
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])
        
        for notification in notifications:
            if notification.get("request_number") == request_number:
                return notification.get("id")
    
    return None

def test_send_to_placement(operator_token, notification_id):
    """Test the send to placement endpoint"""
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    print(f"🧪 Testing send-to-placement for notification: {notification_id}")
    
    response = requests.post(f"{BACKEND_URL}/operator/warehouse-notifications/{notification_id}/send-to-placement", 
                           headers=headers)
    
    print(f"📊 Response status: {response.status_code}")
    print(f"📊 Response body: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        cargo_number = data.get("cargo_number")
        print(f"✅ Success! Cargo created: {cargo_number}")
        return cargo_number
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None

def check_cargo_in_placement(operator_token, cargo_number):
    """Check if cargo appears in placement list with recipient data"""
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        
        for item in items:
            if item.get("cargo_number") == cargo_number:
                print(f"✅ Cargo found in placement list!")
                print(f"📋 Recipient data:")
                print(f"   - recipient_full_name: '{item.get('recipient_full_name', '')}'")
                print(f"   - recipient_phone: '{item.get('recipient_phone', '')}'")
                print(f"   - recipient_address: '{item.get('recipient_address', '')}'")
                return True
        
        print(f"❌ Cargo {cargo_number} not found in placement list")
        return False
    else:
        print(f"❌ Error getting placement list: {response.status_code} - {response.text}")
        return False

def main():
    print("🧪 TESTING SEND PICKUP REQUEST TO PLACEMENT WITH RECIPIENT DATA")
    print("=" * 80)
    
    # 1. Authenticate
    operator_token = authenticate_user(WAREHOUSE_OPERATOR["phone"], WAREHOUSE_OPERATOR["password"])
    courier_token = authenticate_user(COURIER["phone"], COURIER["password"])
    
    if not operator_token or not courier_token:
        print("❌ Authentication failed")
        return
    print("✅ Authentication successful")
    
    # 2. Create pickup request
    request_id = create_pickup_request_with_recipient(operator_token)
    if not request_id:
        print("❌ Failed to create pickup request")
        return
    print(f"✅ Pickup request created: {request_id}")
    
    # 3. Complete courier workflow
    if not complete_courier_workflow(courier_token, request_id):
        print("❌ Failed to complete courier workflow")
        return
    print("✅ Courier workflow completed")
    
    # 4. Find notification
    notification_id = find_notification(operator_token, request_id)
    if not notification_id:
        print("❌ Notification not found")
        return
    print(f"✅ Notification found: {notification_id}")
    
    # 5. Test send to placement
    cargo_number = test_send_to_placement(operator_token, notification_id)
    if not cargo_number:
        print("❌ Send to placement failed")
        return
    
    # 6. Check cargo in placement list
    if check_cargo_in_placement(operator_token, cargo_number):
        print("\n🎉 SUCCESS: Full workflow completed with recipient data!")
    else:
        print("\n❌ FAILURE: Cargo not found in placement or missing recipient data")

if __name__ == "__main__":
    main()