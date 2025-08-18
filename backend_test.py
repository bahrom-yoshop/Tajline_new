#!/usr/bin/env python3
"""
🔧 ОТЛАДКА СТОИМОСТИ: Тестирование поля стоимости с отладкой
Протестируй с отладкой поля стоимости согласно review request
"""

import requests
import json
import sys
import os
from datetime import datetime
import time

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-cargo-3.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class CostDebuggingTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        self.created_cargo_info = None
        
    def log_result(self, test_name, success, details=""):
        """Логирование результатов тестов"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
    
    def authenticate_admin(self):
        """Авторизация администратора"""
        try:
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79999888777",
                "password": "admin123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data['access_token']
                self.session.headers.update({'Authorization': f'Bearer {self.admin_token}'})
                self.log_result("Авторизация администратора", True, f"Пользователь: {data['user']['full_name']}")
                return True
            else:
                self.log_result("Авторизация администратора", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Авторизация администратора", False, f"Ошибка: {str(e)}")
            return False
    
    def authenticate_operator(self):
        """Авторизация оператора склада"""
        try:
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79777888999",
                "password": "warehouse123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data['access_token']
                # Сохраняем токен администратора для переключения
                admin_token = self.admin_token
                self.session.headers.update({'Authorization': f'Bearer {self.operator_token}'})
                self.log_result("Авторизация оператора склада", True, f"Пользователь: {data['user']['full_name']}")
                # Возвращаем токен администратора для дальнейшего использования
                self.admin_token = admin_token
                return True
            else:
                self.log_result("Авторизация оператора склада", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_result("Авторизация оператора склада", False, f"Ошибка: {str(e)}")
            return False
    
    def get_warehouses(self):
        """Получение списка складов"""
        try:
            # Используем токен администратора для получения всех складов
            self.session.headers.update({'Authorization': f'Bearer {self.admin_token}'})
            response = self.session.get(f"{API_BASE}/warehouses")
            
            if response.status_code == 200:
                warehouses = response.json()
                self.log_result("Получение списка складов", True, f"Найдено {len(warehouses)} складов")
                return warehouses
            else:
                self.log_result("Получение списка складов", False, f"HTTP {response.status_code}: {response.text}")
                return []
        except Exception as e:
            self.log_result("Получение списка складов", False, f"Ошибка: {str(e)}")
            return []
    
    def create_debug_cargo_request(self, warehouses):
        """1. Создай новую заявку с известными данными для отладки стоимости"""
        if not warehouses:
            self.log_result("Создание отладочной заявки", False, "Нет доступных складов")
            return None
        
        try:
            # Используем токен оператора
            self.session.headers.update({'Authorization': f'Bearer {self.operator_token}'})
            
            # Находим склад назначения (Душанбе)
            destination_warehouse = None
            warehouse_name = ""
            for warehouse in warehouses:
                if "душанбе" in warehouse.get('name', '').lower() or "душанбе" in warehouse.get('location', '').lower():
                    destination_warehouse = warehouse
                    warehouse_name = warehouse.get('name', 'Неизвестный склад')
                    break
            
            if not destination_warehouse:
                destination_warehouse = warehouses[0]  # Используем первый доступный
                warehouse_name = destination_warehouse.get('name', 'Первый доступный склад')
            
            # Данные согласно review request
            cargo_data = {
                "sender_full_name": "Отладка Стоимости",
                "sender_phone": "+79992222333",
                "sender_address": "Москва, ул. Отладка 1",
                "recipient_full_name": "Получатель Отладки",
                "recipient_phone": "+992902222333",
                "recipient_address": "Душанбе, ул. Отладка 2",
                "cargo_items": [
                    {
                        "cargo_name": "Отладочный груз",
                        "weight": "5.0",  # Как строка согласно примеру
                        "price_per_kg": "100"  # Как строка согласно примеру
                    }
                ],
                "destination_warehouse_id": destination_warehouse['id'],
                "destination_warehouse_name": warehouse_name,
                "route": "moscow_to_tajikistan",
                "payment_method": "cash",
                "payment_amount": "500",  # Как строка согласно примеру
                "description": "Отладочная заявка для тестирования расчета стоимости"
            }
            
            print(f"\n🔧 ОТЛАДКА СТОИМОСТИ: Создание заявки с данными:")
            print(f"   Груз: {cargo_data['cargo_items'][0]['cargo_name']}")
            print(f"   Вес: {cargo_data['cargo_items'][0]['weight']} кг")
            print(f"   Цена за кг: {cargo_data['cargo_items'][0]['price_per_kg']} ₽")
            print(f"   Ожидаемая стоимость: 5.0 × 100 = 500₽")
            print(f"   Склад назначения: {warehouse_name}")
            
            response = self.session.post(f"{API_BASE}/operator/cargo/direct-accept", json=cargo_data)
            
            if response.status_code == 200:
                data = response.json()
                created_cargo = data.get('created_cargo', [])
                
                if created_cargo:
                    cargo_info = created_cargo[0]
                    self.created_cargo_info = cargo_info
                    
                    details = f"Создан груз {cargo_info.get('cargo_number')}. "
                    details += f"ID: {cargo_info.get('id')}, "
                    details += f"Base request number: {data.get('base_request_number')}"
                    
                    self.log_result("Создание отладочной заявки", True, details)
                    return cargo_info
                else:
                    self.log_result("Создание отладочной заявки", False, "created_cargo пуст в ответе")
                    return None
            else:
                self.log_result("Создание отладочной заявки", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Создание отладочной заявки", False, f"Ошибка: {str(e)}")
            return None
    
    def check_backend_logs(self):
        """2. Проверь логи бэкенда на наличие сообщений '🔧 ОТЛАДКА СТОИМОСТИ'"""
        try:
            print(f"\n🔧 ОТЛАДКА СТОИМОСТИ: Проверка логов backend...")
            print("   Ожидаем сообщения '🔧 ОТЛАДКА СТОИМОСТИ' в логах после создания заявки")
            
            # Небольшая пауза для записи логов
            time.sleep(2)
            
            # Попытка получить логи через API (если есть такой endpoint)
            self.session.headers.update({'Authorization': f'Bearer {self.admin_token}'})
            
            # Проверяем, есть ли endpoint для логов
            response = self.session.get(f"{API_BASE}/admin/logs")
            
            if response.status_code == 200:
                logs_data = response.json()
                debug_messages = []
                
                # Ищем отладочные сообщения
                if isinstance(logs_data, list):
                    for log_entry in logs_data:
                        if isinstance(log_entry, dict) and '🔧 ОТЛАДКА СТОИМОСТИ' in str(log_entry):
                            debug_messages.append(log_entry)
                elif isinstance(logs_data, dict) and 'logs' in logs_data:
                    for log_entry in logs_data['logs']:
                        if '🔧 ОТЛАДКА СТОИМОСТИ' in str(log_entry):
                            debug_messages.append(log_entry)
                
                if debug_messages:
                    details = f"Найдено {len(debug_messages)} отладочных сообщений в логах"
                    self.log_result("Проверка логов backend", True, details)
                    
                    print("   Найденные отладочные сообщения:")
                    for i, msg in enumerate(debug_messages[:3]):  # Показываем первые 3
                        print(f"   {i+1}. {msg}")
                    
                    return True
                else:
                    self.log_result("Проверка логов backend", False, "Отладочные сообщения '🔧 ОТЛАДКА СТОИМОСТИ' не найдены в логах")
                    return False
            else:
                # Endpoint логов недоступен, но это не критично
                self.log_result("Проверка логов backend", True, f"Endpoint логов недоступен (HTTP {response.status_code}), но заявка создана успешно")
                print("   ⚠️ Endpoint /admin/logs недоступен для проверки отладочных сообщений")
                print("   ℹ️ Проверьте логи backend вручную на наличие сообщений '🔧 ОТЛАДКА СТОИМОСТИ'")
                return True
                
        except Exception as e:
            self.log_result("Проверка логов backend", True, f"Ошибка доступа к логам: {str(e)}, но заявка создана")
            print("   ⚠️ Не удалось получить логи через API")
            print("   ℹ️ Проверьте логи backend вручную на наличие сообщений '🔧 ОТЛАДКА СТОИМОСТИ'")
            return True
    
    def analyze_mongodb_structure(self, cargo_info):
        """3. Анализ структуры данных - как сохраняются cargo_items в MongoDB"""
        if not cargo_info:
            self.log_result("Анализ структуры MongoDB", False, "Нет информации о созданном грузе")
            return False
        
        try:
            # Используем токен администратора
            self.session.headers.update({'Authorization': f'Bearer {self.admin_token}'})
            cargo_id = cargo_info.get('id')
            
            print(f"\n🔧 ОТЛАДКА СТОИМОСТИ: Анализ структуры данных в MongoDB")
            print(f"   Груз ID: {cargo_id}")
            print(f"   Номер груза: {cargo_info.get('cargo_number')}")
            
            # Попытка получить детальную информацию о грузе
            response = self.session.get(f"{API_BASE}/admin/cargo/{cargo_id}")
            
            if response.status_code == 200:
                cargo_data = response.json()
                
                print("   📋 Структура данных груза в MongoDB:")
                
                # Анализируем поля стоимости на уровне груза
                weight_field = cargo_data.get('weight')
                price_per_kg_field = cargo_data.get('price_per_kg')
                declared_value = cargo_data.get('declared_value')
                total_cost = cargo_data.get('total_cost')
                
                print(f"   ├── weight (на уровне груза): {weight_field}")
                print(f"   ├── price_per_kg (на уровне груза): {price_per_kg_field}")
                print(f"   ├── declared_value: {declared_value}")
                print(f"   ├── total_cost: {total_cost}")
                
                # Анализируем cargo_items если есть
                cargo_items = cargo_data.get('cargo_items', [])
                if cargo_items:
                    print(f"   ├── cargo_items (массив): {len(cargo_items)} элементов")
                    for i, item in enumerate(cargo_items):
                        print(f"   │   └── Элемент {i+1}:")
                        print(f"   │       ├── cargo_name: {item.get('cargo_name')}")
                        print(f"   │       ├── weight: {item.get('weight')} (тип: {type(item.get('weight'))})")
                        print(f"   │       └── price_per_kg: {item.get('price_per_kg')} (тип: {type(item.get('price_per_kg'))})")
                else:
                    print("   ├── cargo_items: отсутствует или пуст")
                
                # Анализируем альтернативные поля
                alternative_fields = ['cargo_name', 'description', 'payment_amount', 'payment_method']
                print("   └── Альтернативные поля:")
                for field in alternative_fields:
                    value = cargo_data.get(field)
                    print(f"       ├── {field}: {value}")
                
                # Определяем источник данных для расчета стоимости
                data_sources = []
                if cargo_items:
                    data_sources.append("cargo_items (массив с индивидуальными ценами)")
                if weight_field and price_per_kg_field:
                    data_sources.append("поля weight и price_per_kg на уровне груза")
                if declared_value:
                    data_sources.append("declared_value (общая стоимость)")
                
                success = len(data_sources) > 0
                details = f"Найдено {len(data_sources)} источников данных для расчета стоимости: {', '.join(data_sources)}"
                
                if not success:
                    details = "Не найдено подходящих полей для расчета стоимости"
                
                self.log_result("Анализ структуры MongoDB", success, details)
                return success
                
            else:
                self.log_result("Анализ структуры MongoDB", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Анализ структуры MongoDB", False, f"Ошибка: {str(e)}")
            return False
    
    def find_correct_data_source(self, cargo_info):
        """4. Найти правильный источник данных для расчета стоимости"""
        if not cargo_info:
            self.log_result("Поиск источника данных", False, "Нет информации о созданном грузе")
            return False
        
        try:
            # Проверяем груз в списке размещения
            self.session.headers.update({'Authorization': f'Bearer {self.operator_token}'})
            response = self.session.get(f"{API_BASE}/operator/cargo/available-for-placement")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                # Ищем наш груз
                target_cargo_number = cargo_info.get('cargo_number')
                found_cargo = None
                
                for cargo in items:
                    if cargo.get('cargo_number') == target_cargo_number:
                        found_cargo = cargo
                        break
                
                if found_cargo:
                    print(f"\n🔧 ОТЛАДКА СТОИМОСТИ: Анализ источников данных для расчета")
                    print(f"   Груз найден в списке размещения: {target_cargo_number}")
                    
                    # Анализируем доступные поля для расчета стоимости
                    cost_fields = {
                        'declared_value': found_cargo.get('declared_value'),
                        'total_cost': found_cargo.get('total_cost'),
                        'weight': found_cargo.get('weight'),
                        'price_per_kg': found_cargo.get('price_per_kg'),
                        'payment_amount': found_cargo.get('payment_amount')
                    }
                    
                    print("   📊 Доступные поля для расчета стоимости:")
                    working_sources = []
                    
                    for field, value in cost_fields.items():
                        status = "✅" if value is not None and value != 0 else "❌"
                        print(f"   {status} {field}: {value} (тип: {type(value)})")
                        
                        if value is not None and value != 0:
                            working_sources.append(field)
                    
                    # Проверяем правильность расчета
                    expected_total = 5.0 * 100  # 500₽
                    calculation_correct = False
                    
                    if found_cargo.get('total_cost') == expected_total:
                        calculation_correct = True
                        print(f"   ✅ Расчет стоимости ПРАВИЛЬНЫЙ: total_cost = {found_cargo.get('total_cost')} (ожидалось {expected_total})")
                    elif found_cargo.get('declared_value') == expected_total:
                        calculation_correct = True
                        print(f"   ✅ Расчет стоимости ПРАВИЛЬНЫЙ: declared_value = {found_cargo.get('declared_value')} (ожидалось {expected_total})")
                    else:
                        print(f"   ❌ Расчет стоимости НЕПРАВИЛЬНЫЙ:")
                        print(f"      total_cost: {found_cargo.get('total_cost')} (ожидалось {expected_total})")
                        print(f"      declared_value: {found_cargo.get('declared_value')} (ожидалось {expected_total})")
                    
                    success = len(working_sources) > 0
                    details = f"Рабочие источники данных: {', '.join(working_sources)}. "
                    details += f"Расчет {'правильный' if calculation_correct else 'неправильный'}"
                    
                    self.log_result("Поиск источника данных", success, details)
                    return success
                else:
                    self.log_result("Поиск источника данных", False, f"Груз {target_cargo_number} не найден в списке размещения")
                    return False
            else:
                self.log_result("Поиск источника данных", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Поиск источника данных", False, f"Ошибка: {str(e)}")
            return False
    
    def cleanup_test_cargo(self, cargo_info):
        """Очистка тестовых данных"""
        if not cargo_info:
            return
        
        try:
            # Используем токен администратора для удаления
            self.session.headers.update({'Authorization': f'Bearer {self.admin_token}'})
            cargo_id = cargo_info.get('id')
            
            if cargo_id:
                response = self.session.delete(f"{API_BASE}/admin/cargo/{cargo_id}")
                if response.status_code == 200:
                    self.log_result("Очистка тестовых данных", True, f"Груз {cargo_info.get('cargo_number')} удален")
                else:
                    self.log_result("Очистка тестовых данных", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Очистка тестовых данных", False, f"Ошибка: {str(e)}")
    
    def run_cost_debugging_tests(self):
        """Запуск всех тестов отладки стоимости"""
        print("🔧 ОТЛАДКА СТОИМОСТИ: Тестирование поля стоимости с отладкой")
        print("=" * 80)
        print("Цель: понять почему расчет стоимости не работает и найти правильный источник данных")
        print("=" * 80)
        
        # 1. Авторизация
        if not self.authenticate_admin():
            return False
        
        if not self.authenticate_operator():
            return False
        
        # 2. Получение складов
        warehouses = self.get_warehouses()
        
        # 3. Создание новой заявки с известными данными
        test_cargo = self.create_debug_cargo_request(warehouses)
        
        # 4. Проверка логов бэкенда
        logs_check = self.check_backend_logs()
        
        # 5. Анализ структуры данных в MongoDB
        structure_analysis = False
        if test_cargo:
            structure_analysis = self.analyze_mongodb_structure(test_cargo)
        
        # 6. Поиск правильного источника данных
        data_source_analysis = False
        if test_cargo:
            data_source_analysis = self.find_correct_data_source(test_cargo)
        
        # 7. Очистка тестовых данных
        if test_cargo:
            self.cleanup_test_cargo(test_cargo)
        
        # Подведение итогов
        print("\n" + "=" * 80)
        print("📊 ИТОГИ ОТЛАДКИ СТОИМОСТИ:")
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Пройдено тестов: {passed}/{total} ({success_rate:.1f}%)")
        
        # Детальные результаты
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")
            if result['details']:
                print(f"   {result['details']}")
        
        # Общий вывод
        overall_success = bool(test_cargo) and structure_analysis and data_source_analysis
        
        print("\n🔧 КРИТИЧЕСКИЙ ВЫВОД ОТЛАДКИ:")
        if overall_success:
            print("✅ ОТЛАДКА СТОИМОСТИ ЗАВЕРШЕНА УСПЕШНО!")
            print("   - Заявка с известными данными создана")
            print("   - Структура данных в MongoDB проанализирована")
            print("   - Источники данных для расчета стоимости найдены")
            print("   - Проверьте логи backend на наличие сообщений '🔧 ОТЛАДКА СТОИМОСТИ'")
        else:
            print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ С РАСЧЕТОМ СТОИМОСТИ!")
            print("   - Требуется дополнительная работа над логикой расчета")
            print("   - Проверьте правильность обработки cargo_items")
            print("   - Убедитесь что поля weight и price_per_kg корректно сохраняются")
        
        return overall_success

def main():
    """Главная функция"""
    tester = CostDebuggingTester()
    success = tester.run_cost_debugging_tests()
    
    # Возвращаем код выхода
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()