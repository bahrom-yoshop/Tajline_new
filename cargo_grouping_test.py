#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Проверка исправления группировки связанных грузов в TAJLINE.TJ
Создание тестовых данных для проверки исправления группировки связанных грузов
"""

import requests
import json
import sys
from datetime import datetime
from collections import defaultdict

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

# Тестовые данные для авторизации
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

class CargoGroupingTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        self.created_cargo_ids = []
        
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
                
                user_info = data.get("user", {})
                self.log_test(
                    "Авторизация администратора",
                    True,
                    f"Пользователь: {user_info.get('full_name', 'N/A')} (номер: {user_info.get('user_number', 'N/A')}, роль: {user_info.get('role', 'N/A')})"
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
                
                # Обновляем заголовки для оператора
                self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
                
                user_info = data.get("user", {})
                self.log_test(
                    "Авторизация оператора склада",
                    True,
                    f"Пользователь: {user_info.get('full_name', 'N/A')} (номер: {user_info.get('user_number', 'N/A')}, роль: {user_info.get('role', 'N/A')})"
                )
                return True
            else:
                self.log_test("Авторизация оператора склада", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Авторизация оператора склада", False, f"Ошибка: {str(e)}")
            return False

    def get_warehouses(self):
        """Получить список складов"""
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/warehouses", timeout=10)
            
            if response.status_code == 200:
                warehouses = response.json()
                if warehouses:
                    warehouse_info = []
                    for w in warehouses[:3]:  # Показываем первые 3 склада
                        warehouse_info.append(f"{w.get('name', 'N/A')} (ID: {w.get('id', 'N/A')})")
                    
                    self.log_test(
                        "Получение списка складов",
                        True,
                        f"Найдено {len(warehouses)} складов. Примеры: {', '.join(warehouse_info)}"
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

    def create_cargo_with_multiple_items(self):
        """Создать заявку с несколькими грузами через API /api/operator/cargo/direct-accept"""
        try:
            # Получаем склады для назначения
            warehouses = self.get_warehouses()
            if not warehouses:
                self.log_test("Создание заявки с несколькими грузами", False, "Нет доступных складов")
                return None
            
            # Используем первый доступный склад
            destination_warehouse = warehouses[0]
            
            # Данные заявки с 2 грузами как указано в review request
            cargo_data = {
                "sender_full_name": "Тест Группировки",
                "sender_phone": "+79991111111",
                "sender_address": "Москва, ул. Тестовая 1",
                "recipient_full_name": "Получатель Теста",
                "recipient_phone": "+992901111111",
                "recipient_address": "Душанбе, ул. Тестовая 2",
                "cargo_items": [
                    {
                        "cargo_name": "Груз 1 для теста группировки",
                        "weight": "1.0",
                        "price_per_kg": "100"
                    },
                    {
                        "cargo_name": "Груз 2 для теста группировки", 
                        "weight": "2.0",
                        "price_per_kg": "150"
                    }
                ],
                "destination_warehouse_id": destination_warehouse.get("id"),
                "destination_warehouse_name": destination_warehouse.get("name", "Тестовый склад"),
                "route": "moscow_to_tajikistan",
                "payment_method": "cash",
                "payment_amount": "450",
                "description": "Тестовая заявка для проверки группировки грузов"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/direct-accept",
                json=cargo_data,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                created_cargo = data.get("created_cargo", [])
                base_request_number = data.get("base_request_number")
                
                if len(created_cargo) == 2 and base_request_number:
                    # Сохраняем ID созданных грузов для очистки
                    for cargo in created_cargo:
                        if cargo.get("id"):
                            self.created_cargo_ids.append(cargo["id"])
                    
                    cargo_numbers = [cargo.get("cargo_number", "N/A") for cargo in created_cargo]
                    
                    self.log_test(
                        "Создание заявки с несколькими грузами",
                        True,
                        f"Создано {len(created_cargo)} грузов. Базовый номер: {base_request_number}. Номера грузов: {', '.join(cargo_numbers)}"
                    )
                    
                    return {
                        "created_cargo": created_cargo,
                        "base_request_number": base_request_number,
                        "cargo_numbers": cargo_numbers
                    }
                else:
                    self.log_test(
                        "Создание заявки с несколькими грузами", 
                        False, 
                        f"Ожидалось 2 груза, получено {len(created_cargo)}. Base request number: {base_request_number}"
                    )
                    return None
            else:
                self.log_test("Создание заявки с несколькими грузами", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Создание заявки с несколькими грузами", False, f"Ошибка: {str(e)}")
            return None

    def verify_cargo_numbering(self, cargo_data):
        """Проверить правильность нумерации грузов"""
        if not cargo_data:
            return False
            
        created_cargo = cargo_data["created_cargo"]
        base_request_number = cargo_data["base_request_number"]
        
        try:
            # Проверяем, что у всех грузов одинаковый base_request_number
            base_numbers_match = True
            cargo_numbers = []
            
            for cargo in created_cargo:
                cargo_base = cargo.get("base_request_number")
                cargo_number = cargo.get("cargo_number")
                
                if cargo_base != base_request_number:
                    base_numbers_match = False
                
                cargo_numbers.append(cargo_number)
            
            # Проверяем формат номеров (должны быть XXXXXXXX/01, XXXXXXXX/02)
            correct_format = True
            expected_suffixes = ["/01", "/02"]
            
            for i, cargo_number in enumerate(cargo_numbers):
                if not cargo_number or not cargo_number.endswith(expected_suffixes[i]):
                    correct_format = False
                    break
            
            if base_numbers_match and correct_format:
                self.log_test(
                    "Проверка нумерации грузов",
                    True,
                    f"Все грузы имеют одинаковый base_request_number: {base_request_number}. Номера: {', '.join(cargo_numbers)}"
                )
                return True
            else:
                details = []
                if not base_numbers_match:
                    details.append("base_request_number не совпадают")
                if not correct_format:
                    details.append("неправильный формат номеров")
                
                self.log_test(
                    "Проверка нумерации грузов",
                    False,
                    f"Проблемы: {', '.join(details)}. Номера: {', '.join(cargo_numbers)}"
                )
                return False
                
        except Exception as e:
            self.log_test("Проверка нумерации грузов", False, f"Ошибка: {str(e)}")
            return False

    def check_available_for_placement(self, cargo_data):
        """Проверить API размещения и найти созданные грузы"""
        if not cargo_data:
            return False
            
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                pagination = data.get("pagination", {})
                
                # Ищем наши созданные грузы
                created_cargo_numbers = cargo_data["cargo_numbers"]
                found_cargo = []
                
                for item in items:
                    cargo_number = item.get("cargo_number")
                    if cargo_number in created_cargo_numbers:
                        found_cargo.append({
                            "cargo_number": cargo_number,
                            "base_request_number": item.get("base_request_number"),
                            "cargo_name": item.get("cargo_name"),
                            "weight": item.get("weight"),
                            "warehouse_name": item.get("warehouse_name")
                        })
                
                if len(found_cargo) >= 2:
                    self.log_test(
                        "Поиск грузов в API размещения",
                        True,
                        f"Найдено {len(found_cargo)} грузов из наших {len(created_cargo_numbers)} созданных в списке размещения (всего в списке: {len(items)})"
                    )
                    
                    # Показываем структуру данных
                    print("📊 Структура данных найденных грузов:")
                    for cargo in found_cargo:
                        print(f"   • {cargo['cargo_number']}: {cargo['cargo_name']} ({cargo['weight']}кг) - {cargo['warehouse_name']}")
                    print()
                    
                    # Проверяем на дублирование наших грузов
                    cargo_numbers_found = [c["cargo_number"] for c in found_cargo]
                    unique_numbers = set(cargo_numbers_found)
                    
                    if len(cargo_numbers_found) > len(unique_numbers):
                        print("🚨 ОБНАРУЖЕНО ДУБЛИРОВАНИЕ наших грузов в API ответе!")
                        for number in unique_numbers:
                            count = cargo_numbers_found.count(number)
                            if count > 1:
                                print(f"   • {number}: найден {count} раз")
                        print()
                    
                    return found_cargo
                else:
                    self.log_test(
                        "Поиск грузов в API размещения",
                        False,
                        f"Найдено {len(found_cargo)} из {len(created_cargo_numbers)} созданных грузов. Ожидалось минимум: 2"
                    )
                    
                    # Показываем что нашли для диагностики
                    if found_cargo:
                        print("📊 Найденные грузы:")
                        for cargo in found_cargo:
                            print(f"   • {cargo['cargo_number']}: {cargo['cargo_name']}")
                        print()
                    
                    return found_cargo
            else:
                self.log_test("Поиск грузов в API размещения", False, f"HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.log_test("Поиск грузов в API размещения", False, f"Ошибка: {str(e)}")
            return []

    def analyze_duplication(self, found_cargo):
        """Анализ дублирования в API ответе"""
        if not found_cargo:
            return False
            
        try:
            # Получаем полный список для анализа дублирования
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement?per_page=100", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                # Анализируем дубликаты по cargo_number
                cargo_number_counts = defaultdict(int)
                duplicates = []
                
                for item in items:
                    cargo_number = item.get("cargo_number")
                    if cargo_number:
                        cargo_number_counts[cargo_number] += 1
                        if cargo_number_counts[cargo_number] > 1:
                            duplicates.append(cargo_number)
                
                # Проверяем наши созданные грузы на дублирование
                our_cargo_numbers = [cargo["cargo_number"] for cargo in found_cargo]
                our_duplicates = [num for num in our_cargo_numbers if num in duplicates]
                
                if not our_duplicates:
                    self.log_test(
                        "Анализ дублирования",
                        True,
                        f"Дублирование НЕ обнаружено для наших грузов. Всего дубликатов в системе: {len(set(duplicates))}"
                    )
                    
                    if duplicates:
                        print(f"⚠️  Найдены дубликаты других грузов: {', '.join(set(duplicates)[:5])}{'...' if len(set(duplicates)) > 5 else ''}")
                        print()
                    
                    return True
                else:
                    self.log_test(
                        "Анализ дублирования",
                        False,
                        f"ОБНАРУЖЕНО дублирование наших грузов: {', '.join(our_duplicates)}"
                    )
                    
                    # Показываем детали дублирования
                    print("🚨 Детали дублирования:")
                    for duplicate_number in our_duplicates:
                        count = cargo_number_counts[duplicate_number]
                        print(f"   • {duplicate_number}: найдено {count} раз")
                    print()
                    
                    return False
            else:
                self.log_test("Анализ дублирования", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Анализ дублирования", False, f"Ошибка: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        if not self.created_cargo_ids:
            return
            
        try:
            # Переключаемся на админа для удаления
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            deleted_count = 0
            for cargo_id in self.created_cargo_ids:
                try:
                    response = self.session.delete(f"{BACKEND_URL}/admin/cargo/{cargo_id}", timeout=10)
                    if response.status_code == 200:
                        deleted_count += 1
                except:
                    pass  # Игнорируем ошибки удаления
            
            self.log_test(
                "Очистка тестовых данных",
                True,
                f"Удалено {deleted_count} из {len(self.created_cargo_ids)} тестовых грузов"
            )
            
        except Exception as e:
            self.log_test("Очистка тестовых данных", False, f"Ошибка: {str(e)}")

    def run_comprehensive_test(self):
        """Запуск полного теста группировки грузов"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Проверка исправления группировки связанных грузов")
        print("=" * 80)
        print()
        
        # 1. Авторизация
        if not self.authenticate_admin():
            return False
            
        if not self.authenticate_operator():
            return False
        
        # 2. Создание заявки с несколькими грузами
        cargo_data = self.create_cargo_with_multiple_items()
        if not cargo_data:
            return False
        
        # 3. Проверка правильности нумерации
        if not self.verify_cargo_numbering(cargo_data):
            return False
        
        # 4. Проверка API размещения
        found_cargo = self.check_available_for_placement(cargo_data)
        if not found_cargo:
            return False
        
        # 5. Анализ дублирования
        if not self.analyze_duplication(found_cargo):
            return False
        
        # 6. Очистка тестовых данных
        self.cleanup_test_data()
        
        # Итоговая статистика
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("=" * 80)
        print(f"📊 ИТОГОВАЯ СТАТИСТИКА ТЕСТИРОВАНИЯ:")
        print(f"   Всего тестов: {total_tests}")
        print(f"   Пройдено: {passed_tests}")
        print(f"   Провалено: {total_tests - passed_tests}")
        print(f"   Успешность: {success_rate:.1f}%")
        print()
        
        if success_rate == 100:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("✅ ПРОБЛЕМА С ДУБЛИРОВАНИЕМ ИСПРАВЛЕНА НА УРОВНЕ ДАННЫХ")
        else:
            print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В ГРУППИРОВКЕ ГРУЗОВ")
            print("⚠️  ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНОЕ ИССЛЕДОВАНИЕ")
        
        print("=" * 80)
        return success_rate == 100

if __name__ == "__main__":
    tester = CargoGroupingTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1)