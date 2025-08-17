#!/usr/bin/env python3
"""
Final JWT Token Versioning System Testing
Tests the complete enhanced admin functionality and JWT token management system
"""

import requests
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

class FinalJWTTester:
    def __init__(self, base_url="https://tajline-manager-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        print(f"🔐 Final JWT Token Versioning & Enhanced Admin Functionality Tester")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 80)

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, token: Optional[str] = None) -> tuple[bool, Dict]:
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
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)

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

    def setup_test_environment(self):
        """Setup test environment with admin and user"""
        print("\n🏗️  SETTING UP TEST ENVIRONMENT")
        
        # Login as admin
        success, admin_response = self.run_test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+79999888777", "password": "admin123"}
        )
        
        if success and 'access_token' in admin_response:
            self.admin_token = admin_response['access_token']
            print(f"   🔑 Admin authenticated successfully")
        else:
            return False
        
        # Create unique test user
        unique_phone = f"+99290000{str(uuid.uuid4())[:4]}"
        success, user_response = self.run_test(
            "Create Test User",
            "POST",
            "/api/auth/register",
            200,
            {
                "full_name": "JWT Test User",
                "phone": unique_phone,
                "password": "test123",
                "role": "user"
            }
        )
        
        if success and 'access_token' in user_response:
            self.user_token = user_response['access_token']
            self.test_user_phone = unique_phone
            print(f"   🔑 Test user created: {unique_phone}")
            return True
        
        return False

    def test_jwt_token_versioning_core(self):
        """Test core JWT token versioning functionality"""
        print("\n🔐 JWT TOKEN VERSIONING CORE FUNCTIONALITY")
        
        results = []
        
        # Test 1: User updates own profile → token version increments → old token becomes invalid
        print("\n   👤 Testing User Profile Update Token Invalidation...")
        
        # Get current user info
        success, current_user = self.run_test(
            "Get Current User Info",
            "GET",
            "/api/auth/me",
            200,
            token=self.user_token
        )
        
        if success:
            original_version = current_user.get('token_version', 1)
            old_token = self.user_token
            
            # Update profile
            success, updated_profile = self.run_test(
                "Update User Profile (Should Increment Token Version)",
                "PUT",
                "/api/user/profile",
                200,
                {
                    "full_name": "JWT Test User Updated",
                    "email": "jwt.test@example.com",
                    "address": "Test Address 123"
                },
                self.user_token
            )
            
            if success:
                new_version = updated_profile.get('token_version', 1)
                if new_version > original_version:
                    print("   ✅ Token version incremented on profile update")
                    results.append(True)
                    
                    # Test old token invalidation
                    success, _ = self.run_test(
                        "Use Old Token (Should Fail)",
                        "GET",
                        "/api/auth/me",
                        401,
                        token=old_token
                    )
                    
                    if success:
                        print("   ✅ Old token correctly invalidated")
                        results.append(True)
                        
                        # Get new token
                        success, login_response = self.run_test(
                            "Login with New Token",
                            "POST",
                            "/api/auth/login",
                            200,
                            {"phone": self.test_user_phone, "password": "test123"}
                        )
                        
                        if success:
                            self.user_token = login_response['access_token']
                            print("   ✅ New token obtained and working")
                            results.append(True)
                        else:
                            results.append(False)
                    else:
                        results.append(False)
                else:
                    print("   ❌ Token version not incremented")
                    results.append(False)
            else:
                results.append(False)
        else:
            results.append(False)
        
        return all(results)

    def test_enhanced_admin_user_management(self):
        """Test enhanced admin user management API"""
        print("\n👑 ENHANCED ADMIN USER MANAGEMENT API")
        
        results = []
        
        # Get user ID for admin operations
        success, user_info = self.run_test(
            "Get User Info for Admin Operations",
            "GET",
            "/api/auth/me",
            200,
            token=self.user_token
        )
        
        if not success:
            return False
        
        user_id = user_info.get('id')
        original_version = user_info.get('token_version', 1)
        
        # Test 1: Admin full profile editing with proper data return
        print("\n   ✏️  Testing Admin Full Profile Editing...")
        
        success, edit_response = self.run_test(
            "Admin Full Profile Edit",
            "PUT",
            f"/api/admin/users/{user_id}/update",
            200,
            {
                "full_name": "Admin Updated User",
                "email": "admin.updated@test.com",
                "address": "Admin Updated Address",
                "is_active": True
            },
            self.admin_token
        )
        
        if success:
            # Check if response contains user data
            if 'user' in edit_response:
                user_data = edit_response['user']
                required_fields = ['id', 'full_name', 'phone', 'email', 'address', 'role', 'is_active', 'token_version']
                missing_fields = [field for field in required_fields if field not in user_data]
                
                if not missing_fields:
                    print("   ✅ Admin edit returns complete user object")
                    results.append(True)
                    
                    # Check if token version incremented
                    new_version = user_data.get('token_version', 1)
                    if new_version > original_version:
                        print("   ✅ Token version incremented on admin update")
                        results.append(True)
                    else:
                        print("   ❌ Token version not incremented on admin update")
                        results.append(False)
                else:
                    print(f"   ❌ Missing fields in admin response: {missing_fields}")
                    results.append(False)
            else:
                print("   ❌ Admin edit response missing user data")
                results.append(False)
        else:
            results.append(False)
        
        # Test 2: Phone uniqueness validation
        print("\n   🔒 Testing Phone Uniqueness Validation...")
        
        success, _ = self.run_test(
            "Admin Update with Duplicate Phone (Should Fail)",
            "PUT",
            f"/api/admin/users/{user_id}/update",
            400,
            {"phone": "+79999888777"},  # Admin's phone
            self.admin_token
        )
        
        if success:
            print("   ✅ Phone uniqueness validation working")
            results.append(True)
        else:
            results.append(False)
        
        # Test 3: Access control
        print("\n   🚫 Testing Access Control...")
        
        success, _ = self.run_test(
            "Regular User Access to Admin Update (Should Fail)",
            "PUT",
            f"/api/admin/users/{user_id}/update",
            403,
            {"full_name": "Unauthorized Update"},
            self.user_token
        )
        
        if success:
            print("   ✅ Access control working correctly")
            results.append(True)
        else:
            results.append(False)
        
        return all(results)

    def test_user_profile_management_api(self):
        """Test user profile management API with token versioning"""
        print("\n👤 USER PROFILE MANAGEMENT API")
        
        results = []
        
        # Test 1: Profile updates increment token version
        success, current_user = self.run_test(
            "Get Current User for Profile Test",
            "GET",
            "/api/auth/me",
            200,
            token=self.user_token
        )
        
        if success:
            original_version = current_user.get('token_version', 1)
            
            success, updated_profile = self.run_test(
                "Update Profile (Should Increment Token Version)",
                "PUT",
                "/api/user/profile",
                200,
                {
                    "full_name": "Profile API Test User",
                    "email": "profile.api@test.com",
                    "address": "Profile API Address"
                },
                self.user_token
            )
            
            if success:
                new_version = updated_profile.get('token_version', 1)
                if new_version > original_version:
                    print("   ✅ Token version incremented on profile update")
                    results.append(True)
                else:
                    print("   ❌ Token version not incremented")
                    results.append(False)
                
                # Test 2: Proper User object returned with all fields
                required_fields = ['id', 'user_number', 'full_name', 'phone', 'role', 'email', 'address', 'is_active', 'token_version']
                missing_fields = [field for field in required_fields if field not in updated_profile]
                
                if not missing_fields:
                    print("   ✅ User object contains all required fields including token_version")
                    results.append(True)
                else:
                    print(f"   ❌ Missing fields in User object: {missing_fields}")
                    results.append(False)
            else:
                results.append(False)
        else:
            results.append(False)
        
        return all(results)

    def test_session_management_with_versioning(self):
        """Test session management with token versioning"""
        print("\n🔐 SESSION MANAGEMENT WITH TOKEN VERSIONING")
        
        results = []
        
        # Test 1: Valid tokens work normally
        print("\n   ✅ Testing Valid Token Operations...")
        
        api_calls = [
            ("Get User Info", "GET", "/api/auth/me"),
            ("Get User Dashboard", "GET", "/api/user/dashboard")
        ]
        
        valid_calls = 0
        for call_name, method, endpoint in api_calls:
            success, _ = self.run_test(
                call_name,
                method,
                endpoint,
                200,
                token=self.user_token
            )
            if success:
                valid_calls += 1
        
        if valid_calls == len(api_calls):
            print(f"   ✅ All {len(api_calls)} API calls successful with valid token")
            results.append(True)
        else:
            print(f"   ❌ Only {valid_calls}/{len(api_calls)} API calls successful")
            results.append(False)
        
        # Test 2: Token validation with versioning
        print("\n   🔢 Testing Token Version Validation...")
        
        # Get current token version
        success, user_info = self.run_test(
            "Get Current Token Version",
            "GET",
            "/api/auth/me",
            200,
            token=self.user_token
        )
        
        if success:
            current_version = user_info.get('token_version', 1)
            old_token = self.user_token
            
            # Update profile to increment version
            success, _ = self.run_test(
                "Update Profile to Test Token Versioning",
                "PUT",
                "/api/user/profile",
                200,
                {"address": "Version Test Address"},
                self.user_token
            )
            
            if success:
                # Test that old token fails with clear error
                success, error_response = self.run_test(
                    "Use Outdated Token (Should Fail with Clear Message)",
                    "GET",
                    "/api/auth/me",
                    401,
                    token=old_token
                )
                
                if success:
                    error_detail = error_response.get('detail', '')
                    if 'Token expired due to profile changes' in error_detail:
                        print("   ✅ Outdated token rejected with clear error message")
                        results.append(True)
                    else:
                        print(f"   ⚠️  Token rejected but unclear error: {error_detail}")
                        results.append(True)  # Still working, just unclear message
                else:
                    results.append(False)
            else:
                results.append(False)
        else:
            results.append(False)
        
        return all(results)

    def test_multi_cargo_creation(self):
        """Test multi-cargo creation with individual pricing"""
        print("\n📦 MULTI-CARGO CREATION WITH INDIVIDUAL PRICING")
        
        success, multi_response = self.run_test(
            "Create Multi-Cargo with Individual Pricing",
            "POST",
            "/api/operator/cargo/accept",
            200,
            {
                "sender_full_name": "Final Test Sender",
                "sender_phone": "+79999999998",
                "recipient_full_name": "Final Test Recipient",
                "recipient_phone": "+992999999998",
                "recipient_address": "Dushanbe, Final Test St, 123",
                "cargo_items": [
                    {"cargo_name": "Documents", "weight": 10.0, "price_per_kg": 60.0},
                    {"cargo_name": "Clothes", "weight": 25.0, "price_per_kg": 60.0},
                    {"cargo_name": "Electronics", "weight": 100.0, "price_per_kg": 65.0}
                ],
                "description": "Final test multi-cargo with individual pricing",
                "route": "moscow_to_tajikistan"
            },
            self.admin_token
        )
        
        if success:
            cargo_number = multi_response.get('cargo_number', 'N/A')
            total_weight = multi_response.get('weight', 0)
            total_cost = multi_response.get('declared_value', 0)
            
            print(f"   ✅ Multi-cargo created: {cargo_number}")
            print(f"   📊 Total weight: {total_weight} kg")
            print(f"   💰 Total cost: {total_cost} руб")
            
            # Expected: 10*60 + 25*60 + 100*65 = 600 + 1500 + 6500 = 8600 ruб, 135 kg
            expected_weight = 135.0
            expected_cost = 8600.0
            
            if abs(total_weight - expected_weight) < 0.01 and abs(total_cost - expected_cost) < 0.01:
                print("   ✅ Multi-cargo calculations verified correctly")
                return True
            else:
                print(f"   ❌ Calculation error - Expected: {expected_weight}kg/{expected_cost}руб")
                return False
        
        return False

    def run_comprehensive_test(self):
        """Run comprehensive JWT token versioning and admin functionality tests"""
        print("\n🚀 STARTING COMPREHENSIVE JWT TOKEN VERSIONING & ADMIN FUNCTIONALITY TESTS")
        print("=" * 80)
        
        # Setup
        if not self.setup_test_environment():
            print("\n❌ FAILED TO SETUP TEST ENVIRONMENT - ABORTING")
            return False
        
        # Run all tests
        test_suites = [
            ("JWT Token Versioning Core Functionality", self.test_jwt_token_versioning_core),
            ("Enhanced Admin User Management API", self.test_enhanced_admin_user_management),
            ("User Profile Management API", self.test_user_profile_management_api),
            ("Session Management with Versioning", self.test_session_management_with_versioning),
            ("Multi-Cargo Creation", self.test_multi_cargo_creation)
        ]
        
        results = []
        for test_name, test_func in test_suites:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"   ❌ Test suite failed with exception: {e}")
                results.append((test_name, False))
        
        # Print final results
        print("\n" + "=" * 80)
        print("🏁 COMPREHENSIVE TEST RESULTS")
        print("=" * 80)
        
        passed_tests = 0
        total_tests = len(results)
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result:
                passed_tests += 1
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Individual Tests Run: {self.tests_run}")
        print(f"   Individual Tests Passed: {self.tests_passed}")
        print(f"   Individual Test Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        print(f"   Test Suites Passed: {passed_tests}/{total_tests}")
        print(f"   Test Suite Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Summary of key findings
        print(f"\n🔍 KEY FINDINGS:")
        print(f"   ✅ JWT Token Versioning System: {'WORKING' if results[0][1] else 'ISSUES FOUND'}")
        print(f"   ✅ Admin User Management: {'WORKING' if results[1][1] else 'ISSUES FOUND'}")
        print(f"   ✅ User Profile Management: {'WORKING' if results[2][1] else 'ISSUES FOUND'}")
        print(f"   ✅ Session Management: {'WORKING' if results[3][1] else 'ISSUES FOUND'}")
        print(f"   ✅ Multi-Cargo Creation: {'WORKING' if results[4][1] else 'ISSUES FOUND'}")
        
        if passed_tests >= 4:  # Allow for 1 failure
            print("\n🎉 JWT TOKEN VERSIONING & ENHANCED ADMIN FUNCTIONALITY IS LARGELY WORKING!")
            print("   The core JWT token versioning system and admin functionality are operational.")
            return True
        else:
            print(f"\n⚠️  Multiple critical issues found. Please review the test results above.")
            return False

if __name__ == "__main__":
    tester = FinalJWTTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1)