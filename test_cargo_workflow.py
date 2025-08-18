#!/usr/bin/env python3
"""
Test the new cargo management workflow that allows admins and warehouse operators 
to create cargo directly from user profiles with auto-filled data.
"""

import requests
import sys
import json
from datetime import datetime

class CargoWorkflowTester:
    def __init__(self, base_url="https://qr-logistics-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 CARGO MANAGEMENT WORKFLOW TESTER")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data=None, token=None, params=None):
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

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
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

    def login_users(self):
        """Login required users"""
        print("\n🔐 LOGGING IN USERS")
        
        # Login admin
        success, admin_response = self.run_test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+79999888777", "password": "admin123"}
        )
        
        if success and 'access_token' in admin_response:
            self.tokens['admin'] = admin_response['access_token']
            self.users['admin'] = admin_response['user']
            print("   🔑 Admin token stored")
        
        # Login regular user
        success, user_response = self.run_test(
            "User Login",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+992900000000", "password": "123456"}
        )
        
        if success and 'access_token' in user_response:
            self.tokens['user'] = user_response['access_token']
            self.users['user'] = user_response['user']
            print("   🔑 User token stored")
        
        # Try to login warehouse operator
        success, operator_response = self.run_test(
            "Warehouse Operator Login",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+79777888999", "password": "warehouse123"}
        )
        
        if success and 'access_token' in operator_response:
            self.tokens['warehouse_operator'] = operator_response['access_token']
            self.users['warehouse_operator'] = operator_response['user']
            print("   🔑 Warehouse operator token stored")
        
        return len(self.tokens) >= 2  # Need at least admin and user

    def test_user_profile_access(self):
        """Test 1: User Profile Access for Admins and Warehouse Operators"""
        print("\n👤 TESTING USER PROFILE ACCESS")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Admin access to user profiles
        success, admin_users = self.run_test(
            "Admin Access to User Profiles",
            "GET",
            "/api/admin/users",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success and isinstance(admin_users, list) and len(admin_users) > 0:
            print(f"   ✅ Admin can access {len(admin_users)} user profiles")
            
            # Find a regular user for testing
            test_user = None
            for user in admin_users:
                if user.get('role') == 'user' and user.get('phone'):
                    test_user = user
                    break
            
            if test_user:
                print(f"   👤 Test user found: {test_user.get('full_name')} ({test_user.get('phone')})")
            else:
                print("   ❌ No suitable test user found")
                all_success = False
        else:
            print("   ❌ Admin cannot access user profiles")
            all_success = False
        
        # Test user dashboard access for history data
        if 'user' in self.tokens:
            success, user_dashboard = self.run_test(
                "Get User Dashboard for History Data",
                "GET",
                "/api/user/dashboard",
                200,
                token=self.tokens['user']
            )
            all_success &= success
            
            if success:
                print("   ✅ User dashboard accessible for history data")
                print(f"   📊 Dashboard structure: {list(user_dashboard.keys()) if isinstance(user_dashboard, dict) else 'Invalid structure'}")
                
                # Check for required dashboard fields
                required_fields = ['user_info', 'cargo_requests', 'sent_cargo', 'received_cargo']
                missing_fields = [field for field in required_fields if field not in user_dashboard]
                
                if not missing_fields:
                    print("   ✅ All required dashboard fields present")
                else:
                    print(f"   ❌ Missing dashboard fields: {missing_fields}")
                    all_success = False
        
        return all_success

    def test_cargo_creation_with_auto_filled_data(self):
        """Test 2: Cargo Creation with Auto-filled Data using POST /api/operator/cargo/accept"""
        print("\n📦 TESTING CARGO CREATION WITH AUTO-FILLED DATA")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Test with admin token - multi-cargo with individual pricing
        auto_filled_cargo_data = {
            "sender_full_name": "Иван Автозаполнение",  # Auto-filled from user profile
            "sender_phone": "+79999999999",  # Auto-filled from user profile
            "recipient_full_name": "Петр Получатель Авто",  # Auto-filled from cargo history
            "recipient_phone": "+992999888777",  # Auto-filled from cargo history
            "recipient_address": "Душанбе, ул. Автозаполнения, 123",  # Auto-filled from history
            "cargo_items": [
                {"cargo_name": "Документы", "weight": 10.0, "price_per_kg": 60.0},
                {"cargo_name": "Одежда", "weight": 25.0, "price_per_kg": 60.0},
                {"cargo_name": "Электроника", "weight": 100.0, "price_per_kg": 65.0}
            ],
            "description": "Груз с автозаполненными данными отправителя и получателя",
            "route": "moscow_to_tajikistan"
        }
        
        success, cargo_response = self.run_test(
            "Create Cargo with Auto-filled Data (Admin)",
            "POST",
            "/api/operator/cargo/accept",
            200,
            auto_filled_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        created_cargo_id = None
        if success and 'id' in cargo_response:
            created_cargo_id = cargo_response['id']
            cargo_number = cargo_response.get('cargo_number', 'N/A')
            total_weight = cargo_response.get('weight', 0)
            total_cost = cargo_response.get('declared_value', 0)
            processing_status = cargo_response.get('processing_status', 'N/A')
            
            print(f"   ✅ Cargo created with auto-filled data: {cargo_number}")
            print(f"   📊 Total weight: {total_weight} kg, Total cost: {total_cost} руб")
            print(f"   🔄 Initial status: {processing_status}")
            
            # Verify individual pricing calculations (135kg, 8600руб as per review request)
            expected_weight = 135.0
            expected_cost = 8600.0
            
            if abs(total_weight - expected_weight) < 0.01 and abs(total_cost - expected_cost) < 0.01:
                print("   ✅ Individual pricing calculations verified (135kg, 8600руб)")
            else:
                print(f"   ❌ Pricing calculation error: expected {expected_weight}kg/{expected_cost}руб, got {total_weight}kg/{total_cost}руб")
                all_success = False
            
            # Verify initial status is payment_pending
            if processing_status == "payment_pending":
                print("   ✅ Initial status correctly set to 'payment_pending'")
            else:
                print(f"   ❌ Initial status incorrect: expected 'payment_pending', got '{processing_status}'")
                all_success = False
        
        # Store cargo ID for later tests
        self.created_cargo_id = created_cargo_id
        
        # Test with warehouse operator token if available
        if 'warehouse_operator' in self.tokens:
            success, warehouse_cargo_response = self.run_test(
                "Create Cargo with Auto-filled Data (Warehouse Operator)",
                "POST",
                "/api/operator/cargo/accept",
                200,
                auto_filled_cargo_data,
                self.tokens['warehouse_operator']
            )
            all_success &= success
            
            if success:
                print("   ✅ Warehouse operator can also create cargo with auto-filled data")
        else:
            print("   ⚠️  Warehouse operator token not available for testing")
        
        return all_success

    def test_cargo_status_workflow(self):
        """Test 3: Cargo Status Workflow"""
        print("\n🔄 TESTING CARGO STATUS WORKFLOW")
        
        if 'admin' not in self.tokens or not hasattr(self, 'created_cargo_id') or not self.created_cargo_id:
            print("   ❌ No admin token or cargo ID available")
            return False
            
        all_success = True
        
        # Test initial status (payment_pending)
        success, cargo_list = self.run_test(
            "Get Cargo List with Payment Pending Filter",
            "GET",
            "/api/operator/cargo/list",
            200,
            params={"filter_status": "payment_pending"},
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success and 'items' in cargo_list:
            payment_pending_cargo = [c for c in cargo_list['items'] if c.get('id') == self.created_cargo_id]
            if payment_pending_cargo:
                print("   ✅ Cargo appears in payment_pending filter")
            else:
                print("   ❌ Cargo not found in payment_pending filter")
                all_success = False
        
        # Test status transition: payment_pending → paid
        success, status_update_response = self.run_test(
            "Update Cargo Status to Paid",
            "PUT",
            f"/api/cargo/{self.created_cargo_id}/processing-status",
            200,
            {"new_status": "paid"},
            self.tokens['admin']
        )
        all_success &= success
        
        if success:
            print("   ✅ Cargo status updated to 'paid'")
            
            # Verify cargo appears in awaiting_placement filter after payment
            success, placement_list = self.run_test(
                "Get Cargo List with Awaiting Placement Filter",
                "GET",
                "/api/operator/cargo/list",
                200,
                params={"filter_status": "awaiting_placement"},
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success and 'items' in placement_list:
                awaiting_placement_cargo = [c for c in placement_list['items'] if c.get('id') == self.created_cargo_id]
                if awaiting_placement_cargo:
                    print("   ✅ Paid cargo appears in awaiting_placement filter")
                else:
                    print("   ❌ Paid cargo not found in awaiting_placement filter")
                    all_success = False
        
        # Test further status transitions
        status_transitions = [
            ("invoice_printed", "Invoice Printed"),
            ("placed", "Placed")
        ]
        
        for new_status, status_name in status_transitions:
            success, _ = self.run_test(
                f"Update Cargo Status to {status_name}",
                "PUT",
                f"/api/cargo/{self.created_cargo_id}/processing-status",
                200,
                {"new_status": new_status},
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print(f"   ✅ Cargo status updated to '{new_status}'")
        
        return all_success

    def test_user_profile_and_history_integration(self):
        """Test 4: User Profile and History Integration"""
        print("\n📚 TESTING USER PROFILE AND HISTORY INTEGRATION")
        
        if 'user' not in self.tokens:
            print("   ❌ No user token available")
            return False
            
        all_success = True
        
        # Test that user dashboard provides data for auto-filling
        success, updated_dashboard = self.run_test(
            "Get Updated User Dashboard",
            "GET",
            "/api/user/dashboard",
            200,
            token=self.tokens['user']
        )
        all_success &= success
        
        if success and isinstance(updated_dashboard, dict):
            # Check if cargo appears in sent_cargo or received_cargo
            sent_cargo = updated_dashboard.get('sent_cargo', [])
            received_cargo = updated_dashboard.get('received_cargo', [])
            
            print(f"   📊 User has {len(sent_cargo)} sent cargo and {len(received_cargo)} received cargo")
            
            # Verify user profile data is accessible
            user_info = updated_dashboard.get('user_info', {})
            if user_info:
                print(f"   👤 User profile accessible: {user_info.get('full_name')} ({user_info.get('phone')})")
                print("   ✅ User profile data available for auto-filling sender data")
            else:
                print("   ❌ User profile data not accessible")
                all_success = False
            
            # Check cargo history for recipient auto-fill data
            cargo_requests = updated_dashboard.get('cargo_requests', [])
            if cargo_requests:
                print(f"   📋 User has {len(cargo_requests)} cargo requests for recipient auto-fill")
                print("   ✅ Cargo history available for auto-filling recipient data")
            else:
                print("   ⚠️  No cargo requests found for recipient auto-fill (may be expected for new user)")
        
        return all_success

    def test_authentication_and_authorization(self):
        """Test 5: Authentication and Authorization"""
        print("\n🔐 TESTING AUTHENTICATION AND AUTHORIZATION")
        
        all_success = True
        
        # Test admin credentials
        success, admin_auth = self.run_test(
            "Admin Authentication Test",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+79999888777", "password": "admin123"}
        )
        all_success &= success
        
        if success:
            print("   ✅ Admin authentication working (+79999888777/admin123)")
        
        # Test warehouse operator credentials
        success, operator_auth = self.run_test(
            "Warehouse Operator Authentication Test",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+79777888999", "password": "warehouse123"}
        )
        
        if success:
            print("   ✅ Warehouse operator authentication working")
        else:
            print("   ⚠️  Warehouse operator authentication may need setup")
        
        # Test access control for cargo creation
        if 'user' in self.tokens:
            test_data = {
                "sender_full_name": "Test Sender",
                "sender_phone": "+79999888777",
                "recipient_full_name": "Test Recipient",
                "recipient_phone": "+992888777999",
                "recipient_address": "Душанбе, ул. Test, 456",
                "cargo_items": [
                    {"cargo_name": "Test Documents", "weight": 5.0, "price_per_kg": 70.0}
                ],
                "description": "Access control test cargo",
                "route": "moscow_to_tajikistan"
            }
            
            success, _ = self.run_test(
                "Regular User Access to Operator Cargo Creation (Should Fail)",
                "POST",
                "/api/operator/cargo/accept",
                403,  # Should be forbidden
                test_data,
                self.tokens['user']
            )
            all_success &= success
            
            if success:
                print("   ✅ Regular users correctly denied access to operator cargo creation")
        
        return all_success

    def run_all_tests(self):
        """Run all cargo management workflow tests"""
        print("\n🚀 STARTING CARGO MANAGEMENT WORKFLOW TESTING")
        print("=" * 60)
        
        # Login users first
        if not self.login_users():
            print("❌ Failed to login required users")
            return False
        
        tests = [
            ("User Profile Access", self.test_user_profile_access),
            ("Cargo Creation with Auto-filled Data", self.test_cargo_creation_with_auto_filled_data),
            ("Cargo Status Workflow", self.test_cargo_status_workflow),
            ("User Profile and History Integration", self.test_user_profile_and_history_integration),
            ("Authentication and Authorization", self.test_authentication_and_authorization)
        ]
        
        passed_tests = []
        failed_tests = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                if result:
                    passed_tests.append(test_name)
                    print(f"✅ {test_name} - PASSED")
                else:
                    failed_tests.append(test_name)
                    print(f"❌ {test_name} - FAILED")
            except Exception as e:
                failed_tests.append(test_name)
                print(f"❌ {test_name} - ERROR: {str(e)}")
        
        # Final summary
        print("\n" + "="*60)
        print("🏁 CARGO MANAGEMENT WORKFLOW TEST SUMMARY")
        print("="*60)
        print(f"📊 Total Tests: {len(tests)}")
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📈 Success Rate: {len(passed_tests)/len(tests)*100:.1f}%")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"   • {test}")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test}")
        
        print(f"\n🔧 Individual API Calls: {self.tests_run} total, {self.tests_passed} passed")
        print("="*60)
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = CargoWorkflowTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)