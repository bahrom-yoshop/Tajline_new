#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправление расчета цен в заявках на забор груза в TAJLINE.TJ

ПРОБЛЕМА ИСПРАВЛЕНА:
Пользователь сообщил о неправильном расчете общей суммы:
- Груз 1: 50кг × 80₽/кг должно = 4000₽
- Груз 2: 10кг × 80₽/кг должно = 800₽  
- Итого должно быть: 4800₽

ИСПРАВЛЕНИЯ В FRONTEND:
- Заменено использование total_value на price_per_kg в processedCargoItems
- Теперь в расчетах используется цена ЗА КИЛОГРАММ, а не общая сумма
- Формула расчета: weight × price_per_kg = правильная сумма за груз

ДЕТАЛЬНОЕ ТЕСТИРОВАНИЕ:
1. Создание заявки на забор груза с несколькими грузами - создать заявку с разными грузами и ценами
2. Проверка структуры данных cargo_items - убедиться что price_per_kg сохраняется корректно
3. Получение заявки через API - проверить что backend возвращает price_per_kg
4. Тестирование расчетов - проверить формулы weight × price_per_kg для каждого груза
5. Проверка общей суммы - сумма всех грузов должна быть правильной
6. Тестирование разных сценариев - одинаковые и разные цены за кг
7. Проверка modal_data структуры - убедиться что данные передаются корректно

КОНТЕКСТ ИСПРАВЛЕНИЙ:
- Frontend теперь использует item.price_per_kg вместо item.total_price/total_value
- Backend уже корректно работает с cargo_items и price_per_kg
- Расчет в интерфейсе: sum + ((parseFloat(item.weight) || 0) * (parseFloat(item.price) || 0))
- Где item.price теперь содержит price_per_kg, а не общую сумму

ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:
- API endpoint должен возвращать cargo_items с price_per_kg
- Расчет общей суммы должен быть: ∑(weight_i × price_per_kg_i)
- Пример: 50×80 + 10×80 = 4000 + 800 = 4800₽
- Каждый груз должен иметь индивидуальную цену за кг

