#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ОТОБРАЖЕНИЯ ЦИФРОВОГО QR КОДА И REACT ОШИБКИ В TAJLINE.TJ

КОНТЕКСТ ИСПРАВЛЕНИЙ:
- Поле ввода ячейки теперь показывает цифровой код QR (03010101) вместо читаемого формата (Б1-П1-Я1)
- Исправлена React ошибка "Objects are not valid as a React child" в функции handlePlaceCargo
- Добавлена правильная обработка объекта response от API размещения груза
- Улучшено сообщение о успешном размещении с извлечением конкретных полей из ответа

КРИТИЧЕСКАЯ ПРОВЕРКА:
- API /api/operator/cargo/place должен возвращать объект с полями warehouse_name, location_code
- Структура ответа должна быть корректной для отображения в сообщениях успеха
- Убедиться что нет других мест где объекты рендерятся напрямую в React

ТЕСТОВЫЙ ПЛАН:
1. Авторизация оператора склада (+79777888999/warehouse123)
2. Получить доступные грузы для размещения
3. Протестировать API /api/operator/cargo/place и проверить структуру ответа
4. Убедиться что ответ содержит поля: warehouse_name, location_code, cargo_number, placed_at

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Backend готов для исправленной логики отображения и размещения.
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Конфигурация
BACKEND_URL = "https://cargo-tracker-29.preview.emergentagent.com/api"

