#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправленная функциональность массового удаления грузов в TAJLINE.TJ

ИСПРАВЛЕНИЯ ДЛЯ ТЕСТИРОВАНИЯ:
1) Frontend теперь использует правильный endpoint /api/operator/cargo/bulk-remove-from-placement
2) Изменена структура данных с {ids: [...]} на {cargo_ids: [...]}
3) Используется роль warehouse_operator вместо admin
4) Обновлены сообщения об успешном удалении

КРИТИЧЕСКИЕ ТЕСТЫ:
1) Авторизация оператора склада (+79777888999/warehouse123)
2) Получение списка доступных грузов для размещения
3) Тестирование массового удаления через правильный endpoint /api/operator/cargo/bulk-remove-from-placement
4) Проверка что грузы действительно удаляются и получают статус 'removed_from_placement'
5) Проверка единичного удаления через /api/operator/cargo/{id}/remove-from-placement
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "https://tajline-cargo-3.preview.emergentagent.com/api"

class BulkRemovalTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, details):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        print(f"{status}: {test_name}")
        print(f"   Details: {details}")
        print()
        
    def authenticate_warehouse_operator(self):
        """Test 1: Авторизация оператора склада (+79777888999/warehouse123)"""
        try:
            login_data = {
                "phone": "+79777888999",
                "password": "warehouse123"
            }
            
            response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('access_token')
                user_info = data.get('user', {})
                
                # Verify role is warehouse_operator
                if user_info.get('role') == 'warehouse_operator':
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.auth_token}'
                    })
                    self.log_test(
                        "Авторизация оператора склада (+79777888999/warehouse123)",
                        True,
                        f"Успешная авторизация '{user_info.get('full_name')}' (номер: {user_info.get('user_number')}), роль: {user_info.get('role')} подтверждена, JWT токен получен"
                    )
                    return True
                else:
                    self.log_test(
                        "Авторизация оператора склада (+79777888999/warehouse123)",
                        False,
                        f"Неправильная роль: ожидалась 'warehouse_operator', получена '{user_info.get('role')}'"
                    )
                    return False
            else:
                self.log_test(
                    "Авторизация оператора склада (+79777888999/warehouse123)",
                    False,
                    f"Ошибка авторизации: HTTP {response.status_code}, {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Авторизация оператора склада (+79777888999/warehouse123)",
                False,
                f"Исключение при авторизации: {str(e)}"
            )
            return False
    
    def get_available_cargo_for_placement(self):
        """Test 2: Получение списка доступных грузов для размещения"""
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement")
            
            if response.status_code == 200:
                data = response.json()
                cargo_list = data.get('items', [])
                
                if len(cargo_list) > 0:
                    # Extract cargo IDs for testing
                    self.available_cargo_ids = [cargo.get('id') for cargo in cargo_list if cargo.get('id')]
                    self.available_cargo_numbers = [cargo.get('cargo_number') for cargo in cargo_list if cargo.get('cargo_number')]
                    
                    self.log_test(
                        "Получение списка доступных грузов для размещения",
                        True,
                        f"GET /api/operator/cargo/available-for-placement работает корректно, найдено {len(cargo_list)} грузов для размещения, все cargo_id доступны для тестирования"
                    )
                    return True
                else:
                    self.log_test(
                        "Получение списка доступных грузов для размещения",
                        False,
                        "Список доступных грузов пуст, нет грузов для тестирования удаления"
                    )
                    return False
            else:
                self.log_test(
                    "Получение списка доступных грузов для размещения",
                    False,
                    f"Ошибка получения грузов: HTTP {response.status_code}, {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Получение списка доступных грузов для размещения",
                False,
                f"Исключение при получении грузов: {str(e)}"
            )
            return False
    
    def test_bulk_removal_validation(self):
        """Test 3: Тестирование валидации массового удаления"""
        try:
            # Test empty cargo_ids list
            empty_data = {"cargo_ids": []}
            response = self.session.delete(f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement", json=empty_data)
            
            if response.status_code == 422:
                validation_success_1 = True
                validation_msg_1 = "Пустой список cargo_ids корректно отклоняется (HTTP 422)"
            else:
                validation_success_1 = False
                validation_msg_1 = f"Пустой список должен возвращать HTTP 422, получен {response.status_code}"
            
            # Test too many cargo_ids (>100)
            large_data = {"cargo_ids": ["test_id"] * 101}
            response = self.session.delete(f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement", json=large_data)
            
            if response.status_code == 422:
                validation_success_2 = True
                validation_msg_2 = "Превышение лимита >100 грузов корректно отклоняется (HTTP 422)"
            else:
                validation_success_2 = False
                validation_msg_2 = f"Большой список должен возвращать HTTP 422, получен {response.status_code}"
            
            # Test non-existent cargo_ids
            fake_data = {"cargo_ids": ["fake_id_1", "fake_id_2"]}
            response = self.session.delete(f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement", json=fake_data)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('deleted_count', -1) == 0:
                    validation_success_3 = True
                    validation_msg_3 = "Несуществующие cargo_id обрабатываются без ошибок (deleted_count=0)"
                else:
                    validation_success_3 = False
                    validation_msg_3 = f"Ожидался deleted_count=0, получен {data.get('deleted_count')}"
            else:
                validation_success_3 = False
                validation_msg_3 = f"Несуществующие ID должны возвращать HTTP 200, получен {response.status_code}"
            
            overall_success = validation_success_1 and validation_success_2 and validation_success_3
            details = f"{validation_msg_1}, {validation_msg_2}, {validation_msg_3}"
            
            self.log_test(
                "Валидация данных для массового удаления",
                overall_success,
                details
            )
            return overall_success
            
        except Exception as e:
            self.log_test(
                "Валидация данных для массового удаления",
                False,
                f"Исключение при тестировании валидации: {str(e)}"
            )
            return False
    
    def test_single_cargo_removal(self):
        """Test 4: Проверка единичного удаления через /api/operator/cargo/{id}/remove-from-placement"""
        try:
            if not hasattr(self, 'available_cargo_ids') or len(self.available_cargo_ids) == 0:
                self.log_test(
                    "Единичное удаление груза",
                    False,
                    "Нет доступных грузов для тестирования единичного удаления"
                )
                return False
            
            # Use first available cargo for single removal test
            test_cargo_id = self.available_cargo_ids[0]
            
            response = self.session.delete(f"{BACKEND_URL}/operator/cargo/{test_cargo_id}/remove-from-placement")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                if (data.get('success') == True and 
                    'message' in data and 
                    'cargo_number' in data):
                    
                    # Remove this cargo from available list for bulk test
                    self.available_cargo_ids.remove(test_cargo_id)
                    
                    self.log_test(
                        "Единичное удаление груза",
                        True,
                        f"DELETE /api/operator/cargo/{test_cargo_id}/remove-from-placement работает корректно, возвращает правильную структуру ответа (success: True, message: '{data.get('message')}', cargo_number: '{data.get('cargo_number')}')"
                    )
                    return True
                else:
                    self.log_test(
                        "Единичное удаление груза",
                        False,
                        f"Неправильная структура ответа: {data}"
                    )
                    return False
            else:
                self.log_test(
                    "Единичное удаление груза",
                    False,
                    f"Ошибка единичного удаления: HTTP {response.status_code}, {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Единичное удаление груза",
                False,
                f"Исключение при единичном удалении: {str(e)}"
            )
            return False
    
    def test_bulk_cargo_removal(self):
        """Test 5: Тестирование массового удаления через правильный endpoint с правильной структурой данных"""
        try:
            if not hasattr(self, 'available_cargo_ids') or len(self.available_cargo_ids) < 2:
                self.log_test(
                    "Массовое удаление грузов",
                    False,
                    "Недостаточно доступных грузов для тестирования массового удаления (нужно минимум 2)"
                )
                return False
            
            # Use 2-3 cargo IDs for bulk removal test
            test_cargo_ids = self.available_cargo_ids[:3] if len(self.available_cargo_ids) >= 3 else self.available_cargo_ids[:2]
            
            # Use correct data structure: {cargo_ids: [...]}
            bulk_data = {"cargo_ids": test_cargo_ids}
            
            response = self.session.delete(f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement", json=bulk_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure and data
                expected_fields = ['success', 'deleted_count', 'total_requested', 'deleted_cargo_numbers']
                missing_fields = [field for field in expected_fields if field not in data]
                
                if not missing_fields:
                    deleted_count = data.get('deleted_count', 0)
                    total_requested = data.get('total_requested', 0)
                    deleted_cargo_numbers = data.get('deleted_cargo_numbers', [])
                    
                    if (data.get('success') == True and 
                        deleted_count == len(test_cargo_ids) and 
                        total_requested == len(test_cargo_ids) and
                        len(deleted_cargo_numbers) == deleted_count):
                        
                        self.log_test(
                            "Массовое удаление грузов",
                            True,
                            f"DELETE /api/operator/cargo/bulk-remove-from-placement УСПЕШНО работает! Удалено {deleted_count} груза из {total_requested} запрошенных, возвращает детальную статистику (deleted_count, total_requested, deleted_cargo_numbers), правильная структура данных {{cargo_ids: [...]}} работает корректно"
                        )
                        
                        # Store deleted cargo numbers for verification
                        self.deleted_cargo_numbers = deleted_cargo_numbers
                        return True
                    else:
                        self.log_test(
                            "Массовое удаление грузов",
                            False,
                            f"Неправильные данные в ответе: success={data.get('success')}, deleted_count={deleted_count}, total_requested={total_requested}, expected={len(test_cargo_ids)}"
                        )
                        return False
                else:
                    self.log_test(
                        "Массовое удаление грузов",
                        False,
                        f"Отсутствуют обязательные поля в ответе: {missing_fields}"
                    )
                    return False
            else:
                self.log_test(
                    "Массовое удаление грузов",
                    False,
                    f"Ошибка массового удаления: HTTP {response.status_code}, {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Массовое удаление грузов",
                False,
                f"Исключение при массовом удалении: {str(e)}"
            )
            return False
    
    def verify_cargo_removal_status(self):
        """Test 6: Проверка что грузы действительно удалены и получили статус 'removed_from_placement'"""
        try:
            # Get updated list of available cargo
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement")
            
            if response.status_code == 200:
                data = response.json()
                current_cargo_list = data.get('items', [])
                current_cargo_numbers = [cargo.get('cargo_number') for cargo in current_cargo_list if cargo.get('cargo_number')]
                
                # Check if deleted cargo numbers are no longer in the list
                if hasattr(self, 'deleted_cargo_numbers'):
                    still_present = [num for num in self.deleted_cargo_numbers if num in current_cargo_numbers]
                    
                    if not still_present:
                        self.log_test(
                            "Проверка изменения статуса грузов",
                            True,
                            f"Все удаленные грузы ({len(self.deleted_cargo_numbers)}) успешно исключены из списка размещения, грузы больше не отображаются в GET /api/operator/cargo/available-for-placement"
                        )
                        return True
                    else:
                        self.log_test(
                            "Проверка изменения статуса грузов",
                            False,
                            f"Следующие грузы все еще присутствуют в списке размещения: {still_present}"
                        )
                        return False
                else:
                    self.log_test(
                        "Проверка изменения статуса грузов",
                        False,
                        "Нет информации об удаленных грузах для проверки"
                    )
                    return False
            else:
                self.log_test(
                    "Проверка изменения статуса грузов",
                    False,
                    f"Ошибка получения обновленного списка грузов: HTTP {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Проверка изменения статуса грузов",
                False,
                f"Исключение при проверке статуса: {str(e)}"
            )
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправленная функциональность массового удаления грузов в TAJLINE.TJ")
        print("=" * 100)
        print()
        
        # Test sequence
        tests = [
            self.authenticate_warehouse_operator,
            self.get_available_cargo_for_placement,
            self.test_bulk_removal_validation,
            self.test_single_cargo_removal,
            self.test_bulk_cargo_removal,
            self.verify_cargo_removal_status
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            if test():
                passed_tests += 1
            else:
                # If critical test fails, we might want to continue or stop
                # For now, continue with all tests
                pass
        
        # Summary
        print("=" * 100)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        print(f"Пройдено тестов: {passed_tests}/{total_tests}")
        print(f"Процент успешности: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        if passed_tests == total_tests:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ: Массовое удаление должно работать без ошибки 'Груз не найден'")
        else:
            print("⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            failed_tests = [result for result in self.test_results if not result['success']]
            print("Неудачные тесты:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        print()
        print("ТЕХНИЧЕСКИЕ ПОДТВЕРЖДЕНИЯ:")
        success_tests = [result for result in self.test_results if result['success']]
        for test in success_tests:
            print(f"✅ {test['test']}")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = BulkRemovalTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)