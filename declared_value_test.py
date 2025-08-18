#!/usr/bin/env python3
"""
Specific test for UPDATED declared value logic in client cargo ordering system
Tests the new minimum declared value requirements:
- moscow_khujand: minimum 60 rubles
- moscow_dushanbe: minimum 80 rubles  
- moscow_kulob: minimum 80 rubles
- moscow_kurgantyube: minimum 80 rubles
"""

import requests
import sys
import json
from datetime import datetime

class DeclaredValueTester:
    def __init__(self, base_url="https://qr-logistics-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.user_token = None
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 DECLARED VALUE LOGIC TESTER")
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

    def login_user(self):
        """Login with the specific user mentioned in requirements"""
        print("\n🔐 USER LOGIN")
        
        success, response = self.run_test(
            "Login User +79123456789",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+79123456789", "password": "123456"}
        )
        
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            print(f"   ✅ Successfully logged in user +79123456789")
            return True
        else:
            print(f"   ❌ Could not login user +79123456789")
            return False

    def test_delivery_options(self):
        """Test delivery options endpoint"""
        print("\n📋 DELIVERY OPTIONS")
        
        success, delivery_options = self.run_test(
            "Get Delivery Options",
            "GET",
            "/api/client/cargo/delivery-options",
            200,
            token=self.user_token
        )
        
        if success:
            routes = delivery_options.get('routes', [])
            print(f"   🛣️  Available routes: {len(routes)}")
            
            # Verify expected routes are present
            route_values = [r.get('value') for r in routes]
            expected_routes = ['moscow_dushanbe', 'moscow_khujand', 'moscow_kulob', 'moscow_kurgantyube']
            
            all_routes_found = True
            for expected_route in expected_routes:
                if expected_route in route_values:
                    print(f"   ✅ Route {expected_route} available")
                else:
                    print(f"   ❌ Route {expected_route} missing")
                    all_routes_found = False
            
            return all_routes_found
        
        return False

    def test_declared_value_calculation_logic(self):
        """Test declared value logic in cost calculation"""
        print("\n💰 DECLARED VALUE CALCULATION LOGIC")
        
        test_scenarios = [
            # Test moscow_khujand with value below minimum (should become 60)
            {
                "route": "moscow_khujand", 
                "input_declared_value": 50.0, 
                "expected_minimum": 60.0,
                "description": "moscow_khujand: 50 → 60 rubles"
            },
            # Test moscow_khujand with value at minimum (should stay 60)
            {
                "route": "moscow_khujand", 
                "input_declared_value": 60.0, 
                "expected_minimum": 60.0,
                "description": "moscow_khujand: 60 → 60 rubles"
            },
            # Test moscow_dushanbe with value below minimum (should become 80)
            {
                "route": "moscow_dushanbe", 
                "input_declared_value": 70.0, 
                "expected_minimum": 80.0,
                "description": "moscow_dushanbe: 70 → 80 rubles"
            },
            # Test moscow_dushanbe with value at minimum (should stay 80)
            {
                "route": "moscow_dushanbe", 
                "input_declared_value": 80.0, 
                "expected_minimum": 80.0,
                "description": "moscow_dushanbe: 80 → 80 rubles"
            },
            # Test moscow_kulob with value below minimum (should become 80)
            {
                "route": "moscow_kulob", 
                "input_declared_value": 75.0, 
                "expected_minimum": 80.0,
                "description": "moscow_kulob: 75 → 80 rubles"
            },
            # Test moscow_kurgantyube with value below minimum (should become 80)
            {
                "route": "moscow_kurgantyube", 
                "input_declared_value": 65.0, 
                "expected_minimum": 80.0,
                "description": "moscow_kurgantyube: 65 → 80 rubles"
            },
            # Test with value above minimum (should stay as provided)
            {
                "route": "moscow_khujand", 
                "input_declared_value": 100.0, 
                "expected_minimum": 100.0,
                "description": "moscow_khujand: 100 → 100 rubles (above minimum)"
            }
        ]
        
        all_success = True
        
        for scenario in test_scenarios:
            cargo_data = {
                "cargo_name": f"Test {scenario['description']}",
                "description": "Test cargo for declared value logic",
                "weight": 10.0,
                "declared_value": scenario['input_declared_value'],
                "recipient_full_name": "Test Recipient",
                "recipient_phone": "+992444555666",
                "recipient_address": "Test recipient address",
                "recipient_city": "Dushanbe",
                "route": scenario['route'],
                "delivery_type": "standard",
                "insurance_requested": False,
                "packaging_service": False,
                "home_pickup": False,
                "home_delivery": False,
                "fragile": False,
                "temperature_sensitive": False
            }
            
            success, calculation = self.run_test(
                f"Calculate: {scenario['description']}",
                "POST",
                "/api/client/cargo/calculate",
                200,
                cargo_data,
                self.user_token
            )
            
            if success:
                calc_data = calculation.get('calculation', {})
                total_cost = calc_data.get('total_cost', 0)
                delivery_days = calc_data.get('delivery_time_days', 0)
                print(f"   💰 {scenario['description']}: {total_cost} руб, {delivery_days} дней")
                
                # Check if the declared value logic is working
                breakdown = calculation.get('breakdown', {})
                print(f"   📊 Breakdown: {breakdown}")
            else:
                all_success = False
        
        return all_success

    def test_declared_value_cargo_creation(self):
        """Test declared value logic in cargo creation"""
        print("\n📦 DECLARED VALUE CARGO CREATION")
        
        creation_tests = [
            {
                "route": "moscow_khujand",
                "declared_value": 50.0,  # Below minimum, should become 60
                "expected_final_value": 60.0,
                "description": "moscow_khujand with 50 rubles (should become 60)"
            },
            {
                "route": "moscow_dushanbe", 
                "declared_value": 70.0,  # Below minimum, should become 80
                "expected_final_value": 80.0,
                "description": "moscow_dushanbe with 70 rubles (should become 80)"
            },
            {
                "route": "moscow_kulob",
                "declared_value": 100.0,  # Above minimum, should stay 100
                "expected_final_value": 100.0,
                "description": "moscow_kulob with 100 rubles (should stay 100)"
            }
        ]
        
        created_cargo_numbers = []
        all_success = True
        
        for test in creation_tests:
            cargo_order_data = {
                "cargo_name": f"Test {test['description']}",
                "description": "Test cargo for declared value logic in creation",
                "weight": 5.5,
                "declared_value": test['declared_value'],
                "recipient_full_name": "Test Recipient",
                "recipient_phone": "+992901234567",
                "recipient_address": "Test address, 25, apt. 10",
                "recipient_city": "Khujand",
                "route": test['route'],
                "delivery_type": "standard",
                "insurance_requested": False,
                "packaging_service": False,
                "home_pickup": False,
                "home_delivery": False,
                "fragile": False,
                "temperature_sensitive": False
            }
            
            success, order_response = self.run_test(
                f"Create Cargo: {test['description']}",
                "POST",
                "/api/client/cargo/create",
                200,
                cargo_order_data,
                self.user_token
            )
            
            if success:
                created_cargo_id = order_response.get('cargo_id')
                created_cargo_number = order_response.get('cargo_number')
                total_cost = order_response.get('total_cost')
                
                print(f"   📦 Created cargo: {created_cargo_number}")
                print(f"   💰 Total cost: {total_cost} rubles")
                
                if created_cargo_number:
                    created_cargo_numbers.append((created_cargo_number, test['expected_final_value']))
                    
                    # Verify cargo number format
                    if len(created_cargo_number) == 4 and created_cargo_number.isdigit():
                        print(f"   ✅ Cargo number format is correct (4-digit)")
                    else:
                        print(f"   ❌ Invalid cargo number format: {created_cargo_number}")
                        all_success = False
            else:
                all_success = False
        
        # Test 4: Verify declared values in database
        print("\n   🗄️  Testing Declared Values in Database...")
        
        for cargo_number, expected_value in created_cargo_numbers:
            if cargo_number:
                # Test cargo tracking to verify declared value was saved correctly
                success, tracking_data = self.run_test(
                    f"Track Cargo {cargo_number} for Declared Value Check",
                    "GET",
                    f"/api/cargo/track/{cargo_number}",
                    200
                )
                
                if success:
                    saved_declared_value = tracking_data.get('declared_value')
                    
                    print(f"   📊 Cargo {cargo_number}: saved declared_value = {saved_declared_value}")
                    print(f"   🎯 Expected declared_value = {expected_value}")
                    
                    if saved_declared_value == expected_value:
                        print(f"   ✅ Declared value logic working correctly!")
                    else:
                        print(f"   ❌ Declared value logic failed - expected {expected_value}, got {saved_declared_value}")
                        all_success = False
                else:
                    all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all declared value tests"""
        print("\n🚀 STARTING DECLARED VALUE TESTS")
        
        # Step 1: Login
        if not self.login_user():
            print("\n❌ FAILED: Could not login user")
            return False
        
        # Step 2: Test delivery options
        if not self.test_delivery_options():
            print("\n❌ FAILED: Delivery options test failed")
            return False
        
        # Step 3: Test calculation logic
        if not self.test_declared_value_calculation_logic():
            print("\n❌ FAILED: Calculation logic test failed")
            return False
        
        # Step 4: Test cargo creation logic
        if not self.test_declared_value_cargo_creation():
            print("\n❌ FAILED: Cargo creation logic test failed")
            return False
        
        # Final summary
        print(f"\n🎯 DECLARED VALUE TESTS SUMMARY")
        print(f"   📊 Tests run: {self.tests_run}")
        print(f"   ✅ Tests passed: {self.tests_passed}")
        print(f"   ❌ Tests failed: {self.tests_run - self.tests_passed}")
        print(f"   📈 Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print(f"\n🎉 ALL DECLARED VALUE TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  SOME DECLARED VALUE TESTS FAILED!")
            return False

if __name__ == "__main__":
    tester = DeclaredValueTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)