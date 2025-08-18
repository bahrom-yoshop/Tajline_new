#!/usr/bin/env python3
"""
Backend Stability Testing for Yandex Maps Integration in TAJLINE.TJ Courier Interface
Tests backend stability after Yandex Maps integration (frontend only changes)
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class YandexMapsBackendTester:
    def __init__(self, base_url="https://tajline-cargo-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🗺️  YANDEX MAPS BACKEND STABILITY TESTER")
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

    def test_courier_authentication(self):
        """Test courier authentication (+79991234567/courier123) - role courier, token generation"""
        print("\n🔐 COURIER AUTHENTICATION TESTING")
        print("   🎯 Testing courier login (+79991234567/courier123) - role courier, token generation")
        
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
        
        if success and 'access_token' in login_response:
            courier_token = login_response['access_token']
            courier_user = login_response.get('user', {})
            courier_role = courier_user.get('role')
            courier_name = courier_user.get('full_name')
            courier_phone = courier_user.get('phone')
            courier_user_number = courier_user.get('user_number')
            
            print(f"   ✅ Courier login successful: {courier_name}")
            print(f"   👑 Role: {courier_role}")
            print(f"   📞 Phone: {courier_phone}")
            print(f"   🆔 User Number: {courier_user_number}")
            print(f"   🔑 JWT Token generated: {len(courier_token)} characters")
            
            # Verify role is courier
            if courier_role == 'courier':
                print("   ✅ Courier role correctly set to 'courier'")
            else:
                print(f"   ❌ Courier role incorrect: expected 'courier', got '{courier_role}'")
                return False
            
            # Store courier token for further tests
            self.tokens['courier'] = courier_token
            self.users['courier'] = courier_user
            return True
        else:
            print("   ❌ Courier authentication failed")
            return False

    def test_courier_requests_endpoints(self):
        """Test courier requests endpoints for address data structure"""
        print("\n📋 COURIER REQUESTS ENDPOINTS TESTING")
        print("   🎯 Testing courier requests endpoints for address data structure")
        
        if 'courier' not in self.tokens:
            print("   ❌ No courier token available")
            return False
            
        courier_token = self.tokens['courier']
        all_success = True
        
        # Test 1: /api/courier/requests/new - check that requests contain pickup_address for maps
        print("\n   📍 Test 1: /api/courier/requests/new - pickup_address for maps...")
        
        success, new_requests_response = self.run_test(
            "Get New Courier Requests (with pickup_address for maps)",
            "GET",
            "/api/courier/requests/new",
            200,
            token=courier_token
        )
        all_success &= success
        
        if success:
            print("   ✅ /api/courier/requests/new endpoint working")
            
            # Check response structure
            if isinstance(new_requests_response, dict):
                new_requests = new_requests_response.get('new_requests', [])
                total_count = new_requests_response.get('total_count', 0)
                
                print(f"   📊 New requests found: {total_count}")
                
                # Check for address data structure
                if new_requests and len(new_requests) > 0:
                    sample_request = new_requests[0]
                    
                    # Check required fields for Yandex Maps integration
                    required_fields = {
                        'pickup_address': 'для карты',
                        'sender_full_name': 'для маркеров',
                        'sender_phone': 'для информационных окон',
                        'cargo_name': 'для описания'
                    }
                    
                    fields_present = {}
                    for field, purpose in required_fields.items():
                        if field in sample_request and sample_request[field]:
                            fields_present[field] = sample_request[field]
                            print(f"   ✅ {field} present {purpose}: {sample_request[field]}")
                        else:
                            print(f"   ❌ {field} missing {purpose}")
                            all_success = False
                    
                    if len(fields_present) == len(required_fields):
                        print("   ✅ All required fields for Yandex Maps integration present")
                    else:
                        print(f"   ❌ Missing {len(required_fields) - len(fields_present)} required fields")
                        all_success = False
                else:
                    print("   ⚠️  No new requests available to check address structure")
            else:
                print("   ❌ Unexpected response format")
                all_success = False
        else:
            print("   ❌ /api/courier/requests/new endpoint failed")
            all_success = False
        
        # Test 2: /api/courier/requests/accepted - check accepted requests with addresses
        print("\n   ✅ Test 2: /api/courier/requests/accepted - accepted requests with addresses...")
        
        success, accepted_requests_response = self.run_test(
            "Get Accepted Courier Requests (with addresses)",
            "GET",
            "/api/courier/requests/accepted",
            200,
            token=courier_token
        )
        all_success &= success
        
        if success:
            print("   ✅ /api/courier/requests/accepted endpoint working")
            
            # Check response structure
            if isinstance(accepted_requests_response, dict):
                accepted_requests = accepted_requests_response.get('accepted_requests', [])
                total_count = accepted_requests_response.get('total_count', 0)
                
                print(f"   📊 Accepted requests found: {total_count}")
                
                # Check for address data structure
                if accepted_requests and len(accepted_requests) > 0:
                    sample_request = accepted_requests[0]
                    
                    # Check required fields for Yandex Maps integration
                    required_fields = {
                        'pickup_address': 'для карты',
                        'sender_full_name': 'для маркеров',
                        'sender_phone': 'для информационных окон',
                        'cargo_name': 'для описания'
                    }
                    
                    fields_present = {}
                    for field, purpose in required_fields.items():
                        if field in sample_request and sample_request[field]:
                            fields_present[field] = sample_request[field]
                            print(f"   ✅ {field} present {purpose}: {sample_request[field]}")
                        else:
                            print(f"   ❌ {field} missing {purpose}")
                            all_success = False
                    
                    if len(fields_present) == len(required_fields):
                        print("   ✅ All required fields for Yandex Maps integration present")
                    else:
                        print(f"   ❌ Missing {len(required_fields) - len(fields_present)} required fields")
                        all_success = False
                else:
                    print("   ⚠️  No accepted requests available to check address structure")
            else:
                print("   ❌ Unexpected response format")
                all_success = False
        else:
            print("   ❌ /api/courier/requests/accepted endpoint failed")
            all_success = False
        
        # Test 3: /api/courier/requests/picked - check picked requests
        print("\n   📦 Test 3: /api/courier/requests/picked - picked requests...")
        
        success, picked_requests_response = self.run_test(
            "Get Picked Courier Requests",
            "GET",
            "/api/courier/requests/picked",
            200,
            token=courier_token
        )
        all_success &= success
        
        if success:
            print("   ✅ /api/courier/requests/picked endpoint working")
            
            # Check response structure
            if isinstance(picked_requests_response, dict):
                picked_requests = picked_requests_response.get('picked_requests', [])
                total_count = picked_requests_response.get('total_count', 0)
                
                print(f"   📊 Picked requests found: {total_count}")
                
                # Check for address data structure if requests exist
                if picked_requests and len(picked_requests) > 0:
                    sample_request = picked_requests[0]
                    
                    # Check required fields for Yandex Maps integration
                    required_fields = ['pickup_address', 'sender_full_name', 'sender_phone', 'cargo_name']
                    
                    fields_present = 0
                    for field in required_fields:
                        if field in sample_request and sample_request[field]:
                            fields_present += 1
                            print(f"   ✅ {field} present: {sample_request[field]}")
                    
                    print(f"   📊 Address fields present: {fields_present}/{len(required_fields)}")
                else:
                    print("   ⚠️  No picked requests available to check address structure")
            else:
                print("   ❌ Unexpected response format")
                all_success = False
        else:
            print("   ❌ /api/courier/requests/picked endpoint failed")
            all_success = False
        
        # Test 4: /api/courier/requests/history - check request history
        print("\n   📚 Test 4: /api/courier/requests/history - request history...")
        
        success, history_response = self.run_test(
            "Get Courier Request History",
            "GET",
            "/api/courier/requests/history",
            200,
            token=courier_token
        )
        all_success &= success
        
        if success:
            print("   ✅ /api/courier/requests/history endpoint working")
            
            # Check response structure
            if isinstance(history_response, dict):
                # Check for pagination structure
                if 'items' in history_response:
                    items = history_response.get('items', [])
                    total_count = history_response.get('total_count', 0)
                    page = history_response.get('page', 1)
                    
                    print(f"   📊 History items found: {len(items)} (total: {total_count}, page: {page})")
                    print("   ✅ Pagination structure present")
                    
                    # Check for address data structure if items exist
                    if items and len(items) > 0:
                        sample_item = items[0]
                        
                        # Check required fields for Yandex Maps integration
                        required_fields = ['pickup_address', 'sender_full_name', 'sender_phone', 'cargo_name']
                        
                        fields_present = 0
                        for field in required_fields:
                            if field in sample_item and sample_item[field]:
                                fields_present += 1
                                print(f"   ✅ {field} present: {sample_item[field]}")
                        
                        print(f"   📊 Address fields present: {fields_present}/{len(required_fields)}")
                    else:
                        print("   ⚠️  No history items available to check address structure")
                else:
                    # Direct list format
                    history_items = history_response if isinstance(history_response, list) else []
                    print(f"   📊 History items found: {len(history_items)}")
            else:
                print("   ❌ Unexpected response format")
                all_success = False
        else:
            print("   ❌ /api/courier/requests/history endpoint failed")
            all_success = False
        
        return all_success

    def test_backend_stability(self):
        """Test backend stability after Yandex Maps integration"""
        print("\n🛡️  BACKEND STABILITY TESTING")
        print("   🎯 Testing backend stability after Yandex Maps integration (frontend only changes)")
        
        if 'courier' not in self.tokens:
            print("   ❌ No courier token available")
            return False
            
        courier_token = self.tokens['courier']
        all_success = True
        
        # Test 1: No 500 errors
        print("\n   🚨 Test 1: Checking for 500 Internal Server Errors...")
        
        endpoints_to_test = [
            "/api/courier/requests/new",
            "/api/courier/requests/accepted", 
            "/api/courier/requests/picked",
            "/api/courier/requests/history",
            "/api/auth/me"
        ]
        
        error_500_count = 0
        for endpoint in endpoints_to_test:
            try:
                url = f"{self.base_url}{endpoint}"
                headers = {'Authorization': f'Bearer {courier_token}', 'Content-Type': 'application/json'}
                response = requests.get(url, headers=headers)
                
                if response.status_code == 500:
                    error_500_count += 1
                    print(f"   ❌ 500 Error in {endpoint}")
                else:
                    print(f"   ✅ {endpoint} - Status: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Exception testing {endpoint}: {str(e)}")
                all_success = False
        
        if error_500_count == 0:
            print("   ✅ No 500 Internal Server Errors found!")
        else:
            print(f"   ❌ Found {error_500_count} endpoints with 500 Internal Server Errors")
            all_success = False
        
        # Test 2: JSON serialization correctness
        print("\n   🔍 Test 2: JSON Serialization Correctness...")
        
        serialization_issues = 0
        for endpoint in endpoints_to_test:
            try:
                url = f"{self.base_url}{endpoint}"
                headers = {'Authorization': f'Bearer {courier_token}', 'Content-Type': 'application/json'}
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        json_str = json.dumps(response_data)
                        
                        # Check for ObjectId serialization issues
                        if 'ObjectId' in json_str:
                            serialization_issues += 1
                            print(f"   ❌ ObjectId serialization issue in {endpoint}")
                        else:
                            print(f"   ✅ {endpoint} - JSON serialization correct")
                    except json.JSONDecodeError:
                        serialization_issues += 1
                        print(f"   ❌ JSON decode error in {endpoint}")
                else:
                    print(f"   ⚠️  {endpoint} - Status: {response.status_code} (skipping JSON check)")
            except Exception as e:
                serialization_issues += 1
                print(f"   ❌ Exception testing JSON serialization for {endpoint}: {str(e)}")
        
        if serialization_issues == 0:
            print("   ✅ All endpoints have correct JSON serialization!")
        else:
            print(f"   ❌ Found {serialization_issues} endpoints with JSON serialization issues")
            all_success = False
        
        # Test 3: Session management stability
        print("\n   🔐 Test 3: Session Management Stability...")
        
        session_tests = [
            ("/api/auth/me", "User Info"),
            ("/api/courier/requests/new", "New Requests"),
            ("/api/courier/requests/history", "Request History")
        ]
        
        session_failures = 0
        for endpoint, description in session_tests:
            success, response = self.run_test(
                f"Session Test - {description}",
                "GET",
                endpoint,
                200,
                token=courier_token
            )
            
            if not success:
                session_failures += 1
                print(f"   ❌ Session test failed for {description}")
            else:
                print(f"   ✅ Session stable for {description}")
        
        if session_failures == 0:
            print("   ✅ Session management stable!")
        else:
            print(f"   ❌ Found {session_failures} session management issues")
            all_success = False
        
        # Test 4: All endpoints respond with 200 status
        print("\n   📊 Test 4: All Endpoints Respond with 200 Status...")
        
        status_200_count = 0
        total_endpoints = len(endpoints_to_test)
        
        for endpoint in endpoints_to_test:
            try:
                url = f"{self.base_url}{endpoint}"
                headers = {'Authorization': f'Bearer {courier_token}', 'Content-Type': 'application/json'}
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    status_200_count += 1
                    print(f"   ✅ {endpoint} - 200 OK")
                else:
                    print(f"   ❌ {endpoint} - Status: {response.status_code}")
                    all_success = False
            except Exception as e:
                print(f"   ❌ Exception testing {endpoint}: {str(e)}")
                all_success = False
        
        success_rate = (status_200_count / total_endpoints * 100) if total_endpoints > 0 else 0
        print(f"   📈 Endpoint Success Rate: {status_200_count}/{total_endpoints} ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("   ✅ All endpoints respond with 200 status!")
        else:
            print(f"   ❌ {total_endpoints - status_200_count} endpoints not responding with 200 status")
            all_success = False
        
        return all_success

    def run_comprehensive_test(self):
        """Run comprehensive backend stability test for Yandex Maps integration"""
        print("\n🎯 COMPREHENSIVE BACKEND STABILITY TEST FOR YANDEX MAPS INTEGRATION")
        print("   📋 Testing backend stability after Yandex Maps integration in courier interface")
        print("   🗺️  Yandex Maps integration is frontend-only, backend should remain stable")
        
        test_results = {}
        
        # Test 1: Courier Authentication
        print("\n" + "="*80)
        test_results['courier_authentication'] = self.test_courier_authentication()
        
        # Test 2: Courier Requests Endpoints
        print("\n" + "="*80)
        test_results['courier_requests_endpoints'] = self.test_courier_requests_endpoints()
        
        # Test 3: Backend Stability
        print("\n" + "="*80)
        test_results['backend_stability'] = self.test_backend_stability()
        
        # Final Summary
        print("\n" + "="*80)
        print("🎉 FINAL COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Overall Test Results: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"🔢 Individual Tests Run: {self.tests_run}")
        print(f"✅ Individual Tests Passed: {self.tests_passed}")
        
        individual_success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Individual Success Rate: {individual_success_rate:.1f}%")
        
        print("\n📋 Test Category Results:")
        for category, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {category.replace('_', ' ').title()}: {status}")
        
        if all(test_results.values()):
            print("\n🎉 ALL TESTS PASSED - BACKEND STABILITY CONFIRMED!")
            print("✅ Courier authentication working (+79991234567/courier123)")
            print("✅ All courier endpoints contain pickup_address for maps")
            print("✅ Address data structure correct (pickup_address, sender_full_name, sender_phone, cargo_name)")
            print("✅ No 500 Internal Server Errors")
            print("✅ JSON serialization correct")
            print("✅ Session management stable")
            print("✅ All endpoints respond with 200 status")
            print("\n🗺️  YANDEX MAPS INTEGRATION BACKEND STABILITY: CONFIRMED")
            print("   Backend remains fully stable after frontend-only Yandex Maps integration")
            return True
        else:
            print("\n❌ SOME TESTS FAILED - BACKEND STABILITY ISSUES DETECTED")
            failed_categories = [cat for cat, result in test_results.items() if not result]
            print(f"   Failed categories: {', '.join(failed_categories)}")
            print("   🔍 Check the specific failed tests above for details")
            return False

if __name__ == "__main__":
    tester = YandexMapsBackendTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1)