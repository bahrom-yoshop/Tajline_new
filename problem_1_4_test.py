#!/usr/bin/env python3
"""
Focused Test for Problem 1.4: Cargo Acceptance Target Warehouse Assignment
Tests the POST /api/operator/cargo/accept endpoint to verify target_warehouse_id and target_warehouse_name fields
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class Problem14Tester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.warehouse_id = None
        self.binding_id = None
        
        print(f"🎯 PROBLEM 1.4 FOCUSED TEST: Cargo Acceptance Target Warehouse Assignment")
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

        print(f"\n🔍 {name}")
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
        """Setup test users, warehouse, and bindings"""
        print("\n🔧 SETTING UP TEST ENVIRONMENT")
        
        # 1. Login as admin
        admin_login = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        success, response = self.run_test(
            "Login Admin",
            "POST",
            "/api/auth/login",
            200,
            admin_login
        )
        
        if success and 'access_token' in response:
            self.tokens['admin'] = response['access_token']
            self.users['admin'] = response['user']
            print(f"   🔑 Admin token obtained")
        else:
            print("   ❌ Failed to get admin token")
            return False
        
        # 2. Login as warehouse operator
        operator_login = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, response = self.run_test(
            "Login Warehouse Operator",
            "POST",
            "/api/auth/login",
            200,
            operator_login
        )
        
        if success and 'access_token' in response:
            self.tokens['warehouse_operator'] = response['access_token']
            self.users['warehouse_operator'] = response['user']
            print(f"   🔑 Warehouse operator token obtained")
        else:
            print("   ❌ Failed to get warehouse operator token")
            return False
        
        # 3. Create a test warehouse
        warehouse_data = {
            "name": "Test Warehouse for Problem 1.4",
            "location": "Moscow Test Location",
            "blocks_count": 2,
            "shelves_per_block": 2,
            "cells_per_shelf": 5
        }
        
        success, response = self.run_test(
            "Create Test Warehouse",
            "POST",
            "/api/warehouses/create",
            200,
            warehouse_data,
            self.tokens['admin']
        )
        
        if success and 'id' in response:
            self.warehouse_id = response['id']
            print(f"   🏭 Test warehouse created: {self.warehouse_id}")
        else:
            print("   ❌ Failed to create test warehouse")
            return False
        
        # 4. Create operator-warehouse binding
        binding_data = {
            "operator_id": self.users['warehouse_operator']['id'],
            "warehouse_id": self.warehouse_id
        }
        
        success, response = self.run_test(
            "Create Operator-Warehouse Binding",
            "POST",
            "/api/admin/operator-warehouse-binding",
            200,
            binding_data,
            self.tokens['admin']
        )
        
        if success and 'binding_id' in response:
            self.binding_id = response['binding_id']
            print(f"   🔗 Operator-warehouse binding created: {self.binding_id}")
        else:
            print("   ❌ Failed to create operator-warehouse binding")
            return False
        
        print("   ✅ Test environment setup complete")
        return True

    def test_operator_cargo_acceptance_target_warehouse(self):
        """Test operator cargo acceptance with target warehouse assignment"""
        print("\n🎯 TEST 1: OPERATOR CARGO ACCEPTANCE - Target Warehouse Assignment")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        cargo_data = {
            "sender_full_name": "Test Sender Operator",
            "sender_phone": "+79111222333",
            "recipient_full_name": "Test Recipient Operator",
            "recipient_phone": "+992444555666",
            "recipient_address": "Dushanbe, Test Street, 1",
            "weight": 15.5,
            "cargo_name": "Test Cargo for Operator",
            "declared_value": 8000.0,
            "description": "Test cargo for operator acceptance",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Operator Cargo Acceptance",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            self.tokens['warehouse_operator']
        )
        
        if not success:
            return False
        
        # Verify response structure and target warehouse fields
        print("\n   🔍 VERIFYING RESPONSE FIELDS:")
        
        # Check if target_warehouse_id exists and is not None
        target_warehouse_id = response.get('target_warehouse_id')
        if target_warehouse_id is None:
            print(f"   ❌ CRITICAL: target_warehouse_id is None/missing")
            print(f"   📄 Full response: {json.dumps(response, indent=2, default=str)}")
            return False
        else:
            print(f"   ✅ target_warehouse_id present: {target_warehouse_id}")
        
        # Check if target_warehouse_name exists and is not None
        target_warehouse_name = response.get('target_warehouse_name')
        if target_warehouse_name is None:
            print(f"   ❌ CRITICAL: target_warehouse_name is None/missing")
            return False
        else:
            print(f"   ✅ target_warehouse_name present: {target_warehouse_name}")
        
        # Verify target_warehouse_id matches operator's bound warehouse
        if target_warehouse_id == self.warehouse_id:
            print(f"   ✅ target_warehouse_id matches operator's bound warehouse")
        else:
            print(f"   ❌ CRITICAL: target_warehouse_id ({target_warehouse_id}) does not match bound warehouse ({self.warehouse_id})")
            return False
        
        # Verify target_warehouse_name matches expected warehouse name
        if "Test Warehouse for Problem 1.4" in target_warehouse_name:
            print(f"   ✅ target_warehouse_name matches expected warehouse name")
        else:
            print(f"   ❌ target_warehouse_name ({target_warehouse_name}) doesn't match expected name")
            return False
        
        print("   ✅ OPERATOR CARGO ACCEPTANCE TEST PASSED")
        return True

    def test_admin_cargo_acceptance_target_warehouse(self):
        """Test admin cargo acceptance with target warehouse assignment"""
        print("\n🎯 TEST 2: ADMIN CARGO ACCEPTANCE - Target Warehouse Assignment")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
        
        cargo_data = {
            "sender_full_name": "Test Sender Admin",
            "sender_phone": "+79111222444",
            "recipient_full_name": "Test Recipient Admin",
            "recipient_phone": "+992444555777",
            "recipient_address": "Dushanbe, Admin Test Street, 2",
            "weight": 20.0,
            "cargo_name": "Test Cargo for Admin",
            "declared_value": 12000.0,
            "description": "Test cargo for admin acceptance",
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
        
        # Verify response structure and target warehouse fields
        print("\n   🔍 VERIFYING RESPONSE FIELDS:")
        
        # Check if target_warehouse_id exists and is not None
        target_warehouse_id = response.get('target_warehouse_id')
        if target_warehouse_id is None:
            print(f"   ❌ CRITICAL: target_warehouse_id is None/missing")
            print(f"   📄 Full response: {json.dumps(response, indent=2, default=str)}")
            return False
        else:
            print(f"   ✅ target_warehouse_id present: {target_warehouse_id}")
        
        # Check if target_warehouse_name exists and is not None
        target_warehouse_name = response.get('target_warehouse_name')
        if target_warehouse_name is None:
            print(f"   ❌ CRITICAL: target_warehouse_name is None/missing")
            return False
        else:
            print(f"   ✅ target_warehouse_name present: {target_warehouse_name}")
        
        # For admin, target_warehouse_id should be a valid warehouse ID from available active warehouses
        # We'll verify it's a valid UUID-like string and not empty
        if isinstance(target_warehouse_id, str) and len(target_warehouse_id) > 10:
            print(f"   ✅ target_warehouse_id appears to be a valid warehouse ID")
        else:
            print(f"   ❌ CRITICAL: target_warehouse_id ({target_warehouse_id}) doesn't appear to be a valid warehouse ID")
            return False
        
        # Verify target_warehouse_name is not empty
        if isinstance(target_warehouse_name, str) and len(target_warehouse_name) > 0:
            print(f"   ✅ target_warehouse_name is a valid non-empty string")
        else:
            print(f"   ❌ target_warehouse_name ({target_warehouse_name}) is not a valid warehouse name")
            return False
        
        print("   ✅ ADMIN CARGO ACCEPTANCE TEST PASSED")
        return True

    def test_admin_cargo_acceptance_no_warehouses(self):
        """Test admin cargo acceptance when no active warehouses exist"""
        print("\n🎯 TEST 3: ADMIN CARGO ACCEPTANCE - No Active Warehouses (Edge Case)")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
        
        # First, deactivate all warehouses to simulate the edge case
        print("   ⚠️  Deactivating test warehouse to simulate no active warehouses...")
        
        success, _ = self.run_test(
            "Deactivate Test Warehouse",
            "DELETE",
            f"/api/warehouses/{self.warehouse_id}",
            200,
            token=self.tokens['admin']
        )
        
        if not success:
            print("   ❌ Failed to deactivate warehouse for edge case test")
            return False
        
        # Now try to accept cargo when no active warehouses exist
        cargo_data = {
            "sender_full_name": "Test Sender No Warehouse",
            "sender_phone": "+79111222555",
            "recipient_full_name": "Test Recipient No Warehouse",
            "recipient_phone": "+992444555888",
            "recipient_address": "Dushanbe, No Warehouse Street, 3",
            "weight": 10.0,
            "cargo_name": "Test Cargo No Warehouse",
            "declared_value": 5000.0,
            "description": "Test cargo when no warehouses available",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Admin Cargo Acceptance - No Active Warehouses",
            "POST",
            "/api/operator/cargo/accept",
            400,  # Expecting 400 error when no active warehouses
            cargo_data,
            self.tokens['admin']
        )
        
        if success:
            print("   ✅ Correctly returned 400 error when no active warehouses available")
            
            # Verify error message mentions warehouse availability
            if 'detail' in response:
                error_detail = response['detail']
                if 'warehouse' in error_detail.lower():
                    print(f"   ✅ Error message mentions warehouse issue: {error_detail}")
                else:
                    print(f"   ⚠️  Error message doesn't mention warehouse: {error_detail}")
            
            return True
        else:
            print("   ❌ Expected 400 error but got different response")
            return False

    def run_all_tests(self):
        """Run all Problem 1.4 focused tests"""
        print("\n🚀 STARTING PROBLEM 1.4 FOCUSED TESTS")
        
        # Setup test environment
        if not self.setup_test_environment():
            print("\n❌ FAILED TO SETUP TEST ENVIRONMENT")
            return False
        
        # Run tests
        test_results = []
        
        # Test 1: Operator cargo acceptance
        result1 = self.test_operator_cargo_acceptance_target_warehouse()
        test_results.append(("Operator Cargo Acceptance", result1))
        
        # Test 2: Admin cargo acceptance
        result2 = self.test_admin_cargo_acceptance_target_warehouse()
        test_results.append(("Admin Cargo Acceptance", result2))
        
        # Test 3: Edge case - no active warehouses
        result3 = self.test_admin_cargo_acceptance_no_warehouses()
        test_results.append(("No Active Warehouses Edge Case", result3))
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 PROBLEM 1.4 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status} - {test_name}")
            if result:
                passed_tests += 1
        
        print(f"\n📊 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL PROBLEM 1.4 TESTS PASSED!")
            return True
        else:
            print("❌ SOME PROBLEM 1.4 TESTS FAILED!")
            return False

def main():
    """Main function to run Problem 1.4 tests"""
    tester = Problem14Tester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()