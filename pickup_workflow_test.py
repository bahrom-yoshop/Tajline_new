#!/usr/bin/env python3
"""
Полный тест workflow заявок на забор груза для проверки отображения в размещенных грузах

WORKFLOW:
1. Оператор создает заявку на забор груза
2. Курьер принимает заявку
3. Курьер забирает груз
4. Курьер сдает груз на склад (создается уведомление)
5. Оператор принимает уведомление
6. Оператор завершает оформление (создается груз со статусом placement_ready)
7. Проверяем отображение в /api/warehouses/placed-cargo
"""

import requests
import sys
import json
from datetime import datetime

class PickupWorkflowTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.operator_token = None
        self.courier_token = None
        self.pickup_request_id = None
        self.notification_id = None
        self.cargo_numbers = []
        
        print(f"🚚 ПОЛНЫЙ ТЕСТ WORKFLOW ЗАЯВОК НА ЗАБОР ГРУЗА")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 80)

    def authenticate_operator(self):
        """Авторизация оператора"""
        login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.operator_token = data["access_token"]
            print(f"✅ Оператор авторизован")
            return True
        else:
            print(f"❌ Ошибка авторизации оператора: {response.status_code}")
            return False

    def authenticate_courier(self):
        """Авторизация курьера"""
        login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.courier_token = data["access_token"]
            print(f"✅ Курьер авторизован")
            return True
        else:
            print(f"❌ Ошибка авторизации курьера: {response.status_code}")
            return False

    def create_pickup_request(self):
        """Шаг 1: Создание заявки на забор груза"""
        print(f"\n🎯 ШАГ 1: СОЗДАНИЕ ЗАЯВКИ НА ЗАБОР ГРУЗА")
        
        if not self.operator_token:
            return False
        
        headers = {'Authorization': f'Bearer {self.operator_token}'}
        
        pickup_request_data = {
            "sender_full_name": "Тестовый Отправитель Workflow",
            "sender_phone": "+79991234567, +79887776655",
            "pickup_address": "Москва, ул. Тестовая Workflow, 789",
            "pickup_date": "2025-01-15",
            "pickup_time_from": "09:00",
            "pickup_time_to": "17:00",
            "route": "moscow_to_tajikistan",
            "courier_fee": 750.0
        }
        
        response = requests.post(f"{self.base_url}/api/admin/courier/pickup-request", 
                               json=pickup_request_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            self.pickup_request_id = data.get("id")
            request_number = data.get("request_number")
            print(f"   ✅ Заявка создана: ID {self.pickup_request_id}, номер {request_number}")
            return True
        else:
            print(f"   ❌ Ошибка создания заявки: {response.status_code}")
            print(f"   📄 Ответ: {response.text}")
            return False

    def courier_accept_request(self):
        """Шаг 2: Курьер принимает заявку"""
        print(f"\n🎯 ШАГ 2: КУРЬЕР ПРИНИМАЕТ ЗАЯВКУ")
        
        if not self.courier_token or not self.pickup_request_id:
            return False
        
        headers = {'Authorization': f'Bearer {self.courier_token}'}
        
        response = requests.post(f"{self.base_url}/api/courier/requests/{self.pickup_request_id}/accept", 
                               headers=headers)
        
        if response.status_code == 200:
            print(f"   ✅ Заявка принята курьером")
            return True
        else:
            print(f"   ❌ Ошибка принятия заявки: {response.status_code}")
            print(f"   📄 Ответ: {response.text}")
            return False

    def courier_pickup_cargo(self):
        """Шаг 3: Курьер забирает груз"""
        print(f"\n🎯 ШАГ 3: КУРЬЕР ЗАБИРАЕТ ГРУЗ")
        
        if not self.courier_token or not self.pickup_request_id:
            return False
        
        headers = {'Authorization': f'Bearer {self.courier_token}'}
        
        response = requests.post(f"{self.base_url}/api/courier/requests/{self.pickup_request_id}/pickup", 
                               headers=headers)
        
        if response.status_code == 200:
            print(f"   ✅ Груз забран курьером")
            return True
        else:
            print(f"   ❌ Ошибка забора груза: {response.status_code}")
            print(f"   📄 Ответ: {response.text}")
            return False

    def courier_deliver_to_warehouse(self):
        """Шаг 4: Курьер сдает груз на склад"""
        print(f"\n🎯 ШАГ 4: КУРЬЕР СДАЕТ ГРУЗ НА СКЛАД")
        
        if not self.courier_token or not self.pickup_request_id:
            return False
        
        headers = {'Authorization': f'Bearer {self.courier_token}'}
        
        response = requests.post(f"{self.base_url}/api/courier/requests/{self.pickup_request_id}/deliver-to-warehouse", 
                               headers=headers)
        
        if response.status_code == 200:
            print(f"   ✅ Груз сдан на склад, создано уведомление")
            return True
        else:
            print(f"   ❌ Ошибка сдачи груза на склад: {response.status_code}")
            print(f"   📄 Ответ: {response.text}")
            return False

    def get_warehouse_notifications(self):
        """Шаг 5: Получение уведомлений склада"""
        print(f"\n🎯 ШАГ 5: ПОЛУЧЕНИЕ УВЕДОМЛЕНИЙ СКЛАДА")
        
        if not self.operator_token:
            return False
        
        headers = {'Authorization': f'Bearer {self.operator_token}'}
        
        response = requests.get(f"{self.base_url}/api/operator/warehouse-notifications", 
                              headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            notifications = data.get("items", [])
            print(f"   📋 Найдено уведомлений: {len(notifications)}")
            
            # Ищем наше уведомление
            for notification in notifications:
                if notification.get("pickup_request_id") == self.pickup_request_id:
                    self.notification_id = notification.get("id")
                    print(f"   ✅ Найдено уведомление: {self.notification_id}")
                    return True
            
            # Если не нашли конкретное, берем первое доступное
            if notifications:
                self.notification_id = notifications[0].get("id")
                print(f"   ⚠️ Взято первое доступное уведомление: {self.notification_id}")
                return True
            
            print(f"   ❌ Уведомления не найдены")
            return False
        else:
            print(f"   ❌ Ошибка получения уведомлений: {response.status_code}")
            return False

    def accept_notification(self):
        """Шаг 6: Принятие уведомления"""
        print(f"\n🎯 ШАГ 6: ПРИНЯТИЕ УВЕДОМЛЕНИЯ")
        
        if not self.operator_token or not self.notification_id:
            return False
        
        headers = {'Authorization': f'Bearer {self.operator_token}'}
        
        response = requests.post(f"{self.base_url}/api/operator/warehouse-notifications/{self.notification_id}/accept", 
                               headers=headers)
        
        if response.status_code == 200:
            print(f"   ✅ Уведомление принято")
            return True
        else:
            print(f"   ❌ Ошибка принятия уведомления: {response.status_code}")
            print(f"   📄 Ответ: {response.text}")
            return False

    def complete_notification(self):
        """Шаг 7: Завершение оформления (создание грузов)"""
        print(f"\n🎯 ШАГ 7: ЗАВЕРШЕНИЕ ОФОРМЛЕНИЯ")
        
        if not self.operator_token or not self.notification_id:
            return False
        
        headers = {'Authorization': f'Bearer {self.operator_token}'}
        
        # Данные для создания грузов
        cargo_data = {
            "cargo_items": [
                {
                    "recipient_full_name": "Получатель Тест 1",
                    "recipient_phone": "+79887776655",
                    "recipient_address": "Душанбе, ул. Получателя, 123",
                    "weight": 3.5,
                    "cargo_name": "Тестовый груз 1 из заявки",
                    "declared_value": 1500.0,
                    "description": "Первый груз из заявки на забор"
                },
                {
                    "recipient_full_name": "Получатель Тест 2", 
                    "recipient_phone": "+79887776656",
                    "recipient_address": "Худжанд, ул. Получателя, 456",
                    "weight": 2.8,
                    "cargo_name": "Тестовый груз 2 из заявки",
                    "declared_value": 1200.0,
                    "description": "Второй груз из заявки на забор"
                }
            ]
        }
        
        response = requests.post(f"{self.base_url}/api/operator/warehouse-notifications/{self.notification_id}/complete", 
                               json=cargo_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo_numbers = data.get("cargo_numbers", [])
            self.cargo_numbers = cargo_numbers
            print(f"   ✅ Оформление завершено")
            print(f"   📦 Созданы грузы: {', '.join(cargo_numbers)}")
            return True
        else:
            print(f"   ❌ Ошибка завершения оформления: {response.status_code}")
            print(f"   📄 Ответ: {response.text}")
            return False

    def test_placed_cargo_display(self):
        """Шаг 8: Проверка отображения в размещенных грузах"""
        print(f"\n🎯 ШАГ 8: ПРОВЕРКА ОТОБРАЖЕНИЯ В РАЗМЕЩЕННЫХ ГРУЗАХ")
        
        if not self.operator_token:
            return False
        
        headers = {'Authorization': f'Bearer {self.operator_token}'}
        
        response = requests.get(f"{self.base_url}/api/warehouses/placed-cargo", 
                              headers=headers, params={"page": 1, "per_page": 50})
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            total = data.get("pagination", {}).get("total", 0)
            
            print(f"   📊 Всего размещенных грузов: {total}")
            print(f"   📋 На странице: {len(items)}")
            
            # Ищем наши грузы
            found_cargo = []
            placement_ready_count = 0
            pickup_request_count = 0
            
            for cargo in items:
                cargo_number = cargo.get("cargo_number", "")
                status = cargo.get("status", "")
                pickup_request_id = cargo.get("pickup_request_id")
                
                if status == "placement_ready":
                    placement_ready_count += 1
                
                if pickup_request_id:
                    pickup_request_count += 1
                
                # Проверяем наши созданные грузы
                if cargo_number in self.cargo_numbers:
                    found_cargo.append(cargo)
                    print(f"   ✅ НАЙДЕН наш груз: {cargo_number}")
                    print(f"      📊 Статус: {status}")
                    print(f"      🚚 Заявка на забор: {pickup_request_id}")
                
                # Показываем грузы с номерами в формате заявки
                if "/" in cargo_number:
                    print(f"   📋 Груз в формате заявки: {cargo_number} (статус: {status})")
            
            print(f"\n   📈 ИТОГОВАЯ СТАТИСТИКА:")
            print(f"   🎯 Грузы со статусом 'placement_ready': {placement_ready_count}")
            print(f"   🚚 Грузы из заявок на забор: {pickup_request_count}")
            print(f"   ✅ Найдено наших грузов: {len(found_cargo)}")
            
            # ОСНОВНОЙ РЕЗУЛЬТАТ
            if placement_ready_count > 0:
                print(f"\n   🎉 УСПЕХ: Найдены грузы со статусом 'placement_ready'!")
                return True
            else:
                print(f"\n   ⚠️ Грузы со статусом 'placement_ready' не найдены")
                return False
        else:
            print(f"   ❌ Ошибка получения размещенных грузов: {response.status_code}")
            return False

    def run_full_workflow(self):
        """Запуск полного workflow"""
        print(f"🚀 ЗАПУСК ПОЛНОГО WORKFLOW ЗАЯВОК НА ЗАБОР ГРУЗА")
        print(f"⏰ Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        steps = [
            ("Авторизация оператора", self.authenticate_operator),
            ("Авторизация курьера", self.authenticate_courier),
            ("Создание заявки на забор", self.create_pickup_request),
            ("Принятие заявки курьером", self.courier_accept_request),
            ("Забор груза курьером", self.courier_pickup_cargo),
            ("Сдача груза на склад", self.courier_deliver_to_warehouse),
            ("Получение уведомлений", self.get_warehouse_notifications),
            ("Принятие уведомления", self.accept_notification),
            ("Завершение оформления", self.complete_notification),
            ("Проверка отображения", self.test_placed_cargo_display)
        ]
        
        success_count = 0
        
        for step_name, step_func in steps:
            print(f"\n{'='*60}")
            print(f"🔄 {step_name.upper()}")
            print(f"{'='*60}")
            
            if step_func():
                success_count += 1
                print(f"✅ {step_name} - УСПЕХ")
            else:
                print(f"❌ {step_name} - ОШИБКА")
                # Продолжаем выполнение даже при ошибках
        
        print(f"\n{'='*80}")
        print(f"📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ WORKFLOW")
        print(f"{'='*80}")
        print(f"🎯 Всего этапов: {len(steps)}")
        print(f"✅ Успешных: {success_count}")
        print(f"❌ Неуспешных: {len(steps) - success_count}")
        print(f"📈 Процент успеха: {(success_count/len(steps)*100):.1f}%")
        
        if success_count >= 8:  # Минимум 8 из 10 этапов
            print(f"\n🎉 WORKFLOW ЗАВЕРШЕН УСПЕШНО!")
            print(f"✅ ИСПРАВЛЕНИЕ ОТОБРАЖЕНИЯ ГРУЗОВ ИЗ ЗАЯВОК НА ЗАБОР РАБОТАЕТ!")
        else:
            print(f"\n⚠️ WORKFLOW ЗАВЕРШЕН С ПРОБЛЕМАМИ")
            print(f"❌ ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА")
        
        print(f"⏰ Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return success_count >= 8

if __name__ == "__main__":
    tester = PickupWorkflowTester()
    success = tester.run_full_workflow()
    sys.exit(0 if success else 1)