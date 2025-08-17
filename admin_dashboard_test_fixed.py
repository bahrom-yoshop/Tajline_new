#!/usr/bin/env python3
"""
Admin Panel Enhancements and Personal Dashboard Testing - FIXED VERSION
Tests user number generation, role management API, and personal dashboard functionality
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class AdminDashboardTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        print(f"🎯 ADMIN PANEL ENHANCEMENTS & PERSONAL DASHBOARD TESTER - FIXED")
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
                    if isinstance(result, dict) and len(str(result)) < 300:
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

    def test_user_number_generation(self):
        """Test 1: User Number Display Testing"""
        print("\n🔢 USER NUMBER GENERATION TESTING")
        
        all_success = True
        
        # Test user registration with user number generation
        test_user_data = {
            "full_name": "Тест Админ Панель",
            "phone": "+79777666555",
            "password": "test123",
            "role": "user"
        }
        
        success, response = self.run_test(
            "Register User with Number Generation",
            "POST",
            "/api/auth/register",
            200,
            test_user_data
        )
        all_success &= success
        
        if success and 'user' in response:
            user_data = response['user']
            user_number = user_data.get('user_number')
            
            # Verify USR###### format
            if user_number and user_number.startswith('USR') and len(user_number) == 9:
                print(f"   ✅ User number generated correctly: {user_number}")
                self.tokens['test_user'] = response['access_token']
                self.users['test_user'] = user_data
            else:
                print(f"   ❌ Invalid user number format: {user_number}")
                all_success = False
        
        # Test login includes user_number
        if 'test_user' in self.tokens:
            success, login_response = self.run_test(
                "Login Response Includes User Number",
                "POST",
                "/api/auth/login",
                200,
                {"phone": test_user_data['phone'], "password": test_user_data['password']}
            )
            all_success &= success
            
            if success and 'user' in login_response:
                login_user = login_response['user']
                if login_user.get('user_number') == self.users['test_user']['user_number']:
                    print(f"   ✅ Login response includes correct user_number")
                else:
                    print(f"   ❌ Login user_number mismatch")
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
            all_success &= success
            
            if success and me_response.get('user_number'):
                print(f"   ✅ /api/auth/me includes user_number: {me_response['user_number']}")
            else:
                print(f"   ❌ /api/auth/me missing user_number")
                all_success = False
        
        return all_success

    def test_role_management_api(self):
        """Test 2: Role Management API Testing"""
        print("\n👑 ROLE MANAGEMENT API TESTING")
        
        all_success = True
        
        # Try to login with existing admin user first
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
            print(f"   🔑 Admin token stored for existing user")
        else:
            # If login fails, try to create new admin
            admin_data = {
                "full_name": "Админ Тестер Новый",
                "phone": "+79999888778",
                "password": "admin123",
                "role": "admin"
            }
            
            success, admin_reg_response = self.run_test(
                "Register New Admin User",
                "POST",
                "/api/auth/register",
                200,
                admin_data
            )
            all_success &= success
            
            if success and 'access_token' in admin_reg_response:
                self.tokens['admin'] = admin_reg_response['access_token']
                self.users['admin'] = admin_reg_response['user']
                print(f"   🔑 New admin token stored")

        # Create a regular user to test role changes on (if not already created)
        if 'test_user' not in self.users:
            test_user_data = {
                "full_name": "Тест Пользователь Роль",
                "phone": "+79777666556",
                "password": "test123",
                "role": "user"
            }
            
            success, user_response = self.run_test(
                "Register Test User for Role Change",
                "POST",
                "/api/auth/register",
                200,
                test_user_data
            )
            all_success &= success
            
            if success:
                self.tokens['test_user'] = user_response['access_token']
                self.users['test_user'] = user_response['user']

        if 'admin' in self.tokens and 'test_user' in self.users:
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
                # Verify response includes user_number
                if 'user_number' in role_response:
                    print(f"   ✅ Role change response includes user_number: {role_response['user_number']}")
                else:
                    print(f"   ❌ Role change response missing user_number")
                    all_success = False
                
                # Verify role was actually changed
                if role_response.get('role') == 'warehouse_operator':
                    print(f"   ✅ Role successfully changed to warehouse_operator")
                else:
                    print(f"   ❌ Role change failed, got: {role_response.get('role')}")
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
            
            if success and role_response_2.get('role') == 'admin':
                print(f"   ✅ Role successfully changed to admin")
            
            # Test error handling - non-admin user trying to change roles
            success, error_response = self.run_test(
                "Non-admin Role Change (Should Fail)",
                "PUT",
                f"/api/admin/users/{test_user_id}/role",
                403,  # Should be forbidden
                {"user_id": test_user_id, "new_role": "user"},
                self.tokens['test_user']
            )
            all_success &= success
            
            if success:
                print(f"   ✅ Non-admin users correctly denied role change access")
            
            # Test role change on non-existent user
            success, not_found_response = self.run_test(
                "Role Change on Non-existent User (Should Fail)",
                "PUT",
                "/api/admin/users/nonexistent-id/role",
                404,
                {"user_id": "nonexistent-id", "new_role": "user"},
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print(f"   ✅ Non-existent user role change correctly returns 404")
        
        return all_success

    def test_personal_dashboard_api(self):
        """Test 3: Personal Dashboard API Testing"""
        print("\n📊 PERSONAL DASHBOARD API TESTING")
        
        all_success = True
        
        # Test dashboard for different user types
        user_types = ['test_user', 'admin']
        
        for user_type in user_types:
            if user_type in self.tokens:
                success, dashboard_response = self.run_test(
                    f"Get Personal Dashboard ({user_type})",
                    "GET",
                    "/api/user/dashboard",
                    200,
                    token=self.tokens[user_type]
                )
                all_success &= success
                
                if success:
                    # Verify dashboard structure
                    required_fields = ['user_info', 'cargo_requests', 'sent_cargo', 'received_cargo']
                    missing_fields = [field for field in required_fields if field not in dashboard_response]
                    
                    if not missing_fields:
                        print(f"   ✅ Dashboard has all required fields for {user_type}")
                        
                        # Verify user_info includes user_number
                        user_info = dashboard_response.get('user_info', {})
                        if 'user_number' in user_info:
                            print(f"   ✅ Dashboard user_info includes user_number: {user_info['user_number']}")
                        else:
                            print(f"   ❌ Dashboard user_info missing user_number")
                            all_success = False
                        
                        # Verify arrays are present (even if empty)
                        cargo_requests = dashboard_response.get('cargo_requests', [])
                        sent_cargo = dashboard_response.get('sent_cargo', [])
                        received_cargo = dashboard_response.get('received_cargo', [])
                        
                        print(f"   📊 Dashboard data: {len(cargo_requests)} requests, {len(sent_cargo)} sent, {len(received_cargo)} received")
                        
                    else:
                        print(f"   ❌ Dashboard missing required fields: {missing_fields}")
                        all_success = False
        
        # Test dashboard access with invalid token
        success, invalid_response = self.run_test(
            "Dashboard Access with Invalid Token (Should Fail)",
            "GET",
            "/api/user/dashboard",
            401,
            token="invalid-token"
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Invalid token correctly denied dashboard access")
        
        return all_success

    def test_integration_workflow(self):
        """Test 4: Integration Testing - Complete Flow"""
        print("\n🔄 INTEGRATION WORKFLOW TESTING")
        
        all_success = True
        
        # Complete flow: register user → change role → access dashboard
        
        # Step 1: Register new user
        integration_user_data = {
            "full_name": "Интеграция Тест",
            "phone": "+79777666557",
            "password": "integration123",
            "role": "user"
        }
        
        success, reg_response = self.run_test(
            "Integration: Register New User",
            "POST",
            "/api/auth/register",
            200,
            integration_user_data
        )
        all_success &= success
        
        integration_user_id = None
        integration_token = None
        
        if success and 'user' in reg_response:
            integration_user_id = reg_response['user']['id']
            integration_token = reg_response['access_token']
            user_number = reg_response['user']['user_number']
            
            print(f"   ✅ Step 1: User registered with number {user_number}")
        
        # Step 2: Change role (admin required)
        if integration_user_id and 'admin' in self.tokens:
            success, role_response = self.run_test(
                "Integration: Change User Role",
                "PUT",
                f"/api/admin/users/{integration_user_id}/role",
                200,
                {"user_id": integration_user_id, "new_role": "warehouse_operator"},
                self.tokens['admin']
            )
            all_success &= success
            
            if success and role_response.get('role') == 'warehouse_operator':
                print(f"   ✅ Step 2: Role changed to warehouse_operator")
        
        # Step 3: Access dashboard with new role
        if integration_token:
            success, dashboard_response = self.run_test(
                "Integration: Access Dashboard with New Role",
                "GET",
                "/api/user/dashboard",
                200,
                token=integration_token
            )
            all_success &= success
            
            if success:
                user_info = dashboard_response.get('user_info', {})
                dashboard_role = user_info.get('role')
                dashboard_user_number = user_info.get('user_number')
                
                if dashboard_role == 'warehouse_operator':
                    print(f"   ✅ Step 3: Dashboard shows updated role: {dashboard_role}")
                else:
                    print(f"   ❌ Step 3: Dashboard role mismatch: {dashboard_role}")
                    all_success = False
                
                if dashboard_user_number:
                    print(f"   ✅ Step 3: Dashboard shows user_number: {dashboard_user_number}")
                else:
                    print(f"   ❌ Step 3: Dashboard missing user_number")
                    all_success = False
        
        # Step 4: Verify data consistency across collections
        if 'admin' in self.tokens:
            success, users_list = self.run_test(
                "Integration: Verify User in Admin List",
                "GET",
                "/api/admin/users",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success and isinstance(users_list, list):
                integration_user = next((u for u in users_list if u.get('id') == integration_user_id), None)
                
                if integration_user:
                    if integration_user.get('role') == 'warehouse_operator':
                        print(f"   ✅ Step 4: User role consistent in admin list")
                    else:
                        print(f"   ❌ Step 4: Role inconsistency in admin list")
                        all_success = False
                    
                    if 'user_number' in integration_user:
                        print(f"   ✅ Step 4: User number appears in admin list")
                    else:
                        print(f"   ❌ Step 4: User number missing from admin list")
                        all_success = False
                else:
                    print(f"   ❌ Step 4: User not found in admin list")
                    all_success = False
        
        return all_success

    def test_error_handling(self):
        """Test 5: Error Handling Testing"""
        print("\n⚠️  ERROR HANDLING TESTING")
        
        all_success = True
        
        # Test role change with non-admin user
        if 'test_user' in self.tokens and 'admin' in self.users:
            admin_id = self.users['admin']['id']
            
            success, error_response = self.run_test(
                "Non-admin Role Change Attempt",
                "PUT",
                f"/api/admin/users/{admin_id}/role",
                403,
                {"user_id": admin_id, "new_role": "user"},
                self.tokens['test_user']
            )
            all_success &= success
        
        # Test dashboard access without token
        success, no_auth_response = self.run_test(
            "Dashboard Access Without Token",
            "GET",
            "/api/user/dashboard",
            403  # Should be forbidden without auth
        )
        all_success &= success
        
        # Test role change on non-existent user
        if 'admin' in self.tokens:
            success, not_found_response = self.run_test(
                "Role Change Non-existent User",
                "PUT",
                "/api/admin/users/fake-user-id/role",
                404,
                {"user_id": "fake-user-id", "new_role": "user"},
                self.tokens['admin']
            )
            all_success &= success
        
        return all_success

    def test_data_verification(self):
        """Test 6: Data Verification Testing"""
        print("\n🔍 DATA VERIFICATION TESTING")
        
        all_success = True
        
        # Test user_number uniqueness
        user_numbers = set()
        
        if 'admin' in self.tokens:
            success, users_list = self.run_test(
                "Get All Users for Uniqueness Check",
                "GET",
                "/api/admin/users",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success and isinstance(users_list, list):
                for user in users_list:
                    user_number = user.get('user_number')
                    if user_number:
                        if user_number in user_numbers:
                            print(f"   ❌ Duplicate user_number found: {user_number}")
                            all_success = False
                        else:
                            user_numbers.add(user_number)
                
                if len(user_numbers) == len([u for u in users_list if u.get('user_number')]):
                    print(f"   ✅ All user_numbers are unique ({len(user_numbers)} users)")
                else:
                    print(f"   ❌ User_number uniqueness violation detected")
                    all_success = False
        
        # Test cargo history includes all relevant fields (if any cargo exists)
        for user_type in ['test_user', 'admin']:
            if user_type in self.tokens:
                success, dashboard = self.run_test(
                    f"Verify Dashboard Data Structure ({user_type})",
                    "GET",
                    "/api/user/dashboard",
                    200,
                    token=self.tokens[user_type]
                )
                all_success &= success
                
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
                            all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all admin panel and dashboard tests"""
        print("🚀 STARTING ADMIN PANEL ENHANCEMENTS & PERSONAL DASHBOARD TESTS")
        print("=" * 70)
        
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
        
        # Test 5: Error Handling
        result5 = self.test_error_handling()
        test_results.append(("Error Handling", result5))
        
        # Test 6: Data Verification
        result6 = self.test_data_verification()
        test_results.append(("Data Verification", result6))
        
        # Print final results
        print("\n" + "=" * 70)
        print("📊 FINAL TEST RESULTS")
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
        
        if passed_tests == total_tests:
            print("\n🎉 ALL ADMIN PANEL & DASHBOARD TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  {total_tests - passed_tests} TEST SUITE(S) FAILED")
            return False

if __name__ == "__main__":
    tester = AdminDashboardTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)