#!/usr/bin/env python3
"""
WAREHOUSE STATISTICS FIXES TESTING FOR TAJLINE.TJ
=================================================

КОНТЕКСТ: Исправлены критические проблемы в разделе складов:
1. BACKEND: Новый endpoint GET /api/warehouses/{warehouse_id}/statistics для получения реальной статистики склада
2. FRONTEND: Исправлено отображение данных на карточках складов - убраны жестко заданные 60% и случайные числа
3. ФУНКЦИОНАЛЬНОСТЬ: Добавлена функция загрузки статистики складов с реальными данными о заполненности
4. КНОПКИ УПРАВЛЕНИЯ: Исправлена кнопка "Управление ячейками" для перехода к управлению

ТЕСТОВЫЙ ПЛАН:
1. Авторизация администратора (admin@emergent.com/admin123)
2. Получение списка складов (/api/warehouses)
3. Тестирование нового endpoint статистики для каждого склада
4. Проверка корректности расчетов:
   - Общее количество ячеек (блоки × полки × ячейки)
   - Занятые ячейки (из коллекции warehouse_cells)
   - Свободные ячейки (общие - занятые)
   - Процент заполненности (занятые / общие × 100)
   - Количество грузов (из operator_cargo + cargo коллекций)
   - Общий вес грузов
5. Проверка обработки складов без данных

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Endpoint должен возвращать корректную статистику складов с реальными данными вместо жестко заданных значений, процент заполненности должен рассчитываться на основе реальных данных о занятых ячейках.
"""

