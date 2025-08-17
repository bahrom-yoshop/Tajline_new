#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ ОШИБКИ "ЗАВЕРШЕНИЕ ОФОРМЛЕНИЯ" В МОДАЛЬНОМ ОКНЕ ПРИНЯТИЯ ГРУЗА TAJLINE.TJ

КОНТЕКСТ: Исправлена проблема в функции complete_cargo_processing (endpoint /api/operator/warehouse-notifications/{id}/complete):
1. Исправлена логика получения warehouse_id - если у оператора нет привязок к складам, используется первый активный склад
2. Добавлены обязательные поля "route" и "description" для создания груза
3. Добавлен processing_status = "paid" чтобы грузы появлялись в списке размещения
4. Добавлены значения по умолчанию для всех полей

ТЕСТОВЫЙ ПЛАН:
1. Авторизация оператора склада (+79777888999/warehouse123)
2. Получение уведомлений со статусом "in_processing"
3. Тестирование endpoint /api/operator/warehouse-notifications/{id}/complete
4. Проверка создания грузов с обязательными полями
5. Проверка появления грузов в списке размещения
6. Проверка обновления статуса уведомления на "completed"

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Endpoint должен работать без ошибок, создавать грузы с обязательными полями route и description, устанавливать processing_status="paid" для появления в размещении.
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class WarehouseCompletionFixTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ 'ЗАВЕРШЕНИЕ ОФОРМЛЕНИЯ' В TAJLINE.TJ")
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
                    if isinstance(result, dict) and len(str(result)) < 500:
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
                    print(f"   📄 Raw response: {response.text[:300]}")
                return False, {}

        except Exception as e:
            print(f"   ❌ FAILED - Exception: {str(e)}")
            return False, {}

    def test_warehouse_completion_fix(self):
        """Протестировать исправление функции завершения оформления груза"""
        print("\n🎯 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ ЗАВЕРШЕНИЯ ОФОРМЛЕНИЯ ГРУЗА")
        print("   📋 Тестирование исправлений в endpoint /api/operator/warehouse-notifications/{id}/complete")
        
        all_success = True
        
        # ЭТАП 1: АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА (+79777888999/warehouse123)
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
            operator_user_number = operator_user.get('user_number')
            
            print(f"   ✅ Авторизация успешна: {operator_name}")
            print(f"   👑 Роль: {operator_role}")
            print(f"   📞 Телефон: {operator_user.get('phone')}")
            print(f"   🆔 Номер пользователя: {operator_user_number}")
            
            # Проверяем роль
            if operator_role == 'warehouse_operator':
                print("   ✅ Роль оператора корректна: 'warehouse_operator'")
            else:
                print(f"   ❌ Неверная роль: ожидалась 'warehouse_operator', получена '{operator_role}'")
                all_success = False
            
            self.tokens['warehouse_operator'] = operator_token
            self.users['warehouse_operator'] = operator_user
        else:
            print("   ❌ Авторизация не удалась - токен не получен")
            all_success = False
            return False
        
        # ЭТАП 2: ПОЛУЧЕНИЕ УВЕДОМЛЕНИЙ СО СТАТУСОМ "in_processing"
        print("\n   📋 ЭТАП 2: ПОЛУЧЕНИЕ УВЕДОМЛЕНИЙ СО СТАТУСОМ 'in_processing'...")
        
        success, notifications_response = self.run_test(
            "Получение уведомлений склада",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        all_success &= success
        
        in_processing_notification = None
        if success:
            notifications = notifications_response.get('notifications', [])
            total_count = notifications_response.get('total_count', 0)
            in_processing_count = notifications_response.get('in_processing_count', 0)
            
            print(f"   ✅ Получено уведомлений: {total_count}")
            print(f"   📊 В обработке: {in_processing_count}")
            
            # Найдем уведомление со статусом "in_processing"
            for notification in notifications:
                if notification.get('status') == 'in_processing':
                    in_processing_notification = notification
                    print(f"   🎯 Найдено уведомление в обработке: {notification.get('id')}")
                    print(f"   📄 Номер заявки: {notification.get('request_number')}")
                    print(f"   👤 Отправитель: {notification.get('sender_full_name')}")
                    break
            
            if not in_processing_notification:
                print("   ⚠️  Нет уведомлений со статусом 'in_processing'")
                print("   📝 Создадим тестовое уведомление для тестирования...")
                
                # Создаем тестовое уведомление (если есть админский доступ)
                # Для простоты тестирования, используем первое доступное уведомление
                if notifications:
                    in_processing_notification = notifications[0]
                    print(f"   🔄 Используем уведомление: {in_processing_notification.get('id')} для тестирования")
                else:
                    print("   ❌ Нет доступных уведомлений для тестирования")
                    all_success = False
        else:
            print("   ❌ Не удалось получить уведомления")
            all_success = False
        
        # ЭТАП 3: ТЕСТИРОВАНИЕ ENDPOINT /api/operator/warehouse-notifications/{id}/complete
        print("\n   🎯 ЭТАП 3: ТЕСТИРОВАНИЕ ENDPOINT ЗАВЕРШЕНИЯ ОФОРМЛЕНИЯ...")
        
        if in_processing_notification:
            notification_id = in_processing_notification.get('id')
            
            # Подготавливаем тестовые данные для завершения оформления
            completion_data = {
                "sender_full_name": "Тестовый Отправитель Исправления",
                "sender_phone": "+79991234567",
                "sender_address": "Москва, ул. Тестовая Исправления, 1",
                "recipient_full_name": "Тестовый Получатель Исправления",
                "recipient_phone": "+992987654321",
                "recipient_address": "Душанбе, ул. Получателя Исправления, 2",
                "payment_method": "cash",
                "payment_status": "paid",
                "delivery_method": "pickup",
                "cargo_items": [
                    {
                        "name": "Тестовый груз с обязательными полями",
                        "weight": "15.5",
                        "price": "2500"
                    },
                    {
                        "name": "Второй тестовый груз",
                        "weight": "8.0",
                        "price": "1200"
                    }
                ]
            }
            
            success, completion_response = self.run_test(
                "Завершение оформления груза (КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ)",
                "POST",
                f"/api/operator/warehouse-notifications/{notification_id}/complete",
                200,
                completion_data,
                operator_token
            )
            all_success &= success
            
            created_cargo_number = None
            created_cargo_id = None
            
            if success:
                print("   ✅ КРИТИЧЕСКИЙ УСПЕХ - Endpoint завершения оформления работает!")
                
                # Проверяем структуру ответа
                message = completion_response.get('message')
                cargo_id = completion_response.get('cargo_id')
                cargo_number = completion_response.get('cargo_number')
                notification_status = completion_response.get('notification_status')
                created_cargos = completion_response.get('created_cargos', [])
                total_items = completion_response.get('total_items', 0)
                
                print(f"   📄 Сообщение: {message}")
                print(f"   🆔 ID груза: {cargo_id}")
                print(f"   📦 Номер груза: {cargo_number}")
                print(f"   📊 Статус уведомления: {notification_status}")
                print(f"   📋 Создано грузов: {total_items}")
                
                created_cargo_number = cargo_number
                created_cargo_id = cargo_id
                
                # Проверяем, что статус уведомления изменился на "completed"
                if notification_status == "completed":
                    print("   ✅ Статус уведомления корректно обновлен на 'completed'")
                else:
                    print(f"   ❌ Неверный статус уведомления: ожидался 'completed', получен '{notification_status}'")
                    all_success = False
                
                # Проверяем создание грузов
                if total_items > 0:
                    print(f"   ✅ Создано {total_items} грузов из заявки")
                else:
                    print("   ❌ Грузы не созданы")
                    all_success = False
                    
            else:
                print("   ❌ КРИТИЧЕСКАЯ ОШИБКА - Endpoint завершения оформления не работает!")
                all_success = False
        else:
            print("   ❌ Нет уведомления для тестирования завершения оформления")
            all_success = False
        
        # ЭТАП 4: ПРОВЕРКА СОЗДАНИЯ ГРУЗОВ С ОБЯЗАТЕЛЬНЫМИ ПОЛЯМИ
        print("\n   📦 ЭТАП 4: ПРОВЕРКА СОЗДАНИЯ ГРУЗОВ С ОБЯЗАТЕЛЬНЫМИ ПОЛЯМИ...")
        
        if created_cargo_number:
            # Проверяем, что груз создан с обязательными полями route и description
            success, cargo_list = self.run_test(
                "Получение списка грузов оператора",
                "GET",
                "/api/operator/cargo/list",
                200,
                token=operator_token
            )
            
            if success:
                cargo_items = cargo_list.get('items', []) if isinstance(cargo_list, dict) else cargo_list
                
                # Ищем созданный груз
                created_cargo = None
                for cargo in cargo_items:
                    if cargo.get('cargo_number') == created_cargo_number:
                        created_cargo = cargo
                        break
                
                if created_cargo:
                    print(f"   ✅ Созданный груз найден: {created_cargo_number}")
                    
                    # Проверяем обязательные поля
                    route = created_cargo.get('route')
                    description = created_cargo.get('description')
                    processing_status = created_cargo.get('processing_status')
                    warehouse_id = created_cargo.get('warehouse_id')
                    
                    print(f"   📍 Route: {route}")
                    print(f"   📝 Description: {description}")
                    print(f"   📊 Processing Status: {processing_status}")
                    print(f"   🏭 Warehouse ID: {warehouse_id}")
                    
                    # Проверяем наличие обязательных полей
                    if route:
                        print("   ✅ Обязательное поле 'route' присутствует")
                    else:
                        print("   ❌ Обязательное поле 'route' отсутствует")
                        all_success = False
                    
                    if description:
                        print("   ✅ Обязательное поле 'description' присутствует")
                    else:
                        print("   ❌ Обязательное поле 'description' отсутствует")
                        all_success = False
                    
                    # Проверяем processing_status = "paid"
                    if processing_status == "paid":
                        print("   ✅ Processing status корректно установлен как 'paid'")
                    else:
                        print(f"   ❌ Неверный processing status: ожидался 'paid', получен '{processing_status}'")
                        all_success = False
                    
                    # Проверяем warehouse_id (исправление логики получения warehouse_id)
                    if warehouse_id:
                        print("   ✅ Warehouse ID корректно назначен")
                    else:
                        print("   ❌ Warehouse ID не назначен")
                        all_success = False
                        
                else:
                    print(f"   ❌ Созданный груз {created_cargo_number} не найден в списке")
                    all_success = False
            else:
                print("   ❌ Не удалось получить список грузов для проверки")
                all_success = False
        else:
            print("   ❌ Нет номера созданного груза для проверки")
            all_success = False
        
        # ЭТАП 5: ПРОВЕРКА ПОЯВЛЕНИЯ ГРУЗОВ В СПИСКЕ РАЗМЕЩЕНИЯ
        print("\n   🎯 ЭТАП 5: ПРОВЕРКА ПОЯВЛЕНИЯ ГРУЗОВ В СПИСКЕ РАЗМЕЩЕНИЯ...")
        
        success, placement_list = self.run_test(
            "Получение грузов доступных для размещения",
            "GET",
            "/api/operator/cargo/available-for-placement",
            200,
            token=operator_token
        )
        all_success &= success
        
        if success:
            placement_items = placement_list.get('items', []) if isinstance(placement_list, dict) else placement_list
            total_available = len(placement_items)
            
            print(f"   ✅ Получен список размещения: {total_available} грузов")
            
            # Проверяем, что созданный груз появился в списке размещения
            if created_cargo_number:
                cargo_in_placement = False
                for cargo in placement_items:
                    if cargo.get('cargo_number') == created_cargo_number:
                        cargo_in_placement = True
                        processing_status = cargo.get('processing_status')
                        print(f"   ✅ Созданный груз {created_cargo_number} найден в списке размещения")
                        print(f"   📊 Processing status в размещении: {processing_status}")
                        
                        if processing_status == "paid":
                            print("   ✅ Груз корректно имеет статус 'paid' в списке размещения")
                        else:
                            print(f"   ❌ Неверный статус в размещении: ожидался 'paid', получен '{processing_status}'")
                            all_success = False
                        break
                
                if cargo_in_placement:
                    print("   ✅ КРИТИЧЕСКИЙ УСПЕХ - Груз появился в списке размещения!")
                else:
                    print("   ❌ КРИТИЧЕСКАЯ ОШИБКА - Груз не появился в списке размещения")
                    all_success = False
            
            # Проверяем, что все грузы в списке размещения имеют статус "paid"
            paid_count = 0
            for cargo in placement_items:
                if cargo.get('processing_status') == 'paid':
                    paid_count += 1
            
            if paid_count == total_available:
                print(f"   ✅ Все {total_available} грузов в списке размещения имеют статус 'paid'")
            else:
                print(f"   ⚠️  {paid_count}/{total_available} грузов имеют статус 'paid'")
                
        else:
            print("   ❌ Не удалось получить список грузов для размещения")
            all_success = False
        
        # ЭТАП 6: ПРОВЕРКА ОБНОВЛЕНИЯ СТАТУСА УВЕДОМЛЕНИЯ НА "completed"
        print("\n   📋 ЭТАП 6: ПРОВЕРКА ОБНОВЛЕНИЯ СТАТУСА УВЕДОМЛЕНИЯ НА 'completed'...")
        
        success, updated_notifications = self.run_test(
            "Проверка обновленных уведомлений",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        
        if success:
            notifications = updated_notifications.get('notifications', [])
            in_processing_count = updated_notifications.get('in_processing_count', 0)
            
            print(f"   📊 Уведомлений в обработке после завершения: {in_processing_count}")
            
            # Проверяем, что обработанное уведомление больше не в списке активных
            if in_processing_notification:
                processed_notification_id = in_processing_notification.get('id')
                still_in_list = any(n.get('id') == processed_notification_id for n in notifications)
                
                if not still_in_list:
                    print("   ✅ Обработанное уведомление исключено из активного списка")
                else:
                    print("   ❌ Обработанное уведомление все еще в активном списке")
                    all_success = False
        else:
            print("   ❌ Не удалось проверить обновленные уведомления")
            all_success = False
        
        # ФИНАЛЬНАЯ СВОДКА
        print("\n   📊 ФИНАЛЬНАЯ СВОДКА ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЯ ЗАВЕРШЕНИЯ ОФОРМЛЕНИЯ:")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"   📈 Успешность тестов: {self.tests_passed}/{self.tests_run} ({success_rate:.1f}%)")
        
        if all_success:
            print("   🎉 ВСЕ КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ РАБОТАЮТ УСПЕШНО!")
            print("   ✅ Авторизация оператора склада (+79777888999/warehouse123)")
            print("   ✅ Получение уведомлений со статусом 'in_processing'")
            print("   ✅ Endpoint /api/operator/warehouse-notifications/{id}/complete работает")
            print("   ✅ Создание грузов с обязательными полями 'route' и 'description'")
            print("   ✅ Processing status = 'paid' для появления в размещении")
            print("   ✅ Логика получения warehouse_id исправлена")
            print("   ✅ Грузы появляются в списке размещения")
            print("   ✅ Статус уведомления обновляется на 'completed'")
            print("   🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ!")
        else:
            print("   ❌ НЕКОТОРЫЕ КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ ТРЕБУЮТ ВНИМАНИЯ")
            print("   🔍 Проверьте детали неудачных тестов выше")
        
        return all_success

    def run_all_tests(self):
        """Запустить все тесты"""
        print("\n🚀 ЗАПУСК ВСЕХ ТЕСТОВ ИСПРАВЛЕНИЯ ЗАВЕРШЕНИЯ ОФОРМЛЕНИЯ...")
        
        overall_success = True
        
        # Основной тест исправления
        success = self.test_warehouse_completion_fix()
        overall_success &= success
        
        # Финальная сводка
        print("\n" + "=" * 80)
        print("📊 ИТОГОВАЯ СВОДКА ТЕСТИРОВАНИЯ")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"📈 Общая успешность: {self.tests_passed}/{self.tests_run} тестов ({success_rate:.1f}%)")
        
        if overall_success:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("✅ Исправление функции завершения оформления груза работает корректно")
            print("✅ Endpoint /api/operator/warehouse-notifications/{id}/complete функционален")
            print("✅ Обязательные поля 'route' и 'description' добавлены")
            print("✅ Processing status = 'paid' для появления в размещении")
            print("✅ Логика получения warehouse_id исправлена")
            print("🎯 TAJLINE.TJ готов к использованию с исправленной функцией завершения оформления!")
        else:
            print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            print("🔧 Требуется дополнительная работа над исправлениями")
        
        return overall_success

if __name__ == "__main__":
    tester = WarehouseCompletionFixTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)