#!/usr/bin/env python3
"""
TAJLINE.TJ Comprehensive Testing for Enhanced Cargo Management Improvements
Testing critical improvements after payment and cargo placement functionality

ПРИОРИТЕТ: КРИТИЧЕСКИЙ - Тестирование новых функций после оплаты и размещения

ГЛАВНЫЕ УЛУЧШЕНИЯ ДЛЯ ТЕСТИРОВАНИЯ:
1. УЛУЧШЕНИЕ СТАТУСОВ ПОСЛЕ ОПЛАТЫ
2. АНАЛИТИКА СКЛАДОВ ДЛЯ РАЗМЕЩЕНИЯ  
3. РАЗМЕЩЕННЫЕ ГРУЗЫ
4. ПОЛНЫЙ WORKFLOW РАЗМЕЩЕНИЯ
5. СИНХРОНИЗАЦИЯ СТАТУСОВ
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class TAJLINEImprovementsTester:
    def __init__(self, base_url="https://cargo-system-debug.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.test_cargo_ids = []
        self.test_warehouse_id = None
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🚛 TAJLINE.TJ IMPROVEMENTS TESTER")
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
                    elif isinstance(result, list) and len(result) > 0:
                        print(f"   📄 Response: {len(result)} items returned")
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
        print("\n🔐 SETTING UP AUTHENTICATION")
        
        # Login as Admin
        admin_login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        success, admin_response = self.run_test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            admin_login_data
        )
        
        if success and 'access_token' in admin_response:
            self.tokens['admin'] = admin_response['access_token']
            self.users['admin'] = admin_response['user']
            print(f"   🔑 Admin token stored")
        else:
            print("   ❌ Admin login failed")
            return False
        
        # Login as Warehouse Operator
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, operator_response = self.run_test(
            "Warehouse Operator Login",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        
        if success and 'access_token' in operator_response:
            self.tokens['warehouse_operator'] = operator_response['access_token']
            self.users['warehouse_operator'] = operator_response['user']
            print(f"   🔑 Warehouse Operator token stored")
        else:
            print("   ❌ Warehouse Operator login failed")
            return False
        
        return True

    def test_payment_status_improvements(self):
        """Test 1: УЛУЧШЕНИЕ СТАТУСОВ ПОСЛЕ ОПЛАТЫ"""
        print("\n💰 ТЕСТИРОВАНИЕ УЛУЧШЕНИЙ СТАТУСОВ ПОСЛЕ ОПЛАТЫ")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
        
        all_success = True
        
        # Step 1: Create test cargo for payment testing
        print("\n   📦 Creating test cargo for payment workflow...")
        
        test_cargo_data = {
            "sender_full_name": "Тест Отправитель Оплата",
            "sender_phone": "+79999111222",
            "recipient_full_name": "Тест Получатель Оплата",
            "recipient_phone": "+992900111222",
            "recipient_address": "Душанбе, ул. Оплаты, 1",
            "cargo_items": [
                {"cargo_name": "Документы", "weight": 10.0, "price_per_kg": 60.0},
                {"cargo_name": "Одежда", "weight": 25.0, "price_per_kg": 60.0},
                {"cargo_name": "Электроника", "weight": 100.0, "price_per_kg": 65.0}
            ],
            "description": "Тестовый груз для проверки оплаты (135кг, 8600руб)",
            "route": "moscow_dushanbe"
        }
        
        success, cargo_response = self.run_test(
            "Create Test Cargo for Payment",
            "POST",
            "/api/operator/cargo/accept",
            200,
            test_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        test_cargo_id = None
        if success and 'id' in cargo_response:
            test_cargo_id = cargo_response['id']
            cargo_number = cargo_response.get('cargo_number')
            initial_status = cargo_response.get('processing_status', 'unknown')
            
            print(f"   ✅ Test cargo created: {cargo_number}")
            print(f"   📊 Weight: {cargo_response.get('weight')}kg, Cost: {cargo_response.get('declared_value')}руб")
            print(f"   🏷️  Initial status: {initial_status}")
            
            self.test_cargo_ids.append(test_cargo_id)
            
            # Verify initial status is payment_pending
            if initial_status == 'payment_pending':
                print("   ✅ Initial status correctly set to 'payment_pending'")
            else:
                print(f"   ❌ Expected 'payment_pending', got '{initial_status}'")
                all_success = False
        
        # Step 2: Test payment processing endpoint
        print("\n   💳 Testing payment processing endpoint...")
        
        if test_cargo_id:
            payment_data = {
                "new_status": "paid"
            }
            
            success, payment_response = self.run_test(
                "Process Payment (paid status)",
                "PUT",
                f"/api/cargo/{test_cargo_id}/processing-status",
                200,
                payment_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print("   ✅ Payment processing endpoint working")
                print(f"   📄 Response: {payment_response}")
        
        # Step 3: Verify status updates in all tables and categories
        print("\n   🔄 Verifying status synchronization across all endpoints...")
        
        if test_cargo_id:
            # Check operator cargo list
            success, operator_cargo = self.run_test(
                "Check Operator Cargo List",
                "GET",
                "/api/operator/cargo/list",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success and 'items' in operator_cargo:
                # Find our test cargo
                test_cargo_found = None
                for cargo in operator_cargo['items']:
                    if cargo.get('id') == test_cargo_id:
                        test_cargo_found = cargo
                        break
                
                if test_cargo_found:
                    processing_status = test_cargo_found.get('processing_status')
                    payment_status = test_cargo_found.get('payment_status')
                    
                    print(f"   📊 Cargo found in operator list:")
                    print(f"   - processing_status: {processing_status}")
                    print(f"   - payment_status: {payment_status}")
                    
                    if processing_status == 'paid' and payment_status == 'paid':
                        print("   ✅ Status synchronized in operator cargo list")
                    else:
                        print("   ❌ Status not properly synchronized")
                        all_success = False
                else:
                    print("   ❌ Test cargo not found in operator list")
                    all_success = False
        
        # Step 4: Test movement from "Касса" -> "Не оплачено" to "Ожидает размещение"
        print("\n   📋 Testing cargo movement to 'Ожидает размещение' section...")
        
        # Check awaiting placement filter
        success, awaiting_placement = self.run_test(
            "Check Awaiting Placement Filter",
            "GET",
            "/api/operator/cargo/list",
            200,
            params={"filter_status": "awaiting_placement"},
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success and 'items' in awaiting_placement:
            # Look for our paid cargo
            found_in_awaiting = False
            for cargo in awaiting_placement['items']:
                if cargo.get('id') == test_cargo_id:
                    found_in_awaiting = True
                    print(f"   ✅ Paid cargo found in 'Ожидает размещение' section")
                    break
            
            if not found_in_awaiting:
                print("   ❌ Paid cargo not found in 'Ожидает размещение' section")
                all_success = False
        
        return all_success

    def test_warehouse_analytics(self):
        """Test 2: АНАЛИТИКА СКЛАДОВ ДЛЯ РАЗМЕЩЕНИЯ"""
        print("\n🏭 ТЕСТИРОВАНИЕ АНАЛИТИКИ СКЛАДОВ ДЛЯ РАЗМЕЩЕНИЯ")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
        
        all_success = True
        
        # Test existing warehouse endpoints for analytics data
        print("\n   📊 Testing warehouse data for analytics...")
        
        success, warehouses = self.run_test(
            "Get Warehouses List",
            "GET",
            "/api/warehouses",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success and len(warehouses) > 0:
            total_warehouses = len(warehouses)
            print(f"   📈 total_warehouses: {total_warehouses}")
            
            test_warehouse = warehouses[0]
            warehouse_id = test_warehouse.get('id')
            warehouse_name = test_warehouse.get('name')
            
            print(f"   🏭 Testing with warehouse: {warehouse_name} (ID: {warehouse_id})")
            self.test_warehouse_id = warehouse_id
            
            # Test warehouse structure for cell analytics
            success, structure = self.run_test(
                "Get Warehouse Structure",
                "GET",
                f"/api/warehouses/{warehouse_id}/structure",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success:
                total_cells = structure.get('total_cells', 0)
                available_cells = structure.get('available_cells', 0)
                occupied_cells = total_cells - available_cells
                
                print(f"   📈 available_cells: {available_cells}")
                print(f"   📈 occupied_cells: {occupied_cells}")
                print(f"   ✅ Warehouse analytics data available through structure endpoint")
            
            # Test available cells endpoint
            success, available_cells_response = self.run_test(
                "Get Available Cells",
                "GET",
                f"/api/warehouses/{warehouse_id}/available-cells",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print(f"   ✅ Available cells endpoint working")
                if isinstance(available_cells_response, list):
                    print(f"   📊 Found {len(available_cells_response)} available cells")
                elif isinstance(available_cells_response, dict):
                    cells_count = available_cells_response.get('available_cells', 0)
                    print(f"   📊 Available cells: {cells_count}")
        else:
            print("   ❌ No warehouses found for testing")
            all_success = False
        
        return all_success

    def test_placed_cargo_functionality(self):
        """Test 3: РАЗМЕЩЕННЫЕ ГРУЗЫ"""
        print("\n📍 ТЕСТИРОВАНИЕ ФУНКЦИОНАЛЬНОСТИ РАЗМЕЩЕННЫХ ГРУЗОВ")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
        
        all_success = True
        
        # Test placed cargo through existing endpoints
        print("\n   📦 Testing placed cargo through operator cargo list...")
        
        success, cargo_list = self.run_test(
            "Get Operator Cargo List",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success and 'items' in cargo_list:
            cargo_items = cargo_list['items']
            placed_cargo = [cargo for cargo in cargo_items if cargo.get('status') == 'placed' or cargo.get('warehouse_location')]
            
            print(f"   ✅ Found {len(placed_cargo)} cargo items with placement information")
            
            if placed_cargo:
                sample_cargo = placed_cargo[0]
                placement_fields = {
                    'warehouse_location': sample_cargo.get('warehouse_location'),
                    'warehouse_id': sample_cargo.get('warehouse_id'),
                    'block_number': sample_cargo.get('block_number'),
                    'shelf_number': sample_cargo.get('shelf_number'),
                    'cell_number': sample_cargo.get('cell_number'),
                    'placed_by_operator': sample_cargo.get('placed_by_operator'),
                    'created_at': sample_cargo.get('created_at')
                }
                
                print("   📊 Placement information available:")
                for field, value in placement_fields.items():
                    status = "✅" if value else "❌"
                    print(f"   {status} {field}: {value}")
                
                # Count how many placement fields are available
                available_fields = sum(1 for value in placement_fields.values() if value)
                if available_fields >= 3:  # At least 3 placement fields should be available
                    print("   ✅ Adequate placement information available")
                else:
                    print("   ⚠️  Limited placement information available")
            else:
                print("   ℹ️  No placed cargo found (this may be expected)")
        
        # Test warehouse layout with cargo
        print("\n   🏗️ Testing warehouse layout with cargo information...")
        
        if self.test_warehouse_id:
            success, layout_response = self.run_test(
                "Get Warehouse Layout with Cargo",
                "GET",
                f"/api/warehouses/{self.test_warehouse_id}/layout-with-cargo",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print("   ✅ Warehouse layout with cargo endpoint working")
                if isinstance(layout_response, dict):
                    blocks = layout_response.get('blocks', [])
                    total_placed = 0
                    for block in blocks:
                        shelves = block.get('shelves', [])
                        for shelf in shelves:
                            cells = shelf.get('cells', [])
                            placed_in_shelf = sum(1 for cell in cells if cell.get('is_occupied'))
                            total_placed += placed_in_shelf
                    
                    print(f"   📊 Total placed cargo in warehouse: {total_placed}")
        
        return all_success

    def test_complete_placement_workflow(self):
        """Test 4: ПОЛНЫЙ WORKFLOW РАЗМЕЩЕНИЯ"""
        print("\n🔄 ТЕСТИРОВАНИЕ ПОЛНОГО WORKFLOW РАЗМЕЩЕНИЯ")
        
        if 'admin' not in self.tokens or not self.test_warehouse_id:
            print("   ❌ Missing admin token or warehouse ID")
            return False
        
        all_success = True
        
        # Step 1: Create test cargo
        print("\n   📦 Step 1: Creating test cargo for placement workflow...")
        
        workflow_cargo_data = {
            "sender_full_name": "Workflow Тест Отправитель",
            "sender_phone": "+79999333444",
            "recipient_full_name": "Workflow Тест Получатель",
            "recipient_phone": "+992900333444",
            "recipient_address": "Душанбе, ул. Workflow, 1",
            "cargo_items": [
                {"cargo_name": "Тест Размещение", "weight": 15.0, "price_per_kg": 70.0}
            ],
            "description": "Тестовый груз для полного workflow размещения",
            "route": "moscow_dushanbe"
        }
        
        success, workflow_cargo = self.run_test(
            "Create Workflow Test Cargo",
            "POST",
            "/api/operator/cargo/accept",
            200,
            workflow_cargo_data,
            self.tokens['admin']
        )
        all_success &= success
        
        workflow_cargo_id = None
        if success and 'id' in workflow_cargo:
            workflow_cargo_id = workflow_cargo['id']
            cargo_number = workflow_cargo.get('cargo_number')
            print(f"   ✅ Workflow cargo created: {cargo_number}")
        
        # Step 2: Process payment (статус -> "paid")
        print("\n   💳 Step 2: Processing payment...")
        
        if workflow_cargo_id:
            payment_data = {"new_status": "paid"}
            
            success, _ = self.run_test(
                "Process Payment for Workflow Cargo",
                "PUT",
                f"/api/cargo/{workflow_cargo_id}/processing-status",
                200,
                payment_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success:
                print("   ✅ Payment processed successfully")
        
        # Step 3: Place cargo (размещение груза)
        print("\n   📍 Step 3: Placing cargo in warehouse...")
        
        if workflow_cargo_id and self.test_warehouse_id:
            # First get available cells to avoid conflicts
            success, available_cells = self.run_test(
                "Get Available Cells",
                "GET",
                f"/api/warehouses/{self.test_warehouse_id}/available-cells",
                200,
                token=self.tokens['admin']
            )
            
            if success and available_cells:
                # Use first available cell
                if isinstance(available_cells, list) and len(available_cells) > 0:
                    first_cell = available_cells[0]
                    block_num = first_cell.get('block_number', 1)
                    shelf_num = first_cell.get('shelf_number', 1)
                    cell_num = first_cell.get('cell_number', 1)
                elif isinstance(available_cells, dict):
                    block_num = 1
                    shelf_num = 1
                    cell_num = 1
                else:
                    block_num = 1
                    shelf_num = 1
                    cell_num = 1
                
                placement_data = {
                    "cargo_id": workflow_cargo_id,
                    "warehouse_id": self.test_warehouse_id,
                    "block_number": block_num,
                    "shelf_number": shelf_num,
                    "cell_number": cell_num
                }
                
                success, placement_response = self.run_test(
                    "Place Cargo in Warehouse",
                    "POST",
                    "/api/operator/cargo/place",
                    200,
                    placement_data,
                    self.tokens['admin']
                )
                
                if success:
                    print("   ✅ Cargo placement successful")
                    print(f"   📍 Placement response: {placement_response}")
                else:
                    # Try alternative placement method
                    auto_placement_data = {
                        "cargo_id": workflow_cargo_id,
                        "block_number": block_num,
                        "shelf_number": shelf_num,
                        "cell_number": cell_num
                    }
                    
                    success, auto_placement_response = self.run_test(
                        "Place Cargo Auto",
                        "POST",
                        "/api/operator/cargo/place-auto",
                        200,
                        auto_placement_data,
                        self.tokens['admin']
                    )
                    
                    if success:
                        print("   ✅ Auto cargo placement successful")
                        print(f"   📍 Auto placement response: {auto_placement_response}")
                    else:
                        print("   ⚠️  Cargo placement failed - may be due to cell conflicts")
                        all_success = False
        
        # Step 4: Verify status updated to "placed"
        print("\n   🔍 Step 4: Verifying status updated after placement...")
        
        if workflow_cargo_id:
            success, cargo_list = self.run_test(
                "Check Cargo Status After Placement",
                "GET",
                "/api/operator/cargo/list",
                200,
                token=self.tokens['admin']
            )
            all_success &= success
            
            if success and 'items' in cargo_list:
                # Find our workflow cargo
                workflow_cargo_found = None
                for cargo in cargo_list['items']:
                    if cargo.get('id') == workflow_cargo_id:
                        workflow_cargo_found = cargo
                        break
                
                if workflow_cargo_found:
                    status = workflow_cargo_found.get('status')
                    processing_status = workflow_cargo_found.get('processing_status')
                    warehouse_location = workflow_cargo_found.get('warehouse_location')
                    
                    print(f"   📊 Cargo status after placement:")
                    print(f"   - status: {status}")
                    print(f"   - processing_status: {processing_status}")
                    print(f"   - warehouse_location: {warehouse_location}")
                    
                    if status in ['placed', 'in_warehouse'] or warehouse_location:
                        print("   ✅ Cargo status correctly updated after placement")
                    else:
                        print("   ⚠️  Cargo status may not be fully updated")
                else:
                    print("   ❌ Workflow cargo not found after placement")
                    all_success = False
        
        return all_success

    def test_status_synchronization(self):
        """Test 5: СИНХРОНИЗАЦИЯ СТАТУСОВ"""
        print("\n🔄 ТЕСТИРОВАНИЕ СИНХРОНИЗАЦИИ СТАТУСОВ")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
        
        all_success = True
        
        # Test existing status synchronization endpoints
        print("\n   📊 Testing status synchronization across available endpoints...")
        
        endpoints_to_test = [
            ("Operator Cargo List", "/api/operator/cargo/list", {}),
            ("All Cargo (Admin)", "/api/cargo/all", {}),
            ("Warehouse Cargo", "/api/warehouse/cargo", {}),
        ]
        
        for endpoint_name, endpoint_path, params in endpoints_to_test:
            success, response = self.run_test(
                f"Check {endpoint_name}",
                "GET",
                endpoint_path,
                200,
                params=params,
                token=self.tokens['admin']
            )
            
            if success:
                print(f"   ✅ {endpoint_name} endpoint working")
                
                # Check if response has expected structure
                if isinstance(response, dict):
                    if 'items' in response:
                        items_count = len(response['items'])
                        print(f"   📊 {endpoint_name}: {items_count} items")
                    else:
                        print(f"   📊 {endpoint_name}: {len(response)} fields in response")
                elif isinstance(response, list):
                    print(f"   📊 {endpoint_name}: {len(response)} items")
                
                # Verify status fields are present in cargo items
                cargo_items = []
                if isinstance(response, dict) and 'items' in response:
                    cargo_items = response['items']
                elif isinstance(response, list):
                    cargo_items = response
                
                if cargo_items:
                    sample_cargo = cargo_items[0]
                    status_fields = ['status', 'processing_status', 'payment_status']
                    present_fields = [field for field in status_fields if field in sample_cargo]
                    
                    print(f"   📋 Status fields present: {present_fields}")
                    
                    if len(present_fields) >= 2:  # At least 2 status fields should be present
                        print(f"   ✅ {endpoint_name} has adequate status field coverage")
                    else:
                        print(f"   ⚠️  {endpoint_name} has limited status field coverage")
            else:
                print(f"   ❌ {endpoint_name} endpoint failed")
                all_success = False
        
        # Test status consistency across endpoints
        print("\n   🔍 Testing status consistency across endpoints...")
        
        if self.test_cargo_ids:
            test_cargo_id = self.test_cargo_ids[0]
            
            # Get cargo from different endpoints and compare status
            cargo_statuses = {}
            
            for endpoint_name, endpoint_path, params in endpoints_to_test:
                success, response = self.run_test(
                    f"Get Cargo from {endpoint_name}",
                    "GET",
                    endpoint_path,
                    200,
                    params=params,
                    token=self.tokens['admin']
                )
                
                if success:
                    # Find our test cargo
                    cargo_items = []
                    if isinstance(response, dict) and 'items' in response:
                        cargo_items = response['items']
                    elif isinstance(response, list):
                        cargo_items = response
                    
                    for cargo in cargo_items:
                        if cargo.get('id') == test_cargo_id:
                            cargo_statuses[endpoint_name] = {
                                'status': cargo.get('status'),
                                'processing_status': cargo.get('processing_status'),
                                'payment_status': cargo.get('payment_status')
                            }
                            break
            
            # Compare statuses across endpoints
            if len(cargo_statuses) > 1:
                print("   📊 Status comparison across endpoints:")
                for endpoint_name, statuses in cargo_statuses.items():
                    print(f"   {endpoint_name}: {statuses}")
                
                # Check if statuses are consistent
                status_values = [statuses.get('status') for statuses in cargo_statuses.values()]
                processing_status_values = [statuses.get('processing_status') for statuses in cargo_statuses.values()]
                payment_status_values = [statuses.get('payment_status') for statuses in cargo_statuses.values()]
                
                status_consistent = len(set(filter(None, status_values))) <= 1
                processing_consistent = len(set(filter(None, processing_status_values))) <= 1
                payment_consistent = len(set(filter(None, payment_status_values))) <= 1
                
                if status_consistent and processing_consistent and payment_consistent:
                    print("   ✅ Status synchronization verified - all endpoints consistent")
                else:
                    print("   ❌ Status synchronization issues detected")
                    all_success = False
            else:
                print("   ℹ️  Could not find test cargo in multiple endpoints for comparison")
        
        # Test specific status filters
        print("\n   🔍 Testing status-based filtering...")
        
        # Test payment_pending filter
        success, payment_pending = self.run_test(
            "Check Payment Pending Filter",
            "GET",
            "/api/operator/cargo/list",
            200,
            params={"filter_status": "payment_pending"},
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success and 'items' in payment_pending:
            pending_count = len(payment_pending['items'])
            print(f"   📊 Payment pending cargo: {pending_count} items")
            
            # Verify all items have payment_pending status
            if payment_pending['items']:
                all_pending = all(
                    cargo.get('processing_status') == 'payment_pending' or 
                    cargo.get('payment_status') == 'pending'
                    for cargo in payment_pending['items']
                )
                if all_pending:
                    print("   ✅ Payment pending filter working correctly")
                else:
                    print("   ⚠️  Payment pending filter may have inconsistencies")
        
        return all_success

    def run_all_tests(self):
        """Run all TAJLINE improvement tests"""
        print("\n🚀 STARTING TAJLINE.TJ IMPROVEMENTS COMPREHENSIVE TESTING")
        print("=" * 80)
        
        # Setup
        if not self.setup_authentication():
            print("\n❌ AUTHENTICATION SETUP FAILED - CANNOT CONTINUE")
            return False
        
        # Run all improvement tests
        test_results = []
        
        test_results.append(("Payment Status Improvements", self.test_payment_status_improvements()))
        test_results.append(("Warehouse Analytics", self.test_warehouse_analytics()))
        test_results.append(("Placed Cargo Functionality", self.test_placed_cargo_functionality()))
        test_results.append(("Complete Placement Workflow", self.test_complete_placement_workflow()))
        test_results.append(("Status Synchronization", self.test_status_synchronization()))
        
        # Print final results
        print("\n" + "=" * 80)
        print("🏁 TAJLINE.TJ IMPROVEMENTS TESTING RESULTS")
        print("=" * 80)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result:
                passed_tests += 1
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Test Suites Passed: {passed_tests}/{total_tests}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TAJLINE.TJ IMPROVEMENTS TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  {total_tests - passed_tests} TEST SUITE(S) FAILED")
            return False

if __name__ == "__main__":
    tester = TAJLINEImprovementsTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)