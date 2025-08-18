#!/usr/bin/env python3
"""
Final Testing Script for КаргоТранс Application
Tests the specific scenarios mentioned in the review request
"""

import requests
import sys
import json
from datetime import datetime

class FinalTester:
    def __init__(self, base_url="https://tajline-cargo-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.operator_token = None
        self.warehouse_id = None
        self.cargo_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 КаргоТранс Final Testing")
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

    def test_admin_login(self):
        """Test admin login with specified credentials"""
        print("\n👑 ADMIN LOGIN TEST")
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            {"phone": "+79999888777", "password": "admin123"}
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   🔑 Admin token obtained")
            print(f"   👤 User: {response['user']['full_name']} ({response['user']['role']})")
            return True
        return False

    def test_create_warehouse_operator(self):
        """Create warehouse operator as specified in requirements"""
        print("\n👷 CREATE WAREHOUSE OPERATOR")
        
        if not self.admin_token:
            print("   ❌ No admin token available")
            return False
        
        operator_data = {
            "full_name": "Оператор Финальный",
            "phone": "+79111000111", 
            "password": "operator123",
            "role": "warehouse_operator"
        }
        
        success, response = self.run_test(
            "Create Warehouse Operator",
            "POST",
            "/api/auth/register",
            200,
            operator_data
        )
        
        if success and 'access_token' in response:
            self.operator_token = response['access_token']
            print(f"   🔑 Operator token obtained")
            print(f"   👤 User: {response['user']['full_name']} ({response['user']['role']})")
            return True
        elif not success:
            # Try to login if user already exists
            print("   ℹ️  User might already exist, trying to login...")
            success, response = self.run_test(
                "Login Existing Operator",
                "POST",
                "/api/auth/login",
                200,
                {"phone": "+79111000111", "password": "operator123"}
            )
            if success and 'access_token' in response:
                self.operator_token = response['access_token']
                print(f"   🔑 Operator token obtained via login")
                return True
        return False

    def test_accept_cargo(self):
        """Test accepting new cargo through operator form"""
        print("\n📦 ACCEPT NEW CARGO")
        
        if not self.admin_token:
            print("   ❌ No admin token available")
            return False
        
        cargo_data = {
            "sender_full_name": "Тестовый Отправитель",
            "sender_phone": "+79111222333",
            "recipient_full_name": "Тестовый Получатель",
            "recipient_phone": "+992444555666",
            "recipient_address": "Душанбе, ул. Тестовая, 1",
            "weight": 10.0,
            "declared_value": 5000.0,
            "description": "Тестовый груз для финального тестирования",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Accept New Cargo",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            self.admin_token
        )
        
        if success and 'id' in response:
            self.cargo_id = response['id']
            print(f"   📦 Cargo accepted with ID: {self.cargo_id}")
            print(f"   🏷️  Cargo number: {response.get('cargo_number', 'N/A')}")
            return True
        return False

    def test_create_warehouse(self):
        """Test creating warehouse"""
        print("\n🏗️ CREATE WAREHOUSE")
        
        if not self.admin_token:
            print("   ❌ No admin token available")
            return False
        
        warehouse_data = {
            "name": "Финальный Тестовый Склад",
            "location": "Москва, Тестовая территория",
            "blocks_count": 2,
            "shelves_per_block": 2,
            "cells_per_shelf": 10
        }
        
        success, response = self.run_test(
            "Create Warehouse",
            "POST",
            "/api/warehouses/create",
            200,
            warehouse_data,
            self.admin_token
        )
        
        if success and 'id' in response:
            self.warehouse_id = response['id']
            print(f"   🏭 Warehouse created with ID: {self.warehouse_id}")
            print(f"   📊 Total capacity: {response.get('total_capacity', 'N/A')} cells")
            return True
        return False

    def test_available_cells_api(self):
        """Test the fixed /api/warehouses/{id}/available-cells endpoint"""
        print("\n🔧 TEST FIXED AVAILABLE CELLS API")
        
        if not self.admin_token or not self.warehouse_id:
            print("   ❌ Missing admin token or warehouse ID")
            return False
        
        success, response = self.run_test(
            "Get Available Cells (Fixed API)",
            "GET",
            f"/api/warehouses/{self.warehouse_id}/available-cells",
            200,
            token=self.admin_token
        )
        
        if success:
            available_cells = response.get('available_cells', [])
            total_available = response.get('total_available', 0)
            warehouse_info = response.get('warehouse', {})
            
            print(f"   📊 Available cells: {total_available}")
            print(f"   🏭 Warehouse: {warehouse_info.get('name', 'N/A')}")
            print(f"   ✅ API endpoint working correctly (no 500 error)")
            return True
        return False

    def test_cargo_placement(self):
        """Test cargo placement in warehouse"""
        print("\n📍 CARGO PLACEMENT")
        
        if not self.admin_token or not self.warehouse_id or not self.cargo_id:
            print("   ❌ Missing required data for placement")
            return False
        
        placement_data = {
            "cargo_id": self.cargo_id,
            "warehouse_id": self.warehouse_id,
            "block_number": 1,
            "shelf_number": 1,
            "cell_number": 1
        }
        
        success, response = self.run_test(
            "Place Cargo in Warehouse",
            "POST",
            "/api/operator/cargo/place",
            200,
            placement_data,
            self.admin_token
        )
        
        if success:
            location = response.get('location', 'Unknown')
            warehouse_name = response.get('warehouse', 'Unknown')
            print(f"   📍 Cargo placed at: {location}")
            print(f"   🏭 Warehouse: {warehouse_name}")
            return True
        return False

    def test_operator_permissions(self):
        """Test that operator doesn't have access to admin functions"""
        print("\n🔒 OPERATOR PERMISSIONS TEST")
        
        if not self.operator_token:
            print("   ❌ No operator token available")
            return False
        
        # Test that operator cannot access admin users endpoint
        success, response = self.run_test(
            "Operator Access to Admin Users (Should Fail)",
            "GET",
            "/api/admin/users",
            403,  # Should be forbidden
            token=self.operator_token
        )
        
        if success:
            print("   ✅ Operator correctly denied access to admin functions")
            return True
        return False

    def test_complete_workflow(self):
        """Test the complete workflow as specified"""
        print("\n🔄 COMPLETE WORKFLOW TEST")
        
        workflow_success = True
        
        # 1. Admin login
        if not self.test_admin_login():
            workflow_success = False
        
        # 2. Create warehouse operator
        if not self.test_create_warehouse_operator():
            workflow_success = False
        
        # 3. Accept cargo
        if not self.test_accept_cargo():
            workflow_success = False
        
        # 4. Create warehouse
        if not self.test_create_warehouse():
            workflow_success = False
        
        # 5. Test fixed API
        if not self.test_available_cells_api():
            workflow_success = False
        
        # 6. Place cargo
        if not self.test_cargo_placement():
            workflow_success = False
        
        # 7. Test operator permissions
        if not self.test_operator_permissions():
            workflow_success = False
        
        return workflow_success

    def run_final_tests(self):
        """Run all final tests"""
        print("🚀 Starting final testing scenarios...")
        
        workflow_success = self.test_complete_workflow()
        
        # Print final results
        print("\n" + "=" * 60)
        print("📊 FINAL TEST RESULTS")
        print("=" * 60)
        
        print(f"📈 Individual Tests: {self.tests_passed}/{self.tests_run} passed")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print(f"🔄 Complete Workflow: {'✅ PASSED' if workflow_success else '❌ FAILED'}")
        
        if workflow_success and self.tests_passed == self.tests_run:
            print("\n🎉 ALL FINAL TESTS PASSED!")
            print("✅ Fixed API /api/warehouses/{id}/available-cells is working")
            print("✅ Complete cargo workflow is functional")
            print("✅ Operator permissions are correctly restricted")
            return 0
        else:
            print(f"\n⚠️  Some tests failed.")
            return 1

def main():
    """Main test execution"""
    tester = FinalTester()
    return tester.run_final_tests()

if __name__ == "__main__":
    sys.exit(main())