#!/usr/bin/env python3
"""
Multi-Cargo Form Functionality Test
Tests the enhanced multi-cargo form with calculator features
"""

import requests
import sys
import json
from datetime import datetime

class MultiCargoTester:
    def __init__(self, base_url="https://cargo-tracker-29.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🧮 MULTI-CARGO FORM TESTER")
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
                    if isinstance(result, dict) and len(str(result)) < 500:
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

    def login_admin(self):
        """Login as admin"""
        print("\n🔐 LOGGING IN AS ADMIN")
        
        success, response = self.run_test(
            "Login Admin",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+79999888777", "password": "admin123"}
        )
        
        if success and 'access_token' in response:
            self.tokens['admin'] = response['access_token']
            print(f"   🔑 Token obtained for admin")
            return True
        return False

    def test_enhanced_multi_cargo_form_functionality(self):
        """Test enhanced multi-cargo form functionality with calculator features"""
        print("\n🧮 ENHANCED MULTI-CARGO FORM WITH CALCULATOR")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Test 1: Single cargo mode (backward compatibility)
        print("\n   📦 Testing Single Cargo Mode (Backward Compatibility)...")
        
        single_cargo_data = {
            "sender_full_name": "Иван Тестов",
            "sender_phone": "+79999999999",
            "recipient_full_name": "Петр Получатель",
            "recipient_phone": "+992999999999",
            "recipient_address": "Душанбе",
            "weight": 5.0,
            "cargo_name": "Документы",
            "declared_value": 500,
            "price_per_kg": 100.0,  # Required field
            "description": "Документы и личные вещи",
            "route": "moscow_to_tajikistan"
        }
        
        success, single_response = self.run_test(
            "Single Cargo Mode Test",
            "POST",
            "/api/operator/cargo/accept",
            200,
            single_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        single_cargo_id = None
        if success and 'id' in single_response:
            single_cargo_id = single_response['id']
            cargo_number = single_response.get('cargo_number', 'N/A')
            weight = single_response.get('weight', 0)
            declared_value = single_response.get('declared_value', 0)
            cargo_name = single_response.get('cargo_name', 'N/A')
            
            print(f"   ✅ Single cargo created: {cargo_number}")
            print(f"   📊 Weight: {weight} kg, Value: {declared_value} руб")
            print(f"   🏷️  Cargo name: {cargo_name}")
            
            # Verify backward compatibility fields
            if weight == 5.0 and declared_value == 500 and cargo_name == "Документы":
                print("   ✅ Backward compatibility verified")
            else:
                print("   ❌ Backward compatibility failed")
                all_success = False
        
        # Test 2: Multi-cargo mode with calculator
        print("\n   🧮 Testing Multi-Cargo Mode with Calculator...")
        
        multi_cargo_data = {
            "sender_full_name": "Иван Тестов",
            "sender_phone": "+79999999999",
            "recipient_full_name": "Петр Получатель",
            "recipient_phone": "+992999999999",
            "recipient_address": "Душанбе",
            "cargo_items": [
                {"cargo_name": "Документы", "weight": 2.5},
                {"cargo_name": "Одежда", "weight": 3.0}
            ],
            "price_per_kg": 100.0,
            "description": "Разные виды груза",
            "route": "moscow_to_tajikistan"
        }
        
        success, multi_response = self.run_test(
            "Multi-Cargo Mode Test",
            "POST",
            "/api/operator/cargo/accept",
            200,
            multi_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        multi_cargo_id = None
        if success and 'id' in multi_response:
            multi_cargo_id = multi_response['id']
            cargo_number = multi_response.get('cargo_number', 'N/A')
            total_weight = multi_response.get('weight', 0)
            total_cost = multi_response.get('declared_value', 0)
            cargo_name = multi_response.get('cargo_name', 'N/A')
            description = multi_response.get('description', '')
            
            print(f"   ✅ Multi-cargo created: {cargo_number}")
            print(f"   📊 Total weight: {total_weight} kg")
            print(f"   💰 Total cost: {total_cost} руб")
            print(f"   🏷️  Combined cargo name: {cargo_name}")
            
            # Verify calculations
            expected_weight = 2.5 + 3.0  # 5.5 kg
            expected_cost = 5.5 * 100.0  # 550 rubles
            expected_name = "Документы, Одежда"
            
            if (abs(total_weight - expected_weight) < 0.01 and 
                abs(total_cost - expected_cost) < 0.01 and 
                cargo_name == expected_name):
                print("   ✅ Multi-cargo calculations verified")
            else:
                print(f"   ❌ Calculation error: expected {expected_weight}kg/{expected_cost}руб, got {total_weight}kg/{total_cost}руб")
                all_success = False
            
            # Verify detailed description includes composition breakdown
            if ("Состав груза:" in description and 
                "1. Документы - 2.5 кг" in description and
                "2. Одежда - 3.0 кг" in description and
                "Общий вес: 5.5 кг" in description and
                "Цена за кг: 100.0 руб." in description and
                "Общая стоимость: 550.0 руб." in description):
                print("   ✅ Detailed cargo description verified")
            else:
                print("   ❌ Detailed description missing required information")
                print(f"   📄 Description: {description[:200]}...")
                all_success = False
        
        # Test 3: Data structure validation
        print("\n   🔍 Testing Data Structure Validation...")
        
        # Test invalid cargo item (missing cargo_name)
        invalid_cargo_data = {
            "sender_full_name": "Тест Отправитель",
            "sender_phone": "+79999999999",
            "recipient_full_name": "Тест Получатель",
            "recipient_phone": "+992999999999",
            "recipient_address": "Душанбе",
            "cargo_items": [
                {"weight": 2.5}  # Missing cargo_name
            ],
            "price_per_kg": 100.0,
            "description": "Тест валидации",
            "route": "moscow_to_tajikistan"
        }
        
        success, _ = self.run_test(
            "Invalid Cargo Item Validation",
            "POST",
            "/api/operator/cargo/accept",
            422,  # Validation error expected
            invalid_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        if success:
            print("   ✅ Cargo item validation working correctly")
        
        # Test 4: Complex multi-cargo scenario
        print("\n   🎯 Testing Complex Multi-Cargo Scenario...")
        
        complex_cargo_data = {
            "sender_full_name": "Сложный Тест",
            "sender_phone": "+79999999998",
            "recipient_full_name": "Получатель Сложный",
            "recipient_phone": "+992999999998",
            "recipient_address": "Душанбе, сложный адрес",
            "cargo_items": [
                {"cargo_name": "Электроника", "weight": 1.2},
                {"cargo_name": "Книги", "weight": 3.8},
                {"cargo_name": "Сувениры", "weight": 0.5},
                {"cargo_name": "Медикаменты", "weight": 2.1}
            ],
            "price_per_kg": 150.0,
            "description": "Сложная посылка с разными товарами",
            "route": "moscow_to_tajikistan"
        }
        
        success, complex_response = self.run_test(
            "Complex Multi-Cargo Test",
            "POST",
            "/api/operator/cargo/accept",
            200,
            complex_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        if success and 'id' in complex_response:
            cargo_number = complex_response.get('cargo_number', 'N/A')
            total_weight = complex_response.get('weight', 0)
            total_cost = complex_response.get('declared_value', 0)
            cargo_name = complex_response.get('cargo_name', 'N/A')
            
            # Expected calculations
            expected_weight = 1.2 + 3.8 + 0.5 + 2.1  # 7.6 kg
            expected_cost = 7.6 * 150.0  # 1140 rubles
            expected_name = "Электроника, Книги, Сувениры, Медикаменты"
            
            print(f"   ✅ Complex cargo created: {cargo_number}")
            print(f"   📊 Weight: {total_weight} kg (expected: {expected_weight})")
            print(f"   💰 Cost: {total_cost} руб (expected: {expected_cost})")
            print(f"   🏷️  Name: {cargo_name}")
            
            if (abs(total_weight - expected_weight) < 0.01 and 
                abs(total_cost - expected_cost) < 0.01 and 
                cargo_name == expected_name):
                print("   ✅ Complex multi-cargo calculations verified")
            else:
                print("   ❌ Complex calculation error")
                all_success = False
        
        return all_success

    def run_tests(self):
        """Run all multi-cargo tests"""
        print("🚀 Starting multi-cargo form testing...")
        
        # Login first
        if not self.login_admin():
            print("❌ Failed to login as admin")
            return False
        
        # Run the multi-cargo tests
        success = self.test_enhanced_multi_cargo_form_functionality()
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"   Tests run: {self.tests_run}")
        print(f"   Tests passed: {self.tests_passed}")
        print(f"   Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if success:
            print("✅ MULTI-CARGO FORM FUNCTIONALITY - PASSED")
        else:
            print("❌ MULTI-CARGO FORM FUNCTIONALITY - FAILED")
        
        return success

if __name__ == "__main__":
    tester = MultiCargoTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)