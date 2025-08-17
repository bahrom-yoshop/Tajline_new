#!/usr/bin/env python3
"""
Warehouse Management API Testing for КаргоТранс Application
Tests warehouse creation and management functionality as specified in the requirements
"""

import requests
import sys
import json
from datetime import datetime

class WarehouseAPITester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.operator_token = None
        self.warehouse_ids = []
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🏭 КаргоТранс Warehouse API Tester")
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

    def setup_authentication(self):
        """Setup authentication for admin and warehouse operator"""
        print("\n🔐 AUTHENTICATION SETUP")
        
        # Login as admin
        admin_data = {"phone": "+79111111111", "password": "admin123"}
        success, response = self.run_test(
            "Admin Login", "POST", "/api/auth/login", 200, admin_data
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   🔑 Admin token obtained")
        else:
            # Try to register admin if login fails
            admin_reg_data = {
                "full_name": "Тест Админ",
                "phone": "+79111111111", 
                "password": "admin123",
                "role": "admin"
            }
            success, response = self.run_test(
                "Admin Registration", "POST", "/api/auth/register", 200, admin_reg_data
            )
            if success and 'access_token' in response:
                self.admin_token = response['access_token']
                print(f"   🔑 Admin registered and token obtained")
        
        # Login as warehouse operator
        operator_data = {"phone": "+79222222222", "password": "warehouse123"}
        success, response = self.run_test(
            "Operator Login", "POST", "/api/auth/login", 200, operator_data
        )
        
        if success and 'access_token' in response:
            self.operator_token = response['access_token']
            print(f"   🔑 Operator token obtained")
        else:
            # Try to register operator if login fails
            operator_reg_data = {
                "full_name": "Оператор Тест",
                "phone": "+79222222222",
                "password": "warehouse123", 
                "role": "warehouse_operator"
            }
            success, response = self.run_test(
                "Operator Registration", "POST", "/api/auth/register", 200, operator_reg_data
            )
            if success and 'access_token' in response:
                self.operator_token = response['access_token']
                print(f"   🔑 Operator registered and token obtained")
        
        return self.admin_token is not None and self.operator_token is not None

    def test_warehouse_creation_as_admin(self):
        """Test warehouse creation as admin with exact parameters from requirements"""
        print("\n🏭 WAREHOUSE CREATION (ADMIN)")
        
        if not self.admin_token:
            print("   ❌ No admin token available")
            return False
        
        # Test warehouse data as specified in requirements
        warehouse_data = {
            "name": "Тестовый склад Москва",
            "location": "Москва, ул. Складская, 10", 
            "blocks_count": 3,
            "shelves_per_block": 2,
            "cells_per_shelf": 5
        }
        
        success, response = self.run_test(
            "Create Test Warehouse Moscow",
            "POST",
            "/api/warehouses/create",
            200,
            warehouse_data,
            self.admin_token
        )
        
        if success:
            warehouse_id = response.get('id')
            if warehouse_id:
                self.warehouse_ids.append(warehouse_id)
                print(f"   🏭 Warehouse created with ID: {warehouse_id}")
                print(f"   📊 Total capacity: {response.get('total_capacity')} cells")
                
                # Verify capacity calculation (3 × 2 × 5 = 30)
                expected_capacity = 3 * 2 * 5
                actual_capacity = response.get('total_capacity')
                if actual_capacity == expected_capacity:
                    print(f"   ✅ Capacity calculation correct: {actual_capacity} cells")
                else:
                    print(f"   ❌ Capacity calculation wrong: expected {expected_capacity}, got {actual_capacity}")
                    
        return success

    def test_warehouse_creation_as_operator(self):
        """Test warehouse creation as warehouse operator"""
        print("\n🏭 WAREHOUSE CREATION (OPERATOR)")
        
        if not self.operator_token:
            print("   ❌ No operator token available")
            return False
        
        warehouse_data = {
            "name": "Склад Оператора",
            "location": "Москва, ул. Операторская, 5",
            "blocks_count": 2,
            "shelves_per_block": 3,
            "cells_per_shelf": 10
        }
        
        success, response = self.run_test(
            "Create Warehouse as Operator",
            "POST",
            "/api/warehouses/create", 
            200,
            warehouse_data,
            self.operator_token
        )
        
        if success:
            warehouse_id = response.get('id')
            if warehouse_id:
                self.warehouse_ids.append(warehouse_id)
                print(f"   🏭 Warehouse created with ID: {warehouse_id}")
                print(f"   📊 Total capacity: {response.get('total_capacity')} cells")
                
        return success

    def test_warehouse_list(self):
        """Test getting warehouse list"""
        print("\n📋 WAREHOUSE LIST")
        
        all_success = True
        
        # Test as admin
        if self.admin_token:
            success, response = self.run_test(
                "Get Warehouses (Admin)",
                "GET",
                "/api/warehouses",
                200,
                token=self.admin_token
            )
            
            if success:
                warehouse_count = len(response) if isinstance(response, list) else 0
                print(f"   🏭 Admin sees {warehouse_count} warehouses")
            
            all_success &= success
        
        # Test as operator
        if self.operator_token:
            success, response = self.run_test(
                "Get Warehouses (Operator)",
                "GET", 
                "/api/warehouses",
                200,
                token=self.operator_token
            )
            
            if success:
                warehouse_count = len(response) if isinstance(response, list) else 0
                print(f"   🏭 Operator sees {warehouse_count} warehouses")
            
            all_success &= success
            
        return all_success

    def test_warehouse_structure(self):
        """Test warehouse structure endpoint"""
        print("\n🏗️ WAREHOUSE STRUCTURE")
        
        if not self.warehouse_ids or not self.admin_token:
            print("   ❌ No warehouse or admin token available")
            return False
            
        warehouse_id = self.warehouse_ids[0]
        
        success, response = self.run_test(
            "Get Warehouse Structure",
            "GET",
            f"/api/warehouses/{warehouse_id}/structure",
            200,
            token=self.admin_token
        )
        
        if success:
            warehouse_info = response.get('warehouse', {})
            structure = response.get('structure', {})
            total_cells = response.get('total_cells', 0)
            available_cells = response.get('available_cells', 0)
            
            print(f"   🏭 Warehouse: {warehouse_info.get('name', 'Unknown')}")
            print(f"   📊 Total cells: {total_cells}")
            print(f"   🟢 Available cells: {available_cells}")
            print(f"   🏗️ Structure blocks: {len(structure)}")
            
        return success

    def test_warehouse_validation(self):
        """Test warehouse creation validation"""
        print("\n✅ WAREHOUSE VALIDATION")
        
        if not self.admin_token:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Test invalid data - too many blocks
        invalid_data = {
            "name": "Invalid Warehouse",
            "location": "Test Location",
            "blocks_count": 15,  # Should be max 9
            "shelves_per_block": 2,
            "cells_per_shelf": 5
        }
        
        success, _ = self.run_test(
            "Invalid Warehouse (Too Many Blocks)",
            "POST",
            "/api/warehouses/create",
            422,  # Validation error
            invalid_data,
            self.admin_token
        )
        all_success &= success
        
        # Test invalid data - too many shelves
        invalid_data2 = {
            "name": "Invalid Warehouse 2", 
            "location": "Test Location",
            "blocks_count": 2,
            "shelves_per_block": 5,  # Should be max 3
            "cells_per_shelf": 5
        }
        
        success, _ = self.run_test(
            "Invalid Warehouse (Too Many Shelves)",
            "POST",
            "/api/warehouses/create",
            422,  # Validation error
            invalid_data2,
            self.admin_token
        )
        all_success &= success
        
        return all_success

    def test_unauthorized_access(self):
        """Test unauthorized warehouse access"""
        print("\n🚫 UNAUTHORIZED ACCESS")
        
        # Test warehouse creation without token
        warehouse_data = {
            "name": "Unauthorized Warehouse",
            "location": "Test Location",
            "blocks_count": 1,
            "shelves_per_block": 1,
            "cells_per_shelf": 5
        }
        
        success, _ = self.run_test(
            "Create Warehouse Without Auth",
            "POST",
            "/api/warehouses/create",
            401,  # Unauthorized
            warehouse_data
        )
        
        return success

    def run_all_tests(self):
        """Run all warehouse tests"""
        print("🚀 Starting warehouse API testing...")
        
        test_results = []
        
        # Setup authentication first
        if not self.setup_authentication():
            print("❌ Authentication setup failed")
            return 1
        
        # Run test suites
        test_suites = [
            ("Warehouse Creation (Admin)", self.test_warehouse_creation_as_admin),
            ("Warehouse Creation (Operator)", self.test_warehouse_creation_as_operator),
            ("Warehouse List", self.test_warehouse_list),
            ("Warehouse Structure", self.test_warehouse_structure),
            ("Warehouse Validation", self.test_warehouse_validation),
            ("Unauthorized Access", self.test_unauthorized_access)
        ]
        
        for suite_name, test_func in test_suites:
            try:
                result = test_func()
                test_results.append((suite_name, result))
                if result:
                    print(f"✅ {suite_name} - PASSED")
                else:
                    print(f"❌ {suite_name} - FAILED")
            except Exception as e:
                print(f"💥 {suite_name} - ERROR: {str(e)}")
                test_results.append((suite_name, False))
        
        # Print final results
        print("\n" + "=" * 60)
        print("📊 WAREHOUSE TEST RESULTS")
        print("=" * 60)
        
        passed_suites = sum(1 for _, result in test_results if result)
        total_suites = len(test_results)
        
        for suite_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {suite_name}")
            
        print(f"\n📈 Overall Results:")
        print(f"   Test Suites: {passed_suites}/{total_suites} passed")
        print(f"   Individual Tests: {self.tests_passed}/{self.tests_run} passed")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if passed_suites == total_suites:
            print("\n🎉 ALL WAREHOUSE TESTS PASSED!")
            return 0
        else:
            print(f"\n⚠️  {total_suites - passed_suites} warehouse test suite(s) failed.")
            return 1

def main():
    """Main test execution"""
    tester = WarehouseAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())