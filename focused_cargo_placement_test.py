#!/usr/bin/env python3
"""
Focused test for Enhanced Cargo Placement System with Cargo Number-based Selection
Tests the specific functionality requested in the review
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
import random

class EnhancedCargoPlacementTester:
    def __init__(self, base_url="https://qr-logistics-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🔢 Enhanced Cargo Placement System Tester")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

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
        
        # Login as different users
        login_data = [
            {"role": "user", "phone": "+79123456789", "password": "123456"},
            {"role": "admin", "phone": "+79999888777", "password": "admin123"},
            {"role": "warehouse_operator", "phone": "+79777888999", "password": "warehouse123"}
        ]
        
        for login_info in login_data:
            success, response = self.run_test(
                f"Login {login_info['role']}", 
                "POST", 
                "/api/auth/login", 
                200,
                {"phone": login_info['phone'], "password": login_info['password']}
            )
            
            if success and 'access_token' in response:
                self.tokens[login_info['role']] = response['access_token']
                self.users[login_info['role']] = response['user']
                print(f"   🔑 Token stored for {login_info['role']}")
            else:
                print(f"   ❌ Failed to login as {login_info['role']}")
                return False
        
        return True

    def test_enhanced_cargo_placement_by_numbers(self):
        """Test enhanced cargo placement system with cargo number-based selection"""
        print("\n🔢 ENHANCED CARGO PLACEMENT BY NUMBERS")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Step 1: Create a unique transport for testing
        print("\n   🚛 Creating Transport for Placement Test...")
        transport_number = f"CARGO{random.randint(1000, 9999)}"
        transport_data = {
            "driver_name": "Тестовый Водитель Размещения",
            "driver_phone": "+79123456789",
            "transport_number": transport_number,
            "capacity_kg": 1000.0,
            "direction": "Москва - Душанбе"
        }
        
        success, transport_response = self.run_test(
            "Create Transport for Placement Test",
            "POST",
            "/api/transport/create",
            200,
            transport_data,
            self.tokens['admin']
        )
        
        if not success or 'transport_id' not in transport_response:
            print("   ❌ Failed to create transport for placement test")
            return False
        
        transport_id = transport_response['transport_id']
        print(f"   🚛 Created transport: {transport_id}")
        
        # Step 2: Create cargo in different collections
        print("\n   📦 Creating Test Cargo in Different Collections...")
        test_cargo_numbers = []
        
        # Create user cargo
        user_cargo_data = {
            "recipient_name": "Получатель Пользователя",
            "recipient_phone": "+992444555666",
            "route": "moscow_to_tajikistan",
            "weight": 50.0,
            "description": "Пользовательский груз для транспорта",
            "declared_value": 8000.0,
            "sender_address": "Москва, ул. Пользователя, 1",
            "recipient_address": "Душанбе, ул. Получателя, 1"
        }
        
        success, user_cargo_response = self.run_test(
            "Create User Cargo for Transport",
            "POST",
            "/api/cargo/create",
            200,
            user_cargo_data,
            self.tokens['user']
        )
        
        if success and 'cargo_number' in user_cargo_response:
            user_cargo_number = user_cargo_response['cargo_number']
            user_cargo_id = user_cargo_response['id']
            test_cargo_numbers.append(user_cargo_number)
            print(f"   📋 Created user cargo: {user_cargo_number}")
            
            # Update status to accepted with warehouse location
            success, _ = self.run_test(
                "Update User Cargo Status",
                "PUT",
                f"/api/cargo/{user_cargo_id}/status",
                200,
                token=self.tokens['admin'],
                params={"status": "accepted", "warehouse_location": "Склад А, Стеллаж 1"}
            )
            all_success &= success
        
        # Create operator cargo
        operator_cargo_data = {
            "sender_full_name": "Отправитель Оператора",
            "sender_phone": "+79111222333",
            "recipient_full_name": "Получатель Оператора",
            "recipient_phone": "+992777888999",
            "recipient_address": "Душанбе, ул. Операторская, 25",
            "weight": 75.0,
            "declared_value": 12000.0,
            "description": "Операторский груз для транспорта",
            "route": "moscow_to_tajikistan"
        }
        
        success, operator_cargo_response = self.run_test(
            "Create Operator Cargo for Transport",
            "POST",
            "/api/operator/cargo/accept",
            200,
            operator_cargo_data,
            self.tokens['admin']
        )
        
        if success and 'cargo_number' in operator_cargo_response:
            operator_cargo_number = operator_cargo_response['cargo_number']
            test_cargo_numbers.append(operator_cargo_number)
            print(f"   📋 Created operator cargo: {operator_cargo_number}")
            
            # Get available warehouses to place cargo
            success, warehouses = self.run_test(
                "Get Warehouses for Cargo Placement",
                "GET",
                "/api/warehouses",
                200,
                token=self.tokens['admin']
            )
            
            if success and warehouses:
                warehouse_id = warehouses[0]['id']
                placement_data = {
                    "cargo_id": operator_cargo_response['id'],
                    "warehouse_id": warehouse_id,
                    "block_number": 1,
                    "shelf_number": 1,
                    "cell_number": 1
                }
                
                success, _ = self.run_test(
                    "Place Operator Cargo in Warehouse",
                    "POST",
                    "/api/operator/cargo/place",
                    200,
                    placement_data,
                    self.tokens['admin']
                )
                all_success &= success
        
        # Step 3: Test cargo placement by numbers from multiple collections
        print("\n   🚛 Testing Cargo Placement by Numbers...")
        if test_cargo_numbers:
            placement_data = {
                "transport_id": transport_id,
                "cargo_numbers": test_cargo_numbers
            }
            
            success, placement_response = self.run_test(
                "Place Cargo by Numbers on Transport",
                "POST",
                f"/api/transport/{transport_id}/place-cargo",
                200,
                placement_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                cargo_count = placement_response.get('cargo_count', 0)
                total_weight = placement_response.get('total_weight', 0)
                placed_numbers = placement_response.get('cargo_numbers', [])
                
                print(f"   ✅ Successfully placed {cargo_count} cargo items")
                print(f"   ⚖️  Total weight: {total_weight}kg")
                print(f"   📋 Placed cargo numbers: {placed_numbers}")
                
                # Verify all requested cargo was placed
                if set(placed_numbers) == set(test_cargo_numbers):
                    print(f"   ✅ All requested cargo numbers were placed")
                else:
                    print(f"   ❌ Mismatch in placed cargo numbers")
                    all_success = False
        
        # Step 4: Test weight calculation and capacity validation
        print("\n   ⚖️  Testing Weight Calculation and Capacity Validation...")
        
        # Create heavy cargo that would exceed capacity
        heavy_cargo_data = {
            "sender_full_name": "Тяжелый Отправитель",
            "sender_phone": "+79555666777",
            "recipient_full_name": "Тяжелый Получатель",
            "recipient_phone": "+992888999000",
            "recipient_address": "Душанбе, ул. Тяжелая, 1",
            "weight": 2000.0,  # Very heavy cargo
            "declared_value": 50000.0,
            "description": "Очень тяжелый груз для тестирования лимитов",
            "route": "moscow_to_tajikistan"
        }
        
        success, heavy_cargo_response = self.run_test(
            "Create Heavy Cargo for Capacity Test",
            "POST",
            "/api/operator/cargo/accept",
            200,
            heavy_cargo_data,
            self.tokens['admin']
        )
        
        if success and 'cargo_number' in heavy_cargo_response:
            heavy_cargo_number = heavy_cargo_response['cargo_number']
            print(f"   📦 Created heavy cargo: {heavy_cargo_number}")
            
            # Place in warehouse
            success, warehouses = self.run_test(
                "Get Warehouses for Heavy Cargo",
                "GET",
                "/api/warehouses",
                200,
                token=self.tokens['admin']
            )
            
            if success and warehouses:
                warehouse_id = warehouses[0]['id']
                placement_data = {
                    "cargo_id": heavy_cargo_response['id'],
                    "warehouse_id": warehouse_id,
                    "block_number": 1,
                    "shelf_number": 2,
                    "cell_number": 1
                }
                
                success, _ = self.run_test(
                    "Place Heavy Cargo in Warehouse",
                    "POST",
                    "/api/operator/cargo/place",
                    200,
                    placement_data,
                    self.tokens['admin']
                )
                
                if success:
                    # Try to place heavy cargo on transport (should fail due to capacity)
                    heavy_placement_data = {
                        "transport_id": transport_id,
                        "cargo_numbers": [heavy_cargo_number]
                    }
                    
                    success, _ = self.run_test(
                        "Place Heavy Cargo (Should Exceed Capacity)",
                        "POST",
                        f"/api/transport/{transport_id}/place-cargo",
                        400,  # Expecting capacity exceeded error
                        heavy_placement_data,
                        self.tokens['admin']
                    )
                    all_success &= success
                    
                    if success:
                        print(f"   ✅ Capacity validation working correctly")
        
        # Step 5: Test error handling for non-existent cargo numbers
        print("\n   ❌ Testing Error Handling for Non-existent Cargo...")
        invalid_placement_data = {
            "transport_id": transport_id,
            "cargo_numbers": ["9999", "8888", "7777"]  # Non-existent numbers
        }
        
        success, _ = self.run_test(
            "Place Non-existent Cargo (Should Fail)",
            "POST",
            f"/api/transport/{transport_id}/place-cargo",
            404,  # Expecting cargo not found error
            invalid_placement_data,
            self.tokens['admin']
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Error handling for non-existent cargo working correctly")
        
        return all_success

    def test_cross_warehouse_cargo_access(self):
        """Test cross-warehouse cargo access and placement"""
        print("\n🏭 CROSS-WAREHOUSE CARGO ACCESS")
        
        if 'admin' not in self.tokens or 'warehouse_operator' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # Test 1: Admin can see cargo from all warehouses
        print("\n   👑 Testing Admin Access to All Warehouse Cargo...")
        success, admin_available_cargo = self.run_test(
            "Get Available Cargo for Transport (Admin)",
            "GET",
            "/api/transport/available-cargo",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success:
            cargo_count = len(admin_available_cargo) if isinstance(admin_available_cargo, list) else 0
            print(f"   📦 Admin can see {cargo_count} available cargo items from all warehouses")
            
            # Check if cargo from different collections is included
            user_cargo_count = len([c for c in admin_available_cargo if 'sender_id' in c])
            operator_cargo_count = len([c for c in admin_available_cargo if 'created_by' in c and 'sender_id' not in c])
            
            print(f"   👤 User cargo items: {user_cargo_count}")
            print(f"   🏭 Operator cargo items: {operator_cargo_count}")
        
        # Test 2: Operator can only see cargo from assigned warehouses
        print("\n   🔒 Testing Operator Access to Assigned Warehouse Cargo...")
        success, operator_available_cargo = self.run_test(
            "Get Available Cargo for Transport (Operator)",
            "GET",
            "/api/transport/available-cargo",
            200,
            token=self.tokens['warehouse_operator']
        )
        all_success &= success
        
        if success:
            operator_cargo_count = len(operator_available_cargo) if isinstance(operator_available_cargo, list) else 0
            print(f"   📦 Operator can see {operator_cargo_count} available cargo items from assigned warehouses")
            
            # Operator should see fewer or equal cargo items compared to admin
            admin_cargo_count = len(admin_available_cargo) if isinstance(admin_available_cargo, list) else 0
            if operator_cargo_count <= admin_cargo_count:
                print(f"   ✅ Operator access control working correctly")
            else:
                print(f"   ❌ Operator sees more cargo than admin (unexpected)")
                all_success = False
        
        # Test 3: Regular user access should be denied
        print("\n   🚫 Testing Regular User Access (Should be Denied)...")
        success, _ = self.run_test(
            "Get Available Cargo for Transport (User - Should Fail)",
            "GET",
            "/api/transport/available-cargo",
            403,  # Expecting access denied
            token=self.tokens['user']
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Regular user access properly denied")
        
        return all_success

    def test_operator_warehouse_binding_integration(self):
        """Test integration with operator-warehouse binding system"""
        print("\n🔗 OPERATOR-WAREHOUSE BINDING INTEGRATION")
        
        if 'admin' not in self.tokens or 'warehouse_operator' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # Test 1: Get operator's assigned warehouses
        print("\n   🏭 Testing Operator's Assigned Warehouses...")
        success, operator_warehouses = self.run_test(
            "Get Operator's Assigned Warehouses",
            "GET",
            "/api/operator/my-warehouses",
            200,
            token=self.tokens['warehouse_operator']
        )
        all_success &= success
        
        if success:
            warehouse_count = len(operator_warehouses) if isinstance(operator_warehouses, list) else 0
            print(f"   🏭 Operator has access to {warehouse_count} warehouses")
            
            if warehouse_count > 0:
                assigned_warehouse_ids = [w.get('id') for w in operator_warehouses]
                print(f"   📋 Assigned warehouse IDs: {assigned_warehouse_ids}")
        
        # Test 2: Test that admin can access cargo from any warehouse
        print("\n   👑 Testing Admin Universal Access...")
        success, admin_available_cargo = self.run_test(
            "Get Available Cargo (Admin Universal Access)",
            "GET",
            "/api/transport/available-cargo",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success:
            admin_cargo_count = len(admin_available_cargo) if isinstance(admin_available_cargo, list) else 0
            print(f"   📦 Admin can access {admin_cargo_count} cargo items from all warehouses")
            
            # Check warehouse diversity
            if isinstance(admin_available_cargo, list):
                warehouse_ids = set()
                for cargo in admin_available_cargo:
                    if cargo.get('warehouse_id'):
                        warehouse_ids.add(cargo['warehouse_id'])
                
                print(f"   🏭 Cargo from {len(warehouse_ids)} different warehouses")
        
        return all_success

    def run_focused_tests(self):
        """Run focused tests for enhanced cargo placement system"""
        print("🚀 Starting focused enhanced cargo placement testing...")
        
        # Setup authentication
        if not self.setup_authentication():
            print("❌ Failed to setup authentication")
            return False
        
        test_results = []
        
        # Run focused test suites
        test_suites = [
            ("Enhanced Cargo Placement by Numbers", self.test_enhanced_cargo_placement_by_numbers),
            ("Cross-Warehouse Cargo Access", self.test_cross_warehouse_cargo_access),
            ("Operator-Warehouse Binding Integration", self.test_operator_warehouse_binding_integration)
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
        print("📊 FOCUSED TEST RESULTS")
        print("=" * 60)
        
        passed_suites = sum(1 for _, result in test_results if result)
        total_suites = len(test_results)
        
        for suite_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {suite_name}")
        
        print(f"\n📈 Overall Results:")
        print(f"   Test Suites: {passed_suites}/{total_suites} passed")
        print(f"   Individual Tests: {self.tests_passed}/{self.tests_run} passed")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if passed_suites == total_suites:
            print("\n🎉 ALL FOCUSED TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  {total_suites - passed_suites} test suite(s) failed.")
            return False

if __name__ == "__main__":
    tester = EnhancedCargoPlacementTester()
    success = tester.run_focused_tests()
    sys.exit(0 if success else 1)