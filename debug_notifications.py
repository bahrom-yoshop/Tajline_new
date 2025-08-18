#!/usr/bin/env python3
"""
Debug script to check warehouse notifications and cargo creation
"""

import requests
import json

def debug_notifications():
    base_url = "https://cargo-talk.preview.emergentagent.com"
    
    # Login as operator
    login_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return
    
    token = response.json()["access_token"]
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get warehouse notifications
    print("🔍 Testing /api/operator/warehouse-notifications endpoint:")
    response = requests.get(f"{base_url}/api/operator/warehouse-notifications", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])
        print(f"Found {len(notifications)} notifications")
        
        for i, notif in enumerate(notifications[:3]):  # Show first 3
            print(f"\nNotification {i+1}:")
            print(f"  ID: {notif.get('id')}")
            print(f"  Status: {notif.get('status')}")
            print(f"  Request ID: {notif.get('request_id')}")
            print(f"  Request Number: {notif.get('request_number')}")
            print(f"  Message: {notif.get('message', 'No message')[:100]}...")
            
            # Try to complete the first pending notification
            if i == 0 and notif.get('status') == 'pending':
                print(f"\n🔄 Trying to accept and complete notification {notif.get('id')}")
                
                # Accept
                accept_response = requests.post(
                    f"{base_url}/api/operator/warehouse-notifications/{notif.get('id')}/accept",
                    headers=headers
                )
                print(f"Accept status: {accept_response.status_code}")
                
                if accept_response.status_code == 200:
                    # Complete with cargo details
                    cargo_completion_data = {
                        "sender_full_name": "Тестовый Отправитель",
                        "sender_phone": "+79123456789",
                        "sender_address": "Москва, ул. Тестовая, 123",
                        "recipient_full_name": "Тестовый Получатель",
                        "recipient_phone": "+79987654321",
                        "recipient_address": "Душанбе, ул. Получателя, 456",
                        "payment_method": "cash",
                        "payment_status": "not_paid",
                        "delivery_method": "pickup",
                        "cargo_items": [
                            {
                                "name": "Тестовый груз",
                                "weight": 10.0,
                                "price": 1000.0
                            }
                        ]
                    }
                    
                    complete_response = requests.post(
                        f"{base_url}/api/operator/warehouse-notifications/{notif.get('id')}/complete",
                        json=cargo_completion_data,
                        headers=headers
                    )
                    print(f"Complete status: {complete_response.status_code}")
                    
                    if complete_response.status_code == 200:
                        complete_data = complete_response.json()
                        print(f"Complete response: {json.dumps(complete_data, indent=2, ensure_ascii=False)}")
                    else:
                        print(f"Complete error: {complete_response.text}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    debug_notifications()