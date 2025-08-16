#!/usr/bin/env python3
"""
Тестирование изменений формы заявки на забор груза в TAJLINE.TJ
Проверяет замену поля "Назначение груза" на "Наименование груза"
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class PickupCargoNameTester:
    def __init__(self, base_url="https://cargo-tracker-29.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🚚 TAJLINE.TJ Pickup Cargo Name Changes Tester")
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

    def test_pickup_cargo_name_changes(self):
        """Test изменения формы заявки на забор груза: замена 'Назначение груза' на 'Наименование груза'"""
        print("\n🎯 PICKUP CARGO NAME CHANGES TESTING")
        print("   🔧 ИЗМЕНЕНИЯ РЕАЛИЗОВАННЫЕ:")
        print("   1. Frontend: Заменено поле 'Назначение груза' (Select с маршрутами) на поле 'Наименование груза' (Input) в форме режима 'Забор груза'")
        print("   2. Frontend: Обновлена функция handlePickupCargoSubmit - теперь отправляет cargo_name как destination вместо route")
        print("   3. Frontend: Обновлена очистка формы для включения нового поля cargo_name")
        print("   🎯 ТЕСТ ИЗМЕНЕНИЙ:")
        print("   1. Авторизация оператора (+79777888999/warehouse123)")
        print("   2. ОСНОВНОЙ ТЕСТ: Создание заявки на забор груза через POST /api/admin/courier/pickup-request с новыми данными")
        print("   3. Проверить что заявка создается с полем destination содержащим наименование груза")
        print("   4. Авторизация курьера и проверка что заявка отображается в GET /api/courier/requests/new с правильным наименованием")
        print("   🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Заявки на забор груза должны создаваться с наименованием груза вместо маршрута в поле destination.")
        
        all_success = True
        
        # Test 1: АВТОРИЗАЦИЯ ОПЕРАТОРА (+79777888999/warehouse123)
        print("\n   🔐 Test 1: АВТОРИЗАЦИЯ ОПЕРАТОРА (+79777888999/warehouse123)...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Operator Authentication",
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
            operator_user_number = operator_user.get('user_number')
            
            print(f"   ✅ Operator login successful: {operator_name}")
            print(f"   👑 Role: {operator_role}")
            print(f"   📞 Phone: {operator_user.get('phone')}")
            print(f"   🆔 User Number: {operator_user_number}")
            
            self.tokens['warehouse_operator'] = operator_token
            self.users['warehouse_operator'] = operator_user
        else:
            print("   ❌ Operator login failed")
            all_success = False
            return False
        
        # Test 2: ОСНОВНОЙ ТЕСТ - Создание заявки на забор груза с новой структурой данных
        print("\n   📦 Test 2: ОСНОВНОЙ ТЕСТ - Создание заявки на забор груза с наименованием груза...")
        print("   🔧 Тестируем новую структуру: cargo_name отправляется как destination вместо route")
        
        pickup_request_data = {
            "sender_full_name": "Тест Наименование",
            "sender_phone": "+7999888777",
            "pickup_address": "Москва, ул. Тестовая, 123",
            "pickup_date": "2025-01-20",
            "pickup_time_from": "10:00",
            "pickup_time_to": "12:00",
            "destination": "Документы и подарки",  # Наименование груза вместо маршрута
            "courier_fee": 800,
            "payment_method": "not_paid"
        }
        
        success, pickup_response = self.run_test(
            "Create Pickup Request with Cargo Name as Destination",
            "POST",
            "/api/admin/courier/pickup-request",
            200,
            pickup_request_data,
            operator_token
        )
        all_success &= success
        
        pickup_request_id = None
        if success and pickup_response.get('success'):
            pickup_request_id = pickup_response.get('request_id')
            pickup_request_number = pickup_response.get('request_number')
            
            print(f"   ✅ Pickup request created successfully with cargo name as destination")
            print(f"   🆔 Request ID: {pickup_request_id}")
            print(f"   📋 Request Number: {pickup_request_number}")
            print(f"   📦 Cargo Name (as destination): 'Документы и подарки'")
            print(f"   📄 Message: {pickup_response.get('message')}")
            
            # Verify required fields are present
            if pickup_request_id and pickup_request_number:
                print("   ✅ Required fields present in pickup request response")
            else:
                print(f"   ❌ Missing required fields in pickup request response")
                all_success = False
        else:
            print("   ❌ Failed to create pickup request with cargo name")
            all_success = False
            return False
        
        # Test 3: АВТОРИЗАЦИЯ КУРЬЕРА (+79991234567/courier123)
        print("\n   🚴 Test 3: АВТОРИЗАЦИЯ КУРЬЕРА (+79991234567/courier123)...")
        
        courier_login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        success, courier_login_response = self.run_test(
            "Courier Authentication",
            "POST",
            "/api/auth/login",
            200,
            courier_login_data
        )
        all_success &= success
        
        courier_token = None
        if success and 'access_token' in courier_login_response:
            courier_token = courier_login_response['access_token']
            courier_user = courier_login_response.get('user', {})
            courier_role = courier_user.get('role')
            courier_name = courier_user.get('full_name')
            courier_user_number = courier_user.get('user_number')
            
            print(f"   ✅ Courier login successful: {courier_name}")
            print(f"   👑 Role: {courier_role}")
            print(f"   📞 Phone: {courier_user.get('phone')}")
            print(f"   🆔 User Number: {courier_user_number}")
            
            self.tokens['courier'] = courier_token
            self.users['courier'] = courier_user
        else:
            print("   ❌ Courier login failed")
            all_success = False
            return False
        
        # Test 4: Проверка что заявка отображается в GET /api/courier/requests/new с правильным наименованием
        print("\n   📋 Test 4: Проверка заявки в GET /api/courier/requests/new с наименованием груза...")
        
        success, new_requests_response = self.run_test(
            "Get New Requests (Should Show Cargo Name in Destination)",
            "GET",
            "/api/courier/requests/new",
            200,
            token=courier_token
        )
        all_success &= success
        
        if success and isinstance(new_requests_response, dict):
            new_requests = new_requests_response.get('new_requests', [])
            print(f"   📊 Found {len(new_requests)} new requests")
            
            # Look for our pickup request with cargo name
            cargo_name_found = False
            for request in new_requests:
                if (request.get('id') == pickup_request_id or 
                    request.get('sender_full_name') == 'Тест Наименование'):
                    
                    destination = request.get('destination', '')
                    cargo_name = request.get('cargo_name', '')
                    request_type = request.get('request_type', '')
                    
                    print(f"   🎯 Found our pickup request:")
                    print(f"      🆔 ID: {request.get('id')}")
                    print(f"      👤 Sender: {request.get('sender_full_name')}")
                    print(f"      📦 Destination: '{destination}'")
                    print(f"      📦 Cargo Name: '{cargo_name}'")
                    print(f"      🏷️ Request Type: '{request_type}'")
                    
                    # Check if destination contains cargo name
                    if destination == "Документы и подарки":
                        print("   ✅ SUCCESS: Destination field contains cargo name 'Документы и подарки'")
                        cargo_name_found = True
                    else:
                        print(f"   ❌ FAILED: Expected destination 'Документы и подарки', got '{destination}'")
                        all_success = False
                    
                    # Check request type
                    if request_type == 'pickup':
                        print("   ✅ Request type correctly set to 'pickup'")
                    else:
                        print(f"   ⚠️ Request type: '{request_type}' (expected 'pickup')")
                    
                    break
            
            if not cargo_name_found:
                print("   ❌ FAILED: Our pickup request with cargo name not found in new requests")
                print("   📋 Available requests:")
                for i, req in enumerate(new_requests[:3]):  # Show first 3 requests
                    print(f"      {i+1}. Sender: {req.get('sender_full_name')}, Destination: {req.get('destination', 'N/A')}")
                all_success = False
        else:
            print("   ❌ Failed to get new requests or invalid response format")
            all_success = False
        
        # Test 5: Дополнительная проверка - создание еще одной заявки с другим наименованием груза
        print("\n   📦 Test 5: Дополнительная проверка - создание заявки с другим наименованием груза...")
        
        pickup_request_data_2 = {
            "sender_full_name": "Тест Наименование 2",
            "sender_phone": "+7999888778",
            "pickup_address": "Москва, ул. Тестовая 2, 456",
            "pickup_date": "2025-01-21",
            "pickup_time_from": "14:00",
            "pickup_time_to": "16:00",
            "destination": "Электроника и техника",  # Другое наименование груза
            "courier_fee": 1000,
            "payment_method": "not_paid"
        }
        
        success, pickup_response_2 = self.run_test(
            "Create Second Pickup Request with Different Cargo Name",
            "POST",
            "/api/admin/courier/pickup-request",
            200,
            pickup_request_data_2,
            operator_token
        )
        all_success &= success
        
        if success and pickup_response_2.get('success'):
            pickup_request_id_2 = pickup_response_2.get('request_id')
            print(f"   ✅ Second pickup request created with cargo name: 'Электроника и техника'")
            print(f"   🆔 Request ID: {pickup_request_id_2}")
        else:
            print("   ❌ Failed to create second pickup request")
            all_success = False
        
        return all_success

    def run_all_tests(self):
        """Run all pickup cargo name change tests"""
        print("\n🚀 Starting Pickup Cargo Name Changes Testing...")
        
        success = self.test_pickup_cargo_name_changes()
        
        print("\n" + "=" * 60)
        print(f"📊 FINAL RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if success:
            print("   🎉 ALL PICKUP CARGO NAME CHANGES TESTS PASSED!")
            print("   ✅ EXPECTED RESULT ACHIEVED: Заявки на забор груза создаются с наименованием груза вместо маршрута в поле destination")
        else:
            print("   ❌ SOME TESTS FAILED!")
            print("   🔧 Please check the failed tests above")
        
        return success

if __name__ == "__main__":
    tester = PickupCargoNameTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)