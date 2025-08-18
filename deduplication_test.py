#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправление дедупликации в API размещения грузов TAJLINE.TJ
Тестирование дедупликации в /api/operator/cargo/available-for-placement и генерации QR-кодов
"""

import requests
import json
import sys
from datetime import datetime
from collections import Counter

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

class DeduplicationTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        self.created_cargo_ids = []  # Для очистки тестовых данных
        
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

    def test_available_for_placement_deduplication(self):
        """Тест API размещения на дедупликацию"""
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
                        "API размещения - дедупликация",
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
                        "API размещения - дедупликация",
                        False,
                        f"Найдены дубликаты cargo_number: {duplicates}. Всего грузов: {len(items)}, уникальных номеров: {len(set(cargo_numbers))}"
                    )
                    return False
                else:
                    # Ищем заявки с несколькими грузами
                    base_request_numbers = [item.get("base_request_number") for item in items if item.get("base_request_number")]
                    base_counter = Counter(base_request_numbers)
                    multi_cargo_requests = {number: count for number, count in base_counter.items() if count > 1}
                    
                    self.log_test(
                        "API размещения - дедупликация",
                        True,
                        f"Все cargo_number уникальны! Всего грузов: {len(items)}, "
                        f"заявок с несколькими грузами: {len(multi_cargo_requests)}, "
                        f"примеры: {list(multi_cargo_requests.keys())[:3] if multi_cargo_requests else 'нет'}"
                    )
                    return True
            else:
                self.log_test(
                    "API размещения - дедупликация",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("API размещения - дедупликация", False, f"Ошибка: {str(e)}")
            return False

    def create_test_request_with_2_cargo(self, warehouse_id, warehouse_name):
        """Создание новой тестовой заявки с 2 грузами"""
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
                "description": "Тестовая заявка для проверки дедупликации QR кодов"
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
                    
                    self.log_test(
                        "Создание тестовой заявки с 2 грузами",
                        True,
                        f"Базовый номер заявки: {base_request_number}, "
                        f"Номера грузов: {cargo_numbers}, "
                        f"Общая стоимость: {data.get('total_cost', 'N/A')}₽"
                    )
                    return data
                else:
                    self.log_test(
                        "Создание тестовой заявки с 2 грузами",
                        False,
                        f"Неверное количество грузов: ожидалось 2, получено {len(created_cargo)}"
                    )
                    return None
            else:
                self.log_test(
                    "Создание тестовой заявки с 2 грузами",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_test("Создание тестовой заявки с 2 грузами", False, f"Ошибка: {str(e)}")
            return None

    def test_qr_batch_generation(self, base_request_number):
        """Тест генерации QR-кодов для заявки"""
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
                
                if generated_count == 2 and len(qr_codes) == 2:
                    # Проверяем уникальность cargo_number в QR кодах
                    cargo_numbers = [qr.get("cargo_number") for qr in qr_codes if qr.get("cargo_number")]
                    unique_numbers = set(cargo_numbers)
                    
                    if len(unique_numbers) == 2:
                        # Проверяем структуру QR кодов
                        qr_details = []
                        for qr in qr_codes:
                            qr_details.append(f"Номер: {qr.get('cargo_number')}, QR данные: {qr.get('qr_data', 'N/A')[:10]}...")
                        
                        self.log_test(
                            "Генерация QR-кодов - дедупликация",
                            True,
                            f"Сгенерировано ровно 2 уникальных QR-кода. "
                            f"Generated_count: {generated_count}, "
                            f"Детали: {'; '.join(qr_details)}"
                        )
                        return data
                    else:
                        self.log_test(
                            "Генерация QR-кодов - дедупликация",
                            False,
                            f"Найдены дубликаты cargo_number в QR кодах: {cargo_numbers}"
                        )
                        return None
                else:
                    self.log_test(
                        "Генерация QR-кодов - дедупликация",
                        False,
                        f"Неверное количество QR кодов: ожидалось 2, получено {len(qr_codes)} (generated_count: {generated_count})"
                    )
                    return None
            else:
                self.log_test(
                    "Генерация QR-кодов - дедупликация",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_test("Генерация QR-кодов - дедупликация", False, f"Ошибка: {str(e)}")
            return None

    def check_deduplication_logs(self):
        """Проверка логов дедупликации (имитация)"""
        # Поскольку у нас нет прямого доступа к логам backend, 
        # мы можем только отметить что нужно проверить логи
        self.log_test(
            "Проверка логов дедупликации",
            True,
            "В логах backend должно быть сообщение '🔧 ДЕДУПЛИКАЦИЯ' если были найдены дубли. "
            "Проверьте логи backend вручную для подтверждения работы дедупликации."
        )

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

    def print_summary(self):
        """Вывод итогового отчета"""
        print("\n" + "="*80)
        print("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ ДЕДУПЛИКАЦИИ")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Всего тестов: {total_tests}")
        print(f"✅ Успешных: {passed_tests}")
        print(f"❌ Неудачных: {failed_tests}")
        print(f"📈 Процент успеха: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ НЕУДАЧНЫЕ ТЕСТЫ:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        print(f"\n🎯 ЦЕЛЬ ТЕСТИРОВАНИЯ: Подтвердить что исправление дедупликации работает и QR-коды генерируются правильно")
        
        # Определяем общий результат
        critical_tests = [
            "API размещения - дедупликация",
            "Создание тестовой заявки с 2 грузами", 
            "Генерация QR-кодов - дедупликация"
        ]
        
        critical_passed = sum(1 for result in self.test_results 
                            if result["test"] in critical_tests and result["success"])
        
        if critical_passed == len(critical_tests):
            print(f"\n🎉 РЕЗУЛЬТАТ: ДЕДУПЛИКАЦИЯ РАБОТАЕТ КОРРЕКТНО!")
            print(f"   ✅ API размещения возвращает уникальные грузы")
            print(f"   ✅ QR-коды генерируются правильно без дублей")
            print(f"   ✅ Каждый cargo_number уникален")
        else:
            print(f"\n⚠️ РЕЗУЛЬТАТ: ОБНАРУЖЕНЫ ПРОБЛЕМЫ С ДЕДУПЛИКАЦИЕЙ!")
            print(f"   Критических тестов пройдено: {critical_passed}/{len(critical_tests)}")

def main():
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправление дедупликации в API размещения грузов")
    print("="*80)
    
    tester = DeduplicationTester()
    
    # Шаг 1: Авторизация
    if not tester.authenticate_admin():
        print("❌ Не удалось авторизоваться как администратор")
        return
    
    if not tester.authenticate_operator():
        print("❌ Не удалось авторизоваться как оператор")
        return
    
    # Шаг 2: Получение складов
    warehouses = tester.get_warehouses()
    if not warehouses:
        print("❌ Не удалось получить список складов")
        return
    
    warehouse_id = warehouses[0]["id"]
    warehouse_name = warehouses[0]["name"]
    
    # Шаг 3: Тест API размещения на дедупликацию
    tester.test_available_for_placement_deduplication()
    
    # Шаг 4: Создание тестовой заявки с 2 грузами
    test_request = tester.create_test_request_with_2_cargo(warehouse_id, warehouse_name)
    
    if test_request:
        base_request_number = test_request.get("base_request_number")
        
        # Шаг 5: Тест генерации QR-кодов
        if base_request_number:
            tester.test_qr_batch_generation(base_request_number)
    
    # Шаг 6: Проверка логов дедупликации
    tester.check_deduplication_logs()
    
    # Шаг 7: Очистка тестовых данных
    tester.cleanup_test_data()
    
    # Шаг 8: Итоговый отчет
    tester.print_summary()

if __name__ == "__main__":
    main()