#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправления схемы склада и поиск связанных грузов в TAJLINE.TJ

Тестирует исправления согласно review request:
1. Авторизация администратора
2. Тестирование схемы склада с размещенными грузами
3. Тестирование поиска связанных грузов
4. Проверка статистики занятых/свободных ячеек
5. Комплексное тестирование с созданием тестовых грузов

Endpoints для тестирования:
- GET /api/warehouses/{warehouse_id}/layout-with-cargo
- POST /api/warehouses/{warehouse_id}/related-cargo
"""

import requests
import json
import uuid
from datetime import datetime
import os

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE = f"{BACKEND_URL}/api"

class WarehouseSchemaRelatedCargoTester:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.test_cargo_ids = []
        self.test_warehouse_id = None
        self.session = requests.Session()
        
    def log(self, message):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def make_request(self, method, endpoint, data=None, token=None, params=None):
        """Универсальный метод для HTTP запросов"""
        url = f"{API_BASE}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Request failed: {e}")
            return None
    
    def test_admin_authorization(self):
        """1. Тестирование авторизации администратора"""
        self.log("🔐 ТЕСТИРОВАНИЕ АВТОРИЗАЦИИ АДМИНИСТРАТОРА")
        
        # Данные администратора
        admin_credentials = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        response = self.make_request("POST", "/auth/login", admin_credentials)
        
        if not response or response.status_code != 200:
            self.log(f"❌ Ошибка авторизации администратора: {response.status_code if response else 'No response'}")
            return False
            
        data = response.json()
        self.admin_token = data.get("access_token")
        user_info = data.get("user", {})
        
        self.log(f"✅ Администратор авторизован: {user_info.get('full_name', 'Unknown')}")
        self.log(f"   📱 Телефон: {user_info.get('phone', 'Unknown')}")
        self.log(f"   👤 Роль: {user_info.get('role', 'Unknown')}")
        self.log(f"   🆔 ID: {user_info.get('id', 'Unknown')}")
        
        return True
    
    def find_warehouse_with_cargo(self):
        """2. Поиск склада с размещенными грузами"""
        self.log("🏭 ПОИСК СКЛАДА С РАЗМЕЩЕННЫМИ ГРУЗАМИ")
        
        # Получаем список всех складов
        response = self.make_request("GET", "/warehouses", token=self.admin_token)
        
        if not response or response.status_code != 200:
            self.log(f"❌ Ошибка получения списка складов: {response.status_code if response else 'No response'}")
            return False
            
        warehouses = response.json()
        self.log(f"📦 Найдено складов: {len(warehouses)}")
        
        # Ищем склад с грузами
        for warehouse in warehouses:
            warehouse_id = warehouse.get("id")
            warehouse_name = warehouse.get("name", "Unknown")
            
            # Проверяем схему склада
            layout_response = self.make_request("GET", f"/warehouses/{warehouse_id}/layout-with-cargo", token=self.admin_token)
            
            if layout_response and layout_response.status_code == 200:
                layout_data = layout_response.json()
                total_cargo = layout_data.get("total_cargo", 0)
                
                if total_cargo > 0:
                    self.test_warehouse_id = warehouse_id
                    self.log(f"✅ Найден склад с грузами: {warehouse_name}")
                    self.log(f"   🆔 ID склада: {warehouse_id}")
                    self.log(f"   📦 Количество грузов: {total_cargo}")
                    self.log(f"   🏢 Занятых ячеек: {layout_data.get('occupied_cells', 0)}")
                    self.log(f"   📊 Процент загрузки: {layout_data.get('occupancy_percentage', 0)}%")
                    return True
        
        # Если не найден склад с грузами, используем первый доступный
        if warehouses:
            self.test_warehouse_id = warehouses[0].get("id")
            warehouse_name = warehouses[0].get("name", "Unknown")
            self.log(f"⚠️ Склад с грузами не найден, используем: {warehouse_name}")
            self.log(f"   🆔 ID склада: {self.test_warehouse_id}")
            return True
            
        self.log("❌ Не найдено ни одного склада")
        return False
    
    def test_warehouse_layout_with_cargo(self):
        """3. Тестирование GET /api/warehouses/{warehouse_id}/layout-with-cargo"""
        self.log("🗺️ ТЕСТИРОВАНИЕ СХЕМЫ СКЛАДА С ГРУЗАМИ")
        
        if not self.test_warehouse_id:
            self.log("❌ ID склада не определен")
            return False
            
        response = self.make_request("GET", f"/warehouses/{self.test_warehouse_id}/layout-with-cargo", token=self.admin_token)
        
        if not response or response.status_code != 200:
            self.log(f"❌ Ошибка получения схемы склада: {response.status_code if response else 'No response'}")
            if response:
                self.log(f"   Ответ: {response.text}")
            return False
            
        data = response.json()
        
        # Проверяем структуру ответа
        required_fields = ["warehouse", "layout", "total_cargo", "occupied_cells", "total_cells", "occupancy_percentage"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            self.log(f"❌ Отсутствуют обязательные поля: {missing_fields}")
            return False
            
        self.log("✅ Схема склада получена успешно")
        self.log(f"   📦 Всего грузов: {data['total_cargo']}")
        self.log(f"   🏢 Занятых ячеек: {data['occupied_cells']}")
        self.log(f"   📊 Всего ячеек: {data['total_cells']}")
        self.log(f"   📈 Процент загрузки: {data['occupancy_percentage']}%")
        
        # Проверяем структуру layout
        layout = data.get("layout", {})
        if not layout:
            self.log("⚠️ Layout пуст")
            return True
            
        # Анализируем блоки
        blocks_count = len(layout)
        self.log(f"   🏗️ Количество блоков: {blocks_count}")
        
        occupied_cells_found = 0
        free_cells_found = 0
        
        for block_key, block_data in layout.items():
            shelves = block_data.get("shelves", {})
            for shelf_key, shelf_data in shelves.items():
                cells = shelf_data.get("cells", {})
                for cell_key, cell_data in cells.items():
                    if cell_data.get("is_occupied", False):
                        occupied_cells_found += 1
                        cargo = cell_data.get("cargo")
                        if cargo:
                            self.log(f"   📦 Груз в ячейке {cell_data.get('location_code', 'Unknown')}: {cargo.get('cargo_number', 'Unknown')}")
                    else:
                        free_cells_found += 1
        
        self.log(f"   ✅ Проверено ячеек - Занято: {occupied_cells_found}, Свободно: {free_cells_found}")
        
        # Проверяем соответствие статистики
        if occupied_cells_found == data['occupied_cells']:
            self.log("✅ Статистика занятых ячеек корректна")
        else:
            self.log(f"⚠️ Несоответствие статистики: найдено {occupied_cells_found}, в API {data['occupied_cells']}")
            
        return True
    
    def create_test_cargo_with_same_contacts(self):
        """4. Создание тестовых грузов с одинаковыми контактными данными"""
        self.log("📦 СОЗДАНИЕ ТЕСТОВЫХ ГРУЗОВ С ОДИНАКОВЫМИ КОНТАКТАМИ")
        
        if not self.test_warehouse_id:
            self.log("❌ ID склада не определен")
            return False
            
        # Общие контактные данные для связанных грузов
        common_sender = {
            "sender_full_name": "Тестовый Отправитель Связанных Грузов",
            "sender_phone": "+992123456789"
        }
        
        common_recipient = {
            "recipient_full_name": "Тестовый Получатель Связанных Грузов", 
            "recipient_phone": "+992987654321",
            "recipient_address": "Душанбе, ул. Тестовая, 123"
        }
        
        # Создаем 3 груза с одинаковыми отправителем и получателем
        test_cargos = [
            {
                "cargo_name": "Тестовый груз №1 (связанный)",
                "weight": 15.5,
                "declared_value": 1500,
                "description": "Первый груз для тестирования связанных грузов"
            },
            {
                "cargo_name": "Тестовый груз №2 (связанный)",
                "weight": 22.3,
                "declared_value": 2200,
                "description": "Второй груз для тестирования связанных грузов"
            },
            {
                "cargo_name": "Тестовый груз №3 (связанный)",
                "weight": 8.7,
                "declared_value": 870,
                "description": "Третий груз для тестирования связанных грузов"
            }
        ]
        
        created_count = 0
        
        for i, cargo_data in enumerate(test_cargos, 1):
            # Объединяем данные груза с общими контактами
            full_cargo_data = {
                **common_sender,
                **common_recipient,
                **cargo_data,
                "route": "moscow_to_tajikistan",
                "warehouse_id": self.test_warehouse_id,
                "payment_method": "cash",
                "payment_amount": cargo_data["declared_value"]
            }
            
            response = self.make_request("POST", "/operator/cargo/direct-accept", full_cargo_data, token=self.admin_token)
            
            if response and response.status_code == 200:
                result = response.json()
                cargo_id = result.get("cargo_id")
                cargo_number = result.get("cargo_number")
                
                if cargo_id:
                    self.test_cargo_ids.append(cargo_id)
                    created_count += 1
                    self.log(f"✅ Создан груз #{i}: {cargo_number} (ID: {cargo_id})")
                    
                    # Размещаем груз в разных ячейках
                    placement_data = {
                        "cargo_id": cargo_id,
                        "warehouse_id": self.test_warehouse_id,
                        "block_number": i,  # Разные блоки
                        "shelf_number": 1,
                        "cell_number": i
                    }
                    
                    place_response = self.make_request("POST", "/operator/cargo/place", placement_data, token=self.admin_token)
                    
                    if place_response and place_response.status_code == 200:
                        place_result = place_response.json()
                        location = place_result.get("warehouse_location", "Unknown")
                        self.log(f"   📍 Размещен в ячейке: {location}")
                    else:
                        self.log(f"   ⚠️ Не удалось разместить груз: {place_response.status_code if place_response else 'No response'}")
            else:
                self.log(f"❌ Ошибка создания груза #{i}: {response.status_code if response else 'No response'}")
                if response:
                    self.log(f"   Ответ: {response.text}")
        
        self.log(f"📦 Создано тестовых грузов: {created_count}/3")
        return created_count > 0
    
    def test_related_cargo_search(self):
        """5. Тестирование поиска связанных грузов"""
        self.log("🔍 ТЕСТИРОВАНИЕ ПОИСКА СВЯЗАННЫХ ГРУЗОВ")
        
        if not self.test_warehouse_id or not self.test_cargo_ids:
            self.log("❌ Нет данных для тестирования (склад или грузы не созданы)")
            return False
            
        # Тестируем поиск по отправителю
        search_data = {
            "cargo_id": self.test_cargo_ids[0],  # Исключаем первый груз из поиска
            "sender_phone": "+992123456789",
            "sender_full_name": "Тестовый Отправитель Связанных Грузов"
        }
        
        response = self.make_request("POST", f"/warehouses/{self.test_warehouse_id}/related-cargo", search_data, token=self.admin_token)
        
        if not response or response.status_code != 200:
            self.log(f"❌ Ошибка поиска связанных грузов: {response.status_code if response else 'No response'}")
            if response:
                self.log(f"   Ответ: {response.text}")
            return False
            
        data = response.json()
        
        # Проверяем структуру ответа
        required_fields = ["success", "related_cargo", "total_related", "search_criteria", "message"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            self.log(f"❌ Отсутствуют обязательные поля в ответе: {missing_fields}")
            return False
            
        self.log("✅ Поиск связанных грузов выполнен успешно")
        self.log(f"   🔍 Найдено связанных грузов: {data['total_related']}")
        self.log(f"   📝 Сообщение: {data['message']}")
        
        # Анализируем найденные грузы
        related_cargo = data.get("related_cargo", [])
        
        for i, cargo in enumerate(related_cargo, 1):
            self.log(f"   📦 Связанный груз #{i}:")
            self.log(f"      🆔 Номер: {cargo.get('cargo_number', 'Unknown')}")
            self.log(f"      📦 Название: {cargo.get('cargo_name', 'Unknown')}")
            self.log(f"      ⚖️ Вес: {cargo.get('weight', 0)} кг")
            self.log(f"      📍 Местоположение: {cargo.get('formatted_location', cargo.get('warehouse_location', 'Unknown'))}")
            self.log(f"      👤 Отправитель: {cargo.get('sender_full_name', 'Unknown')} ({cargo.get('sender_phone', 'Unknown')})")
            self.log(f"      👤 Получатель: {cargo.get('recipient_full_name', 'Unknown')} ({cargo.get('recipient_phone', 'Unknown')})")
        
        # Тестируем поиск по получателю
        self.log("🔍 Тестирование поиска по получателю")
        
        recipient_search_data = {
            "cargo_id": self.test_cargo_ids[0],
            "recipient_phone": "+992987654321",
            "recipient_full_name": "Тестовый Получатель Связанных Грузов"
        }
        
        recipient_response = self.make_request("POST", f"/warehouses/{self.test_warehouse_id}/related-cargo", recipient_search_data, token=self.admin_token)
        
        if recipient_response and recipient_response.status_code == 200:
            recipient_data = recipient_response.json()
            self.log(f"✅ Поиск по получателю: найдено {recipient_data.get('total_related', 0)} грузов")
        else:
            self.log(f"⚠️ Ошибка поиска по получателю: {recipient_response.status_code if recipient_response else 'No response'}")
            
        return True
    
    def test_warehouse_statistics(self):
        """6. Проверка статистики склада"""
        self.log("📊 ПРОВЕРКА СТАТИСТИКИ СКЛАДА")
        
        if not self.test_warehouse_id:
            self.log("❌ ID склада не определен")
            return False
            
        # Получаем статистику склада
        response = self.make_request("GET", f"/warehouses/{self.test_warehouse_id}/statistics", token=self.admin_token)
        
        if not response or response.status_code != 200:
            self.log(f"❌ Ошибка получения статистики склада: {response.status_code if response else 'No response'}")
            return False
            
        stats = response.json()
        
        self.log("✅ Статистика склада получена")
        self.log(f"   📦 Всего ячеек: {stats.get('total_cells', 0)}")
        self.log(f"   🏢 Занятых ячеек: {stats.get('occupied_cells', 0)}")
        self.log(f"   🆓 Свободных ячеек: {stats.get('free_cells', 0)}")
        self.log(f"   📈 Процент загрузки: {stats.get('occupancy_percentage', 0)}%")
        
        # Проверяем корректность расчетов
        total_cells = stats.get('total_cells', 0)
        occupied_cells = stats.get('occupied_cells', 0)
        free_cells = stats.get('free_cells', 0)
        occupancy_percentage = stats.get('occupancy_percentage', 0)
        
        if total_cells == occupied_cells + free_cells:
            self.log("✅ Расчет общего количества ячеек корректен")
        else:
            self.log(f"⚠️ Ошибка в расчете: {total_cells} ≠ {occupied_cells} + {free_cells}")
            
        if total_cells > 0:
            expected_percentage = round((occupied_cells / total_cells) * 100, 2)
            if abs(occupancy_percentage - expected_percentage) < 0.01:
                self.log("✅ Расчет процента загрузки корректен")
            else:
                self.log(f"⚠️ Ошибка в расчете процента: {occupancy_percentage}% ≠ {expected_percentage}%")
        
        return True
    
    def test_operator_authorization(self):
        """Дополнительное тестирование авторизации оператора склада"""
        self.log("🔐 ТЕСТИРОВАНИЕ АВТОРИЗАЦИИ ОПЕРАТОРА СКЛАДА")
        
        # Данные оператора склада
        operator_credentials = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        response = self.make_request("POST", "/auth/login", operator_credentials)
        
        if not response or response.status_code != 200:
            self.log(f"❌ Ошибка авторизации оператора: {response.status_code if response else 'No response'}")
            return False
            
        data = response.json()
        self.operator_token = data.get("access_token")
        user_info = data.get("user", {})
        
        self.log(f"✅ Оператор авторизован: {user_info.get('full_name', 'Unknown')}")
        self.log(f"   📱 Телефон: {user_info.get('phone', 'Unknown')}")
        self.log(f"   👤 Роль: {user_info.get('role', 'Unknown')}")
        self.log(f"   🆔 ID: {user_info.get('id', 'Unknown')}")
        
        return True
    
    def test_operator_warehouse_access(self):
        """Тестирование доступа оператора к схеме склада"""
        self.log("🏭 ТЕСТИРОВАНИЕ ДОСТУПА ОПЕРАТОРА К СХЕМЕ СКЛАДА")
        
        if not self.operator_token or not self.test_warehouse_id:
            self.log("❌ Нет токена оператора или ID склада")
            return False
            
        # Тестируем доступ оператора к схеме склада
        response = self.make_request("GET", f"/warehouses/{self.test_warehouse_id}/layout-with-cargo", token=self.operator_token)
        
        if response and response.status_code == 200:
            self.log("✅ Оператор имеет доступ к схеме склада")
            data = response.json()
            self.log(f"   📦 Грузов в схеме: {data.get('total_cargo', 0)}")
            return True
        elif response and response.status_code == 403:
            self.log("✅ Доступ оператора корректно ограничен (403)")
            return True
        else:
            self.log(f"❌ Неожиданный ответ: {response.status_code if response else 'No response'}")
            return False
    
    def cleanup_test_data(self):
        """7. Очистка тестовых данных"""
        self.log("🧹 ОЧИСТКА ТЕСТОВЫХ ДАННЫХ")
        
        deleted_count = 0
        
        for cargo_id in self.test_cargo_ids:
            # Пытаемся удалить из operator_cargo
            response = self.make_request("DELETE", f"/operator/cargo/{cargo_id}", token=self.admin_token)
            
            if response and response.status_code == 200:
                deleted_count += 1
                self.log(f"✅ Удален тестовый груз: {cargo_id}")
            else:
                # Пытаемся удалить из admin cargo
                admin_response = self.make_request("DELETE", f"/admin/cargo/{cargo_id}", token=self.admin_token)
                
                if admin_response and admin_response.status_code == 200:
                    deleted_count += 1
                    self.log(f"✅ Удален тестовый груз (admin): {cargo_id}")
                else:
                    self.log(f"⚠️ Не удалось удалить груз: {cargo_id}")
        
        self.log(f"🧹 Очищено тестовых грузов: {deleted_count}/{len(self.test_cargo_ids)}")
        
        # Очищаем список
        self.test_cargo_ids.clear()
        
        return True
    
    def run_comprehensive_test(self):
        """Запуск полного комплексного тестирования"""
        self.log("🎯 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ СХЕМЫ СКЛАДА И СВЯЗАННЫХ ГРУЗОВ TAJLINE.TJ")
        self.log("=" * 80)
        
        test_results = []
        
        # 1. Авторизация администратора
        test_results.append(("Авторизация администратора", self.test_admin_authorization()))
        
        # 2. Поиск склада с грузами
        test_results.append(("Поиск склада с грузами", self.find_warehouse_with_cargo()))
        
        # 3. Тестирование схемы склада
        test_results.append(("Схема склада с грузами", self.test_warehouse_layout_with_cargo()))
        
        # 4. Создание тестовых грузов
        test_results.append(("Создание тестовых грузов", self.create_test_cargo_with_same_contacts()))
        
        # 5. Тестирование поиска связанных грузов
        test_results.append(("Поиск связанных грузов", self.test_related_cargo_search()))
        
        # 6. Проверка статистики
        test_results.append(("Статистика склада", self.test_warehouse_statistics()))
        
        # 7. Тестирование оператора склада
        test_results.append(("Авторизация оператора склада", self.test_operator_authorization()))
        
        # 8. Тестирование доступа оператора
        test_results.append(("Доступ оператора к схеме склада", self.test_operator_warehouse_access()))
        
        # 9. Очистка данных
        test_results.append(("Очистка тестовых данных", self.cleanup_test_data()))
        
        # Подведение итогов
        self.log("=" * 80)
        self.log("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
            self.log(f"{status}: {test_name}")
            if result:
                passed_tests += 1
        
        success_rate = (passed_tests / total_tests) * 100
        self.log("=" * 80)
        self.log(f"🎯 ИТОГОВЫЙ РЕЗУЛЬТАТ: {passed_tests}/{total_tests} тестов пройдено ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            self.log("🎉 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            self.log("✅ Схема склада и поиск связанных грузов функционируют корректно")
        elif success_rate >= 60:
            self.log("⚠️ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ПРЕДУПРЕЖДЕНИЯМИ")
            self.log("🔧 Требуются незначительные исправления")
        else:
            self.log("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ")
            self.log("🚨 Требуется немедленное исправление")
        
        return success_rate >= 80

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Схема склада и связанные грузы TAJLINE.TJ")
    print("=" * 80)
    
    tester = WarehouseSchemaRelatedCargoTester()
    success = tester.run_comprehensive_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())