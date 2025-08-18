#!/usr/bin/env python3
"""
Быстрое тестирование backend стабильности после улучшений функционала чтения QR кодов
Специальный тест согласно review request
"""

import requests
import sys
import json
from datetime import datetime

class QRStabilityTester:
    def __init__(self):
        # Use the correct backend URL from frontend/.env
        self.base_url = "https://tajline-cargo-3.preview.emergentagent.com"
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print("🎯 БЫСТРОЕ ТЕСТИРОВАНИЕ BACKEND СТАБИЛЬНОСТИ ПОСЛЕ УЛУЧШЕНИЙ QR КОДОВ")
        print(f"📡 Backend URL: {self.base_url}")
        print("=" * 80)

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
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=headers)

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

    def test_warehouse_operator_authentication(self):
        """Test 1: Авторизация оператора склада +79777888999/warehouse123 работает стабильно"""
        print("\n🔐 ТЕСТ 1: АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА (+79777888999/warehouse123)")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Warehouse Operator Login (Stable Authentication)",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        
        if success and 'access_token' in login_response:
            operator_token = login_response['access_token']
            operator_user = login_response.get('user', {})
            operator_role = operator_user.get('role')
            operator_name = operator_user.get('full_name')
            
            print(f"   ✅ Operator login successful: {operator_name}")
            print(f"   👑 Role: {operator_role}")
            print(f"   📞 Phone: {operator_user.get('phone')}")
            
            # Verify role is warehouse_operator
            if operator_role == 'warehouse_operator':
                print("   ✅ Operator role correctly set to 'warehouse_operator'")
                self.tokens['warehouse_operator'] = operator_token
                return True
            else:
                print(f"   ❌ Operator role incorrect: expected 'warehouse_operator', got '{operator_role}'")
                return False
        else:
            print("   ❌ Operator login failed")
            return False

    def test_cargo_placement_endpoints(self):
        """Test 2: Endpoints для размещения груза остаются функциональными"""
        print("\n🏗️ ТЕСТ 2: ENDPOINTS ДЛЯ РАЗМЕЩЕНИЯ ГРУЗА ОСТАЮТСЯ ФУНКЦИОНАЛЬНЫМИ")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No operator token available")
            return False
            
        operator_token = self.tokens['warehouse_operator']
        all_success = True
        
        # Test 2.1: /api/operator/placement-statistics
        print("\n   📊 Test 2.1: /api/operator/placement-statistics...")
        
        success, stats_response = self.run_test(
            "Operator Placement Statistics",
            "GET",
            "/api/operator/placement-statistics",
            200,
            token=operator_token
        )
        all_success &= success
        
        if success:
            print("   ✅ /api/operator/placement-statistics working")
            required_stats = ['operator_name', 'today_placements', 'session_placements', 'recent_placements']
            missing_stats = [field for field in required_stats if field not in stats_response]
            
            if not missing_stats:
                print("   ✅ All placement statistics fields present")
                print(f"   📊 Operator: {stats_response.get('operator_name')}")
                print(f"   📊 Today placements: {stats_response.get('today_placements', 0)}")
                print(f"   📊 Session placements: {stats_response.get('session_placements', 0)}")
            else:
                print(f"   ❌ Missing statistics fields: {missing_stats}")
                all_success = False
        
        # Test 2.2: Get warehouses for testing
        print("\n   🏭 Test 2.2: Get warehouses for placement testing...")
        
        success, warehouses_response = self.run_test(
            "Get Warehouses for Placement Testing",
            "GET",
            "/api/warehouses",
            200,
            token=operator_token
        )
        all_success &= success
        
        test_warehouse = None
        if success and warehouses_response:
            test_warehouse = warehouses_response[0] if isinstance(warehouses_response, list) else None
            if test_warehouse:
                warehouse_id = test_warehouse.get('id')
                warehouse_name = test_warehouse.get('name', 'Test Warehouse')
                print(f"   🏭 Using warehouse: {warehouse_name}")
        
        # Test 2.3: /api/warehouse/available-cells
        if test_warehouse:
            print("\n   🏗️ Test 2.3: /api/warehouse/available-cells...")
            
            warehouse_id = test_warehouse.get('id')
            
            success, cells_response = self.run_test(
                "Get Available Warehouse Cells",
                "GET",
                f"/api/warehouses/{warehouse_id}/available-cells",
                200,
                token=operator_token
            )
            all_success &= success
            
            if success:
                print("   ✅ /api/warehouse/available-cells working")
                if isinstance(cells_response, dict) and 'available_cells' in cells_response:
                    available_count = len(cells_response.get('available_cells', []))
                    print(f"   📊 Found {available_count} available cells")
                elif isinstance(cells_response, list):
                    print(f"   📊 Found {len(cells_response)} available cells")
        
        # Test 2.4: Create test cargo for placement
        print("\n   📦 Test 2.4: Create test cargo for placement...")
        
        cargo_data = {
            "sender_full_name": "Тест Отправитель QR Стабильность",
            "sender_phone": "+79991234567",
            "recipient_full_name": "Тест Получатель QR Стабильность",
            "recipient_phone": "+992987654321",
            "recipient_address": "Душанбе, ул. QR Стабильность, 1",
            "weight": 5.0,
            "cargo_name": "Тестовый груз для проверки стабильности",
            "declared_value": 2000.0,
            "description": "Тест стабильности backend после улучшений QR кодов",
            "route": "moscow_dushanbe",
            "payment_method": "cash",
            "payment_amount": 2000.0
        }
        
        success, cargo_response = self.run_test(
            "Create Test Cargo for Placement",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            operator_token
        )
        all_success &= success
        
        if success and 'cargo_number' in cargo_response:
            test_cargo_number = cargo_response['cargo_number']
            print(f"   ✅ Test cargo created: {test_cargo_number}")
        
        return all_success

    def test_qr_scanning_endpoints(self):
        """Test 3: QR сканирование endpoints работают корректно"""
        print("\n📱 ТЕСТ 3: QR СКАНИРОВАНИЕ ENDPOINTS РАБОТАЮТ КОРРЕКТНО")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No operator token available")
            return False
            
        operator_token = self.tokens['warehouse_operator']
        all_success = True
        
        # Test 3.1: Create test cargo for QR scanning
        print("\n   📦 Test 3.1: Create test cargo for QR scanning...")
        
        cargo_data = {
            "sender_full_name": "Тест QR Сканирование",
            "sender_phone": "+79991234568",
            "recipient_full_name": "Тест QR Получатель",
            "recipient_phone": "+992987654322",
            "recipient_address": "Душанбе, ул. QR Сканирование, 2",
            "weight": 3.0,
            "cargo_name": "Тестовый груз для QR сканирования",
            "declared_value": 1500.0,
            "description": "Тест QR сканирования после улучшений",
            "route": "moscow_dushanbe",
            "payment_method": "cash",
            "payment_amount": 1500.0
        }
        
        success, cargo_response = self.run_test(
            "Create Test Cargo for QR Scanning",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            operator_token
        )
        all_success &= success
        
        test_cargo_number = None
        if success and 'cargo_number' in cargo_response:
            test_cargo_number = cargo_response['cargo_number']
            print(f"   ✅ Test cargo created: {test_cargo_number}")
        
        # Test 3.2: /api/cargo/track/{cargo_number} endpoint
        if test_cargo_number:
            print("\n   🎯 Test 3.2: /api/cargo/track/{cargo_number} endpoint...")
            
            success, track_response = self.run_test(
                f"Track Cargo by Number (QR Search)",
                "GET",
                f"/api/cargo/track/{test_cargo_number}",
                200,
                token=operator_token
            )
            all_success &= success
            
            if success:
                print("   ✅ /api/cargo/track/{cargo_number} endpoint working")
                required_fields = ['cargo_number', 'cargo_name', 'weight', 'recipient_name', 'recipient_phone', 'status']
                missing_fields = [field for field in required_fields if field not in track_response]
                
                if not missing_fields:
                    print("   ✅ All required fields present for QR operations")
                    if track_response.get('cargo_number') == test_cargo_number:
                        print("   ✅ Cargo found by number - QR search working correctly")
                    else:
                        print(f"   ❌ Cargo number mismatch")
                        all_success = False
                else:
                    print(f"   ❌ Missing required fields: {missing_fields}")
                    all_success = False
        
        # Test 3.3: /api/cargo/scan-qr endpoint
        if test_cargo_number:
            print("\n   📱 Test 3.3: /api/cargo/scan-qr endpoint...")
            
            qr_scan_data = {
                "qr_text": test_cargo_number  # QR code contains cargo number
            }
            
            success, scan_response = self.run_test(
                "QR Scan for Operations",
                "POST",
                "/api/cargo/scan-qr",
                200,
                qr_scan_data,
                operator_token
            )
            all_success &= success
            
            if success:
                print("   ✅ QR scanning working correctly")
                if scan_response.get('success'):
                    print("   ✅ QR scan successful")
                    cargo_info = scan_response.get('cargo', {})
                    if cargo_info and cargo_info.get('cargo_number') == test_cargo_number:
                        print("   ✅ Correct cargo found by QR scanning")
                        operations = cargo_info.get('available_operations', [])
                        if operations:
                            print(f"   ✅ Available operations: {operations}")
                        else:
                            print("   ❌ No available operations")
                            all_success = False
                    else:
                        print("   ❌ Wrong cargo found by QR scanning")
                        all_success = False
                else:
                    print("   ❌ QR scan not successful")
                    all_success = False
        
        return all_success

    def test_existing_api_calls(self):
        """Test 4: Все существующие API вызовы работают корректно"""
        print("\n🔗 ТЕСТ 4: ВСЕ СУЩЕСТВУЮЩИЕ API ВЫЗОВЫ РАБОТАЮТ КОРРЕКТНО")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No operator token available")
            return False
            
        operator_token = self.tokens['warehouse_operator']
        all_success = True
        
        # Test existing API endpoints that should remain stable
        existing_endpoints = [
            ("/api/auth/me", "Current User Info"),
            ("/api/operator/warehouses", "Operator Warehouses"),
            ("/api/operator/cargo/list", "Operator Cargo List"),
            ("/api/operator/cargo/available-for-placement", "Available Cargo for Placement"),
            ("/api/warehouses", "Warehouses List"),
        ]
        
        for endpoint, description in existing_endpoints:
            print(f"\n   🔍 Testing {description} ({endpoint})...")
            
            success, response = self.run_test(
                description,
                "GET",
                endpoint,
                200,
                token=operator_token
            )
            all_success &= success
            
            if success:
                print(f"   ✅ {description} working")
                # Check for basic response structure
                if isinstance(response, (dict, list)):
                    print(f"   ✅ Response structure correct")
                else:
                    print(f"   ❌ Unexpected response format")
                    all_success = False
            else:
                print(f"   ❌ {description} failing")
        
        return all_success

    def run_all_tests(self):
        """Run all stability tests"""
        print("\n🚀 ЗАПУСК ВСЕХ ТЕСТОВ СТАБИЛЬНОСТИ BACKEND...")
        
        results = {}
        
        # Test 1: Авторизация оператора склада
        results['authentication'] = self.test_warehouse_operator_authentication()
        
        # Test 2: Endpoints для размещения груза
        results['placement_endpoints'] = self.test_cargo_placement_endpoints()
        
        # Test 3: QR сканирование endpoints
        results['qr_scanning'] = self.test_qr_scanning_endpoints()
        
        # Test 4: Существующие API вызовы
        results['existing_apis'] = self.test_existing_api_calls()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ СТАБИЛЬНОСТИ BACKEND")
        print("=" * 80)
        
        passed_tests = sum(1 for result in results.values() if result)
        total_tests = len(results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 Общие результаты:")
        print(f"   Тестов выполнено: {self.tests_run}")
        print(f"   Тестов пройдено: {self.tests_passed}")
        print(f"   Успешность: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        print(f"\n🎯 Результаты по категориям:")
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {test_name}: {status}")
        
        print(f"\n📊 Общая успешность тестирования: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        if all(results.values()):
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("✅ Авторизация оператора склада (+79777888999/warehouse123) работает стабильно")
            print("✅ Endpoints для размещения груза остаются функциональными")
            print("✅ Backend не затронут изменениями в handleExternalCellScan и обновлениями UI")
            print("✅ Все существующие API вызовы работают корректно")
            print("\n🎯 ЦЕЛЬ ДОСТИГНУТА: Backend остается стабильным после улучшений функционала чтения и отображения QR кодов ячеек")
            return True
        else:
            print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            failed_tests = [name for name, result in results.items() if not result]
            print(f"   Проблемные области: {', '.join(failed_tests)}")
            print("\n🔍 Требуется дополнительная проверка указанных областей")
            return False

if __name__ == "__main__":
    tester = QRStabilityTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)