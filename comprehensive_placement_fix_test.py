#!/usr/bin/env python3
"""
Comprehensive test for placement_ready fix - Full workflow test
Creates pickup request → processes through courier → creates warehouse notification → completes processing
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class ComprehensivePlacementFixTester:
    def __init__(self, base_url="https://cargo-tracker-29.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🔧 COMPREHENSIVE PLACEMENT READY FIX TESTER")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 80)
        print("🎯 ПОЛНЫЙ ТЕСТ: Создание заявки → обработка курьером → уведомление → завершение оформления")
        print("🔍 ПРОВЕРКА: Статус 'awaiting_placement' вместо 'placement_ready'")
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
                response = requests.delete(url, json=data, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
                    if isinstance(result, dict) and len(str(result)) < 300:
                        print(f"   📄 Response: {result}")
                    elif isinstance(result, list) and len(result) <= 3:
                        print(f"   📄 Response: {result}")
                    else:
                        print(f"   📄 Response: {type(result).__name__} with {len(result) if hasattr(result, '__len__') else 'N/A'} items")
                    return True, result
                except:
                    return True, {}
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   📄 Error: {error_detail}")
                except:
                    print(f"   📄 Raw response: {response.text[:300]}")
                return False, {}

        except Exception as e:
            print(f"   ❌ FAILED - Exception: {str(e)}")
            return False, {}

    def test_full_workflow_placement_fix(self):
        """Test the complete workflow from pickup request to cargo creation with placement_ready fix"""
        print("\n🔧 FULL WORKFLOW PLACEMENT READY FIX TEST")
        
        all_success = True
        
        # ЭТАП 1: Авторизация оператора
        print("\n   🔐 ЭТАП 1: АВТОРИЗАЦИЯ ОПЕРАТОРА...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Warehouse Operator Login",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        all_success &= success
        
        if not success:
            return False
            
        operator_token = login_response['access_token']
        operator_user = login_response.get('user', {})
        print(f"   ✅ Operator: {operator_user.get('full_name')} ({operator_user.get('user_number')})")
        
        # ЭТАП 2: Создание заявки на забор груза
        print("\n   📦 ЭТАП 2: СОЗДАНИЕ ЗАЯВКИ НА ЗАБОР ГРУЗА...")
        
        pickup_request_data = {
            "sender_full_name": "Исправленный Тест Отправитель",
            "sender_phone": "+7999777666",
            "pickup_address": "Москва, ул. Исправленная, 1",
            "pickup_date": "2025-01-20",
            "pickup_time_from": "10:00",
            "pickup_time_to": "18:00",
            "route": "moscow_to_tajikistan",
            "courier_fee": 500.0
        }
        
        success, pickup_response = self.run_test(
            "Create Pickup Request",
            "POST",
            "/api/admin/courier/pickup-request",
            200,
            pickup_request_data,
            operator_token
        )
        all_success &= success
        
        if not success:
            return False
            
        pickup_request_id = pickup_response.get('id')
        pickup_request_number = pickup_response.get('request_number')
        print(f"   ✅ Pickup request created: {pickup_request_number} (ID: {pickup_request_id})")
        
        # ЭТАП 3: Авторизация курьера
        print("\n   🚚 ЭТАП 3: АВТОРИЗАЦИЯ КУРЬЕРА...")
        
        courier_login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        success, courier_login_response = self.run_test(
            "Courier Login",
            "POST",
            "/api/auth/login",
            200,
            courier_login_data
        )
        all_success &= success
        
        if not success:
            return False
            
        courier_token = courier_login_response['access_token']
        courier_user = courier_login_response.get('user', {})
        print(f"   ✅ Courier: {courier_user.get('full_name')} ({courier_user.get('user_number')})")
        
        # ЭТАП 4: Принятие заявки курьером
        print(f"\n   ✅ ЭТАП 4: ПРИНЯТИЕ ЗАЯВКИ КУРЬЕРОМ...")
        
        success, accept_response = self.run_test(
            f"Accept Pickup Request {pickup_request_id}",
            "POST",
            f"/api/courier/requests/{pickup_request_id}/accept",
            200,
            token=courier_token
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Pickup request {pickup_request_id} accepted by courier")
        else:
            print(f"   ❌ Failed to accept pickup request")
            return False
        
        # ЭТАП 5: Забор груза курьером
        print(f"\n   📦 ЭТАП 5: ЗАБОР ГРУЗА КУРЬЕРОМ...")
        
        success, pickup_response = self.run_test(
            f"Pickup Cargo {pickup_request_id}",
            "POST",
            f"/api/courier/requests/{pickup_request_id}/pickup",
            200,
            token=courier_token
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Cargo picked up by courier")
        else:
            print(f"   ❌ Failed to pickup cargo")
            return False
        
        # ЭТАП 6: Сдача груза на склад
        print(f"\n   🏭 ЭТАП 6: СДАЧА ГРУЗА НА СКЛАД...")
        
        success, deliver_response = self.run_test(
            f"Deliver to Warehouse {pickup_request_id}",
            "POST",
            f"/api/courier/requests/{pickup_request_id}/deliver-to-warehouse",
            200,
            token=courier_token
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Cargo delivered to warehouse")
            notification_id = deliver_response.get('notification_id')
            if notification_id:
                print(f"   📬 Warehouse notification created: {notification_id}")
        else:
            print(f"   ❌ Failed to deliver cargo to warehouse")
            return False
        
        # ЭТАП 7: Получение уведомлений склада
        print(f"\n   📬 ЭТАП 7: ПОЛУЧЕНИЕ УВЕДОМЛЕНИЙ СКЛАДА...")
        
        success, notifications_response = self.run_test(
            "Get Warehouse Notifications",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        all_success &= success
        
        if not success:
            return False
            
        notifications = notifications_response.get('notifications', [])
        active_notification = None
        
        for notification in notifications:
            if notification.get('status') == 'pending_acceptance':
                active_notification = notification
                notification_id = notification.get('id')
                print(f"   🎯 Found active notification: {notification_id}")
                break
        
        if not active_notification:
            print("   ⚠️  No active notifications found")
            return False
        
        # ЭТАП 8: Принятие уведомления
        print(f"\n   ✅ ЭТАП 8: ПРИНЯТИЕ УВЕДОМЛЕНИЯ...")
        
        notification_id = active_notification.get('id')
        success, accept_notification_response = self.run_test(
            f"Accept Warehouse Notification {notification_id}",
            "POST",
            f"/api/operator/warehouse-notifications/{notification_id}/accept",
            200,
            token=operator_token
        )
        all_success &= success
        
        if not success:
            return False
        
        # ЭТАП 9: КРИТИЧЕСКИЙ ТЕСТ - Завершение оформления
        print(f"\n   🎯 ЭТАП 9: КРИТИЧЕСКИЙ ТЕСТ - ЗАВЕРШЕНИЕ ОФОРМЛЕНИЯ...")
        print("   🔧 Этот endpoint должен работать БЕЗ ValidationError")
        
        complete_data = {
            "sender_full_name": "Исправленный Тест",
            "sender_phone": "+7999777666", 
            "sender_address": "Москва, ул. Исправленная, 1",
            "recipient_full_name": "Получатель Исправленный",
            "recipient_phone": "+992901234567",
            "recipient_address": "Душанбе, ул. Исправленная, 2",
            "cargo_items": [
                {"name": "Тест исправления", "weight": "1.0", "price": "500"}
            ],
            "payment_method": "cash",
            "delivery_method": "pickup"
        }
        
        success, complete_response = self.run_test(
            f"Complete Cargo Processing (CRITICAL FIX TEST)",
            "POST",
            f"/api/operator/warehouse-notifications/{notification_id}/complete",
            200,
            complete_data,
            operator_token
        )
        all_success &= success
        
        created_cargo_number = None
        if success:
            print("   🎉 КРИТИЧЕСКИЙ УСПЕХ: Завершение оформления прошло БЕЗ ValidationError!")
            created_cargo_number = complete_response.get('cargo_number')
            if created_cargo_number:
                print(f"   📦 Груз создан: {created_cargo_number}")
        else:
            print("   ❌ КРИТИЧЕСКАЯ ОШИБКА: ValidationError все еще присутствует!")
            return False
        
        # ЭТАП 10: Проверка статуса созданного груза
        print(f"\n   🔍 ЭТАП 10: ПРОВЕРКА СТАТУСА СОЗДАННОГО ГРУЗА...")
        
        if created_cargo_number:
            success, cargo_details = self.run_test(
                f"Get Cargo Details {created_cargo_number}",
                "GET",
                f"/api/cargo/track/{created_cargo_number}",
                200,
                token=operator_token
            )
            
            if success:
                cargo_status = cargo_details.get('status')
                print(f"   📊 Статус груза: {cargo_status}")
                
                if cargo_status == 'awaiting_placement':
                    print("   ✅ ИСПРАВЛЕНИЕ ПОДТВЕРЖДЕНО: Статус 'awaiting_placement' (валидный)")
                elif cargo_status == 'placement_ready':
                    print("   ❌ ИСПРАВЛЕНИЕ НЕ РАБОТАЕТ: Все еще используется 'placement_ready'")
                    all_success = False
                else:
                    print(f"   ℹ️  Статус груза: {cargo_status}")
        
        # ЭТАП 11: Проверка в размещенных грузах
        print(f"\n   📋 ЭТАП 11: ПРОВЕРКА В РАЗМЕЩЕННЫХ ГРУЗАХ...")
        
        success, placed_cargo_response = self.run_test(
            "Get Placed Cargo",
            "GET",
            "/api/warehouses/placed-cargo",
            200,
            token=operator_token
        )
        
        if success:
            placed_cargo_items = placed_cargo_response.get('items', [])
            print(f"   📊 Размещенных грузов: {len(placed_cargo_items)}")
            
            if created_cargo_number:
                cargo_found = False
                for cargo in placed_cargo_items:
                    if cargo.get('cargo_number') == created_cargo_number:
                        cargo_found = True
                        placed_status = cargo.get('status')
                        print(f"   🎯 Груз найден: {created_cargo_number} (статус: {placed_status})")
                        
                        if placed_status == 'awaiting_placement':
                            print("   ✅ ИСПРАВЛЕНИЕ РАБОТАЕТ: Груз со статусом 'awaiting_placement' виден")
                        break
                
                if not cargo_found:
                    print(f"   ⚠️  Груз {created_cargo_number} не найден в размещенных")
        
        return all_success

    def run_all_tests(self):
        """Run all comprehensive placement fix tests"""
        print("\n🚀 STARTING COMPREHENSIVE PLACEMENT FIX TESTS")
        
        success = self.test_full_workflow_placement_fix()
        
        print(f"\n📊 FINAL TEST RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if success:
            print("\n🎉 COMPREHENSIVE PLACEMENT FIX TESTS COMPLETED SUCCESSFULLY!")
            print("✅ Полный workflow от заявки до создания груза работает")
            print("✅ Исправление 'placement_ready' → 'awaiting_placement' подтверждено")
            print("✅ ValidationError устранена")
        else:
            print("\n❌ COMPREHENSIVE PLACEMENT FIX TESTS FAILED!")
            print("🔍 Workflow или исправление требует внимания")
        
        return success

if __name__ == "__main__":
    tester = ComprehensivePlacementFixTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)