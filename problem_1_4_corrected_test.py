#!/usr/bin/env python3
"""
Corrected Test for Problem 1.4: Cargo Acceptance Target Warehouse Assignment
Tests the POST /api/operator/cargo/accept endpoint to verify target_warehouse_id and target_warehouse_name fields
This version accounts for operators having multiple warehouse bindings
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class Problem14CorrectedTester:
    def __init__(self, base_url="https://cargo-talk.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        
        print(f"🎯 PROBLEM 1.4 CORRECTED TEST: Cargo Acceptance Target Warehouse Assignment")
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
        """Setup test users"""
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
        
        print("   ✅ Test environment setup complete")
        return True

    def test_operator_cargo_acceptance_target_warehouse(self):
        """Test operator cargo acceptance with target warehouse assignment"""
        print("\n🎯 TEST 1: OPERATOR CARGO ACCEPTANCE - Target Warehouse Assignment")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        # First, get the operator's assigned warehouses to know what to expect
        success, my_warehouses = self.run_test(
            "Get Operator's Assigned Warehouses",
            "GET",
            "/api/operator/my-warehouses",
            200,
            token=self.tokens['warehouse_operator']
        )
        
        if not success or not my_warehouses.get('warehouses'):
            print("   ❌ Operator has no assigned warehouses")
            return False
        
        # Get the first warehouse (which should be the target)
        expected_warehouse = my_warehouses['warehouses'][0]
        expected_warehouse_id = expected_warehouse['id']
        expected_warehouse_name = expected_warehouse['name']
        
        print(f"   📋 Operator has {len(my_warehouses['warehouses'])} assigned warehouses")
        print(f"   🎯 Expected target warehouse: {expected_warehouse_name} ({expected_warehouse_id})")
        
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
        
        # Verify target_warehouse_id matches one of operator's bound warehouses
        operator_warehouse_ids = [w['id'] for w in my_warehouses['warehouses']]
        if target_warehouse_id in operator_warehouse_ids:
            print(f"   ✅ target_warehouse_id matches one of operator's bound warehouses")
        else:
            print(f"   ❌ CRITICAL: target_warehouse_id ({target_warehouse_id}) is not in operator's bound warehouses")
            print(f"   📋 Operator's warehouses: {operator_warehouse_ids}")
            return False
        
        # Verify target_warehouse_id matches the FIRST warehouse (system behavior)
        if target_warehouse_id == expected_warehouse_id:
            print(f"   ✅ target_warehouse_id matches expected first warehouse (correct system behavior)")
        else:
            print(f"   ⚠️  target_warehouse_id ({target_warehouse_id}) doesn't match first warehouse ({expected_warehouse_id})")
            print(f"   ℹ️  This could indicate system is not using first warehouse as expected")
        
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
        
        # Verify the warehouse actually exists by checking active warehouses
        success, warehouses = self.run_test(
            "Get All Active Warehouses",
            "GET",
            "/api/warehouses",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            warehouse_ids = [w['id'] for w in warehouses]
            if target_warehouse_id in warehouse_ids:
                print(f"   ✅ target_warehouse_id exists in active warehouses")
            else:
                print(f"   ❌ target_warehouse_id not found in active warehouses")
                return False
        
        print("   ✅ ADMIN CARGO ACCEPTANCE TEST PASSED")
        return True

    def test_field_presence_and_structure(self):
        """Test that the required fields are present in the response structure"""
        print("\n🎯 TEST 3: RESPONSE STRUCTURE VERIFICATION")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        cargo_data = {
            "sender_full_name": "Structure Test Sender",
            "sender_phone": "+79111222555",
            "recipient_full_name": "Structure Test Recipient",
            "recipient_phone": "+992444555888",
            "recipient_address": "Dushanbe, Structure Test Street, 3",
            "weight": 10.0,
            "cargo_name": "Structure Test Cargo",
            "declared_value": 5000.0,
            "description": "Test cargo for structure verification",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Cargo Acceptance for Structure Test",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            self.tokens['warehouse_operator']
        )
        
        if not success:
            return False
        
        print("\n   🔍 VERIFYING RESPONSE STRUCTURE:")
        
        # Required fields that should be present
        required_fields = [
            'id', 'cargo_number', 'sender_full_name', 'recipient_full_name',
            'weight', 'declared_value', 'status', 'created_at', 'updated_at',
            'created_by_operator', 'target_warehouse_id', 'target_warehouse_name'
        ]
        
        missing_fields = []
        present_fields = []
        
        for field in required_fields:
            if field in response:
                present_fields.append(field)
                print(f"   ✅ {field}: {response[field]}")
            else:
                missing_fields.append(field)
                print(f"   ❌ {field}: MISSING")
        
        if missing_fields:
            print(f"\n   ❌ CRITICAL: Missing required fields: {missing_fields}")
            return False
        else:
            print(f"\n   ✅ All required fields present ({len(present_fields)}/{len(required_fields)})")
        
        # Specifically verify the Problem 1.4 fields
        target_warehouse_id = response.get('target_warehouse_id')
        target_warehouse_name = response.get('target_warehouse_name')
        
        if target_warehouse_id and target_warehouse_name:
            print(f"   🎯 PROBLEM 1.4 FIELDS VERIFIED:")
            print(f"      target_warehouse_id: {target_warehouse_id}")
            print(f"      target_warehouse_name: {target_warehouse_name}")
            print(f"   ✅ Problem 1.4 requirements satisfied")
        else:
            print(f"   ❌ Problem 1.4 fields missing or None")
            return False
        
        print("   ✅ RESPONSE STRUCTURE TEST PASSED")
        return True

    def run_all_tests(self):
        """Run all Problem 1.4 focused tests"""
        print("\n🚀 STARTING PROBLEM 1.4 CORRECTED TESTS")
        
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
        
        # Test 3: Response structure verification
        result3 = self.test_field_presence_and_structure()
        test_results.append(("Response Structure Verification", result3))
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 PROBLEM 1.4 CORRECTED TEST RESULTS SUMMARY")
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
            print("\n📋 SUMMARY:")
            print("   ✅ target_warehouse_id field is properly populated")
            print("   ✅ target_warehouse_name field is properly populated")
            print("   ✅ Operator cargo acceptance assigns warehouse from operator bindings")
            print("   ✅ Admin cargo acceptance assigns warehouse from available active warehouses")
            print("   ✅ Response structure includes all required fields")
            return True
        else:
            print("❌ SOME PROBLEM 1.4 TESTS FAILED!")
            return False

def main():
    """Main function to run Problem 1.4 corrected tests"""
    tester = Problem14CorrectedTester()
    
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