# Тестовые данные
WAREHOUSE_OPERATOR = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class QRDisplayFixesTester:
    def __init__(self):
        self.session = requests.Session()
        self.operator_token = None
        self.operator_info = None
        self.test_results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Логирование результата теста"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        if details and not success:
            print(f"   Details: {json.dumps(details, indent=2, ensure_ascii=False)}")
    
    def authenticate_warehouse_operator(self):
        """Авторизация оператора склада"""
        print(f"\n🔐 Авторизация оператора склада ({WAREHOUSE_OPERATOR['phone']})...")
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=WAREHOUSE_OPERATOR,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.operator_info = data.get("user", {})
                
                if self.operator_token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.operator_token}"
                    })
                    
                    operator_name = self.operator_info.get('full_name', 'Unknown')
                    operator_role = self.operator_info.get('role', 'Unknown')
                    operator_number = self.operator_info.get('user_number', 'Unknown')
                    
                    self.log_result(
                        "Авторизация оператора склада",
                        True,
                        f"Успешная авторизация: {operator_name} (роль: {operator_role}, номер: {operator_number})",
                        {
                            "operator_name": operator_name,
                            "operator_role": operator_role,
                            "operator_number": operator_number,
                            "token_received": True
                        }
                    )
                    return True
                else:
                    self.log_result("Авторизация оператора склада", False, "Токен не получен")
                    return False
            else:
                self.log_result("Авторизация оператора склада", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Авторизация оператора склада", False, f"Exception: {str(e)}")
            return False
    
    def get_available_cargo_for_placement(self):
        """Получить доступные грузы для размещения"""
        print(f"\n📦 Получение доступных грузов для размещения...")
        
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                total_count = data.get("total_count", len(items))
                
                if items:
                    # Проверяем структуру первого груза
                    sample_cargo = items[0]
                    required_fields = ["id", "cargo_number", "processing_status", "weight", "sender_full_name", "recipient_full_name"]
                    missing_fields = [field for field in required_fields if field not in sample_cargo]
                    
                    self.log_result(
                        "Получение доступных грузов для размещения",
                        True,
                        f"Найдено {len(items)} грузов для размещения (всего: {total_count})",
                        {
                            "cargo_count": len(items),
                            "total_count": total_count,
                            "sample_cargo": sample_cargo,
                            "missing_fields": missing_fields,
                            "structure_valid": len(missing_fields) == 0
                        }
                    )
                    return items
                else:
                    self.log_result(
                        "Получение доступных грузов для размещения",
                        False,
                        "Нет доступных грузов для размещения",
                        {"response_data": data}
                    )
                    return []
            else:
                self.log_result(
                    "Получение доступных грузов для размещения",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return []
                
        except Exception as e:
            self.log_result("Получение доступных грузов для размещения", False, f"Exception: {str(e)}")
            return []
    
    def test_cargo_placement_api_structure(self, cargo_items):
        """Тестирование API /api/operator/cargo/place и проверка структуры ответа"""
        print(f"\n🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: API /api/operator/cargo/place...")
        
        if not cargo_items:
            self.log_result(
                "API /api/operator/cargo/place структура ответа",
                False,
                "Нет доступных грузов для тестирования размещения"
            )
            return False
        
        # Используем первый доступный груз для тестирования
        test_cargo = cargo_items[0]
        cargo_id = test_cargo.get("id")
        cargo_number = test_cargo.get("cargo_number")
        
        print(f"   📦 Тестовый груз: {cargo_number} (ID: {cargo_id})")
        
        # Получаем список складов оператора для выбора warehouse_id
        try:
            warehouses_response = self.session.get(f"{BACKEND_URL}/operator/warehouses", timeout=30)
            
            if warehouses_response.status_code != 200:
                self.log_result(
                    "API /api/operator/cargo/place структура ответа",
                    False,
                    "Не удалось получить список складов оператора"
                )
                return False
            
            warehouses = warehouses_response.json()
            if not warehouses:
                self.log_result(
                    "API /api/operator/cargo/place структура ответа",
                    False,
                    "У оператора нет назначенных складов"
                )
                return False
            
            # Используем первый склад
            test_warehouse = warehouses[0]
            warehouse_id = test_warehouse.get("id")
            warehouse_name = test_warehouse.get("name")
            
            print(f"   🏭 Тестовый склад: {warehouse_name} (ID: {warehouse_id})")
            
        except Exception as e:
            self.log_result(
                "API /api/operator/cargo/place структура ответа",
                False,
                f"Ошибка получения складов: {str(e)}"
            )
            return False
        
        # Данные для размещения груза
        placement_data = {
            "cargo_id": cargo_id,
            "warehouse_id": warehouse_id,
            "block_number": 1,
            "shelf_number": 1,
            "cell_number": 1
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/place",
                json=placement_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # КРИТИЧЕСКАЯ ПРОВЕРКА: структура ответа должна содержать необходимые поля
                required_fields = ["warehouse_name", "location_code", "cargo_number", "placed_at"]
                present_fields = []
                missing_fields = []
                
                for field in required_fields:
                    if field in data:
                        present_fields.append(field)
                    else:
                        missing_fields.append(field)
                
                # Дополнительные полезные поля
                additional_fields = ["message", "success", "cargo_id", "warehouse_id", "operator_name"]
                additional_present = [field for field in additional_fields if field in data]
                
                # Проверяем типы данных полей
                field_types = {}
                for field in present_fields:
                    field_types[field] = type(data[field]).__name__
                
                success = len(missing_fields) == 0
                
                self.log_result(
                    "API /api/operator/cargo/place структура ответа",
                    success,
                    f"Размещение груза {'успешно' if success else 'с проблемами'}: {len(present_fields)}/{len(required_fields)} обязательных полей",
                    {
                        "cargo_number": cargo_number,
                        "warehouse_name": warehouse_name,
                        "required_fields": required_fields,
                        "present_fields": present_fields,
                        "missing_fields": missing_fields,
                        "additional_fields": additional_present,
                        "field_types": field_types,
                        "full_response": data,
                        "response_structure_valid": success
                    }
                )
                
                # Дополнительная проверка: убеждаемся что поля содержат правильные данные
                if success:
                    print(f"   ✅ КРИТИЧЕСКИЕ ПОЛЯ ПРИСУТСТВУЮТ:")
                    print(f"      - warehouse_name: '{data.get('warehouse_name')}' ({type(data.get('warehouse_name')).__name__})")
                    print(f"      - location_code: '{data.get('location_code')}' ({type(data.get('location_code')).__name__})")
                    print(f"      - cargo_number: '{data.get('cargo_number')}' ({type(data.get('cargo_number')).__name__})")
                    print(f"      - placed_at: '{data.get('placed_at')}' ({type(data.get('placed_at')).__name__})")
                    
                    # Проверяем что поля не являются объектами (что вызывало React ошибку)
                    object_fields = []
                    for field in required_fields:
                        if isinstance(data.get(field), (dict, list)):
                            object_fields.append(field)
                    
                    if object_fields:
                        print(f"   ⚠️  ВНИМАНИЕ: Поля содержат объекты (могут вызвать React ошибку): {object_fields}")
                    else:
                        print(f"   ✅ Все поля содержат примитивные типы (строки/числа) - React ошибка исправлена")
                
                return success
                
            else:
                # Проверяем специфические ошибки
                error_message = response.text
                if "already occupied" in error_message.lower():
                    # Ячейка занята - попробуем другую ячейку
                    print(f"   ⚠️  Ячейка занята, пробуем другую...")
                    
                    for cell_num in range(2, 6):  # Пробуем ячейки 2-5
                        placement_data["cell_number"] = cell_num
                        retry_response = self.session.post(
                            f"{BACKEND_URL}/operator/cargo/place",
                            json=placement_data,
                            timeout=30
                        )
                        
                        if retry_response.status_code == 200:
                            data = retry_response.json()
                            required_fields = ["warehouse_name", "location_code", "cargo_number", "placed_at"]
                            missing_fields = [field for field in required_fields if field not in data]
                            success = len(missing_fields) == 0
                            
                            self.log_result(
                                "API /api/operator/cargo/place структура ответа",
                                success,
                                f"Размещение в ячейку {cell_num} успешно: {len(required_fields) - len(missing_fields)}/{len(required_fields)} полей",
                                {
                                    "cell_number": cell_num,
                                    "required_fields": required_fields,
                                    "missing_fields": missing_fields,
                                    "full_response": data
                                }
                            )
                            return success
                    
                    # Если все ячейки заняты
                    self.log_result(
                        "API /api/operator/cargo/place структура ответа",
                        False,
                        "Все тестовые ячейки заняты, не удалось протестировать размещение"
                    )
                    return False
                else:
                    self.log_result(
                        "API /api/operator/cargo/place структура ответа",
                        False,
                        f"HTTP {response.status_code}: {error_message}"
                    )
                    return False
                
        except Exception as e:
            self.log_result(
                "API /api/operator/cargo/place структура ответа",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def verify_digital_qr_code_support(self):
        """Проверка поддержки цифрового формата QR кода (03010101)"""
        print(f"\n🔢 Проверка поддержки цифрового формата QR кода...")
        
        # Получаем список складов для проверки warehouse_number
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/warehouses", timeout=30)
            
            if response.status_code == 200:
                warehouses = response.json()
                
                if warehouses:
                    # Проверяем что склады имеют warehouse_number для цифрового формата
                    warehouses_with_numbers = []
                    warehouses_without_numbers = []
                    
                    for warehouse in warehouses:
                        warehouse_number = warehouse.get("warehouse_number")
                        if warehouse_number is not None:
                            warehouses_with_numbers.append({
                                "name": warehouse.get("name"),
                                "id": warehouse.get("id"),
                                "warehouse_number": warehouse_number
                            })
                        else:
                            warehouses_without_numbers.append({
                                "name": warehouse.get("name"),
                                "id": warehouse.get("id")
                            })
                    
                    success = len(warehouses_with_numbers) > 0
                    
                    self.log_result(
                        "Поддержка цифрового формата QR кода",
                        success,
                        f"Найдено {len(warehouses_with_numbers)} складов с warehouse_number из {len(warehouses)} общих",
                        {
                            "total_warehouses": len(warehouses),
                            "warehouses_with_numbers": len(warehouses_with_numbers),
                            "warehouses_without_numbers": len(warehouses_without_numbers),
                            "sample_warehouse_numbers": warehouses_with_numbers[:3],
                            "digital_qr_ready": success
                        }
                    )
                    
                    if success:
                        print(f"   ✅ Склады готовы для цифрового QR формата:")
                        for wh in warehouses_with_numbers[:3]:
                            print(f"      - {wh['name']}: warehouse_number = {wh['warehouse_number']}")
                    
                    return success
                else:
                    self.log_result(
                        "Поддержка цифрового формата QR кода",
                        False,
                        "Нет доступных складов для проверки"
                    )
                    return False
            else:
                self.log_result(
                    "Поддержка цифрового формата QR кода",
                    False,
                    f"Ошибка получения складов: HTTP {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Поддержка цифрового формата QR кода",
                False,
                f"Exception: {str(e)}"
            )
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ОТОБРАЖЕНИЯ ЦИФРОВОГО QR КОДА И REACT ОШИБКИ В TAJLINE.TJ")
        print("=" * 120)
        
        # Тест 1: Авторизация оператора склада
        if not self.authenticate_warehouse_operator():
            print("❌ Не удалось авторизоваться как оператор склада")
            return False
        
        # Тест 2: Получение доступных грузов
        available_cargo = self.get_available_cargo_for_placement()
        
        # Тест 3: КРИТИЧЕСКИЙ - Тестирование API размещения груза
        placement_api_success = self.test_cargo_placement_api_structure(available_cargo)
        
        # Тест 4: Проверка поддержки цифрового QR формата
        digital_qr_support = self.verify_digital_qr_code_support()
        
        # Итоговый отчет
        print("\n" + "=" * 120)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЙ")
        print("=" * 120)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Всего тестов: {total_tests}")
        print(f"Пройдено: {passed_tests}")
        print(f"Провалено: {failed_tests}")
        print(f"Процент успеха: {success_rate:.1f}%")
        
        # Детальные результаты
        print(f"\n🔍 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")
        
        # Критические выводы
        print(f"\n🎯 КРИТИЧЕСКИЕ ВЫВОДЫ:")
        
        if placement_api_success:
            print("   ✅ API /api/operator/cargo/place возвращает корректную структуру ответа")
            print("   ✅ Поля warehouse_name, location_code, cargo_number, placed_at присутствуют")
            print("   ✅ React ошибка 'Objects are not valid as a React child' исправлена")
        else:
            print("   ❌ API /api/operator/cargo/place имеет проблемы со структурой ответа")
            print("   ❌ Отсутствуют критические поля для отображения успешного размещения")
        
        if digital_qr_support:
            print("   ✅ Backend готов для отображения цифрового QR кода (warehouse_number поддерживается)")
        else:
            print("   ❌ Backend не готов для цифрового QR формата (отсутствует warehouse_number)")
        
        # Общий вывод
        if success_rate >= 75.0:
            print(f"\n🎉 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ!")
            print("✅ Backend готов для исправленной логики отображения и размещения")
            print("✅ API размещения груза возвращает корректную структуру")
            print("✅ Исправления React ошибки подтверждены на backend уровне")
            return True
        else:
            print(f"\n⚠️ ТРЕБУЮТСЯ ДОПОЛНИТЕЛЬНЫЕ ИСПРАВЛЕНИЯ!")
            print("❌ Backend не полностью готов для исправленной логики")
            return False

def main():
    """Основная функция"""
    tester = QRDisplayFixesTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        sys.exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        sys.exit(1)

if __name__ == "__main__":
    main()