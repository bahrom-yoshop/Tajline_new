#!/usr/bin/env python3
"""
Focused test for POST /api/user/cargo-request endpoint to identify [object Object] error
"""

import requests
import json
from datetime import datetime

class CargoRequestTester:
    def __init__(self, base_url="https://tajline-manager-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.bahrom_token = None
        
        print(f"🎯 CARGO REQUEST ENDPOINT TESTER")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

    def login_bahrom(self):
        """Login as Bahrom user"""
        print("\n🔐 LOGGING IN AS BAHROM")
        
        login_data = {
            "phone": "+992900000000",
            "password": "123456"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.bahrom_token = result.get('access_token')
                user_info = result.get('user', {})
                print(f"   ✅ Login successful")
                print(f"   👤 User: {user_info.get('full_name', 'Unknown')}")
                print(f"   📱 Phone: {user_info.get('phone', 'Unknown')}")
                print(f"   🎭 Role: {user_info.get('role', 'Unknown')}")
                return True
            else:
                print(f"   ❌ Login failed")
                try:
                    error = response.json()
                    print(f"   📄 Error: {error}")
                except:
                    print(f"   📄 Raw response: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception during login: {e}")
            return False

    def test_valid_cargo_request(self):
        """Test creating a valid cargo request"""
        print("\n📦 TESTING VALID CARGO REQUEST")
        
        if not self.bahrom_token:
            print("   ❌ No Bahrom token available")
            return False
            
        valid_data = {
            "recipient_full_name": "Иван Петрович Сидоров",
            "recipient_phone": "+992444555666",
            "recipient_address": "Душанбе, ул. Рудаки, 25, кв. 10",
            "pickup_address": "Москва, ул. Тверская, 15, офис 201",
            "cargo_name": "Документы и личные вещи",
            "weight": 15.5,
            "declared_value": 8000.0,
            "description": "Важные документы и личные вещи для семьи",
            "route": "moscow_dushanbe"
        }
        
        return self._make_request("Valid Cargo Request", valid_data, 200)

    def test_invalid_data_scenarios(self):
        """Test various invalid data scenarios"""
        print("\n⚠️  TESTING INVALID DATA SCENARIOS")
        
        if not self.bahrom_token:
            print("   ❌ No Bahrom token available")
            return False
            
        test_scenarios = [
            {
                "name": "Empty recipient_full_name",
                "data": {
                    "recipient_full_name": "",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Тест",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Тестовый груз",
                    "route": "moscow_dushanbe"
                },
                "expected_status": 422
            },
            {
                "name": "Invalid phone format",
                "data": {
                    "recipient_full_name": "Тест Тестович",
                    "recipient_phone": "123",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Тест",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Тестовый груз",
                    "route": "moscow_dushanbe"
                },
                "expected_status": 422
            },
            {
                "name": "Negative weight",
                "data": {
                    "recipient_full_name": "Тест Тестович",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Тест",
                    "weight": -5.0,
                    "declared_value": 5000.0,
                    "description": "Тестовый груз",
                    "route": "moscow_dushanbe"
                },
                "expected_status": 422
            },
            {
                "name": "Zero declared_value",
                "data": {
                    "recipient_full_name": "Тест Тестович",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Тест",
                    "weight": 10.0,
                    "declared_value": 0.0,
                    "description": "Тестовый груз",
                    "route": "moscow_dushanbe"
                },
                "expected_status": 422
            },
            {
                "name": "Invalid route",
                "data": {
                    "recipient_full_name": "Тест Тестович",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Тест",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Тестовый груз",
                    "route": "invalid_route"
                },
                "expected_status": 422
            },
            {
                "name": "Missing required fields",
                "data": {
                    "recipient_full_name": "Тест Тестович",
                    "weight": 10.0,
                    "declared_value": 5000.0
                    # Missing required fields
                },
                "expected_status": 422
            },
            {
                "name": "Wrong data types",
                "data": {
                    "recipient_full_name": "Тест Тестович",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Тест",
                    "weight": "not_a_number",  # Should be float
                    "declared_value": "not_a_number",  # Should be float
                    "description": "Тестовый груз",
                    "route": "moscow_dushanbe"
                },
                "expected_status": 422
            }
        ]
        
        all_success = True
        for scenario in test_scenarios:
            success = self._make_request(
                scenario["name"], 
                scenario["data"], 
                scenario["expected_status"]
            )
            all_success &= success
            
        return all_success

    def test_edge_cases(self):
        """Test edge cases that might cause [object Object] error"""
        print("\n🔍 TESTING EDGE CASES FOR [object Object] ERROR")
        
        if not self.bahrom_token:
            print("   ❌ No Bahrom token available")
            return False
            
        edge_cases = [
            {
                "name": "Very long strings",
                "data": {
                    "recipient_full_name": "А" * 200,  # Very long name
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Д" * 300,  # Very long address
                    "pickup_address": "М" * 300,  # Very long address
                    "cargo_name": "Т" * 200,  # Very long cargo name
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "О" * 600,  # Very long description
                    "route": "moscow_dushanbe"
                },
                "expected_status": 422
            },
            {
                "name": "Extreme weight values",
                "data": {
                    "recipient_full_name": "Тест Тестович",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Тест",
                    "weight": 99999.0,  # Very high weight
                    "declared_value": 5000.0,
                    "description": "Тестовый груз",
                    "route": "moscow_dushanbe"
                },
                "expected_status": 422
            },
            {
                "name": "Extreme declared_value",
                "data": {
                    "recipient_full_name": "Тест Тестович",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Тест",
                    "weight": 10.0,
                    "declared_value": 99999999.0,  # Very high value
                    "description": "Тестовый груз",
                    "route": "moscow_dushanbe"
                },
                "expected_status": 422
            },
            {
                "name": "Special characters in text fields",
                "data": {
                    "recipient_full_name": "Тест@#$%^&*()Тестович",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки@#$, 25",
                    "pickup_address": "Москва, ул. Тверская@#$, 15",
                    "cargo_name": "Тест@#$%^&*()",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Тестовый груз@#$%^&*()",
                    "route": "moscow_dushanbe"
                },
                "expected_status": 200  # Should be valid
            }
        ]
        
        all_success = True
        for case in edge_cases:
            success = self._make_request(
                case["name"], 
                case["data"], 
                case["expected_status"]
            )
            all_success &= success
            
        return all_success

    def test_malformed_json(self):
        """Test malformed JSON requests"""
        print("\n🔧 TESTING MALFORMED JSON REQUESTS")
        
        if not self.bahrom_token:
            print("   ❌ No Bahrom token available")
            return False
            
        # Test with malformed JSON
        malformed_requests = [
            {
                "name": "Invalid JSON syntax",
                "raw_data": '{"recipient_full_name": "Test", "weight": 10.0, "declared_value": 5000.0,}',  # Trailing comma
                "expected_status": 422
            },
            {
                "name": "Empty JSON",
                "raw_data": '{}',
                "expected_status": 422
            },
            {
                "name": "Non-JSON data",
                "raw_data": 'not json at all',
                "expected_status": 422
            }
        ]
        
        all_success = True
        for test in malformed_requests:
            success = self._make_raw_request(
                test["name"],
                test["raw_data"],
                test["expected_status"]
            )
            all_success &= success
            
        return all_success

    def _make_request(self, test_name, data, expected_status):
        """Make a request and analyze the response"""
        print(f"\n   🧪 {test_name}")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/user/cargo-request",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.bahrom_token}'
                }
            )
            
            print(f"      Status: {response.status_code} (expected: {expected_status})")
            
            # Always try to parse JSON response
            try:
                response_data = response.json()
                print(f"      Response type: {type(response_data)}")
                
                # Check for [object Object] patterns
                response_str = json.dumps(response_data, ensure_ascii=False)
                if "[object Object]" in response_str:
                    print(f"      🚨 FOUND [object Object] PATTERN!")
                    print(f"      📄 Full response: {response_str}")
                
                # Analyze error structure for validation errors
                if response.status_code == 422:
                    print(f"      🔍 VALIDATION ERROR ANALYSIS:")
                    if isinstance(response_data, dict):
                        if 'detail' in response_data:
                            detail = response_data['detail']
                            print(f"         Detail type: {type(detail)}")
                            print(f"         Detail content: {detail}")
                            
                            # Check if detail is a list of validation errors
                            if isinstance(detail, list):
                                print(f"         📋 Validation errors ({len(detail)} items):")
                                for i, error in enumerate(detail):
                                    print(f"            {i+1}. {error}")
                                    if isinstance(error, dict):
                                        for key, value in error.items():
                                            print(f"               {key}: {value} (type: {type(value)})")
                    
                    # Check for specific error patterns
                    if isinstance(response_data, list):
                        print(f"         📋 Response is a list with {len(response_data)} items")
                        for i, item in enumerate(response_data):
                            print(f"            {i+1}. {item} (type: {type(item)})")
                
                print(f"      📄 Response: {json.dumps(response_data, ensure_ascii=False, indent=2)[:500]}...")
                
            except json.JSONDecodeError:
                print(f"      ⚠️  Non-JSON response")
                print(f"      📄 Raw response: {response.text[:200]}...")
            
            # Check if status matches expected
            success = response.status_code == expected_status
            if success:
                print(f"      ✅ Status matches expected")
            else:
                print(f"      ❌ Status mismatch")
                
            return success
            
        except Exception as e:
            print(f"      ❌ Exception: {e}")
            return False

    def _make_raw_request(self, test_name, raw_data, expected_status):
        """Make a raw request with string data"""
        print(f"\n   🧪 {test_name}")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/user/cargo-request",
                data=raw_data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.bahrom_token}'
                }
            )
            
            print(f"      Status: {response.status_code} (expected: {expected_status})")
            
            try:
                response_data = response.json()
                response_str = json.dumps(response_data, ensure_ascii=False)
                if "[object Object]" in response_str:
                    print(f"      🚨 FOUND [object Object] PATTERN!")
                    print(f"      📄 Full response: {response_str}")
                print(f"      📄 Response: {json.dumps(response_data, ensure_ascii=False, indent=2)[:300]}...")
            except:
                print(f"      📄 Raw response: {response.text[:200]}...")
            
            return response.status_code == expected_status
            
        except Exception as e:
            print(f"      ❌ Exception: {e}")
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("\n🚀 STARTING COMPREHENSIVE CARGO REQUEST TESTING")
        
        # Step 1: Login
        if not self.login_bahrom():
            print("\n❌ Cannot proceed without login")
            return False
        
        # Step 2: Test valid request
        print("\n" + "="*60)
        valid_success = self.test_valid_cargo_request()
        
        # Step 3: Test invalid data scenarios
        print("\n" + "="*60)
        invalid_success = self.test_invalid_data_scenarios()
        
        # Step 4: Test edge cases
        print("\n" + "="*60)
        edge_success = self.test_edge_cases()
        
        # Step 5: Test malformed JSON
        print("\n" + "="*60)
        malformed_success = self.test_malformed_json()
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print(f"   Valid request: {'✅' if valid_success else '❌'}")
        print(f"   Invalid data scenarios: {'✅' if invalid_success else '❌'}")
        print(f"   Edge cases: {'✅' if edge_success else '❌'}")
        print(f"   Malformed JSON: {'✅' if malformed_success else '❌'}")
        
        overall_success = valid_success and invalid_success and edge_success and malformed_success
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success

if __name__ == "__main__":
    tester = CargoRequestTester()
    tester.run_all_tests()