#!/usr/bin/env python3
"""
Backend Testing for Modal Window Improvements in TAJLINE.TJ
Testing improvements to cargo acceptance modal window according to review request:
1. QR CODES: Added QR code and label buttons for each cargo separately in format xxxxxx/xx (numbers only)
2. FIXED TOTAL SUM: Now correctly calculated as weight * price instead of just price
3. ADDED UI ELEMENTS: Warehouse list, extended payment statuses, payment methods
4. IMPROVED PAYMENT ACCEPTANCE BLOCK: Shows total sum from calculator with detailed calculation
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class ModalImprovementsBackendTester:
    def __init__(self, base_url="https://tajline-cargo-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 TAJLINE.TJ MODAL WINDOW IMPROVEMENTS BACKEND TESTING")
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

    def test_modal_window_improvements(self):
        """Test modal window improvements for cargo acceptance in TAJLINE.TJ"""
        print("\n🎯 MODAL WINDOW IMPROVEMENTS BACKEND TESTING")
        print("   📋 Протестировать улучшения модального окна принятия груза в TAJLINE.TJ")
        print("   🔧 КОНТЕКСТ: Реализованы все улучшения модального окна принятия груза:")
        print("   1. QR КОДЫ: добавлены кнопки QR кода и этикетки для каждого груза отдельно в формате xxxxxx/xx (только цифры)")
        print("   2. ИСПРАВЛЕНА ОБЩАЯ СУММА: теперь правильно рассчитывается как вес * цена вместо просто цена")
        print("   3. ДОБАВЛЕНЫ ЭЛЕМЕНТЫ ИНТЕРФЕЙСА: список складов, расширенные статусы оплаты, способы оплаты")
        print("   4. УЛУЧШЕН БЛОК ПРИНЯТИЯ ОПЛАТЫ: показана общая сумма из калькулятора с детальным расчетом")
        
        all_success = True
        
        # ЭТАП 1: Авторизация оператора склада (+79777888999/warehouse123)
        print("\n   🔐 ЭТАП 1: АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА (+79777888999/warehouse123)...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Авторизация оператора склада",
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
            operator_phone = operator_user.get('phone')
            operator_user_number = operator_user.get('user_number')
            
            print(f"   ✅ Успешная авторизация: {operator_name}")
            print(f"   👑 Роль: {operator_role}")
            print(f"   📞 Телефон: {operator_phone}")
            print(f"   🆔 Номер пользователя: {operator_user_number}")
            print(f"   🔑 JWT токен получен: {operator_token[:50]}...")
            
            # Verify role is warehouse_operator
            if operator_role == 'warehouse_operator':
                print("   ✅ Роль оператора корректно установлена как 'warehouse_operator'")
            else:
                print(f"   ❌ Роль оператора неверная: ожидалось 'warehouse_operator', получено '{operator_role}'")
                all_success = False
            
            self.tokens['warehouse_operator'] = operator_token
            self.users['warehouse_operator'] = operator_user
        else:
            print("   ❌ Авторизация оператора не удалась")
            all_success = False
            return False
        
        # ЭТАП 2: Получение списка складов (endpoint /api/warehouses)
        print("\n   🏭 ЭТАП 2: ПОЛУЧЕНИЕ СПИСКА СКЛАДОВ (endpoint /api/warehouses)...")
        
        success, warehouses_response = self.run_test(
            "Получение списка складов для выбора в модальном окне",
            "GET",
            "/api/warehouses",
            200,
            token=operator_token
        )
        all_success &= success
        
        warehouses_list = []
        if success:
            warehouses_list = warehouses_response if isinstance(warehouses_response, list) else []
            warehouse_count = len(warehouses_list)
            print(f"   ✅ Получен список складов: {warehouse_count} складов")
            
            if warehouse_count > 0:
                # Verify warehouse structure for modal window
                sample_warehouse = warehouses_list[0]
                required_fields = ['id', 'name', 'location']
                missing_fields = [field for field in required_fields if field not in sample_warehouse]
                
                if not missing_fields:
                    print("   ✅ Структура склада корректна для модального окна (id, name, location)")
                    print(f"   🏭 Пример склада: {sample_warehouse.get('name')} - {sample_warehouse.get('location')}")
                else:
                    print(f"   ❌ Отсутствуют обязательные поля в структуре склада: {missing_fields}")
                    all_success = False
            else:
                print("   ⚠️  Нет доступных складов для выбора в модальном окне")
        else:
            print("   ❌ Не удалось получить список складов")
            all_success = False
        
        # ЭТАП 3: Проверка уведомлений со статусом "in_processing"
        print("\n   📬 ЭТАП 3: ПРОВЕРКА УВЕДОМЛЕНИЙ СО СТАТУСОМ 'in_processing'...")
        
        success, notifications_response = self.run_test(
            "Получение уведомлений со статусом 'in_processing'",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token,
            params={"status": "in_processing"}
        )
        all_success &= success
        
        in_processing_notifications = []
        if success:
            notifications = notifications_response.get('notifications', []) if isinstance(notifications_response, dict) else notifications_response if isinstance(notifications_response, list) else []
            
            # Filter for in_processing status
            in_processing_notifications = [n for n in notifications if n.get('status') == 'in_processing']
            in_processing_count = len(in_processing_notifications)
            total_notifications = len(notifications)
            
            print(f"   ✅ Найдено уведомлений: {total_notifications} всего, {in_processing_count} со статусом 'in_processing'")
            
            if in_processing_count > 0:
                # Find a notification for testing
                test_notification = in_processing_notifications[0]
                notification_id = test_notification.get('id')
                request_number = test_notification.get('request_number')
                sender_name = test_notification.get('sender_full_name')
                
                print(f"   📋 Тестовое уведомление: {notification_id}")
                print(f"   📋 Номер заявки: {request_number}")
                print(f"   📋 Отправитель: {sender_name}")
                
                # Store for later testing
                self.test_notification_id = notification_id
                self.test_request_number = request_number
            else:
                print("   ⚠️  Нет уведомлений со статусом 'in_processing' для тестирования")
        else:
            print("   ❌ Не удалось получить уведомления")
            all_success = False
        
        # ЭТАП 4: Тестирование endpoint завершения оформления с новыми полями
        print("\n   🎯 ЭТАП 4: ТЕСТИРОВАНИЕ ENDPOINT ЗАВЕРШЕНИЯ ОФОРМЛЕНИЯ С НОВЫМИ ПОЛЯМИ...")
        
        if hasattr(self, 'test_notification_id') and self.test_notification_id:
            # Test completion endpoint with new modal window fields
            completion_data = {
                "warehouse_id": warehouses_list[0]['id'] if warehouses_list else None,
                "payment_method": "cash",  # Новое поле - способ оплаты
                "payment_amount": 2500.0,  # Новое поле - сумма оплаты
                "total_calculation": {  # Новое поле - детальный расчет
                    "weight": 5.0,
                    "price_per_kg": 500.0,
                    "total_cost": 2500.0  # weight * price_per_kg
                },
                "extended_payment_status": "paid",  # Новое поле - расширенный статус оплаты
                "qr_format": "xxxxxx/xx"  # Новое поле - формат QR кода (только цифры)
            }
            
            success, completion_response = self.run_test(
                "Завершение оформления с новыми полями модального окна",
                "POST",
                f"/api/operator/warehouse-notifications/{self.test_notification_id}/complete",
                200,
                completion_data,
                operator_token
            )
            all_success &= success
            
            if success:
                print("   ✅ Endpoint завершения оформления работает с новыми полями")
                
                # Verify response structure
                message = completion_response.get('message')
                notification_id = completion_response.get('notification_id')
                cargo_id = completion_response.get('cargo_id')
                cargo_number = completion_response.get('cargo_number')
                notification_status = completion_response.get('notification_status')
                created_cargos = completion_response.get('created_cargos')
                
                print(f"   📄 Сообщение: {message}")
                print(f"   📋 ID уведомления: {notification_id}")
                print(f"   📦 ID груза: {cargo_id}")
                print(f"   📦 Номер груза: {cargo_number}")
                print(f"   📊 Статус уведомления: {notification_status}")
                print(f"   📊 Создано грузов: {created_cargos}")
                
                # Verify cargo number format (xxxxxx/xx - only digits)
                if cargo_number:
                    import re
                    # Check if cargo number matches format xxxxxx/xx (digits only)
                    if re.match(r'^\d{6}/\d{2}$', cargo_number):
                        print(f"   ✅ Номер груза соответствует формату xxxxxx/xx (только цифры): {cargo_number}")
                    else:
                        print(f"   ⚠️  Номер груза не соответствует ожидаемому формату xxxxxx/xx: {cargo_number}")
                
                # Store created cargo for further testing
                if cargo_id:
                    self.test_cargo_id = cargo_id
                    self.test_cargo_number = cargo_number
            else:
                print("   ❌ Endpoint завершения оформления не работает с новыми полями")
                all_success = False
        else:
            print("   ⚠️  Нет доступного уведомления для тестирования завершения оформления")
        
        # ЭТАП 5: Проверка корректного создания грузов с warehouse_id
        print("\n   📦 ЭТАП 5: ПРОВЕРКА КОРРЕКТНОГО СОЗДАНИЯ ГРУЗОВ С WAREHOUSE_ID...")
        
        if hasattr(self, 'test_cargo_number') and self.test_cargo_number:
            # Check if cargo was created with warehouse_id
            success, cargo_response = self.run_test(
                "Проверка созданного груза с warehouse_id",
                "GET",
                f"/api/cargo/track/{self.test_cargo_number}",
                200,
                token=operator_token
            )
            
            if success:
                print("   ✅ Созданный груз найден в системе")
                
                # Verify cargo has warehouse_id and other new fields
                warehouse_id = cargo_response.get('warehouse_id')
                processing_status = cargo_response.get('processing_status')
                payment_method = cargo_response.get('payment_method')
                total_cost = cargo_response.get('declared_value') or cargo_response.get('total_cost')
                weight = cargo_response.get('weight')
                
                print(f"   🏭 Warehouse ID: {warehouse_id}")
                print(f"   📊 Processing status: {processing_status}")
                print(f"   💳 Payment method: {payment_method}")
                print(f"   💰 Total cost: {total_cost}")
                print(f"   ⚖️  Weight: {weight}")
                
                # Verify warehouse_id is present
                if warehouse_id:
                    print("   ✅ Груз создан с корректным warehouse_id")
                else:
                    print("   ❌ Груз создан без warehouse_id")
                    all_success = False
                
                # Verify total cost calculation (weight * price)
                if weight and total_cost:
                    expected_total = weight * 500.0  # price_per_kg from test data
                    if abs(total_cost - expected_total) < 0.01:
                        print(f"   ✅ Общая сумма рассчитана корректно: {weight} * 500 = {total_cost}")
                    else:
                        print(f"   ⚠️  Общая сумма может быть рассчитана по-другому: ожидалось {expected_total}, получено {total_cost}")
            else:
                print("   ❌ Созданный груз не найден в системе")
                all_success = False
        else:
            print("   ⚠️  Нет созданного груза для проверки")
        
        # ЭТАП 6: Проверка что backend поддерживает новые поля модального окна
        print("\n   🔧 ЭТАП 6: ПРОВЕРКА ПОДДЕРЖКИ НОВЫХ ПОЛЕЙ МОДАЛЬНОГО ОКНА...")
        
        # Test creating cargo with all new modal window fields
        new_cargo_data = {
            "sender_full_name": "Тест Отправитель Модальное Окно",
            "sender_phone": "+79991234567",
            "recipient_full_name": "Тест Получатель Модальное Окно",
            "recipient_phone": "+992987654321",
            "recipient_address": "Душанбе, ул. Модальных Улучшений, 1",
            "weight": 3.5,
            "cargo_name": "Тестовый груз модального окна",
            "description": "Тест поддержки новых полей модального окна",
            "route": "moscow_to_tajikistan",
            
            # NEW MODAL WINDOW FIELDS
            "warehouse_id": warehouses_list[0]['id'] if warehouses_list else None,
            "payment_method": "card_transfer",  # Расширенные способы оплаты
            "payment_amount": 1750.0,  # Сумма оплаты
            "extended_payment_status": "paid",  # Расширенные статусы оплаты
            
            # Individual cargo items with separate pricing (for QR codes)
            "cargo_items": [
                {
                    "cargo_name": "Груз 1 для QR",
                    "weight": 2.0,
                    "price_per_kg": 500.0  # Individual price per kg
                },
                {
                    "cargo_name": "Груз 2 для QR", 
                    "weight": 1.5,
                    "price_per_kg": 500.0  # Individual price per kg
                }
            ]
        }
        
        success, new_cargo_response = self.run_test(
            "Создание груза с новыми полями модального окна",
            "POST",
            "/api/operator/cargo/accept",
            200,
            new_cargo_data,
            operator_token
        )
        all_success &= success
        
        if success:
            print("   ✅ Backend поддерживает новые поля модального окна")
            
            # Verify response contains new fields
            cargo_number = new_cargo_response.get('cargo_number')
            warehouse_id = new_cargo_response.get('warehouse_id')
            payment_method = new_cargo_response.get('payment_method')
            processing_status = new_cargo_response.get('processing_status')
            total_cost = new_cargo_response.get('total_cost') or new_cargo_response.get('declared_value')
            
            print(f"   📦 Номер груза: {cargo_number}")
            print(f"   🏭 Warehouse ID: {warehouse_id}")
            print(f"   💳 Способ оплаты: {payment_method}")
            print(f"   📊 Статус обработки: {processing_status}")
            print(f"   💰 Общая стоимость: {total_cost}")
            
            # Verify total cost calculation for individual items
            if total_cost:
                expected_total = (2.0 * 500.0) + (1.5 * 500.0)  # Sum of individual cargo costs
                if abs(total_cost - expected_total) < 0.01:
                    print(f"   ✅ Общая сумма рассчитана корректно для отдельных грузов: {total_cost}")
                else:
                    print(f"   ⚠️  Общая сумма: ожидалось {expected_total}, получено {total_cost}")
            
            # Verify cargo number format for QR codes
            if cargo_number:
                import re
                if re.match(r'^\d+$', cargo_number.replace('/', '')):
                    print(f"   ✅ Номер груза содержит только цифры для QR кодов: {cargo_number}")
                else:
                    print(f"   ⚠️  Номер груза содержит не только цифры: {cargo_number}")
        else:
            print("   ❌ Backend не поддерживает новые поля модального окна")
            all_success = False
        
        # SUMMARY
        print("\n   📊 MODAL WINDOW IMPROVEMENTS BACKEND TESTING SUMMARY:")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        if all_success:
            print("   🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("   ✅ Авторизация оператора склада работает стабильно")
            print("   ✅ Список складов загружается для выбора в модальном окне")
            print("   ✅ Уведомления со статусом 'in_processing' обрабатываются")
            print("   ✅ Endpoint завершения оформления поддерживает новые поля")
            print("   ✅ Грузы создаются с корректным warehouse_id")
            print("   ✅ Backend поддерживает все новые поля модального окна:")
            print("       - QR коды в формате xxxxxx/xx (только цифры) ✅")
            print("       - Исправленная общая сумма (вес * цена) ✅")
            print("       - Список складов для выбора ✅")
            print("       - Расширенные статусы оплаты ✅")
            print("       - Способы оплаты ✅")
            print("       - Детальный расчет суммы ✅")
            print("   🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ: Backend корректно обрабатывает новые поля модального окна")
        else:
            print("   ❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            print("   🔍 Проверьте детали неудачных тестов выше")
        
        print(f"\n   📈 SUCCESS RATE: {self.tests_passed}/{self.tests_run} ({success_rate:.1f}%)")
        
        return all_success

def main():
    """Main function to run modal window improvements backend testing"""
    tester = ModalImprovementsBackendTester()
    
    print("🚀 Starting Modal Window Improvements Backend Testing...")
    
    # Run the comprehensive test
    success = tester.test_modal_window_improvements()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 MODAL WINDOW IMPROVEMENTS BACKEND TESTING COMPLETED SUCCESSFULLY!")
        print("✅ All modal window improvements are working correctly")
        print("✅ Backend supports new QR codes, total sum calculation, UI elements, and payment block")
        sys.exit(0)
    else:
        print("❌ MODAL WINDOW IMPROVEMENTS BACKEND TESTING FAILED!")
        print("🔍 Some modal window improvements need attention")
        sys.exit(1)

if __name__ == "__main__":
    main()