#!/usr/bin/env python3
"""
Check notification status
"""

import requests
import json

BACKEND_URL = "https://tajline-manager-1.preview.emergentagent.com/api"

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

def check_notification_statuses(token):
    """Check the status of recent notifications"""
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BACKEND_URL}/operator/warehouse-notifications", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])
        
        print(f"Found {len(notifications)} notifications")
        
        for notification in notifications[:5]:  # Check first 5
            notification_id = notification.get("id")
            status = notification.get("status")
            request_number = notification.get("request_number")
            
            print(f"\n📋 Notification: {notification_id}")
            print(f"   - Request number: {request_number}")
            print(f"   - Status: '{status}'")
            print(f"   - Expected status for placement: 'in_processing'")
            
            if status == "in_processing":
                print(f"   ✅ Ready for placement")
            else:
                print(f"   ❌ Not ready for placement (status: {status})")
    else:
        print(f"❌ Error getting notifications: {response.status_code}")

def main():
    print("🔍 CHECKING NOTIFICATION STATUSES")
    print("=" * 50)
    
    token = authenticate_operator()
    if not token:
        print("❌ Authentication failed")
        return
    
    check_notification_statuses(token)

if __name__ == "__main__":
    main()