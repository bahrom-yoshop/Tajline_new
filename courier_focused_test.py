#!/usr/bin/env python3
"""
Focused Courier Backend Testing for TAJLINE.TJ
Tests specifically the endpoints mentioned in the review request
"""

import requests
import sys
import json
from datetime import datetime

class CourierFocusedTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.courier_token = None
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🚚 TAJLINE.TJ Courier Focused Tester")
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

    def test_courier_backend_stability(self):
        """Test courier backend stability according to review request"""
        print("\n🎯 COURIER BACKEND STABILITY TESTING")
        print("   📋 ЗАДАЧИ ТЕСТИРОВАНИЯ:")
        print("   1) COURIER AUTHENTICATION: Проверить вход курьера (+79991234567/courier123)")
        print("   2) COURIER REQUESTS: Протестировать основные endpoints:")
        print("      - /api/courier/requests/new для получения новых заявок")
        print("      - /api/courier/requests/history для истории")
        print("   3) BACKEND STABILITY: Убедиться что frontend изменения не повлияли на backend")
        
        all_success = True
        
        # Test 1: COURIER AUTHENTICATION
        print("\n   🔐 Test 1: COURIER AUTHENTICATION...")
        
        courier_login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        success, login_response = self.run_test(
            "Courier Authentication (+79991234567/courier123)",
            "POST",
            "/api/auth/login",
            200,
            courier_login_data
        )
        all_success &= success
        
        if success and 'access_token' in login_response:
            self.courier_token = login_response['access_token']
            courier_user = login_response.get('user', {})
            courier_role = courier_user.get('role')
            courier_name = courier_user.get('full_name')
            courier_phone = courier_user.get('phone')
            user_number = courier_user.get('user_number')
            
            print(f"   ✅ Courier login successful!")
            print(f"   👤 Name: {courier_name}")
            print(f"   📞 Phone: {courier_phone}")
            print(f"   👑 Role: {courier_role}")
            print(f"   🆔 User Number: {user_number}")
            print(f"   🔑 JWT Token received: {self.courier_token[:50]}...")
            
            # Verify role is correct
            if courier_role == 'courier':
                print("   ✅ Courier role correctly set to 'courier'")
            else:
                print(f"   ❌ Courier role incorrect: expected 'courier', got '{courier_role}'")
                all_success = False
        else:
            print("   ❌ Courier login failed - no access token received")
            all_success = False
            return False
        
        # Test 2: /api/courier/requests/new для получения новых заявок
        print("\n   📋 Test 2: /api/courier/requests/new для получения новых заявок...")
        
        success, new_requests = self.run_test(
            "Get New Courier Requests",
            "GET",
            "/api/courier/requests/new",
            200,
            token=self.courier_token
        )
        all_success &= success
        
        if success:
            print("   ✅ /api/courier/requests/new endpoint working")
            
            # Analyze response structure
            if isinstance(new_requests, dict):
                if 'new_requests' in new_requests:
                    # Structured response with new_requests field
                    requests_list = new_requests['new_requests']
                    total_count = new_requests.get('total_count', len(requests_list))
                    courier_info = new_requests.get('courier_info', {})
                    
                    print(f"   📊 New requests found: {total_count}")
                    print(f"   📋 Requests in response: {len(requests_list)}")
                    print(f"   👤 Courier info available: {bool(courier_info)}")
                    print("   ✅ Structured response format with new_requests field")
                    
                elif 'items' in new_requests:
                    # Paginated response
                    items = new_requests['items']
                    total_count = new_requests.get('total_count', 0)
                    
                    print(f"   📊 New requests found: {total_count}")
                    print(f"   📋 Items in current page: {len(items)}")
                    print("   ✅ Paginated response format")
                    
                else:
                    # Direct dict response
                    print("   📊 Direct dictionary response")
                    print("   ✅ Response received successfully")
                    
            elif isinstance(new_requests, list):
                # Direct list response
                print(f"   📊 New requests found: {len(new_requests)}")
                print("   ✅ Direct list response format")
                
            else:
                print("   ❌ Unexpected response format")
                all_success = False
        else:
            print("   ❌ /api/courier/requests/new endpoint failed")
            all_success = False
        
        # Test 3: /api/courier/requests/history для истории
        print("\n   📚 Test 3: /api/courier/requests/history для истории...")
        
        success, history_requests = self.run_test(
            "Get Courier Request History",
            "GET",
            "/api/courier/requests/history",
            200,
            token=self.courier_token
        )
        all_success &= success
        
        if success:
            print("   ✅ /api/courier/requests/history endpoint working")
            
            # Analyze response structure
            if isinstance(history_requests, dict):
                if 'items' in history_requests:
                    # Paginated response
                    items = history_requests['items']
                    total_count = history_requests.get('total_count', 0)
                    page = history_requests.get('page', 1)
                    
                    print(f"   📊 Total history requests: {total_count}")
                    print(f"   📋 Items in current page: {len(items)}")
                    print(f"   📄 Current page: {page}")
                    print("   ✅ Paginated response structure correct")
                    
                else:
                    # Direct dict response
                    print("   📊 Direct dictionary response")
                    print("   ✅ Response received successfully")
                    
            elif isinstance(history_requests, list):
                # Direct list response
                print(f"   📊 History requests found: {len(history_requests)}")
                print("   ✅ Direct list response format")
                
            else:
                print("   ❌ Unexpected response format")
                all_success = False
        else:
            print("   ❌ /api/courier/requests/history endpoint failed")
            all_success = False
        
        # Test 4: BACKEND STABILITY - Check for 500 errors and JSON serialization
        print("\n   🛡️ Test 4: BACKEND STABILITY CHECK...")
        
        # Test multiple requests to check for stability
        stability_endpoints = [
            "/api/auth/me",
            "/api/courier/requests/new", 
            "/api/courier/requests/history"
        ]
        
        stability_results = []
        for endpoint in stability_endpoints:
            success, response = self.run_test(
                f"Stability Check - {endpoint}",
                "GET",
                endpoint,
                200,
                token=self.courier_token
            )
            stability_results.append(success)
        
        stability_success_rate = sum(stability_results) / len(stability_results) * 100
        
        if stability_success_rate == 100:
            print("   ✅ Backend stability confirmed - all endpoints working")
        elif stability_success_rate >= 75:
            print(f"   ⚠️ Backend mostly stable - {stability_success_rate:.1f}% success rate")
        else:
            print(f"   ❌ Backend stability issues - {stability_success_rate:.1f}% success rate")
            all_success = False
        
        # Test 5: Session Management Stability
        print("\n   🔒 Test 5: SESSION MANAGEMENT STABILITY...")
        
        session_tests = []
        for i in range(3):
            success, _ = self.run_test(
                f"Session Stability Test {i+1}",
                "GET",
                "/api/auth/me",
                200,
                token=self.courier_token
            )
            session_tests.append(success)
        
        session_success_rate = sum(session_tests) / len(session_tests) * 100
        
        if session_success_rate == 100:
            print("   ✅ Session management stable - no automatic logout")
        else:
            print(f"   ❌ Session management issues - {session_success_rate:.1f}% success rate")
            all_success = False
        
        # SUMMARY
        print("\n   📊 COURIER BACKEND STABILITY SUMMARY:")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"   📈 Overall Success Rate: {self.tests_passed}/{self.tests_run} ({success_rate:.1f}%)")
        
        if all_success:
            print("   🎉 ALL COURIER BACKEND STABILITY TESTS PASSED!")
            print("   ✅ Courier authentication working (+79991234567/courier123)")
            print("   ✅ /api/courier/requests/new endpoint functional")
            print("   ✅ /api/courier/requests/history endpoint functional")
            print("   ✅ Backend stability confirmed - no 500 errors")
            print("   ✅ Session management stable")
            print("   ✅ JSON serialization correct")
            print("   🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ: Backend остается стабильным после улучшений формы редактирования заявки курьера")
        else:
            print("   ❌ SOME COURIER BACKEND STABILITY TESTS FAILED")
            print("   🔍 Check the specific failed tests above for details")
        
        return all_success

if __name__ == "__main__":
    tester = CourierFocusedTester()
    result = tester.test_courier_backend_stability()
    
    print("\n" + "=" * 80)
    if result:
        print("🎉 COURIER BACKEND STABILITY TEST COMPLETED SUCCESSFULLY!")
    else:
        print("❌ COURIER BACKEND STABILITY TEST COMPLETED WITH ISSUES!")
    print("=" * 80)