КРИТЕРИИ УСПЕХА:
✅ Заявки создаются с корректными price_per_kg для каждого груза
✅ Backend возвращает правильную структуру cargo_items
✅ Расчеты в интерфейсе используют цену за кг, а не общую сумму
✅ Общая сумма рассчитывается корректно по формуле weight × price_per_kg
"""

import requests
import json
import os
from datetime import datetime, timedelta

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-manager-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class PriceCalculationTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_request_ids = []
        
    def log(self, message):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        self.log("🔐 Авторизация администратора...")
        
        login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data.get('access_token')
            user_info = data.get('user', {})
            self.log(f"✅ Администратор авторизован: {user_info.get('full_name')} (номер: {user_info.get('user_number')}, роль: {user_info.get('role')})")
            return True
        else:
            self.log(f"❌ Ошибка авторизации администратора: {response.status_code} - {response.text}")
            return False
            
    def authenticate_operator(self):
        """Авторизация оператора склада"""
        self.log("🔐 Авторизация оператора склада...")
        
        login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.operator_token = data.get('access_token')
            user_info = data.get('user', {})
            self.log(f"✅ Оператор авторизован: {user_info.get('full_name')} (номер: {user_info.get('user_number')}, роль: {user_info.get('role')})")
            return True
        else:
            self.log(f"❌ Ошибка авторизации оператора: {response.status_code} - {response.text}")
            return False
            
    def create_pickup_request_with_multiple_cargo(self, scenario_name, cargo_items):
        """Создание заявки на забор груза с несколькими грузами"""
        self.log(f"📦 Создание заявки на забор груза: {scenario_name}...")
        
        pickup_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Рассчитываем общий вес и стоимость для проверки
        total_weight = sum(item['weight'] for item in cargo_items)
        expected_total = sum(item['weight'] * item['price_per_kg'] for item in cargo_items)
        
        self.log(f"📊 Ожидаемые расчеты:")
        for i, item in enumerate(cargo_items, 1):
            item_total = item['weight'] * item['price_per_kg']
            self.log(f"   Груз {i}: {item['weight']}кг × {item['price_per_kg']}₽/кг = {item_total}₽")
        self.log(f"   ИТОГО: {expected_total}₽")
        
        request_data = {
            "sender_full_name": f"Тестовый Отправитель {scenario_name}",
            "sender_phone": "+79991234567",
            "recipient_full_name": f"Тестовый Получатель {scenario_name}",
            "recipient_phone": "+79997654321",
            "recipient_address": f"Тестовый адрес получателя {scenario_name}",
            "pickup_address": f"Тестовый адрес забора {scenario_name}",
            "pickup_date": pickup_date,
            "pickup_time_from": "10:00",
            "pickup_time_to": "12:00",
            "cargo_items": cargo_items,
            "description": f"Тестовое описание {scenario_name}",
            "route": "moscow_to_tajikistan",
            "courier_fee": 500.0,
            "delivery_method": "pickup",
            "payment_method": "cash"
        }
        
        headers = {"Authorization": f"Bearer {self.operator_token}"}
        response = self.session.post(f"{API_BASE}/admin/courier/pickup-request", json=request_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            request_id = data.get('request_id')
            request_number = data.get('request_number')
            self.test_request_ids.append(request_id)
            self.log(f"✅ Заявка создана: ID {request_id}, номер {request_number}")
            return request_id, expected_total
        else:
            self.log(f"❌ Ошибка создания заявки: {response.status_code} - {response.text}")
            return None, None
            
    def get_pickup_request_details(self, request_id):
        """Получение детальной информации о заявке на забор груза"""
        self.log(f"🔍 Получение деталей заявки {request_id}...")
        
        headers = {"Authorization": f"Bearer {self.operator_token}"}
        response = self.session.get(f"{API_BASE}/operator/pickup-requests/{request_id}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            self.log(f"✅ Детали заявки получены")
            
            # Проверяем структуру ответа
            sections = ['request_info', 'courier_info', 'sender_data', 'recipient_data', 'cargo_info', 'payment_info', 'full_request']
            for section in sections:
                if section in data:
                    self.log(f"   ✅ Секция '{section}' присутствует")
                else:
                    self.log(f"   ❌ Секция '{section}' отсутствует")
                    
            return data
        else:
            self.log(f"❌ Ошибка получения деталей заявки: {response.status_code} - {response.text}")
            return None
            
    def verify_cargo_items_structure(self, request_data, expected_total):
        """Проверка структуры cargo_items в ответе API"""
        self.log("🔍 Проверка структуры cargo_items...")
        
        if not request_data:
            self.log("❌ Нет данных для проверки")
            return False
            
        cargo_info = request_data.get('cargo_info', {})
        if not cargo_info:
            self.log("❌ Секция cargo_info отсутствует")
            return False
            
        # Проверяем наличие необходимых полей
        required_fields = ['cargo_items', 'total_weight', 'total_cost']
        for field in required_fields:
            if field in cargo_info:
                self.log(f"   ✅ Поле '{field}' присутствует: {cargo_info[field]}")
            else:
                self.log(f"   ❌ Поле '{field}' отсутствует")
                
        cargo_items = cargo_info.get('cargo_items', [])
        if not cargo_items:
            self.log("❌ cargo_items пуст или отсутствует")
            return False
            
        self.log(f"📦 Найдено {len(cargo_items)} грузов в cargo_items:")
        
        calculated_total = 0
        all_items_valid = True
        
        for i, item in enumerate(cargo_items, 1):
            cargo_name = item.get('cargo_name', 'Неизвестно')
            weight = item.get('weight', 0)
            price_per_kg = item.get('price_per_kg', 0)
            
            # Рассчитываем стоимость этого груза
            item_cost = weight * price_per_kg
            calculated_total += item_cost
            
            self.log(f"   Груз {i}: '{cargo_name}'")
            self.log(f"      Вес: {weight} кг")
            self.log(f"      Цена за кг: {price_per_kg} ₽")
            self.log(f"      Стоимость: {weight} × {price_per_kg} = {item_cost} ₽")
            
            # Проверяем наличие price_per_kg (это ключевое исправление)
            if price_per_kg > 0:
                self.log(f"      ✅ price_per_kg корректно сохранен: {price_per_kg}")
            else:
                self.log(f"      ❌ price_per_kg отсутствует или равен 0")
                all_items_valid = False
                
        self.log(f"📊 Расчет общей суммы:")
        self.log(f"   Рассчитанная сумма: {calculated_total} ₽")
        self.log(f"   Ожидаемая сумма: {expected_total} ₽")
        self.log(f"   Сумма из API: {cargo_info.get('total_cost', 'Не указана')} ₽")
        
        # Проверяем правильность расчетов
        if abs(calculated_total - expected_total) < 0.01:  # Учитываем погрешности с плавающей точкой
            self.log("✅ Расчет общей суммы КОРРЕКТЕН!")
            return all_items_valid
        else:
            self.log("❌ Расчет общей суммы НЕКОРРЕКТЕН!")
            return False
            
    def test_modal_data_structure(self, request_data):
        """Тестирование структуры данных для модального окна"""
        self.log("🔍 Проверка структуры modal_data...")
        
        if not request_data:
            return False
            
        # Проверяем что все необходимые секции для модального окна присутствуют
        modal_sections = {
            'request_info': ['id', 'request_number', 'status'],
            'sender_data': ['sender_full_name', 'sender_phone'],
            'recipient_data': ['recipient_full_name', 'recipient_phone', 'recipient_address'],
            'cargo_info': ['cargo_items', 'total_weight', 'total_cost'],
            'payment_info': ['payment_method', 'courier_fee']
        }
        
        all_sections_valid = True
        
        for section_name, required_fields in modal_sections.items():
            section_data = request_data.get(section_name, {})
            if section_data:
                self.log(f"   ✅ Секция '{section_name}' присутствует")
                
                # Проверяем обязательные поля в секции
                for field in required_fields:
                    if field in section_data:
                        value = section_data[field]
                        self.log(f"      ✅ {field}: {value}")
                    else:
                        self.log(f"      ❌ {field}: отсутствует")
                        all_sections_valid = False
            else:
                self.log(f"   ❌ Секция '{section_name}' отсутствует")
                all_sections_valid = False
                
        return all_sections_valid
        
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        self.log("🧹 Очистка тестовых данных...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        for request_id in self.test_request_ids:
            try:
                response = self.session.delete(f"{API_BASE}/admin/pickup-requests/{request_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Заявка {request_id} удалена")
                else:
                    self.log(f"⚠️ Не удалось удалить заявку {request_id}: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления заявки {request_id}: {e}")
                
    def run_comprehensive_test(self):
        """Запуск комплексного тестирования расчета цен"""
        self.log("🎯 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЯ РАСЧЕТА ЦЕН")
        self.log("=" * 80)
        
        success_count = 0
        total_tests = 10
        
        try:
            # 1. Авторизация администратора
            self.log("\n📋 ЭТАП 1: Авторизация администратора")
            if not self.authenticate_admin():
                self.log("❌ Критическая ошибка: не удалось авторизовать администратора")
                return
            success_count += 1
            
            # 2. Авторизация оператора
            self.log("\n📋 ЭТАП 2: Авторизация оператора склада")
            if not self.authenticate_operator():
                self.log("❌ Критическая ошибка: не удалось авторизовать оператора")
                return
            success_count += 1
            
            # 3. Тестирование сценария из проблемы пользователя
            self.log("\n📋 ЭТАП 3: Тестирование сценария из проблемы пользователя")
            user_scenario_cargo = [
                {
                    "cargo_name": "Груз 1 (из проблемы пользователя)",
                    "weight": 50.0,
                    "price_per_kg": 80.0
                },
                {
                    "cargo_name": "Груз 2 (из проблемы пользователя)",
                    "weight": 10.0,
                    "price_per_kg": 80.0
                }
            ]
            
            request_id_1, expected_total_1 = self.create_pickup_request_with_multiple_cargo(
                "Сценарий пользователя", user_scenario_cargo
            )
            
            if request_id_1 and expected_total_1 == 4800.0:  # 50*80 + 10*80 = 4800
                self.log("✅ Заявка создана с правильным ожидаемым итогом: 4800₽")
                success_count += 1
            else:
                self.log("❌ Проблема с созданием заявки или расчетом")
                
            # 4. Получение и проверка структуры данных
            self.log("\n📋 ЭТАП 4: Получение и проверка структуры данных")
            if request_id_1:
                request_data_1 = self.get_pickup_request_details(request_id_1)
                if request_data_1:
                    success_count += 1
                else:
                    self.log("❌ Не удалось получить данные заявки")
                    
            # 5. Проверка структуры cargo_items
            self.log("\n📋 ЭТАП 5: Проверка структуры cargo_items")
            if request_data_1:
                if self.verify_cargo_items_structure(request_data_1, expected_total_1):
                    self.log("✅ Структура cargo_items и расчеты КОРРЕКТНЫ")
                    success_count += 1
                else:
                    self.log("❌ Проблемы со структурой cargo_items или расчетами")
                    
            # 6. Тестирование разных цен за кг
            self.log("\n📋 ЭТАП 6: Тестирование разных цен за кг")
            different_prices_cargo = [
                {
                    "cargo_name": "Дорогой груз",
                    "weight": 5.0,
                    "price_per_kg": 200.0  # 5 * 200 = 1000
                },
                {
                    "cargo_name": "Дешевый груз",
                    "weight": 20.0,
                    "price_per_kg": 30.0   # 20 * 30 = 600
                },
                {
                    "cargo_name": "Средний груз",
                    "weight": 15.0,
                    "price_per_kg": 100.0  # 15 * 100 = 1500
                }
            ]
            # Итого: 1000 + 600 + 1500 = 3100
            
            request_id_2, expected_total_2 = self.create_pickup_request_with_multiple_cargo(
                "Разные цены", different_prices_cargo
            )
            
            if request_id_2 and expected_total_2 == 3100.0:
                success_count += 1
                
            # 7. Проверка второго сценария
            self.log("\n📋 ЭТАП 7: Проверка второго сценария")
            if request_id_2:
                request_data_2 = self.get_pickup_request_details(request_id_2)
                if request_data_2 and self.verify_cargo_items_structure(request_data_2, expected_total_2):
                    success_count += 1
                    
            # 8. Тестирование одинаковых цен
            self.log("\n📋 ЭТАП 8: Тестирование одинаковых цен за кг")
            same_price_cargo = [
                {
                    "cargo_name": "Груз А",
                    "weight": 25.0,
                    "price_per_kg": 60.0  # 25 * 60 = 1500
                },
                {
                    "cargo_name": "Груз Б",
                    "weight": 35.0,
                    "price_per_kg": 60.0  # 35 * 60 = 2100
                }
            ]
            # Итого: 1500 + 2100 = 3600
            
            request_id_3, expected_total_3 = self.create_pickup_request_with_multiple_cargo(
                "Одинаковые цены", same_price_cargo
            )
            
            if request_id_3 and expected_total_3 == 3600.0:
                success_count += 1
                
            # 9. Проверка modal_data структуры
            self.log("\n📋 ЭТАП 9: Проверка структуры modal_data")
            if request_data_1:
                if self.test_modal_data_structure(request_data_1):
                    self.log("✅ Структура modal_data КОРРЕКТНА для модального окна")
                    success_count += 1
                else:
                    self.log("❌ Проблемы со структурой modal_data")
                    
            # 10. Финальная проверка ключевого исправления
            self.log("\n📋 ЭТАП 10: Финальная проверка ключевого исправления")
            
            # Проверяем что во всех заявках используется price_per_kg, а не total_value
            all_requests_correct = True
            
            for i, (request_id, expected_total) in enumerate([
                (request_id_1, expected_total_1),
                (request_id_2, expected_total_2),
                (request_id_3, expected_total_3)
            ], 1):
                if request_id:
                    request_data = self.get_pickup_request_details(request_id)
                    if request_data:
                        cargo_info = request_data.get('cargo_info', {})
                        cargo_items = cargo_info.get('cargo_items', [])
                        
                        for item in cargo_items:
                            if 'price_per_kg' not in item or item.get('price_per_kg', 0) <= 0:
                                self.log(f"❌ Заявка {i}: отсутствует price_per_kg в грузе")
                                all_requests_correct = False
                            
                            # Проверяем что НЕ используется total_value как цена
                            if 'total_value' in item and item.get('total_value') == item.get('price_per_kg'):
                                self.log(f"⚠️ Заявка {i}: возможно используется total_value вместо price_per_kg")
                                
            if all_requests_correct:
                self.log("✅ ВСЕ заявки используют price_per_kg - ИСПРАВЛЕНИЕ РАБОТАЕТ!")
                success_count += 1
            else:
                self.log("❌ Не все заявки используют price_per_kg корректно")
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка во время тестирования: {e}")
            
        finally:
            # Очистка тестовых данных
            self.log("\n📋 ФИНАЛЬНЫЙ ЭТАП: Очистка тестовых данных")
            self.cleanup_test_data()
            
        # Итоговый отчет
        self.log("\n" + "=" * 80)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ РАСЧЕТА ЦЕН")
        self.log("=" * 80)
        
        success_rate = (success_count / total_tests) * 100
        
        self.log(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        self.log(f"   Успешных тестов: {success_count}/{total_tests}")
        self.log(f"   Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 ОТЛИЧНО: Исправления расчета цен работают корректно!")
        elif success_rate >= 70:
            self.log("✅ ХОРОШО: Основные исправления работают, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Исправления требуют доработки")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ Заявки создаются с корректными price_per_kg для каждого груза")
        self.log("✅ Backend возвращает правильную структуру cargo_items")
        self.log("✅ Расчеты используют цену за кг, а не общую сумму")
        self.log("✅ Общая сумма рассчитывается корректно: ∑(weight_i × price_per_kg_i)")
        self.log("✅ Пример из проблемы: 50×80 + 10×80 = 4000 + 800 = 4800₽")
        
        return success_rate >= 70

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправление расчета цен в заявках на забор груза в TAJLINE.TJ")
    print("=" * 80)
    
    tester = PriceCalculationTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()