#!/usr/bin/env python3
"""
🎯 ПОЛНОЕ ТЕСТИРОВАНИЕ: Исправление дедупликации согласно review request
Проверка всех аспектов дедупликации в API размещения грузов и генерации QR-кодов
"""

import requests
import json
import sys
from datetime import datetime
from collections import Counter

# Конфигурация
BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"

# Тестовые данные для авторизации
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

class ComprehensiveDeduplicationTester:
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
        """Получение списка складов"""
        try:
            # Используем токен администратора
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            response = self.session.get(f"{BACKEND_URL}/warehouses", timeout=10)
            
            if response.status_code == 200:
                warehouses = response.json()
                if warehouses:
                    warehouse_info = []
                    for w in warehouses:
                        warehouse_info.append(f"{w.get('name', 'N/A')} (ID: {w.get('id', 'N/A')})")
                    
                    self.log_test(
                        "Получение списка складов",
                        True,
                        f"Найдено {len(warehouses)} складов. Список: {'; '.join(warehouse_info)}"
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

    def test_available_for_placement_uniqueness(self):
        """1. Тест API размещения на уникальность грузов без дублирования"""
        try:
            # Используем токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    self.log_test(
                        "1. API размещения возвращает уникальные грузы",
                        True,
                        "Список грузов для размещения пуст - дедупликация не требуется"
                    )
                    return True
                
                # Проверяем уникальность cargo_number
                cargo_numbers = [item.get("cargo_number") for item in items if item.get("cargo_number")]
                cargo_counter = Counter(cargo_numbers)
                duplicates = {number: count for number, count in cargo_counter.items() if count > 1}
                
                if duplicates:
                    self.log_test(
                        "1. API размещения возвращает уникальные грузы",
                        False,
                        f"❌ НАЙДЕНЫ ДУБЛИКАТЫ cargo_number: {duplicates}. Всего грузов: {len(items)}, уникальных номеров: {len(set(cargo_numbers))}"
                    )
                    return False
                else:
                    self.log_test(
                        "1. API размещения возвращает уникальные грузы",
                        True,
                        f"✅ Все cargo_number уникальны! Всего грузов: {len(items)}, все номера уникальны"
                    )
                    return True
            else:
                self.log_test(
                    "1. API размещения возвращает уникальные грузы",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("1. API размещения возвращает уникальные грузы", False, f"Ошибка: {str(e)}")
            return False

    def find_multi_cargo_requests(self):
        """2. Найти заявки с несколькими грузами"""
        try:
            # Используем токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    self.log_test(
                        "2. Поиск заявок с несколькими грузами",
                        True,
                        "Список грузов пуст - заявки с несколькими грузами не найдены"
                    )
                    return []
                
                # Группируем по base_request_number
                base_request_numbers = [item.get("base_request_number") for item in items if item.get("base_request_number")]
                base_counter = Counter(base_request_numbers)
                multi_cargo_requests = {number: count for number, count in base_counter.items() if count > 1}
                
                self.log_test(
                    "2. Поиск заявок с несколькими грузами",
                    True,
                    f"Найдено {len(multi_cargo_requests)} заявок с несколькими грузами. "
                    f"Примеры: {list(multi_cargo_requests.items())[:3] if multi_cargo_requests else 'нет'}"
                )
                return list(multi_cargo_requests.keys())
            else:
                self.log_test(
                    "2. Поиск заявок с несколькими грузами",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return []
                
        except Exception as e:
            self.log_test("2. Поиск заявок с несколькими грузами", False, f"Ошибка: {str(e)}")
            return []

    def verify_cargo_number_uniqueness(self):
        """3. Убедиться что каждый cargo_number встречается только один раз"""
        try:
            # Используем токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    self.log_test(
                        "3. Каждый cargo_number встречается только один раз",
                        True,
                        "Список грузов пуст - проверка уникальности не требуется"
                    )
                    return True
                
                # Проверяем уникальность cargo_number
                cargo_numbers = [item.get("cargo_number") for item in items if item.get("cargo_number")]
                unique_numbers = set(cargo_numbers)
                
                if len(cargo_numbers) == len(unique_numbers):
                    self.log_test(
                        "3. Каждый cargo_number встречается только один раз",
                        True,
                        f"✅ ПОДТВЕРЖДЕНО: Все {len(cargo_numbers)} cargo_number уникальны, дублей нет"
                    )
                    return True
                else:
                    duplicates = [num for num in cargo_numbers if cargo_numbers.count(num) > 1]
                    self.log_test(
                        "3. Каждый cargo_number встречается только один раз",
                        False,
                        f"❌ НАЙДЕНЫ ДУБЛИКАТЫ: {len(cargo_numbers) - len(unique_numbers)} дублей. Примеры: {list(set(duplicates))[:5]}"
                    )
                    return False
            else:
                self.log_test(
                    "3. Каждый cargo_number встречается только один раз",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("3. Каждый cargo_number встречается только один раз", False, f"Ошибка: {str(e)}")
            return False

    def create_test_request_exact_format(self, warehouse_id, warehouse_name):
        """4. Создать новую тестовую заявку с 2 грузами (точный формат из review request)"""
        try:
            # Используем токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            payload = {
                "sender_full_name": "Тест Дедупликации QR",
                "sender_phone": "+79991122333",
                "sender_address": "Москва, ул. Тестовая QR 1",
                "recipient_full_name": "Получатель QR Теста",
                "recipient_phone": "+992901122333",
                "recipient_address": "Душанбе, ул. Тестовая QR 2",
                "cargo_items": [
                    {
                        "cargo_name": "QR Тест Груз 1",
                        "weight": 1.0,
                        "price_per_kg": 200.0
                    },
                    {
                        "cargo_name": "QR Тест Груз 2",
                        "weight": 1.5,
                        "price_per_kg": 250.0
                    }
                ],
                "destination_warehouse_id": warehouse_id,
                "destination_warehouse_name": warehouse_name,
                "route": "moscow_to_tajikistan",
                "payment_method": "cash",
                "payment_amount": 575.0,
                "description": "Тестовая заявка для проверки дедупликации QR кодов - точный формат"
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/direct-accept",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа
                created_cargo = data.get("created_cargo", [])
                base_request_number = data.get("base_request_number")
                
                if len(created_cargo) == 2 and base_request_number:
                    # Сохраняем ID для очистки
                    for cargo in created_cargo:
                        if cargo.get("cargo_id"):
                            self.created_cargo_ids.append(cargo["cargo_id"])
                    
                    cargo_numbers = [cargo.get("cargo_number") for cargo in created_cargo]
                    total_weight = sum(cargo.get("weight", 0) for cargo in created_cargo)
                    
                    self.log_test(
                        "4. Создание тестовой заявки (точный формат)",
                        True,
                        f"✅ Заявка создана: базовый номер {base_request_number}, "
                        f"номера грузов: {cargo_numbers}, общий вес: {total_weight}кг, "
                        f"общая стоимость: 575₽"
                    )
                    return data
                else:
                    self.log_test(
                        "4. Создание тестовой заявки (точный формат)",
                        False,
                        f"❌ Неверная структура: ожидалось 2 груза, получено {len(created_cargo)}"
                    )
                    return None
            else:
                self.log_test(
                    "4. Создание тестовой заявки (точный формат)",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_test("4. Создание тестовой заявки (точный формат)", False, f"Ошибка: {str(e)}")
            return None

    def test_qr_batch_generation_exact(self, base_request_number):
        """5. Тест генерации QR-кодов - ровно 2 QR-кода с уникальными cargo_number"""
        try:
            # Используем токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            payload = {
                "base_request_number": base_request_number
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/generate-qr-batch",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                qr_codes = data.get("qr_codes", [])
                generated_count = data.get("generated_count", 0)
                
                # Проверяем точное количество
                if generated_count != 2:
                    self.log_test(
                        "5. Генерация QR-кодов - ровно 2 QR-кода",
                        False,
                        f"❌ Неверное количество: ожидалось 2, получено {generated_count}"
                    )
                    return None
                
                if len(qr_codes) != 2:
                    self.log_test(
                        "5. Генерация QR-кодов - ровно 2 QR-кода",
                        False,
                        f"❌ Неверное количество в массиве: ожидалось 2, получено {len(qr_codes)}"
                    )
                    return None
                
                # Проверяем уникальность cargo_number в QR кодах
                cargo_numbers = [qr.get("cargo_number") for qr in qr_codes if qr.get("cargo_number")]
                unique_numbers = set(cargo_numbers)
                
                if len(unique_numbers) != 2:
                    self.log_test(
                        "5. Генерация QR-кодов - уникальные cargo_number",
                        False,
                        f"❌ Найдены дубликаты cargo_number: {cargo_numbers}"
                    )
                    return None
                
                # Проверяем структуру QR кодов
                qr_details = []
                for qr in qr_codes:
                    qr_details.append({
                        "cargo_number": qr.get("cargo_number"),
                        "qr_data": qr.get("qr_data"),
                        "has_qr_code": bool(qr.get("qr_code"))
                    })
                
                self.log_test(
                    "5. Генерация QR-кодов - ровно 2 уникальных QR-кода",
                    True,
                    f"✅ УСПЕХ: Сгенерировано ровно 2 уникальных QR-кода. "
                    f"Generated_count: {generated_count}, "
                    f"Cargo_numbers: {cargo_numbers}, "
                    f"QR_data: {[qr.get('qr_data') for qr in qr_codes]}"
                )
                return data
            else:
                self.log_test(
                    "5. Генерация QR-кодов - ровно 2 уникальных QR-кода",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_test("5. Генерация QR-кодов - ровно 2 уникальных QR-кода", False, f"Ошибка: {str(e)}")
            return None

    def verify_unique_cargo_numbers_in_system(self):
        """6. Проверка дедупликации - убедиться что каждый груз имеет уникальный cargo_number"""
        try:
            # Используем токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if not items:
                    self.log_test(
                        "6. Каждый груз имеет уникальный cargo_number",
                        True,
                        "Список грузов пуст - проверка уникальности не требуется"
                    )
                    return True
                
                # Детальная проверка уникальности
                cargo_numbers = []
                cargo_details = []
                
                for item in items:
                    cargo_number = item.get("cargo_number")
                    if cargo_number:
                        cargo_numbers.append(cargo_number)
                        cargo_details.append({
                            "cargo_number": cargo_number,
                            "base_request_number": item.get("base_request_number"),
                            "cargo_name": item.get("cargo_name", "N/A")
                        })
                
                # Проверяем дубликаты
                cargo_counter = Counter(cargo_numbers)
                duplicates = {number: count for number, count in cargo_counter.items() if count > 1}
                
                if duplicates:
                    # Показываем детали дубликатов
                    duplicate_details = []
                    for dup_number in duplicates.keys():
                        dup_items = [d for d in cargo_details if d["cargo_number"] == dup_number]
                        duplicate_details.append(f"{dup_number}: {len(dup_items)} раз")
                    
                    self.log_test(
                        "6. Каждый груз имеет уникальный cargo_number",
                        False,
                        f"❌ НАЙДЕНЫ ДУБЛИКАТЫ: {len(duplicates)} номеров дублируются. "
                        f"Детали: {'; '.join(duplicate_details[:3])}"
                    )
                    return False
                else:
                    self.log_test(
                        "6. Каждый груз имеет уникальный cargo_number",
                        True,
                        f"✅ ПОДТВЕРЖДЕНО: Все {len(cargo_numbers)} cargo_number в системе уникальны"
                    )
                    return True
            else:
                self.log_test(
                    "6. Каждый груз имеет уникальный cargo_number",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("6. Каждый груз имеет уникальный cargo_number", False, f"Ошибка: {str(e)}")
            return False

    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        if not self.created_cargo_ids:
            self.log_test("Очистка тестовых данных", True, "Нет данных для очистки")
            return
        
        try:
            # Используем токен администратора для удаления
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            deleted_count = 0
            for cargo_id in self.created_cargo_ids:
                try:
                    response = self.session.delete(
                        f"{BACKEND_URL}/admin/cargo/{cargo_id}",
                        timeout=10
                    )
                    if response.status_code in [200, 204]:
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

    def print_final_summary(self):
        """Итоговый отчет согласно review request"""
        print("\n" + "="*100)
        print("🎯 ФИНАЛЬНЫЙ ОТЧЕТ: ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ ДЕДУПЛИКАЦИИ В API РАЗМЕЩЕНИЯ ГРУЗОВ")
        print("="*100)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 СТАТИСТИКА ТЕСТИРОВАНИЯ:")
        print(f"   • Всего тестов: {total_tests}")
        print(f"   • ✅ Успешных: {passed_tests}")
        print(f"   • ❌ Неудачных: {failed_tests}")
        print(f"   • 📈 Процент успеха: {(passed_tests/total_tests*100):.1f}%")
        
        print(f"\n🎯 ПРОВЕРЕННЫЕ АСПЕКТЫ СОГЛАСНО REVIEW REQUEST:")
        
        # Проверяем каждый аспект из review request
        aspects = [
            ("1. API размещения возвращает уникальные грузы", "1. API размещения возвращает уникальные грузы"),
            ("2. Найдены заявки с несколькими грузами", "2. Поиск заявок с несколькими грузами"),
            ("3. Каждый cargo_number встречается только один раз", "3. Каждый cargo_number встречается только один раз"),
            ("4. Создана тестовая заявка с 2 грузами", "4. Создание тестовой заявки (точный формат)"),
            ("5. Генерация QR-кодов работает правильно", "5. Генерация QR-кодов - ровно 2 уникальных QR-кода"),
            ("6. Каждый груз имеет уникальный cargo_number", "6. Каждый груз имеет уникальный cargo_number")
        ]
        
        for aspect_name, test_name in aspects:
            test_result = next((r for r in self.test_results if r["test"] == test_name), None)
            if test_result:
                status = "✅ ПРОЙДЕН" if test_result["success"] else "❌ ПРОВАЛЕН"
                print(f"   {status}: {aspect_name}")
            else:
                print(f"   ⚠️ НЕ ТЕСТИРОВАЛСЯ: {aspect_name}")
        
        if failed_tests > 0:
            print(f"\n❌ ПРОБЛЕМЫ ОБНАРУЖЕНЫ:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        # Определяем общий результат
        critical_tests = [
            "1. API размещения возвращает уникальные грузы",
            "3. Каждый cargo_number встречается только один раз", 
            "5. Генерация QR-кодов - ровно 2 уникальных QR-кода",
            "6. Каждый груз имеет уникальный cargo_number"
        ]
        
        critical_passed = sum(1 for result in self.test_results 
                            if result["test"] in critical_tests and result["success"])
        
        print(f"\n🏆 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        if critical_passed == len(critical_tests):
            print(f"   🎉 ИСПРАВЛЕНИЕ ДЕДУПЛИКАЦИИ РАБОТАЕТ КОРРЕКТНО!")
            print(f"   ✅ API /api/operator/cargo/available-for-placement возвращает уникальные грузы без дублирования")
            print(f"   ✅ Заявки с несколькими грузами обрабатываются правильно")
            print(f"   ✅ Каждый cargo_number встречается только один раз")
            print(f"   ✅ QR-коды генерируются правильно - ровно 2 QR-кода для заявки с 2 грузами")
            print(f"   ✅ Cargo_numbers уникальны в QR-кодах")
            print(f"   ✅ Дедупликация работает и QR-коды теперь генерируются правильно")
        else:
            print(f"   ⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ С ДЕДУПЛИКАЦИЕЙ!")
            print(f"   Критических тестов пройдено: {critical_passed}/{len(critical_tests)}")
            print(f"   Требуется дополнительная работа над исправлением дедупликации")
        
        print(f"\n📝 ЗАКЛЮЧЕНИЕ:")
        print(f"   Цель тестирования: подтвердить что исправление дедупликации работает и QR-коды генерируются правильно")
        if critical_passed == len(critical_tests):
            print(f"   ✅ ЦЕЛЬ ДОСТИГНУТА: Дедупликация работает корректно!")
        else:
            print(f"   ❌ ЦЕЛЬ НЕ ДОСТИГНУТА: Требуются дополнительные исправления")

def main():
    print("🎯 ПОЛНОЕ ТЕСТИРОВАНИЕ: Исправление дедупликации в API размещения грузов TAJLINE.TJ")
    print("Согласно review request - проверка всех аспектов дедупликации")
    print("="*100)
    
    tester = ComprehensiveDeduplicationTester()
    
    # Авторизация
    if not tester.authenticate_admin():
        print("❌ Не удалось авторизоваться как администратор")
        return
    
    if not tester.authenticate_operator():
        print("❌ Не удалось авторизоваться как оператор")
        return
    
    # Получение складов
    warehouses = tester.get_warehouses()
    if not warehouses:
        print("❌ Не удалось получить список складов")
        return
    
    warehouse_id = warehouses[0]["id"]
    warehouse_name = warehouses[0]["name"]
    
    # Выполняем все тесты согласно review request
    print(f"\n🔍 ВЫПОЛНЕНИЕ ТЕСТОВ СОГЛАСНО REVIEW REQUEST:")
    
    # 1. Тест API размещения на уникальность
    tester.test_available_for_placement_uniqueness()
    
    # 2. Поиск заявок с несколькими грузами
    multi_cargo_requests = tester.find_multi_cargo_requests()
    
    # 3. Проверка уникальности cargo_number
    tester.verify_cargo_number_uniqueness()
    
    # 4. Создание тестовой заявки с 2 грузами (точный формат)
    test_request = tester.create_test_request_exact_format(warehouse_id, warehouse_name)
    
    if test_request:
        base_request_number = test_request.get("base_request_number")
        
        # 5. Тест генерации QR-кодов
        if base_request_number:
            tester.test_qr_batch_generation_exact(base_request_number)
    
    # 6. Финальная проверка уникальности в системе
    tester.verify_unique_cargo_numbers_in_system()
    
    # Очистка тестовых данных
    tester.cleanup_test_data()
    
    # Итоговый отчет
    tester.print_final_summary()

if __name__ == "__main__":
    main()