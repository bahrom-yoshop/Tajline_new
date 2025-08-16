#!/usr/bin/env python3
"""
Focused Test for Problem 1.4: Cargo Acceptance Target Warehouse Assignment Fix

This test specifically verifies that the POST /api/operator/cargo/accept endpoint
properly includes target_warehouse_id and target_warehouse_name in responses
for both warehouse_operator and admin tokens.
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class Problem14Tester:
    def __init__(self, base_url="https://cargo-tracker-29.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.warehouse_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 PROBLEM 1.4: Cargo Acceptance Target Warehouse Assignment Test")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 70)

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
        """Set up test environment with users, warehouse, and bindings"""
        print("\n🔧 SETTING UP TEST ENVIRONMENT")
        
        # Register test users
        test_users = [
            {
                "name": "Administrator",
                "data": {
                    "full_name": "Админ Тестовый",
                    "phone": "+79999888777",
                    "password": "admin123",
                    "role": "admin"
                }
            },
            {
                "name": "Warehouse Operator",
                "data": {
                    "full_name": "Оператор Тестовый",
                    "phone": "+79777888999",
                    "password": "warehouse123",
                    "role": "warehouse_operator"
                }
            }
        ]
        
        for user_info in test_users:
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
                print(f"   🔑 Token stored for {role}")
            else:
                # Try login if registration failed (user might already exist)
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
                    print(f"   🔑 Token stored for {role} (via login)")
        
        # Create a test warehouse
        if 'admin' in self.tokens:
            warehouse_data = {
                "name": "Склад для тестирования Problem 1.4",
                "location": "Москва, Тестовая территория",
                "blocks_count": 2,
                "shelves_per_block": 2,
                "cells_per_shelf": 3
            }
            
            success, warehouse_response = self.run_test(
                "Create Test Warehouse",
                "POST",
                "/api/warehouses/create",
                200,
                warehouse_data,
                self.tokens['admin']
            )
            
            if success and 'id' in warehouse_response:
                self.warehouse_id = warehouse_response['id']
                print(f"   🏭 Created warehouse: {self.warehouse_id}")
        
        # Create operator-warehouse binding
        if 'admin' in self.tokens and 'warehouse_operator' in self.users and self.warehouse_id:
            operator_id = self.users['warehouse_operator']['id']
            binding_data = {
                "operator_id": operator_id,
                "warehouse_id": self.warehouse_id
            }
            
            success, _ = self.run_test(
                "Create Operator-Warehouse Binding",
                "POST",
                "/api/admin/operator-warehouse-binding",
                200,
                binding_data,
                self.tokens['admin']
            )
            
            if success:
                print(f"   🔗 Operator bound to warehouse")
        
        return 'admin' in self.tokens and 'warehouse_operator' in self.tokens and self.warehouse_id

    def test_warehouse_operator_cargo_acceptance(self):
        """Test cargo acceptance with warehouse_operator token"""
        print("\n🏭 TESTING WAREHOUSE OPERATOR CARGO ACCEPTANCE")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        # First, get the operator's assigned warehouses to understand the expected behavior
        success, my_warehouses = self.run_test(
            "Get Operator's Assigned Warehouses",
            "GET",
            "/api/operator/my-warehouses",
            200,
            token=self.tokens['warehouse_operator']
        )
        
        if not success:
            print("   ❌ Could not get operator's warehouses")
            return False
        
        operator_warehouses = my_warehouses.get('warehouses', [])
        bound_warehouse_ids = [w['id'] for w in operator_warehouses]
        print(f"   📋 Operator has {len(operator_warehouses)} bound warehouses")
        
        cargo_data = {
            "sender_full_name": "Тестовый Отправитель Оператор",
            "sender_phone": "+79111222333",
            "recipient_full_name": "Тестовый Получатель Оператор",
            "recipient_phone": "+992444555666",
            "recipient_address": "Душанбе, ул. Тестовая, 1",
            "weight": 10.0,
            "declared_value": 5000.0,
            "description": "Груз для тестирования Problem 1.4 - оператор",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Warehouse Operator Cargo Acceptance",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            self.tokens['warehouse_operator']
        )
        
        if not success:
            return False
        
        # Verify target_warehouse_id is present and not None
        target_warehouse_id = response.get('target_warehouse_id')
        target_warehouse_name = response.get('target_warehouse_name')
        
        print(f"   📋 Response keys: {list(response.keys())}")
        print(f"   🎯 target_warehouse_id: {target_warehouse_id}")
        print(f"   🏷️  target_warehouse_name: {target_warehouse_name}")
        
        success_checks = []
        
        # Check target_warehouse_id
        if target_warehouse_id is not None and target_warehouse_id != "" and target_warehouse_id != "null":
            print(f"   ✅ target_warehouse_id is valid: {target_warehouse_id}")
            success_checks.append(True)
        else:
            print(f"   ❌ target_warehouse_id is invalid: {target_warehouse_id}")
            success_checks.append(False)
        
        # Check target_warehouse_name
        if target_warehouse_name is not None and target_warehouse_name != "" and target_warehouse_name != "null":
            print(f"   ✅ target_warehouse_name is valid: {target_warehouse_name}")
            success_checks.append(True)
        else:
            print(f"   ❌ target_warehouse_name is invalid: {target_warehouse_name}")
            success_checks.append(False)
        
        # Verify the target warehouse is one of the operator's bound warehouses
        # Note: The system uses the first warehouse from operator's bindings
        if target_warehouse_id in bound_warehouse_ids:
            print(f"   ✅ Target warehouse is one of operator's bound warehouses")
            success_checks.append(True)
        else:
            print(f"   ❌ Target warehouse not in operator's bound warehouses")
            print(f"       Target: {target_warehouse_id}")
            print(f"       Bound warehouses: {bound_warehouse_ids}")
            success_checks.append(False)
        
        return all(success_checks)

    def test_admin_cargo_acceptance(self):
        """Test cargo acceptance with admin token"""
        print("\n👑 TESTING ADMIN CARGO ACCEPTANCE")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
        
        cargo_data = {
            "sender_full_name": "Тестовый Отправитель Админ",
            "sender_phone": "+79222333444",
            "recipient_full_name": "Тестовый Получатель Админ",
            "recipient_phone": "+992555666777",
            "recipient_address": "Душанбе, ул. Админская, 2",
            "weight": 15.0,
            "declared_value": 7500.0,
            "description": "Груз для тестирования Problem 1.4 - админ",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Admin Cargo Acceptance",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            self.tokens['admin']
        )
        
        if not success:
            return False
        
        # Verify target_warehouse_id is present and not None
        target_warehouse_id = response.get('target_warehouse_id')
        target_warehouse_name = response.get('target_warehouse_name')
        
        print(f"   📋 Response keys: {list(response.keys())}")
        print(f"   🎯 target_warehouse_id: {target_warehouse_id}")
        print(f"   🏷️  target_warehouse_name: {target_warehouse_name}")
        
        success_checks = []
        
        # Check target_warehouse_id
        if target_warehouse_id is not None and target_warehouse_id != "" and target_warehouse_id != "null":
            print(f"   ✅ target_warehouse_id is valid: {target_warehouse_id}")
            success_checks.append(True)
        else:
            print(f"   ❌ target_warehouse_id is invalid: {target_warehouse_id}")
            success_checks.append(False)
        
        # Check target_warehouse_name
        if target_warehouse_name is not None and target_warehouse_name != "" and target_warehouse_name != "null":
            print(f"   ✅ target_warehouse_name is valid: {target_warehouse_name}")
            success_checks.append(True)
        else:
            print(f"   ❌ target_warehouse_name is invalid: {target_warehouse_name}")
            success_checks.append(False)
        
        # For admin, target warehouse should be any active warehouse (not necessarily the test warehouse)
        if target_warehouse_id:
            print(f"   ✅ Admin assigned to warehouse: {target_warehouse_id}")
            success_checks.append(True)
        else:
            print(f"   ❌ Admin not assigned to any warehouse")
            success_checks.append(False)
        
        return all(success_checks)

    def test_target_warehouse_id_not_null(self):
        """Test that target_warehouse_id is never None/null in responses"""
        print("\n🔍 TESTING TARGET_WAREHOUSE_ID NON-NULL VALIDATION")
        
        # Test multiple cargo acceptances to ensure consistency
        test_cases = [
            ("Operator Test Case 1", self.tokens.get('warehouse_operator')),
            ("Operator Test Case 2", self.tokens.get('warehouse_operator')),
            ("Admin Test Case 1", self.tokens.get('admin')),
            ("Admin Test Case 2", self.tokens.get('admin'))
        ]
        
        all_success = True
        
        for i, (case_name, token) in enumerate(test_cases):
            if not token:
                continue
                
            cargo_data = {
                "sender_full_name": f"Отправитель {case_name}",
                "sender_phone": f"+7911122233{i}",
                "recipient_full_name": f"Получатель {case_name}",
                "recipient_phone": f"+99244455566{i}",
                "recipient_address": f"Душанбе, ул. Тестовая, {i+1}",
                "weight": 5.0 + i,
                "declared_value": 3000.0 + (i * 500),
                "description": f"Груз для {case_name}",
                "route": "moscow_to_tajikistan"
            }
            
            success, response = self.run_test(
                f"Null Check: {case_name}",
                "POST",
                "/api/operator/cargo/accept",
                200,
                cargo_data,
                token
            )
            
            if success:
                target_id = response.get('target_warehouse_id')
                if target_id is None:
                    print(f"   ❌ {case_name}: target_warehouse_id is None")
                    all_success = False
                elif target_id == "":
                    print(f"   ❌ {case_name}: target_warehouse_id is empty string")
                    all_success = False
                elif target_id == "null":
                    print(f"   ❌ {case_name}: target_warehouse_id is string 'null'")
                    all_success = False
                else:
                    print(f"   ✅ {case_name}: target_warehouse_id is valid ({target_id})")
            else:
                all_success = False
        
        return all_success

    def run_problem_1_4_tests(self):
        """Run all Problem 1.4 specific tests"""
        print("\n🚀 STARTING PROBLEM 1.4 TESTS")
        print("=" * 70)
        
        # Setup test environment
        if not self.setup_test_environment():
            print("❌ Failed to set up test environment")
            return False
        
        # Run the specific tests
        test_results = []
        
        test_results.append(("Warehouse Operator Cargo Acceptance", self.test_warehouse_operator_cargo_acceptance()))
        test_results.append(("Admin Cargo Acceptance", self.test_admin_cargo_acceptance()))
        test_results.append(("Target Warehouse ID Non-Null Validation", self.test_target_warehouse_id_not_null()))
        
        # Print results
        print("\n" + "=" * 70)
        print("🏁 PROBLEM 1.4 TEST RESULTS")
        print("=" * 70)
        
        passed_tests = 0
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status:<12} {test_name}")
            if result:
                passed_tests += 1
        
        print("=" * 70)
        print(f"📊 OVERALL RESULTS: {passed_tests}/{len(test_results)} tests passed")
        print(f"📈 Success Rate: {(passed_tests/len(test_results)*100):.1f}%")
        print(f"🔧 Individual API Calls: {self.tests_passed}/{self.tests_run} passed")
        
        if passed_tests == len(test_results):
            print("🎉 PROBLEM 1.4 TESTS PASSED! Target warehouse assignment is working correctly.")
            return True
        else:
            failed_tests = len(test_results) - passed_tests
            print(f"⚠️  {failed_tests} test(s) failed. Problem 1.4 needs attention.")
            return False

if __name__ == "__main__":
    tester = Problem14Tester()
    success = tester.run_problem_1_4_tests()
    sys.exit(0 if success else 1)