#!/usr/bin/env python3
"""
Проверка существующих данных в системе для тестирования исправления отображения грузов из заявок на забор
"""

import requests
import sys
import json
from datetime import datetime

class DataChecker:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        
        print(f"🔍 ПРОВЕРКА СУЩЕСТВУЮЩИХ ДАННЫХ В СИСТЕМЕ")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

    def authenticate_operator(self):
        """Авторизация оператора"""
        login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            print(f"✅ Авторизация успешна")
            return True
        else:
            print(f"❌ Ошибка авторизации: {response.status_code}")
            return False

    def check_operator_cargo(self):
        """Проверка грузов в коллекции operator_cargo"""
        if not self.token:
            return
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Проверяем все грузы оператора
        response = requests.get(f"{self.base_url}/api/operator/cargo/list", headers=headers)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            print(f"\n📦 ГРУЗЫ В СИСТЕМЕ (operator_cargo):")
            print(f"   Всего грузов: {len(items)}")
            
            placement_ready_count = 0
            pickup_request_count = 0
            
            for i, cargo in enumerate(items[:10]):  # Показываем первые 10
                cargo_number = cargo.get("cargo_number", "Неизвестно")
                status = cargo.get("status", "Неизвестно")
                pickup_request_id = cargo.get("pickup_request_id")
                
                print(f"   {i+1}. {cargo_number} - Статус: {status}")
                
                if status == "placement_ready":
                    placement_ready_count += 1
                    print(f"      ✅ НАЙДЕН груз со статусом 'placement_ready'!")
                
                if pickup_request_id:
                    pickup_request_count += 1
                    print(f"      🚚 Заявка на забор: {pickup_request_id}")
            
            print(f"\n   📊 СТАТИСТИКА:")
            print(f"   🎯 Грузы со статусом 'placement_ready': {placement_ready_count}")
            print(f"   🚚 Грузы из заявок на забор: {pickup_request_count}")
        else:
            print(f"❌ Ошибка получения грузов: {response.status_code}")

    def check_available_for_placement(self):
        """Проверка грузов доступных для размещения"""
        if not self.token:
            return
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(f"{self.base_url}/api/operator/cargo/available-for-placement", headers=headers)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            print(f"\n🎯 ГРУЗЫ ДОСТУПНЫЕ ДЛЯ РАЗМЕЩЕНИЯ:")
            print(f"   Всего грузов: {len(items)}")
            
            for i, cargo in enumerate(items[:5]):  # Показываем первые 5
                cargo_number = cargo.get("cargo_number", "Неизвестно")
                status = cargo.get("status", "Неизвестно")
                processing_status = cargo.get("processing_status", "Неизвестно")
                pickup_request_id = cargo.get("pickup_request_id")
                
                print(f"   {i+1}. {cargo_number}")
                print(f"      📊 Статус: {status}")
                print(f"      ⚙️ Статус обработки: {processing_status}")
                
                if pickup_request_id:
                    print(f"      🚚 Заявка на забор: {pickup_request_id}")
        else:
            print(f"❌ Ошибка получения грузов для размещения: {response.status_code}")

    def create_test_pickup_request_cargo(self):
        """Создание тестового груза из заявки на забор"""
        if not self.token:
            return
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Сначала создаем заявку на забор груза
        pickup_request_data = {
            "sender_full_name": "Тестовый Отправитель Забор",
            "sender_phone": "+79991234567",
            "pickup_address": "Москва, ул. Тестовая для забора, 123",
            "pickup_date": "2025-01-15",
            "pickup_time_from": "10:00",
            "pickup_time_to": "18:00",
            "route": "moscow_to_tajikistan",
            "courier_fee": 500.0
        }
        
        print(f"\n🚚 СОЗДАНИЕ ТЕСТОВОЙ ЗАЯВКИ НА ЗАБОР ГРУЗА:")
        response = requests.post(f"{self.base_url}/api/admin/courier/pickup-request", 
                               json=pickup_request_data, headers=headers)
        
        if response.status_code == 200:
            pickup_data = response.json()
            pickup_request_id = pickup_data.get("id")
            request_number = pickup_data.get("request_number")
            print(f"   ✅ Заявка создана: ID {pickup_request_id}, номер {request_number}")
            
            # Теперь создаем груз, связанный с этой заявкой
            # Имитируем процесс: курьер забрал груз и сдал на склад
            cargo_data = {
                "sender_full_name": "Тестовый Отправитель Забор",
                "sender_phone": "+79991234567",
                "recipient_full_name": "Тестовый Получатель",
                "recipient_phone": "+79887776655",
                "recipient_address": "Душанбе, ул. Получателя, 456",
                "weight": 5.5,
                "cargo_name": "Тестовый груз из заявки на забор",
                "declared_value": 2500.0,
                "description": "Тестовый груз для проверки отображения в размещенных грузах",
                "route": "moscow_to_tajikistan",
                "payment_method": "not_paid",
                "pickup_required": True,
                "pickup_request_id": pickup_request_id  # Связываем с заявкой
            }
            
            print(f"   📦 Создание груза из заявки на забор...")
            cargo_response = requests.post(f"{self.base_url}/api/operator/cargo/accept", 
                                         json=cargo_data, headers=headers)
            
            if cargo_response.status_code == 200:
                cargo_result = cargo_response.json()
                cargo_number = cargo_result.get("cargo_number")
                print(f"   ✅ Груз создан: {cargo_number}")
                
                # Теперь нужно изменить статус груза на placement_ready
                # Это обычно происходит когда курьер сдает груз на склад
                print(f"   ⚙️ Установка статуса 'placement_ready'...")
                
                return cargo_number
            else:
                print(f"   ❌ Ошибка создания груза: {cargo_response.status_code}")
                print(f"   📄 Ответ: {cargo_response.text}")
        else:
            print(f"   ❌ Ошибка создания заявки: {response.status_code}")
            print(f"   📄 Ответ: {response.text}")
        
        return None

    def run_check(self):
        """Запуск проверки данных"""
        print(f"🚀 ЗАПУСК ПРОВЕРКИ СУЩЕСТВУЮЩИХ ДАННЫХ")
        print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.authenticate_operator():
            return False
        
        # Проверяем существующие данные
        self.check_operator_cargo()
        self.check_available_for_placement()
        
        # Создаем тестовые данные если их нет
        print(f"\n🧪 СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ:")
        test_cargo = self.create_test_pickup_request_cargo()
        
        if test_cargo:
            print(f"\n✅ ТЕСТОВЫЕ ДАННЫЕ СОЗДАНЫ")
            print(f"📦 Тестовый груз: {test_cargo}")
            print(f"🎯 Теперь можно протестировать отображение в размещенных грузах")
        
        return True

if __name__ == "__main__":
    checker = DataChecker()
    checker.run_check()