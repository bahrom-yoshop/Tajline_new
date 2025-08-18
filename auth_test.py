#!/usr/bin/env python3
"""
Authentication System Testing for TAJLINE.TJ Application
Focused testing to identify login failures and authentication issues
"""

import requests
import sys
import json
from datetime import datetime
import bcrypt

class AuthenticationTester:
    def __init__(self, base_url="https://tajline-cargo-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.test_users = []
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🔐 TAJLINE.TJ Authentication System Tester")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: dict = None, token: str = None) -> tuple[bool, dict]:
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   {method} {endpoint}")
        if data:
            print(f"   📤 Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
                    print(f"   📥 Response: {json.dumps(result, indent=2)}")
                    return True, result
                except:
                    return True, {}
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   📥 Error Response: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"   📥 Raw response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"   ❌ FAILED - Exception: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test basic health check"""
        print("\n🏥 HEALTH CHECK")
        success, _ = self.run_test("Health Check", "GET", "/api/health", 200)
        return success

    def test_user_registration_comprehensive(self):
        """Test user registration with various scenarios"""
        print("\n👥 COMPREHENSIVE USER REGISTRATION TESTING")
        
        # Test users with phone numbers mentioned in the request
        test_users = [
            {
                "name": "Test User 1",
                "data": {
                    "full_name": "Иван Петров",
                    "phone": "+79123456789",
                    "password": "123456",
                    "role": "user"
                }
            },
            {
                "name": "Test User 2", 
                "data": {
                    "full_name": "Петр Иванов",
                    "phone": "+79123456790",
                    "password": "123456",
                    "role": "user"
                }
            },
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
                "name": "Warehouse Operator",
                "data": {
                    "full_name": "Оператор Складской",
                    "phone": "+79777888999", 
                    "password": "warehouse123",
                    "role": "warehouse_operator"
                }
            }
        ]
        
        all_success = True
        for user_info in test_users:
            success, response = self.run_test(
                f"Register {user_info['name']}", 
                "POST", 
                "/api/auth/register", 
                200, 
                user_info['data']
            )
            
            if success:
                self.test_users.append({
                    'name': user_info['name'],
                    'phone': user_info['data']['phone'],
                    'password': user_info['data']['password'],
                    'role': user_info['data']['role'],
                    'token': response.get('access_token'),
                    'user_data': response.get('user')
                })
                print(f"   🔑 User registered successfully: {user_info['data']['phone']}")
            else:
                # Registration might fail if user already exists - this is OK
                print(f"   ℹ️  Registration failed (user may already exist): {user_info['data']['phone']}")
                # Still add to test users for login testing
                self.test_users.append({
                    'name': user_info['name'],
                    'phone': user_info['data']['phone'],
                    'password': user_info['data']['password'],
                    'role': user_info['data']['role'],
                    'token': None,
                    'user_data': None
                })
                
        return all_success

    def test_user_login_comprehensive(self):
        """Test user login with all registered users"""
        print("\n🔐 COMPREHENSIVE USER LOGIN TESTING")
        
        if not self.test_users:
            print("   ❌ No test users available for login testing")
            return False
            
        all_success = True
        successful_logins = 0
        
        for user in self.test_users:
            print(f"\n   🔑 Testing login for: {user['name']} ({user['phone']})")
            
            login_data = {
                "phone": user['phone'],
                "password": user['password']
            }
            
            success, response = self.run_test(
                f"Login {user['name']}", 
                "POST", 
                "/api/auth/login", 
                200,
                login_data
            )
            
            if success:
                successful_logins += 1
                user['token'] = response.get('access_token')
                user['user_data'] = response.get('user')
                print(f"   ✅ Login successful for {user['phone']}")
                print(f"   👤 User role: {response.get('user', {}).get('role', 'Unknown')}")
            else:
                print(f"   ❌ Login failed for {user['phone']}")
                all_success = False
                
        print(f"\n📊 LOGIN SUMMARY: {successful_logins}/{len(self.test_users)} successful logins")
        return all_success

    def test_password_verification(self):
        """Test password hashing and verification"""
        print("\n🔒 PASSWORD HASHING AND VERIFICATION TESTING")
        
        # Test password hashing
        test_password = "123456"
        
        try:
            # Test bcrypt hashing (same as backend)
            hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            print(f"   🔐 Generated hash for '{test_password}': {hashed[:50]}...")
            
            # Test verification
            is_valid = bcrypt.checkpw(test_password.encode('utf-8'), hashed.encode('utf-8'))
            if is_valid:
                print(f"   ✅ Password verification working correctly")
            else:
                print(f"   ❌ Password verification failed")
                return False
                
            # Test wrong password
            wrong_password = "wrong123"
            is_invalid = bcrypt.checkpw(wrong_password.encode('utf-8'), hashed.encode('utf-8'))
            if not is_invalid:
                print(f"   ✅ Wrong password correctly rejected")
            else:
                print(f"   ❌ Wrong password incorrectly accepted")
                return False
                
        except Exception as e:
            print(f"   ❌ Password hashing test failed: {e}")
            return False
            
        return True

    def test_invalid_login_scenarios(self):
        """Test various invalid login scenarios"""
        print("\n⚠️  INVALID LOGIN SCENARIOS TESTING")
        
        invalid_scenarios = [
            {
                "name": "Non-existent phone",
                "data": {"phone": "+79999999999", "password": "123456"},
                "expected_status": 401
            },
            {
                "name": "Wrong password",
                "data": {"phone": "+79123456789", "password": "wrongpassword"},
                "expected_status": 401
            },
            {
                "name": "Empty phone",
                "data": {"phone": "", "password": "123456"},
                "expected_status": 422  # Validation error
            },
            {
                "name": "Empty password",
                "data": {"phone": "+79123456789", "password": ""},
                "expected_status": 422  # Validation error
            },
            {
                "name": "Missing phone field",
                "data": {"password": "123456"},
                "expected_status": 422  # Validation error
            },
            {
                "name": "Missing password field",
                "data": {"phone": "+79123456789"},
                "expected_status": 422  # Validation error
            }
        ]
        
        all_success = True
        for scenario in invalid_scenarios:
            success, _ = self.run_test(
                scenario['name'],
                "POST",
                "/api/auth/login",
                scenario['expected_status'],
                scenario['data']
            )
            all_success &= success
            
        return all_success

    def test_token_validation(self):
        """Test JWT token validation"""
        print("\n🎫 JWT TOKEN VALIDATION TESTING")
        
        # Find a user with a valid token
        valid_user = None
        for user in self.test_users:
            if user.get('token'):
                valid_user = user
                break
                
        if not valid_user:
            print("   ❌ No valid tokens available for testing")
            return False
            
        all_success = True
        
        # Test valid token
        success, response = self.run_test(
            "Valid Token Authentication",
            "GET",
            "/api/auth/me",
            200,
            token=valid_user['token']
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Valid token accepted")
            print(f"   👤 User: {response.get('full_name', 'Unknown')}")
            print(f"   📱 Phone: {response.get('phone', 'Unknown')}")
            print(f"   🎭 Role: {response.get('role', 'Unknown')}")
        
        # Test invalid token
        success, _ = self.run_test(
            "Invalid Token Authentication",
            "GET",
            "/api/auth/me",
            401,
            token="invalid_token_12345"
        )
        all_success &= success
        
        # Test no token
        success, _ = self.run_test(
            "No Token Authentication",
            "GET",
            "/api/auth/me",
            403  # FastAPI returns 403 for missing auth
        )
        all_success &= success
        
        return all_success

    def test_role_based_access(self):
        """Test role-based access control"""
        print("\n🎭 ROLE-BASED ACCESS CONTROL TESTING")
        
        # Find users with different roles
        admin_user = None
        operator_user = None
        regular_user = None
        
        for user in self.test_users:
            if user.get('token'):
                if user['role'] == 'admin':
                    admin_user = user
                elif user['role'] == 'warehouse_operator':
                    operator_user = user
                elif user['role'] == 'user':
                    regular_user = user
                    
        all_success = True
        
        # Test admin access
        if admin_user:
            success, response = self.run_test(
                "Admin Access to User List",
                "GET",
                "/api/admin/users",
                200,
                token=admin_user['token']
            )
            all_success &= success
            
            if success:
                user_count = len(response) if isinstance(response, list) else 0
                print(f"   👑 Admin can access user list ({user_count} users)")
        
        # Test regular user denied admin access
        if regular_user:
            success, _ = self.run_test(
                "Regular User Denied Admin Access",
                "GET",
                "/api/admin/users",
                403,
                token=regular_user['token']
            )
            all_success &= success
            
        # Test warehouse operator access
        if operator_user:
            success, response = self.run_test(
                "Warehouse Operator Access to Warehouse Cargo",
                "GET",
                "/api/warehouse/cargo",
                200,
                token=operator_user['token']
            )
            all_success &= success
            
            if success:
                cargo_count = len(response) if isinstance(response, list) else 0
                print(f"   🏭 Warehouse operator can access warehouse cargo ({cargo_count} items)")
        
        return all_success

    def test_database_user_existence(self):
        """Test if users exist in database by attempting login with known credentials"""
        print("\n🗄️  DATABASE USER EXISTENCE TESTING")
        
        # Test specific phone numbers mentioned in the request
        known_phones = [
            "+79123456789",
            "+79123456790", 
            "+79999888777",  # admin
            "+79777888999"   # warehouse_operator
        ]
        
        existing_users = []
        
        for phone in known_phones:
            # Try to login with common passwords
            common_passwords = ["123456", "admin123", "warehouse123", "password", "test123"]
            
            user_exists = False
            for password in common_passwords:
                login_data = {"phone": phone, "password": password}
                
                success, response = self.run_test(
                    f"Test Login {phone} with {password}",
                    "POST",
                    "/api/auth/login",
                    200,
                    login_data
                )
                
                if success:
                    existing_users.append({
                        'phone': phone,
                        'password': password,
                        'role': response.get('user', {}).get('role', 'unknown'),
                        'name': response.get('user', {}).get('full_name', 'unknown')
                    })
                    user_exists = True
                    print(f"   ✅ Found existing user: {phone} (role: {response.get('user', {}).get('role')})")
                    break
                    
            if not user_exists:
                print(f"   ❌ No valid credentials found for: {phone}")
        
        print(f"\n📊 EXISTING USERS SUMMARY:")
        if existing_users:
            for user in existing_users:
                print(f"   👤 {user['name']} ({user['phone']}) - Role: {user['role']} - Password: {user['password']}")
        else:
            print("   ⚠️  No existing users found with tested credentials")
            
        return len(existing_users) > 0

    def run_all_tests(self):
        """Run all authentication tests"""
        print("\n🚀 STARTING COMPREHENSIVE AUTHENTICATION TESTING")
        
        # Test 1: Health check
        health_ok = self.test_health_check()
        
        # Test 2: Password verification logic
        password_ok = self.test_password_verification()
        
        # Test 3: Check for existing users in database
        existing_users_found = self.test_database_user_existence()
        
        # Test 4: User registration
        registration_ok = self.test_user_registration_comprehensive()
        
        # Test 5: User login
        login_ok = self.test_user_login_comprehensive()
        
        # Test 6: Invalid login scenarios
        invalid_login_ok = self.test_invalid_login_scenarios()
        
        # Test 7: Token validation
        token_ok = self.test_token_validation()
        
        # Test 8: Role-based access
        role_access_ok = self.test_role_based_access()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 AUTHENTICATION TESTING SUMMARY")
        print("=" * 60)
        print(f"📊 Total Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print(f"\n🔍 DETAILED RESULTS:")
        print(f"   🏥 Health Check: {'✅' if health_ok else '❌'}")
        print(f"   🔒 Password Verification: {'✅' if password_ok else '❌'}")
        print(f"   🗄️  Existing Users Found: {'✅' if existing_users_found else '❌'}")
        print(f"   👥 User Registration: {'✅' if registration_ok else '❌'}")
        print(f"   🔐 User Login: {'✅' if login_ok else '❌'}")
        print(f"   ⚠️  Invalid Login Handling: {'✅' if invalid_login_ok else '❌'}")
        print(f"   🎫 Token Validation: {'✅' if token_ok else '❌'}")
        print(f"   🎭 Role-based Access: {'✅' if role_access_ok else '❌'}")
        
        # Provide working credentials
        print(f"\n🔑 WORKING TEST CREDENTIALS:")
        working_credentials = []
        for user in self.test_users:
            if user.get('token'):
                working_credentials.append(user)
                
        if working_credentials:
            for user in working_credentials:
                print(f"   📱 Phone: {user['phone']}")
                print(f"   🔐 Password: {user['password']}")
                print(f"   🎭 Role: {user['role']}")
                print(f"   👤 Name: {user.get('user_data', {}).get('full_name', 'Unknown')}")
                print()
        else:
            print("   ⚠️  No working credentials found")
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = AuthenticationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)