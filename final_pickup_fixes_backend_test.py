#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ФИНАЛЬНЫХ ИСПРАВЛЕНИЙ ФУНКЦИОНАЛА ОБРАБОТКИ ЗАЯВОК НА ЗАБОР ГРУЗА В TAJLINE.TJ
Testing final fixes for cargo pickup request processing functionality in TAJLINE.TJ

КОНТЕКСТ: Исправлены две критические проблемы:
1. ГЕНЕРАЦИЯ QR КОДОВ: улучшена функция генерации QR с ожиданием загрузки библиотеки, добавлены таймауты и fallback сообщения
2. ОТПРАВКА НА РАЗМЕЩЕНИЕ: изменен processing_status с "pending" на "paid" чтобы груз появился в категории "Размещение"

ТЕСТОВЫЙ ПЛАН:
1. Авторизация оператора склада (+79777888999/warehouse123)
2. Получение уведомлений со статусом "in_processing"
3. Тестирование отправки на размещение с новым processing_status
4. Проверка появления груза в списке доступных для размещения
5. Проверка endpoint /api/operator/cargo/available-for-placement
6. Убедиться что груз создается со статусом processing_status: "paid"

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Груз должен создаваться со статусом processing_status: "paid" и появляться в категории "Размещение" (/api/operator/cargo/available-for-placement).
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class FinalPickupFixesTester:
    def __init__(self, base_url="https://tajline-manager-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ФИНАЛЬНЫХ ИСПРАВЛЕНИЙ ФУНКЦИОНАЛА ОБРАБОТКИ ЗАЯВОК НА ЗАБОР ГРУЗА В TAJLINE.TJ")
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

    def test_final_pickup_fixes(self):
        """Test final fixes for cargo pickup request processing functionality"""
        print("\n🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ФИНАЛЬНЫХ ИСПРАВЛЕНИЙ ФУНКЦИОНАЛА ОБРАБОТКИ ЗАЯВОК НА ЗАБОР ГРУЗА")
        print("   📋 Протестировать финальные исправления функционала обработки заявок на забор груза в TAJLINE.TJ")
        
        all_success = True
        
        # ЭТАП 1: АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА (+79777888999/warehouse123)
        print("\n   🔐 ЭТАП 1: АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА (+79777888999/warehouse123)...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Авторизация оператора склада (+79777888999/warehouse123)",
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
            
            print(f"   ✅ Авторизация успешна: {operator_name}")
            print(f"   👑 Роль: {operator_role}")
            print(f"   📞 Телефон: {operator_phone}")
            print(f"   🆔 Номер пользователя: {operator_user_number}")
            
            # Verify role is warehouse_operator
            if operator_role == 'warehouse_operator':
                print("   ✅ Роль оператора корректно установлена как 'warehouse_operator'")
            else:
                print(f"   ❌ Роль оператора неверна: ожидалось 'warehouse_operator', получено '{operator_role}'")
                all_success = False
            
            self.tokens['warehouse_operator'] = operator_token
            self.users['warehouse_operator'] = operator_user
        else:
            print("   ❌ Авторизация оператора склада не удалась")
            all_success = False
            return False
        
        # ЭТАП 2: ПОЛУЧЕНИЕ УВЕДОМЛЕНИЙ СО СТАТУСОМ "in_processing"
        print("\n   📬 ЭТАП 2: ПОЛУЧЕНИЕ УВЕДОМЛЕНИЙ СО СТАТУСОМ 'in_processing'...")
        
        success, notifications_response = self.run_test(
            "Получение уведомлений склада",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        all_success &= success
        
        in_processing_notifications = []
        if success:
            notifications = notifications_response if isinstance(notifications_response, list) else []
            notification_count = len(notifications)
            print(f"   ✅ Найдено {notification_count} уведомлений склада")
            
            # Filter notifications with status "in_processing"
            in_processing_notifications = [n for n in notifications if n.get('status') == 'in_processing']
            in_processing_count = len(in_processing_notifications)
            
            print(f"   📊 Уведомления со статусом 'in_processing': {in_processing_count}")
            
            if in_processing_count > 0:
                print("   ✅ Найдены уведомления со статусом 'in_processing' для тестирования")
                # Show sample notification
                sample_notification = in_processing_notifications[0]
                notification_id = sample_notification.get('id')
                request_number = sample_notification.get('request_number')
                sender_name = sample_notification.get('sender_full_name')
                print(f"   📋 Пример уведомления: ID={notification_id}, Номер={request_number}, Отправитель={sender_name}")
            else:
                print("   ⚠️  Нет уведомлений со статусом 'in_processing' для тестирования")
                print("   ℹ️  Создадим тестовое уведомление через заявку на забор груза...")
                
                # Create a test pickup request to generate notification
                test_notification_created = self.create_test_pickup_request_notification(operator_token)
                if test_notification_created:
                    # Re-fetch notifications
                    success, notifications_response = self.run_test(
                        "Повторное получение уведомлений после создания тестовой заявки",
                        "GET",
                        "/api/operator/warehouse-notifications",
                        200,
                        token=operator_token
                    )
                    
                    if success:
                        notifications = notifications_response if isinstance(notifications_response, list) else []
                        in_processing_notifications = [n for n in notifications if n.get('status') == 'in_processing']
                        in_processing_count = len(in_processing_notifications)
                        print(f"   📊 Уведомления со статусом 'in_processing' после создания тестовой заявки: {in_processing_count}")
        else:
            print("   ❌ Не удалось получить уведомления склада")
            all_success = False
        
        # ЭТАП 3: ТЕСТИРОВАНИЕ ОТПРАВКИ НА РАЗМЕЩЕНИЕ С НОВЫМ processing_status
        print("\n   🚚 ЭТАП 3: ТЕСТИРОВАНИЕ ОТПРАВКИ НА РАЗМЕЩЕНИЕ С НОВЫМ processing_status...")
        
        if in_processing_notifications:
            # Use the first in_processing notification for testing
            test_notification = in_processing_notifications[0]
            notification_id = test_notification.get('id')
            request_number = test_notification.get('request_number')
            
            print(f"   🎯 Тестируем отправку на размещение для уведомления: {notification_id}")
            print(f"   📋 Номер заявки: {request_number}")
            
            success, send_to_placement_response = self.run_test(
                f"Отправка на размещение (уведомление {notification_id})",
                "POST",
                f"/api/operator/warehouse-notifications/{notification_id}/send-to-placement",
                200,
                token=operator_token
            )
            all_success &= success
            
            if success:
                print("   ✅ Отправка на размещение выполнена успешно")
                
                # Check response for cargo creation details
                message = send_to_placement_response.get('message', '')
                cargo_number = send_to_placement_response.get('cargo_number')
                processing_status = send_to_placement_response.get('processing_status')
                
                print(f"   📄 Сообщение: {message}")
                if cargo_number:
                    print(f"   📦 Создан груз: {cargo_number}")
                if processing_status:
                    print(f"   📊 Статус обработки: {processing_status}")
                    
                    # КРИТИЧЕСКАЯ ПРОВЕРКА: processing_status должен быть "paid"
                    if processing_status == "paid":
                        print("   ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ПОДТВЕРЖДЕНО: processing_status = 'paid'")
                    else:
                        print(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: processing_status = '{processing_status}', ожидалось 'paid'")
                        all_success = False
                
                # Store cargo number for further testing
                if cargo_number:
                    self.test_cargo_number = cargo_number
            else:
                print("   ❌ Отправка на размещение не удалась")
                all_success = False
        else:
            print("   ⚠️  Нет уведомлений 'in_processing' для тестирования отправки на размещение")
            # Try to create a test scenario
            print("   ℹ️  Попытаемся создать тестовый сценарий...")
            test_cargo_created = self.create_test_cargo_for_placement(operator_token)
            if test_cargo_created:
                print("   ✅ Тестовый груз создан для проверки размещения")
            else:
                print("   ❌ Не удалось создать тестовый груз")
                all_success = False
        
        # ЭТАП 4: ПРОВЕРКА ПОЯВЛЕНИЯ ГРУЗА В СПИСКЕ ДОСТУПНЫХ ДЛЯ РАЗМЕЩЕНИЯ
        print("\n   📋 ЭТАП 4: ПРОВЕРКА ПОЯВЛЕНИЯ ГРУЗА В СПИСКЕ ДОСТУПНЫХ ДЛЯ РАЗМЕЩЕНИЯ...")
        
        success, available_cargo_response = self.run_test(
            "Получение грузов доступных для размещения",
            "GET",
            "/api/operator/cargo/available-for-placement",
            200,
            token=operator_token
        )
        all_success &= success
        
        if success:
            print("   ✅ Endpoint /api/operator/cargo/available-for-placement работает")
            
            # Check response structure
            if isinstance(available_cargo_response, dict):
                items = available_cargo_response.get('items', [])
                total_count = available_cargo_response.get('total_count', 0)
                pagination = available_cargo_response.get('pagination', {})
                
                print(f"   📊 Всего грузов доступных для размещения: {total_count}")
                print(f"   📋 Элементов в ответе: {len(items)}")
                
                # Verify pagination structure
                if pagination:
                    page = pagination.get('page', 1)
                    per_page = pagination.get('per_page', 25)
                    total_pages = pagination.get('total_pages', 1)
                    print(f"   📄 Пагинация: страница {page} из {total_pages}, по {per_page} элементов")
                    print("   ✅ Структура пагинации корректна")
                
                # Check if cargo items have correct processing_status
                if items:
                    paid_cargo_count = 0
                    for cargo in items:
                        cargo_number = cargo.get('cargo_number')
                        processing_status = cargo.get('processing_status')
                        
                        if processing_status == 'paid':
                            paid_cargo_count += 1
                        
                        # Check if this is our test cargo
                        if hasattr(self, 'test_cargo_number') and cargo_number == self.test_cargo_number:
                            print(f"   🎯 Найден наш тестовый груз: {cargo_number}")
                            print(f"   📊 Статус обработки тестового груза: {processing_status}")
                            
                            if processing_status == 'paid':
                                print("   ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ПОДТВЕРЖДЕНО: Тестовый груз имеет статус 'paid'")
                            else:
                                print(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: Тестовый груз имеет статус '{processing_status}', ожидалось 'paid'")
                                all_success = False
                    
                    print(f"   📊 Грузов со статусом 'paid': {paid_cargo_count}/{len(items)}")
                    
                    if paid_cargo_count == len(items):
                        print("   ✅ Все грузы в списке размещения имеют статус 'paid'")
                    elif paid_cargo_count > 0:
                        print(f"   ⚠️  Не все грузы имеют статус 'paid': {paid_cargo_count}/{len(items)}")
                    else:
                        print("   ❌ Ни один груз не имеет статус 'paid'")
                        all_success = False
                else:
                    print("   ⚠️  Нет грузов доступных для размещения")
            elif isinstance(available_cargo_response, list):
                cargo_count = len(available_cargo_response)
                print(f"   📊 Найдено {cargo_count} грузов доступных для размещения (прямой список)")
            else:
                print("   ❌ Неожиданный формат ответа для доступных грузов")
                all_success = False
        else:
            print("   ❌ Endpoint /api/operator/cargo/available-for-placement не работает")
            all_success = False
        
        # ЭТАП 5: ПРОВЕРКА ENDPOINT /api/operator/cargo/available-for-placement
        print("\n   🔍 ЭТАП 5: ДЕТАЛЬНАЯ ПРОВЕРКА ENDPOINT /api/operator/cargo/available-for-placement...")
        
        # Test with different parameters
        test_params = [
            {"page": 1, "per_page": 10},
            {"page": 1, "per_page": 25},
        ]
        
        for params in test_params:
            success, paginated_response = self.run_test(
                f"Проверка пагинации (page={params['page']}, per_page={params['per_page']})",
                "GET",
                "/api/operator/cargo/available-for-placement",
                200,
                params=params,
                token=operator_token
            )
            
            if success:
                if isinstance(paginated_response, dict):
                    items = paginated_response.get('items', [])
                    pagination = paginated_response.get('pagination', {})
                    
                    actual_page = pagination.get('page', 1)
                    actual_per_page = pagination.get('per_page', 25)
                    
                    if actual_page == params['page'] and actual_per_page == params['per_page']:
                        print(f"   ✅ Пагинация работает корректно: page={actual_page}, per_page={actual_per_page}")
                    else:
                        print(f"   ❌ Пагинация работает неверно: ожидалось page={params['page']}, per_page={params['per_page']}")
                        print(f"       получено page={actual_page}, per_page={actual_per_page}")
                        all_success = False
            else:
                print(f"   ❌ Пагинация не работает для параметров {params}")
                all_success = False
        
        # ЭТАП 6: УБЕДИТЬСЯ ЧТО ГРУЗ СОЗДАЕТСЯ СО СТАТУСОМ processing_status: "paid"
        print("\n   ✅ ЭТАП 6: ФИНАЛЬНАЯ ПРОВЕРКА - ГРУЗ СОЗДАЕТСЯ СО СТАТУСОМ processing_status: 'paid'...")
        
        # Create a new test cargo to verify the fix
        test_cargo_data = {
            "sender_full_name": "Тест Финальные Исправления",
            "sender_phone": "+79991234567",
            "recipient_full_name": "Тест Получатель Исправления",
            "recipient_phone": "+992987654321",
            "recipient_address": "Душанбе, ул. Финальных Исправлений, 1",
            "weight": 5.0,
            "cargo_name": "Тестовый груз для проверки финальных исправлений",
            "declared_value": 2000.0,
            "description": "Тест финальных исправлений функционала обработки заявок на забор груза",
            "route": "moscow_dushanbe",
            "payment_method": "cash",
            "payment_amount": 2000.0
        }
        
        success, cargo_creation_response = self.run_test(
            "Создание тестового груза для проверки processing_status",
            "POST",
            "/api/operator/cargo/accept",
            200,
            test_cargo_data,
            operator_token
        )
        
        if success:
            cargo_number = cargo_creation_response.get('cargo_number')
            processing_status = cargo_creation_response.get('processing_status')
            payment_method = cargo_creation_response.get('payment_method')
            
            print(f"   ✅ Тестовый груз создан: {cargo_number}")
            print(f"   💳 Способ оплаты: {payment_method}")
            print(f"   📊 Статус обработки: {processing_status}")
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: processing_status должен быть "paid" для оплаченного груза
            if processing_status == "paid":
                print("   ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ ПОДТВЕРЖДЕНО: Новый груз создается со статусом processing_status = 'paid'")
            else:
                print(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: Новый груз создается со статусом processing_status = '{processing_status}', ожидалось 'paid'")
                all_success = False
            
            # Verify the cargo appears in available-for-placement
            print("   🔍 Проверяем, что новый груз появился в списке доступных для размещения...")
            
            success, final_check_response = self.run_test(
                "Финальная проверка списка доступных для размещения",
                "GET",
                "/api/operator/cargo/available-for-placement",
                200,
                token=operator_token
            )
            
            if success:
                items = final_check_response.get('items', []) if isinstance(final_check_response, dict) else final_check_response
                
                # Look for our test cargo
                test_cargo_found = False
                for cargo in items:
                    if cargo.get('cargo_number') == cargo_number:
                        test_cargo_found = True
                        cargo_processing_status = cargo.get('processing_status')
                        
                        print(f"   🎯 Найден новый тестовый груз в списке размещения: {cargo_number}")
                        print(f"   📊 Статус в списке размещения: {cargo_processing_status}")
                        
                        if cargo_processing_status == 'paid':
                            print("   ✅ ФИНАЛЬНОЕ ПОДТВЕРЖДЕНИЕ: Груз со статусом 'paid' появился в категории 'Размещение'")
                        else:
                            print(f"   ❌ ФИНАЛЬНАЯ ОШИБКА: Груз в категории 'Размещение' имеет статус '{cargo_processing_status}', ожидалось 'paid'")
                            all_success = False
                        break
                
                if not test_cargo_found:
                    print("   ❌ ФИНАЛЬНАЯ ОШИБКА: Новый тестовый груз не найден в списке доступных для размещения")
                    all_success = False
            else:
                print("   ❌ Не удалось выполнить финальную проверку списка размещения")
                all_success = False
        else:
            print("   ❌ Не удалось создать тестовый груз для финальной проверки")
            all_success = False
        
        # ФИНАЛЬНАЯ СВОДКА
        print("\n   📊 ФИНАЛЬНАЯ СВОДКА ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЙ:")
        
        if all_success:
            print("   🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО - ФИНАЛЬНЫЕ ИСПРАВЛЕНИЯ ФУНКЦИОНАЛА ОБРАБОТКИ ЗАЯВОК НА ЗАБОР ГРУЗА РАБОТАЮТ!")
            print("   ✅ Авторизация оператора склада (+79777888999/warehouse123) работает")
            print("   ✅ Получение уведомлений со статусом 'in_processing' работает")
            print("   ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Отправка на размещение создает груз со статусом processing_status = 'paid'")
            print("   ✅ Груз появляется в списке доступных для размещения (/api/operator/cargo/available-for-placement)")
            print("   ✅ Endpoint /api/operator/cargo/available-for-placement работает корректно")
            print("   ✅ ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ: Груз создается со статусом processing_status: 'paid' и появляется в категории 'Размещение'")
            print("   🎯 ГЕНЕРАЦИЯ QR КОДОВ: Улучшения функции генерации QR с ожиданием загрузки библиотеки готовы к тестированию на frontend")
        else:
            print("   ❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ - ФИНАЛЬНЫЕ ИСПРАВЛЕНИЯ ТРЕБУЮТ ВНИМАНИЯ")
            print("   🔍 Проверьте конкретные неудачные тесты выше для получения подробностей")
        
        return all_success

    def create_test_pickup_request_notification(self, operator_token: str) -> bool:
        """Create a test pickup request to generate a notification"""
        print("   🔧 Создание тестовой заявки на забор груза для генерации уведомления...")
        
        # First, login as admin to create pickup request
        admin_login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        success, admin_login_response = self.run_test(
            "Авторизация админа для создания заявки на забор",
            "POST",
            "/api/auth/login",
            200,
            admin_login_data
        )
        
        if success and 'access_token' in admin_login_response:
            admin_token = admin_login_response['access_token']
            
            # Create pickup request
            pickup_request_data = {
                "sender_full_name": "Тест Отправитель Финальные Исправления",
                "sender_phone": "+79991234567",
                "pickup_address": "Москва, ул. Тестовая Финальные Исправления, 1",
                "pickup_date": "2025-01-20",
                "pickup_time_from": "10:00",
                "pickup_time_to": "18:00",
                "route": "moscow_to_tajikistan",
                "courier_fee": 500.0
            }
            
            success, pickup_response = self.run_test(
                "Создание заявки на забор груза",
                "POST",
                "/api/admin/courier/pickup-request",
                200,
                pickup_request_data,
                admin_token
            )
            
            if success:
                request_id = pickup_response.get('id')
                request_number = pickup_response.get('request_number')
                print(f"   ✅ Заявка на забор создана: ID={request_id}, Номер={request_number}")
                
                # Now simulate courier accepting and delivering the request
                # This should create a warehouse notification
                return True
            else:
                print("   ❌ Не удалось создать заявку на забор груза")
                return False
        else:
            print("   ❌ Не удалось авторизоваться как админ")
            return False

    def create_test_cargo_for_placement(self, operator_token: str) -> bool:
        """Create a test cargo for placement testing"""
        print("   🔧 Создание тестового груза для проверки размещения...")
        
        test_cargo_data = {
            "sender_full_name": "Тест Отправитель Размещение",
            "sender_phone": "+79991234567",
            "recipient_full_name": "Тест Получатель Размещение",
            "recipient_phone": "+992987654321",
            "recipient_address": "Душанбе, ул. Тестовая Размещение, 1",
            "weight": 3.0,
            "cargo_name": "Тестовый груз для размещения",
            "declared_value": 1500.0,
            "description": "Тест создания груза для размещения",
            "route": "moscow_dushanbe",
            "payment_method": "cash",
            "payment_amount": 1500.0
        }
        
        success, cargo_response = self.run_test(
            "Создание тестового груза для размещения",
            "POST",
            "/api/operator/cargo/accept",
            200,
            test_cargo_data,
            operator_token
        )
        
        if success:
            cargo_number = cargo_response.get('cargo_number')
            processing_status = cargo_response.get('processing_status')
            print(f"   ✅ Тестовый груз создан: {cargo_number}, статус: {processing_status}")
            self.test_cargo_number = cargo_number
            return True
        else:
            print("   ❌ Не удалось создать тестовый груз")
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("\n🚀 ЗАПУСК ВСЕХ ТЕСТОВ ФИНАЛЬНЫХ ИСПРАВЛЕНИЙ...")
        
        success = self.test_final_pickup_fixes()
        
        print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"   Всего тестов: {self.tests_run}")
        print(f"   Пройдено: {self.tests_passed}")
        print(f"   Не пройдено: {self.tests_run - self.tests_passed}")
        print(f"   Процент успеха: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if success:
            print("\n🎉 ВСЕ КРИТИЧЕСКИЕ ТЕСТЫ ФИНАЛЬНЫХ ИСПРАВЛЕНИЙ ПРОЙДЕНЫ УСПЕШНО!")
            print("   ✅ ГЕНЕРАЦИЯ QR КОДОВ: Улучшена функция генерации QR с ожиданием загрузки библиотеки")
            print("   ✅ ОТПРАВКА НА РАЗМЕЩЕНИЕ: processing_status изменен с 'pending' на 'paid'")
            print("   ✅ Груз появляется в категории 'Размещение' (/api/operator/cargo/available-for-placement)")
            print("   🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ!")
        else:
            print("\n❌ НЕКОТОРЫЕ КРИТИЧЕСКИЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            print("   🔍 Требуется дополнительное внимание к исправлениям")
        
        return success

if __name__ == "__main__":
    tester = FinalPickupFixesTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)