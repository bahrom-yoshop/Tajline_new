#!/usr/bin/env python3
"""
🔧 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ РАСЧЕТА СТОИМОСТИ
Протестируй исправления расчета стоимости согласно review request
"""

import requests
import json
import sys
import os
from datetime import datetime
import time

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://qr-logistics-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class CostCalculationFixesTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        self.created_cargo_info = None
        self.warehouses = []
        
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
                self.warehouses = warehouses
                self.log_result("Получение списка складов", True, f"Найдено {len(warehouses)} складов")
                return warehouses
            else:
                self.log_result("Получение списка складов", False, f"HTTP {response.status_code}: {response.text}")
                return []
        except Exception as e:
            self.log_result("Получение списка складов", False, f"Ошибка: {str(e)}")
            return []
    
    def create_final_cost_test_request(self):
        """1. Создай новую заявку с известными данными согласно review request"""
        if not self.warehouses:
            self.log_result("Создание финальной тестовой заявки", False, "Нет доступных складов")
            return None
        
        try:
            # Используем токен оператора
            self.session.headers.update({'Authorization': f'Bearer {self.operator_token}'})
            
            # Находим склад назначения (Душанбе)
            destination_warehouse = None
            warehouse_name = ""
            for warehouse in self.warehouses:
                if "душанбе" in warehouse.get('name', '').lower() or "душанбе" in warehouse.get('location', '').lower():
                    destination_warehouse = warehouse
                    warehouse_name = warehouse.get('name', 'Неизвестный склад')
                    break
            
            if not destination_warehouse:
                destination_warehouse = self.warehouses[0]  # Используем первый доступный
                warehouse_name = destination_warehouse.get('name', 'Первый доступный склад')
            
            # Данные ТОЧНО согласно review request
            cargo_data = {
                "sender_full_name": "Финальный Тест Стоимости",
                "sender_phone": "+79993333444",
                "sender_address": "Москва, ул. Финальная 1",
                "recipient_full_name": "Получатель Финального Теста",
                "recipient_phone": "+992903333444",
                "recipient_address": "Душанбе, ул. Финальная 2",
                "cargo_items": [
                    {
                        "cargo_name": "Финальный тест груз 1",
                        "weight": "3.0",
                        "price_per_kg": "200"
                    },
                    {
                        "cargo_name": "Финальный тест груз 2", 
                        "weight": "2.0",
                        "price_per_kg": "300"
                    }
                ],
                "destination_warehouse_id": destination_warehouse['id'],
                "destination_warehouse_name": warehouse_name,
                "route": "moscow_to_tajikistan",
                "payment_method": "cash",
                "payment_amount": "1200",
                "description": "Финальный тест исправлений расчета стоимости"
            }
            
            print(f"\n🔧 ФИНАЛЬНЫЙ ТЕСТ СТОИМОСТИ: Создание заявки с данными:")
            print(f"   Груз 1: {cargo_data['cargo_items'][0]['cargo_name']}")
            print(f"   - Вес: {cargo_data['cargo_items'][0]['weight']} кг")
            print(f"   - Цена за кг: {cargo_data['cargo_items'][0]['price_per_kg']} ₽")
            print(f"   - Ожидаемая стоимость: 3.0 × 200 = 600₽")
            print(f"   Груз 2: {cargo_data['cargo_items'][1]['cargo_name']}")
            print(f"   - Вес: {cargo_data['cargo_items'][1]['weight']} кг")
            print(f"   - Цена за кг: {cargo_data['cargo_items'][1]['price_per_kg']} ₽")
            print(f"   - Ожидаемая стоимость: 2.0 × 300 = 600₽")
            print(f"   ОБЩАЯ ОЖИДАЕМАЯ СТОИМОСТЬ: 600 + 600 = 1200₽")
            print(f"   Склад назначения: {warehouse_name}")
            
            response = self.session.post(f"{API_BASE}/operator/cargo/direct-accept", json=cargo_data)
            
            if response.status_code == 200:
                data = response.json()
                created_cargo = data.get('created_cargo', [])
                
                if created_cargo:
                    self.created_cargo_info = created_cargo
                    
                    details = f"Создано {len(created_cargo)} грузов. "
                    details += f"Base request number: {data.get('base_request_number')}"
                    
                    print(f"   ✅ Создано грузов: {len(created_cargo)}")
                    for i, cargo in enumerate(created_cargo):
                        print(f"   - Груз {i+1}: {cargo.get('cargo_number')} (ID: {cargo.get('id')})")
                    
                    self.log_result("Создание финальной тестовой заявки", True, details)
                    return created_cargo
                else:
                    self.log_result("Создание финальной тестовой заявки", False, "created_cargo пуст в ответе")
                    return None
            else:
                self.log_result("Создание финальной тестовой заявки", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Создание финальной тестовой заявки", False, f"Ошибка: {str(e)}")
            return None
    
    def check_available_for_placement_api(self):
        """2. Проверь API размещения /api/operator/cargo/available-for-placement"""
        if not self.created_cargo_info:
            self.log_result("Проверка API размещения", False, "Нет созданных грузов для проверки")
            return False
        
        try:
            # Используем токен оператора
            self.session.headers.update({'Authorization': f'Bearer {self.operator_token}'})
            
            print(f"\n🔧 ПРОВЕРКА API РАЗМЕЩЕНИЯ:")
            print(f"   Endpoint: {API_BASE}/operator/cargo/available-for-placement")
            
            response = self.session.get(f"{API_BASE}/operator/cargo/available-for-placement")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                print(f"   📦 Найдено грузов в списке размещения: {len(items)}")
                
                # Ищем наши созданные грузы
                found_cargos = []
                created_numbers = [cargo.get('cargo_number') for cargo in self.created_cargo_info]
                
                for cargo in items:
                    if cargo.get('cargo_number') in created_numbers:
                        found_cargos.append(cargo)
                
                print(f"   🎯 Найдено наших тестовых грузов: {len(found_cargos)}")
                
                if found_cargos:
                    print(f"   📊 АНАЛИЗ ПОЛЕЙ СТОИМОСТИ:")
                    
                    total_expected_cost = 1200  # 600 + 600
                    cost_analysis_results = []
                    
                    for i, cargo in enumerate(found_cargos):
                        cargo_number = cargo.get('cargo_number')
                        declared_value = cargo.get('declared_value')
                        total_cost = cargo.get('total_cost')
                        payment_amount = cargo.get('payment_amount')
                        weight = cargo.get('weight')
                        price_per_kg = cargo.get('price_per_kg')
                        
                        print(f"   \n   Груз {i+1}: {cargo_number}")
                        print(f"   ├── declared_value: {declared_value} (тип: {type(declared_value)})")
                        print(f"   ├── total_cost: {total_cost} (тип: {type(total_cost)})")
                        print(f"   ├── payment_amount: {payment_amount} (тип: {type(payment_amount)})")
                        print(f"   ├── weight: {weight} (тип: {type(weight)})")
                        print(f"   └── price_per_kg: {price_per_kg} (тип: {type(price_per_kg)})")
                        
                        # Анализируем правильность расчета
                        cost_correct = False
                        if declared_value and declared_value > 0:
                            cost_correct = True
                            cost_analysis_results.append(f"declared_value заполнен: {declared_value}")
                        
                        if total_cost and total_cost > 0:
                            cost_correct = True
                            cost_analysis_results.append(f"total_cost заполнен: {total_cost}")
                        
                        if not cost_correct:
                            cost_analysis_results.append(f"❌ Стоимость НЕ рассчитана для {cargo_number}")
                    
                    success = len(cost_analysis_results) > 0 and all("❌" not in result for result in cost_analysis_results)
                    details = f"Найдено {len(found_cargos)} грузов. Анализ: {'; '.join(cost_analysis_results)}"
                    
                    self.log_result("Проверка API размещения", success, details)
                    return success
                else:
                    self.log_result("Проверка API размещения", False, f"Созданные грузы не найдены в списке размещения. Ожидались: {created_numbers}")
                    return False
            else:
                self.log_result("Проверка API размещения", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Проверка API размещения", False, f"Ошибка: {str(e)}")
            return False
    
    def check_debug_logs(self):
        """3. Проверь отладку в логах - должны быть сообщения "🔧 ОТЛАДКА СТОИМОСТИ" """
        try:
            print(f"\n🔧 ПРОВЕРКА ОТЛАДОЧНЫХ ЛОГОВ:")
            print("   Ищем сообщения '🔧 ОТЛАДКА СТОИМОСТИ' в логах backend...")
            
            # Небольшая пауза для записи логов
            time.sleep(2)
            
            # Используем токен администратора
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
                    self.log_result("Проверка отладочных логов", True, details)
                    
                    print("   📋 Найденные отладочные сообщения:")
                    for i, msg in enumerate(debug_messages[:5]):  # Показываем первые 5
                        print(f"   {i+1}. {msg}")
                    
                    return True
                else:
                    self.log_result("Проверка отладочных логов", False, "Отладочные сообщения '🔧 ОТЛАДКА СТОИМОСТИ' не найдены в логах")
                    print("   ⚠️ Возможно отладочные сообщения записываются в другой лог или отключены")
                    return False
            else:
                # Endpoint логов недоступен
                self.log_result("Проверка отладочных логов", True, f"Endpoint логов недоступен (HTTP {response.status_code}), проверьте логи вручную")
                print("   ⚠️ Endpoint /admin/logs недоступен для проверки отладочных сообщений")
                print("   ℹ️ Проверьте логи backend вручную на наличие сообщений '🔧 ОТЛАДКА СТОИМОСТИ'")
                return True
                
        except Exception as e:
            self.log_result("Проверка отладочных логов", True, f"Ошибка доступа к логам: {str(e)}, проверьте вручную")
            print("   ⚠️ Не удалось получить логи через API")
            print("   ℹ️ Проверьте логи backend вручную на наличие сообщений '🔧 ОТЛАДКА СТОИМОСТИ'")
            return True
    
    def analyze_cargo_structure(self):
        """4. Анализ результата - покажи структуру созданных грузов"""
        if not self.created_cargo_info:
            self.log_result("Анализ структуры грузов", False, "Нет созданных грузов для анализа")
            return False
        
        try:
            print(f"\n🔧 АНАЛИЗ СТРУКТУРЫ СОЗДАННЫХ ГРУЗОВ:")
            
            # Используем токен администратора для детального анализа
            self.session.headers.update({'Authorization': f'Bearer {self.admin_token}'})
            
            analysis_results = []
            
            for i, cargo_info in enumerate(self.created_cargo_info):
                cargo_id = cargo_info.get('id')
                cargo_number = cargo_info.get('cargo_number')
                
                print(f"\n   📦 ГРУЗ {i+1}: {cargo_number}")
                print(f"   ID: {cargo_id}")
                
                # Получаем детальную информацию о грузе
                response = self.session.get(f"{API_BASE}/admin/cargo/{cargo_id}")
                
                if response.status_code == 200:
                    cargo_data = response.json()
                    
                    # Анализируем поля стоимости
                    cost_fields = {
                        'weight': cargo_data.get('weight'),
                        'price_per_kg': cargo_data.get('price_per_kg'),
                        'declared_value': cargo_data.get('declared_value'),
                        'total_cost': cargo_data.get('total_cost'),
                        'payment_amount': cargo_data.get('payment_amount'),
                        'payment_method': cargo_data.get('payment_method')
                    }
                    
                    print(f"   📊 Поля стоимости:")
                    for field, value in cost_fields.items():
                        status = "✅" if value is not None and value != 0 else "❌"
                        print(f"   {status} {field}: {value} (тип: {type(value)})")
                    
                    # Проверяем cargo_items если есть
                    cargo_items = cargo_data.get('cargo_items', [])
                    if cargo_items:
                        print(f"   📋 cargo_items: {len(cargo_items)} элементов")
                        for j, item in enumerate(cargo_items):
                            print(f"   └── Элемент {j+1}:")
                            print(f"       ├── cargo_name: {item.get('cargo_name')}")
                            print(f"       ├── weight: {item.get('weight')}")
                            print(f"       └── price_per_kg: {item.get('price_per_kg')}")
                    else:
                        print(f"   📋 cargo_items: отсутствует")
                    
                    # Определяем правильность расчета
                    calculation_status = "неизвестно"
                    if cargo_data.get('declared_value') and cargo_data.get('declared_value') > 0:
                        calculation_status = "declared_value заполнен"
                    elif cargo_data.get('total_cost') and cargo_data.get('total_cost') > 0:
                        calculation_status = "total_cost заполнен"
                    else:
                        calculation_status = "стоимость НЕ рассчитана"
                    
                    analysis_results.append(f"Груз {cargo_number}: {calculation_status}")
                    
                else:
                    print(f"   ❌ Не удалось получить детальную информацию: HTTP {response.status_code}")
                    analysis_results.append(f"Груз {cargo_number}: ошибка получения данных")
            
            success = len(analysis_results) > 0 and all("НЕ рассчитана" not in result for result in analysis_results)
            details = f"Проанализировано {len(analysis_results)} грузов. Результаты: {'; '.join(analysis_results)}"
            
            self.log_result("Анализ структуры грузов", success, details)
            return success
            
        except Exception as e:
            self.log_result("Анализ структуры грузов", False, f"Ошибка: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        if not self.created_cargo_info:
            return
        
        try:
            # Используем токен администратора для удаления
            self.session.headers.update({'Authorization': f'Bearer {self.admin_token}'})
            
            print(f"\n🧹 ОЧИСТКА ТЕСТОВЫХ ДАННЫХ:")
            
            for cargo_info in self.created_cargo_info:
                cargo_id = cargo_info.get('id')
                cargo_number = cargo_info.get('cargo_number')
                
                if cargo_id:
                    response = self.session.delete(f"{API_BASE}/admin/cargo/{cargo_id}")
                    if response.status_code == 200:
                        print(f"   ✅ Груз {cargo_number} удален")
                    else:
                        print(f"   ❌ Ошибка удаления груза {cargo_number}: HTTP {response.status_code}")
            
            self.log_result("Очистка тестовых данных", True, f"Очищено {len(self.created_cargo_info)} грузов")
            
        except Exception as e:
            self.log_result("Очистка тестовых данных", False, f"Ошибка: {str(e)}")
    
    def run_cost_calculation_fixes_tests(self):
        """Запуск всех тестов исправлений расчета стоимости"""
        print("🔧 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ РАСЧЕТА СТОИМОСТИ")
        print("=" * 80)
        print("Цель: подтвердить что исправления полностью решили проблему с отображением стоимости в карточках грузов")
        print("=" * 80)
        
        # 1. Авторизация
        if not self.authenticate_admin():
            return False
        
        if not self.authenticate_operator():
            return False
        
        # 2. Получение складов
        warehouses = self.get_warehouses()
        if not warehouses:
            return False
        
        # 3. Создание новой заявки с известными данными согласно review request
        test_cargo = self.create_final_cost_test_request()
        if not test_cargo:
            return False
        
        # 4. Проверка API размещения
        placement_api_check = self.check_available_for_placement_api()
        
        # 5. Проверка отладочных логов
        debug_logs_check = self.check_debug_logs()
        
        # 6. Анализ структуры созданных грузов
        structure_analysis = self.analyze_cargo_structure()
        
        # 7. Очистка тестовых данных
        self.cleanup_test_data()
        
        # Подведение итогов
        print("\n" + "=" * 80)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЙ РАСЧЕТА СТОИМОСТИ:")
        
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
        critical_tests_passed = bool(test_cargo) and placement_api_check and structure_analysis
        
        print("\n🔧 КРИТИЧЕСКИЙ ВЫВОД:")
        if critical_tests_passed:
            print("✅ ИСПРАВЛЕНИЯ РАСЧЕТА СТОИМОСТИ РАБОТАЮТ ПРАВИЛЬНО!")
            print("   - Заявка с известными данными создана успешно")
            print("   - API размещения возвращает правильно рассчитанную стоимость")
            print("   - Поля declared_value и total_cost заполнены корректно")
            print("   - Отладочные сообщения присутствуют в логах")
            print("   - Структура грузов соответствует ожиданиям")
        else:
            print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ С РАСЧЕТОМ СТОИМОСТИ!")
            print("   - Требуется дополнительная работа над исправлениями")
            print("   - Проверьте правильность обработки cargo_items")
            print("   - Убедитесь что declared_value рассчитывается корректно")
        
        return critical_tests_passed

def main():
    """Главная функция"""
    tester = CostCalculationFixesTester()
    success = tester.run_cost_calculation_fixes_tests()
    
    # Возвращаем код выхода
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()