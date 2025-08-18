#!/usr/bin/env python3
"""
Cargo Name Field Integration Testing
Tests the fixed cargo system with optional cargo_name field focusing on:
1. Cargo Creation Compatibility (with and without cargo_name field)
2. Search System Verification 
3. Automatic Warehouse Placement
4. Backward compatibility verification
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class CargoNameTester:
    def __init__(self, base_url="https://cargo-talk.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🏷️ CARGO NAME FIELD INTEGRATION TESTER")
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
        """Setup authentication tokens for testing"""
        print("\n🔐 SETTING UP AUTHENTICATION")
        
        # Login as different users
        login_data = [
            {"role": "user", "phone": "+79123456789", "password": "123456"},
            {"role": "admin", "phone": "+79999888777", "password": "admin123"},
            {"role": "warehouse_operator", "phone": "+79777888999", "password": "warehouse123"}
        ]
        
        all_success = True
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
            else:
                all_success = False
                
        return all_success

    def test_cargo_creation_without_cargo_name(self):
        """Test cargo creation without cargo_name field (backward compatibility)"""
        print("\n📦 CARGO CREATION WITHOUT CARGO_NAME (BACKWARD COMPATIBILITY)")
        
        if 'user' not in self.tokens:
            print("   ❌ No user token available")
            return False
            
        all_success = True
        
        # Test 1: User cargo creation without cargo_name
        cargo_data_no_name = {
            "recipient_name": "Получатель Без Названия",
            "recipient_phone": "+992111222333", 
            "route": "moscow_to_tajikistan",
            "weight": 15.5,
            # No cargo_name field
            "description": "Документы и личные вещи без названия груза",
            "declared_value": 8000.0,
            "sender_address": "Москва, ул. Тестовая, 1",
            "recipient_address": "Душанбе, ул. Получателя, 1"
        }
        
        success, response = self.run_test(
            "User Cargo Creation WITHOUT cargo_name",
            "POST", 
            "/api/cargo/create",
            200,
            cargo_data_no_name,
            self.tokens['user']
        )
        all_success &= success
        
        if success:
            cargo_name = response.get('cargo_name')
            print(f"   🏷️  Generated cargo_name: {cargo_name}")
            if cargo_name:
                print(f"   ✅ System automatically generated cargo_name from description")
            else:
                print(f"   ❌ No cargo_name generated")
                all_success = False
        
        # Test 2: Operator cargo creation without cargo_name
        operator_cargo_data_no_name = {
            "sender_full_name": "Отправитель Оператор Без Названия",
            "sender_phone": "+79111222333",
            "recipient_full_name": "Получатель Оператор Без Названия",
            "recipient_phone": "+992444555666",
            "recipient_address": "Душанбе, ул. Операторская, 25",
            "weight": 20.0,
            # No cargo_name field
            "declared_value": 12000.0,
            "description": "Груз оператора без названия",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Operator Cargo Creation WITHOUT cargo_name",
            "POST",
            "/api/operator/cargo/accept",
            200,
            operator_cargo_data_no_name,
            self.tokens['admin']
        )
        all_success &= success
        
        if success:
            cargo_name = response.get('cargo_name')
            print(f"   🏷️  Generated cargo_name: {cargo_name}")
            if cargo_name:
                print(f"   ✅ System automatically generated cargo_name from description")
            else:
                print(f"   ❌ No cargo_name generated")
                all_success = False
        
        # Test 3: Cargo request without cargo_name (this should fail as cargo_name is required in requests)
        request_data_no_name = {
            "recipient_full_name": "Получатель Заявки Без Названия",
            "recipient_phone": "+992555666777",
            "recipient_address": "Душанбе, ул. Заявочная, 1",
            "pickup_address": "Москва, ул. Забора, 1",
            # No cargo_name field - this is required in CargoRequestCreate
            "weight": 10.0,
            "declared_value": 5000.0,
            "description": "Заявка без названия груза",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Cargo Request WITHOUT cargo_name (Should Fail)",
            "POST",
            "/api/user/cargo-request",
            422,  # Expecting validation error
            request_data_no_name,
            self.tokens['user']
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Cargo request correctly failed without cargo_name (as expected)")
        
        return all_success

    def test_cargo_creation_with_cargo_name(self):
        """Test cargo creation with cargo_name field"""
        print("\n📦 CARGO CREATION WITH CARGO_NAME")
        
        if 'user' not in self.tokens:
            print("   ❌ No user token available")
            return False
            
        all_success = True
        
        # Test 1: User cargo creation with cargo_name
        cargo_data_with_name = {
            "recipient_name": "Получатель С Названием",
            "recipient_phone": "+992111222444", 
            "route": "moscow_to_tajikistan",
            "weight": 25.0,
            "cargo_name": "Электроника и документы",  # Explicit cargo_name
            "description": "Подробное описание груза с электроникой",
            "declared_value": 15000.0,
            "sender_address": "Москва, ул. Электронная, 5",
            "recipient_address": "Душанбе, ул. Получателя, 5"
        }
        
        success, response = self.run_test(
            "User Cargo Creation WITH cargo_name",
            "POST", 
            "/api/cargo/create",
            200,
            cargo_data_with_name,
            self.tokens['user']
        )
        all_success &= success
        
        if success:
            cargo_name = response.get('cargo_name')
            expected_name = cargo_data_with_name['cargo_name']
            print(f"   🏷️  Expected: {expected_name}")
            print(f"   🏷️  Received: {cargo_name}")
            if cargo_name == expected_name:
                print(f"   ✅ Cargo name correctly preserved")
            else:
                print(f"   ❌ Cargo name not preserved correctly")
                all_success = False
        
        # Test 2: Operator cargo creation with cargo_name
        operator_cargo_data_with_name = {
            "sender_full_name": "Отправитель Оператор С Названием",
            "sender_phone": "+79111222444",
            "recipient_full_name": "Получатель Оператор С Названием",
            "recipient_phone": "+992444555777",
            "recipient_address": "Душанбе, ул. Операторская, 30",
            "weight": 18.5,
            "cargo_name": "Медицинские препараты",  # Explicit cargo_name
            "declared_value": 20000.0,
            "description": "Медицинские препараты для больницы",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Operator Cargo Creation WITH cargo_name",
            "POST",
            "/api/operator/cargo/accept",
            200,
            operator_cargo_data_with_name,
            self.tokens['admin']
        )
        all_success &= success
        
        if success:
            cargo_name = response.get('cargo_name')
            expected_name = operator_cargo_data_with_name['cargo_name']
            print(f"   🏷️  Expected: {expected_name}")
            print(f"   🏷️  Received: {cargo_name}")
            if cargo_name == expected_name:
                print(f"   ✅ Cargo name correctly preserved")
            else:
                print(f"   ❌ Cargo name not preserved correctly")
                all_success = False
        
        # Test 3: Cargo request with cargo_name
        request_data_with_name = {
            "recipient_full_name": "Получатель Заявки С Названием",
            "recipient_phone": "+992555666888",
            "recipient_address": "Душанбе, ул. Заявочная, 10",
            "pickup_address": "Москва, ул. Забора, 10",
            "cargo_name": "Строительные материалы",  # Required field
            "weight": 50.0,
            "declared_value": 25000.0,
            "description": "Строительные материалы для ремонта",
            "route": "moscow_to_tajikistan"
        }
        
        success, response = self.run_test(
            "Cargo Request WITH cargo_name",
            "POST",
            "/api/user/cargo-request",
            200,
            request_data_with_name,
            self.tokens['user']
        )
        all_success &= success
        
        request_id = None
        if success:
            request_id = response.get('id')
            cargo_name = response.get('cargo_name')
            expected_name = request_data_with_name['cargo_name']
            print(f"   🏷️  Expected: {expected_name}")
            print(f"   🏷️  Received: {cargo_name}")
            if cargo_name == expected_name:
                print(f"   ✅ Cargo name correctly preserved in request")
            else:
                print(f"   ❌ Cargo name not preserved correctly in request")
                all_success = False
        
        # Test 4: Accept cargo request and verify cargo_name is preserved
        if request_id:
            success, accept_response = self.run_test(
                "Accept Cargo Request and Verify cargo_name",
                "POST",
                f"/api/admin/cargo-requests/{request_id}/accept",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success:
                cargo_number = accept_response.get('cargo_number')
                print(f"   📦 Created cargo: {cargo_number}")
                
                # Get the created cargo to verify cargo_name
                success, cargo_list = self.run_test(
                    "Get Operator Cargo List to Verify cargo_name",
                    "GET",
                    "/api/operator/cargo/list",
                    200,
                    token=self.tokens['admin']
                )
                
                if success and isinstance(cargo_list, list):
                    created_cargo = next((c for c in cargo_list if c.get('cargo_number') == cargo_number), None)
                    if created_cargo:
                        cargo_name = created_cargo.get('cargo_name')
                        expected_name = request_data_with_name['cargo_name']
                        print(f"   🏷️  Expected in created cargo: {expected_name}")
                        print(f"   🏷️  Received in created cargo: {cargo_name}")
                        if cargo_name == expected_name:
                            print(f"   ✅ Cargo name preserved when accepting request")
                        else:
                            print(f"   ❌ Cargo name not preserved when accepting request")
                            all_success = False
        
        return all_success

    def test_cargo_listings_compatibility(self):
        """Test that existing cargo listings work without errors"""
        print("\n📋 CARGO LISTINGS COMPATIBILITY")
        
        if 'user' not in self.tokens or 'admin' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # Test 1: User's cargo list
        success, user_cargo = self.run_test(
            "Get User's Cargo List",
            "GET",
            "/api/cargo/my",
            200,
            token=self.tokens['user']
        )
        all_success &= success
        
        if success:
            cargo_count = len(user_cargo) if isinstance(user_cargo, list) else 0
            print(f"   📦 Found {cargo_count} user cargo items")
            
            # Check if any cargo has cargo_name field
            if isinstance(user_cargo, list) and user_cargo:
                with_name = sum(1 for c in user_cargo if c.get('cargo_name'))
                without_name = cargo_count - with_name
                print(f"   🏷️  With cargo_name: {with_name}")
                print(f"   📝 Without cargo_name: {without_name}")
        
        # Test 2: Admin's all cargo list
        success, all_cargo = self.run_test(
            "Get All Cargo List (Admin)",
            "GET",
            "/api/cargo/all",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success:
            cargo_count = len(all_cargo) if isinstance(all_cargo, list) else 0
            print(f"   📦 Found {cargo_count} total cargo items")
        
        # Test 3: Operator cargo list
        success, operator_cargo = self.run_test(
            "Get Operator Cargo List",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success:
            cargo_count = len(operator_cargo) if isinstance(operator_cargo, list) else 0
            print(f"   📦 Found {cargo_count} operator cargo items")
            
            # Check cargo_name field presence
            if isinstance(operator_cargo, list) and operator_cargo:
                with_name = sum(1 for c in operator_cargo if c.get('cargo_name'))
                without_name = cargo_count - with_name
                print(f"   🏷️  With cargo_name: {with_name}")
                print(f"   📝 Without cargo_name: {without_name}")
        
        # Test 4: Warehouse cargo list
        if 'warehouse_operator' in self.tokens:
            success, warehouse_cargo = self.run_test(
                "Get Warehouse Cargo List",
                "GET",
                "/api/warehouse/cargo",
                200,
                token=self.tokens['warehouse_operator']
            )
            all_success &= success
            
            if success:
                cargo_count = len(warehouse_cargo) if isinstance(warehouse_cargo, list) else 0
                print(f"   📦 Found {cargo_count} warehouse cargo items")
        
        return all_success

    def test_search_system_with_cargo_name(self):
        """Test search functionality with cargo_name field"""
        print("\n🔍 SEARCH SYSTEM WITH CARGO_NAME")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # First create some cargo with specific cargo_name for testing
        test_cargo_data = {
            "sender_full_name": "Тестовый Отправитель Поиска",
            "sender_phone": "+79111222555",
            "recipient_full_name": "Тестовый Получатель Поиска",
            "recipient_phone": "+992444555888",
            "recipient_address": "Душанбе, ул. Поисковая, 1",
            "weight": 5.0,
            "cargo_name": "Уникальное Название Для Поиска",  # Unique name for search
            "declared_value": 3000.0,
            "description": "Тестовый груз для проверки поиска",
            "route": "moscow_to_tajikistan"
        }
        
        success, cargo_response = self.run_test(
            "Create Test Cargo for Search",
            "POST",
            "/api/operator/cargo/accept",
            200,
            test_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        test_cargo_number = None
        if success:
            test_cargo_number = cargo_response.get('cargo_number')
            print(f"   📦 Created test cargo: {test_cargo_number}")
        
        # Test 1: Advanced cargo search by cargo_name
        success, search_results = self.run_test(
            "Search Cargo by cargo_name",
            "GET",
            "/api/cargo/search",
            200,
            token=self.tokens['admin'],
            params={"query": "Уникальное Название", "search_type": "cargo_name"}
        )
        all_success &= success
        
        if success:
            result_count = len(search_results) if isinstance(search_results, list) else 0
            print(f"   🔍 Found {result_count} results for cargo_name search")
            
            # Verify our test cargo is in results
            if isinstance(search_results, list) and test_cargo_number:
                found_cargo = any(c.get('cargo_number') == test_cargo_number for c in search_results)
                if found_cargo:
                    print(f"   ✅ Test cargo found in cargo_name search")
                else:
                    print(f"   ❌ Test cargo not found in cargo_name search")
                    all_success = False
        
        # Test 2: Comprehensive search (should include cargo_name)
        success, comprehensive_results = self.run_test(
            "Comprehensive Search Including cargo_name",
            "GET",
            "/api/cargo/search",
            200,
            token=self.tokens['admin'],
            params={"query": "Уникальное", "search_type": "all"}  # Changed from "comprehensive" to "all"
        )
        all_success &= success
        
        if success:
            result_count = len(comprehensive_results) if isinstance(comprehensive_results, list) else 0
            print(f"   🔍 Found {result_count} results for comprehensive search")
            
            # Verify our test cargo is in results
            if isinstance(comprehensive_results, list) and test_cargo_number:
                found_cargo = any(c.get('cargo_number') == test_cargo_number for c in comprehensive_results)
                if found_cargo:
                    print(f"   ✅ Test cargo found in comprehensive search")
                else:
                    print(f"   ❌ Test cargo not found in comprehensive search")
                    all_success = False
        
        # Test 3: Legacy warehouse search (should still work)
        if 'warehouse_operator' in self.tokens:
            success, warehouse_search = self.run_test(
                "Legacy Warehouse Search",
                "GET",
                "/api/warehouse/search",
                200,
                token=self.tokens['warehouse_operator'],
                params={"query": "Уникальное"}
            )
            all_success &= success
            
            if success:
                result_count = len(warehouse_search) if isinstance(warehouse_search, list) else 0
                print(f"   🔍 Found {result_count} results for warehouse search")
        
        # Test 4: Search by cargo number (should still work)
        if test_cargo_number:
            success, number_search = self.run_test(
                "Search by Cargo Number",
                "GET",
                "/api/cargo/search",
                200,
                token=self.tokens['admin'],
                params={"query": test_cargo_number, "search_type": "cargo_number"}
            )
            all_success &= success
            
            if success:
                result_count = len(number_search) if isinstance(number_search, list) else 0
                print(f"   🔍 Found {result_count} results for cargo number search")
                
                if result_count > 0:
                    print(f"   ✅ Cargo number search working correctly")
                else:
                    print(f"   ❌ Cargo number search not working")
                    all_success = False
        
        return all_success

    def test_automatic_warehouse_placement(self):
        """Test automatic warehouse placement for operators"""
        print("\n🏭 AUTOMATIC WAREHOUSE PLACEMENT")
        
        if 'admin' not in self.tokens or 'warehouse_operator' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # First ensure we have a warehouse and operator binding
        warehouse_data = {
            "name": "Склад Автоматического Размещения",
            "location": "Москва, Автоматическая территория",
            "blocks_count": 2,
            "shelves_per_block": 2,
            "cells_per_shelf": 5
        }
        
        success, warehouse_response = self.run_test(
            "Create Warehouse for Auto Placement",
            "POST",
            "/api/warehouses/create",
            200,
            warehouse_data,
            self.tokens['admin']
        )
        all_success &= success
        
        warehouse_id = None
        if success and 'id' in warehouse_response:
            warehouse_id = warehouse_response['id']
            print(f"   🏭 Created warehouse: {warehouse_id}")
        
        # Create operator-warehouse binding
        if warehouse_id:
            operator_id = self.users['warehouse_operator']['id']
            binding_data = {
                "operator_id": operator_id,
                "warehouse_id": warehouse_id
            }
            
            success, binding_response = self.run_test(
                "Create Operator-Warehouse Binding for Auto Placement",
                "POST",
                "/api/admin/operator-warehouse-binding",
                200,
                binding_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print(f"   🔗 Created operator binding")
        
        # Create cargo for auto placement testing
        cargo_data = {
            "sender_full_name": "Отправитель Автоматического Размещения",
            "sender_phone": "+79111222666",
            "recipient_full_name": "Получатель Автоматического Размещения",
            "recipient_phone": "+992444555999",
            "recipient_address": "Душанбе, ул. Автоматическая, 1",
            "weight": 10.0,
            "cargo_name": "Груз для автоматического размещения",
            "declared_value": 5000.0,
            "description": "Тестовый груз для автоматического размещения",
            "route": "moscow_to_tajikistan"
        }
        
        success, cargo_response = self.run_test(
            "Create Cargo for Auto Placement",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            self.tokens['warehouse_operator']  # Use warehouse operator
        )
        all_success &= success
        
        cargo_id = None
        if success and 'id' in cargo_response:
            cargo_id = cargo_response['id']
            print(f"   📦 Created cargo: {cargo_id}")
        
        # Test 1: Automatic warehouse placement (operator chooses only block/shelf/cell)
        if cargo_id:
            auto_placement_data = {
                "cargo_id": cargo_id,
                "block_number": 1,
                "shelf_number": 1,
                "cell_number": 1
                # No warehouse_id - should be determined automatically
            }
            
            success, placement_response = self.run_test(
                "Automatic Warehouse Placement (Operator)",
                "POST",
                "/api/operator/cargo/place-auto",
                200,
                auto_placement_data,
                self.tokens['warehouse_operator']
            )
            all_success &= success
            
            if success:
                warehouse_name = placement_response.get('warehouse_name', 'Unknown')
                print(f"   ✅ Cargo automatically placed in warehouse: {warehouse_name}")
        
        # Test 2: Admin should get error when trying to use auto placement
        if cargo_id:
            # Create another cargo for admin test
            admin_cargo_data = {
                "sender_full_name": "Отправитель Админа",
                "sender_phone": "+79111222777",
                "recipient_full_name": "Получатель Админа",
                "recipient_phone": "+992444555000",
                "recipient_address": "Душанбе, ул. Админская, 1",
                "weight": 8.0,
                "cargo_name": "Груз админа для теста",
                "declared_value": 4000.0,
                "description": "Тестовый груз админа",
                "route": "moscow_to_tajikistan"
            }
            
            success, admin_cargo_response = self.run_test(
                "Create Cargo for Admin Auto Placement Test",
                "POST",
                "/api/operator/cargo/accept",
                200,
                admin_cargo_data,
                self.tokens['admin']
            )
            
            if success and 'id' in admin_cargo_response:
                admin_cargo_id = admin_cargo_response['id']
                
                admin_auto_placement_data = {
                    "cargo_id": admin_cargo_id,
                    "block_number": 1,
                    "shelf_number": 2,
                    "cell_number": 1
                }
                
                success, _ = self.run_test(
                    "Admin Auto Placement (Should Fail)",
                    "POST",
                    "/api/operator/cargo/place-auto",
                    400,  # Expecting error
                    admin_auto_placement_data,
                    self.tokens['admin']
                )
                all_success &= success
                
                if success:
                    print(f"   ✅ Admin correctly blocked from using auto placement")
        
        # Test 3: Unbound operator should get error
        # First remove the binding
        if warehouse_id:
            # Get all bindings to find the one to delete
            success, bindings = self.run_test(
                "Get Bindings for Cleanup",
                "GET",
                "/api/admin/operator-warehouse-bindings",
                200,
                token=self.tokens['admin']
            )
            
            if success and isinstance(bindings, list):
                operator_id = self.users['warehouse_operator']['id']
                binding_to_delete = next((b for b in bindings if b.get('operator_id') == operator_id and b.get('warehouse_id') == warehouse_id), None)
                
                if binding_to_delete:
                    binding_id = binding_to_delete['id']
                    success, _ = self.run_test(
                        "Delete Operator Binding for Unbound Test",
                        "DELETE",
                        f"/api/admin/operator-warehouse-binding/{binding_id}",
                        200,
                        token=self.tokens['admin']
                    )
                    
                    if success:
                        print(f"   🗑️  Removed operator binding for unbound test")
                        
                        # Now test unbound operator
                        unbound_cargo_data = {
                            "sender_full_name": "Отправитель Несвязанного Оператора",
                            "sender_phone": "+79111222888",
                            "recipient_full_name": "Получатель Несвязанного Оператора",
                            "recipient_phone": "+992444555111",
                            "recipient_address": "Душанбе, ул. Несвязанная, 1",
                            "weight": 6.0,
                            "cargo_name": "Груз несвязанного оператора",
                            "declared_value": 3000.0,
                            "description": "Тестовый груз несвязанного оператора",
                            "route": "moscow_to_tajikistan"
                        }
                        
                        success, unbound_cargo_response = self.run_test(
                            "Create Cargo for Unbound Operator Test",
                            "POST",
                            "/api/operator/cargo/accept",
                            200,
                            unbound_cargo_data,
                            self.tokens['warehouse_operator']
                        )
                        
                        if success and 'id' in unbound_cargo_response:
                            unbound_cargo_id = unbound_cargo_response['id']
                            
                            unbound_placement_data = {
                                "cargo_id": unbound_cargo_id,
                                "block_number": 2,
                                "shelf_number": 1,
                                "cell_number": 1
                            }
                            
                            success, _ = self.run_test(
                                "Unbound Operator Auto Placement (Should Fail)",
                                "POST",
                                "/api/operator/cargo/place-auto",
                                403,  # Expecting forbidden
                                unbound_placement_data,
                                self.tokens['warehouse_operator']
                            )
                            all_success &= success
                            
                            if success:
                                print(f"   ✅ Unbound operator correctly blocked from auto placement")
        
        return all_success

    def run_all_tests(self):
        """Run all cargo name integration tests"""
        print("\n🚀 STARTING CARGO NAME FIELD INTEGRATION TESTS")
        
        # Setup authentication
        if not self.setup_authentication():
            print("\n❌ Authentication setup failed")
            return False
        
        test_results = []
        
        # Run all test suites
        test_suites = [
            ("Cargo Creation Without cargo_name", self.test_cargo_creation_without_cargo_name),
            ("Cargo Creation With cargo_name", self.test_cargo_creation_with_cargo_name),
            ("Cargo Listings Compatibility", self.test_cargo_listings_compatibility),
            ("Search System with cargo_name", self.test_search_system_with_cargo_name),
            ("Automatic Warehouse Placement", self.test_automatic_warehouse_placement),
        ]
        
        for suite_name, test_func in test_suites:
            print(f"\n{'='*60}")
            print(f"🧪 RUNNING: {suite_name}")
            print(f"{'='*60}")
            
            try:
                result = test_func()
                test_results.append((suite_name, result))
                
                if result:
                    print(f"\n✅ {suite_name}: PASSED")
                else:
                    print(f"\n❌ {suite_name}: FAILED")
                    
            except Exception as e:
                print(f"\n💥 {suite_name}: EXCEPTION - {str(e)}")
                test_results.append((suite_name, False))
        
        # Print final summary
        print(f"\n{'='*60}")
        print(f"📊 FINAL RESULTS")
        print(f"{'='*60}")
        
        passed_suites = sum(1 for _, result in test_results if result)
        total_suites = len(test_results)
        
        for suite_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status}: {suite_name}")
        
        print(f"\n📈 SUMMARY:")
        print(f"   🧪 Total Tests Run: {self.tests_run}")
        print(f"   ✅ Tests Passed: {self.tests_passed}")
        print(f"   ❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   📊 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print(f"\n📋 TEST SUITES:")
        print(f"   ✅ Suites Passed: {passed_suites}")
        print(f"   ❌ Suites Failed: {total_suites - passed_suites}")
        print(f"   📊 Suite Success Rate: {(passed_suites/total_suites)*100:.1f}%")
        
        overall_success = passed_suites == total_suites
        
        if overall_success:
            print(f"\n🎉 ALL TESTS PASSED! Cargo name field integration is working correctly.")
        else:
            print(f"\n⚠️  SOME TESTS FAILED! Please review the failed test suites above.")
        
        return overall_success

if __name__ == "__main__":
    tester = CargoNameTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)