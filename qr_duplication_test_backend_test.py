#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Проблема дублирования QR-кодов в API TAJLINE.TJ
Тестирование API endpoint /api/operator/cargo/generate-qr-batch на дублирование QR-кодов
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

class QRDuplicationTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        self.found_request = None
        self.created_test_data = []
        
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

    def find_test_request_with_250818(self):
        """Поиск тестовой заявки с базовым номером начинающимся на 250818"""
        try:
            # Переключаемся на токен администратора для поиска
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            # Ищем в available-for-placement
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement?page=1&per_page=100",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                # Ищем заявки с базовым номером начинающимся на 250818
                requests_250818 = {}
                for item in items:
                    base_number = item.get("base_request_number", "")
                    if base_number.startswith("250818"):
                        if base_number not in requests_250818:
                            requests_250818[base_number] = []
                        requests_250818[base_number].append(item)
                
                # Ищем заявку с ровно 2 грузами
                for base_number, cargo_list in requests_250818.items():
                    if len(cargo_list) == 2:
                        cargo_numbers = [c.get("cargo_number", "") for c in cargo_list]
                        cargo_ids = [c.get("id", "") for c in cargo_list]
                        
                        self.found_request = {
                            "base_request_number": base_number,
                            "cargo_count": len(cargo_list),
                            "cargo_numbers": cargo_numbers,
                            "cargo_ids": cargo_ids,
                            "cargo_list": cargo_list
                        }
                        
                        self.log_test(
                            "Поиск тестовой заявки с 250818",
                            True,
                            f"Найдена заявка {base_number} с {len(cargo_list)} грузами: {', '.join(cargo_numbers)}"
                        )
                        return True
                
                # Если не найдено заявок с 2 грузами, показываем что есть
                if requests_250818:
                    details = []
                    for base_number, cargo_list in requests_250818.items():
                        details.append(f"{base_number} ({len(cargo_list)} грузов)")
                    
                    self.log_test(
                        "Поиск тестовой заявки с 250818",
                        False,
                        f"Найдены заявки с 250818, но не с 2 грузами: {'; '.join(details)}"
                    )
                else:
                    self.log_test(
                        "Поиск тестовой заявки с 250818",
                        False,
                        f"Не найдено заявок с базовым номером 250818. Всего проверено {len(items)} грузов"
                    )
                
                return False
            else:
                self.log_test(
                    "Поиск тестовой заявки с 250818",
                    False,
                    f"Ошибка получения списка грузов: HTTP {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_test("Поиск тестовой заявки с 250818", False, f"Ошибка: {str(e)}")
            return False

    def create_test_request_with_250818(self):
        """Создание тестовой заявки с базовым номером 250818"""
        try:
            # Переключаемся на токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            # Получаем список складов
            warehouses_response = self.session.get(f"{BACKEND_URL}/warehouses", timeout=10)
            if warehouses_response.status_code != 200:
                self.log_test("Создание тестовой заявки", False, "Не удалось получить список складов")
                return False
            
            warehouses = warehouses_response.json()
            if not warehouses:
                self.log_test("Создание тестовой заявки", False, "Список складов пуст")
                return False
            
            warehouse_id = warehouses[0].get("id")
            
            # Создаем заявку с 2 грузами
            payload = {
                "sender_full_name": "Тестовый Отправитель QR",
                "sender_phone": "+79991234567",
                "sender_address": "Москва, ул. Тестовая 1",
                "recipient_full_name": "Тестовый Получатель QR",
                "recipient_phone": "+992901234567",
                "recipient_address": "Душанбе, ул. Тестовая 1",
                "cargo_items": [
                    {
                        "cargo_name": "Тестовый груз 1 для QR",
                        "weight": 1.0,
                        "price_per_kg": 100.0
                    },
                    {
                        "cargo_name": "Тестовый груз 2 для QR",
                        "weight": 2.0,
                        "price_per_kg": 150.0
                    }
                ],
                "description": "Тестовая заявка для проверки дублирования QR кодов",
                "route": "moscow_to_tajikistan",
                "warehouse_id": warehouse_id,
                "payment_method": "cash",
                "payment_amount": 400.0
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/direct-accept",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                base_request_number = data.get("base_request_number", "")
                created_cargo = data.get("created_cargo", [])
                
                if base_request_number and len(created_cargo) == 2:
                    cargo_numbers = [c.get("cargo_number", "") for c in created_cargo]
                    cargo_ids = [c.get("cargo_id", "") for c in created_cargo]
                    
                    self.found_request = {
                        "base_request_number": base_request_number,
                        "cargo_count": len(created_cargo),
                        "cargo_numbers": cargo_numbers,
                        "cargo_ids": cargo_ids,
                        "cargo_list": created_cargo
                    }
                    
                    # Сохраняем для очистки
                    self.created_test_data.extend(cargo_ids)
                    
                    self.log_test(
                        "Создание тестовой заявки с 2 грузами",
                        True,
                        f"Создана заявка {base_request_number} с 2 грузами: {', '.join(cargo_numbers)}"
                    )
                    return True
                else:
                    self.log_test(
                        "Создание тестовой заявки с 2 грузами",
                        False,
                        f"Неверная структура ответа: base_number={base_request_number}, cargo_count={len(created_cargo)}"
                    )
                    return False
            else:
                self.log_test(
                    "Создание тестовой заявки с 2 грузами",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("Создание тестовой заявки с 2 грузами", False, f"Ошибка: {str(e)}")
            return False

    def test_qr_generation_api(self):
        """Тестирование API генерации QR кодов"""
        if not self.found_request:
            self.log_test("Тестирование API генерации QR", False, "Нет данных заявки для тестирования")
            return None
        
        try:
            # Переключаемся на токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            base_request_number = self.found_request["base_request_number"]
            cargo_ids = self.found_request["cargo_ids"]
            
            payload = {
                "base_request_number": base_request_number,
                "cargo_ids": cargo_ids
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/generate-qr-batch",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Анализируем ответ
                qr_codes = data.get("qr_codes", [])
                generated_count = data.get("generated_count", 0)
                
                self.log_test(
                    "API генерации QR - базовый ответ",
                    True,
                    f"Получено {len(qr_codes)} QR кодов, generated_count: {generated_count}"
                )
                
                # Проверяем количество QR кодов
                expected_count = len(cargo_ids)
                if len(qr_codes) == expected_count:
                    self.log_test(
                        "Проверка количества QR кодов",
                        True,
                        f"Количество QR кодов соответствует ожидаемому: {len(qr_codes)} = {expected_count}"
                    )
                else:
                    self.log_test(
                        "Проверка количества QR кодов",
                        False,
                        f"Неверное количество QR кодов: получено {len(qr_codes)}, ожидалось {expected_count}"
                    )
                
                # Проверяем generated_count
                if generated_count == expected_count:
                    self.log_test(
                        "Проверка поля generated_count",
                        True,
                        f"generated_count корректен: {generated_count}"
                    )
                else:
                    self.log_test(
                        "Проверка поля generated_count",
                        False,
                        f"generated_count неверен: {generated_count}, ожидалось {expected_count}"
                    )
                
                # Анализируем структуру каждого QR кода
                cargo_numbers_in_qr = []
                qr_data_list = []
                
                for i, qr_code in enumerate(qr_codes):
                    cargo_number = qr_code.get("cargo_number", "")
                    qr_data = qr_code.get("qr_data", "")
                    qr_image = qr_code.get("qr_code", "")
                    
                    cargo_numbers_in_qr.append(cargo_number)
                    qr_data_list.append(qr_data)
                    
                    self.log_test(
                        f"Структура QR кода {i+1}",
                        True,
                        f"cargo_number: {cargo_number}, qr_data: {qr_data}, qr_image: {'Присутствует' if qr_image else 'Отсутствует'}"
                    )
                
                # Проверяем дублированные cargo_number
                cargo_number_counts = Counter(cargo_numbers_in_qr)
                duplicated_cargo_numbers = [cn for cn, count in cargo_number_counts.items() if count > 1]
                
                if duplicated_cargo_numbers:
                    self.log_test(
                        "Проверка дублированных cargo_number",
                        False,
                        f"Найдены дублированные cargo_number: {duplicated_cargo_numbers}. Статистика: {dict(cargo_number_counts)}"
                    )
                else:
                    self.log_test(
                        "Проверка дублированных cargo_number",
                        True,
                        f"Дублированных cargo_number не найдено. Все уникальны: {cargo_numbers_in_qr}"
                    )
                
                # Проверяем дублированные qr_data
                qr_data_counts = Counter(qr_data_list)
                duplicated_qr_data = [qd for qd, count in qr_data_counts.items() if count > 1]
                
                if duplicated_qr_data:
                    self.log_test(
                        "Проверка дублированных qr_data",
                        False,
                        f"Найдены дублированные qr_data: {duplicated_qr_data}. Статистика: {dict(qr_data_counts)}"
                    )
                else:
                    self.log_test(
                        "Проверка дублированных qr_data",
                        True,
                        f"Дублированных qr_data не найдено. Все уникальны: {qr_data_list}"
                    )
                
                return data
            else:
                self.log_test(
                    "API генерации QR",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_test("API генерации QR", False, f"Ошибка: {str(e)}")
            return None

    def test_available_for_placement_api(self):
        """Проверка API available-for-placement на дублирование"""
        if not self.found_request:
            self.log_test("Проверка available-for-placement", False, "Нет данных заявки для проверки")
            return
        
        try:
            # Переключаемся на токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement?page=1&per_page=100",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                # Ищем наши грузы
                our_cargo_numbers = self.found_request["cargo_numbers"]
                found_cargo = []
                
                for item in items:
                    cargo_number = item.get("cargo_number", "")
                    if cargo_number in our_cargo_numbers:
                        found_cargo.append(item)
                
                # Анализируем найденные грузы
                cargo_number_counts = Counter([c.get("cargo_number", "") for c in found_cargo])
                
                self.log_test(
                    "Поиск наших грузов в available-for-placement",
                    True,
                    f"Найдено {len(found_cargo)} записей для наших грузов {our_cargo_numbers}"
                )
                
                # Проверяем дублирование
                duplicated_in_placement = [cn for cn, count in cargo_number_counts.items() if count > 1]
                
                if duplicated_in_placement:
                    self.log_test(
                        "Проверка дублирования в available-for-placement",
                        False,
                        f"Найдены дублированные грузы: {duplicated_in_placement}. Статистика: {dict(cargo_number_counts)}"
                    )
                else:
                    self.log_test(
                        "Проверка дублирования в available-for-placement",
                        True,
                        f"Дублирования не найдено. Статистика: {dict(cargo_number_counts)}"
                    )
                
            else:
                self.log_test(
                    "Проверка available-for-placement",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_test("Проверка available-for-placement", False, f"Ошибка: {str(e)}")

    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        if not self.created_test_data:
            self.log_test("Очистка тестовых данных", True, "Нет данных для очистки")
            return
        
        try:
            # Переключаемся на токен администратора
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            cleanup_count = 0
            
            for cargo_id in self.created_test_data:
                try:
                    response = self.session.delete(
                        f"{BACKEND_URL}/admin/cargo/{cargo_id}",
                        timeout=10
                    )
                    
                    if response.status_code in [200, 204]:
                        cleanup_count += 1
                except:
                    pass  # Игнорируем ошибки при очистке
            
            self.log_test(
                "Очистка тестовых данных",
                cleanup_count > 0,
                f"Удалено {cleanup_count} из {len(self.created_test_data)} тестовых грузов"
            )
            
        except Exception as e:
            self.log_test("Очистка тестовых данных", False, f"Ошибка: {str(e)}")

    def run_comprehensive_test(self):
        """Запуск полного тестирования дублирования QR кодов"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Проблема дублирования QR-кодов в API")
        print("=" * 80)
        print()
        
        # 1. Авторизация
        if not self.authenticate_admin():
            print("❌ Не удалось авторизоваться как администратор. Тестирование прервано.")
            return False
            
        if not self.authenticate_operator():
            print("❌ Не удалось авторизоваться как оператор. Тестирование прервано.")
            return False
        
        # 2. Поиск тестовой заявки с 250818
        print("🔍 Поиск тестовой заявки с базовым номером 250818...")
        print("-" * 60)
        found = self.find_test_request_with_250818()
        
        # 3. Если не найдено, создаем тестовую заявку
        if not found:
            print("🔧 Создание тестовой заявки с 2 грузами...")
            print("-" * 60)
            if not self.create_test_request_with_250818():
                print("❌ Не удалось создать тестовую заявку. Тестирование прервано.")
                return False
        
        # 4. Тестирование API генерации QR кодов
        print("🔍 Тестирование API генерации QR кодов...")
        print("-" * 60)
        qr_result = self.test_qr_generation_api()
        
        # 5. Проверка API available-for-placement
        print("🔍 Проверка API available-for-placement на дублирование...")
        print("-" * 60)
        self.test_available_for_placement_api()
        
        # 6. Очистка тестовых данных
        print("🧹 Очистка тестовых данных...")
        print("-" * 60)
        self.cleanup_test_data()
        
        # 7. Подведение итогов
        self.print_summary()
        
        return True

    def print_summary(self):
        """Вывод итогового отчета"""
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ ДУБЛИРОВАНИЯ QR КОДОВ")
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
        
        # Анализ результатов
        qr_duplication_issues = []
        placement_duplication_issues = []
        
        for result in self.test_results:
            test_name = result["test"]
            if not result["success"]:
                if "дублированных" in test_name.lower() or "количества qr" in test_name.lower():
                    qr_duplication_issues.append(result)
                elif "available-for-placement" in test_name.lower():
                    placement_duplication_issues.append(result)
        
        # Выводы по дублированию
        print("🔍 АНАЛИЗ ДУБЛИРОВАНИЯ:")
        print("-" * 40)
        
        if qr_duplication_issues:
            print("❌ ПРОБЛЕМЫ С QR ГЕНЕРАЦИЕЙ:")
            for issue in qr_duplication_issues:
                print(f"   • {issue['test']}: {issue['details']}")
        else:
            print("✅ QR ГЕНЕРАЦИЯ: Дублирования не обнаружено")
        
        if placement_duplication_issues:
            print("❌ ПРОБЛЕМЫ С AVAILABLE-FOR-PLACEMENT:")
            for issue in placement_duplication_issues:
                print(f"   • {issue['test']}: {issue['details']}")
        else:
            print("✅ AVAILABLE-FOR-PLACEMENT: Дублирования не обнаружено")
        
        print("\n" + "=" * 80)
        
        # Критические выводы
        if failed_tests == 0:
            print("🎉 КРИТИЧЕСКИЙ ВЫВОД: ДУБЛИРОВАНИЯ QR КОДОВ НЕ ОБНАРУЖЕНО!")
            print("API генерации QR кодов работает корректно, каждый груз получает уникальный QR код.")
        elif qr_duplication_issues:
            print("🚨 КРИТИЧЕСКИЙ ВЫВОД: ОБНАРУЖЕНО ДУБЛИРОВАНИЕ QR КОДОВ!")
            print("API /api/operator/cargo/generate-qr-batch возвращает дублированные QR коды.")
            print("РЕКОМЕНДАЦИЯ: Исправить логику генерации QR кодов в backend.")
        elif placement_duplication_issues:
            print("⚠️ КРИТИЧЕСКИЙ ВЫВОД: ДУБЛИРОВАНИЕ В AVAILABLE-FOR-PLACEMENT!")
            print("Проблема не в генерации QR, а в API available-for-placement.")
        else:
            print("⚠️ КРИТИЧЕСКИЙ ВЫВОД: ОБНАРУЖЕНЫ МИНОРНЫЕ ПРОБЛЕМЫ!")
            print("Основная функциональность работает, но есть технические проблемы.")
        
        print("=" * 80)

def main():
    """Главная функция"""
    tester = QRDuplicationTester()
    
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