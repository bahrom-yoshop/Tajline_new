#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ДАННЫХ О ЗАНЯТОСТИ ЯЧЕЕК СКЛАДА "МОСКВА №1" В TAJLINE.TJ
=================================================================================

ПРОБЛЕМА:
- Карточка склада "Москва №1" показывает: "Занято 2 ячейки, загрузка 1.0%"
- Схема склада показывает: "Занято: 0, Свободно: 210"
- Есть несоответствие в данных между интерфейсами

ЗАДАЧИ ДЛЯ ПРОВЕРКИ:
1. Авторизация admin (+79999888777/admin123)
2. Найти склад "Москва №1" (вероятно первый в списке)
3. Получить warehouse_id для "Москва №1"
4. **КРИТИЧНО**: Проверить реальные данные о ячейках через GET /api/warehouses/{warehouse_id}/cells
5. Проверить статистику склада через GET /api/warehouses/{warehouse_id}/statistics
6. Найти реальное количество занятых ячеек (должно быть 2)
7. Определить, какие именно ячейки заняты (блок, полка, ячейка)

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
- API должен показать 2 занятые ячейки для склада "Москва №1"
- Нужно получить точные координаты занятых ячеек для исправления схемы
- Найти причину расхождения между карточкой (2 ячейки) и схемой (0 ячеек)

ФОКУС: Определить реальное количество занятых ячеек и их координаты для исправления схемы склада!
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BASE_URL = "https://qr-logistics-1.preview.emergentagent.com/api"
ADMIN_PHONE = "+79999888777"
ADMIN_PASSWORD = "admin123"

