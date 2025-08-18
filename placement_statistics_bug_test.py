#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ БАГА С placementStatistics В TAJLINE.TJ

КОНТЕКСТ ПРОБЛЕМЫ:
- В frontend переменная placementStatistics содержит объект {location_code, cargo_name, cargo_number, placed_at, warehouse_name}
- Это вызывает React ошибку "Objects are not valid as a React child"
- Ожидается структура {today_placements, session_placements, recent_placements}

ПОДОЗРЕНИЯ:
- API /api/operator/placement-statistics возвращает неправильную структуру
- Или где-то происходит перезапись placementStatistics результатом размещения груза
- Нужно проверить точную структуру ответа API

ТЕСТОВЫЙ ПЛАН:
1. Авторизация оператора склада (+79777888999/warehouse123)
2. ГЛАВНАЯ ПРОВЕРКА: Протестировать API /api/operator/placement-statistics
3. Проверить структуру ответа - должен содержать поля today_placements, session_placements, recent_placements
4. НЕ должен содержать поля location_code, cargo_name, cargo_number, placed_at, warehouse_name

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: API должен возвращать статистику размещения, а не данные конкретного груза.
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"

# Учетные данные оператора склада
WAREHOUSE_OPERATOR = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class PlacementStatisticsBugTester:
    def __init__(self):
        self.session = requests.Session()
        self.operator_token = None
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
                        f"Успешная авторизация: {user_info.get('full_name', 'Unknown')} (роль: {user_info.get('role', 'Unknown')})"
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
    
    def test_placement_statistics_api_structure(self):
        """КРИТИЧЕСКАЯ ПРОВЕРКА: Тестирование структуры API /api/operator/placement-statistics"""
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/placement-statistics", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем что это объект, а не массив
                if not isinstance(data, dict):
                    self.log_result(
                        "КРИТИЧЕСКАЯ ПРОВЕРКА: Структура API placement-statistics",
                        False,
                        f"API возвращает {type(data).__name__} вместо объекта",
                        {"response_type": type(data).__name__, "response_data": data}
                    )
                    return False
                
                # Проверяем наличие ПРАВИЛЬНЫХ полей статистики
                expected_fields = ["today_placements", "session_placements", "recent_placements"]
                present_expected_fields = [field for field in expected_fields if field in data]
                
                # Проверяем отсутствие НЕПРАВИЛЬНЫХ полей груза
                wrong_fields = ["location_code", "cargo_name", "cargo_number", "placed_at", "warehouse_name"]
                present_wrong_fields = [field for field in wrong_fields if field in data]
                
                # Анализируем результат
                has_correct_structure = len(present_expected_fields) > 0
                has_wrong_structure = len(present_wrong_fields) > 0
                
                if has_correct_structure and not has_wrong_structure:
                    self.log_result(
                        "КРИТИЧЕСКАЯ ПРОВЕРКА: Структура API placement-statistics",
                        True,
                        f"API возвращает правильную структуру статистики с полями: {present_expected_fields}",
                        {
                            "correct_fields_present": present_expected_fields,
                            "wrong_fields_absent": True,
                            "full_response": data
                        }
                    )
                    return True
                elif has_wrong_structure:
                    self.log_result(
                        "КРИТИЧЕСКАЯ ПРОВЕРКА: Структура API placement-statistics",
                        False,
                        f"🚨 КРИТИЧЕСКИЙ БАГ ПОДТВЕРЖДЕН: API возвращает поля груза вместо статистики: {present_wrong_fields}",
                        {
                            "wrong_fields_present": present_wrong_fields,
                            "expected_fields_present": present_expected_fields,
                            "full_response": data,
                            "bug_confirmed": True,
                            "react_error_cause": "Objects are not valid as a React child - API возвращает объект груза"
                        }
                    )
                    return False
                else:
                    self.log_result(
                        "КРИТИЧЕСКАЯ ПРОВЕРКА: Структура API placement-statistics",
                        False,
                        f"API возвращает неожиданную структуру без ожидаемых полей статистики",
                        {
                            "expected_fields_missing": [field for field in expected_fields if field not in data],
                            "actual_fields": list(data.keys()),
                            "full_response": data
                        }
                    )
                    return False
            else:
                self.log_result(
                    "КРИТИЧЕСКАЯ ПРОВЕРКА: Структура API placement-statistics",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("КРИТИЧЕСКАЯ ПРОВЕРКА: Структура API placement-statistics", False, f"Исключение: {str(e)}")
            return False
    
    def test_placement_statistics_data_types(self):
        """Проверка типов данных в ответе placement-statistics"""
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/placement-statistics", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем типы данных для статистических полей
                type_checks = []
                
                if "today_placements" in data:
                    today_type = type(data["today_placements"]).__name__
                    is_numeric = isinstance(data["today_placements"], (int, float))
                    type_checks.append({
                        "field": "today_placements",
                        "type": today_type,
                        "value": data["today_placements"],
                        "is_numeric": is_numeric
                    })
                
                if "session_placements" in data:
                    session_type = type(data["session_placements"]).__name__
                    is_numeric = isinstance(data["session_placements"], (int, float))
                    type_checks.append({
                        "field": "session_placements",
                        "type": session_type,
                        "value": data["session_placements"],
                        "is_numeric": is_numeric
                    })
                
                if "recent_placements" in data:
                    recent_type = type(data["recent_placements"]).__name__
                    is_list = isinstance(data["recent_placements"], list)
                    type_checks.append({
                        "field": "recent_placements",
                        "type": recent_type,
                        "value": data["recent_placements"],
                        "is_list": is_list
                    })
                
                # Проверяем что все типы корректны
                all_types_correct = True
                for check in type_checks:
                    if check["field"] in ["today_placements", "session_placements"]:
                        if not check["is_numeric"]:
                            all_types_correct = False
                    elif check["field"] == "recent_placements":
                        if not check["is_list"]:
                            all_types_correct = False
                
                if all_types_correct and type_checks:
                    self.log_result(
                        "Проверка типов данных placement-statistics",
                        True,
                        f"Все типы данных корректны для статистических полей",
                        {"type_checks": type_checks}
                    )
                    return True
                else:
                    self.log_result(
                        "Проверка типов данных placement-statistics",
                        False,
                        f"Некорректные типы данных в статистических полях",
                        {"type_checks": type_checks, "all_correct": all_types_correct}
                    )
                    return False
            else:
                self.log_result(
                    "Проверка типов данных placement-statistics",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Проверка типов данных placement-statistics", False, f"Исключение: {str(e)}")
            return False
    
    def test_placement_statistics_values(self):
        """Проверка значений в ответе placement-statistics"""
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/placement-statistics", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем значения статистики
                value_checks = []
                
                if "today_placements" in data:
                    today_val = data["today_placements"]
                    is_valid = isinstance(today_val, (int, float)) and today_val >= 0
                    value_checks.append({
                        "field": "today_placements",
                        "value": today_val,
                        "is_valid": is_valid,
                        "reason": "должно быть неотрицательным числом"
                    })
                
                if "session_placements" in data:
                    session_val = data["session_placements"]
                    is_valid = isinstance(session_val, (int, float)) and session_val >= 0
                    value_checks.append({
                        "field": "session_placements",
                        "value": session_val,
                        "is_valid": is_valid,
                        "reason": "должно быть неотрицательным числом"
                    })
                
                if "recent_placements" in data:
                    recent_val = data["recent_placements"]
                    is_valid = isinstance(recent_val, list)
                    value_checks.append({
                        "field": "recent_placements",
                        "value": f"массив из {len(recent_val)} элементов" if is_valid else recent_val,
                        "is_valid": is_valid,
                        "reason": "должно быть массивом"
                    })
                
                # Проверяем все значения
                all_values_valid = all(check["is_valid"] for check in value_checks)
                
                if all_values_valid and value_checks:
                    self.log_result(
                        "Проверка значений placement-statistics",
                        True,
                        f"Все значения статистики корректны",
                        {"value_checks": value_checks}
                    )
                    return True
                else:
                    invalid_checks = [check for check in value_checks if not check["is_valid"]]
                    self.log_result(
                        "Проверка значений placement-statistics",
                        False,
                        f"Некорректные значения в статистике: {len(invalid_checks)} полей",
                        {"invalid_checks": invalid_checks, "all_checks": value_checks}
                    )
                    return False
            else:
                self.log_result(
                    "Проверка значений placement-statistics",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Проверка значений placement-statistics", False, f"Исключение: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов для диагностики бага placementStatistics"""
        print("🚨 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ БАГА С placementStatistics В TAJLINE.TJ")
        print("=" * 80)
        print("🎯 ЦЕЛЬ: Проверить структуру API /api/operator/placement-statistics")
        print("🔍 ПРОБЛЕМА: React ошибка 'Objects are not valid as a React child'")
        print("=" * 80)
        
        # Шаг 1: Авторизация оператора склада
        if not self.authenticate_warehouse_operator():
            print("❌ Невозможно продолжить без авторизации оператора склада")
            return False
        
        # Шаг 2: КРИТИЧЕСКАЯ ПРОВЕРКА структуры API
        api_structure_correct = self.test_placement_statistics_api_structure()
        
        # Шаг 3: Проверка типов данных (если структура правильная)
        if api_structure_correct:
            self.test_placement_statistics_data_types()
            self.test_placement_statistics_values()
        
        # Итоговый отчет
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ БАГА")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Всего тестов: {total_tests}")
        print(f"Пройдено: {passed_tests}")
        print(f"Провалено: {failed_tests}")
        print(f"Процент успеха: {success_rate:.1f}%")
        
        # Критические результаты
        critical_test = next((r for r in self.test_results if "КРИТИЧЕСКАЯ ПРОВЕРКА" in r["test"]), None)
        
        print(f"\n🔍 ДИАГНОСТИКА БАГА:")
        
        if critical_test:
            if critical_test["success"]:
                print("   ✅ API /api/operator/placement-statistics возвращает ПРАВИЛЬНУЮ структуру статистики")
                print("   ✅ Поля today_placements, session_placements, recent_placements присутствуют")
                print("   ✅ Поля груза (location_code, cargo_name, etc.) отсутствуют")
                print("   ✅ React ошибка НЕ должна возникать из-за этого API")
                print("\n🤔 ВЫВОД: Проблема может быть в frontend коде, где placementStatistics")
                print("   перезаписывается результатом размещения груза вместо статистики")
            else:
                details = critical_test.get("details", {})
                if details.get("bug_confirmed"):
                    print("   🚨 БАГ ПОДТВЕРЖДЕН: API возвращает данные ГРУЗА вместо СТАТИСТИКИ")
                    print(f"   ❌ Найдены поля груза: {details.get('wrong_fields_present', [])}")
                    print("   ❌ Это вызывает React ошибку 'Objects are not valid as a React child'")
                    print("\n🔧 РЕШЕНИЕ: Исправить API /api/operator/placement-statistics")
                    print("   чтобы он возвращал статистику, а не данные конкретного груза")
                else:
                    print("   ❌ API возвращает неожиданную структуру")
                    print("   🔍 Требуется дополнительная диагностика")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        if critical_test and not critical_test["success"]:
            print("   1. Проверить backend код endpoint /api/operator/placement-statistics")
            print("   2. Убедиться что возвращается статистика, а не данные груза")
            print("   3. Исправить структуру ответа API")
        else:
            print("   1. Проверить frontend код где используется placementStatistics")
            print("   2. Найти место где статистика перезаписывается данными груза")
            print("   3. Разделить переменные для статистики и результата размещения")
        
        return success_rate >= 75.0

if __name__ == "__main__":
    tester = PlacementStatisticsBugTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО!")
        sys.exit(0)
    else:
        print("\n❌ ОБНАРУЖЕНЫ КРИТИЧЕСКИЕ ПРОБЛЕМЫ!")
        sys.exit(1)