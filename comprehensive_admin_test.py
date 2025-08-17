#!/usr/bin/env python3
"""
Comprehensive Admin Panel Enhancements and Personal Dashboard Testing
Tests user number generation, role management API, and personal dashboard functionality
Based on actual API implementation analysis
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class ComprehensiveAdminTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.tests_run = 0
        self.tests_passed = 0
        self.critical_issues = []
        self.minor_issues = []
        
        print(f"🎯 COMPREHENSIVE ADMIN PANEL & DASHBOARD TESTER")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 70)

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
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
                    if isinstance(result, dict) and len(str(result)) < 400:
                        print(f"   📄 Response: {result}")
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

    def setup_test_environment(self):
        """Setup test environment with admin and test users"""
        print("\n🔧 SETTING UP TEST ENVIRONMENT")
        
        # Login with existing admin
        admin_login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        success, admin_response = self.run_test(
            "Login Existing Admin User",
            "POST",
            "/api/auth/login",
            200,
            admin_login_data
        )
        
        if success and 'access_token' in admin_response:
            self.tokens['admin'] = admin_response['access_token']
            self.users['admin'] = admin_response['user']
            print(f"   🔑 Admin token stored")
        else:
            print("   ❌ Failed to setup admin user")
            return False
        
        # Create a new test user with unique phone
        import time
        unique_suffix = str(int(time.time()))[-4:]
        test_user_data = {
            "full_name": "Тест Пользователь Админ",
            "phone": f"+7977766{unique_suffix}",
            "password": "test123",
            "role": "user"
        }
        
        success, user_response = self.run_test(
            "Create Test User",
            "POST",
            "/api/auth/register",
            200,
            test_user_data
        )
        
        if success and 'access_token' in user_response:
            self.tokens['test_user'] = user_response['access_token']
            self.users['test_user'] = user_response['user']
            print(f"   🔑 Test user token stored")
            return True
        else:
            print("   ❌ Failed to create test user")
            return False

    def test_user_number_generation(self):
        """Test 1: User Number Display Testing"""
        print("\n🔢 USER NUMBER GENERATION TESTING")
        
        all_success = True
        
        # Check if test user has user_number
        if 'test_user' in self.users:
            user_data = self.users['test_user']
            user_number = user_data.get('user_number')
            
            # Verify USR###### format
            if user_number and user_number.startswith('USR') and len(user_number) == 9:
                print(f"   ✅ User number generated correctly: {user_number}")
            else:
                print(f"   ❌ Invalid user number format: {user_number}")
                self.critical_issues.append("User number generation not working properly")
                all_success = False
        
        # Test /api/auth/me includes user_number
        if 'test_user' in self.tokens:
            success, me_response = self.run_test(
                "/api/auth/me Includes User Number",
                "GET",
                "/api/auth/me",
                200,
                token=self.tokens['test_user']
            )
            
            if success and me_response.get('user_number'):
                print(f"   ✅ /api/auth/me includes user_number: {me_response['user_number']}")
            else:
                print(f"   ❌ /api/auth/me missing user_number")
                self.critical_issues.append("/api/auth/me endpoint missing user_number field")
                all_success = False
        
        # Test admin user has user_number (may be N/A for existing users)
        if 'admin' in self.users:
            admin_user_number = self.users['admin'].get('user_number')
            if admin_user_number:
                print(f"   ✅ Admin user has user_number: {admin_user_number}")
            else:
                print(f"   ⚠️  Admin user missing user_number (expected for existing users)")
                self.minor_issues.append("Existing admin user missing user_number (backward compatibility)")
        
        return all_success

    def test_role_management_api(self):
        """Test 2: Role Management API Testing"""
        print("\n👑 ROLE MANAGEMENT API TESTING")
        
        all_success = True
        
        if 'admin' not in self.tokens or 'test_user' not in self.users:
            print("   ❌ Required users not available")
            return False
        
        test_user_id = self.users['test_user']['id']
        
        # Test role change from 'user' to 'warehouse_operator'
        success, role_response = self.run_test(
            "Change Role: user → warehouse_operator",
            "PUT",
            f"/api/admin/users/{test_user_id}/role",
            200,
            {"user_id": test_user_id, "new_role": "warehouse_operator"},
            self.tokens['admin']
        )
        all_success &= success
        
        if success:
            # Check response structure
            if 'user' in role_response and 'user_number' in role_response['user']:
                print(f"   ✅ Role change response includes user_number: {role_response['user']['user_number']}")
            else:
                print(f"   ❌ Role change response missing user_number")
                self.critical_issues.append("Role change API response missing user_number")
                all_success = False
            
            # Verify role was actually changed
            if role_response.get('user', {}).get('role') == 'warehouse_operator':
                print(f"   ✅ Role successfully changed to warehouse_operator")
            else:
                print(f"   ❌ Role change failed")
                self.critical_issues.append("Role change not working correctly")
                all_success = False
        
        # Test role change from 'warehouse_operator' to 'admin'
        success, role_response_2 = self.run_test(
            "Change Role: warehouse_operator → admin",
            "PUT",
            f"/api/admin/users/{test_user_id}/role",
            200,
            {"user_id": test_user_id, "new_role": "admin"},
            self.tokens['admin']
        )
        all_success &= success
        
        if success and role_response_2.get('user', {}).get('role') == 'admin':
            print(f"   ✅ Role successfully changed to admin")
        
        # Test error handling - self role change prevention
        admin_id = self.users['admin']['id']
        success, error_response = self.run_test(
            "Self Role Change Prevention (Should Fail)",
            "PUT",
            f"/api/admin/users/{admin_id}/role",
            400,  # Should be 400 "Cannot change your own role"
            {"user_id": admin_id, "new_role": "user"},
            self.tokens['admin']
        )
        
        if success and 'Cannot change your own role' in str(error_response):
            print(f"   ✅ Self role change correctly prevented")
        else:
            print(f"   ❌ Self role change prevention not working")
            self.critical_issues.append("Self role change prevention not working correctly")
            all_success = False
        
        # Test role change on non-existent user
        success, not_found_response = self.run_test(
            "Role Change on Non-existent User (Should Fail)",
            "PUT",
            "/api/admin/users/nonexistent-id/role",
            404,
            {"user_id": "nonexistent-id", "new_role": "user"},
            self.tokens['admin']
        )
        
        if success:
            print(f"   ✅ Non-existent user role change correctly returns 404")
        else:
            all_success = False
        
        return all_success

    def test_personal_dashboard_api(self):
        """Test 3: Personal Dashboard API Testing"""
        print("\n📊 PERSONAL DASHBOARD API TESTING")
        
        all_success = True
        
        # Test dashboard for test user
        if 'test_user' in self.tokens:
            success, dashboard_response = self.run_test(
                "Get Personal Dashboard (test_user)",
                "GET",
                "/api/user/dashboard",
                200,
                token=self.tokens['test_user']
            )
            all_success &= success
            
            if success:
                # Verify dashboard structure
                required_fields = ['user_info', 'cargo_requests', 'sent_cargo', 'received_cargo']
                missing_fields = [field for field in required_fields if field not in dashboard_response]
                
                if not missing_fields:
                    print(f"   ✅ Dashboard has all required fields")
                    
                    # Verify user_info includes user_number
                    user_info = dashboard_response.get('user_info', {})
                    if 'user_number' in user_info:
                        print(f"   ✅ Dashboard user_info includes user_number: {user_info['user_number']}")
                    else:
                        print(f"   ❌ Dashboard user_info missing user_number")
                        self.critical_issues.append("Dashboard user_info missing user_number field")
                        all_success = False
                    
                    # Verify arrays are present (even if empty)
                    cargo_requests = dashboard_response.get('cargo_requests', [])
                    sent_cargo = dashboard_response.get('sent_cargo', [])
                    received_cargo = dashboard_response.get('received_cargo', [])
                    
                    print(f"   📊 Dashboard data: {len(cargo_requests)} requests, {len(sent_cargo)} sent, {len(received_cargo)} received")
                    
                else:
                    print(f"   ❌ Dashboard missing required fields: {missing_fields}")
                    self.critical_issues.append(f"Dashboard missing required fields: {missing_fields}")
                    all_success = False
        
        # Test dashboard for admin user
        if 'admin' in self.tokens:
            success, admin_dashboard = self.run_test(
                "Get Personal Dashboard (admin)",
                "GET",
                "/api/user/dashboard",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success:
                admin_user_info = admin_dashboard.get('user_info', {})
                admin_user_number = admin_user_info.get('user_number')
                
                if admin_user_number and admin_user_number != 'N/A':
                    print(f"   ✅ Admin dashboard includes user_number: {admin_user_number}")
                else:
                    print(f"   ⚠️  Admin dashboard user_number is N/A (expected for existing users)")
                    self.minor_issues.append("Admin user has N/A user_number (backward compatibility)")
        
        # Test dashboard access with invalid token
        success, invalid_response = self.run_test(
            "Dashboard Access with Invalid Token (Should Fail)",
            "GET",
            "/api/user/dashboard",
            401,
            token="invalid-token"
        )
        
        if success:
            print(f"   ✅ Invalid token correctly denied dashboard access")
        else:
            all_success = False
        
        return all_success

    def test_integration_workflow(self):
        """Test 4: Integration Testing - Complete Flow"""
        print("\n🔄 INTEGRATION WORKFLOW TESTING")
        
        all_success = True
        
        if 'admin' not in self.tokens or 'test_user' not in self.users:
            print("   ❌ Required users not available")
            return False
        
        test_user_id = self.users['test_user']['id']
        test_user_token = self.tokens['test_user']
        
        # Step 1: Verify initial user state
        success, initial_dashboard = self.run_test(
            "Integration: Get Initial Dashboard",
            "GET",
            "/api/user/dashboard",
            200,
            token=test_user_token
        )
        all_success &= success
        
        if success:
            initial_role = initial_dashboard.get('user_info', {}).get('role')
            initial_user_number = initial_dashboard.get('user_info', {}).get('user_number')
            print(f"   ✅ Step 1: Initial state - Role: {initial_role}, User Number: {initial_user_number}")
        
        # Step 2: Change role
        success, role_change = self.run_test(
            "Integration: Change User Role",
            "PUT",
            f"/api/admin/users/{test_user_id}/role",
            200,
            {"user_id": test_user_id, "new_role": "warehouse_operator"},
            self.tokens['admin']
        )
        all_success &= success
        
        if success:
            new_role = role_change.get('user', {}).get('role')
            print(f"   ✅ Step 2: Role changed to {new_role}")
        
        # Step 3: Verify dashboard reflects role change
        success, updated_dashboard = self.run_test(
            "Integration: Verify Dashboard After Role Change",
            "GET",
            "/api/user/dashboard",
            200,
            token=test_user_token
        )
        all_success &= success
        
        if success:
            dashboard_role = updated_dashboard.get('user_info', {}).get('role')
            dashboard_user_number = updated_dashboard.get('user_info', {}).get('user_number')
            
            if dashboard_role == 'warehouse_operator':
                print(f"   ✅ Step 3: Dashboard shows updated role: {dashboard_role}")
            else:
                print(f"   ❌ Step 3: Dashboard role not updated: {dashboard_role}")
                self.critical_issues.append("Dashboard not reflecting role changes immediately")
                all_success = False
            
            if dashboard_user_number:
                print(f"   ✅ Step 3: Dashboard shows user_number: {dashboard_user_number}")
            else:
                print(f"   ❌ Step 3: Dashboard missing user_number")
                all_success = False
        
        return all_success

    def test_cargo_creation_for_dashboard(self):
        """Test 5: Create test cargo to verify dashboard functionality"""
        print("\n📦 CARGO CREATION FOR DASHBOARD TESTING")
        
        all_success = True
        
        if 'test_user' not in self.tokens:
            print("   ❌ Test user not available")
            return False
        
        # Create a cargo request to test dashboard cargo_requests array
        cargo_request_data = {
            "recipient_full_name": "Тест Получатель",
            "recipient_phone": "+992777888999",
            "recipient_address": "Душанбе, ул. Тестовая, 1",
            "pickup_address": "Москва, ул. Тестовая, 1",
            "cargo_name": "Тест груз для дашборда",
            "weight": 10.0,
            "declared_value": 5000.0,
            "description": "Тестовый груз для проверки дашборда",
            "route": "moscow_to_tajikistan"
        }
        
        success, cargo_request_response = self.run_test(
            "Create Cargo Request for Dashboard",
            "POST",
            "/api/user/cargo-request",
            200,
            cargo_request_data,
            self.tokens['test_user']
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Cargo request created for dashboard testing")
        
        # Verify dashboard now shows the cargo request
        success, dashboard_with_cargo = self.run_test(
            "Verify Dashboard Shows Cargo Request",
            "GET",
            "/api/user/dashboard",
            200,
            token=self.tokens['test_user']
        )
        all_success &= success
        
        if success:
            cargo_requests = dashboard_with_cargo.get('cargo_requests', [])
            if len(cargo_requests) > 0:
                print(f"   ✅ Dashboard shows {len(cargo_requests)} cargo request(s)")
                
                # Verify cargo request structure
                first_request = cargo_requests[0]
                required_fields = ['id', 'cargo_name', 'weight', 'declared_value', 'status', 'created_at']
                missing_fields = [field for field in required_fields if field not in first_request]
                
                if not missing_fields:
                    print(f"   ✅ Cargo request has all required fields")
                else:
                    print(f"   ❌ Cargo request missing fields: {missing_fields}")
                    self.minor_issues.append(f"Cargo request missing fields: {missing_fields}")
            else:
                print(f"   ❌ Dashboard not showing cargo requests")
                self.critical_issues.append("Dashboard not displaying cargo requests")
                all_success = False
        
        return all_success

    def test_data_verification(self):
        """Test 6: Data Verification Testing"""
        print("\n🔍 DATA VERIFICATION TESTING")
        
        all_success = True
        
        # Test user_number uniqueness by getting all users
        if 'admin' in self.tokens:
            success, users_list = self.run_test(
                "Get All Users for Uniqueness Check",
                "GET",
                "/api/admin/users",
                200,
                token=self.tokens['admin']
            )
            
            if success and isinstance(users_list, list):
                user_numbers = []
                for user in users_list:
                    user_number = user.get('user_number')
                    if user_number and user_number != 'N/A':
                        user_numbers.append(user_number)
                
                # Check for duplicates
                unique_numbers = set(user_numbers)
                if len(user_numbers) == len(unique_numbers):
                    print(f"   ✅ All user_numbers are unique ({len(user_numbers)} users with numbers)")
                else:
                    print(f"   ❌ Duplicate user_numbers found")
                    self.critical_issues.append("User number uniqueness violation")
                    all_success = False
            else:
                print(f"   ❌ Could not retrieve users list")
                all_success = False
        
        # Test dashboard data structure consistency
        for user_type in ['test_user', 'admin']:
            if user_type in self.tokens:
                success, dashboard = self.run_test(
                    f"Verify Dashboard Data Structure ({user_type})",
                    "GET",
                    "/api/user/dashboard",
                    200,
                    token=self.tokens[user_type]
                )
                
                if success:
                    # Check if cargo arrays have proper structure
                    sent_cargo = dashboard.get('sent_cargo', [])
                    received_cargo = dashboard.get('received_cargo', [])
                    cargo_requests = dashboard.get('cargo_requests', [])
                    
                    # Verify sorting by created_at (if data exists)
                    if len(sent_cargo) > 1:
                        dates = [item.get('created_at') for item in sent_cargo if item.get('created_at')]
                        if dates == sorted(dates, reverse=True):
                            print(f"   ✅ Sent cargo properly sorted by created_at")
                        else:
                            print(f"   ❌ Sent cargo sorting issue")
                            self.minor_issues.append("Sent cargo not properly sorted")
                    
                    print(f"   ✅ Dashboard structure verified for {user_type}")
                else:
                    all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all comprehensive tests"""
        print("🚀 STARTING COMPREHENSIVE ADMIN PANEL & DASHBOARD TESTS")
        print("=" * 70)
        
        # Setup test environment
        if not self.setup_test_environment():
            print("❌ Failed to setup test environment")
            return False
        
        test_results = []
        
        # Test 1: User Number Generation
        result1 = self.test_user_number_generation()
        test_results.append(("User Number Generation", result1))
        
        # Test 2: Role Management API
        result2 = self.test_role_management_api()
        test_results.append(("Role Management API", result2))
        
        # Test 3: Personal Dashboard API
        result3 = self.test_personal_dashboard_api()
        test_results.append(("Personal Dashboard API", result3))
        
        # Test 4: Integration Workflow
        result4 = self.test_integration_workflow()
        test_results.append(("Integration Workflow", result4))
        
        # Test 5: Cargo Creation for Dashboard
        result5 = self.test_cargo_creation_for_dashboard()
        test_results.append(("Cargo Creation for Dashboard", result5))
        
        # Test 6: Data Verification
        result6 = self.test_data_verification()
        test_results.append(("Data Verification", result6))
        
        # Print final results
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 70)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result:
                passed_tests += 1
        
        print(f"\n📈 SUMMARY: {passed_tests}/{total_tests} test suites passed")
        print(f"📈 INDIVIDUAL TESTS: {self.tests_passed}/{self.tests_run} individual tests passed")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 SUCCESS RATE: {success_rate:.1f}%")
        
        # Print issues summary
        if self.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES FOUND ({len(self.critical_issues)}):")
            for i, issue in enumerate(self.critical_issues, 1):
                print(f"   {i}. {issue}")
        
        if self.minor_issues:
            print(f"\n⚠️  MINOR ISSUES FOUND ({len(self.minor_issues)}):")
            for i, issue in enumerate(self.minor_issues, 1):
                print(f"   {i}. {issue}")
        
        if not self.critical_issues and not self.minor_issues:
            print("\n🎉 NO ISSUES FOUND - ALL FUNCTIONALITY WORKING CORRECTLY!")
        
        return len(self.critical_issues) == 0

if __name__ == "__main__":
    tester = ComprehensiveAdminTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)