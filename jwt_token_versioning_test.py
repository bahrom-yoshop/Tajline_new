#!/usr/bin/env python3
"""
JWT Token Versioning System and Enhanced Admin Functionality Testing
Tests the complete enhanced admin functionality and JWT token management system for TAJLINE.TJ
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class JWTTokenVersioningTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🔐 JWT Token Versioning & Enhanced Admin Functionality Tester")
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

    def setup_test_users(self):
        """Setup test users for JWT token versioning tests"""
        print("\n👥 SETTING UP TEST USERS")
        
        # Test users as specified in requirements
        test_users = [
            {
                "name": "Admin User",
                "data": {
                    "full_name": "Админ Системы",
                    "phone": "+79999888777",
                    "password": "admin123",
                    "role": "admin"
                }
            },
            {
                "name": "Regular User",
                "data": {
                    "full_name": "Тест Пользователь",
                    "phone": "+992900000000",
                    "password": "123456",
                    "role": "user"
                }
            }
        ]
        
        all_success = True
        for user_info in test_users:
            # Try login first (user might already exist)
            success, response = self.run_test(
                f"Login {user_info['name']}", 
                "POST", 
                "/api/auth/login", 
                200,
                {"phone": user_info['data']['phone'], "password": user_info['data']['password']}
            )
            
            if success and 'access_token' in response:
                role = user_info['data']['role']
                self.tokens[role] = response['access_token']
                self.users[role] = response['user']
                print(f"   🔑 Token stored for {role} (existing user)")
            else:
                # Try registration if login failed
                success, response = self.run_test(
                    f"Register {user_info['name']}", 
                    "POST", 
                    "/api/auth/register", 
                    200, 
                    user_info['data']
                )
                
                if success and 'access_token' in response:
                    role = user_info['data']['role']
                    self.tokens[role] = response['access_token']
                    self.users[role] = response['user']
                    print(f"   🔑 Token stored for {role} (new user)")
                else:
                    all_success = False
                    
        return all_success

    def test_jwt_token_versioning_system(self):
        """Test JWT Token Versioning System - Primary Test"""
        print("\n🔐 JWT TOKEN VERSIONING SYSTEM TESTING")
        
        if 'user' not in self.tokens or 'admin' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # Test 1: User updates own profile → token version increments → old token becomes invalid
        print("\n   👤 Testing User Profile Update Token Invalidation...")
        
        # Get current user info and token version
        success, current_user = self.run_test(
            "Get Current User Info",
            "GET",
            "/api/auth/me",
            200,
            token=self.tokens['user']
        )
        all_success &= success
        
        if success:
            original_token_version = current_user.get('token_version', 1)
            original_phone = current_user.get('phone')
            print(f"   📊 Original token version: {original_token_version}")
            print(f"   📞 Original phone: {original_phone}")
            
            # Store the old token
            old_token = self.tokens['user']
            
            # Update user profile (this should increment token version)
            profile_update_data = {
                "full_name": "Тест Пользователь Обновленный",
                "email": "updated.user@test.com",
                "address": "Душанбе, ул. Обновленная, 123"
            }
            
            success, updated_profile = self.run_test(
                "Update User Profile (Should Increment Token Version)",
                "PUT",
                "/api/user/profile",
                200,
                profile_update_data,
                self.tokens['user']
            )
            all_success &= success
            
            if success:
                new_token_version = updated_profile.get('token_version', 1)
                print(f"   📊 New token version: {new_token_version}")
                
                if new_token_version > original_token_version:
                    print("   ✅ Token version incremented after profile update")
                else:
                    print("   ❌ Token version not incremented")
                    all_success = False
                
                # Test that old token becomes invalid
                print("\n   🚫 Testing Old Token Invalidation...")
                
                success, _ = self.run_test(
                    "Use Old Token (Should Fail)",
                    "GET",
                    "/api/auth/me",
                    401,  # Should be unauthorized
                    token=old_token
                )
                all_success &= success
                
                if success:
                    print("   ✅ Old token correctly invalidated after profile update")
                else:
                    print("   ❌ Old token still valid (should be invalid)")
                    all_success = False
                
                # Login again to get new token
                success, login_response = self.run_test(
                    "Login After Profile Update (Get New Token)",
                    "POST",
                    "/api/auth/login",
                    200,
                    {"phone": original_phone, "password": "123456"}
                )
                all_success &= success
                
                if success and 'access_token' in login_response:
                    self.tokens['user'] = login_response['access_token']
                    print("   🔑 New token obtained after profile update")
                    
                    # Verify new token works
                    success, new_user_info = self.run_test(
                        "Verify New Token Works",
                        "GET",
                        "/api/auth/me",
                        200,
                        token=self.tokens['user']
                    )
                    all_success &= success
                    
                    if success:
                        print("   ✅ New token works correctly")
                        print(f"   📊 Current token version: {new_user_info.get('token_version')}")
        
        # Test 2: Admin updates user profile → token version increments → user's token becomes invalid
        print("\n   👑 Testing Admin User Profile Update Token Invalidation...")
        
        # Get user ID for admin update
        success, user_info = self.run_test(
            "Get User Info Before Admin Update",
            "GET",
            "/api/auth/me",
            200,
            token=self.tokens['user']
        )
        all_success &= success
        
        if success:
            user_id = user_info.get('id')
            user_phone = user_info.get('phone')
            original_token_version = user_info.get('token_version', 1)
            print(f"   🆔 User ID: {user_id}")
            print(f"   📊 Token version before admin update: {original_token_version}")
            
            # Store current user token
            user_token_before_admin_update = self.tokens['user']
            
            # Admin updates user profile
            admin_update_data = {
                "full_name": "Пользователь Обновлен Админом",
                "email": "admin.updated@test.com",
                "address": "Душанбе, ул. Админская, 456",
                "is_active": True
            }
            
            success, admin_update_response = self.run_test(
                "Admin Updates User Profile",
                "PUT",
                f"/api/admin/users/{user_id}/update",
                200,
                admin_update_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                new_token_version = admin_update_response.get('token_version', 1)
                print(f"   📊 Token version after admin update: {new_token_version}")
                
                if new_token_version > original_token_version:
                    print("   ✅ Token version incremented after admin update")
                else:
                    print("   ❌ Token version not incremented by admin update")
                    all_success = False
                
                # Test that user's old token becomes invalid
                print("\n   🚫 Testing User Token Invalidation After Admin Update...")
                
                success, _ = self.run_test(
                    "Use User Token After Admin Update (Should Fail)",
                    "GET",
                    "/api/auth/me",
                    401,  # Should be unauthorized
                    token=user_token_before_admin_update
                )
                all_success &= success
                
                if success:
                    print("   ✅ User token correctly invalidated after admin update")
                else:
                    print("   ❌ User token still valid after admin update (should be invalid)")
                    all_success = False
                
                # User needs to login again
                success, user_relogin = self.run_test(
                    "User Re-login After Admin Update",
                    "POST",
                    "/api/auth/login",
                    200,
                    {"phone": user_phone, "password": "123456"}
                )
                all_success &= success
                
                if success and 'access_token' in user_relogin:
                    self.tokens['user'] = user_relogin['access_token']
                    print("   🔑 User obtained new token after admin update")
                    
                    # Verify new token works and has updated info
                    success, updated_user_info = self.run_test(
                        "Verify User New Token and Updated Info",
                        "GET",
                        "/api/auth/me",
                        200,
                        token=self.tokens['user']
                    )
                    all_success &= success
                    
                    if success:
                        print("   ✅ User new token works correctly")
                        print(f"   👤 Updated name: {updated_user_info.get('full_name')}")
                        print(f"   📧 Updated email: {updated_user_info.get('email')}")
                        print(f"   📊 Current token version: {updated_user_info.get('token_version')}")
        
        return all_success

    def test_enhanced_admin_user_management_api(self):
        """Test Enhanced Admin User Management API"""
        print("\n👑 ENHANCED ADMIN USER MANAGEMENT API TESTING")
        
        if 'admin' not in self.tokens or 'user' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # Test 1: Full user profile editing by admin with proper data return
        print("\n   ✏️  Testing Admin User Profile Editing...")
        
        # Get user info first
        success, user_info = self.run_test(
            "Get User Info for Admin Edit",
            "GET",
            "/api/auth/me",
            200,
            token=self.tokens['user']
        )
        all_success &= success
        
        if success:
            user_id = user_info.get('id')
            original_phone = user_info.get('phone')
            original_email = user_info.get('email')
            
            # Test full profile update by admin
            admin_edit_data = {
                "full_name": "Полностью Обновленный Пользователь",
                "phone": "+992900000001",  # Different phone
                "email": "fully.updated@admin.com",
                "address": "Душанбе, ул. Полная, 789",
                "role": "user",
                "is_active": True
            }
            
            success, edit_response = self.run_test(
                "Admin Full Profile Edit",
                "PUT",
                f"/api/admin/users/{user_id}/update",
                200,
                admin_edit_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                # Verify all fields are returned properly
                returned_fields = ['id', 'full_name', 'phone', 'email', 'address', 'role', 'is_active', 'token_version']
                missing_fields = [field for field in returned_fields if field not in edit_response]
                
                if not missing_fields:
                    print("   ✅ All required fields returned in admin edit response")
                    print(f"   👤 Updated name: {edit_response.get('full_name')}")
                    print(f"   📞 Updated phone: {edit_response.get('phone')}")
                    print(f"   📧 Updated email: {edit_response.get('email')}")
                    print(f"   🏠 Updated address: {edit_response.get('address')}")
                    print(f"   🔢 Token version: {edit_response.get('token_version')}")
                else:
                    print(f"   ❌ Missing fields in response: {missing_fields}")
                    all_success = False
                
                # Verify data was actually updated
                if (edit_response.get('full_name') == admin_edit_data['full_name'] and
                    edit_response.get('phone') == admin_edit_data['phone'] and
                    edit_response.get('email') == admin_edit_data['email'] and
                    edit_response.get('address') == admin_edit_data['address']):
                    print("   ✅ All profile data correctly updated by admin")
                else:
                    print("   ❌ Some profile data not updated correctly")
                    all_success = False
        
        # Test 2: Phone/email uniqueness validation
        print("\n   🔒 Testing Phone/Email Uniqueness Validation...")
        
        # Get admin info to test uniqueness
        success, admin_info = self.run_test(
            "Get Admin Info for Uniqueness Test",
            "GET",
            "/api/auth/me",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success and user_id:
            admin_phone = admin_info.get('phone')
            admin_email = admin_info.get('email', 'admin@test.com')
            
            # Test duplicate phone validation
            duplicate_phone_data = {
                "phone": admin_phone  # Use admin's phone
            }
            
            success, _ = self.run_test(
                "Admin Update with Duplicate Phone (Should Fail)",
                "PUT",
                f"/api/admin/users/{user_id}/update",
                400,
                duplicate_phone_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print("   ✅ Phone uniqueness validation working correctly")
            
            # Set admin email first if not set
            if not admin_email or admin_email == 'admin@test.com':
                admin_email_data = {"email": "admin.unique@test.com"}
                success, _ = self.run_test(
                    "Set Admin Email for Uniqueness Test",
                    "PUT",
                    "/api/user/profile",
                    200,
                    admin_email_data,
                    self.tokens['admin']
                )
                admin_email = "admin.unique@test.com"
            
            # Test duplicate email validation
            duplicate_email_data = {
                "email": admin_email  # Use admin's email
            }
            
            success, _ = self.run_test(
                "Admin Update with Duplicate Email (Should Fail)",
                "PUT",
                f"/api/admin/users/{user_id}/update",
                400,
                duplicate_email_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print("   ✅ Email uniqueness validation working correctly")
        
        # Test 3: Token version increments on critical changes
        print("\n   🔢 Testing Token Version Increment on Critical Changes...")
        
        if user_id:
            # Get current token version
            success, current_user = self.run_test(
                "Get Current Token Version",
                "GET",
                "/api/auth/me",
                200,
                token=self.tokens['user']
            )
            
            if success:
                original_version = current_user.get('token_version', 1)
                
                # Test phone change (critical change)
                phone_change_data = {
                    "phone": "+992900000002"
                }
                
                success, phone_response = self.run_test(
                    "Admin Changes User Phone (Critical Change)",
                    "PUT",
                    f"/api/admin/users/{user_id}/update",
                    200,
                    phone_change_data,
                    self.tokens['admin']
                )
                all_success &= success
                
                if success:
                    new_version = phone_response.get('token_version', 1)
                    if new_version > original_version:
                        print("   ✅ Token version incremented on phone change")
                    else:
                        print("   ❌ Token version not incremented on phone change")
                        all_success = False
                
                # Test role change (critical change)
                role_change_data = {
                    "role": "warehouse_operator"
                }
                
                success, role_response = self.run_test(
                    "Admin Changes User Role (Critical Change)",
                    "PUT",
                    f"/api/admin/users/{user_id}/update",
                    200,
                    role_change_data,
                    self.tokens['admin']
                )
                all_success &= success
                
                if success:
                    role_version = role_response.get('token_version', 1)
                    if role_version > new_version:
                        print("   ✅ Token version incremented on role change")
                    else:
                        print("   ❌ Token version not incremented on role change")
                        all_success = False
                
                # Test is_active change (critical change)
                active_change_data = {
                    "is_active": False
                }
                
                success, active_response = self.run_test(
                    "Admin Changes User Active Status (Critical Change)",
                    "PUT",
                    f"/api/admin/users/{user_id}/update",
                    200,
                    active_change_data,
                    self.tokens['admin']
                )
                all_success &= success
                
                if success:
                    active_version = active_response.get('token_version', 1)
                    if active_version > role_version:
                        print("   ✅ Token version incremented on active status change")
                    else:
                        print("   ❌ Token version not incremented on active status change")
                        all_success = False
        
        # Test 4: Access control - regular users denied access
        print("\n   🚫 Testing Access Control...")
        
        if user_id:
            success, _ = self.run_test(
                "Regular User Access to Admin Update (Should Fail)",
                "PUT",
                f"/api/admin/users/{user_id}/update",
                403,
                {"full_name": "Unauthorized Update"},
                self.tokens['user']
            )
            all_success &= success
            
            if success:
                print("   ✅ Regular users correctly denied access to admin user management")
        
        return all_success

    def test_user_profile_management_api(self):
        """Test User Profile Management API with token versioning"""
        print("\n👤 USER PROFILE MANAGEMENT API TESTING")
        
        if 'user' not in self.tokens:
            print("   ❌ User token not available")
            return False
            
        all_success = True
        
        # Test 1: User profile updates increment token version
        print("\n   🔢 Testing Token Version Increment on Profile Updates...")
        
        # Get current token version
        success, current_user = self.run_test(
            "Get Current User Token Version",
            "GET",
            "/api/auth/me",
            200,
            token=self.tokens['user']
        )
        all_success &= success
        
        if success:
            original_version = current_user.get('token_version', 1)
            print(f"   📊 Original token version: {original_version}")
            
            # Test profile update
            profile_data = {
                "full_name": "Пользователь Версия Токена",
                "email": "token.version@test.com",
                "address": "Душанбе, ул. Токенная, 123"
            }
            
            success, updated_profile = self.run_test(
                "Update Profile (Should Increment Token Version)",
                "PUT",
                "/api/user/profile",
                200,
                profile_data,
                self.tokens['user']
            )
            all_success &= success
            
            if success:
                new_version = updated_profile.get('token_version', 1)
                print(f"   📊 New token version: {new_version}")
                
                if new_version > original_version:
                    print("   ✅ Token version incremented on profile update")
                else:
                    print("   ❌ Token version not incremented")
                    all_success = False
                
                # Verify all fields working correctly
                if (updated_profile.get('full_name') == profile_data['full_name'] and
                    updated_profile.get('email') == profile_data['email'] and
                    updated_profile.get('address') == profile_data['address']):
                    print("   ✅ All profile fields updated correctly")
                else:
                    print("   ❌ Some profile fields not updated correctly")
                    all_success = False
        
        # Test 2: Proper User object returned with token_version
        print("\n   📄 Testing User Object Response Structure...")
        
        success, user_response = self.run_test(
            "Get User Profile Response",
            "GET",
            "/api/auth/me",
            200,
            token=self.tokens['user']
        )
        all_success &= success
        
        if success:
            required_fields = ['id', 'user_number', 'full_name', 'phone', 'role', 'email', 'address', 'is_active', 'token_version', 'created_at']
            missing_fields = [field for field in required_fields if field not in user_response]
            
            if not missing_fields:
                print("   ✅ User object contains all required fields including token_version")
                print(f"   🔢 Token version: {user_response.get('token_version')}")
                print(f"   🆔 User number: {user_response.get('user_number')}")
            else:
                print(f"   ❌ Missing fields in User object: {missing_fields}")
                all_success = False
        
        return all_success

    def test_session_management_with_versioning(self):
        """Test session management with token versioning"""
        print("\n🔐 SESSION MANAGEMENT WITH TOKEN VERSIONING TESTING")
        
        if 'user' not in self.tokens or 'admin' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # Test 1: Valid tokens work normally
        print("\n   ✅ Testing Valid Token Operations...")
        
        # Test multiple API calls with valid token
        api_calls = [
            ("Get User Info", "GET", "/api/auth/me"),
            ("Get User Notifications", "GET", "/api/notifications"),
            ("Get User Dashboard", "GET", "/api/user/dashboard")
        ]
        
        valid_token_success = 0
        for call_name, method, endpoint in api_calls:
            success, _ = self.run_test(
                call_name,
                method,
                endpoint,
                200,
                token=self.tokens['user']
            )
            if success:
                valid_token_success += 1
        
        if valid_token_success == len(api_calls):
            print(f"   ✅ All {len(api_calls)} API calls successful with valid token")
        else:
            print(f"   ❌ Only {valid_token_success}/{len(api_calls)} API calls successful")
            all_success = False
        
        # Test 2: Outdated tokens (wrong version) are rejected
        print("\n   🚫 Testing Outdated Token Rejection...")
        
        # Get current user info and token version
        success, current_user = self.run_test(
            "Get Current User for Token Test",
            "GET",
            "/api/auth/me",
            200,
            token=self.tokens['user']
        )
        
        if success:
            current_phone = current_user.get('phone')
            
            # Store current token
            current_token = self.tokens['user']
            
            # Update profile to increment token version
            success, _ = self.run_test(
                "Update Profile to Invalidate Token",
                "PUT",
                "/api/user/profile",
                200,
                {"address": "Душанбе, ул. Новая Версия, 999"},
                self.tokens['user']
            )
            
            if success:
                # Try to use old token (should fail)
                success, error_response = self.run_test(
                    "Use Outdated Token (Should Fail)",
                    "GET",
                    "/api/auth/me",
                    401,
                    token=current_token
                )
                all_success &= success
                
                if success:
                    error_detail = error_response.get('detail', '')
                    if 'Token expired due to profile changes' in error_detail:
                        print("   ✅ Outdated token rejected with clear error message")
                    else:
                        print(f"   ⚠️  Outdated token rejected but unclear error: {error_detail}")
                
                # Get new token
                success, login_response = self.run_test(
                    "Login to Get New Token",
                    "POST",
                    "/api/auth/login",
                    200,
                    {"phone": current_phone, "password": "123456"}
                )
                
                if success and 'access_token' in login_response:
                    self.tokens['user'] = login_response['access_token']
                    print("   🔑 New token obtained")
        
        # Test 3: New tokens after profile changes work correctly
        print("\n   🔄 Testing New Token After Profile Changes...")
        
        success, new_token_user = self.run_test(
            "Test New Token Works",
            "GET",
            "/api/auth/me",
            200,
            token=self.tokens['user']
        )
        all_success &= success
        
        if success:
            print("   ✅ New token works correctly after profile changes")
            print(f"   🔢 Current token version: {new_token_user.get('token_version')}")
        
        return all_success

    def test_multi_cargo_creation(self):
        """Test POST /api/operator/cargo/accept with multiple cargo items and individual pricing"""
        print("\n📦 MULTI-CARGO CREATION WITH INDIVIDUAL PRICING TESTING")
        
        if 'admin' not in self.tokens:
            print("   ❌ Admin token not available")
            return False
            
        all_success = True
        
        # Test 1: Multi-cargo with individual pricing
        print("\n   🧮 Testing Multi-Cargo with Individual Pricing...")
        
        multi_cargo_data = {
            "sender_full_name": "Тест Отправитель Мульти",
            "sender_phone": "+79999999999",
            "recipient_full_name": "Тест Получатель Мульти",
            "recipient_phone": "+992999999999",
            "recipient_address": "Душанбе, ул. Мульти, 123",
            "cargo_items": [
                {"cargo_name": "Документы", "weight": 5.0, "price_per_kg": 80.0},
                {"cargo_name": "Одежда", "weight": 15.0, "price_per_kg": 70.0},
                {"cargo_name": "Электроника", "weight": 8.0, "price_per_kg": 120.0}
            ],
            "description": "Мульти-груз с индивидуальными ценами",
            "route": "moscow_to_tajikistan"
        }
        
        success, multi_response = self.run_test(
            "Create Multi-Cargo with Individual Pricing",
            "POST",
            "/api/operator/cargo/accept",
            200,
            multi_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        if success and 'id' in multi_response:
            cargo_id = multi_response['id']
            cargo_number = multi_response.get('cargo_number', 'N/A')
            total_weight = multi_response.get('weight', 0)
            total_cost = multi_response.get('declared_value', 0)
            cargo_name = multi_response.get('cargo_name', 'N/A')
            
            print(f"   ✅ Multi-cargo created: {cargo_number}")
            print(f"   📊 Total weight: {total_weight} kg")
            print(f"   💰 Total cost: {total_cost} руб")
            print(f"   🏷️  Combined name: {cargo_name}")
            
            # Expected calculations:
            # Документы: 5.0 × 80.0 = 400 руб
            # Одежда: 15.0 × 70.0 = 1050 руб
            # Электроника: 8.0 × 120.0 = 960 руб
            # Total: 28.0 kg, 2410 руб
            expected_weight = 5.0 + 15.0 + 8.0  # 28.0 kg
            expected_cost = (5.0 * 80.0) + (15.0 * 70.0) + (8.0 * 120.0)  # 400 + 1050 + 960 = 2410 руб
            expected_name = "Документы, Одежда, Электроника"
            
            if (abs(total_weight - expected_weight) < 0.01 and 
                abs(total_cost - expected_cost) < 0.01 and 
                cargo_name == expected_name):
                print("   ✅ Multi-cargo calculations verified correctly")
            else:
                print(f"   ❌ Calculation error - Expected: {expected_weight}kg/{expected_cost}руб, Got: {total_weight}kg/{total_cost}руб")
                all_success = False
        
        # Test 2: Data persistence and validation
        print("\n   💾 Testing Data Persistence and Validation...")
        
        # Verify cargo appears in operator cargo list
        success, cargo_list = self.run_test(
            "Get Operator Cargo List",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success and 'items' in cargo_list:
            cargo_items = cargo_list['items']
            multi_cargo_found = False
            
            for cargo in cargo_items:
                if cargo.get('id') == cargo_id:
                    multi_cargo_found = True
                    print(f"   ✅ Multi-cargo found in list: {cargo.get('cargo_name')}")
                    print(f"   💰 Listed cost: {cargo.get('declared_value')} руб")
                    break
            
            if multi_cargo_found:
                print("   ✅ Multi-cargo properly persisted and appears in cargo list")
            else:
                print("   ❌ Multi-cargo not found in cargo list")
                all_success = False
        
        return all_success

    def run_comprehensive_test(self):
        """Run all comprehensive tests"""
        print("\n🚀 STARTING COMPREHENSIVE JWT TOKEN VERSIONING & ENHANCED ADMIN FUNCTIONALITY TESTS")
        print("=" * 80)
        
        # Setup
        if not self.setup_test_users():
            print("\n❌ FAILED TO SETUP TEST USERS - ABORTING")
            return False
        
        # Run all tests
        test_results = []
        
        test_results.append(("JWT Token Versioning System", self.test_jwt_token_versioning_system()))
        test_results.append(("Enhanced Admin User Management API", self.test_enhanced_admin_user_management_api()))
        test_results.append(("User Profile Management API", self.test_user_profile_management_api()))
        test_results.append(("Session Management with Versioning", self.test_session_management_with_versioning()))
        test_results.append(("Multi-Cargo Creation", self.test_multi_cargo_creation()))
        
        # Print results
        print("\n" + "=" * 80)
        print("🏁 COMPREHENSIVE TEST RESULTS")
        print("=" * 80)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result:
                passed_tests += 1
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Individual Test Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        print(f"   Test Suites Passed: {passed_tests}/{total_tests}")
        print(f"   Test Suite Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! JWT Token Versioning & Enhanced Admin Functionality is working correctly!")
            return True
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test suite(s) failed. Please review the issues above.")
            return False

if __name__ == "__main__":
    tester = JWTTokenVersioningTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1)