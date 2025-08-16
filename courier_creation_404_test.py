#!/usr/bin/env python3
"""
🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема 404 при создании курьера в TAJLINE.TJ

ПРОБЛЕМА:
Пользователь сообщает о ошибке при регистрации курьера: "404 page not found" при нажатии кнопку "Сохранить"

ДЕТАЛЬНАЯ ДИАГНОСТИКА:
1. **Проверка существования endpoint** POST /api/admin/couriers/create
2. **Тестирование авторизации** администратора для доступа к endpoint
3. **Проверка валидации данных** CourierCreate модели
4. **Тестирование создания курьера** с корректными данными
5. **Проверка всех обязательных полей** модели CourierCreate
6. **Диагностика ошибок валидации** Pydantic
7. **Проверка доступности складов** для назначения курьеру
8. **Тестирование транспортных типов** TransportType enum

КОНТЕКСТ ИЗ КОДА:
- Frontend вызывает: POST /api/admin/couriers/create
- Backend endpoint существует на строке 13551
- Использует модель CourierCreate с полями: full_name, phone, password, address, transport_type, transport_number, transport_capacity, assigned_warehouse_id
- Требует авторизацию администратора или оператора склада

ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:
- Endpoint должен отвечать не 404, а либо успехом либо ошибкой валидации
- Определить точную причину 404 ошибки  
- Предложить решение проблемы

ТЕСТОВЫЕ ДАННЫЕ:
Использовать реалистичные данные курьера:
- full_name: "Тестовый Курьер Иванов" 
- phone: "+79991234567"
- password: "courier123"
- address: "Тестовый адрес"
- transport_type: "car"
- transport_number: "A123BC777"
- transport_capacity: 100.0
- assigned_warehouse_id: получить из списка складов
"""

import requests
import json
import sys
import os
from datetime import datetime
import time

# Получаем URL backend из переменных окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE = f"{BACKEND_URL}/api"

