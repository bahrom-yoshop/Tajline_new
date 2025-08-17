#!/usr/bin/env python3
"""
Create test pickup request and warehouse notification for diagnostic purposes
"""

import requests
import sys
import json
from datetime import datetime

class TestDataCreator:
    def __init__(self, base_url="https://tajline-manager-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.operator_token = None
        self.admin_token = None
        
        print(f"🔧 TEST DATA CREATOR FOR PICKUP REQUEST DIAGNOSTIC")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 80)

    def login_operator(self):
        """Login as warehouse operator"""
        print("\n🔐 LOGGING IN AS WAREHOUSE OPERATOR...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        url = f"{self.base_url}/api/auth/login"
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, json=operator_login_data, headers=headers)
            if response.status_code == 200:
                login_response = response.json()
                self.operator_token = login_response['access_token']
                operator_user = login_response.get('user', {})
                print(f"   ✅ Operator login successful: {operator_user.get('full_name')}")
                return True
            else:
                print(f"   ❌ Operator login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Operator login error: {e}")
            return False

    def login_admin(self):
        """Login as admin"""
        print("\n👑 LOGGING IN AS ADMIN...")
        
        admin_login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        url = f"{self.base_url}/api/auth/login"
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, json=admin_login_data, headers=headers)
            if response.status_code == 200:
                login_response = response.json()
                self.admin_token = login_response['access_token']
                admin_user = login_response.get('user', {})
                print(f"   ✅ Admin login successful: {admin_user.get('full_name')}")
                return True
            else:
                print(f"   ❌ Admin login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Admin login error: {e}")
            return False

    def create_pickup_request(self):
        """Create a pickup request that should generate a warehouse notification"""
        print("\n📦 CREATING PICKUP REQUEST...")
        
        if not self.operator_token:
            print("   ❌ No operator token available")
            return False
        
        pickup_request_data = {
            "sender_full_name": "Тест Отправитель Диагностика",
            "sender_phone": "+79991234567",
            "pickup_address": "Москва, ул. Диагностическая, 100010",
            "pickup_date": "2025-01-20",
            "pickup_time_from": "10:00",
            "pickup_time_to": "18:00",
            "route": "moscow_to_tajikistan",
            "courier_fee": 500.0,
            "destination": "Душанбе, ул. Тестовая, 1"
        }
        
        url = f"{self.base_url}/api/admin/courier/pickup-request"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.operator_token}'
        }
        
        try:
            response = requests.post(url, json=pickup_request_data, headers=headers)
            if response.status_code == 200:
                pickup_response = response.json()
                pickup_request_id = pickup_response.get('id')
                request_number = pickup_response.get('request_number')
                print(f"   ✅ Pickup request created successfully!")
                print(f"   📋 Request ID: {pickup_request_id}")
                print(f"   📋 Request Number: {request_number}")
                return pickup_request_id, request_number
            else:
                print(f"   ❌ Pickup request creation failed: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   📄 Error: {error_detail}")
                except:
                    print(f"   📄 Raw response: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Pickup request creation error: {e}")
            return False

    def check_warehouse_notifications_after_creation(self):
        """Check warehouse notifications after creating pickup request"""
        print("\n📋 CHECKING WAREHOUSE NOTIFICATIONS AFTER CREATION...")
        
        if not self.operator_token:
            print("   ❌ No operator token available")
            return False
        
        url = f"{self.base_url}/api/operator/warehouse-notifications"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.operator_token}'
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                notifications = response.json()
                notification_count = len(notifications) if isinstance(notifications, list) else 0
                
                print(f"   ✅ Found {notification_count} warehouse notifications")
                
                if notification_count > 0:
                    print("\n   📋 WAREHOUSE NOTIFICATIONS:")
                    for i, notification in enumerate(notifications, 1):
                        notification_id = notification.get('id', 'N/A')
                        notification_number = notification.get('notification_number', 'N/A')
                        pickup_request_id = notification.get('pickup_request_id', 'N/A')
                        status = notification.get('status', 'N/A')
                        sender_name = notification.get('sender_full_name', 'N/A')
                        
                        print(f"   {i}. ID: {notification_id}")
                        print(f"      Number: {notification_number}")
                        print(f"      pickup_request_id: {pickup_request_id}")
                        print(f"      Status: {status}")
                        print(f"      Sender: {sender_name}")
                        print(f"      ---")
                        
                        # Check if this is notification #100010
                        if str(notification_number) == '100010':
                            print(f"   🎯 FOUND NOTIFICATION #100010!")
                            return notification
                
                return notifications
            else:
                print(f"   ❌ Failed to get warehouse notifications: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Error getting warehouse notifications: {e}")
            return False

    def test_pickup_request_endpoint(self, pickup_request_id):
        """Test the pickup request endpoint"""
        print(f"\n🔗 TESTING PICKUP REQUEST ENDPOINT...")
        print(f"   📋 GET /api/operator/pickup-requests/{pickup_request_id}")
        
        if not self.operator_token:
            print("   ❌ No operator token available")
            return False
        
        url = f"{self.base_url}/api/operator/pickup-requests/{pickup_request_id}"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.operator_token}'
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                pickup_request = response.json()
                print(f"   ✅ Pickup request endpoint working!")
                
                print("\n   📊 PICKUP REQUEST STRUCTURE:")
                for key, value in pickup_request.items():
                    print(f"   {key}: {value}")
                
                return True
            else:
                print(f"   ❌ Pickup request endpoint failed: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   📄 Error: {error_detail}")
                except:
                    print(f"   📄 Raw response: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Error testing pickup request endpoint: {e}")
            return False

    def run_full_test(self):
        """Run full test to create data and diagnose"""
        print("🚀 STARTING TEST DATA CREATION AND DIAGNOSTIC")
        
        # Step 1: Login as operator
        if not self.login_operator():
            print("\n❌ TEST FAILED: Cannot login as operator")
            return False
        
        # Step 2: Check current notifications (should be empty)
        print("\n📋 CHECKING CURRENT NOTIFICATIONS (BEFORE CREATION)...")
        initial_notifications = self.check_warehouse_notifications_after_creation()
        
        # Step 3: Create pickup request
        pickup_result = self.create_pickup_request()
        if not pickup_result:
            print("\n❌ TEST FAILED: Cannot create pickup request")
            return False
        
        pickup_request_id, request_number = pickup_result
        
        # Step 4: Check notifications after creation
        final_notifications = self.check_warehouse_notifications_after_creation()
        
        # Step 5: Test pickup request endpoint if we have an ID
        if pickup_request_id:
            self.test_pickup_request_endpoint(pickup_request_id)
        
        # Final summary
        print("\n" + "="*80)
        print("📊 TEST DATA CREATION SUMMARY")
        print("="*80)
        
        if final_notifications and isinstance(final_notifications, list) and len(final_notifications) > 0:
            print("✅ SUCCESS: Warehouse notifications created")
            print(f"📊 Total notifications: {len(final_notifications)}")
            
            # Check if any notification has pickup_request_id
            notifications_with_pickup_id = [n for n in final_notifications if isinstance(n, dict) and n.get('pickup_request_id')]
            if notifications_with_pickup_id:
                print(f"✅ {len(notifications_with_pickup_id)} notifications have pickup_request_id")
            else:
                print("❌ NO notifications have pickup_request_id")
        else:
            print("❌ FAILED: No warehouse notifications created")
        
        print("\n🎯 NEXT STEPS:")
        print("1. Run the diagnostic test again to see if notification #100010 exists")
        print("2. Check if the pickup_request_id is properly set")
        print("3. Test the 'Продолжить оформление' button functionality")
        
        return True

if __name__ == "__main__":
    creator = TestDataCreator()
    creator.run_full_test()