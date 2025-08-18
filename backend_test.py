#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Полный флоу приёма груза через форму оператора в TAJLINE.TJ
Тестирование API endpoint /api/operator/cargo/direct-accept с множественными грузами
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://tajline-cargo-3.preview.emergentagent.com/api"

# Тестовые данные для авторизации
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """Логирование результатов тестов"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   📝 {details}")
        print()

    def authenticate_admin(self):
        """Авторизация администратора"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
                
                user_info = data.get("user", {})
                self.log_test(
                    "Авторизация администратора",
                    True,
                    f"Пользователь: {user_info.get('full_name', 'N/A')} (роль: {user_info.get('role', 'N/A')})"
                )
                return True
            else:
                self.log_test("Авторизация администратора", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Авторизация администратора", False, f"Ошибка: {str(e)}")
            return False

    def authenticate_operator(self):
        """Авторизация оператора склада"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=OPERATOR_CREDENTIALS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                
                user_info = data.get("user", {})
                self.log_test(
                    "Авторизация оператора склада",
                    True,
                    f"Пользователь: {user_info.get('full_name', 'N/A')} (роль: {user_info.get('role', 'N/A')})"
                )
                return True
            else:
                self.log_test("Авторизация оператора склада", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Авторизация оператора склада", False, f"Ошибка: {str(e)}")
            return False

    def get_warehouses(self):
        """Получение списка складов"""
        try:
            response = self.session.get(f"{BACKEND_URL}/warehouses", timeout=10)
            
            if response.status_code == 200:
                warehouses = response.json()
                if warehouses:
                    warehouse_info = []
                    for w in warehouses[:3]:  # Показываем первые 3 склада
                        warehouse_info.append(f"{w.get('name', 'N/A')} (ID: {w.get('id', 'N/A')})")
                    
                    self.log_test(
                        "Получение списка складов",
                        True,
                        f"Найдено {len(warehouses)} складов. Примеры: {'; '.join(warehouse_info)}"
                    )
                    return warehouses
                else:
                    self.log_test("Получение списка складов", False, "Список складов пуст")
                    return []
            else:
                self.log_test("Получение списка складов", False, f"HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.log_test("Получение списка складов", False, f"Ошибка: {str(e)}")
            return []

    def test_direct_accept_single_cargo(self, warehouse_id):
        """Тест с одним грузом"""
        try:
            # Переключаемся на токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            payload = {
                "sender_full_name": "Иван Петров",
                "sender_phone": "+79991234567",
                "sender_address": "Москва, ул. Ленина 1",
                "recipient_full_name": "Али Рахимов",
                "recipient_phone": "+992901234567",
                "recipient_address": "Душанбе, ул. Рудаки 10",
                "cargo_items": [
                    {
                        "cargo_name": "Документы",
                        "weight": 0.5,
                        "price_per_kg": 2000.0
                    }
                ],
                "description": "Принят через оператора на складе",
                "route": "moscow_to_tajikistan",
                "warehouse_id": warehouse_id,
                "payment_method": "cash",
                "payment_amount": 1000.0
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/direct-accept",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа
                required_fields = ["success", "base_request_number", "total_cargo_count", "created_cargo", "received_by", "received_at"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    created_cargo = data.get("created_cargo", [])
                    if created_cargo and len(created_cargo) == 1:
                        cargo = created_cargo[0]
                        cargo_fields = ["cargo_id", "cargo_number", "cargo_name", "weight", "declared_value"]
                        cargo_missing = [field for field in cargo_fields if field not in cargo]
                        
                        if not cargo_missing:
                            self.log_test(
                                "Тест с одним грузом - структура ответа",
                                True,
                                f"Базовый номер: {data.get('base_request_number')}, "
                                f"Номер груза: {cargo.get('cargo_number')}, "
                                f"Вес: {cargo.get('weight')}кг, "
                                f"Стоимость: {cargo.get('declared_value')}₽"
                            )
                            return data
                        else:
                            self.log_test(
                                "Тест с одним грузом - структура ответа",
                                False,
                                f"Отсутствуют поля в created_cargo: {cargo_missing}"
                            )
                    else:
                        self.log_test(
                            "Тест с одним грузом - структура ответа",
                            False,
                            f"Неверное количество грузов: ожидался 1, получено {len(created_cargo)}"
                        )
                else:
                    self.log_test(
                        "Тест с одним грузом - структура ответа",
                        False,
                        f"Отсутствуют обязательные поля: {missing_fields}"
                    )
            else:
                self.log_test(
                    "Тест с одним грузом",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_test("Тест с одним грузом", False, f"Ошибка: {str(e)}")
            
        return None

    def test_direct_accept_multiple_cargo(self, warehouse_id):
        """Тест с множественными грузами"""
        try:
            payload = {
                "sender_full_name": "Петр Сидоров",
                "sender_phone": "+79995555555",
                "sender_address": "Москва, ул. Пушкина 5",
                "recipient_full_name": "Бахтияр Назаров",
                "recipient_phone": "+992905555555",
                "recipient_address": "Душанбе, ул. Исмоили Сомони 25",
                "cargo_items": [
                    {
                        "cargo_name": "Электроника",
                        "weight": 2.0,
                        "price_per_kg": 100.0
                    },
                    {
                        "cargo_name": "Одежда",
                        "weight": 1.5,
                        "price_per_kg": 50.0
                    },
                    {
                        "cargo_name": "Книги",
                        "weight": 3.0,
                        "price_per_kg": 30.0
                    }
                ],
                "description": "Принят через оператора на складе",
                "route": "moscow_to_tajikistan",
                "warehouse_id": warehouse_id,
                "payment_method": "card_transfer",
                "payment_amount": 365.0
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/direct-accept",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа
                required_fields = ["success", "base_request_number", "total_cargo_count", "created_cargo"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    created_cargo = data.get("created_cargo", [])
                    expected_count = 3
                    
                    if len(created_cargo) == expected_count:
                        # Проверяем каждый груз
                        all_valid = True
                        cargo_details = []
                        
                        for i, cargo in enumerate(created_cargo):
                            cargo_fields = ["cargo_id", "cargo_number", "cargo_name", "weight", "declared_value"]
                            cargo_missing = [field for field in cargo_fields if field not in cargo]
                            
                            if cargo_missing:
                                all_valid = False
                                break
                            
                            cargo_details.append(
                                f"Груз {i+1}: {cargo.get('cargo_name')} "
                                f"({cargo.get('cargo_number')}, {cargo.get('weight')}кг, {cargo.get('declared_value')}₽)"
                            )
                        
                        if all_valid:
                            self.log_test(
                                "Тест с множественными грузами - структура ответа",
                                True,
                                f"Базовый номер: {data.get('base_request_number')}, "
                                f"Создано {len(created_cargo)} грузов. "
                                f"Детали: {'; '.join(cargo_details)}"
                            )
                            return data
                        else:
                            self.log_test(
                                "Тест с множественными грузами - структура ответа",
                                False,
                                f"Неполные данные в грузах"
                            )
                    else:
                        self.log_test(
                            "Тест с множественными грузами - структура ответа",
                            False,
                            f"Неверное количество грузов: ожидалось {expected_count}, получено {len(created_cargo)}"
                        )
                else:
                    self.log_test(
                        "Тест с множественными грузами - структура ответа",
                        False,
                        f"Отсутствуют обязательные поля: {missing_fields}"
                    )
            else:
                self.log_test(
                    "Тест с множественными грузами",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_test("Тест с множественными грузами", False, f"Ошибка: {str(e)}")
            
        return None

    def test_validation_errors(self, warehouse_id):
        """Тест валидации ошибок"""
        test_cases = [
            {
                "name": "Отсутствие обязательных полей",
                "payload": {
                    "sender_full_name": "Тест",
                    # Отсутствуют другие обязательные поля
                },
                "expected_status": [400, 422]
            },
            {
                "name": "Пустой массив cargo_items",
                "payload": {
                    "sender_full_name": "Тест Отправитель",
                    "sender_phone": "+79991234567",
                    "sender_address": "Москва, ул. Тестовая 1",
                    "recipient_full_name": "Тест Получатель",
                    "recipient_phone": "+992901234567",
                    "recipient_address": "Душанбе, ул. Тестовая 1",
                    "cargo_items": [],  # Пустой массив
                    "description": "Тест",
                    "route": "moscow_to_tajikistan",
                    "warehouse_id": warehouse_id
                },
                "expected_status": [400, 422]
            },
            {
                "name": "Некорректные типы данных",
                "payload": {
                    "sender_full_name": "Тест Отправитель",
                    "sender_phone": "+79991234567",
                    "sender_address": "Москва, ул. Тестовая 1",
                    "recipient_full_name": "Тест Получатель",
                    "recipient_phone": "+992901234567",
                    "recipient_address": "Душанбе, ул. Тестовая 1",
                    "cargo_items": [
                        {
                            "cargo_name": "Тест",
                            "weight": "неверный_тип",  # Должно быть число
                            "price_per_kg": 100.0
                        }
                    ],
                    "description": "Тест",
                    "route": "moscow_to_tajikistan",
                    "warehouse_id": warehouse_id
                },
                "expected_status": [400, 422]
            }
        ]
        
        validation_results = []
        
        for test_case in test_cases:
            try:
                response = self.session.post(
                    f"{BACKEND_URL}/operator/cargo/direct-accept",
                    json=test_case["payload"],
                    timeout=10
                )
                
                if response.status_code in test_case["expected_status"]:
                    self.log_test(
                        f"Валидация: {test_case['name']}",
                        True,
                        f"Корректно возвращен HTTP {response.status_code}"
                    )
                    validation_results.append(True)
                else:
                    self.log_test(
                        f"Валидация: {test_case['name']}",
                        False,
                        f"Ожидался HTTP {test_case['expected_status']}, получен {response.status_code}"
                    )
                    validation_results.append(False)
                    
            except Exception as e:
                self.log_test(f"Валидация: {test_case['name']}", False, f"Ошибка: {str(e)}")
                validation_results.append(False)
        
        return validation_results

    def verify_cargo_creation(self, created_cargo_data):
        """Проверка корректности создания грузов"""
        if not created_cargo_data:
            return False
            
        try:
            # Переключаемся на токен администратора для проверки
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            created_cargo = created_cargo_data.get("created_cargo", [])
            verification_results = []
            
            for cargo in created_cargo:
                cargo_id = cargo.get("cargo_id")
                cargo_number = cargo.get("cargo_number")
                
                if not cargo_id:
                    verification_results.append(False)
                    continue
                
                # Проверяем существование груза в базе данных
                response = self.session.get(
                    f"{BACKEND_URL}/debug/find-cargo-by-number/{cargo_number}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    found_cargo = data.get("found_cargo")
                    
                    if found_cargo and len(found_cargo) > 0:
                        cargo_info = found_cargo[0]
                        
                        # Проверяем ключевые поля
                        has_warehouse_id = cargo_info.get("warehouse_id") is not None
                        has_cargo_number = cargo_info.get("cargo_number") == cargo_number
                        has_status = cargo_info.get("status") is not None
                        
                        if has_warehouse_id and has_cargo_number and has_status:
                            verification_results.append(True)
                            self.log_test(
                                f"Проверка груза {cargo_number}",
                                True,
                                f"Груз найден в базе данных со статусом {cargo_info.get('status')}"
                            )
                        else:
                            verification_results.append(False)
                            self.log_test(
                                f"Проверка груза {cargo_number}",
                                False,
                                f"Неполные данные груза в базе"
                            )
                    else:
                        verification_results.append(False)
                        self.log_test(
                            f"Проверка груза {cargo_number}",
                            False,
                            "Груз не найден в базе данных"
                        )
                else:
                    verification_results.append(False)
                    self.log_test(
                        f"Проверка груза {cargo_number}",
                        False,
                        f"Ошибка поиска груза: HTTP {response.status_code}"
                    )
            
            return all(verification_results)
            
        except Exception as e:
            self.log_test("Проверка создания грузов", False, f"Ошибка: {str(e)}")
            return False

    def cleanup_test_data(self, created_cargo_data):
        """Очистка тестовых данных"""
        if not created_cargo_data:
            return
            
        try:
            # Переключаемся на токен администратора
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            created_cargo = created_cargo_data.get("created_cargo", [])
            cleanup_count = 0
            
            for cargo in created_cargo:
                cargo_id = cargo.get("cargo_id")
                cargo_number = cargo.get("cargo_number")
                
                if cargo_id:
                    response = self.session.delete(
                        f"{BACKEND_URL}/admin/cargo/{cargo_id}",
                        timeout=10
                    )
                    
                    if response.status_code in [200, 204]:
                        cleanup_count += 1
            
            self.log_test(
                "Очистка тестовых данных",
                cleanup_count > 0,
                f"Удалено {cleanup_count} из {len(created_cargo)} тестовых грузов"
            )
            
        except Exception as e:
            self.log_test("Очистка тестовых данных", False, f"Ошибка: {str(e)}")

    def run_comprehensive_test(self):
        """Запуск полного тестирования"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Полный флоу приёма груза через форму оператора")
        print("=" * 80)
        print()
        
        # 1. Авторизация
        if not self.authenticate_admin():
            print("❌ Не удалось авторизоваться как администратор. Тестирование прервано.")
            return False
            
        if not self.authenticate_operator():
            print("❌ Не удалось авторизоваться как оператор. Тестирование прервано.")
            return False
        
        # 2. Получение складов
        warehouses = self.get_warehouses()
        if not warehouses:
            print("❌ Не удалось получить список складов. Тестирование прервано.")
            return False
        
        warehouse_id = warehouses[0].get("id")
        
        # 3. Тестирование endpoint с одним грузом
        print("🔍 Тестирование endpoint /api/operator/cargo/direct-accept с одним грузом")
        print("-" * 60)
        single_cargo_result = self.test_direct_accept_single_cargo(warehouse_id)
        
        # 4. Тестирование endpoint с множественными грузами
        print("🔍 Тестирование endpoint /api/operator/cargo/direct-accept с множественными грузами")
        print("-" * 60)
        multiple_cargo_result = self.test_direct_accept_multiple_cargo(warehouse_id)
        
        # 5. Тестирование валидации
        print("🔍 Тестирование валидации ошибок")
        print("-" * 60)
        validation_results = self.test_validation_errors(warehouse_id)
        
        # 6. Проверка корректности создания грузов
        print("🔍 Проверка корректности создания грузов в базе данных")
        print("-" * 60)
        verification_success = False
        if single_cargo_result:
            verification_success = self.verify_cargo_creation(single_cargo_result)
        
        # 7. Очистка тестовых данных
        print("🧹 Очистка тестовых данных")
        print("-" * 60)
        if single_cargo_result:
            self.cleanup_test_data(single_cargo_result)
        if multiple_cargo_result:
            self.cleanup_test_data(multiple_cargo_result)
        
        # 8. Подведение итогов
        self.print_summary()
        
        return True

    def print_summary(self):
        """Вывод итогового отчета"""
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {passed_tests} ✅")
        print(f"Неудачных: {failed_tests} ❌")
        print(f"Процент успеха: {success_rate:.1f}%")
        print()
        
        # Группировка результатов по категориям
        categories = {
            "Авторизация": [],
            "API Endpoints": [],
            "Валидация": [],
            "Проверка данных": [],
            "Очистка": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if "авторизация" in test_name.lower():
                categories["Авторизация"].append(result)
            elif "валидация" in test_name.lower():
                categories["Валидация"].append(result)
            elif "проверка" in test_name.lower():
                categories["Проверка данных"].append(result)
            elif "очистка" in test_name.lower():
                categories["Очистка"].append(result)
            else:
                categories["API Endpoints"].append(result)
        
        for category, tests in categories.items():
            if tests:
                passed = sum(1 for t in tests if t["success"])
                total = len(tests)
                print(f"{category}: {passed}/{total} ✅")
        
        print("\n" + "=" * 80)
        
        # Критические выводы
        if success_rate >= 90:
            print("🎉 КРИТИЧЕСКИЙ ВЫВОД: ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            print("Endpoint /api/operator/cargo/direct-accept работает корректно с множественными грузами.")
        elif success_rate >= 70:
            print("⚠️ КРИТИЧЕСКИЙ ВЫВОД: ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ПРЕДУПРЕЖДЕНИЯМИ!")
            print("Основная функциональность работает, но есть минорные проблемы.")
        else:
            print("❌ КРИТИЧЕСКИЙ ВЫВОД: ОБНАРУЖЕНЫ СЕРЬЕЗНЫЕ ПРОБЛЕМЫ!")
            print("Требуется исправление критических ошибок.")
        
        print("=" * 80)

def main():
    """Главная функция"""
    tester = BackendTester()
    
    try:
        success = tester.run_comprehensive_test()
        if success:
            print("\n✅ Тестирование завершено успешно!")
        else:
            print("\n❌ Тестирование завершено с ошибками!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка тестирования: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()