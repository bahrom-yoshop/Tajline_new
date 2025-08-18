#!/usr/bin/env python3
"""
Cargo Items Structure Analysis Test for TAJLINE.TJ Application
Tests the structure of cargo_items in pickup requests
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class CargoItemsAnalyzer:
    def __init__(self, base_url="https://cargo-talk.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🚛 TAJLINE.TJ Cargo Items Structure Analyzer")
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
                response = requests.delete(url, json=data, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
                    if isinstance(result, dict) and len(str(result)) < 200:
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

    def analyze_cargo_items_structure(self):
        """Analyze cargo_items data structure in pickup requests for TAJLINE.TJ"""
        print("\n📦 CARGO_ITEMS STRUCTURE ANALYSIS FOR PICKUP REQUESTS")
        print("   🎯 Исследование структуры данных cargo_items в заявке на забор груза TAJLINE.TJ")
        print("   🔧 АНАЛИЗ СТРУКТУРЫ ДАННЫХ О ГРУЗАХ:")
        print("   1) Авторизация оператора (+79777888999/warehouse123)")
        print("   2) Получить список уведомлений: GET /api/operator/warehouse-notifications")
        print("   3) Найти уведомление с pickup_request_id и протестировать GET /api/operator/pickup-requests/{pickup_request_id}")
        print("   4) Проанализировать структуру cargo_info и cargo_items")
        
        all_success = True
        
        # Test 1: АВТОРИЗАЦИЯ ОПЕРАТОРА (+79777888999/warehouse123)
        print("\n   🔐 Test 1: АВТОРИЗАЦИЯ ОПЕРАТОРА (+79777888999/warehouse123)...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Warehouse Operator Login for Cargo Items Analysis",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        all_success &= success
        
        operator_token = None
        if success and 'access_token' in login_response:
            operator_token = login_response['access_token']
            operator_user = login_response.get('user', {})
            operator_role = operator_user.get('role')
            operator_name = operator_user.get('full_name')
            
            print(f"   ✅ Operator login successful: {operator_name}")
            print(f"   👑 Role: {operator_role}")
            print(f"   📞 Phone: {operator_user.get('phone')}")
            
            self.tokens['warehouse_operator'] = operator_token
            self.users['warehouse_operator'] = operator_user
        else:
            print("   ❌ Operator login failed - no access token received")
            return False
        
        # Test 2: ПОЛУЧИТЬ СПИСОК УВЕДОМЛЕНИЙ
        print("\n   📋 Test 2: ПОЛУЧИТЬ СПИСОК УВЕДОМЛЕНИЙ: GET /api/operator/warehouse-notifications...")
        
        success, notifications_response = self.run_test(
            "Get Warehouse Notifications List",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        all_success &= success
        
        pickup_request_id = None
        
        if success:
            notifications = notifications_response if isinstance(notifications_response, list) else []
            notification_count = len(notifications)
            print(f"   ✅ Found {notification_count} warehouse notifications")
            
            # Поиск уведомления с pickup_request_id
            for notification in notifications:
                if 'pickup_request_id' in notification and notification.get('pickup_request_id'):
                    pickup_request_id = notification.get('pickup_request_id')
                    print(f"   🎯 Found notification with pickup_request_id: {pickup_request_id}")
                    break
            
            if not pickup_request_id:
                print("   ⚠️  No notification with pickup_request_id found")
                print("   📋 Will use a test pickup_request_id for analysis...")
                pickup_request_id = "test_pickup_request_123"
        else:
            print("   ❌ Failed to get warehouse notifications")
            return False
        
        # Test 3: ПРОТЕСТИРОВАТЬ GET /api/operator/pickup-requests/{pickup_request_id}
        print(f"\n   🔍 Test 3: ПРОТЕСТИРОВАТЬ GET /api/operator/pickup-requests/{pickup_request_id}...")
        
        success, pickup_request_response = self.run_test(
            f"Get Pickup Request Details (ID: {pickup_request_id})",
            "GET",
            f"/api/operator/pickup-requests/{pickup_request_id}",
            200,
            token=operator_token
        )
        
        if success:
            print("   ✅ /api/operator/pickup-requests/{pickup_request_id} endpoint working")
            
            # Test 4: ПРОАНАЛИЗИРОВАТЬ СТРУКТУРУ cargo_info И cargo_items
            print("\n   📦 Test 4: АНАЛИЗ СТРУКТУРЫ cargo_info И cargo_items...")
            
            print("   🔍 ДЕТАЛЬНЫЙ АНАЛИЗ СТРУКТУРЫ ДАННЫХ:")
            print(f"   📄 Response type: {type(pickup_request_response)}")
            print(f"   📄 All fields in response: {list(pickup_request_response.keys()) if isinstance(pickup_request_response, dict) else 'Not a dict'}")
            
            # Check for cargo_info field
            cargo_info = pickup_request_response.get('cargo_info')
            if cargo_info:
                print("   ✅ Поле 'cargo_info' найдено")
                print(f"   📄 cargo_info type: {type(cargo_info)}")
                print(f"   📄 cargo_info content: {cargo_info}")
            else:
                print("   ❌ Поле 'cargo_info' НЕ найдено")
            
            # Check for cargo_items field
            cargo_items = pickup_request_response.get('cargo_items')
            if cargo_items:
                print("   ✅ Поле 'cargo_items' найдено")
                print(f"   📄 cargo_items type: {type(cargo_items)}")
                
                if isinstance(cargo_items, list):
                    print(f"   📊 cargo_items является массивом с {len(cargo_items)} элементами")
                    
                    # Analyze each cargo item
                    for i, item in enumerate(cargo_items):
                        print(f"   📦 Cargo Item {i+1}:")
                        if isinstance(item, dict):
                            # Check for required fields
                            required_fields = ['name', 'weight', 'price']
                            for field in required_fields:
                                if field in item:
                                    print(f"     ✅ {field}: {item[field]} (type: {type(item[field]).__name__})")
                                else:
                                    print(f"     ❌ {field}: НЕ найдено")
                            
                            # Show all fields in the item
                            print(f"     📄 Все поля: {list(item.keys())}")
                        else:
                            print(f"     📄 Item type: {type(item)}, content: {item}")
                elif isinstance(cargo_items, str):
                    print("   📊 cargo_items является строкой")
                    print(f"     - Содержимое: {cargo_items}")
                else:
                    print(f"   📊 cargo_items имеет тип: {type(cargo_items)}")
            else:
                print("   ❌ Поле 'cargo_items' НЕ найдено")
            
            # Check for alternative cargo fields
            alternative_cargo_fields = ['cargo_name', 'cargo_data', 'items', 'goods', 'products']
            for field in alternative_cargo_fields:
                if field in pickup_request_response:
                    value = pickup_request_response[field]
                    print(f"   🔍 Альтернативное поле '{field}' найдено: {value} (type: {type(value).__name__})")
            
            # Critical analysis questions
            print("\n   ❓ КРИТИЧЕСКИЕ ВОПРОСЫ - АНАЛИЗ:")
            
            # Question 1: Возвращает ли backend массив cargo_items или одну строку cargo_name?
            has_cargo_items_array = isinstance(pickup_request_response.get('cargo_items'), list)
            has_cargo_name_string = isinstance(pickup_request_response.get('cargo_name'), str)
            
            if has_cargo_items_array:
                print("   ✅ ОТВЕТ 1: Backend возвращает массив cargo_items")
                cargo_items_count = len(pickup_request_response.get('cargo_items', []))
                print(f"     - Количество элементов в массиве: {cargo_items_count}")
            elif has_cargo_name_string:
                print("   ❌ ОТВЕТ 1: Backend возвращает только строку cargo_name")
                print(f"     - cargo_name: {pickup_request_response.get('cargo_name')}")
            else:
                print("   ⚠️  ОТВЕТ 1: Неясно - нет ни cargo_items массива, ни cargo_name строки")
            
            # Question 2: Как правильно разбить грузы на отдельные контейнеры в UI?
            if has_cargo_items_array:
                cargo_items_list = pickup_request_response.get('cargo_items', [])
                print("   ✅ ОТВЕТ 2: Можно создать отдельный контейнер для каждого элемента cargo_items")
                print(f"     - Рекомендуется создать {len(cargo_items_list)} контейнеров")
            else:
                print("   ❌ ОТВЕТ 2: Нужно парсить строку cargo_name или использовать другой подход")
            
            # Question 3: Есть ли данные о весе и цене для каждого отдельного груза?
            individual_weight_price_data = False
            if has_cargo_items_array:
                cargo_items_list = pickup_request_response.get('cargo_items', [])
                for item in cargo_items_list:
                    if isinstance(item, dict) and ('weight' in item or 'price' in item):
                        individual_weight_price_data = True
                        break
            
            if individual_weight_price_data:
                print("   ✅ ОТВЕТ 3: Есть индивидуальные данные о весе и цене для каждого груза")
                print("     - Можно реализовать автоматические расчеты для каждого контейнера")
            else:
                print("   ❌ ОТВЕТ 3: Нет индивидуальных данных о весе и цене")
                print("     - Автоматические расчеты будут ограничены")
                
        else:
            print("   ❌ Failed to get pickup request details")
            print("   📋 This could mean:")
            print("     - The pickup_request_id doesn't exist")
            print("     - The endpoint is not implemented")
            print("     - Access permissions issue")
            all_success = False
        
        # SUMMARY
        print("\n   📊 CARGO_ITEMS STRUCTURE ANALYSIS SUMMARY:")
        
        if all_success:
            print("   🎉 CARGO_ITEMS STRUCTURE ANALYSIS COMPLETED!")
            print("   ✅ Авторизация оператора склада (+79777888999/warehouse123) работает")
            print("   ✅ Endpoint /api/operator/warehouse-notifications доступен")
            if success:
                print("   ✅ Endpoint /api/operator/pickup-requests/{pickup_request_id} доступен")
            else:
                print("   ❌ Endpoint /api/operator/pickup-requests/{pickup_request_id} недоступен")
            
            print("\n   💡 РЕКОМЕНДАЦИИ ДЛЯ UI РАЗРАБОТКИ:")
            print("   1. Проверить наличие поля cargo_items как массива в ответе API")
            print("   2. Если cargo_items массив существует - создать отдельный контейнер для каждого элемента")
            print("   3. Если cargo_items отсутствует - использовать cargo_name или cargo_info как единое поле")
            print("   4. Для автоматических расчетов проверить наличие полей weight и price в каждом элементе")
            print("   5. Реализовать fallback для случаев, когда структура данных неполная")
            
            print("\n   🎯 КРИТИЧЕСКИЕ ВЫВОДЫ:")
            print("   - Backend endpoint /api/operator/pickup-requests/{pickup_request_id} протестирован")
            print("   - Структура ответа зависит от того, как курьер заполнил данные")
            print("   - Необходимо проверить реальные данные в production для точного анализа")
            print("   - UI должен быть готов к различным форматам данных (массив vs строка)")
        else:
            print("   ❌ SOME CARGO_ITEMS ANALYSIS TESTS FAILED")
            print("   🔍 Check the specific failed tests above for details")
        
        return all_success


if __name__ == "__main__":
    import os
    backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-talk.preview.emergentagent.com')
    
    analyzer = CargoItemsAnalyzer(base_url=backend_url)
    
    print("🎯 RUNNING CARGO ITEMS STRUCTURE ANALYSIS")
    print("=" * 80)
    
    result = analyzer.analyze_cargo_items_structure()
    
    print("\n" + "=" * 80)
    print("🏁 FINAL TEST RESULT")
    print("=" * 80)
    print(f"📊 Total tests run: {analyzer.tests_run}")
    print(f"✅ Tests passed: {analyzer.tests_passed}")
    print(f"❌ Tests failed: {analyzer.tests_run - analyzer.tests_passed}")
    print(f"📈 Success rate: {(analyzer.tests_passed/analyzer.tests_run*100):.1f}%" if analyzer.tests_run > 0 else "0%")
    
    if result:
        print("\n🎉 CARGO ITEMS STRUCTURE ANALYSIS COMPLETED!")
        print("✅ Analysis completed successfully")
    else:
        print("\n❌ CARGO ITEMS STRUCTURE ANALYSIS FAILED")
        print("🔍 Check test results above for details")