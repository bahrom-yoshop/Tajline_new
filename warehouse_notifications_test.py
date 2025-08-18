#!/usr/bin/env python3
"""
Comprehensive Testing for New Warehouse Notifications System in TAJLINE.TJ
Tests the complete cycle from pickup request creation to warehouse operator cargo acceptance
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class WarehouseNotificationsTester:
    def __init__(self, base_url="https://tajline-cargo-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.request_ids = []  # Store created request IDs
        self.notification_ids = []  # Store notification IDs
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🔔 TAJLINE.TJ Warehouse Notifications System Tester")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 80)

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, token: Optional[str] = None, 
                 params: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
                    if isinstance(result, dict) and len(str(result)) < 300:
                        print(f"   📄 Response: {result}")
                    elif isinstance(result, list) and len(result) <= 3:
                        print(f"   📄 Response: {result}")
                    else:
                        print(f"   📄 Response: Large data structure with {len(result) if isinstance(result, (list, dict)) else 'unknown'} items")
                    return True, result
                except:
                    return True, {}
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   📄 Error: {error_detail}")
                except:
                    print(f"   📄 Raw response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"   ❌ FAILED - Exception: {str(e)}")
            return False, {}

    def test_complete_notification_cycle(self):
        """Test the complete warehouse notifications cycle"""
        print("\n🎯 COMPLETE WAREHOUSE NOTIFICATIONS CYCLE TESTING")
        print("   Testing full cycle from pickup request to warehouse operator acceptance")
        
        all_success = True
        
        # Step 1: Operator Authentication
        print("\n📋 STEP 1: OPERATOR AUTHENTICATION")
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Warehouse Operator Login (+79777888999/warehouse123)",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        all_success &= success
        
        operator_token = None
        if success and 'access_token' in login_response:
            operator_token = login_response['access_token']
            operator_user = login_response.get('user', {})
            print(f"   ✅ Operator authenticated: {operator_user.get('full_name')} ({operator_user.get('role')})")
            self.tokens['operator'] = operator_token
            self.users['operator'] = operator_user
        else:
            print("   ❌ Operator authentication failed")
            return False
        
        # Step 2: Create Pickup Request
        print("\n📦 STEP 2: CREATE PICKUP REQUEST")
        pickup_request_data = {
            "sender_full_name": "Тестовый Отправитель Уведомлений",
            "sender_phone": "+79123456789",
            "pickup_address": "Москва, ул. Тестовая для Уведомлений, 123",
            "pickup_date": "2025-01-20",
            "pickup_time_from": "10:00",
            "pickup_time_to": "12:00",
            "route": "moscow_to_tajikistan",
            "courier_fee": 500.0,
            "cargo_name": "Тестовый груз для системы уведомлений",
            "weight": 5.5,
            "declared_value": 2500.0,
            "description": "Тестовый груз для проверки системы уведомлений склада"
        }
        
        success, pickup_response = self.run_test(
            "Create Pickup Request for Notifications Testing",
            "POST",
            "/api/admin/courier/pickup-request",
            200,
            pickup_request_data,
            operator_token
        )
        all_success &= success
        
        request_id = None
        if success and 'request_id' in pickup_response:
            request_id = pickup_response['request_id']
            request_number = pickup_response.get('request_number')
            print(f"   ✅ Pickup request created: ID {request_id}, Number {request_number}")
            self.request_ids.append(request_id)
        else:
            print("   ❌ Pickup request creation failed")
            return False
        
        # Step 3: Courier Authentication
        print("\n🚚 STEP 3: COURIER AUTHENTICATION")
        courier_login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        success, courier_login_response = self.run_test(
            "Courier Login (+79991234567/courier123)",
            "POST",
            "/api/auth/login",
            200,
            courier_login_data
        )
        all_success &= success
        
        courier_token = None
        if success and 'access_token' in courier_login_response:
            courier_token = courier_login_response['access_token']
            courier_user = courier_login_response.get('user', {})
            print(f"   ✅ Courier authenticated: {courier_user.get('full_name')} ({courier_user.get('role')})")
            self.tokens['courier'] = courier_token
            self.users['courier'] = courier_user
        else:
            print("   ❌ Courier authentication failed")
            return False
        
        # Step 4: Accept Pickup Request
        print("\n✋ STEP 4: ACCEPT PICKUP REQUEST")
        success, accept_response = self.run_test(
            "Accept Pickup Request by Courier",
            "POST",
            f"/api/courier/requests/{request_id}/accept",
            200,
            {},
            courier_token
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Pickup request {request_id} accepted by courier")
        else:
            print("   ❌ Pickup request acceptance failed")
            return False
        
        # Step 5: Pickup Cargo
        print("\n📋 STEP 5: PICKUP CARGO")
        success, pickup_cargo_response = self.run_test(
            "Pickup Cargo by Courier",
            "POST",
            f"/api/courier/requests/{request_id}/pickup",
            200,
            {},
            courier_token
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Cargo picked up for request {request_id}")
        else:
            print("   ❌ Cargo pickup failed")
            return False
        
        # Step 6: NEW TEST - Deliver Cargo to Warehouse (Should Create Notification)
        print("\n🏭 STEP 6: DELIVER CARGO TO WAREHOUSE (NEW FUNCTIONALITY)")
        success, deliver_response = self.run_test(
            "Deliver Cargo to Warehouse (Creates Notification)",
            "POST",
            f"/api/courier/requests/{request_id}/deliver-to-warehouse",
            200,
            {},
            courier_token
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Cargo delivered to warehouse for request {request_id}")
            print("   📢 Notification should be created for warehouse operators")
        else:
            print("   ❌ Cargo delivery to warehouse failed")
            return False
        
        # Step 7: NEW TEST - Get Warehouse Notifications
        print("\n🔔 STEP 7: GET WAREHOUSE NOTIFICATIONS (NEW ENDPOINT)")
        success, notifications_response = self.run_test(
            "Get Warehouse Notifications for Operator",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        all_success &= success
        
        notification_id = None
        if success:
            notifications = notifications_response if isinstance(notifications_response, list) else notifications_response.get('notifications', [])
            print(f"   ✅ Retrieved {len(notifications)} warehouse notifications")
            
            # Find our notification
            for notification in notifications:
                if notification.get('related_request_id') == request_id:
                    notification_id = notification.get('id')
                    print(f"   📢 Found notification for our request: {notification_id}")
                    print(f"   📄 Notification message: {notification.get('message', 'N/A')}")
                    self.notification_ids.append(notification_id)
                    break
            
            if not notification_id:
                print("   ⚠️ No notification found for our delivered cargo")
        else:
            print("   ❌ Failed to get warehouse notifications")
            return False
        
        # Step 8: NEW TEST - Accept Cargo by Operator
        if notification_id:
            print("\n✅ STEP 8: ACCEPT CARGO BY WAREHOUSE OPERATOR (NEW ENDPOINT)")
            success, accept_cargo_response = self.run_test(
                "Accept Cargo by Warehouse Operator",
                "POST",
                f"/api/operator/warehouse-notifications/{notification_id}/accept",
                200,
                {},
                operator_token
            )
            all_success &= success
            
            if success:
                print(f"   ✅ Cargo accepted by warehouse operator via notification {notification_id}")
            else:
                print("   ❌ Cargo acceptance by operator failed")
                all_success = False
        else:
            print("\n⚠️ STEP 8: SKIPPED - No notification ID available")
            all_success = False
        
        # Step 9: NEW TEST - Get All Pickup Requests
        print("\n📋 STEP 9: GET ALL PICKUP REQUESTS (NEW ENDPOINT)")
        success, pickup_requests_response = self.run_test(
            "Get All Pickup Requests for Operators",
            "GET",
            "/api/operator/pickup-requests",
            200,
            token=operator_token
        )
        all_success &= success
        
        if success:
            pickup_requests = pickup_requests_response if isinstance(pickup_requests_response, list) else pickup_requests_response.get('requests', [])
            print(f"   ✅ Retrieved {len(pickup_requests)} pickup requests")
            
            # Find our request
            our_request = None
            for req in pickup_requests:
                if req.get('id') == request_id:
                    our_request = req
                    break
            
            if our_request:
                print(f"   📦 Found our request in the list: {our_request.get('request_number')}")
                print(f"   📊 Request status: {our_request.get('request_status')}")
            else:
                print("   ⚠️ Our request not found in pickup requests list")
        else:
            print("   ❌ Failed to get pickup requests")
            all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all warehouse notifications tests"""
        print("\n🚀 STARTING WAREHOUSE NOTIFICATIONS SYSTEM TESTING")
        print("=" * 80)
        
        start_time = datetime.now()
        
        # Run the complete notification cycle test
        cycle_success = self.test_complete_notification_cycle()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Print final results
        print("\n" + "=" * 80)
        print("📊 FINAL TEST RESULTS")
        print("=" * 80)
        print(f"⏱️  Total testing time: {duration:.2f} seconds")
        print(f"🧪 Tests run: {self.tests_run}")
        print(f"✅ Tests passed: {self.tests_passed}")
        print(f"❌ Tests failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if cycle_success:
            print("\n🎉 WAREHOUSE NOTIFICATIONS SYSTEM TESTING COMPLETED SUCCESSFULLY!")
            print("✅ All new endpoints working correctly:")
            print("   • /api/courier/requests/{request_id}/deliver-to-warehouse")
            print("   • /api/operator/warehouse-notifications")
            print("   • /api/operator/warehouse-notifications/{notification_id}/accept")
            print("   • /api/operator/pickup-requests")
            print("\n🔄 Complete cycle from pickup request to warehouse acceptance works!")
        else:
            print("\n❌ WAREHOUSE NOTIFICATIONS SYSTEM TESTING FAILED!")
            print("Some endpoints or functionality not working as expected.")
        
        return cycle_success

if __name__ == "__main__":
    tester = WarehouseNotificationsTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)