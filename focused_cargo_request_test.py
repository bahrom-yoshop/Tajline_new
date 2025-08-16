#!/usr/bin/env python3
"""
Focused test for POST /api/user/cargo-request endpoint to identify [object Object] error
"""

import requests
import json
from datetime import datetime

class CargoRequestTester:
    def __init__(self, base_url="https://cargo-tracker-29.preview.emergentagent.com"):
        self.base_url = base_url
        self.bahrom_token = None
        
        print("🎯 CARGO REQUEST ENDPOINT TESTING")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

    def login_bahrom(self):
        """Login as Bahrom user"""
        print("\n🔐 BAHROM LOGIN")
        
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
            print(f"   ❌ Exception: {str(e)}")
            return False

    def test_valid_cargo_request(self):
        """Test creating a valid cargo request"""
        print("\n📦 VALID CARGO REQUEST TEST")
        
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
        
        return self._make_request("Valid Cargo Request", valid_data)

    def test_invalid_data_scenarios(self):
        """Test various invalid data scenarios"""
        print("\n⚠️  INVALID DATA SCENARIOS")
        
        if not self.bahrom_token:
            print("   ❌ No Bahrom token available")
            return False
            
        test_scenarios = [
            {
                "name": "Empty recipient name",
                "data": {
                    "recipient_full_name": "",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Test cargo",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Test description",
                    "route": "moscow_dushanbe"
                }
            },
            {
                "name": "Invalid phone format",
                "data": {
                    "recipient_full_name": "Test Recipient",
                    "recipient_phone": "123",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Test cargo",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Test description",
                    "route": "moscow_dushanbe"
                }
            },
            {
                "name": "Zero weight",
                "data": {
                    "recipient_full_name": "Test Recipient",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Test cargo",
                    "weight": 0.0,
                    "declared_value": 5000.0,
                    "description": "Test description",
                    "route": "moscow_dushanbe"
                }
            },
            {
                "name": "Negative declared value",
                "data": {
                    "recipient_full_name": "Test Recipient",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Test cargo",
                    "weight": 10.0,
                    "declared_value": -1000.0,
                    "description": "Test description",
                    "route": "moscow_dushanbe"
                }
            },
            {
                "name": "Missing required fields",
                "data": {
                    "recipient_full_name": "Test Recipient",
                    "weight": 10.0,
                    "declared_value": 5000.0
                    # Missing other required fields
                }
            },
            {
                "name": "Invalid route",
                "data": {
                    "recipient_full_name": "Test Recipient",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Test cargo",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Test description",
                    "route": "invalid_route"
                }
            },
            {
                "name": "Wrong data types",
                "data": {
                    "recipient_full_name": "Test Recipient",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Душанбе, ул. Рудаки, 25",
                    "pickup_address": "Москва, ул. Тверская, 15",
                    "cargo_name": "Test cargo",
                    "weight": "not_a_number",
                    "declared_value": "also_not_a_number",
                    "description": "Test description",
                    "route": "moscow_dushanbe"
                }
            }
        ]
        
        all_success = True
        for scenario in test_scenarios:
            success = self._make_request(scenario["name"], scenario["data"], expect_error=True)
            all_success &= success
            
        return all_success

    def test_edge_cases(self):
        """Test edge cases that might cause [object Object] error"""
        print("\n🔍 EDGE CASES FOR [object Object] ERROR")
        
        if not self.bahrom_token:
            print("   ❌ No Bahrom token available")
            return False
            
        edge_cases = [
            {
                "name": "Very long strings",
                "data": {
                    "recipient_full_name": "A" * 200,  # Very long name
                    "recipient_phone": "+992444555666",
                    "recipient_address": "B" * 300,  # Very long address
                    "pickup_address": "C" * 300,  # Very long pickup address
                    "cargo_name": "D" * 200,  # Very long cargo name
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "E" * 600,  # Very long description
                    "route": "moscow_dushanbe"
                }
            },
            {
                "name": "Special characters",
                "data": {
                    "recipient_full_name": "Test <script>alert('xss')</script>",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Address with special chars: @#$%^&*()",
                    "pickup_address": "Pickup with quotes: \"'`",
                    "cargo_name": "Cargo with unicode: 测试货物",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Description with newlines:\nLine 2\nLine 3",
                    "route": "moscow_dushanbe"
                }
            },
            {
                "name": "Extreme values",
                "data": {
                    "recipient_full_name": "Test Recipient",
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Test Address",
                    "pickup_address": "Test Pickup",
                    "cargo_name": "Test Cargo",
                    "weight": 999999.99,  # Very large weight
                    "declared_value": 999999999.99,  # Very large value
                    "description": "Test description",
                    "route": "moscow_dushanbe"
                }
            },
            {
                "name": "Array instead of string",
                "data": {
                    "recipient_full_name": ["Test", "Recipient"],  # Array instead of string
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Test Address",
                    "pickup_address": "Test Pickup",
                    "cargo_name": "Test Cargo",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Test description",
                    "route": "moscow_dushanbe"
                }
            },
            {
                "name": "Object instead of string",
                "data": {
                    "recipient_full_name": {"first": "Test", "last": "Recipient"},  # Object instead of string
                    "recipient_phone": "+992444555666",
                    "recipient_address": "Test Address",
                    "pickup_address": "Test Pickup",
                    "cargo_name": "Test Cargo",
                    "weight": 10.0,
                    "declared_value": 5000.0,
                    "description": "Test description",
                    "route": "moscow_dushanbe"
                }
            }
        ]
        
        all_success = True
        for case in edge_cases:
            success = self._make_request(case["name"], case["data"], expect_error=True)
            all_success &= success
            
        return all_success

    def _make_request(self, test_name, data, expect_error=False):
        """Make a request to the cargo-request endpoint"""
        print(f"\n   🧪 Test: {test_name}")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/user/cargo-request",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.bahrom_token}'
                }
            )
            
            print(f"   📊 Status Code: {response.status_code}")
            print(f"   📋 Headers: {dict(response.headers)}")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                print(f"   📄 Response Type: {type(response_data)}")
                
                if isinstance(response_data, dict):
                    print(f"   📄 Response Keys: {list(response_data.keys())}")
                    
                    # Check for validation errors that might cause [object Object]
                    if 'detail' in response_data:
                        detail = response_data['detail']
                        print(f"   ⚠️  Detail Type: {type(detail)}")
                        print(f"   ⚠️  Detail Content: {detail}")
                        
                        # Check if detail is a list (common for validation errors)
                        if isinstance(detail, list):
                            print(f"   📋 Detail is a list with {len(detail)} items:")
                            for i, item in enumerate(detail):
                                print(f"      [{i}] Type: {type(item)}, Content: {item}")
                                
                elif isinstance(response_data, list):
                    print(f"   📄 Response is a list with {len(response_data)} items:")
                    for i, item in enumerate(response_data):
                        print(f"      [{i}] Type: {type(item)}, Content: {item}")
                
                # Print full response for analysis
                print(f"   📄 Full Response: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                
            except json.JSONDecodeError:
                print(f"   ❌ Failed to parse JSON response")
                print(f"   📄 Raw Response: {response.text}")
                
            # Determine success
            if expect_error:
                success = response.status_code >= 400
                if success:
                    print(f"   ✅ Expected error received")
                else:
                    print(f"   ❌ Expected error but got success")
            else:
                success = response.status_code == 200
                if success:
                    print(f"   ✅ Request successful")
                else:
                    print(f"   ❌ Request failed")
                    
            return success
            
        except Exception as e:
            print(f"   ❌ Exception occurred: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("\n🚀 STARTING COMPREHENSIVE CARGO REQUEST TESTING")
        
        # Step 1: Login as Bahrom
        if not self.login_bahrom():
            print("\n❌ TESTING ABORTED - Could not login as Bahrom")
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
        
        # Summary
        print("\n" + "="*60)
        print("📊 TESTING SUMMARY")
        print(f"   Valid Request Test: {'✅ PASSED' if valid_success else '❌ FAILED'}")
        print(f"   Invalid Data Tests: {'✅ PASSED' if invalid_success else '❌ FAILED'}")
        print(f"   Edge Case Tests: {'✅ PASSED' if edge_success else '❌ FAILED'}")
        
        overall_success = valid_success and invalid_success and edge_success
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success

if __name__ == "__main__":
    tester = CargoRequestTester()
    tester.run_all_tests()