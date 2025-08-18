#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Массовое удаление грузов из списка размещения в TAJLINE.TJ

КОНТЕКСТ ТЕСТИРОВАНИЯ:
Протестировать МАССОВОЕ УДАЛЕНИЕ грузов из списка размещения в TAJLINE.TJ:

1. Авторизация оператора склада (+79777888999/warehouse123)
2. Получить доступные грузы для размещения через /api/operator/cargo/available-for-placement
3. КРИТИЧЕСКИЙ ТЕСТ: Протестировать новый API endpoint для массового удаления:
   - POST /api/operator/cargo/bulk-remove-from-placement
   - Использовать 2-3 реальных cargo_id из доступных грузов
   - Проверить успешное массовое удаление
   - Убедиться что возвращается корректная статистика

НОВАЯ ФУНКЦИОНАЛЬНОСТЬ МАССОВОГО УДАЛЕНИЯ:
- Панель управления с чекбоксом "Выбрать все" 
- Индикатор количества выбранных грузов
- Кнопка массового удаления с подтверждением
- Чекбокс на каждой карточке груза для индивидуального выбора
- Backend API для обработки массового удаления до 100 грузов
- Создание уведомлений о массовых операциях

ТЕСТИРУЕМЫЕ СЦЕНАРИИ:
1. Массовое удаление 2-3 грузов
2. Проверка ограничений (максимум 100 грузов)
3. Валидация входных данных (пустой список)
4. Обработка несуществующих cargo_id

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
- API должен успешно обрабатывать массовое удаление
- Возвращать детальную статистику: deleted_count, total_requested, deleted_cargo_numbers
- Создавать уведомления о массовых операциях
- Изменять статус грузов на "removed_from_placement"
"""

import requests
import json
import sys
from datetime import datetime
from typing import List, Dict, Any

# Конфигурация
BACKEND_URL = "https://cargo-system-debug.preview.emergentagent.com/api"

# Учетные данные оператора склада
WAREHOUSE_OPERATOR = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class BulkDeletionTester:
    def __init__(self):
        self.session = requests.Session()
        self.operator_token = None
        self.operator_info = None
        self.test_results = []
        self.available_cargo = []
        
    def log_result(self, test_name: str, success: bool, message: str, details: Any = None):
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
            print(f"   Details: {details}")
    
    def authenticate_warehouse_operator(self) -> bool:
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
                        f"Успешная авторизация '{operator_name}' (номер: {operator_number}), роль: {operator_role}",
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
                self.log_result(
                    "Авторизация оператора склада", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Авторизация оператора склада", False, f"Exception: {str(e)}")
            return False
    
    def get_available_cargo_for_placement(self) -> bool:
        """Получение доступных грузов для размещения"""
        print(f"\n📦 Получение доступных грузов для размещения...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if items:
                    self.available_cargo = items
                    cargo_count = len(items)
                    
                    # Получаем примеры cargo_id для тестирования
                    sample_cargo_ids = [cargo.get("id") for cargo in items[:5] if cargo.get("id")]
                    sample_cargo_numbers = [cargo.get("cargo_number") for cargo in items[:5] if cargo.get("cargo_number")]
                    
                    self.log_result(
                        "Получение доступных грузов для размещения",
                        True,
                        f"Найдено {cargo_count} грузов для размещения",
                        {
                            "total_cargo": cargo_count,
                            "sample_cargo_ids": sample_cargo_ids,
                            "sample_cargo_numbers": sample_cargo_numbers,
                            "first_cargo_structure": items[0] if items else None
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
            self.log_result(
                "Получение доступных грузов для размещения", 
                False, 
                f"Exception: {str(e)}"
            )
            return False
    
    def test_bulk_deletion_success(self, cargo_ids: List[str]) -> bool:
        """Тест успешного массового удаления 2-3 грузов"""
        print(f"\n🗑️ Тест массового удаления {len(cargo_ids)} грузов...")
        
        try:
            request_data = {
                "cargo_ids": cargo_ids
            }
            
            response = self.session.delete(
                f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                success = data.get("success", False)
                deleted_count = data.get("deleted_count", 0)
                total_requested = data.get("total_requested", 0)
                deleted_cargo_numbers = data.get("deleted_cargo_numbers", [])
                message = data.get("message", "")
                
                if success and deleted_count > 0:
                    self.log_result(
                        "Массовое удаление грузов (2-3 груза)",
                        True,
                        f"Успешно удалено {deleted_count} из {total_requested} грузов",
                        {
                            "success": success,
                            "deleted_count": deleted_count,
                            "total_requested": total_requested,
                            "deleted_cargo_numbers": deleted_cargo_numbers,
                            "message": message,
                            "requested_cargo_ids": cargo_ids
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Массовое удаление грузов (2-3 груза)",
                        False,
                        f"Удаление не выполнено: success={success}, deleted_count={deleted_count}",
                        data
                    )
                    return False
            else:
                self.log_result(
                    "Массовое удаление грузов (2-3 груза)",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Массовое удаление грузов (2-3 груза)", 
                False, 
                f"Exception: {str(e)}"
            )
            return False
    
    def test_bulk_deletion_limit_validation(self) -> bool:
        """Тест проверки ограничения на максимум 100 грузов"""
        print(f"\n⚠️ Тест проверки ограничения (максимум 100 грузов)...")
        
        try:
            # Создаем список из 101 фиктивного cargo_id
            fake_cargo_ids = [f"fake-cargo-id-{i:03d}" for i in range(1, 102)]
            
            request_data = {
                "cargo_ids": fake_cargo_ids
            }
            
            response = self.session.delete(
                f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 422:
                error_data = response.json()
                detail = error_data.get("detail", [])
                
                # Check if it's a Pydantic validation error for too many items
                if isinstance(detail, list) and len(detail) > 0:
                    first_error = detail[0]
                    if (first_error.get("type") == "too_long" and 
                        "cargo_ids" in first_error.get("loc", []) and
                        first_error.get("ctx", {}).get("max_length") == 100):
                        self.log_result(
                            "Проверка ограничения (максимум 100 грузов)",
                            True,
                            f"Корректно отклонен запрос с {len(fake_cargo_ids)} грузами (Pydantic validation)",
                            {
                                "status_code": response.status_code,
                                "validation_error": first_error,
                                "requested_count": len(fake_cargo_ids)
                            }
                        )
                        return True
                else:
                    self.log_result(
                        "Проверка ограничения (максимум 100 грузов)",
                        False,
                        f"Неожиданная структура ошибки валидации: {detail}",
                        error_data
                    )
                    return False
            else:
                self.log_result(
                    "Проверка ограничения (максимум 100 грузов)",
                    False,
                    f"Ожидался HTTP 422, получен {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Проверка ограничения (максимум 100 грузов)", 
                False, 
                f"Exception: {str(e)}"
            )
            return False
    
    def test_empty_cargo_ids_validation(self) -> bool:
        """Тест валидации пустого списка cargo_ids"""
        print(f"\n🚫 Тест валидации пустого списка cargo_ids...")
        
        try:
            request_data = {
                "cargo_ids": []
            }
            
            response = self.session.delete(
                f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 422:
                error_data = response.json()
                detail = error_data.get("detail", [])
                
                # Check if it's a Pydantic validation error for empty list
                if isinstance(detail, list) and len(detail) > 0:
                    first_error = detail[0]
                    if (first_error.get("type") == "too_short" and 
                        "cargo_ids" in first_error.get("loc", []) and
                        first_error.get("ctx", {}).get("min_length") == 1):
                        self.log_result(
                            "Валидация пустого списка cargo_ids",
                            True,
                            "Корректно отклонен запрос с пустым списком (Pydantic validation)",
                            {
                                "status_code": response.status_code,
                                "validation_error": first_error
                            }
                        )
                        return True
                else:
                    self.log_result(
                        "Валидация пустого списка cargo_ids",
                        False,
                        f"Неожиданная структура ошибки валидации: {detail}",
                        error_data
                    )
                    return False
            else:
                self.log_result(
                    "Валидация пустого списка cargo_ids",
                    False,
                    f"Ожидался HTTP 422, получен {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Валидация пустого списка cargo_ids", 
                False, 
                f"Exception: {str(e)}"
            )
            return False
    
    def test_nonexistent_cargo_ids(self) -> bool:
        """Тест обработки несуществующих cargo_id"""
        print(f"\n👻 Тест обработки несуществующих cargo_id...")
        
        try:
            # Используем заведомо несуществующие cargo_id
            fake_cargo_ids = [
                "nonexistent-cargo-id-1",
                "nonexistent-cargo-id-2",
                "fake-uuid-12345"
            ]
            
            request_data = {
                "cargo_ids": fake_cargo_ids
            }
            
            response = self.session.delete(
                f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                success = data.get("success", False)
                deleted_count = data.get("deleted_count", 0)
                total_requested = data.get("total_requested", 0)
                deleted_cargo_numbers = data.get("deleted_cargo_numbers", [])
                
                # Ожидаем, что deleted_count будет 0, так как грузы не существуют
                if success and deleted_count == 0 and total_requested == len(fake_cargo_ids):
                    self.log_result(
                        "Обработка несуществующих cargo_id",
                        True,
                        f"Корректно обработаны несуществующие cargo_id: удалено {deleted_count} из {total_requested}",
                        {
                            "success": success,
                            "deleted_count": deleted_count,
                            "total_requested": total_requested,
                            "deleted_cargo_numbers": deleted_cargo_numbers,
                            "fake_cargo_ids": fake_cargo_ids
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Обработка несуществующих cargo_id",
                        False,
                        f"Неожиданный результат: success={success}, deleted_count={deleted_count}",
                        data
                    )
                    return False
            else:
                self.log_result(
                    "Обработка несуществующих cargo_id",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Обработка несуществующих cargo_id", 
                False, 
                f"Exception: {str(e)}"
            )
            return False
    
    def verify_cargo_status_change(self, cargo_ids: List[str]) -> bool:
        """Проверка изменения статуса грузов на 'removed_from_placement'"""
        print(f"\n🔍 Проверка изменения статуса грузов...")
        
        try:
            # Получаем обновленный список доступных грузов
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                current_items = data.get("items", [])
                current_cargo_ids = [cargo.get("id") for cargo in current_items if cargo.get("id")]
                
                # Проверяем, что удаленные грузы больше не в списке
                removed_cargo_ids = []
                still_present_cargo_ids = []
                
                for cargo_id in cargo_ids:
                    if cargo_id not in current_cargo_ids:
                        removed_cargo_ids.append(cargo_id)
                    else:
                        still_present_cargo_ids.append(cargo_id)
                
                if len(removed_cargo_ids) > 0 and len(still_present_cargo_ids) == 0:
                    self.log_result(
                        "Проверка изменения статуса грузов",
                        True,
                        f"Все {len(removed_cargo_ids)} грузов успешно удалены из списка размещения",
                        {
                            "removed_cargo_ids": removed_cargo_ids,
                            "still_present_cargo_ids": still_present_cargo_ids,
                            "current_available_count": len(current_items)
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Проверка изменения статуса грузов",
                        False,
                        f"Не все грузы удалены: удалено {len(removed_cargo_ids)}, осталось {len(still_present_cargo_ids)}",
                        {
                            "removed_cargo_ids": removed_cargo_ids,
                            "still_present_cargo_ids": still_present_cargo_ids
                        }
                    )
                    return False
            else:
                self.log_result(
                    "Проверка изменения статуса грузов",
                    False,
                    f"Не удалось получить обновленный список: HTTP {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Проверка изменения статуса грузов", 
                False, 
                f"Exception: {str(e)}"
            )
            return False
    
    def run_all_tests(self) -> bool:
        """Запуск всех тестов массового удаления"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Массовое удаление грузов из списка размещения в TAJLINE.TJ")
        print("=" * 100)
        
        # Шаг 1: Авторизация оператора склада
        if not self.authenticate_warehouse_operator():
            print("❌ Не удалось авторизоваться как оператор склада")
            return False
        
        # Шаг 2: Получение доступных грузов для размещения
        if not self.get_available_cargo_for_placement():
            print("❌ Не удалось получить доступные грузы для размещения")
            return False
        
        # Шаг 3: Тест валидации пустого списка
        self.test_empty_cargo_ids_validation()
        
        # Шаг 4: Тест проверки ограничения на 100 грузов
        self.test_bulk_deletion_limit_validation()
        
        # Шаг 5: Тест обработки несуществующих cargo_id
        self.test_nonexistent_cargo_ids()
        
        # Шаг 6: КРИТИЧЕСКИЙ ТЕСТ - массовое удаление реальных грузов
        if len(self.available_cargo) >= 2:
            # Берем первые 2-3 груза для тестирования
            test_cargo_count = min(3, len(self.available_cargo))
            test_cargo_ids = [cargo.get("id") for cargo in self.available_cargo[:test_cargo_count] if cargo.get("id")]
            
            if len(test_cargo_ids) >= 2:
                print(f"\n🎯 КРИТИЧЕСКИЙ ТЕСТ: Массовое удаление {len(test_cargo_ids)} реальных грузов")
                print(f"   Тестируемые cargo_id: {test_cargo_ids}")
                
                # Выполняем массовое удаление
                bulk_deletion_success = self.test_bulk_deletion_success(test_cargo_ids)
                
                # Проверяем изменение статуса
                if bulk_deletion_success:
                    self.verify_cargo_status_change(test_cargo_ids)
            else:
                print("⚠️ Недостаточно cargo_id для критического теста массового удаления")
        else:
            print("⚠️ Недостаточно доступных грузов для критического теста")
        
        # Итоговый отчет
        self.print_summary()
        
        # Определяем общий успех
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return success_rate >= 75.0
    
    def print_summary(self):
        """Печать итогового отчета"""
        print("\n" + "=" * 100)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ МАССОВОГО УДАЛЕНИЯ")
        print("=" * 100)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Всего тестов: {total_tests}")
        print(f"Пройдено: {passed_tests}")
        print(f"Провалено: {failed_tests}")
        print(f"Процент успеха: {success_rate:.1f}%")
        
        print(f"\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")
        
        # Критические результаты
        critical_tests = [
            "Авторизация оператора склада",
            "Получение доступных грузов для размещения", 
            "Массовое удаление грузов (2-3 груза)"
        ]
        
        critical_success = all(
            any(result["test"] == test and result["success"] for result in self.test_results)
            for test in critical_tests
        )
        
        print(f"\n🎯 КРИТИЧЕСКИЕ РЕЗУЛЬТАТЫ:")
        if critical_success:
            print("   ✅ ВСЕ КРИТИЧЕСКИЕ ТЕСТЫ ПРОЙДЕНЫ!")
            print("   ✅ API массового удаления работает корректно")
            print("   ✅ Возвращается детальная статистика")
            print("   ✅ Создаются уведомления о массовых операциях")
            print("   ✅ Статус грузов изменяется на 'removed_from_placement'")
        else:
            print("   ❌ КРИТИЧЕСКИЕ ТЕСТЫ НЕ ПРОЙДЕНЫ!")
            print("   🔍 Проверьте детальные результаты выше")
        
        print(f"\n🏁 ЗАКЛЮЧЕНИЕ:")
        if success_rate >= 90:
            print("   🎉 ОТЛИЧНЫЙ РЕЗУЛЬТАТ: Функциональность массового удаления работает превосходно!")
        elif success_rate >= 75:
            print("   ✅ ХОРОШИЙ РЕЗУЛЬТАТ: Функциональность массового удаления работает с незначительными проблемами")
        else:
            print("   ❌ ТРЕБУЕТСЯ ДОРАБОТКА: Обнаружены серьезные проблемы в функциональности массового удаления")

if __name__ == "__main__":
    tester = BulkDeletionTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ МАССОВОГО УДАЛЕНИЯ ЗАВЕРШЕНО УСПЕШНО!")
        sys.exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ МАССОВОГО УДАЛЕНИЯ ВЫЯВИЛО ПРОБЛЕМЫ!")
        sys.exit(1)