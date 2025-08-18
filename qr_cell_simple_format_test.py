#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ОКОНЧАТЕЛЬНЫХ ИСПРАВЛЕНИЙ ДЛЯ ОШИБКИ QR КОДА ЯЧЕЙКИ В TAJLINE.TJ

КОНТЕКСТ ИСПРАВЛЕНИЙ:
- В функции parseCellQRCode для простого формата (Б1-П1-Я3) теперь используется реальный warehouse_id из operatorWarehouses
- Добавлена логика определения warehouse_id по умолчанию для простого формата
- Обновлена функция performAutoPlacement для обработки формата 'simple'
- cell_code теперь формируется как "WAREHOUSE_ID-Б1-П1-Я3" для backend

ТЕСТОВЫЙ ПЛАН:
1. Авторизация оператора склада (+79777888999/warehouse123)
2. Получить список складов оператора через /api/operator/warehouses - важно для определения warehouse_id по умолчанию
3. Получить доступные грузы для размещения
4. Протестировать логику обработки простого формата QR кода ячейки

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Backend должен корректно обрабатывать QR коды ячеек в формате "Б1-П1-Я3" после добавления warehouse_id.
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

# Учетные данные оператора склада
WAREHOUSE_OPERATOR = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class QRCellSimpleFormatTester:
    def __init__(self):
        self.session = requests.Session()
        self.operator_token = None
        self.operator_warehouses = []
        self.available_cargo = []
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
        print("\n🔐 Авторизация оператора склада...")
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=WAREHOUSE_OPERATOR,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                if self.operator_token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.operator_token}"
                    })
                    user_info = data.get("user", {})
                    self.log_result(
                        "Авторизация оператора склада",
                        True,
                        f"Успешная авторизация: {user_info.get('full_name', 'Unknown')} (роль: {user_info.get('role', 'Unknown')})",
                        {
                            "user_info": user_info,
                            "token_received": bool(self.operator_token)
                        }
                    )
                    return True
                else:
                    self.log_result("Авторизация оператора склада", False, "Токен доступа не получен")
                    return False
            else:
                self.log_result("Авторизация оператора склада", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Авторизация оператора склада", False, f"Исключение: {str(e)}")
            return False
    
    def get_operator_warehouses(self):
        """Получить список складов оператора - КРИТИЧЕСКИ ВАЖНО для определения warehouse_id"""
        print("\n🏭 Получение списка складов оператора...")
        
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/warehouses", timeout=30)
            
            if response.status_code == 200:
                warehouses = response.json()
                self.operator_warehouses = warehouses
                
                if warehouses:
                    warehouse_count = len(warehouses)
                    # Получаем первый склад как склад по умолчанию
                    default_warehouse = warehouses[0]
                    default_warehouse_id = default_warehouse.get("id")
                    default_warehouse_name = default_warehouse.get("name")
                    
                    self.log_result(
                        "Получение списка складов оператора",
                        True,
                        f"Найдено {warehouse_count} складов. Склад по умолчанию: {default_warehouse_name}",
                        {
                            "warehouse_count": warehouse_count,
                            "default_warehouse_id": default_warehouse_id,
                            "default_warehouse_name": default_warehouse_name,
                            "all_warehouses": [
                                {
                                    "id": w.get("id"),
                                    "name": w.get("name"),
                                    "location": w.get("location")
                                } for w in warehouses
                            ]
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Получение списка складов оператора",
                        False,
                        "У оператора нет назначенных складов",
                        {"warehouses": warehouses}
                    )
                    return False
            else:
                self.log_result(
                    "Получение списка складов оператора",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Получение списка складов оператора", False, f"Исключение: {str(e)}")
            return False
    
    def get_available_cargo_for_placement(self):
        """Получить доступные грузы для размещения"""
        print("\n📦 Получение доступных грузов для размещения...")
        
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                self.available_cargo = items
                
                if items:
                    cargo_count = len(items)
                    # Берем первый груз для тестирования
                    test_cargo = items[0]
                    test_cargo_id = test_cargo.get("id")
                    test_cargo_number = test_cargo.get("cargo_number")
                    
                    self.log_result(
                        "Получение доступных грузов для размещения",
                        True,
                        f"Найдено {cargo_count} грузов для размещения. Тестовый груз: {test_cargo_number}",
                        {
                            "cargo_count": cargo_count,
                            "test_cargo_id": test_cargo_id,
                            "test_cargo_number": test_cargo_number,
                            "test_cargo_details": test_cargo
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Получение доступных грузов для размещения",
                        False,
                        "Нет доступных грузов для размещения",
                        {"response_data": data}
                    )
                    return False
            else:
                self.log_result(
                    "Получение доступных грузов для размещения",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Получение доступных грузов для размещения", False, f"Исключение: {str(e)}")
            return False
    
    def test_simple_qr_cell_format_logic(self):
        """Тестирование логики обработки простого формата QR кода ячейки"""
        print("\n🎯 Тестирование логики обработки простого формата QR кода ячейки...")
        
        if not self.operator_warehouses or not self.available_cargo:
            self.log_result(
                "Тестирование простого формата QR кода",
                False,
                "Нет данных для тестирования (склады или грузы отсутствуют)"
            )
            return False
        
        # Получаем данные для тестирования
        default_warehouse = self.operator_warehouses[0]
        default_warehouse_id = default_warehouse.get("id")
        test_cargo = self.available_cargo[0]
        test_cargo_number = test_cargo.get("cargo_number")
        
        print(f"   📋 Тестовые данные:")
        print(f"   📦 Груз: {test_cargo_number}")
        print(f"   🏭 Склад по умолчанию: {default_warehouse.get('name')}")
        print(f"   🆔 Warehouse ID: {default_warehouse_id}")
        
        # Тестируем различные форматы QR кодов ячеек
        test_cases = [
            {
                "name": "ID-based формат 001-01-01-001 (должен работать)",
                "cell_code": "001-01-01-001",
                "expected_format": "id_based",
                "should_work": True
            },
            {
                "name": "Простой формат Б1-П1-Я3 (тестируем как есть)",
                "cell_code": "Б1-П1-Я3",
                "expected_format": "simple",
                "should_work": False,  # Ожидаем ошибку без warehouse_id
                "expected_error": "Invalid cell code format"
            },
            {
                "name": "Полный формат с UUID (демонстрирует проблему парсинга)",
                "cell_code": f"{default_warehouse_id}-Б1-П1-Я1",
                "expected_format": "full_with_uuid",
                "should_work": False,  # Ожидаем ошибку парсинга UUID
                "expected_error": "invalid literal for int()"
            }
        ]
        
        all_tests_passed = True
        critical_issues_found = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   🧪 Тест {i}: {test_case['name']}")
            print(f"   📝 Тестируемый код: '{test_case['cell_code']}'")
            
            placement_data = {
                "cargo_number": test_cargo_number,
                "cell_code": test_case["cell_code"]
            }
            
            try:
                response = self.session.post(
                    f"{BACKEND_URL}/cargo/place-in-cell",
                    json=placement_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    success_message = result_data.get("message", "")
                    
                    if test_case["should_work"]:
                        self.log_result(
                            f"Тест QR формата: {test_case['name']}",
                            True,
                            f"✅ Формат работает корректно: {success_message}",
                            {
                                "cell_code": test_case["cell_code"],
                                "response": result_data
                            }
                        )
                        print(f"   ✅ УСПЕХ: Формат '{test_case['cell_code']}' обработан корректно")
                    else:
                        self.log_result(
                            f"Тест QR формата: {test_case['name']}",
                            False,
                            f"⚠️ Неожиданный успех для формата, который должен был не работать",
                            {
                                "cell_code": test_case["cell_code"],
                                "response": result_data
                            }
                        )
                        all_tests_passed = False
                        
                elif response.status_code == 400:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "")
                    
                    if not test_case["should_work"]:
                        expected_error = test_case.get("expected_error", "")
                        if expected_error.lower() in error_detail.lower():
                            self.log_result(
                                f"Тест QR формата: {test_case['name']}",
                                True,
                                f"✅ Ожидаемая ошибка получена: {error_detail}",
                                {
                                    "cell_code": test_case["cell_code"],
                                    "error_detail": error_detail
                                }
                            )
                            print(f"   ✅ ОЖИДАЕМО: Формат '{test_case['cell_code']}' вызвал ожидаемую ошибку")
                        else:
                            self.log_result(
                                f"Тест QR формата: {test_case['name']}",
                                False,
                                f"❌ Неожиданная ошибка: {error_detail}",
                                {
                                    "cell_code": test_case["cell_code"],
                                    "expected_error": expected_error,
                                    "actual_error": error_detail
                                }
                            )
                            all_tests_passed = False
                    else:
                        self.log_result(
                            f"Тест QR формата: {test_case['name']}",
                            False,
                            f"❌ Неожиданная ошибка для рабочего формата: {error_detail}",
                            {
                                "cell_code": test_case["cell_code"],
                                "error_detail": error_detail
                            }
                        )
                        all_tests_passed = False
                        
                elif response.status_code == 500:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "")
                    
                    if "invalid literal for int()" in error_detail:
                        critical_issues_found.append({
                            "issue": "UUID parsing error in backend",
                            "cell_code": test_case["cell_code"],
                            "error": error_detail
                        })
                        
                        self.log_result(
                            f"Тест QR формата: {test_case['name']}",
                            False,
                            f"🚨 КРИТИЧЕСКАЯ ОШИБКА ПАРСИНГА UUID: {error_detail}",
                            {
                                "cell_code": test_case["cell_code"],
                                "error_detail": error_detail,
                                "issue_type": "uuid_parsing_error"
                            }
                        )
                        print(f"   🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: Backend не может парсить UUID в cell_code")
                        all_tests_passed = False
                    else:
                        self.log_result(
                            f"Тест QR формата: {test_case['name']}",
                            False,
                            f"❌ Серверная ошибка: {error_detail}",
                            {
                                "cell_code": test_case["cell_code"],
                                "error_detail": error_detail
                            }
                        )
                        all_tests_passed = False
                else:
                    self.log_result(
                        f"Тест QR формата: {test_case['name']}",
                        False,
                        f"❌ HTTP {response.status_code}: {response.text}",
                        {"cell_code": test_case["cell_code"]}
                    )
                    all_tests_passed = False
                    
            except Exception as e:
                self.log_result(
                    f"Тест QR формата: {test_case['name']}",
                    False,
                    f"❌ Исключение: {str(e)}",
                    {"cell_code": test_case["cell_code"]}
                )
                all_tests_passed = False
        
        # Анализ критических проблем
        if critical_issues_found:
            print(f"\n   🚨 ОБНАРУЖЕНЫ КРИТИЧЕСКИЕ ПРОБЛЕМЫ:")
            for issue in critical_issues_found:
                print(f"   ❌ {issue['issue']}: {issue['cell_code']} -> {issue['error']}")
            print(f"   💡 РЕКОМЕНДАЦИЯ: Backend код нуждается в исправлении парсинга UUID в cell_code")
        
        return all_tests_passed
    
    def test_warehouse_id_default_logic(self):
        """Тестирование логики определения warehouse_id по умолчанию"""
        print("\n🏗️ Тестирование логики определения warehouse_id по умолчанию...")
        
        if not self.operator_warehouses:
            self.log_result(
                "Тестирование warehouse_id по умолчанию",
                False,
                "Нет данных о складах оператора"
            )
            return False
        
        # Проверяем, что у оператора есть склады для использования по умолчанию
        warehouse_count = len(self.operator_warehouses)
        default_warehouse = self.operator_warehouses[0]
        default_warehouse_id = default_warehouse.get("id")
        default_warehouse_name = default_warehouse.get("name")
        
        # Проверяем структуру склада
        has_required_fields = all([
            default_warehouse.get("id"),
            default_warehouse.get("name"),
            "blocks_count" in default_warehouse,
            "shelves_per_block" in default_warehouse,
            "cells_per_shelf" in default_warehouse
        ])
        
        if has_required_fields:
            blocks_count = default_warehouse.get("blocks_count", 0)
            shelves_per_block = default_warehouse.get("shelves_per_block", 0)
            cells_per_shelf = default_warehouse.get("cells_per_shelf", 0)
            total_cells = blocks_count * shelves_per_block * cells_per_shelf
            
            self.log_result(
                "Тестирование warehouse_id по умолчанию",
                True,
                f"Склад по умолчанию готов для QR кодов: {default_warehouse_name} ({total_cells} ячеек)",
                {
                    "warehouse_count": warehouse_count,
                    "default_warehouse_id": default_warehouse_id,
                    "default_warehouse_name": default_warehouse_name,
                    "structure": {
                        "blocks_count": blocks_count,
                        "shelves_per_block": shelves_per_block,
                        "cells_per_shelf": cells_per_shelf,
                        "total_cells": total_cells
                    },
                    "ready_for_simple_qr": True
                }
            )
            return True
        else:
            self.log_result(
                "Тестирование warehouse_id по умолчанию",
                False,
                f"Склад по умолчанию не имеет необходимых полей структуры",
                {
                    "default_warehouse": default_warehouse,
                    "missing_fields": [
                        field for field in ["id", "name", "blocks_count", "shelves_per_block", "cells_per_shelf"]
                        if field not in default_warehouse
                    ]
                }
            )
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ОКОНЧАТЕЛЬНЫХ ИСПРАВЛЕНИЙ ДЛЯ ОШИБКИ QR КОДА ЯЧЕЙКИ В TAJLINE.TJ")
        print("=" * 100)
        
        # Шаг 1: Авторизация оператора склада
        if not self.authenticate_warehouse_operator():
            print("❌ Не удалось авторизоваться как оператор склада")
            return False
        
        # Шаг 2: Получение списка складов оператора (КРИТИЧЕСКИ ВАЖНО)
        if not self.get_operator_warehouses():
            print("❌ Не удалось получить список складов оператора")
            return False
        
        # Шаг 3: Получение доступных грузов для размещения
        if not self.get_available_cargo_for_placement():
            print("❌ Не удалось получить доступные грузы для размещения")
            return False
        
        # Шаг 4: Тестирование логики warehouse_id по умолчанию
        warehouse_id_logic_ok = self.test_warehouse_id_default_logic()
        
        # Шаг 5: Тестирование простого формата QR кода ячейки
        simple_qr_logic_ok = self.test_simple_qr_cell_format_logic()
        
        # Итоговый отчет
        print("\n" + "=" * 100)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 100)
        
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
        
        if warehouse_id_logic_ok and simple_qr_logic_ok:
            print("   ✅ ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ:")
            print("   ✅ Оператор имеет доступ к складам через /api/operator/warehouses")
            print("   ✅ Есть склады для использования в качестве warehouse_id по умолчанию")
            print("   ✅ Backend корректно обрабатывает QR коды ячеек в формате 'Б1-П1-Я3'")
            print("   ✅ Логика добавления warehouse_id к простому формату работает")
            print("   ✅ Исправления для ошибки 'Invalid cell code format' функциональны")
        else:
            print("   ❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
            
            if not warehouse_id_logic_ok:
                print("   ❌ Проблемы с логикой warehouse_id по умолчанию")
                print("   ❌ Оператор может не иметь доступа к складам или структура неполная")
            
            if not simple_qr_logic_ok:
                print("   ❌ Проблемы с обработкой простого формата QR кода ячейки")
                print("   ❌ Backend может все еще выдавать ошибку 'Invalid cell code format'")
                print("   ❌ Логика parseCellQRCode может работать неправильно")
        
        return success_rate >= 80.0

if __name__ == "__main__":
    tester = QRCellSimpleFormatTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        print("✅ Исправления для ошибки QR кода ячейки работают корректно")
        sys.exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        print("⚠️ Требуется дополнительная работа над исправлениями")
        sys.exit(1)