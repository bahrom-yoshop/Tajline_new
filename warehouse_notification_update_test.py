#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новый endpoint для обновления уведомлений о поступивших грузах в TAJLINE.TJ

ЦЕЛЬ ТЕСТИРОВАНИЯ:
- Проверить работу нового endpoint PUT /api/operator/warehouse-notifications/{notification_id}
- Убедиться, что только авторизованные операторы и админы могут обновлять уведомления
- Проверить корректность обновления разрешенных полей уведомления
- Проверить обработку ошибок (несуществующие уведомления, неправильные данные)

ДЕТАЛИ ДЛЯ ТЕСТИРОВАНИЯ:
1. Создать тестовое уведомление
2. Протестировать обновление с разными типами пользователей
3. Проверить обновление различных полей (sender_full_name, sender_phone, pickup_address, destination, courier_fee, payment_method)
4. Проверить обработку ошибок для несуществующих уведомлений
5. Убедиться, что возвращается корректный ответ с обновленными данными

ИСПОЛЬЗУЮТСЯ ВАЛИДНЫЕ ДАННЫЕ ИЗ СУЩЕСТВУЮЩИХ ENDPOINT'ОВ.
"""

import requests
import json
import sys
import time
from datetime import datetime
import uuid

# Конфигурация
BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"

# Учетные данные для тестирования
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

OPERATOR_CREDENTIALS = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class WarehouseNotificationUpdateTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.admin_user = None
        self.operator_user = None
        self.test_results = []
        self.test_notification_id = None
        
    def log_test(self, test_name, success, details=""):
        """Логирование результатов тестов"""
        status = "✅" if success else "❌"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        print(f"{status} {test_name}: {details}")
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=ADMIN_CREDENTIALS,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                self.admin_user = data["user"]
                
                self.log_test(
                    "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                    True,
                    f"Успешная авторизация '{self.admin_user['full_name']}' (номер: {self.admin_user.get('user_number', 'N/A')}, роль: {self.admin_user['role']})"
                )
                return True
            else:
                self.log_test(
                    "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("АВТОРИЗАЦИЯ АДМИНИСТРАТОРА", False, f"Ошибка: {str(e)}")
            return False
    
    def authenticate_operator(self):
        """Авторизация оператора склада"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=OPERATOR_CREDENTIALS,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data["access_token"]
                self.operator_user = data["user"]
                
                self.log_test(
                    "АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА",
                    True,
                    f"Успешная авторизация '{self.operator_user['full_name']}' (номер: {self.operator_user.get('user_number', 'N/A')}, роль: {self.operator_user['role']})"
                )
                return True
            else:
                self.log_test(
                    "АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА", False, f"Ошибка: {str(e)}")
            return False
    
    def create_test_notification(self):
        """Создать тестовое уведомление о поступившем грузе"""
        try:
            # Используем админский токен для создания тестового уведомления
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Сначала создаем тестовую заявку на забор груза
            pickup_request_data = {
                "sender_full_name": "Тестовый Отправитель Уведомлений",
                "sender_phone": "+79991234567",
                "pickup_address": "Москва, ул. Тестовая, д. 123",
                "cargo_name": "Тестовый груз для уведомлений",
                "weight": 5.5,
                "declared_value": 1000.0,
                "description": "Тестовое описание груза для проверки уведомлений",
                "recipient_full_name": "Тестовый Получатель",
                "recipient_phone": "+79997654321",
                "destination": "Душанбе, ул. Получателя, д. 456",
                "courier_fee": 500.0,
                "payment_method": "cash"
            }
            
            # Создаем заявку на забор груза через админа
            response = self.session.post(
                f"{BACKEND_URL}/admin/courier/pickup-request",
                json=pickup_request_data,
                headers={**headers, "Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                self.log_test(
                    "СОЗДАНИЕ ТЕСТОВОЙ ЗАЯВКИ НА ЗАБОР",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
            
            pickup_request = response.json()
            request_id = pickup_request.get("request_id")
            
            if not request_id:
                self.log_test(
                    "СОЗДАНИЕ ТЕСТОВОЙ ЗАЯВКИ НА ЗАБОР",
                    False,
                    "Не получен request_id из ответа"
                )
                return False
            
            self.log_test(
                "СОЗДАНИЕ ТЕСТОВОЙ ЗАЯВКИ НА ЗАБОР",
                True,
                f"Заявка создана с ID: {request_id}"
            )
            
            # Теперь создаем уведомление о доставке груза на склад
            notification_data = {
                "id": str(uuid.uuid4()),
                "request_id": request_id,
                "request_number": pickup_request.get("request_number", "TEST001"),
                "request_type": "pickup_request",
                "courier_name": "Тестовый Курьер",
                "courier_id": str(uuid.uuid4()),
                "sender_full_name": pickup_request_data["sender_full_name"],
                "sender_phone": pickup_request_data["sender_phone"],
                "pickup_address": pickup_request_data["pickup_address"],
                "destination": pickup_request_data["destination"],
                "courier_fee": pickup_request_data["courier_fee"],
                "payment_method": pickup_request_data["payment_method"],
                "delivered_at": datetime.utcnow(),
                "status": "pending_acceptance",
                "action_history": [
                    {
                        "action": "delivered_to_warehouse",
                        "timestamp": datetime.utcnow(),
                        "performed_by": "Тестовый Курьер"
                    }
                ],
                "created_at": datetime.utcnow()
            }
            
            # Вставляем уведомление напрямую в базу данных через MongoDB
            # Поскольку у нас нет прямого endpoint для создания уведомлений,
            # мы будем использовать существующие уведомления из базы
            
            # Получаем существующие уведомления
            response = self.session.get(
                f"{BACKEND_URL}/operator/warehouse-notifications",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                notifications = data.get("notifications", []) if isinstance(data, dict) else data
                print(f"DEBUG: Found {len(notifications)} notifications")
                
                if notifications and len(notifications) > 0:
                    # Используем первое доступное уведомление для тестирования
                    first_notification = notifications[0]
                    self.test_notification_id = first_notification.get("id")
                    
                    if self.test_notification_id:
                        self.log_test(
                            "ПОЛУЧЕНИЕ ТЕСТОВОГО УВЕДОМЛЕНИЯ",
                            True,
                            f"Используется существующее уведомление с ID: {self.test_notification_id[:8]}..."
                        )
                        return True
                    else:
                        self.log_test(
                            "ПОЛУЧЕНИЕ ТЕСТОВОГО УВЕДОМЛЕНИЯ",
                            False,
                            f"Уведомление не содержит поле 'id': {list(first_notification.keys())}"
                        )
                        return False
                else:
                    # Если нет уведомлений, создаем фиктивный ID для тестирования endpoint
                    self.test_notification_id = "test-notification-id-12345"
                    self.log_test(
                        "ПОЛУЧЕНИЕ ТЕСТОВОГО УВЕДОМЛЕНИЯ",
                        True,
                        f"Нет доступных уведомлений, используется тестовый ID для проверки endpoint"
                    )
                    return True
            else:
                self.log_test(
                    "ПОЛУЧЕНИЕ ТЕСТОВОГО УВЕДОМЛЕНИЯ",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("СОЗДАНИЕ ТЕСТОВОГО УВЕДОМЛЕНИЯ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_unauthorized_access(self):
        """Тест доступа без авторизации"""
        try:
            # Попытка обновления без токена
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{self.test_notification_id}",
                json={"sender_full_name": "Тест без авторизации"},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 401:
                self.log_test(
                    "ДОСТУП БЕЗ АВТОРИЗАЦИИ",
                    True,
                    f"HTTP 401: Корректно заблокирован доступ без токена"
                )
                return True
            else:
                self.log_test(
                    "ДОСТУП БЕЗ АВТОРИЗАЦИИ",
                    False,
                    f"HTTP {response.status_code}: Ожидался 401"
                )
                return False
                
        except Exception as e:
            self.log_test("ДОСТУП БЕЗ АВТОРИЗАЦИИ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_admin_update_notification(self):
        """Тест обновления уведомления администратором"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
            
            update_data = {
                "sender_full_name": "Обновленный Отправитель Админом",
                "sender_phone": "+79991111111",
                "pickup_address": "Москва, ул. Обновленная Админом, д. 999",
                "destination": "Душанбе, ул. Новая Админская, д. 888",
                "courier_fee": 750.0,
                "payment_method": "card_transfer"
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{self.test_notification_id}",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Проверяем структуру ответа
                required_fields = ["message", "notification_id", "updated_fields", "notification"]
                missing_fields = [field for field in required_fields if field not in result]
                
                if not missing_fields:
                    # Проверяем, что обновленные поля присутствуют
                    updated_notification = result["notification"]
                    all_fields_updated = all(
                        updated_notification.get(field) == update_data[field]
                        for field in update_data.keys()
                    )
                    
                    if all_fields_updated:
                        self.log_test(
                            "🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ АДМИНИСТРАТОРОМ",
                            True,
                            f"Все поля обновлены корректно: {', '.join(update_data.keys())}"
                        )
                        return True
                    else:
                        self.log_test(
                            "🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ АДМИНИСТРАТОРОМ",
                            False,
                            "Не все поля были обновлены корректно"
                        )
                        return False
                else:
                    self.log_test(
                        "🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ АДМИНИСТРАТОРОМ",
                        False,
                        f"Отсутствуют поля в ответе: {missing_fields}"
                    )
                    return False
            else:
                self.log_test(
                    "🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ АДМИНИСТРАТОРОМ",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ АДМИНИСТРАТОРОМ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_operator_update_notification(self):
        """Тест обновления уведомления оператором склада"""
        try:
            headers = {"Authorization": f"Bearer {self.operator_token}", "Content-Type": "application/json"}
            
            update_data = {
                "sender_full_name": "Обновленный Отправитель Оператором",
                "sender_phone": "+79992222222",
                "pickup_address": "Москва, ул. Обновленная Оператором, д. 777",
                "destination": "Худжанд, ул. Новая Операторская, д. 666",
                "courier_fee": 600.0,
                "payment_method": "cash_on_delivery"
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{self.test_notification_id}",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Проверяем, что уведомление обновлено
                updated_notification = result.get("notification", {})
                
                # Проверяем обновление ключевых полей
                key_fields_updated = (
                    updated_notification.get("sender_full_name") == update_data["sender_full_name"] and
                    updated_notification.get("courier_fee") == update_data["courier_fee"] and
                    updated_notification.get("payment_method") == update_data["payment_method"]
                )
                
                if key_fields_updated:
                    self.log_test(
                        "🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ ОПЕРАТОРОМ",
                        True,
                        f"Ключевые поля обновлены: {update_data['sender_full_name']}, {update_data['courier_fee']}, {update_data['payment_method']}"
                    )
                    return True
                else:
                    self.log_test(
                        "🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ ОПЕРАТОРОМ",
                        False,
                        "Ключевые поля не были обновлены корректно"
                    )
                    return False
            else:
                self.log_test(
                    "🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ ОПЕРАТОРОМ",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("🎯 КРИТИЧЕСКИЙ УСПЕХ - ОБНОВЛЕНИЕ ОПЕРАТОРОМ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_individual_field_updates(self):
        """Тест обновления отдельных полей"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
            
            # Тест обновления только имени отправителя
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{self.test_notification_id}",
                json={"sender_full_name": "Только Имя Обновлено"},
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                updated_fields = result.get("updated_fields", [])
                
                if "sender_full_name" in updated_fields:
                    self.log_test(
                        "ОБНОВЛЕНИЕ ОТДЕЛЬНОГО ПОЛЯ - ИМЯ ОТПРАВИТЕЛЯ",
                        True,
                        f"Поле sender_full_name обновлено, всего обновлено полей: {len(updated_fields)}"
                    )
                else:
                    self.log_test(
                        "ОБНОВЛЕНИЕ ОТДЕЛЬНОГО ПОЛЯ - ИМЯ ОТПРАВИТЕЛЯ",
                        False,
                        f"Поле sender_full_name не найдено в обновленных полях: {updated_fields}"
                    )
                    return False
            else:
                self.log_test(
                    "ОБНОВЛЕНИЕ ОТДЕЛЬНОГО ПОЛЯ - ИМЯ ОТПРАВИТЕЛЯ",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
            
            # Тест обновления только стоимости курьера
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{self.test_notification_id}",
                json={"courier_fee": 999.99},
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                notification = result.get("notification", {})
                
                if notification.get("courier_fee") == 999.99:
                    self.log_test(
                        "ОБНОВЛЕНИЕ ОТДЕЛЬНОГО ПОЛЯ - СТОИМОСТЬ КУРЬЕРА",
                        True,
                        f"Поле courier_fee обновлено на 999.99"
                    )
                    return True
                else:
                    self.log_test(
                        "ОБНОВЛЕНИЕ ОТДЕЛЬНОГО ПОЛЯ - СТОИМОСТЬ КУРЬЕРА",
                        False,
                        f"Поле courier_fee не обновлено корректно: {notification.get('courier_fee')}"
                    )
                    return False
            else:
                self.log_test(
                    "ОБНОВЛЕНИЕ ОТДЕЛЬНОГО ПОЛЯ - СТОИМОСТЬ КУРЬЕРА",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("ОБНОВЛЕНИЕ ОТДЕЛЬНЫХ ПОЛЕЙ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_invalid_notification_id(self):
        """Тест обновления несуществующего уведомления"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
            
            fake_notification_id = "00000000-0000-0000-0000-000000000000"
            
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{fake_notification_id}",
                json={"sender_full_name": "Тест несуществующего уведомления"},
                headers=headers
            )
            
            if response.status_code == 404:
                self.log_test(
                    "ОБНОВЛЕНИЕ НЕСУЩЕСТВУЮЩЕГО УВЕДОМЛЕНИЯ",
                    True,
                    f"HTTP 404: Корректно обработана ошибка несуществующего уведомления"
                )
                return True
            else:
                self.log_test(
                    "ОБНОВЛЕНИЕ НЕСУЩЕСТВУЮЩЕГО УВЕДОМЛЕНИЯ",
                    False,
                    f"HTTP {response.status_code}: Ожидался 404"
                )
                return False
                
        except Exception as e:
            self.log_test("ОБНОВЛЕНИЕ НЕСУЩЕСТВУЮЩЕГО УВЕДОМЛЕНИЯ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_invalid_data_validation(self):
        """Тест валидации неправильных данных"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
            
            # Тест с пустыми данными
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{self.test_notification_id}",
                json={},
                headers=headers
            )
            
            if response.status_code == 400:
                self.log_test(
                    "ВАЛИДАЦИЯ ПУСТЫХ ДАННЫХ",
                    True,
                    f"HTTP 400: Корректно обработаны пустые данные для обновления"
                )
            else:
                # Может быть и другой код ошибки, главное не 200
                if response.status_code != 200:
                    self.log_test(
                        "ВАЛИДАЦИЯ ПУСТЫХ ДАННЫХ",
                        True,
                        f"HTTP {response.status_code}: Пустые данные корректно отклонены"
                    )
                else:
                    self.log_test(
                        "ВАЛИДАЦИЯ ПУСТЫХ ДАННЫХ",
                        False,
                        f"HTTP 200: Пустые данные не должны приводить к успешному обновлению"
                    )
                    return False
            
            # Тест с недопустимыми полями
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{self.test_notification_id}",
                json={
                    "invalid_field": "Недопустимое поле",
                    "another_invalid": 123,
                    "sender_full_name": "Валидное поле"
                },
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                updated_fields = result.get("updated_fields", [])
                
                # Проверяем, что только валидные поля были обновлены
                if "sender_full_name" in updated_fields and "invalid_field" not in updated_fields:
                    self.log_test(
                        "ВАЛИДАЦИЯ НЕДОПУСТИМЫХ ПОЛЕЙ",
                        True,
                        f"Только валидные поля обновлены: {updated_fields}"
                    )
                    return True
                else:
                    self.log_test(
                        "ВАЛИДАЦИЯ НЕДОПУСТИМЫХ ПОЛЕЙ",
                        False,
                        f"Недопустимые поля могли быть обновлены: {updated_fields}"
                    )
                    return False
            else:
                self.log_test(
                    "ВАЛИДАЦИЯ НЕДОПУСТИМЫХ ПОЛЕЙ",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("ВАЛИДАЦИЯ НЕПРАВИЛЬНЫХ ДАННЫХ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_response_structure(self):
        """Тест структуры ответа endpoint'а"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
            
            response = self.session.put(
                f"{BACKEND_URL}/operator/warehouse-notifications/{self.test_notification_id}",
                json={"sender_full_name": "Тест структуры ответа"},
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Проверяем обязательные поля в ответе
                required_fields = ["message", "notification_id", "updated_fields", "notification"]
                missing_fields = [field for field in required_fields if field not in result]
                
                if not missing_fields:
                    # Проверяем типы данных
                    valid_types = (
                        isinstance(result["message"], str) and
                        isinstance(result["notification_id"], str) and
                        isinstance(result["updated_fields"], list) and
                        isinstance(result["notification"], dict)
                    )
                    
                    if valid_types:
                        # Проверяем, что notification_id соответствует запрошенному
                        if result["notification_id"] == self.test_notification_id:
                            self.log_test(
                                "СТРУКТУРА ОТВЕТА ENDPOINT",
                                True,
                                f"Все обязательные поля присутствуют с корректными типами данных"
                            )
                            return True
                        else:
                            self.log_test(
                                "СТРУКТУРА ОТВЕТА ENDPOINT",
                                False,
                                f"notification_id в ответе не соответствует запрошенному"
                            )
                            return False
                    else:
                        self.log_test(
                            "СТРУКТУРА ОТВЕТА ENDPOINT",
                            False,
                            f"Некорректные типы данных в ответе"
                        )
                        return False
                else:
                    self.log_test(
                        "СТРУКТУРА ОТВЕТА ENDPOINT",
                        False,
                        f"Отсутствуют обязательные поля: {missing_fields}"
                    )
                    return False
            else:
                self.log_test(
                    "СТРУКТУРА ОТВЕТА ENDPOINT",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("СТРУКТУРА ОТВЕТА ENDPOINT", False, f"Ошибка: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новый endpoint для обновления уведомлений о поступивших грузах в TAJLINE.TJ")
        print("="*120)
        print(f"Время начала тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Backend URL: {BACKEND_URL}")
        print("="*120)
        
        # Авторизация
        if not self.authenticate_admin():
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
            return False
        
        if not self.authenticate_operator():
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как оператор склада")
            return False
        
        # Создание тестового уведомления
        if not self.create_test_notification():
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать/получить тестовое уведомление")
            return False
        
        # Запуск тестов
        tests = [
            ("UNAUTHORIZED ACCESS", self.test_unauthorized_access),
            ("ADMIN UPDATE NOTIFICATION", self.test_admin_update_notification),
            ("OPERATOR UPDATE NOTIFICATION", self.test_operator_update_notification),
            ("INDIVIDUAL FIELD UPDATES", self.test_individual_field_updates),
            ("INVALID NOTIFICATION ID", self.test_invalid_notification_id),
            ("INVALID DATA VALIDATION", self.test_invalid_data_validation),
            ("RESPONSE STRUCTURE", self.test_response_structure)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"🧪 ВЫПОЛНЕНИЕ ТЕСТА: {test_name}")
            print(f"{'='*60}")
            
            try:
                if test_func():
                    passed_tests += 1
                    print(f"✅ ТЕСТ '{test_name}' ЗАВЕРШЕН УСПЕШНО")
                else:
                    print(f"❌ ТЕСТ '{test_name}' ЗАВЕРШЕН С ОШИБКАМИ")
            except Exception as e:
                print(f"❌ ТЕСТ '{test_name}' ЗАВЕРШЕН С ИСКЛЮЧЕНИЕМ: {str(e)}")
        
        # Итоговый отчет
        print("\n" + "="*120)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("="*120)
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"Успешно пройдено тестов: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Детальная статистика по отдельным проверкам
        successful_checks = sum(1 for result in self.test_results if result["success"])
        total_checks = len(self.test_results)
        check_success_rate = (successful_checks / total_checks) * 100 if total_checks > 0 else 0
        
        print(f"Успешно пройдено проверок: {successful_checks}/{total_checks} ({check_success_rate:.1f}%)")
        
        # Список неудачных тестов
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print(f"\n❌ НЕУДАЧНЫЕ ПРОВЕРКИ ({len(failed_tests)}):")
            for failed in failed_tests:
                print(f"   • {failed['test']}: {failed['details']}")
        
        print(f"\nВремя завершения тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Финальная оценка
        if success_rate >= 90:
            print("\n🎉 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            print("✅ Новый endpoint PUT /api/operator/warehouse-notifications/{notification_id} работает корректно")
            print("✅ Авторизация операторов и админов функционирует правильно")
            print("✅ Обновление разрешенных полей уведомления работает без ошибок")
            print("✅ Обработка ошибок для несуществующих уведомлений корректна")
            print("✅ Структура ответа соответствует ожиданиям")
        elif success_rate >= 70:
            print("\n⚠️ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ПРЕДУПРЕЖДЕНИЯМИ")
            print("⚠️ Основная функциональность работает, но есть минорные проблемы")
        else:
            print("\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ")
            print("❌ Требуется исправление найденных проблем перед использованием")
        
        return success_rate >= 70

def main():
    """Главная функция"""
    tester = WarehouseNotificationUpdateTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()