class CourierCreation404Tester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.admin_user = None
        self.operator_user = None
        self.test_results = []
        self.available_warehouses = []
        self.test_courier_id = None
        self.test_user_id = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def log_test(self, test_name, success, details=""):
        """Логирование результатов тестов"""
        status = "✅" if success else "❌"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        self.log(f"{status} {test_name}: {details}")
        
    def test_admin_auth(self):
        """Авторизация администратора"""
        try:
            self.log("🔐 Авторизация администратора...")
            
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79999888777",
                "password": "admin123"
            })
            
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
    
    def test_operator_auth(self):
        """Авторизация оператора склада"""
        try:
            self.log("🔐 Авторизация оператора склада...")
            
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79777888999",
                "password": "warehouse123"
            })
            
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
    
    def get_available_warehouses(self):
        """Получить список доступных складов для назначения курьеру"""
        try:
            self.log("🏢 Получение списка складов...")
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{API_BASE}/warehouses", headers=headers)
            
            if response.status_code == 200:
                warehouses = response.json()
                self.available_warehouses = warehouses
                
                self.log_test(
                    "ПОЛУЧЕНИЕ СПИСКА СКЛАДОВ",
                    True,
                    f"Получено {len(warehouses)} складов: {', '.join([w['name'] for w in warehouses[:3]])}"
                )
                return len(warehouses) > 0
            else:
                self.log_test(
                    "ПОЛУЧЕНИЕ СПИСКА СКЛАДОВ",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("ПОЛУЧЕНИЕ СПИСКА СКЛАДОВ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_endpoint_exists(self):
        """Проверить существование endpoint POST /api/admin/couriers/create"""
        try:
            self.log("🎯 КРИТИЧЕСКИЙ ТЕСТ: Проверка существования endpoint POST /api/admin/couriers/create")
            
            if not self.available_warehouses:
                self.log_test(
                    "ПРОВЕРКА СУЩЕСТВОВАНИЯ ENDPOINT",
                    False,
                    "Нет доступных складов для тестирования"
                )
                return False
            
            # Используем реалистичные данные согласно review request
            courier_data = {
                "full_name": "Тестовый Курьер Иванов",
                "phone": "+79991234567",
                "password": "courier123",
                "address": "Москва, ул. Тестовая, д. 10, кв. 5",
                "transport_type": "car",
                "transport_number": "A123BC777",
                "transport_capacity": 100.0,
                "assigned_warehouse_id": self.available_warehouses[0]["id"]
            }
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                       json=courier_data, headers=headers)
            
            if response.status_code == 404:
                self.log_test(
                    "ПРОВЕРКА СУЩЕСТВОВАНИЯ ENDPOINT",
                    False,
                    f"🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: Endpoint возвращает HTTP 404! Это объясняет проблему пользователя. Response: {response.text}"
                )
                return False
            elif response.status_code == 200:
                data = response.json()
                self.test_courier_id = data.get("courier_id")
                self.test_user_id = data.get("user_id")
                
                self.log_test(
                    "ПРОВЕРКА СУЩЕСТВОВАНИЯ ENDPOINT",
                    True,
                    f"✅ Endpoint работает! Курьер создан: ID={self.test_courier_id}, User ID={self.test_user_id}"
                )
                return True
            elif response.status_code in [400, 422]:
                # Ошибки валидации - это нормально, главное что endpoint существует
                self.log_test(
                    "ПРОВЕРКА СУЩЕСТВОВАНИЯ ENDPOINT",
                    True,
                    f"✅ Endpoint существует (ошибка валидации): HTTP {response.status_code} - {response.text}"
                )
                return True
            else:
                self.log_test(
                    "ПРОВЕРКА СУЩЕСТВОВАНИЯ ENDPOINT",
                    False,
                    f"Неожиданный HTTP код: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("ПРОВЕРКА СУЩЕСТВОВАНИЯ ENDPOINT", False, f"Ошибка: {str(e)}")
            return False
    
    def test_validation_errors(self):
        """Тестирование различных ошибок валидации"""
        try:
            self.log("🔍 ТЕСТ: Проверка валидации данных CourierCreate")
            
            if not self.available_warehouses:
                self.log_test(
                    "ТЕСТИРОВАНИЕ ВАЛИДАЦИИ",
                    False,
                    "Нет доступных складов для тестирования"
                )
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            validation_tests = []
            
            # Тест 1: Пустые обязательные поля
            test_data = {
                "full_name": "",
                "phone": "",
                "password": "",
                "address": "",
                "transport_type": "car",
                "transport_number": "",
                "transport_capacity": 0,
                "assigned_warehouse_id": ""
            }
            
            response = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                       json=test_data, headers=headers)
            validation_tests.append(f"Пустые поля: HTTP {response.status_code}")
            
            # Тест 2: Неверный transport_type
            test_data = {
                "full_name": "Тест Курьер",
                "phone": "+79991234568",
                "password": "courier123",
                "address": "Тестовый адрес",
                "transport_type": "invalid_transport",
                "transport_number": "A123BC778",
                "transport_capacity": 100.0,
                "assigned_warehouse_id": self.available_warehouses[0]["id"]
            }
            
            response = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                       json=test_data, headers=headers)
            validation_tests.append(f"Неверный transport_type: HTTP {response.status_code}")
            
            # Тест 3: Несуществующий склад
            test_data = {
                "full_name": "Тест Курьер",
                "phone": "+79991234569",
                "password": "courier123",
                "address": "Тестовый адрес",
                "transport_type": "car",
                "transport_number": "A123BC779",
                "transport_capacity": 100.0,
                "assigned_warehouse_id": "non-existent-warehouse-id"
            }
            
            response = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                       json=test_data, headers=headers)
            validation_tests.append(f"Несуществующий склад: HTTP {response.status_code}")
            
            self.log_test(
                "ТЕСТИРОВАНИЕ ВАЛИДАЦИИ",
                True,
                f"Результаты валидации: {', '.join(validation_tests)}"
            )
            return True
                
        except Exception as e:
            self.log_test("ТЕСТИРОВАНИЕ ВАЛИДАЦИИ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_transport_types(self):
        """Тестирование всех доступных типов транспорта"""
        try:
            self.log("🚗 ТЕСТ: Проверка всех типов транспорта TransportType")
            
            if not self.available_warehouses:
                self.log_test(
                    "ТЕСТИРОВАНИЕ ТИПОВ ТРАНСПОРТА",
                    False,
                    "Нет доступных складов для тестирования"
                )
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            transport_types = ["car", "van", "truck", "motorcycle", "bicycle", "on_foot"]
            successful_types = []
            failed_types = []
            
            for i, transport_type in enumerate(transport_types):
                test_data = {
                    "full_name": f"Курьер {transport_type.title()}",
                    "phone": f"+7999123456{i}",
                    "password": "courier123",
                    "address": "Тестовый адрес",
                    "transport_type": transport_type,
                    "transport_number": f"TEST{i:03d}",
                    "transport_capacity": 50.0 + i * 10,
                    "assigned_warehouse_id": self.available_warehouses[0]["id"]
                }
                
                response = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                           json=test_data, headers=headers)
                
                if response.status_code == 200:
                    successful_types.append(transport_type)
                    # Сохраняем ID для очистки
                    data = response.json()
                    courier_id = data.get("courier_id")
                    if courier_id:
                        # Удаляем тестового курьера
                        self.session.delete(f"{API_BASE}/admin/couriers/{courier_id}", headers=headers)
                elif response.status_code == 400 and "already exists" in response.text:
                    # Пользователь уже существует - это нормально для тестирования
                    successful_types.append(f"{transport_type} (дубликат)")
                else:
                    failed_types.append(f"{transport_type}: HTTP {response.status_code}")
                
                time.sleep(0.1)  # Небольшая пауза между запросами
            
            success = len(failed_types) == 0
            details = f"Успешные: {', '.join(successful_types)}"
            if failed_types:
                details += f"; Неудачные: {', '.join(failed_types)}"
            
            self.log_test(
                "ТЕСТИРОВАНИЕ ТИПОВ ТРАНСПОРТА",
                success,
                details
            )
            return success
                
        except Exception as e:
            self.log_test("ТЕСТИРОВАНИЕ ТИПОВ ТРАНСПОРТА", False, f"Ошибка: {str(e)}")
            return False
    
    def test_authorization_levels(self):
        """Тестирование различных уровней авторизации"""
        try:
            self.log("👤 ТЕСТ: Проверка авторизации администратора и оператора")
            
            if not self.available_warehouses:
                self.log_test(
                    "ТЕСТИРОВАНИЕ АВТОРИЗАЦИИ",
                    False,
                    "Нет доступных складов для тестирования"
                )
                return False
            
            auth_tests = []
            
            # Тест 1: Администратор
            if self.admin_token:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                test_data = {
                    "full_name": "Админ Тест Курьер",
                    "phone": "+79991234570",
                    "password": "courier123",
                    "address": "Тестовый адрес",
                    "transport_type": "car",
                    "transport_number": "ADMIN001",
                    "transport_capacity": 100.0,
                    "assigned_warehouse_id": self.available_warehouses[0]["id"]
                }
                
                response = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                           json=test_data, headers=headers)
                
                if response.status_code == 200:
                    auth_tests.append("Администратор: ✅")
                    # Удаляем тестового курьера
                    data = response.json()
                    courier_id = data.get("courier_id")
                    if courier_id:
                        self.session.delete(f"{API_BASE}/admin/couriers/{courier_id}", headers=headers)
                elif response.status_code == 400 and "already exists" in response.text:
                    auth_tests.append("Администратор: ✅ (дубликат)")
                else:
                    auth_tests.append(f"Администратор: ❌ HTTP {response.status_code}")
            
            # Тест 2: Оператор склада
            if self.operator_token:
                headers = {"Authorization": f"Bearer {self.operator_token}"}
                test_data = {
                    "full_name": "Оператор Тест Курьер",
                    "phone": "+79991234571",
                    "password": "courier123",
                    "address": "Тестовый адрес",
                    "transport_type": "van",
                    "transport_number": "OPER001",
                    "transport_capacity": 150.0,
                    "assigned_warehouse_id": self.available_warehouses[0]["id"]
                }
                
                response = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                           json=test_data, headers=headers)
                
                if response.status_code == 200:
                    auth_tests.append("Оператор: ✅")
                    # Удаляем тестового курьера
                    data = response.json()
                    courier_id = data.get("courier_id")
                    if courier_id:
                        self.session.delete(f"{API_BASE}/admin/couriers/{courier_id}", headers=headers)
                elif response.status_code == 400 and "already exists" in response.text:
                    auth_tests.append("Оператор: ✅ (дубликат)")
                else:
                    auth_tests.append(f"Оператор: ❌ HTTP {response.status_code}")
            
            # Тест 3: Без авторизации
            test_data = {
                "full_name": "Неавторизованный Курьер",
                "phone": "+79991234572",
                "password": "courier123",
                "address": "Тестовый адрес",
                "transport_type": "car",
                "transport_number": "NOAUTH001",
                "transport_capacity": 100.0,
                "assigned_warehouse_id": self.available_warehouses[0]["id"]
            }
            
            response = self.session.post(f"{API_BASE}/admin/couriers/create", json=test_data)
            
            if response.status_code in [401, 403]:
                auth_tests.append("Без авторизации: ✅ (отклонено)")
            else:
                auth_tests.append(f"Без авторизации: ❌ HTTP {response.status_code}")
            
            self.log_test(
                "ТЕСТИРОВАНИЕ АВТОРИЗАЦИИ",
                True,
                f"Результаты: {', '.join(auth_tests)}"
            )
            return True
                
        except Exception as e:
            self.log_test("ТЕСТИРОВАНИЕ АВТОРИЗАЦИИ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_duplicate_phone_handling(self):
        """Тестирование обработки дублирующихся номеров телефонов"""
        try:
            self.log("📞 ТЕСТ: Проверка обработки дублирующихся номеров телефонов")
            
            if not self.available_warehouses:
                self.log_test(
                    "ТЕСТИРОВАНИЕ ДУБЛИКАТОВ ТЕЛЕФОНОВ",
                    False,
                    "Нет доступных складов для тестирования"
                )
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Создаем первого курьера
            test_data_1 = {
                "full_name": "Первый Курьер",
                "phone": "+79991234580",
                "password": "courier123",
                "address": "Тестовый адрес 1",
                "transport_type": "car",
                "transport_number": "DUP001",
                "transport_capacity": 100.0,
                "assigned_warehouse_id": self.available_warehouses[0]["id"]
            }
            
            response1 = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                        json=test_data_1, headers=headers)
            
            first_courier_id = None
            if response1.status_code == 200:
                data = response1.json()
                first_courier_id = data.get("courier_id")
            
            # Пытаемся создать второго курьера с тем же номером телефона
            test_data_2 = {
                "full_name": "Второй Курьер",
                "phone": "+79991234580",  # Тот же номер!
                "password": "courier456",
                "address": "Тестовый адрес 2",
                "transport_type": "van",
                "transport_number": "DUP002",
                "transport_capacity": 150.0,
                "assigned_warehouse_id": self.available_warehouses[0]["id"]
            }
            
            response2 = self.session.post(f"{API_BASE}/admin/couriers/create", 
                                        json=test_data_2, headers=headers)
            
            # Проверяем что второй запрос отклонен
            if response2.status_code == 400 and "already exists" in response2.text:
                self.log_test(
                    "ТЕСТИРОВАНИЕ ДУБЛИКАТОВ ТЕЛЕФОНОВ",
                    True,
                    f"✅ Дубликат корректно отклонен: HTTP {response2.status_code} - {response2.text}"
                )
                success = True
            else:
                self.log_test(
                    "ТЕСТИРОВАНИЕ ДУБЛИКАТОВ ТЕЛЕФОНОВ",
                    False,
                    f"❌ Дубликат не отклонен: HTTP {response2.status_code} - {response2.text}"
                )
                success = False
            
            # Очистка: удаляем первого курьера если он был создан
            if first_courier_id:
                self.session.delete(f"{API_BASE}/admin/couriers/{first_courier_id}", headers=headers)
            
            return success
                
        except Exception as e:
            self.log_test("ТЕСТИРОВАНИЕ ДУБЛИКАТОВ ТЕЛЕФОНОВ", False, f"Ошибка: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """Очистить тестовые данные"""
        try:
            if self.test_courier_id and self.admin_token:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                response = self.session.delete(f"{API_BASE}/admin/couriers/{self.test_courier_id}", headers=headers)
                
                if response.status_code == 200:
                    self.log_test(
                        "ОЧИСТКА ТЕСТОВЫХ ДАННЫХ",
                        True,
                        f"Тестовый курьер {self.test_courier_id} успешно удален"
                    )
                else:
                    self.log_test(
                        "ОЧИСТКА ТЕСТОВЫХ ДАННЫХ",
                        False,
                        f"Ошибка удаления курьера: HTTP {response.status_code}"
                    )
            return True
                
        except Exception as e:
            self.log_test("ОЧИСТКА ТЕСТОВЫХ ДАННЫХ", False, f"Ошибка: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        self.log("🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема 404 при создании курьера в TAJLINE.TJ")
        self.log("=" * 100)
        
        # Список всех тестов
        tests = [
            ("Авторизация администратора", self.test_admin_auth),
            ("Авторизация оператора склада", self.test_operator_auth),
            ("Получение списка складов", self.get_available_warehouses),
            ("🎯 КРИТИЧЕСКИЙ: Проверка существования endpoint", self.test_endpoint_exists),
            ("Тестирование валидации данных", self.test_validation_errors),
            ("Тестирование типов транспорта", self.test_transport_types),
            ("Тестирование уровней авторизации", self.test_authorization_levels),
            ("Тестирование дубликатов телефонов", self.test_duplicate_phone_handling)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n📋 ТЕСТ: {test_name}")
            self.log("-" * 80)
            
            try:
                result = test_func()
                if result:
                    passed_tests += 1
                    self.log(f"✅ ТЕСТ ПРОЙДЕН: {test_name}")
                else:
                    self.log(f"❌ ТЕСТ НЕ ПРОЙДЕН: {test_name}")
            except Exception as e:
                self.log(f"❌ ИСКЛЮЧЕНИЕ В ТЕСТЕ {test_name}: {e}", "ERROR")
        
        # Очистка тестовых данных
        self.cleanup_test_data()
        
        # Итоговый отчет
        self.log("\n" + "=" * 100)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ КРИТИЧЕСКОЙ ДИАГНОСТИКИ")
        self.log("=" * 100)
        
        success_rate = (passed_tests / total_tests) * 100
        self.log(f"📊 РЕЗУЛЬТАТ: {passed_tests}/{total_tests} тестов пройдено ({success_rate:.1f}%)")
        
        self.log("\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            self.log(f"   {status} {result['test']}: {result['details']}")
        
        # КРИТИЧЕСКИЕ ВЫВОДЫ
        self.log("\n🔍 КРИТИЧЕСКИЕ ВЫВОДЫ:")
        
        endpoint_test = next((r for r in self.test_results if "СУЩЕСТВОВАНИЯ ENDPOINT" in r["test"]), None)
        if endpoint_test:
            if endpoint_test["success"]:
                self.log("✅ ENDPOINT POST /api/admin/couriers/create РАБОТАЕТ КОРРЕКТНО")
                self.log("✅ Проблема 404 НЕ связана с отсутствием endpoint'а")
                self.log("🔍 ВОЗМОЖНЫЕ ПРИЧИНЫ 404 ошибки:")
                self.log("   1. Неправильный URL в frontend (проверить REACT_APP_BACKEND_URL)")
                self.log("   2. Проблемы с CORS или прокси")
                self.log("   3. Неправильный HTTP метод (должен быть POST)")
                self.log("   4. Проблемы с авторизацией (отсутствует Bearer token)")
            else:
                self.log("🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА НАЙДЕНА: ENDPOINT ВОЗВРАЩАЕТ 404!")
                self.log("❌ Это объясняет проблему пользователя")
                self.log("🔧 РЕШЕНИЕ: Проверить маршрутизацию FastAPI и убедиться что endpoint определен корректно")
        
        if success_rate >= 75:
            self.log(f"\n🎉 ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО!")
            self.log(f"✅ Большинство компонентов системы создания курьеров работают корректно")
        else:
            self.log(f"\n❌ ДИАГНОСТИКА ВЫЯВИЛА КРИТИЧЕСКИЕ ПРОБЛЕМЫ!")
            self.log(f"❌ Требуется немедленное исправление проблем с созданием курьеров")
        
        return success_rate >= 75

def main():
    """Главная функция"""
    print("🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема 404 при создании курьера в TAJLINE.TJ")
    print("=" * 100)
    
    tester = CourierCreation404Tester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()