class WarehouseMoscow1Tester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.admin_user_info = None
        self.moscow_1_warehouse = None
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, details: str):
        """Логирование результатов тестирования"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}: {details}"
        self.test_results.append(result)
        print(result)
        
    def authenticate_admin(self):
        """Шаг 1: Авторизация администратора"""
        try:
            login_data = {
                "phone": ADMIN_PHONE,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                
                # Получаем информацию о пользователе
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                me_response = self.session.get(f"{BASE_URL}/auth/me", headers=headers)
                
                if me_response.status_code == 200:
                    self.admin_user_info = me_response.json()
                    user_role = self.admin_user_info.get("role")
                    user_name = self.admin_user_info.get("full_name")
                    user_number = self.admin_user_info.get("user_number")
                    
                    if user_role == "admin":
                        self.log_result(
                            "ADMIN AUTHENTICATION", 
                            True, 
                            f"Успешная авторизация администратора '{user_name}' (номер: {user_number}), роль: {user_role}"
                        )
                        return True
                    else:
                        self.log_result("ADMIN AUTHENTICATION", False, f"Неверная роль пользователя: {user_role}")
                        return False
                else:
                    self.log_result("ADMIN AUTHENTICATION", False, f"Ошибка получения данных пользователя: {me_response.status_code}")
                    return False
            else:
                self.log_result("ADMIN AUTHENTICATION", False, f"Ошибка авторизации: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("ADMIN AUTHENTICATION", False, f"Исключение при авторизации: {str(e)}")
            return False
    
    def find_moscow_1_warehouse(self):
        """Шаг 2-3: Найти склад "Москва №1" и получить его warehouse_id"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BASE_URL}/warehouses", headers=headers)
            
            if response.status_code == 200:
                warehouses = response.json()
                
                # Ищем склад "Москва №1"
                moscow_1_candidates = []
                
                for warehouse in warehouses:
                    name = warehouse.get("name", "").lower()
                    location = warehouse.get("location", "").lower()
                    
                    # Ищем склады с "москва" в названии или местоположении и "№1" или "1"
                    if ("москва" in name or "москва" in location) and ("№1" in warehouse.get("name", "") or "1" in warehouse.get("name", "")):
                        moscow_1_candidates.append(warehouse)
                
                if moscow_1_candidates:
                    # Берем первый найденный склад "Москва №1"
                    self.moscow_1_warehouse = moscow_1_candidates[0]
                    warehouse_name = self.moscow_1_warehouse.get("name")
                    warehouse_location = self.moscow_1_warehouse.get("location")
                    warehouse_id = self.moscow_1_warehouse.get("id")
                    
                    self.log_result(
                        "FIND MOSCOW №1 WAREHOUSE", 
                        True, 
                        f"Найден склад '{warehouse_name}' (ID: {warehouse_id}) в локации '{warehouse_location}'"
                    )
                    return True
                else:
                    # Если точного совпадения нет, ищем любой склад с "москва"
                    moscow_warehouses = [w for w in warehouses if "москва" in w.get("name", "").lower() or "москва" in w.get("location", "").lower()]
                    
                    if moscow_warehouses:
                        self.moscow_1_warehouse = moscow_warehouses[0]  # Берем первый московский склад
                        warehouse_name = self.moscow_1_warehouse.get("name")
                        warehouse_location = self.moscow_1_warehouse.get("location")
                        warehouse_id = self.moscow_1_warehouse.get("id")
                        
                        self.log_result(
                            "FIND MOSCOW №1 WAREHOUSE", 
                            True, 
                            f"Найден московский склад '{warehouse_name}' (ID: {warehouse_id}) в локации '{warehouse_location}' (возможно это 'Москва №1')"
                        )
                        return True
                    else:
                        self.log_result("FIND MOSCOW №1 WAREHOUSE", False, f"Склад 'Москва №1' не найден среди {len(warehouses)} складов")
                        return False
            else:
                self.log_result("FIND MOSCOW №1 WAREHOUSE", False, f"Ошибка получения списка складов: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("FIND MOSCOW №1 WAREHOUSE", False, f"Исключение при поиске склада: {str(e)}")
            return False
    
    def check_warehouse_cells_data(self):
        """Шаг 4: **КРИТИЧНО** Проверить реальные данные о ячейках через GET /api/warehouses/{warehouse_id}/cells"""
        try:
            warehouse_id = self.moscow_1_warehouse.get("id")
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            response = self.session.get(f"{BASE_URL}/warehouses/{warehouse_id}/cells", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                cells = data.get("cells", [])
                
                # Анализируем ячейки
                total_cells = len(cells)
                occupied_cells = [cell for cell in cells if cell.get("is_occupied", False)]
                occupied_count = len(occupied_cells)
                free_count = total_cells - occupied_count
                
                # Детали занятых ячеек
                occupied_details = []
                for cell in occupied_cells:
                    block = cell.get("block_number")
                    shelf = cell.get("shelf_number") 
                    cell_num = cell.get("cell_number")
                    cargo_id = cell.get("cargo_id")
                    occupied_details.append(f"Блок {block}, Полка {shelf}, Ячейка {cell_num} (груз: {cargo_id})")
                
                # Проверяем ожидаемое количество (2 ячейки)
                expected_occupied = 2
                is_correct = occupied_count == expected_occupied
                
                details = f"Всего ячеек: {total_cells}, Занято: {occupied_count}, Свободно: {free_count}"
                if occupied_details:
                    details += f". ЗАНЯТЫЕ ЯЧЕЙКИ: {'; '.join(occupied_details)}"
                
                if is_correct:
                    details += f" ✅ СООТВЕТСТВУЕТ ОЖИДАНИЯМ (ожидалось {expected_occupied} занятых ячеек)"
                else:
                    details += f" ⚠️ НЕ СООТВЕТСТВУЕТ ОЖИДАНИЯМ (ожидалось {expected_occupied}, найдено {occupied_count})"
                
                self.log_result("WAREHOUSE CELLS DATA CHECK", True, details)
                return True, occupied_count, occupied_details, total_cells
                
            else:
                self.log_result("WAREHOUSE CELLS DATA CHECK", False, f"Ошибка получения данных ячеек: {response.status_code} - {response.text}")
                return False, 0, [], 0
                
        except Exception as e:
            self.log_result("WAREHOUSE CELLS DATA CHECK", False, f"Исключение при проверке ячеек: {str(e)}")
            return False, 0, [], 0
    
    def check_warehouse_statistics(self):
        """Шаг 5: Проверить статистику склада через GET /api/warehouses/{warehouse_id}/statistics"""
        try:
            warehouse_id = self.moscow_1_warehouse.get("id")
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            response = self.session.get(f"{BASE_URL}/warehouses/{warehouse_id}/statistics", headers=headers)
            
            if response.status_code == 200:
                stats = response.json()
                
                total_cells = stats.get("total_cells", 0)
                occupied_cells = stats.get("occupied_cells", 0)
                free_cells = stats.get("free_cells", 0)
                utilization_percent = stats.get("utilization_percent", 0)
                
                # Проверяем математику
                calculated_free = total_cells - occupied_cells
                calculated_utilization = (occupied_cells / total_cells * 100) if total_cells > 0 else 0
                
                math_correct = (free_cells == calculated_free and 
                               abs(utilization_percent - calculated_utilization) < 0.1)
                
                details = f"Всего ячеек: {total_cells}, Занято: {occupied_cells}, Свободно: {free_cells}, Загрузка: {utilization_percent}%"
                
                if math_correct:
                    details += " ✅ МАТЕМАТИКА КОРРЕКТНА"
                else:
                    details += f" ⚠️ ОШИБКА В РАСЧЕТАХ (ожидалось свободно: {calculated_free}, загрузка: {calculated_utilization:.1f}%)"
                
                # Проверяем соответствие ожиданиям (2 ячейки, 1.0% загрузка)
                expected_occupied = 2
                expected_utilization = 1.0
                
                if occupied_cells == expected_occupied and abs(utilization_percent - expected_utilization) < 0.1:
                    details += f" ✅ СООТВЕТСТВУЕТ КАРТОЧКЕ СКЛАДА (2 ячейки, ~1.0%)"
                else:
                    details += f" ⚠️ НЕ СООТВЕТСТВУЕТ КАРТОЧКЕ (ожидалось {expected_occupied} ячеек, ~{expected_utilization}%)"
                
                self.log_result("WAREHOUSE STATISTICS CHECK", True, details)
                return True, stats
                
            else:
                self.log_result("WAREHOUSE STATISTICS CHECK", False, f"Ошибка получения статистики: {response.status_code} - {response.text}")
                return False, {}
                
        except Exception as e:
            self.log_result("WAREHOUSE STATISTICS CHECK", False, f"Исключение при проверке статистики: {str(e)}")
            return False, {}
    
    def analyze_discrepancy(self, cells_occupied_count, cells_details, stats_data):
        """Шаг 6-7: Анализ расхождений и определение причин"""
        try:
            stats_occupied = stats_data.get("occupied_cells", 0)
            
            # Сравниваем данные из разных источников
            discrepancy_found = cells_occupied_count != stats_occupied
            
            if discrepancy_found:
                details = f"НАЙДЕНО РАСХОЖДЕНИЕ: Cells API показывает {cells_occupied_count} занятых ячеек, Statistics API показывает {stats_occupied}"
                
                if cells_details:
                    details += f". Конкретные занятые ячейки: {'; '.join(cells_details)}"
                
                details += ". ТРЕБУЕТСЯ ИСПРАВЛЕНИЕ СХЕМЫ СКЛАДА!"
                
                self.log_result("DISCREPANCY ANALYSIS", False, details)
            else:
                details = f"Данные согласованы: оба API показывают {cells_occupied_count} занятых ячеек"
                
                if cells_details:
                    details += f". Занятые ячейки: {'; '.join(cells_details)}"
                
                # Проверяем соответствие ожиданиям
                if cells_occupied_count == 2:
                    details += " ✅ СООТВЕТСТВУЕТ ОЖИДАНИЯМ КАРТОЧКИ СКЛАДА"
                else:
                    details += f" ⚠️ НЕ СООТВЕТСТВУЕТ ОЖИДАНИЯМ (ожидалось 2 ячейки)"
                
                self.log_result("DISCREPANCY ANALYSIS", True, details)
            
            return True
            
        except Exception as e:
            self.log_result("DISCREPANCY ANALYSIS", False, f"Исключение при анализе расхождений: {str(e)}")
            return False
    
    def run_comprehensive_test(self):
        """Запуск полного тестирования"""
        print("🏭 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ДАННЫХ О ЗАНЯТОСТИ ЯЧЕЕК СКЛАДА 'МОСКВА №1' В TAJLINE.TJ")
        print("=" * 90)
        print(f"Время начала тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Шаг 1: Авторизация администратора
        if not self.authenticate_admin():
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
            return False
        
        # Шаг 2-3: Поиск склада "Москва №1"
        if not self.find_moscow_1_warehouse():
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось найти склад 'Москва №1'")
            return False
        
        # Шаг 4: Проверка данных ячеек
        cells_success, occupied_count, occupied_details, total_cells = self.check_warehouse_cells_data()
        if not cells_success:
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить данные о ячейках")
            return False
        
        # Шаг 5: Проверка статистики склада
        stats_success, stats_data = self.check_warehouse_statistics()
        if not stats_success:
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить статистику склада")
            return False
        
        # Шаг 6-7: Анализ расхождений
        if not self.analyze_discrepancy(occupied_count, occupied_details, stats_data):
            print("\n❌ ОШИБКА: Не удалось проанализировать расхождения")
            return False
        
        # Итоговый отчет
        print("\n" + "=" * 90)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 90)
        
        success_count = len([r for r in self.test_results if "✅ PASS" in r])
        total_count = len(self.test_results)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        print(f"Успешных тестов: {success_count}/{total_count} ({success_rate:.1f}%)")
        print()
        
        # Ключевые выводы
        print("🎯 КЛЮЧЕВЫЕ ВЫВОДЫ:")
        if self.moscow_1_warehouse:
            warehouse_name = self.moscow_1_warehouse.get("name")
            print(f"• Склад: {warehouse_name}")
            print(f"• Всего ячеек: {total_cells}")
            print(f"• Занято ячеек: {occupied_count}")
            
            if occupied_details:
                print("• Занятые ячейки:")
                for detail in occupied_details:
                    print(f"  - {detail}")
            
            # Рекомендации
            print("\n💡 РЕКОМЕНДАЦИИ:")
            if occupied_count == 2:
                print("✅ Данные соответствуют ожиданиям карточки склада (2 занятые ячейки)")
                print("✅ Схема склада должна отображать эти 2 занятые ячейки")
            else:
                print(f"⚠️ Найдено {occupied_count} занятых ячеек вместо ожидаемых 2")
                print("⚠️ Требуется проверка данных и исправление схемы")
        
        print(f"\nВремя завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return success_rate >= 80

def main():
    """Основная функция"""
    tester = WarehouseMoscow1Tester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            sys.exit(0)
        else:
            print("\n❌ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ОШИБКАМИ!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()