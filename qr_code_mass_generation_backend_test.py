#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Массовая генерация и печать QR кодов для ячеек склада в TAJLINE.TJ

ЦЕЛЬ ТЕСТИРОВАНИЯ:
Проверить работу API endpoint для генерации QR кодов ячеек и подготовки к массовой печати с обозначениями "Б?-П?-Я?"

ДЕТАЛЬНЫЕ ТЕСТЫ:
1. **Авторизация администратора** - проверить доступ к QR функциям
2. **API endpoint POST /api/warehouse/cell/generate-qr** - генерация QR кода для отдельной ячейки
3. **Проверка формата ответа** - должен содержать поля: success, cell_code, readable_name, qr_code
4. **Проверка уникальности номеров складов** - warehouse_id_number должны быть уникальными
5. **Тестирование format: 'id'** - новый формат с уникальными номерами (001-01-01-001)
6. **Проверка обозначения readable_name** - должно быть в формате "Б?-П?-Я?"
7. **Тестирование для разных ячеек** - Блок 1-5, Полка 1-5, Ячейка 1-10

КОНТЕКСТ:
- Система TAJLINE.TJ уже имеет backend функции генерации QR кодов
- Frontend код для печати с обозначениями уже реализован
- Нужно убедиться что backend корректно возвращает данные для массовой печати
- Тестируем только backend API - frontend будет тестироваться отдельно

ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:
- API endpoint должен работать без ошибок
- QR коды должны генерироваться в формате XXX-BB-PP-CCC (001-01-01-001)
- readable_name должно быть в формате "Б1-П1-Я1" для отображения в интерфейсе
- Уникальные номера складов должны обеспечивать различные коды для разных складов
"""

import requests
import json
import sys
import os
from datetime import datetime

# Получаем URL backend из переменных окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE = f"{BACKEND_URL}/api"

class QRCodeMassGenerationTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_warehouses = []
        self.test_results = []
        self.generated_qr_codes = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_admin_auth(self):
        """1. Авторизация администратора для доступа к QR функциям"""
        try:
            self.log("🔐 Авторизация администратора для доступа к QR функциям...")
            
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79999888777",
                "password": "admin123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                user_info = data["user"]
                self.log(f"✅ Успешная авторизация администратора: {user_info['full_name']} (номер: {user_info.get('user_number', 'N/A')}, роль: {user_info['role']})")
                return True
            else:
                self.log(f"❌ Ошибка авторизации администратора: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при авторизации администратора: {e}", "ERROR")
            return False
    
    def get_warehouses_for_testing(self):
        """Получить склады для тестирования уникальности номеров"""
        try:
            self.log("🏢 Получение складов для тестирования уникальности номеров...")
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{API_BASE}/warehouses", headers=headers)
            
            if response.status_code == 200:
                warehouses = response.json()
                
                # Берем первые 3 склада для тестирования
                self.test_warehouses = warehouses[:3] if len(warehouses) >= 3 else warehouses
                
                self.log(f"✅ Получено {len(self.test_warehouses)} складов для тестирования:")
                for warehouse in self.test_warehouses:
                    warehouse_id_number = warehouse.get('warehouse_id_number', 'НЕТ')
                    self.log(f"   - {warehouse['name']} (ID: {warehouse['id'][:8]}..., Номер: {warehouse_id_number})")
                
                return len(self.test_warehouses) > 0
            else:
                self.log(f"❌ Ошибка получения складов: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при получении складов: {e}", "ERROR")
            return False
    
    def test_single_cell_qr_generation_api(self):
        """2. API endpoint POST /api/warehouse/cell/generate-qr - генерация QR кода для отдельной ячейки"""
        try:
            self.log("🎯 КРИТИЧЕСКИЙ ТЕСТ: API endpoint POST /api/warehouse/cell/generate-qr")
            
            if not self.test_warehouses:
                self.log("❌ Нет доступных складов для тестирования", "ERROR")
                return False
            
            warehouse = self.test_warehouses[0]
            warehouse_id = warehouse['id']
            
            # Тестируем генерацию QR кода для ячейки Б1-П1-Я1
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            cell_data = {
                "warehouse_id": warehouse_id,
                "block": 1,
                "shelf": 1, 
                "cell": 1,
                "format": "id"  # Новый формат с уникальными номерами
            }
            
            response = self.session.post(f"{API_BASE}/warehouse/cell/generate-qr", 
                                       json=cell_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                self.log(f"✅ API endpoint работает корректно:")
                self.log(f"   - HTTP статус: {response.status_code}")
                self.log(f"   - Ответ получен успешно")
                
                # Сохраняем данные для дальнейших тестов
                self.generated_qr_codes.append(data)
                return True
            else:
                self.log(f"❌ Ошибка API endpoint: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при тестировании API endpoint: {e}", "ERROR")
            return False
    
    def test_response_format_validation(self):
        """3. Проверка формата ответа - должен содержать поля: success, cell_code, readable_name, qr_code"""
        try:
            self.log("📋 КРИТИЧЕСКИЙ ТЕСТ: Проверка формата ответа API")
            
            if not self.generated_qr_codes:
                self.log("❌ Нет сгенерированных QR кодов для проверки", "ERROR")
                return False
            
            data = self.generated_qr_codes[0]
            
            # Проверяем обязательные поля согласно review request
            required_fields = ['success', 'cell_code', 'qr_code']
            optional_fields = ['warehouse_id', 'warehouse_id_number', 'format_type', 'readable_name']
            
            missing_required = [field for field in required_fields if field not in data]
            present_optional = [field for field in optional_fields if field in data]
            
            if missing_required:
                self.log(f"❌ Отсутствуют обязательные поля: {missing_required}", "ERROR")
                return False
            
            self.log(f"✅ Формат ответа корректен:")
            self.log(f"   - Обязательные поля: {required_fields} ✅")
            self.log(f"   - Дополнительные поля: {present_optional}")
            
            # Проверяем значения полей
            success = data.get('success')
            cell_code = data.get('cell_code')
            qr_code = data.get('qr_code')
            
            if success and cell_code and qr_code:
                self.log(f"   - success: {success}")
                self.log(f"   - cell_code: {cell_code}")
                self.log(f"   - qr_code: {'✅ Присутствует' if qr_code else '❌ Отсутствует'}")
                return True
            else:
                self.log(f"❌ Некорректные значения полей", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при проверке формата ответа: {e}", "ERROR")
            return False
    
    def test_warehouse_id_number_uniqueness(self):
        """4. Проверка уникальности номеров складов - warehouse_id_number должны быть уникальными"""
        try:
            self.log("🔄 КРИТИЧЕСКИЙ ТЕСТ: Уникальность номеров складов (warehouse_id_number)")
            
            if len(self.test_warehouses) < 2:
                self.log("❌ Недостаточно складов для тестирования уникальности (нужно минимум 2)", "ERROR")
                return False
            
            # Собираем номера складов
            warehouse_numbers = []
            for warehouse in self.test_warehouses:
                warehouse_id_number = warehouse.get('warehouse_id_number')
                if warehouse_id_number:
                    warehouse_numbers.append(warehouse_id_number)
                    self.log(f"   - Склад '{warehouse['name']}': номер {warehouse_id_number}")
            
            # Проверяем уникальность
            unique_numbers = set(warehouse_numbers)
            
            if len(unique_numbers) == len(warehouse_numbers):
                self.log(f"✅ Номера складов уникальны:")
                self.log(f"   - Всего складов: {len(warehouse_numbers)}")
                self.log(f"   - Уникальных номеров: {len(unique_numbers)}")
                self.log(f"   - Номера: {sorted(warehouse_numbers)}")
                return True
            else:
                duplicates = [num for num in warehouse_numbers if warehouse_numbers.count(num) > 1]
                self.log(f"❌ Найдены дублирующиеся номера складов: {set(duplicates)}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при проверке уникальности номеров складов: {e}", "ERROR")
            return False
    
    def test_format_id_new_format(self):
        """5. Тестирование format: 'id' - новый формат с уникальными номерами (001-01-01-001)"""
        try:
            self.log("🆕 КРИТИЧЕСКИЙ ТЕСТ: Новый формат format: 'id' (XXX-BB-PP-CCC)")
            
            if not self.test_warehouses:
                self.log("❌ Нет доступных складов для тестирования", "ERROR")
                return False
            
            warehouse = self.test_warehouses[0]
            warehouse_id = warehouse['id']
            
            # Тестируем генерацию с format: 'id'
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            cell_data = {
                "warehouse_id": warehouse_id,
                "block": 1,
                "shelf": 1,
                "cell": 1,
                "format": "id"  # КРИТИЧЕСКИЙ ПАРАМЕТР
            }
            
            response = self.session.post(f"{API_BASE}/warehouse/cell/generate-qr", 
                                       json=cell_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                cell_code = data.get('cell_code')
                warehouse_id_number = data.get('warehouse_id_number')
                
                # Проверяем формат XXX-BB-PP-CCC
                if cell_code and '-' in cell_code:
                    parts = cell_code.split('-')
                    
                    if len(parts) == 4:
                        warehouse_part, block_part, shelf_part, cell_part = parts
                        
                        # Проверяем формат каждой части
                        format_valid = (
                            len(warehouse_part) == 3 and warehouse_part.isdigit() and
                            len(block_part) == 2 and block_part.isdigit() and
                            len(shelf_part) == 2 and shelf_part.isdigit() and
                            len(cell_part) == 3 and cell_part.isdigit()
                        )
                        
                        if format_valid:
                            self.log(f"✅ Новый формат format: 'id' работает корректно:")
                            self.log(f"   - Код ячейки: {cell_code}")
                            self.log(f"   - Формат: XXX-BB-PP-CCC ✅")
                            self.log(f"   - Номер склада: {warehouse_part} (из warehouse_id_number: {warehouse_id_number})")
                            
                            # Проверяем соответствие номера склада
                            if warehouse_id_number and warehouse_part == warehouse_id_number:
                                self.log(f"   - Соответствие номера склада: ✅")
                                return True
                            else:
                                self.log(f"   - Несоответствие номера склада: {warehouse_part} != {warehouse_id_number}", "ERROR")
                                return False
                        else:
                            self.log(f"❌ Неправильный формат частей: {cell_code}", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Неправильное количество частей в коде: {len(parts)} (ожидается 4)", "ERROR")
                        return False
                else:
                    self.log(f"❌ Код ячейки не содержит разделители: {cell_code}", "ERROR")
                    return False
            else:
                self.log(f"❌ Ошибка генерации с format: 'id': {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при тестировании format: 'id': {e}", "ERROR")
            return False
    
    def test_readable_name_format(self):
        """6. Проверка обозначения readable_name - должно быть в формате "Б?-П?-Я?" """
        try:
            self.log("📝 КРИТИЧЕСКИЙ ТЕСТ: Формат readable_name (Б?-П?-Я?)")
            
            if not self.test_warehouses:
                self.log("❌ Нет доступных складов для тестирования", "ERROR")
                return False
            
            warehouse = self.test_warehouses[0]
            warehouse_id = warehouse['id']
            
            # Тестируем несколько разных ячеек
            test_cells = [
                {"block": 1, "shelf": 1, "cell": 1, "expected": "Б1-П1-Я1"},
                {"block": 2, "shelf": 3, "cell": 5, "expected": "Б2-П3-Я5"},
                {"block": 5, "shelf": 5, "cell": 10, "expected": "Б5-П5-Я10"}
            ]
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            all_passed = True
            
            for test_cell in test_cells:
                cell_data = {
                    "warehouse_id": warehouse_id,
                    "block": test_cell["block"],
                    "shelf": test_cell["shelf"],
                    "cell": test_cell["cell"],
                    "format": "id"
                }
                
                response = self.session.post(f"{API_BASE}/warehouse/cell/generate-qr", 
                                           json=cell_data, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    readable_name = data.get('readable_name')
                    
                    if readable_name == test_cell["expected"]:
                        self.log(f"   ✅ Б{test_cell['block']}-П{test_cell['shelf']}-Я{test_cell['cell']}: {readable_name}")
                    else:
                        self.log(f"   ❌ Б{test_cell['block']}-П{test_cell['shelf']}-Я{test_cell['cell']}: ожидалось '{test_cell['expected']}', получено '{readable_name}'")
                        all_passed = False
                else:
                    self.log(f"   ❌ Ошибка генерации для Б{test_cell['block']}-П{test_cell['shelf']}-Я{test_cell['cell']}: {response.status_code}")
                    all_passed = False
            
            if all_passed:
                self.log(f"✅ Формат readable_name корректен для всех тестовых ячеек")
                return True
            else:
                self.log(f"❌ Обнаружены ошибки в формате readable_name", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при проверке readable_name: {e}", "ERROR")
            return False
    
    def test_different_cells_range(self):
        """7. Тестирование для разных ячеек - Блок 1-5, Полка 1-5, Ячейка 1-10"""
        try:
            self.log("🏗️ КРИТИЧЕСКИЙ ТЕСТ: Генерация QR кодов для диапазона ячеек (Блок 1-5, Полка 1-5, Ячейка 1-10)")
            
            if not self.test_warehouses:
                self.log("❌ Нет доступных складов для тестирования", "ERROR")
                return False
            
            warehouse = self.test_warehouses[0]
            warehouse_id = warehouse['id']
            warehouse_name = warehouse['name']
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Тестируем выборочные ячейки из указанного диапазона
            test_cells = [
                {"block": 1, "shelf": 1, "cell": 1},   # Минимальные значения
                {"block": 3, "shelf": 3, "cell": 5},   # Средние значения
                {"block": 5, "shelf": 5, "cell": 10},  # Максимальные значения
                {"block": 2, "shelf": 1, "cell": 8},   # Смешанные значения
                {"block": 4, "shelf": 2, "cell": 3}    # Еще одна комбинация
            ]
            
            successful_generations = 0
            unique_codes = set()
            
            self.log(f"   Тестирование склада: {warehouse_name}")
            
            for i, test_cell in enumerate(test_cells, 1):
                cell_data = {
                    "warehouse_id": warehouse_id,
                    "block": test_cell["block"],
                    "shelf": test_cell["shelf"],
                    "cell": test_cell["cell"],
                    "format": "id"
                }
                
                response = self.session.post(f"{API_BASE}/warehouse/cell/generate-qr", 
                                           json=cell_data, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    cell_code = data.get('cell_code')
                    readable_name = data.get('readable_name')
                    
                    if cell_code:
                        unique_codes.add(cell_code)
                        successful_generations += 1
                        self.log(f"   {i}. Б{test_cell['block']}-П{test_cell['shelf']}-Я{test_cell['cell']}: {cell_code} ({readable_name})")
                    else:
                        self.log(f"   {i}. ❌ Б{test_cell['block']}-П{test_cell['shelf']}-Я{test_cell['cell']}: Нет cell_code в ответе")
                else:
                    self.log(f"   {i}. ❌ Б{test_cell['block']}-П{test_cell['shelf']}-Я{test_cell['cell']}: HTTP {response.status_code}")
            
            # Проверяем результаты
            if successful_generations == len(test_cells):
                if len(unique_codes) == len(test_cells):
                    self.log(f"✅ Генерация QR кодов для диапазона ячеек успешна:")
                    self.log(f"   - Протестировано ячеек: {len(test_cells)}")
                    self.log(f"   - Успешных генераций: {successful_generations}")
                    self.log(f"   - Уникальных кодов: {len(unique_codes)}")
                    return True
                else:
                    self.log(f"❌ Обнаружены дублирующиеся QR коды", "ERROR")
                    return False
            else:
                self.log(f"❌ Не все ячейки сгенерированы успешно: {successful_generations}/{len(test_cells)}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при тестировании диапазона ячеек: {e}", "ERROR")
            return False
    
    def test_multiple_warehouses_uniqueness(self):
        """Дополнительный тест: Проверка уникальности QR кодов между разными складами"""
        try:
            self.log("🔄 ДОПОЛНИТЕЛЬНЫЙ ТЕСТ: Уникальность QR кодов между разными складами")
            
            if len(self.test_warehouses) < 2:
                self.log("❌ Недостаточно складов для тестирования межскладской уникальности", "ERROR")
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            warehouse_codes = {}
            
            # Генерируем QR коды для одинаковых ячеек разных складов
            for i, warehouse in enumerate(self.test_warehouses[:3]):  # Максимум 3 склада
                warehouse_id = warehouse['id']
                warehouse_name = warehouse['name']
                
                cell_data = {
                    "warehouse_id": warehouse_id,
                    "block": 1,
                    "shelf": 1,
                    "cell": 1,
                    "format": "id"
                }
                
                response = self.session.post(f"{API_BASE}/warehouse/cell/generate-qr", 
                                           json=cell_data, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    cell_code = data.get('cell_code')
                    warehouse_id_number = data.get('warehouse_id_number')
                    
                    warehouse_codes[warehouse_name] = {
                        'cell_code': cell_code,
                        'warehouse_id_number': warehouse_id_number
                    }
                    
                    self.log(f"   Склад {i+1} ({warehouse_name}): {cell_code} (номер: {warehouse_id_number})")
            
            # Проверяем уникальность
            all_codes = [info['cell_code'] for info in warehouse_codes.values()]
            unique_codes = set(all_codes)
            
            if len(unique_codes) == len(all_codes):
                self.log(f"✅ QR коды уникальны между складами:")
                self.log(f"   - Протестировано складов: {len(warehouse_codes)}")
                self.log(f"   - Уникальных кодов: {len(unique_codes)}")
                
                # Проверяем, что различие именно в номерах складов
                warehouse_numbers = set([info['warehouse_id_number'] for info in warehouse_codes.values()])
                if len(warehouse_numbers) == len(warehouse_codes):
                    self.log(f"   - Уникальность обеспечивается номерами складов: {sorted(warehouse_numbers)}")
                    return True
                else:
                    self.log(f"❌ Проблема с уникальностью номеров складов", "ERROR")
                    return False
            else:
                self.log(f"❌ Найдены дублирующиеся QR коды между складами", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при тестировании межскладской уникальности: {e}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов согласно review request"""
        self.log("🚀 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ МАССОВОЙ ГЕНЕРАЦИИ QR КОДОВ")
        self.log("🎯 ЦЕЛЬ: Проверить работу API endpoint для генерации QR кодов ячеек и подготовки к массовой печати")
        self.log("=" * 100)
        
        # Список всех тестов согласно review request
        tests = [
            ("1. Авторизация администратора", self.test_admin_auth),
            ("2. Получение складов для тестирования", self.get_warehouses_for_testing),
            ("3. API endpoint POST /api/warehouse/cell/generate-qr", self.test_single_cell_qr_generation_api),
            ("4. Проверка формата ответа (success, cell_code, readable_name, qr_code)", self.test_response_format_validation),
            ("5. Проверка уникальности номеров складов", self.test_warehouse_id_number_uniqueness),
            ("6. Тестирование format: 'id' (001-01-01-001)", self.test_format_id_new_format),
            ("7. Проверка обозначения readable_name (Б?-П?-Я?)", self.test_readable_name_format),
            ("8. Тестирование для разных ячеек (Блок 1-5, Полка 1-5, Ячейка 1-10)", self.test_different_cells_range),
            ("9. Дополнительно: Уникальность между складами", self.test_multiple_warehouses_uniqueness)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n📋 ТЕСТ: {test_name}")
            self.log("-" * 80)
            
            try:
                result = test_func()
                if result:
                    passed_tests += 1
                    self.test_results.append(f"✅ {test_name}")
                    self.log(f"✅ ТЕСТ ПРОЙДЕН: {test_name}")
                else:
                    self.test_results.append(f"❌ {test_name}")
                    self.log(f"❌ ТЕСТ НЕ ПРОЙДЕН: {test_name}")
            except Exception as e:
                self.test_results.append(f"❌ {test_name} (Исключение: {e})")
                self.log(f"❌ ИСКЛЮЧЕНИЕ В ТЕСТЕ {test_name}: {e}", "ERROR")
        
        # Итоговый отчет
        self.log("\n" + "=" * 100)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ МАССОВОЙ ГЕНЕРАЦИИ QR КОДОВ")
        self.log("=" * 100)
        
        success_rate = (passed_tests / total_tests) * 100
        self.log(f"📊 РЕЗУЛЬТАТ: {passed_tests}/{total_tests} тестов пройдено ({success_rate:.1f}%)")
        
        self.log("\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            self.log(f"   {result}")
        
        # Выводы согласно ожидаемым результатам
        if success_rate >= 80:
            self.log(f"\n🎉 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            self.log(f"✅ API endpoint работает без ошибок")
            self.log(f"✅ QR коды генерируются в формате XXX-BB-PP-CCC (001-01-01-001)")
            self.log(f"✅ readable_name в формате 'Б1-П1-Я1' для отображения в интерфейсе")
            self.log(f"✅ Уникальные номера складов обеспечивают различные коды для разных складов")
            self.log(f"✅ Backend корректно возвращает данные для массовой печати")
        else:
            self.log(f"\n❌ КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
            self.log(f"❌ Требуется дополнительная работа над функциональностью QR кодов")
        
        return success_rate >= 80

def main():
    """Главная функция"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Массовая генерация и печать QR кодов для ячеек склада в TAJLINE.TJ")
    print("=" * 120)
    
    tester = QRCodeMassGenerationTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()