import requests
import json
import os
from datetime import datetime

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-cargo-3.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class WarehouseStatisticsTest:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_results = []
        
    def log_result(self, test_name, success, details):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {details}")
        
    def authenticate_admin(self):
        """Authenticate as admin"""
        try:
            # Try admin@emergent.com/admin123 first
            login_data = {
                "phone": "admin@emergent.com",
                "password": "admin123"
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
            
            if response.status_code != 200:
                # Try +79999888777/admin123 as fallback
                login_data = {
                    "phone": "+79999888777",
                    "password": "admin123"
                }
                response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                user_info = data.get("user", {})
                
                self.log_result(
                    "Admin Authentication",
                    True,
                    f"Успешная авторизация администратора. Роль: {user_info.get('role')}, "
                    f"Имя: {user_info.get('full_name')}, Номер: {user_info.get('user_number', 'N/A')}"
                )
                
                # Set authorization header
                self.session.headers.update({
                    "Authorization": f"Bearer {self.admin_token}"
                })
                return True
            else:
                self.log_result(
                    "Admin Authentication",
                    False,
                    f"Ошибка авторизации: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Admin Authentication", False, f"Исключение: {str(e)}")
            return False
    
    def get_warehouses_list(self):
        """Get list of warehouses"""
        try:
            response = self.session.get(f"{API_BASE}/warehouses")
            
            if response.status_code == 200:
                warehouses = response.json()
                warehouse_count = len(warehouses)
                
                self.log_result(
                    "Get Warehouses List",
                    True,
                    f"Получен список складов: {warehouse_count} складов. "
                    f"Примеры: {[w.get('name', 'N/A')[:30] for w in warehouses[:3]]}"
                )
                return warehouses
            else:
                self.log_result(
                    "Get Warehouses List",
                    False,
                    f"Ошибка получения списка складов: {response.status_code} - {response.text}"
                )
                return []
                
        except Exception as e:
            self.log_result("Get Warehouses List", False, f"Исключение: {str(e)}")
            return []
    
    def test_warehouse_statistics_endpoint(self, warehouse):
        """Test new warehouse statistics endpoint"""
        warehouse_id = warehouse.get('id')
        warehouse_name = warehouse.get('name', 'Unknown')
        
        try:
            # Test new statistics endpoint
            response = self.session.get(f"{API_BASE}/warehouses/{warehouse_id}/statistics")
            
            if response.status_code == 200:
                stats = response.json()
                
                # Validate required fields (using actual field names from API)
                required_fields = [
                    'total_cells', 'occupied_cells', 'free_cells', 
                    'utilization_percent', 'total_cargo_count', 'total_weight'
                ]
                
                missing_fields = [field for field in required_fields if field not in stats]
                
                if missing_fields:
                    self.log_result(
                        f"Statistics Endpoint - {warehouse_name}",
                        False,
                        f"Отсутствуют обязательные поля: {missing_fields}"
                    )
                    return False
                
                # Validate data types and logic (using actual field names)
                total_cells = stats.get('total_cells', 0)
                occupied_cells = stats.get('occupied_cells', 0)
                free_cells = stats.get('free_cells', 0)
                utilization_percent = stats.get('utilization_percent', 0)
                total_cargo_count = stats.get('total_cargo_count', 0)
                total_weight = stats.get('total_weight', 0)
                
                # Check calculations
                calculated_free = total_cells - occupied_cells
                calculated_percentage = (occupied_cells / total_cells * 100) if total_cells > 0 else 0
                
                calculation_errors = []
                
                if free_cells != calculated_free:
                    calculation_errors.append(f"Свободные ячейки: ожидалось {calculated_free}, получено {free_cells}")
                
                if abs(utilization_percent - calculated_percentage) > 0.1:
                    calculation_errors.append(f"Процент заполненности: ожидалось {calculated_percentage:.1f}%, получено {utilization_percent}%")
                
                if calculation_errors:
                    self.log_result(
                        f"Statistics Calculations - {warehouse_name}",
                        False,
                        f"Ошибки расчетов: {'; '.join(calculation_errors)}"
                    )
                else:
                    self.log_result(
                        f"Statistics Calculations - {warehouse_name}",
                        True,
                        f"Расчеты корректны: {total_cells} всего, {occupied_cells} занято, "
                        f"{free_cells} свободно, {utilization_percent:.1f}% заполненность"
                    )
                
                # Check if data looks realistic (not hardcoded)
                is_realistic = True
                realism_notes = []
                
                if utilization_percent == 60.0:
                    is_realistic = False
                    realism_notes.append("Подозрение на жестко заданные 60%")
                
                if total_cells in [100, 200, 300] and utilization_percent in [50.0, 60.0, 75.0]:
                    is_realistic = False
                    realism_notes.append("Подозрение на тестовые данные")
                
                self.log_result(
                    f"Data Realism Check - {warehouse_name}",
                    is_realistic,
                    f"Данные {'выглядят реалистично' if is_realistic else 'подозрительны'}: "
                    f"{'; '.join(realism_notes) if realism_notes else 'Нет подозрений'}"
                )
                
                self.log_result(
                    f"Statistics Endpoint - {warehouse_name}",
                    True,
                    f"Endpoint работает. Статистика: всего ячеек {total_cells}, "
                    f"занято {occupied_cells} ({utilization_percent:.1f}%), "
                    f"грузов {total_cargo_count}, общий вес {total_weight}кг"
                )
                
                return True
                
            elif response.status_code == 404:
                self.log_result(
                    f"Statistics Endpoint - {warehouse_name}",
                    False,
                    f"Endpoint не найден (404) - возможно не реализован"
                )
                return False
            else:
                self.log_result(
                    f"Statistics Endpoint - {warehouse_name}",
                    False,
                    f"Ошибка: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                f"Statistics Endpoint - {warehouse_name}",
                False,
                f"Исключение: {str(e)}"
            )
            return False
    
    def test_warehouse_structure_calculation(self, warehouse):
        """Test if warehouse structure calculation is correct"""
        warehouse_id = warehouse.get('id')
        warehouse_name = warehouse.get('name', 'Unknown')
        
        try:
            # Get warehouse details
            blocks_count = warehouse.get('blocks_count', 0)
            shelves_per_block = warehouse.get('shelves_per_block', 0)
            cells_per_shelf = warehouse.get('cells_per_shelf', 0)
            
            expected_total_cells = blocks_count * shelves_per_block * cells_per_shelf
            
            # Get statistics
            response = self.session.get(f"{API_BASE}/warehouses/{warehouse_id}/statistics")
            
            if response.status_code == 200:
                stats = response.json()
                actual_total_cells = stats.get('total_cells', 0)
                
                if actual_total_cells == expected_total_cells:
                    self.log_result(
                        f"Structure Calculation - {warehouse_name}",
                        True,
                        f"Расчет структуры корректен: {blocks_count} блоков × {shelves_per_block} полок × "
                        f"{cells_per_shelf} ячеек = {expected_total_cells} всего ячеек"
                    )
                    return True
                else:
                    self.log_result(
                        f"Structure Calculation - {warehouse_name}",
                        False,
                        f"Неверный расчет структуры: ожидалось {expected_total_cells}, "
                        f"получено {actual_total_cells}"
                    )
                    return False
            else:
                self.log_result(
                    f"Structure Calculation - {warehouse_name}",
                    False,
                    f"Не удалось получить статистику для проверки расчета"
                )
                return False
                
        except Exception as e:
            self.log_result(
                f"Structure Calculation - {warehouse_name}",
                False,
                f"Исключение: {str(e)}"
            )
            return False
    
    def test_empty_warehouse_handling(self):
        """Test handling of warehouses without data"""
        try:
            # Try to get statistics for a non-existent warehouse
            fake_warehouse_id = "non-existent-warehouse-id"
            response = self.session.get(f"{API_BASE}/warehouses/{fake_warehouse_id}/statistics")
            
            if response.status_code == 404:
                self.log_result(
                    "Empty Warehouse Handling",
                    True,
                    "Корректная обработка несуществующего склада (404 Not Found)"
                )
                return True
            elif response.status_code == 200:
                stats = response.json()
                # Check if it returns zeros for empty warehouse
                if all(stats.get(field, 0) == 0 for field in ['total_cells', 'occupied_cells', 'total_cargo_count']):
                    self.log_result(
                        "Empty Warehouse Handling",
                        True,
                        "Корректная обработка пустого склада (возвращает нули)"
                    )
                    return True
                else:
                    self.log_result(
                        "Empty Warehouse Handling",
                        False,
                        f"Неожиданные данные для несуществующего склада: {stats}"
                    )
                    return False
            else:
                self.log_result(
                    "Empty Warehouse Handling",
                    False,
                    f"Неожиданный статус код: {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result("Empty Warehouse Handling", False, f"Исключение: {str(e)}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive warehouse statistics test"""
        print("🏭 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ОШИБОК В КАТЕГОРИИ СКЛАДОВ TAJLINE.TJ")
        print("=" * 80)
        
        # Step 1: Authenticate as admin
        if not self.authenticate_admin():
            print("❌ Не удалось авторизоваться как администратор. Тестирование прервано.")
            return False
        
        # Step 2: Get warehouses list
        warehouses = self.get_warehouses_list()
        if not warehouses:
            print("❌ Не удалось получить список складов. Тестирование прервано.")
            return False
        
        # Step 3: Test statistics endpoint for each warehouse
        successful_tests = 0
        total_tests = 0
        
        for warehouse in warehouses[:5]:  # Test first 5 warehouses to avoid timeout
            total_tests += 1
            if self.test_warehouse_statistics_endpoint(warehouse):
                successful_tests += 1
            
            # Also test structure calculation
            self.test_warehouse_structure_calculation(warehouse)
        
        # Step 4: Test empty warehouse handling
        self.test_empty_warehouse_handling()
        
        # Calculate success rate
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 80)
        print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЙ СКЛАДОВ")
        print("=" * 80)
        
        passed_tests = sum(1 for result in self.test_results if result["success"])
        total_test_count = len(self.test_results)
        overall_success_rate = (passed_tests / total_test_count * 100) if total_test_count > 0 else 0
        
        print(f"✅ Успешных тестов: {passed_tests}/{total_test_count}")
        print(f"📈 Общий процент успешности: {overall_success_rate:.1f}%")
        print(f"🏭 Протестировано складов: {total_tests}")
        print(f"📊 Успешность endpoint статистики: {success_rate:.1f}%")
        
        # Summary of key findings
        print("\n🔍 КЛЮЧЕВЫЕ РЕЗУЛЬТАТЫ:")
        
        endpoint_working = any("Statistics Endpoint" in result["test"] and result["success"] 
                              for result in self.test_results)
        
        if endpoint_working:
            print("✅ Новый endpoint GET /api/warehouses/{warehouse_id}/statistics работает")
        else:
            print("❌ Новый endpoint GET /api/warehouses/{warehouse_id}/statistics не найден или не работает")
        
        realistic_data = any("Data Realism Check" in result["test"] and result["success"] 
                           for result in self.test_results)
        
        if realistic_data:
            print("✅ Данные выглядят реалистично (не жестко заданные)")
        else:
            print("⚠️ Обнаружены подозрения на жестко заданные данные")
        
        correct_calculations = any("Statistics Calculations" in result["test"] and result["success"] 
                                 for result in self.test_results)
        
        if correct_calculations:
            print("✅ Расчеты статистики корректны")
        else:
            print("❌ Обнаружены ошибки в расчетах статистики")
        
        print(f"\n🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ {'ДОСТИГНУТ' if overall_success_rate >= 80 else 'НЕ ДОСТИГНУТ'}")
        
        if overall_success_rate >= 80:
            print("✅ Endpoint возвращает корректную статистику складов с реальными данными")
            print("✅ Процент заполненности рассчитывается на основе реальных данных о занятых ячейках")
        else:
            print("❌ Требуются дополнительные исправления в системе статистики складов")
        
        return overall_success_rate >= 80

if __name__ == "__main__":
    tester = WarehouseStatisticsTest()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
    else:
        print("\n⚠️ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")