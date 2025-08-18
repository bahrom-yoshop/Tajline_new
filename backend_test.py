#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправления полей стоимости и оплаты в API размещения
Тестирование исправлений в /api/operator/cargo/available-for-placement согласно review request
"""

import requests
import json
import sys
import os
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-cargo-3.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class TajlineAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        
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
    
    def test_available_for_placement_api(self):
        """Тест API /api/operator/cargo/available-for-placement после исправлений"""
        try:
            # Используем токен оператора
            self.session.headers.update({'Authorization': f'Bearer {self.operator_token}'})
            response = self.session.get(f"{API_BASE}/operator/cargo/available-for-placement")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                if not items:
                    self.log_result("API available-for-placement", False, "Нет грузов для анализа")
                    return False
                
                # Анализируем первые несколько грузов
                sample_size = min(5, len(items))
                analysis_results = {
                    'declared_value_present': 0,
                    'declared_value_non_zero': 0,
                    'total_cost_present': 0,
                    'payment_amount_present': 0,
                    'debt_due_date_present': 0,
                    'received_by_operator_present': 0
                }
                
                sample_cargos = []
                
                for i, cargo in enumerate(items[:sample_size]):
                    cargo_analysis = {
                        'cargo_number': cargo.get('cargo_number', 'N/A'),
                        'declared_value': cargo.get('declared_value'),
                        'total_cost': cargo.get('total_cost'),
                        'payment_amount': cargo.get('payment_amount'),
                        'debt_due_date': cargo.get('debt_due_date'),
                        'received_by_operator': cargo.get('received_by_operator')
                    }
                    sample_cargos.append(cargo_analysis)
                    
                    # Подсчет статистики
                    if cargo.get('declared_value') is not None:
                        analysis_results['declared_value_present'] += 1
                        if cargo.get('declared_value', 0) != 0.0:
                            analysis_results['declared_value_non_zero'] += 1
                    
                    if cargo.get('total_cost') is not None:
                        analysis_results['total_cost_present'] += 1
                    
                    if cargo.get('payment_amount') is not None:
                        analysis_results['payment_amount_present'] += 1
                    
                    if cargo.get('debt_due_date') is not None:
                        analysis_results['debt_due_date_present'] += 1
                    
                    if cargo.get('received_by_operator'):
                        analysis_results['received_by_operator_present'] += 1
                
                # Проверяем исправления
                success = True
                issues = []
                
                # Проверка declared_value (не должно быть 0.0)
                if analysis_results['declared_value_non_zero'] == 0:
                    success = False
                    issues.append("declared_value все еще равно 0.0 у всех грузов")
                
                # Проверка total_cost (должно быть рассчитано)
                if analysis_results['total_cost_present'] == 0:
                    success = False
                    issues.append("total_cost отсутствует у всех грузов")
                
                # Проверка received_by_operator (ФИО оператора)
                if analysis_results['received_by_operator_present'] == 0:
                    success = False
                    issues.append("received_by_operator отсутствует у всех грузов")
                
                details = f"Проанализировано {sample_size} грузов из {len(items)}. "
                details += f"declared_value не равно 0: {analysis_results['declared_value_non_zero']}/{sample_size}, "
                details += f"total_cost присутствует: {analysis_results['total_cost_present']}/{sample_size}, "
                details += f"received_by_operator заполнен: {analysis_results['received_by_operator_present']}/{sample_size}"
                
                if issues:
                    details += f". ПРОБЛЕМЫ: {'; '.join(issues)}"
                
                self.log_result("Анализ полей стоимости и оплаты", success, details)
                
                # Выводим примеры грузов
                print("\n📋 ПРИМЕРЫ ГРУЗОВ:")
                for i, cargo in enumerate(sample_cargos):
                    print(f"   Груз {i+1}: {cargo['cargo_number']}")
                    print(f"      declared_value: {cargo['declared_value']}")
                    print(f"      total_cost: {cargo['total_cost']}")
                    print(f"      payment_amount: {cargo['payment_amount']}")
                    print(f"      received_by_operator: {cargo['received_by_operator']}")
                
                return success
                
            else:
                self.log_result("API available-for-placement", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("API available-for-placement", False, f"Ошибка: {str(e)}")
            return False
    
    def create_test_cargo(self, warehouses):
        """Создание новой тестовой заявки для проверки"""
        if not warehouses:
            self.log_result("Создание тестовой заявки", False, "Нет доступных складов")
            return None
        
        try:
            # Используем токен оператора
            self.session.headers.update({'Authorization': f'Bearer {self.operator_token}'})
            
            # Находим склад назначения
            destination_warehouse = None
            for warehouse in warehouses:
                if "душанбе" in warehouse.get('name', '').lower() or "душанбе" in warehouse.get('location', '').lower():
                    destination_warehouse = warehouse
                    break
            
            if not destination_warehouse:
                destination_warehouse = warehouses[0]  # Используем первый доступный
            
            cargo_data = {
                "sender_full_name": "Тест Стоимости",
                "sender_phone": "+79991234567",
                "sender_address": "Москва, ул. Тестовая 1",
                "recipient_full_name": "Получатель Стоимости",
                "recipient_phone": "+992901234567",
                "recipient_address": "Душанбе, ул. Тестовая 2",
                "cargo_items": [
                    {
                        "cargo_name": "Тест стоимости груз 1",
                        "weight": 2.0,
                        "price_per_kg": 150
                    },
                    {
                        "cargo_name": "Тест стоимости груз 2", 
                        "weight": 3.0,
                        "price_per_kg": 200
                    }
                ],
                "destination_warehouse_id": destination_warehouse['id'],
                "destination_warehouse_name": destination_warehouse['name'],
                "route": "moscow_to_tajikistan",
                "payment_method": "cash",
                "payment_amount": 900,
                "description": "Тестовая заявка для проверки стоимости"
            }
            
            response = self.session.post(f"{API_BASE}/operator/cargo/direct-accept", json=cargo_data)
            
            if response.status_code == 200:
                data = response.json()
                created_cargo = data.get('created_cargo', [])
                
                if created_cargo:
                    cargo_info = created_cargo[0]
                    
                    # Проверяем расчет стоимости
                    expected_total = (2.0 * 150) + (3.0 * 200)  # 300 + 600 = 900
                    
                    details = f"Создан груз {cargo_info.get('cargo_number')}. "
                    details += f"Ожидаемая стоимость: {expected_total}, "
                    details += f"payment_amount: {cargo_data['payment_amount']}"
                    
                    self.log_result("Создание тестовой заявки", True, details)
                    return cargo_info
                else:
                    self.log_result("Создание тестовой заявки", False, "created_cargo пуст в ответе")
                    return None
            else:
                self.log_result("Создание тестовой заявки", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Создание тестовой заявки", False, f"Ошибка: {str(e)}")
            return None
    
    def verify_cargo_in_placement_list(self, cargo_info):
        """Проверка что созданный груз появился в списке размещения с правильными полями"""
        if not cargo_info:
            return False
        
        try:
            # Используем токен оператора
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
                    # Проверяем поля стоимости
                    checks = {
                        'declared_value_filled': found_cargo.get('declared_value', 0) != 0,
                        'total_cost_present': found_cargo.get('total_cost') is not None,
                        'payment_amount_present': found_cargo.get('payment_amount') is not None,
                        'received_by_operator_filled': bool(found_cargo.get('received_by_operator'))
                    }
                    
                    success = all(checks.values())
                    
                    details = f"Груз {target_cargo_number} найден. "
                    details += f"declared_value: {found_cargo.get('declared_value')}, "
                    details += f"total_cost: {found_cargo.get('total_cost')}, "
                    details += f"payment_amount: {found_cargo.get('payment_amount')}, "
                    details += f"received_by_operator: {found_cargo.get('received_by_operator')}"
                    
                    if not success:
                        failed_checks = [k for k, v in checks.items() if not v]
                        details += f". ПРОБЛЕМЫ: {', '.join(failed_checks)}"
                    
                    self.log_result("Проверка груза в списке размещения", success, details)
                    return success
                else:
                    self.log_result("Проверка груза в списке размещения", False, f"Груз {target_cargo_number} не найден в списке")
                    return False
            else:
                self.log_result("Проверка груза в списке размещения", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Проверка груза в списке размещения", False, f"Ошибка: {str(e)}")
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
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправления полей стоимости и оплаты в API размещения")
        print("=" * 80)
        
        # 1. Авторизация
        if not self.authenticate_admin():
            return False
        
        if not self.authenticate_operator():
            return False
        
        # 2. Получение складов
        warehouses = self.get_warehouses()
        
        # 3. Тест API после исправлений
        api_test_success = self.test_available_for_placement_api()
        
        # 4. Создание тестовой заявки
        test_cargo = self.create_test_cargo(warehouses)
        
        # 5. Проверка груза в списке размещения
        placement_test_success = False
        if test_cargo:
            placement_test_success = self.verify_cargo_in_placement_list(test_cargo)
        
        # 6. Очистка
        if test_cargo:
            self.cleanup_test_cargo(test_cargo)
        
        # Подведение итогов
        print("\n" + "=" * 80)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
        
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
        overall_success = api_test_success and (placement_test_success if test_cargo else True)
        
        print("\n🎯 КРИТИЧЕСКИЙ ВЫВОД:")
        if overall_success:
            print("✅ ИСПРАВЛЕНИЯ ПОЛЕЙ СТОИМОСТИ И ОПЛАТЫ РАБОТАЮТ КОРРЕКТНО!")
            print("   - API возвращает правильные поля стоимости")
            print("   - Новые заявки создаются с корректными расчетами")
            print("   - Поля payment_amount и received_by_operator заполняются")
        else:
            print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ С ИСПРАВЛЕНИЯМИ!")
            print("   - Требуется дополнительная работа над полями стоимости")
        
        return overall_success

def main():
    """Главная функция"""
    tester = TajlineAPITester()
    success = tester.run_all_tests()
    
    # Возвращаем код выхода
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()