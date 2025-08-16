#!/usr/bin/env python3
"""
Focused test for Warehouse Cell Management System
Tests the newly implemented warehouse cell management endpoints
"""

import requests
import sys
import json
from datetime import datetime

class WarehouseCellTester:
    def __init__(self, base_url="https://cargo-tracker-29.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.warehouse_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🏢 WAREHOUSE CELL MANAGEMENT TESTER")
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

    def setup_authentication(self):
        """Setup authentication tokens"""
        print("\n🔐 SETTING UP AUTHENTICATION")
        
        # Login as admin
        admin_login = {
            "phone": "+79999999999",
            "password": "123456"
        }
        
        success, admin_response = self.run_test(
            "Login Admin",
            "POST",
            "/api/auth/login",
            200,
            admin_login
        )
        
        if success and 'access_token' in admin_response:
            self.tokens['admin'] = admin_response['access_token']
            self.users['admin'] = admin_response['user']
            print(f"   ✅ Admin authenticated")
        else:
            print(f"   ❌ Failed to authenticate admin")
            return False
        
        # Login as warehouse operator
        operator_login = {
            "phone": "+79666666666",
            "password": "123456"
        }
        
        success, operator_response = self.run_test(
            "Login Warehouse Operator",
            "POST",
            "/api/auth/login",
            200,
            operator_login
        )
        
        if success and 'access_token' in operator_response:
            self.tokens['warehouse_operator'] = operator_response['access_token']
            self.users['warehouse_operator'] = operator_response['user']
            print(f"   ✅ Warehouse operator authenticated")
        else:
            print(f"   ❌ Failed to authenticate warehouse operator")
            return False
        
        return True

    def setup_warehouse(self):
        """Create a test warehouse"""
        print("\n🏭 SETTING UP TEST WAREHOUSE")
        
        warehouse_data = {
            "name": "Тестовый Склад для Ячеек",
            "location": "Москва, ул. Тестовая, 1",
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
            print(f"   ✅ Test warehouse created: {self.warehouse_id}")
            return True
        else:
            print(f"   ❌ Failed to create test warehouse")
            return False

    def test_warehouse_cell_endpoints(self):
        """Test the new warehouse cell management endpoints"""
        print("\n🏢 TESTING WAREHOUSE CELL MANAGEMENT ENDPOINTS")
        all_success = True
        
        # Create test cargo
        cargo_data = {
            "sender_full_name": "Тест Отправитель",
            "sender_phone": "+79111222333",
            "recipient_full_name": "Тест Получатель",
            "recipient_phone": "+992444555666",
            "recipient_address": "Душанбе, ул. Тестовая, 10",
            "weight": 5.0,
            "cargo_name": "Тестовый Груз",
            "declared_value": 2500.0,
            "description": "Груз для тестирования ячеек",
            "route": "moscow_to_tajikistan"
        }
        
        success, cargo_response = self.run_test(
            "Create Test Cargo",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            self.tokens['warehouse_operator']
        )
        
        if not success or 'id' not in cargo_response:
            print("   ❌ Failed to create test cargo")
            return False
        
        cargo_id = cargo_response['id']
        cargo_number = cargo_response['cargo_number']
        print(f"   📦 Created cargo: {cargo_number} (ID: {cargo_id})")
        
        # Place cargo in warehouse cell
        placement_data = {
            "cargo_id": cargo_id,
            "warehouse_id": self.warehouse_id,
            "block_number": 1,
            "shelf_number": 1,
            "cell_number": 1
        }
        
        success, _ = self.run_test(
            "Place Cargo in Cell",
            "POST",
            "/api/operator/cargo/place",
            200,
            placement_data,
            self.tokens['warehouse_operator']
        )
        
        if not success:
            print("   ❌ Failed to place cargo in cell")
            return False
        
        print(f"   ✅ Cargo placed in cell B1-S1-C1")
        
        # Test 1: Get cargo information from specific warehouse cell
        print(f"\n   📍 Testing: Get Cargo in Cell")
        location_code = "B1-S1-C1"
        success, cell_cargo = self.run_test(
            "Get Cargo in Warehouse Cell",
            "GET",
            f"/api/warehouse/{self.warehouse_id}/cell/{location_code}/cargo",
            200,
            None,
            self.tokens['warehouse_operator']
        )
        
        if success and cell_cargo:
            if cell_cargo.get('id') == cargo_id:
                print(f"   ✅ Correct cargo found in cell: {cell_cargo.get('cargo_number')}")
            else:
                print(f"   ❌ Wrong cargo found in cell")
                all_success = False
        else:
            all_success = False
        
        # Test 2: Get comprehensive cargo details
        print(f"\n   📋 Testing: Get Cargo Details")
        success, cargo_details = self.run_test(
            "Get Comprehensive Cargo Details",
            "GET",
            f"/api/cargo/{cargo_id}/details",
            200,
            None,
            self.tokens['warehouse_operator']
        )
        
        if success and cargo_details:
            expected_fields = ['cargo_number', 'sender_full_name', 'recipient_full_name', 'weight']
            missing_fields = [field for field in expected_fields if field not in cargo_details]
            if not missing_fields:
                print(f"   ✅ All expected fields present in cargo details")
            else:
                print(f"   ⚠️ Missing fields: {missing_fields}")
        else:
            all_success = False
        
        # Test 3: Update cargo details
        print(f"\n   ✏️ Testing: Update Cargo Details")
        update_data = {
            "cargo_name": "Обновленное Название",
            "description": "Обновленное описание",
            "weight": 5.5,
            "declared_value": 2750.0
        }
        
        success, _ = self.run_test(
            "Update Cargo Details",
            "PUT",
            f"/api/cargo/{cargo_id}/update",
            200,
            update_data,
            self.tokens['warehouse_operator']
        )
        
        if success:
            # Verify update
            success, updated_cargo = self.run_test(
                "Verify Cargo Update",
                "GET",
                f"/api/cargo/{cargo_id}/details",
                200,
                None,
                self.tokens['warehouse_operator']
            )
            
            if success and updated_cargo:
                if updated_cargo.get('cargo_name') == update_data['cargo_name']:
                    print(f"   ✅ Cargo name updated successfully")
                else:
                    print(f"   ❌ Cargo name not updated")
                    all_success = False
                
                if 'updated_by_operator' in updated_cargo:
                    print(f"   ✅ Operator tracking added")
                else:
                    print(f"   ❌ Operator tracking missing")
                    all_success = False
        else:
            all_success = False
        
        # Test 4: Move cargo between cells
        print(f"\n   🔄 Testing: Move Cargo Between Cells")
        new_location = {
            "warehouse_id": self.warehouse_id,
            "block_number": 1,
            "shelf_number": 2,
            "cell_number": 1
        }
        
        success, move_response = self.run_test(
            "Move Cargo to Different Cell",
            "POST",
            f"/api/warehouse/cargo/{cargo_id}/move",
            200,
            new_location,
            self.tokens['warehouse_operator']
        )
        
        if success and move_response:
            new_location_code = move_response.get('new_location')
            print(f"   ✅ Cargo moved to: {new_location_code}")
            
            # Verify old cell is empty
            success, _ = self.run_test(
                "Verify Old Cell is Empty",
                "GET",
                f"/api/warehouse/{self.warehouse_id}/cell/B1-S1-C1/cargo",
                404,
                None,
                self.tokens['warehouse_operator']
            )
            
            if success:
                print(f"   ✅ Old cell is now empty")
            else:
                print(f"   ❌ Old cell still occupied")
                all_success = False
            
            # Verify cargo in new cell
            success, new_cell_cargo = self.run_test(
                "Verify Cargo in New Cell",
                "GET",
                f"/api/warehouse/{self.warehouse_id}/cell/{new_location_code}/cargo",
                200,
                None,
                self.tokens['warehouse_operator']
            )
            
            if success and new_cell_cargo and new_cell_cargo.get('id') == cargo_id:
                print(f"   ✅ Cargo found in new cell")
            else:
                print(f"   ❌ Cargo not found in new cell")
                all_success = False
        else:
            all_success = False
        
        # Test 5: Remove cargo from cell
        print(f"\n   🗑️ Testing: Remove Cargo from Cell")
        success, _ = self.run_test(
            "Remove Cargo from Cell",
            "DELETE",
            f"/api/warehouse/cargo/{cargo_id}/remove",
            200,
            None,
            self.tokens['warehouse_operator']
        )
        
        if success:
            # Verify cell is empty
            success, _ = self.run_test(
                "Verify Cell is Empty After Removal",
                "GET",
                f"/api/warehouse/{self.warehouse_id}/cell/B1-S2-C1/cargo",
                404,
                None,
                self.tokens['warehouse_operator']
            )
            
            if success:
                print(f"   ✅ Cell is empty after removal")
            else:
                print(f"   ❌ Cell still occupied after removal")
                all_success = False
            
            # Verify cargo status reset
            success, removed_cargo = self.run_test(
                "Verify Cargo Status After Removal",
                "GET",
                f"/api/cargo/{cargo_id}/details",
                200,
                None,
                self.tokens['warehouse_operator']
            )
            
            if success and removed_cargo:
                if removed_cargo.get('status') == 'accepted':
                    print(f"   ✅ Cargo status reset to 'accepted'")
                else:
                    print(f"   ❌ Cargo status not reset: {removed_cargo.get('status')}")
                    all_success = False
                
                if not removed_cargo.get('warehouse_location'):
                    print(f"   ✅ Warehouse location cleared")
                else:
                    print(f"   ❌ Warehouse location not cleared")
                    all_success = False
        else:
            all_success = False
        
        return all_success

    def test_automatic_cell_liberation(self):
        """Test automatic cell liberation when cargo is placed on transport"""
        print("\n🚛 TESTING AUTOMATIC CELL LIBERATION")
        all_success = True
        
        # First create operator-warehouse binding
        binding_data = {
            "operator_id": self.users['warehouse_operator']['id'],
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
            print(f"   ✅ Operator-warehouse binding created")
        else:
            print(f"   ⚠️ Binding may already exist, continuing...")
        
        # Create cargo for liberation test
        liberation_cargo_data = {
            "sender_full_name": "Освобождение Отправитель",
            "sender_phone": "+79555666777",
            "recipient_full_name": "Освобождение Получатель",
            "recipient_phone": "+992888999000",
            "recipient_address": "Душанбе, ул. Освобождения, 25",
            "weight": 4.0,
            "cargo_name": "Груз для Освобождения",
            "declared_value": 2000.0,
            "description": "Груз для тестирования автоматического освобождения ячеек",
            "route": "moscow_to_tajikistan"
        }
        
        success, liberation_cargo_response = self.run_test(
            "Create Cargo for Liberation Test",
            "POST",
            "/api/operator/cargo/accept",
            200,
            liberation_cargo_data,
            self.tokens['warehouse_operator']
        )
        
        if not success or 'id' not in liberation_cargo_response:
            print("   ❌ Failed to create cargo for liberation test")
            return False
        
        liberation_cargo_id = liberation_cargo_response['id']
        liberation_cargo_number = liberation_cargo_response['cargo_number']
        print(f"   📦 Created liberation cargo: {liberation_cargo_number}")
        
        # Place cargo in warehouse cell
        liberation_placement_data = {
            "cargo_id": liberation_cargo_id,
            "warehouse_id": self.warehouse_id,
            "block_number": 2,
            "shelf_number": 1,
            "cell_number": 1
        }
        
        success, _ = self.run_test(
            "Place Cargo for Liberation Test",
            "POST",
            "/api/operator/cargo/place",
            200,
            liberation_placement_data,
            self.tokens['warehouse_operator']
        )
        
        if not success:
            print("   ❌ Failed to place cargo for liberation test")
            return False
        
        print(f"   ✅ Cargo placed in cell B2-S1-C1")
        
        # Verify cargo is in cell
        success, cell_cargo = self.run_test(
            "Verify Cargo is in Cell Before Transport",
            "GET",
            f"/api/warehouse/{self.warehouse_id}/cell/B2-S1-C1/cargo",
            200,
            None,
            self.tokens['warehouse_operator']
        )
        
        if success and cell_cargo and cell_cargo.get('id') == liberation_cargo_id:
            print(f"   ✅ Cargo confirmed in cell before transport")
        else:
            print(f"   ❌ Cargo not found in expected cell")
            return False
        
        # Create transport
        import time
        unique_suffix = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        transport_data = {
            "driver_name": "Водитель Освобождения",
            "driver_phone": "+79111222333",
            "transport_number": f"LIB{unique_suffix}",
            "capacity_kg": 1000.0,
            "direction": "Москва → Душанбе"
        }
        
        success, transport_response = self.run_test(
            "Create Transport for Liberation Test",
            "POST",
            "/api/transport/create",
            200,
            transport_data,
            self.tokens['admin']
        )
        
        if not success or 'transport_id' not in transport_response:
            print("   ❌ Failed to create transport for liberation test")
            return False
        
        liberation_transport_id = transport_response['transport_id']
        print(f"   🚛 Created transport: {liberation_transport_id}")
        
        # Place cargo on transport (should automatically free cell)
        transport_placement_data = {
            "transport_id": liberation_transport_id,
            "cargo_numbers": [liberation_cargo_number]
        }
        
        success, placement_response = self.run_test(
            "Place Cargo on Transport (Should Free Cell)",
            "POST",
            f"/api/transport/{liberation_transport_id}/place-cargo",
            200,
            transport_placement_data,
            self.tokens['warehouse_operator']
        )
        
        if success:
            print(f"   ✅ Cargo placed on transport successfully")
            
            # Test automatic cell liberation
            success, _ = self.run_test(
                "Verify Cell is Automatically Freed",
                "GET",
                f"/api/warehouse/{self.warehouse_id}/cell/B2-S1-C1/cargo",
                404,
                None,
                self.tokens['warehouse_operator']
            )
            
            if success:
                print(f"   ✅ Warehouse cell automatically freed")
            else:
                print(f"   ❌ Warehouse cell not automatically freed")
                all_success = False
            
            # Verify cargo location fields are cleared
            success, cargo_after_transport = self.run_test(
                "Verify Cargo Location Cleared",
                "GET",
                f"/api/cargo/{liberation_cargo_id}/details",
                200,
                None,
                self.tokens['warehouse_operator']
            )
            
            if success and cargo_after_transport:
                if not cargo_after_transport.get('warehouse_location'):
                    print(f"   ✅ Cargo warehouse_location cleared")
                else:
                    print(f"   ❌ Cargo warehouse_location not cleared")
                    all_success = False
                
                if cargo_after_transport.get('status') == 'in_transit':
                    print(f"   ✅ Cargo status updated to 'in_transit'")
                else:
                    print(f"   ❌ Cargo status not updated: {cargo_after_transport.get('status')}")
                    all_success = False
        else:
            all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all warehouse cell management tests"""
        print("🚀 Starting warehouse cell management testing...")
        
        # Setup
        if not self.setup_authentication():
            return 1
        
        if not self.setup_warehouse():
            return 1
        
        # Run tests
        test_results = []
        
        test_suites = [
            ("Warehouse Cell Management Endpoints", self.test_warehouse_cell_endpoints),
            ("Automatic Cell Liberation", self.test_automatic_cell_liberation)
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
        
        # Print results
        print("\n" + "=" * 60)
        print("📊 WAREHOUSE CELL MANAGEMENT TEST RESULTS")
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
            print("\n🎉 ALL WAREHOUSE CELL MANAGEMENT TESTS PASSED!")
            return 0
        else:
            print(f"\n⚠️ {total_suites - passed_suites} test suite(s) failed.")
            return 1

def main():
    """Main test execution"""
    tester = WarehouseCellTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())