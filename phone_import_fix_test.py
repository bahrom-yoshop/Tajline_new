#!/usr/bin/env python3
"""
Backend Stability Test After Phone Import Fix in TAJLINE.TJ
Tests backend stability after fixing frontend Phone import error
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class PhoneImportFixTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"📱 TAJLINE.TJ Backend Stability Test After Phone Import Fix")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 70)

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

    def test_basic_connectivity(self):
        """Test basic API connectivity and health check"""
        print("\n🌐 BASIC CONNECTIVITY TEST")
        print("   🎯 Проверить доступность API и основных endpoints")
        
        all_success = True
        
        # Test 1: Health Check
        print("\n   ❤️ Test 1: API Health Check...")
        
        success, health_response = self.run_test(
            "API Health Check",
            "GET",
            "/api/health",
            200
        )
        all_success &= success
        
        if success:
            print("   ✅ API is healthy and accessible")
            if health_response.get('status') == 'ok':
                print("   ✅ Health status: OK")
            else:
                print(f"   ⚠️ Health status: {health_response.get('status', 'Unknown')}")
        else:
            print("   ❌ API health check failed")
            return False
        
        # Test 2: Basic endpoints without authentication
        print("\n   🔗 Test 2: Basic Endpoints Accessibility...")
        
        basic_endpoints = [
            ("/api/health", "Health Check"),
        ]
        
        for endpoint, description in basic_endpoints:
            success, response = self.run_test(
                f"Basic Endpoint: {description}",
                "GET",
                endpoint,
                200
            )
            all_success &= success
            
            if success:
                print(f"   ✅ {description} accessible")
            else:
                print(f"   ❌ {description} not accessible")
        
        return all_success

    def test_courier_login(self):
        """Test courier authentication (+79991234567/courier123)"""
        print("\n🚚 COURIER LOGIN TEST")
        print("   🎯 Быстро проверить авторизацию курьера (+79991234567/courier123)")
        
        all_success = True
        
        # Test: Courier Login
        print("\n   🔐 Test: Courier Authentication...")
        
        courier_login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        success, login_response = self.run_test(
            "Courier Login (+79991234567/courier123)",
            "POST",
            "/api/auth/login",
            200,
            courier_login_data
        )
        all_success &= success
        
        courier_token = None
        if success and 'access_token' in login_response:
            courier_token = login_response['access_token']
            courier_user = login_response.get('user', {})
            courier_role = courier_user.get('role')
            courier_name = courier_user.get('full_name')
            courier_phone = courier_user.get('phone')
            courier_user_number = courier_user.get('user_number')
            
            print(f"   ✅ Courier login successful!")
            print(f"   👤 Name: {courier_name}")
            print(f"   📞 Phone: {courier_phone}")
            print(f"   👑 Role: {courier_role}")
            print(f"   🆔 User Number: {courier_user_number}")
            print(f"   🔑 JWT Token received: {courier_token[:50]}...")
            
            # Verify role is courier
            if courier_role == 'courier':
                print("   ✅ Courier role correctly set to 'courier'")
            else:
                print(f"   ❌ Courier role incorrect: expected 'courier', got '{courier_role}'")
                all_success = False
            
            # Store courier token for further tests
            self.tokens['courier'] = courier_token
            
            # Test basic courier endpoint to verify functionality
            print("\n   📋 Testing basic courier endpoint...")
            
            success, requests_response = self.run_test(
                "Get Courier Requests",
                "GET",
                "/api/courier/requests/new",
                200,
                token=courier_token
            )
            
            if success:
                print("   ✅ Courier endpoints accessible after login")
                if isinstance(requests_response, dict):
                    total_count = requests_response.get('total_count', 0)
                    print(f"   📊 New requests: {total_count}")
                elif isinstance(requests_response, list):
                    print(f"   📊 New requests: {len(requests_response)}")
            else:
                print("   ❌ Courier endpoints not accessible")
                all_success = False
                
        else:
            print("   ❌ Courier login failed - no access token received")
            print(f"   📄 Response: {login_response}")
            all_success = False
        
        return all_success

    def test_import_fix_verification(self):
        """Test that frontend Phone import fix didn't affect backend functionality"""
        print("\n🔧 IMPORT FIX VERIFICATION TEST")
        print("   🎯 Убедиться что исправление frontend импорта Phone не повлияло на backend функциональность")
        
        all_success = True
        
        # Test 1: Backend services are running
        print("\n   🖥️ Test 1: Backend Services Status...")
        
        success, health_response = self.run_test(
            "Backend Services Health",
            "GET",
            "/api/health",
            200
        )
        all_success &= success
        
        if success:
            print("   ✅ Backend services running normally")
        else:
            print("   ❌ Backend services may have issues")
            return False
        
        # Test 2: Authentication system working
        print("\n   🔐 Test 2: Authentication System Integrity...")
        
        if 'courier' in self.tokens:
            # Test /api/auth/me endpoint
            success, me_response = self.run_test(
                "Get Current User Info",
                "GET",
                "/api/auth/me",
                200,
                token=self.tokens['courier']
            )
            all_success &= success
            
            if success:
                print("   ✅ Authentication system working correctly")
                user_role = me_response.get('role')
                user_name = me_response.get('full_name')
                print(f"   👤 Authenticated user: {user_name} ({user_role})")
            else:
                print("   ❌ Authentication system may have issues")
                all_success = False
        else:
            print("   ⚠️ No courier token available for authentication test")
        
        # Test 3: Core API endpoints functioning
        print("\n   🔗 Test 3: Core API Endpoints Functioning...")
        
        core_endpoints = [
            ("/api/health", "Health Check", None),
        ]
        
        # Add authenticated endpoints if courier token is available
        if 'courier' in self.tokens:
            core_endpoints.extend([
                ("/api/auth/me", "Current User Info", self.tokens['courier']),
                ("/api/courier/requests/new", "Courier New Requests", self.tokens['courier']),
            ])
        
        for endpoint, description, token in core_endpoints:
            success, response = self.run_test(
                f"Core Endpoint: {description}",
                "GET",
                endpoint,
                200,
                token=token
            )
            
            if success:
                print(f"   ✅ {description} working correctly")
                
                # Check for JSON serialization issues
                try:
                    json_str = json.dumps(response)
                    if 'ObjectId' in json_str:
                        print(f"   ⚠️ Potential ObjectId serialization issue in {description}")
                    else:
                        print(f"   ✅ JSON serialization correct for {description}")
                except Exception as e:
                    print(f"   ❌ JSON serialization error in {description}: {str(e)}")
                    all_success = False
            else:
                print(f"   ❌ {description} not working correctly")
                all_success = False
        
        # Test 4: No 500 Internal Server Errors
        print("\n   🚨 Test 4: No 500 Internal Server Errors...")
        
        error_500_count = 0
        test_endpoints = ["/api/health"]
        
        if 'courier' in self.tokens:
            test_endpoints.extend([
                "/api/auth/me",
                "/api/courier/requests/new"
            ])
        
        for endpoint in test_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                headers = {'Content-Type': 'application/json'}
                
                if endpoint != "/api/health" and 'courier' in self.tokens:
                    headers['Authorization'] = f'Bearer {self.tokens["courier"]}'
                
                response = requests.get(url, headers=headers)
                
                if response.status_code == 500:
                    error_500_count += 1
                    print(f"   ❌ 500 Error in {endpoint}")
                    
            except Exception as e:
                print(f"   ⚠️ Exception testing {endpoint}: {str(e)}")
        
        if error_500_count == 0:
            print("   ✅ No 500 Internal Server Errors found!")
        else:
            print(f"   ❌ Found {error_500_count} endpoints with 500 Internal Server Errors")
            all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all tests for backend stability after Phone import fix"""
        print("\n🚀 STARTING BACKEND STABILITY TESTS AFTER PHONE IMPORT FIX")
        print("   📋 Test Plan:")
        print("   1) BASIC CONNECTIVITY: Проверить доступность API и основных endpoints")
        print("   2) COURIER LOGIN: Быстро проверить авторизацию курьера (+79991234567/courier123)")
        print("   3) IMPORT FIX VERIFICATION: Убедиться что исправление frontend импорта Phone не повлияло на backend функциональность")
        
        start_time = datetime.now()
        
        # Run all test suites
        test_results = []
        
        # Test 1: Basic Connectivity
        result1 = self.test_basic_connectivity()
        test_results.append(("Basic Connectivity", result1))
        
        # Test 2: Courier Login
        result2 = self.test_courier_login()
        test_results.append(("Courier Login", result2))
        
        # Test 3: Import Fix Verification
        result3 = self.test_import_fix_verification()
        test_results.append(("Import Fix Verification", result3))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Final Summary
        print("\n" + "=" * 70)
        print("📊 FINAL TEST SUMMARY - BACKEND STABILITY AFTER PHONE IMPORT FIX")
        print("=" * 70)
        
        passed_tests = sum(1 for _, result in test_results if result)
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"⏱️ Test Duration: {duration:.2f} seconds")
        print(f"📈 Test Suite Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"🔍 Individual Tests: {self.tests_passed}/{self.tests_run} ({(self.tests_passed/self.tests_run*100):.1f}%)")
        
        print("\n📋 Test Results:")
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status} - {test_name}")
        
        overall_success = all(result for _, result in test_results)
        
        if overall_success:
            print("\n🎉 ALL TESTS PASSED - BACKEND STABILITY CONFIRMED!")
            print("✅ Backend работает стабильно после исправления ошибки импорта Phone")
            print("✅ Все основные endpoints доступны и функциональны")
            print("✅ Авторизация курьера работает корректно")
            print("✅ Исправление frontend импорта Phone не повлияло на backend функциональность")
            print("\n🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ!")
        else:
            print("\n❌ SOME TESTS FAILED - BACKEND STABILITY NEEDS ATTENTION")
            failed_tests = [name for name, result in test_results if not result]
            print(f"❌ Failed test suites: {', '.join(failed_tests)}")
            print("🔍 Check the specific failed tests above for details")
        
        return overall_success

if __name__ == "__main__":
    tester = PhoneImportFixTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)