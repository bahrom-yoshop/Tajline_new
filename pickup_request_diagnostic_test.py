#!/usr/bin/env python3
"""
PICKUP REQUEST DIAGNOSTIC TEST FOR TAJLINE.TJ
Диагностика кнопки "Продолжить оформление" и определение pickup_request_id

ЦЕЛЬ: Понять почему функция handleAcceptWarehouseDelivery не вызывает API или не выводит консольные логи.

КРИТИЧЕСКИЕ ПРОВЕРКИ:
- Какие уведомления есть в системе?
- Есть ли у уведомления №100010 pickup_request_id?
- Если есть, то работает ли endpoint /api/operator/pickup-requests/{pickup_request_id}?
- Почему консольные логи не показываются при нажатии "Продолжить оформление"?
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class PickupRequestDiagnosticTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.operator_token = None
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🔍 PICKUP REQUEST DIAGNOSTIC TEST FOR TAJLINE.TJ")
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

    def test_operator_authentication(self):
        """Test 1: Авторизация оператора (+79777888999/warehouse123)"""
        print("\n🔐 ЭТАП 1: АВТОРИЗАЦИЯ ОПЕРАТОРА")
        print("   📋 Авторизация оператора (+79777888999/warehouse123)")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Operator Authentication (+79777888999/warehouse123)",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        
        if success and 'access_token' in login_response:
            self.operator_token = login_response['access_token']
            operator_user = login_response.get('user', {})
            operator_role = operator_user.get('role')
            operator_name = operator_user.get('full_name')
            operator_phone = operator_user.get('phone')
            operator_user_number = operator_user.get('user_number')
            
            print(f"   ✅ Operator login successful!")
            print(f"   👤 Name: {operator_name}")
            print(f"   📞 Phone: {operator_phone}")
            print(f"   👑 Role: {operator_role}")
            print(f"   🆔 User Number: {operator_user_number}")
            print(f"   🔑 JWT Token: {self.operator_token[:50]}...")
            
            # Verify role is warehouse_operator
            if operator_role == 'warehouse_operator':
                print("   ✅ Operator role correctly set to 'warehouse_operator'")
                return True
            else:
                print(f"   ❌ Operator role incorrect: expected 'warehouse_operator', got '{operator_role}'")
                return False
        else:
            print("   ❌ Operator login failed - no access token received")
            print(f"   📄 Response: {login_response}")
            return False

    def test_get_all_warehouse_notifications(self):
        """Test 2: Получить список всех уведомлений оператора: GET /api/operator/warehouse-notifications"""
        print("\n📋 ЭТАП 2: ПОЛУЧЕНИЕ ВСЕХ УВЕДОМЛЕНИЙ СКЛАДА")
        print("   📋 GET /api/operator/warehouse-notifications")
        
        if not self.operator_token:
            print("   ❌ No operator token available")
            return False, []
        
        success, notifications_response = self.run_test(
            "Get All Warehouse Notifications",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=self.operator_token
        )
        
        if success:
            notifications = notifications_response if isinstance(notifications_response, list) else []
            notification_count = len(notifications)
            
            print(f"   ✅ Found {notification_count} warehouse notifications")
            
            # Display all notifications with their IDs and key information
            print("\n   📋 СПИСОК ВСЕХ УВЕДОМЛЕНИЙ:")
            for i, notification in enumerate(notifications, 1):
                notification_id = notification.get('id', 'N/A')
                notification_number = notification.get('notification_number', 'N/A')
                pickup_request_id = notification.get('pickup_request_id', 'N/A')
                status = notification.get('status', 'N/A')
                sender_name = notification.get('sender_full_name', 'N/A')
                created_at = notification.get('created_at', 'N/A')
                
                print(f"   {i}. ID: {notification_id}")
                print(f"      Number: {notification_number}")
                print(f"      pickup_request_id: {pickup_request_id}")
                print(f"      Status: {status}")
                print(f"      Sender: {sender_name}")
                print(f"      Created: {created_at}")
                print(f"      ---")
            
            return True, notifications
        else:
            print("   ❌ Failed to get warehouse notifications")
            return False, []

    def test_find_notification_100010(self, notifications):
        """Test 3: Найти уведомление №100010 и проверить его структуру"""
        print("\n🔍 ЭТАП 3: ПОИСК УВЕДОМЛЕНИЯ №100010")
        print("   📋 Поиск уведомления №100010 (которое показывается в UI)")
        
        # Search for notification #100010
        notification_100010 = None
        for notification in notifications:
            notification_number = str(notification.get('notification_number', ''))
            notification_id = str(notification.get('id', ''))
            
            # Check both notification_number and id fields
            if notification_number == '100010' or notification_id == '100010':
                notification_100010 = notification
                break
        
        if notification_100010:
            print(f"   ✅ Found notification #100010!")
            
            # Analyze the notification structure
            print("\n   📊 СТРУКТУРА УВЕДОМЛЕНИЯ #100010:")
            for key, value in notification_100010.items():
                print(f"   {key}: {value}")
            
            # Check for pickup_request_id
            pickup_request_id = notification_100010.get('pickup_request_id')
            
            print(f"\n   🔍 КРИТИЧЕСКАЯ ПРОВЕРКА - pickup_request_id:")
            if pickup_request_id and pickup_request_id != 'N/A' and pickup_request_id is not None:
                print(f"   ✅ pickup_request_id НАЙДЕН: {pickup_request_id}")
                return True, pickup_request_id, notification_100010
            else:
                print(f"   ❌ pickup_request_id НЕ НАЙДЕН или пустой: {pickup_request_id}")
                return False, None, notification_100010
        else:
            print("   ❌ Notification #100010 NOT FOUND!")
            print("   📋 Available notification numbers:")
            for notification in notifications:
                notification_number = notification.get('notification_number', 'N/A')
                notification_id = notification.get('id', 'N/A')
                print(f"      - Number: {notification_number}, ID: {notification_id}")
            
            return False, None, None

    def test_pickup_request_endpoint(self, pickup_request_id):
        """Test 4: Если pickup_request_id есть, протестировать endpoint GET /api/operator/pickup-requests/{pickup_request_id}"""
        print(f"\n🔗 ЭТАП 4: ТЕСТИРОВАНИЕ ENDPOINT /api/operator/pickup-requests/{pickup_request_id}")
        print(f"   📋 GET /api/operator/pickup-requests/{pickup_request_id}")
        
        if not self.operator_token:
            print("   ❌ No operator token available")
            return False
        
        success, pickup_request_response = self.run_test(
            f"Get Pickup Request Details ({pickup_request_id})",
            "GET",
            f"/api/operator/pickup-requests/{pickup_request_id}",
            200,
            token=self.operator_token
        )
        
        if success:
            print(f"   ✅ Endpoint /api/operator/pickup-requests/{pickup_request_id} РАБОТАЕТ!")
            
            # Analyze the pickup request structure
            print("\n   📊 СТРУКТУРА PICKUP REQUEST:")
            for key, value in pickup_request_response.items():
                print(f"   {key}: {value}")
            
            # Check for key fields that might be needed for "Продолжить оформление"
            key_fields = ['id', 'request_number', 'sender_full_name', 'sender_phone', 'pickup_address', 'status']
            missing_fields = []
            
            for field in key_fields:
                if field not in pickup_request_response:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ⚠️  Missing key fields: {missing_fields}")
            else:
                print("   ✅ All key fields present for pickup request processing")
            
            return True
        else:
            print(f"   ❌ Endpoint /api/operator/pickup-requests/{pickup_request_id} НЕ РАБОТАЕТ!")
            return False

    def test_find_notification_with_pickup_request_id(self, notifications):
        """Test 5: Если pickup_request_id НЕТ у #100010, найти уведомление с pickup_request_id и протестировать его"""
        print("\n🔍 ЭТАП 5: ПОИСК УВЕДОМЛЕНИЯ С pickup_request_id")
        print("   📋 Поиск любого уведомления с непустым pickup_request_id")
        
        notifications_with_pickup_id = []
        
        for notification in notifications:
            pickup_request_id = notification.get('pickup_request_id')
            if pickup_request_id and pickup_request_id != 'N/A' and pickup_request_id is not None:
                notifications_with_pickup_id.append({
                    'notification': notification,
                    'pickup_request_id': pickup_request_id
                })
        
        if notifications_with_pickup_id:
            print(f"   ✅ Found {len(notifications_with_pickup_id)} notifications with pickup_request_id")
            
            # Test the first one
            test_notification = notifications_with_pickup_id[0]
            notification = test_notification['notification']
            pickup_request_id = test_notification['pickup_request_id']
            
            notification_number = notification.get('notification_number', 'N/A')
            notification_id = notification.get('id', 'N/A')
            
            print(f"   🔍 Testing notification: Number={notification_number}, ID={notification_id}")
            print(f"   🔍 pickup_request_id: {pickup_request_id}")
            
            # Test the pickup request endpoint
            success = self.test_pickup_request_endpoint(pickup_request_id)
            
            if success:
                print(f"   ✅ Pickup request endpoint working for notification {notification_number}")
                return True, pickup_request_id, notification
            else:
                print(f"   ❌ Pickup request endpoint failed for notification {notification_number}")
                return False, pickup_request_id, notification
        else:
            print("   ❌ NO notifications found with pickup_request_id!")
            print("   📋 This might be the root cause of the 'Продолжить оформление' button issue")
            return False, None, None

    def test_console_log_investigation(self, notification_100010):
        """Test 6: Исследование проблемы с консольными логами"""
        print("\n🔍 ЭТАП 6: ИССЛЕДОВАНИЕ ПРОБЛЕМЫ С КОНСОЛЬНЫМИ ЛОГАМИ")
        print("   📋 Анализ возможных причин отсутствия консольных логов при нажатии 'Продолжить оформление'")
        
        if notification_100010:
            print("\n   📊 АНАЛИЗ УВЕДОМЛЕНИЯ #100010:")
            
            # Check notification status
            status = notification_100010.get('status', 'N/A')
            print(f"   Status: {status}")
            
            if status == 'completed':
                print("   ⚠️  ВОЗМОЖНАЯ ПРИЧИНА: Уведомление уже обработано (status: completed)")
                print("   💡 Кнопка 'Продолжить оформление' может быть неактивна для завершенных уведомлений")
            elif status == 'pending_acceptance':
                print("   ✅ Уведомление ожидает принятия (status: pending_acceptance)")
                print("   💡 Кнопка должна быть активна")
            else:
                print(f"   ⚠️  Неожиданный статус: {status}")
            
            # Check pickup_request_id again
            pickup_request_id = notification_100010.get('pickup_request_id')
            if not pickup_request_id or pickup_request_id == 'N/A':
                print("   ❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: pickup_request_id отсутствует!")
                print("   💡 Функция handleAcceptWarehouseDelivery не может получить pickup_request_id")
                print("   💡 Это объясняет отсутствие API вызовов и консольных логов")
            else:
                print(f"   ✅ pickup_request_id присутствует: {pickup_request_id}")
            
            # Check other required fields
            required_fields = ['id', 'notification_number', 'sender_full_name', 'cargo_items']
            missing_fields = []
            
            for field in required_fields:
                if field not in notification_100010 or not notification_100010.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ⚠️  Отсутствующие поля: {missing_fields}")
                print("   💡 Это может влиять на работу функции handleAcceptWarehouseDelivery")
            else:
                print("   ✅ Все основные поля присутствуют")
            
        else:
            print("   ❌ Notification #100010 not available for analysis")
        
        # General recommendations
        print("\n   💡 РЕКОМЕНДАЦИИ ПО ДИАГНОСТИКЕ:")
        print("   1. Проверить browser console на наличие JavaScript ошибок")
        print("   2. Убедиться что pickup_request_id передается в функцию handleAcceptWarehouseDelivery")
        print("   3. Проверить что endpoint /api/operator/pickup-requests/{pickup_request_id} доступен")
        print("   4. Убедиться что уведомление имеет статус 'pending_acceptance'")
        print("   5. Проверить что все необходимые поля присутствуют в уведомлении")

    def run_full_diagnostic(self):
        """Run complete diagnostic test"""
        print("🚀 STARTING FULL PICKUP REQUEST DIAGNOSTIC")
        
        # Step 1: Operator Authentication
        auth_success = self.test_operator_authentication()
        if not auth_success:
            print("\n❌ DIAGNOSTIC FAILED: Cannot authenticate operator")
            return False
        
        # Step 2: Get All Warehouse Notifications
        notifications_success, notifications = self.test_get_all_warehouse_notifications()
        if not notifications_success:
            print("\n❌ DIAGNOSTIC FAILED: Cannot get warehouse notifications")
            return False
        
        # Step 3: Find Notification #100010
        found_100010, pickup_request_id_100010, notification_100010 = self.test_find_notification_100010(notifications)
        
        # Step 4: Test pickup request endpoint if pickup_request_id exists for #100010
        if found_100010 and pickup_request_id_100010:
            endpoint_success = self.test_pickup_request_endpoint(pickup_request_id_100010)
            if endpoint_success:
                print(f"\n✅ ДИАГНОСТИКА ЗАВЕРШЕНА: Уведомление #100010 имеет pickup_request_id и endpoint работает")
            else:
                print(f"\n⚠️  ПРОБЛЕМА НАЙДЕНА: pickup_request_id есть, но endpoint не работает")
        else:
            # Step 5: Find any notification with pickup_request_id
            found_alternative, pickup_request_id_alt, notification_alt = self.test_find_notification_with_pickup_request_id(notifications)
            
            if found_alternative:
                print(f"\n⚠️  ПРОБЛЕМА НАЙДЕНА: У уведомления #100010 нет pickup_request_id, но другие уведомления имеют")
            else:
                print(f"\n❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: НИ ОДНО уведомление не имеет pickup_request_id")
        
        # Step 6: Console Log Investigation
        self.test_console_log_investigation(notification_100010)
        
        # Final Summary
        print("\n" + "="*80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ")
        print("="*80)
        
        print(f"Всего тестов выполнено: {self.tests_run}")
        print(f"Тестов прошло успешно: {self.tests_passed}")
        print(f"Успешность: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        print("\n🔍 КЛЮЧЕВЫЕ НАХОДКИ:")
        
        if notification_100010:
            pickup_request_id = notification_100010.get('pickup_request_id')
            status = notification_100010.get('status', 'N/A')
            
            print(f"✅ Уведомление #100010 найдено")
            print(f"📊 Статус уведомления: {status}")
            
            if pickup_request_id and pickup_request_id != 'N/A':
                print(f"✅ pickup_request_id найден: {pickup_request_id}")
                print(f"💡 ВЕРОЯТНАЯ ПРИЧИНА: Проблема в frontend коде или endpoint не работает")
            else:
                print(f"❌ pickup_request_id НЕ НАЙДЕН")
                print(f"💡 ОСНОВНАЯ ПРИЧИНА: handleAcceptWarehouseDelivery не может получить pickup_request_id")
                print(f"💡 РЕШЕНИЕ: Добавить pickup_request_id к уведомлению #100010")
        else:
            print(f"❌ Уведомление #100010 НЕ НАЙДЕНО")
            print(f"💡 ОСНОВНАЯ ПРИЧИНА: UI показывает несуществующее уведомление")
        
        print("\n🎯 РЕКОМЕНДАЦИИ:")
        print("1. Проверить откуда UI берет уведомление #100010")
        print("2. Убедиться что у уведомления есть pickup_request_id")
        print("3. Проверить что endpoint /api/operator/pickup-requests/{pickup_request_id} работает")
        print("4. Добавить console.log в handleAcceptWarehouseDelivery для отладки")
        print("5. Проверить что кнопка 'Продолжить оформление' правильно передает данные")
        
        return True

if __name__ == "__main__":
    tester = PickupRequestDiagnosticTester()
    tester.run_full_diagnostic()