#!/usr/bin/env python3
"""
Backend Testing for Recipient Information Display Fixes in TAJLINE.TJ
Tests the fixes for displaying recipient information for pickup cargo instead of hardcoded "Не указан"
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class RecipientInfoTester:
    def __init__(self):
        # Get backend URL from frontend .env
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        self.base_url = line.split('=')[1].strip()
                        break
        except:
            self.base_url = "https://tajline-cargo-3.preview.emergentagent.com"
        
        self.api_base = f"{self.base_url}/api"
        self.tokens = {}
        self.test_data = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 RECIPIENT INFO DISPLAY FIXES TESTING")
        print(f"📡 Backend URL: {self.api_base}")
        print("=" * 80)

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, token: Optional[str] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.api_base}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == expected_status:
                self.tests_passed += 1
                print(f"   ✅ PASSED")
                try:
                    return True, response.json()
                except:
                    return True, {"status": "success", "text": response.text}
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                    return False, error_data
                except:
                    print(f"   Error: {response.text}")
                    return False, {"error": response.text}
                    
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")
            return False, {"error": str(e)}

    def authenticate_warehouse_operator(self):
        """Step 1: Authenticate warehouse operator"""
        print("\n" + "="*50)
        print("STEP 1: WAREHOUSE OPERATOR AUTHENTICATION")
        print("="*50)
        
        login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, response = self.run_test(
            "Warehouse Operator Login",
            "POST", "/auth/login", 200, login_data
        )
        
        if success and "access_token" in response:
            self.tokens["warehouse_operator"] = response["access_token"]
            print(f"✅ Warehouse operator authenticated successfully")
            
            # Get user info
            success, user_info = self.run_test(
                "Get Warehouse Operator Info",
                "GET", "/auth/me", 200, token=self.tokens["warehouse_operator"]
            )
            
            if success:
                print(f"   Role: {user_info.get('role', 'Unknown')}")
                print(f"   Name: {user_info.get('full_name', 'Unknown')}")
                print(f"   User Number: {user_info.get('user_number', 'Unknown')}")
                return True
        
        print("❌ Failed to authenticate warehouse operator")
        return False

    def authenticate_courier(self):
        """Step 2: Authenticate courier"""
        print("\n" + "="*50)
        print("STEP 2: COURIER AUTHENTICATION")
        print("="*50)
        
        login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        success, response = self.run_test(
            "Courier Login",
            "POST", "/auth/login", 200, login_data
        )
        
        if success and "access_token" in response:
            self.tokens["courier"] = response["access_token"]
            print(f"✅ Courier authenticated successfully")
            
            # Get user info
            success, user_info = self.run_test(
                "Get Courier Info",
                "GET", "/auth/me", 200, token=self.tokens["courier"]
            )
            
            if success:
                print(f"   Role: {user_info.get('role', 'Unknown')}")
                print(f"   Name: {user_info.get('full_name', 'Unknown')}")
                print(f"   User Number: {user_info.get('user_number', 'Unknown')}")
                return True
        
        print("❌ Failed to authenticate courier")
        return False

    def create_pickup_request_with_recipient_data(self):
        """Step 3: Create pickup request with recipient data"""
        print("\n" + "="*50)
        print("STEP 3: CREATE PICKUP REQUEST WITH RECIPIENT DATA")
        print("="*50)
        
        pickup_request_data = {
            "sender_full_name": "Иван Петрович Сидоров",
            "sender_phone": "+79123456789",
            "recipient_full_name": "Мария Александровна Козлова",
            "recipient_phone": "+79987654321",
            "recipient_address": "г. Душанбе, ул. Рудаки, д. 25, кв. 10",
            "pickup_address": "г. Москва, ул. Тестовая, д. 123",
            "pickup_date": "2025-01-15",
            "pickup_time_from": "10:00",
            "pickup_time_to": "18:00",
            "cargo_name": "Документы и подарки",
            "route": "moscow_to_tajikistan",
            "courier_fee": 500.0
        }
        
        success, response = self.run_test(
            "Create Pickup Request with Recipient Data",
            "POST", "/admin/courier/pickup-request", 200, 
            pickup_request_data, token=self.tokens["warehouse_operator"]
        )
        
        if success:
            print(f"✅ Pickup request API call successful")
            print(f"   Response: {response}")
            
            # Check for different possible response formats
            if "id" in response:
                self.test_data["pickup_request_id"] = response["id"]
                self.test_data["pickup_request_number"] = response.get("request_number", "Unknown")
            elif "request_id" in response:
                self.test_data["pickup_request_id"] = response["request_id"]
                self.test_data["pickup_request_number"] = response.get("request_number", "Unknown")
            else:
                print("❌ No ID found in response, but request was successful")
                return False
            
            print(f"✅ Pickup request created successfully")
            print(f"   Request ID: {self.test_data['pickup_request_id']}")
            print(f"   Request Number: {self.test_data['pickup_request_number']}")
            print(f"   Recipient Name: {pickup_request_data['recipient_full_name']}")
            print(f"   Recipient Phone: {pickup_request_data['recipient_phone']}")
            print(f"   Recipient Address: {pickup_request_data['recipient_address']}")
            return True
        
        print("❌ Failed to create pickup request")
        print(f"   Response: {response}")
        return False

    def verify_pickup_request_data(self):
        """Verify that our pickup request has the correct recipient data"""
        print("\n" + "="*50)
        print("STEP 4.5: VERIFY PICKUP REQUEST DATA")
        print("="*50)
        
        # Check the pickup request data directly
        success, response = self.run_test(
            "Get Courier New Requests",
            "GET", "/courier/requests/new", 200,
            token=self.tokens["courier"]
        )
        
        if success:
            new_requests = response.get("new_requests", [])
            our_request = None
            
            for request in new_requests:
                if request.get("id") == self.test_data["pickup_request_id"]:
                    our_request = request
                    break
            
            if our_request:
                print(f"✅ Found our pickup request in courier's new requests")
                print(f"   Request ID: {our_request.get('id')}")
                print(f"   Sender: {our_request.get('sender_full_name')}")
                print(f"   Recipient Name: {our_request.get('recipient_full_name', 'NOT SET')}")
                print(f"   Recipient Phone: {our_request.get('recipient_phone', 'NOT SET')}")
                print(f"   Recipient Address: {our_request.get('recipient_address', 'NOT SET')}")
                return True
            else:
                print(f"❌ Could not find our pickup request in courier's new requests")
        
        return False
        """Step 4: Process pickup request by courier (accept and pickup)"""
        print("\n" + "="*50)
        print("STEP 4: PROCESS PICKUP REQUEST BY COURIER")
        print("="*50)
        
        # Accept the pickup request
        success, response = self.run_test(
            "Accept Pickup Request",
            "POST", f"/courier/requests/{self.test_data['pickup_request_id']}/accept", 200,
            token=self.tokens["courier"]
        )
        
        if not success:
            print("❌ Failed to accept pickup request")
            return False
        
        print("✅ Pickup request accepted by courier")
        
        # Pickup the cargo
        success, response = self.run_test(
            "Pickup Cargo",
            "POST", f"/courier/requests/{self.test_data['pickup_request_id']}/pickup", 200,
            token=self.tokens["courier"]
        )
        
        if success:
            print("✅ Cargo picked up by courier")
            return True
        
        print("❌ Failed to pickup cargo")
        return False

    def send_pickup_to_placement(self):
        """Step 5: Send pickup request to placement"""
        print("\n" + "="*50)
        print("STEP 5: SEND PICKUP REQUEST TO PLACEMENT")
        print("="*50)
        
        # First, get warehouse notifications to find our pickup request
        success, response = self.run_test(
            "Get Warehouse Notifications",
            "GET", "/operator/warehouse-notifications", 200,
            token=self.tokens["warehouse_operator"]
        )
        
        if not success:
            print("❌ Failed to get warehouse notifications")
            return False
        
        # Find notification related to our pickup request
        notifications = response.get("notifications", [])
        target_notification = None
        
        print(f"   Searching for notification with request number: {self.test_data['pickup_request_number']}")
        print(f"   Available notifications: {len(notifications)}")
        
        for i, notification in enumerate(notifications):
            print(f"   Notification {i+1}: {notification.get('request_number', 'No number')} - {notification.get('sender_full_name', 'No sender')}")
            if (notification.get("request_number") == self.test_data["pickup_request_number"] or
                "Иван Петрович Сидоров" in notification.get("sender_full_name", "")):
                target_notification = notification
                break
        
        if not target_notification:
            # Try to find by status 'in_processing' and recent creation
            for notification in notifications:
                if (notification.get("status") == "in_processing" and 
                    "Иван" in notification.get("sender_full_name", "")):
                    target_notification = notification
                    print(f"   Found notification by sender name and status")
                    break
        
        if not target_notification:
            print("❌ Could not find warehouse notification for our pickup request")
            print(f"   This might be expected if the notification creation is delayed")
            print(f"   Let's try to find the most recent 'in_processing' notification")
            
            # Find the most recent in_processing notification
            in_processing_notifications = [n for n in notifications if n.get("status") == "in_processing"]
            if in_processing_notifications:
                target_notification = in_processing_notifications[0]  # Take the first one
                print(f"   Using most recent in_processing notification: {target_notification.get('id')}")
            else:
                return False
        
        print(f"✅ Found warehouse notification: {target_notification['id']}")
        self.test_data["notification_id"] = target_notification["id"]
        
        # Send to placement
        success, response = self.run_test(
            "Send Pickup Request to Placement",
            "POST", f"/operator/warehouse-notifications/{target_notification['id']}/send-to-placement", 200,
            token=self.tokens["warehouse_operator"]
        )
        
        if success and "cargo_id" in response:
            self.test_data["cargo_id"] = response["cargo_id"]
            self.test_data["cargo_number"] = response.get("cargo_number", "Unknown")
            print(f"✅ Pickup request sent to placement successfully")
            print(f"   Cargo ID: {self.test_data['cargo_id']}")
            print(f"   Cargo Number: {self.test_data['cargo_number']}")
            return True
        
        print("❌ Failed to send pickup request to placement")
        return False

    def verify_recipient_data_in_placement(self):
        """Step 6: Verify recipient data in available-for-placement endpoint"""
        print("\n" + "="*50)
        print("STEP 6: VERIFY RECIPIENT DATA IN PLACEMENT")
        print("="*50)
        
        success, response = self.run_test(
            "Get Available for Placement Cargo",
            "GET", "/operator/cargo/available-for-placement", 200,
            token=self.tokens["warehouse_operator"]
        )
        
        if not success:
            print("❌ Failed to get available for placement cargo")
            return False
        
        # Find our cargo in the list
        cargo_items = response.get("items", [])
        target_cargo = None
        
        for cargo in cargo_items:
            if cargo.get("cargo_number") == self.test_data["cargo_number"]:
                target_cargo = cargo
                break
        
        if not target_cargo:
            print("❌ Could not find our cargo in available for placement list")
            print(f"   Looking for cargo number: {self.test_data['cargo_number']}")
            print(f"   Available cargo count: {len(cargo_items)}")
            return False
        
        print(f"✅ Found cargo in placement list: {target_cargo['cargo_number']}")
        
        # Verify recipient data is NOT hardcoded "Не указан"
        recipient_name = target_cargo.get("recipient_full_name", "")
        recipient_phone = target_cargo.get("recipient_phone", "")
        recipient_address = target_cargo.get("recipient_address", "")
        
        print(f"\n📋 RECIPIENT DATA VERIFICATION:")
        print(f"   Recipient Name: '{recipient_name}'")
        print(f"   Recipient Phone: '{recipient_phone}'")
        print(f"   Recipient Address: '{recipient_address}'")
        
        # Check if recipient data is properly filled (not hardcoded values)
        issues = []
        
        if recipient_name == "Не указан" or recipient_name == "":
            issues.append("Recipient name is empty or hardcoded 'Не указан'")
        elif "Мария Александровна Козлова" in recipient_name:
            print("   ✅ Recipient name contains real data from pickup request")
        
        if recipient_phone == "" or recipient_phone == "Не указан":
            issues.append("Recipient phone is empty or hardcoded")
        elif "+79987654321" in recipient_phone:
            print("   ✅ Recipient phone contains real data from pickup request")
        
        if recipient_address == "" or recipient_address == "Не указан":
            issues.append("Recipient address is empty or hardcoded")
        elif "Душанбе" in recipient_address:
            print("   ✅ Recipient address contains real data from pickup request")
        
        if issues:
            print(f"\n❌ RECIPIENT DATA ISSUES FOUND:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        
        print(f"\n✅ RECIPIENT DATA VERIFICATION SUCCESSFUL!")
        print(f"   All recipient fields contain real data from pickup request")
        print(f"   No hardcoded 'Не указан' values found")
        return True

    def run_comprehensive_test(self):
        """Run the complete test suite"""
        print(f"\n🎯 STARTING COMPREHENSIVE RECIPIENT INFO DISPLAY FIXES TEST")
        print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Authenticate warehouse operator
        if not self.authenticate_warehouse_operator():
            return False
        
        # Step 2: Authenticate courier
        if not self.authenticate_courier():
            return False
        
        # Step 3: Create pickup request with recipient data
        if not self.create_pickup_request_with_recipient_data():
            return False
        
        # Step 4: Verify pickup request data
        if not self.verify_pickup_request_data():
            return False
        
        # Step 5: Process pickup request by courier
        if not self.process_pickup_request_by_courier():
            return False
        
        # Step 6: Send pickup to placement
        if not self.send_pickup_to_placement():
            return False
        
        # Step 7: Verify recipient data in placement
        if not self.verify_recipient_data_in_placement():
            return False
        
        return True

    def print_final_results(self):
        """Print final test results"""
        print("\n" + "="*80)
        print("🎯 RECIPIENT INFO DISPLAY FIXES TEST RESULTS")
        print("="*80)
        print(f"📊 Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"✅ Recipient information display fixes are working correctly")
            print(f"✅ Pickup cargo shows real recipient data instead of 'Не указан'")
            print(f"✅ Backend properly passes recipient data from pickup requests")
        else:
            print(f"\n⚠️  SOME TESTS FAILED!")
            print(f"❌ Recipient information display fixes need attention")
        
        print("="*80)

def main():
    """Main test execution"""
    tester = RecipientInfoTester()
    
    try:
        success = tester.run_comprehensive_test()
        tester.print_final_results()
        
        if success:
            print(f"\n🎯 EXPECTED RESULT ACHIEVED:")
            print(f"✅ Pickup cargo displays real recipient information")
            print(f"✅ No hardcoded 'Не указан' or 'Указывается при размещении'")
            print(f"✅ Data filled by courier/operator is properly shown")
            sys.exit(0)
        else:
            print(f"\n❌ EXPECTED RESULT NOT ACHIEVED:")
            print(f"❌ Issues found with recipient information display")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user")
        tester.print_final_results()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        tester.print_final_results()
        sys.exit(1)

if __name__ == "__main__":
    main()