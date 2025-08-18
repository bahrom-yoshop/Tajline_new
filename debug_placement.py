#!/usr/bin/env python3
"""
Debug the send_pickup_request_to_placement function
"""

import requests
import json

BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"

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

def get_notification_with_pickup_data(token):
    """Get a notification and check its pickup request data"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get warehouse notifications
    response = requests.get(f"{BACKEND_URL}/operator/warehouse-notifications", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])
        
        # Find a notification that hasn't been sent to placement yet
        for notification in notifications:
            if notification.get("status") != "sent_to_placement":
                notification_id = notification.get("id")
                pickup_request_id = notification.get("pickup_request_id")
                
                print(f"🔍 Found notification: {notification_id}")
                print(f"📋 Pickup request ID: {pickup_request_id}")
                
                # Get the pickup request details
                if pickup_request_id:
                    response = requests.get(f"{BACKEND_URL}/operator/pickup-requests/{pickup_request_id}", headers=headers)
                    
                    if response.status_code == 200:
                        pickup_data = response.json()
                        full_request = pickup_data.get("full_request", {})
                        
                        print(f"📋 Pickup Request data before sending to placement:")
                        print(f"   - recipient_full_name: '{full_request.get('recipient_full_name')}'")
                        print(f"   - recipient_phone: '{full_request.get('recipient_phone')}'")
                        print(f"   - recipient_address: '{full_request.get('recipient_address')}'")
                        print(f"   - sender_full_name: '{full_request.get('sender_full_name')}'")
                        print(f"   - route: '{full_request.get('route')}'")
                        print(f"   - destination: '{full_request.get('destination')}'")
                        
                        return notification_id, full_request
                    else:
                        print(f"❌ Error getting pickup request: {response.status_code}")
                
        print("❌ No suitable notification found")
        return None, None
    else:
        print(f"❌ Error getting notifications: {response.status_code}")
        return None, None

def test_send_to_placement_with_debug(token, notification_id):
    """Test send to placement and capture the error details"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n🧪 Testing send-to-placement for notification: {notification_id}")
    
    response = requests.post(f"{BACKEND_URL}/operator/warehouse-notifications/{notification_id}/send-to-placement", 
                           headers=headers)
    
    print(f"📊 Response status: {response.status_code}")
    print(f"📊 Response headers: {dict(response.headers)}")
    print(f"📊 Response body: {response.text}")
    
    if response.status_code != 200:
        print(f"\n❌ ERROR DETAILS:")
        try:
            error_data = response.json()
            print(f"   - Error message: {error_data.get('detail', 'No detail provided')}")
        except:
            print(f"   - Raw response: {response.text}")
    
    return response.status_code == 200

def main():
    print("🔍 DEBUGGING SEND PICKUP REQUEST TO PLACEMENT")
    print("=" * 60)
    
    token = authenticate_operator()
    if not token:
        print("❌ Authentication failed")
        return
    
    # Get a notification with pickup data
    notification_id, pickup_data = get_notification_with_pickup_data(token)
    
    if not notification_id:
        print("❌ No suitable notification found for testing")
        return
    
    # Test send to placement
    success = test_send_to_placement_with_debug(token, notification_id)
    
    if success:
        print("\n✅ SUCCESS: Send to placement worked!")
    else:
        print("\n❌ FAILURE: Send to placement failed!")

if __name__ == "__main__":
    main()