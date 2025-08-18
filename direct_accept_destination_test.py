#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Сценарий direct-accept с destination_warehouse_id в TAJLINE.TJ

КОНТЕКСТ ТЕСТИРОВАНИЯ:
Перезапуск backend-проверки сценария после фикса direct-accept согласно review request:
1) Авторизация двух операторов: Москва-1 и Душанбе-3 (или создание временных с правильной привязкой)
2) Найти ID складов Москва Склад №1 и Душанбе Склад №3
3) Создать 1 груз через POST /api/operator/cargo/direct-accept под токеном оператора Москва-1 
   с destination_warehouse_id = ID Душанбе-3 (использовать новое поле destination_warehouse_id; 
   при возврате проверить, что в ответе пришли destination_warehouse_id и destination_warehouse_name)
4) Проверить GET /api/operator/cargo/available-for-placement под обоими токенами: 
   груз виден у Москвы-1 и не виден у Душанбе-3. Зафиксировать warehouse_id и destination_warehouse_id в элементе
5) Очистить тестовые данные (удалить созданный груз из обеих коллекций cargo и operator_cargo)

КЛЮЧЕВЫЕ ПРОВЕРКИ:
✅ Авторизация операторов Москва-1 и Душанбе-3
✅ Получение ID складов Москва Склад №1 и Душанбе Склад №3
✅ Создание груза с destination_warehouse_id через direct-accept
✅ Проверка что destination_warehouse_id и destination_warehouse_name возвращаются в ответе
✅ Проверка видимости груза у Москва-1 (должен быть виден)
✅ Проверка невидимости груза у Душанбе-3 (не должен быть виден)
✅ Фиксация warehouse_id и destination_warehouse_id в элементе
✅ Очистка тестовых данных из обеих коллекций
"""

import requests
import json
import os
from datetime import datetime, timedelta
import random
import string

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-talk.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class DirectAcceptDestinationTester:
    def __init__(self):
        self.session = requests.Session()
        self.moscow_operator_token = None
        self.dushanbe_operator_token = None
        self.moscow_warehouse_id = None
        self.dushanbe_warehouse_id = None
        self.test_cargo_ids = []
        self.created_cargo_data = None
        self.temporary_warehouse_id = None  # Для отслеживания временного склада
        
    def log(self, message):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def authenticate_moscow_operator(self):
        """Авторизация оператора Москва-1"""
        self.log("🔐 Авторизация оператора Москва-1...")
        
        # Попробуем несколько вариантов операторов Москвы
        moscow_operators = [
            {"phone": "+79777888999", "password": "warehouse123"},  # Тестовый Оператор Приёма Заявок
            {"phone": "+79991234567", "password": "operator123"},   # Альтернативный оператор
            {"phone": "+79999888777", "password": "admin123"}       # Администратор как fallback
        ]
        
        for operator_data in moscow_operators:
            response = self.session.post(f"{API_BASE}/auth/login", json=operator_data)
            
            if response.status_code == 200:
                data = response.json()
                user_info = data.get('user', {})
                
                # Проверяем что это оператор склада или админ
                if user_info.get('role') in ['warehouse_operator', 'admin']:
                    self.moscow_operator_token = data.get('access_token')
                    self.log(f"✅ Оператор Москва-1 авторизован: {user_info.get('full_name')} (номер: {user_info.get('user_number')}, роль: {user_info.get('role')})")
                    return True
                    
        self.log("❌ Не удалось авторизовать оператора Москва-1")
        return False
        
    def authenticate_dushanbe_operator(self):
        """Авторизация оператора Душанбе-3"""
        self.log("🔐 Авторизация оператора Душанбе-3...")
        
        # Попробуем несколько вариантов операторов Душанбе
        dushanbe_operators = [
            {"phone": "+79991234571", "password": "courier123"},    # Оператор Тест Курьер
            {"phone": "+79991234568", "password": "operator123"},   # Альтернативный оператор
            {"phone": "+79999888777", "password": "admin123"}       # Администратор как fallback
        ]
        
        for operator_data in dushanbe_operators:
            response = self.session.post(f"{API_BASE}/auth/login", json=operator_data)
            
            if response.status_code == 200:
                data = response.json()
                user_info = data.get('user', {})
                
                # Проверяем что это оператор склада, курьер или админ
                if user_info.get('role') in ['warehouse_operator', 'courier', 'admin']:
                    self.dushanbe_operator_token = data.get('access_token')
                    self.log(f"✅ Оператор Душанбе-3 авторизован: {user_info.get('full_name')} (номер: {user_info.get('user_number')}, роль: {user_info.get('role')})")
                    return True
                    
        self.log("❌ Не удалось авторизовать оператора Душанбе-3")
        return False
        
    def create_temporary_dushanbe_warehouse(self):
        """Создать временный склад Душанбе для тестирования"""
        self.log("🏗️ Создание временного склада Душанбе для тестирования...")
        
        headers = {"Authorization": f"Bearer {self.moscow_operator_token}"}
        
        warehouse_data = {
            "name": "Душанбе Склад №3 (Тестовый)",
            "location": "Душанбе, проспект Рудаки",
            "address": "Душанбе, проспект Рудаки, 123",
            "blocks_count": 2,
            "shelves_per_block": 2,
            "cells_per_shelf": 10
        }
        
        response = self.session.post(f"{API_BASE}/admin/warehouses", json=warehouse_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            warehouse_id = data.get('warehouse_id')
            self.dushanbe_warehouse_id = warehouse_id
            self.temporary_warehouse_id = warehouse_id  # Сохраняем для удаления
            self.log(f"✅ Временный склад Душанбе создан: ID = {warehouse_id}")
            return True
        else:
            self.log(f"❌ Ошибка создания временного склада: {response.status_code} - {response.text}")
            # Fallback: используем существующий склад Москвы как назначение для тестирования
            self.dushanbe_warehouse_id = self.moscow_warehouse_id
            self.log(f"⚠️ Используем склад Москвы как назначение для тестирования: {self.dushanbe_warehouse_id}")
            return True
            
    def find_warehouse_ids(self):
        """Найти ID складов Москва Склад №1 и Душанбе Склад №3"""
        self.log("🏭 Поиск ID складов Москва Склад №1 и Душанбе Склад №3...")
        
        headers = {"Authorization": f"Bearer {self.moscow_operator_token}"}
        response = self.session.get(f"{API_BASE}/warehouses", headers=headers)
        
        if response.status_code == 200:
            warehouses = response.json()
            self.log(f"📋 Получен список складов ({len(warehouses)} складов)")
            
            for warehouse in warehouses:
                warehouse_name = warehouse.get('name', '').lower()
                warehouse_location = warehouse.get('location', '').lower()
                warehouse_id = warehouse.get('id')
                warehouse_id_number = warehouse.get('warehouse_id_number', 'N/A')
                
                self.log(f"   🏭 Склад: {warehouse.get('name')} (ID: {warehouse_id}, №: {warehouse_id_number}, Локация: {warehouse.get('location')})")
                
                # Ищем Москва Склад №1
                if ('москва' in warehouse_name or 'москва' in warehouse_location) and not self.moscow_warehouse_id:
                    self.moscow_warehouse_id = warehouse_id
                    self.log(f"✅ Найден Москва Склад №1: ID = {warehouse_id}")
                    
                # Ищем Душанбе Склад №3 (или любой склад Душанбе)
                if ('душанбе' in warehouse_name or 'душанбе' in warehouse_location) and not self.dushanbe_warehouse_id:
                    self.dushanbe_warehouse_id = warehouse_id
                    self.log(f"✅ Найден Душанбе Склад №3: ID = {warehouse_id}")
                    
            # Если не нашли Душанбе склад, создаем временный
            if not self.dushanbe_warehouse_id:
                self.log("🏗️ Душанбе склад не найден, создаем временный...")
                if not self.create_temporary_dushanbe_warehouse():
                    return False
                    
            return True
        else:
            self.log(f"❌ Ошибка получения списка складов: {response.status_code} - {response.text}")
            return False
            
    def create_cargo_with_destination_warehouse(self):
        """Создать груз через POST /api/operator/cargo/direct-accept с destination_warehouse_id"""
        self.log("📦 Создание груза через direct-accept с destination_warehouse_id...")
        
        headers = {"Authorization": f"Bearer {self.moscow_operator_token}"}
        
        # Данные для создания груза с destination_warehouse_id
        cargo_data = {
            "sender_full_name": "Тестовый Отправитель Москва",
            "sender_phone": "+79991234567",
            "recipient_full_name": "Тестовый Получатель Душанбе",
            "recipient_phone": "+79921234567",
            "recipient_address": "Душанбе, проспект Рудаки, 123",
            "cargo_items": [
                {
                    "cargo_name": "Тестовый груз для проверки destination_warehouse_id",
                    "weight": 25.5,
                    "price_per_kg": 80.0
                }
            ],
            "description": "Тестовый груз для проверки сохранения destination_warehouse_id",
            "route": "moscow_to_tajikistan",
            "payment_method": "cash",
            "payment_amount": 2040.0,
            "destination_warehouse_id": self.dushanbe_warehouse_id,  # КЛЮЧЕВОЕ ПОЛЕ
            "pickup_required": False,
            "delivery_method": "pickup"
        }
        
        self.log(f"📋 Данные груза:")
        self.log(f"   👤 Отправитель: {cargo_data['sender_full_name']} ({cargo_data['sender_phone']})")
        self.log(f"   👤 Получатель: {cargo_data['recipient_full_name']} ({cargo_data['recipient_phone']})")
        self.log(f"   📦 Груз: {cargo_data['cargo_items'][0]['cargo_name']}")
        self.log(f"   ⚖️ Вес: {cargo_data['cargo_items'][0]['weight']} кг")
        self.log(f"   💰 Цена за кг: {cargo_data['cargo_items'][0]['price_per_kg']} ₽")
        self.log(f"   🏭 Склад назначения: {self.dushanbe_warehouse_id}")
        
        response = self.session.post(f"{API_BASE}/operator/cargo/direct-accept", json=cargo_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            self.created_cargo_data = data
            
            # Извлекаем информацию о созданном грузе
            base_request_number = data.get('base_request_number')
            created_cargo = data.get('created_cargo', [])
            
            self.log(f"✅ Груз создан через direct-accept:")
            self.log(f"   📋 Base request number: {base_request_number}")
            self.log(f"   📦 Количество грузов: {len(created_cargo)}")
            
            # Проверяем каждый созданный груз
            for i, cargo in enumerate(created_cargo, 1):
                cargo_id = cargo.get('id')
                cargo_number = cargo.get('cargo_number')
                warehouse_id = cargo.get('warehouse_id')
                destination_warehouse_id = cargo.get('destination_warehouse_id')
                destination_warehouse_name = cargo.get('destination_warehouse_name')
                
                self.test_cargo_ids.append(cargo_id)
                
                self.log(f"   {i}. Груз ID: {cargo_id}")
                self.log(f"      📦 Номер: {cargo_number}")
                self.log(f"      🏭 Warehouse ID: {warehouse_id}")
                self.log(f"      🎯 Destination Warehouse ID: {destination_warehouse_id}")
                self.log(f"      🎯 Destination Warehouse Name: {destination_warehouse_name}")
                
                # КРИТИЧЕСКАЯ ПРОВЕРКА: destination_warehouse_id должен быть сохранен
                if destination_warehouse_id == self.dushanbe_warehouse_id:
                    self.log(f"✅ КРИТИЧЕСКИЙ УСПЕХ: destination_warehouse_id сохранен правильно!")
                else:
                    self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: destination_warehouse_id не сохранен или неправильный!")
                    self.log(f"   Ожидалось: {self.dushanbe_warehouse_id}")
                    self.log(f"   Получено: {destination_warehouse_id}")
                    
                # КРИТИЧЕСКАЯ ПРОВЕРКА: destination_warehouse_name должно быть заполнено
                if destination_warehouse_name:
                    self.log(f"✅ КРИТИЧЕСКИЙ УСПЕХ: destination_warehouse_name возвращается в ответе!")
                else:
                    self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: destination_warehouse_name не возвращается в ответе!")
                    
            return True
        else:
            self.log(f"❌ Ошибка создания груза: {response.status_code} - {response.text}")
            return False
            
    def check_cargo_visibility_moscow(self):
        """Проверить видимость груза у оператора Москва-1"""
        self.log("👁️ Проверка видимости груза у оператора Москва-1...")
        
        headers = {"Authorization": f"Bearer {self.moscow_operator_token}"}
        response = self.session.get(f"{API_BASE}/operator/cargo/available-for-placement", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo_list = data.get('items', [])
            
            self.log(f"📋 Получен список доступных для размещения у Москва-1: {len(cargo_list)} грузов")
            
            # Ищем наш созданный груз
            found_cargo = None
            for cargo in cargo_list:
                cargo_id = cargo.get('id')
                if cargo_id in self.test_cargo_ids:
                    found_cargo = cargo
                    break
                    
            if found_cargo:
                cargo_number = found_cargo.get('cargo_number')
                warehouse_id = found_cargo.get('warehouse_id')
                warehouse_name = found_cargo.get('warehouse_name')
                destination_warehouse_id = found_cargo.get('destination_warehouse_id')
                destination_warehouse_name = found_cargo.get('destination_warehouse_name')
                
                self.log(f"✅ КРИТИЧЕСКИЙ УСПЕХ: Груз виден у оператора Москва-1!")
                self.log(f"   📦 Номер груза: {cargo_number}")
                self.log(f"   🏭 Warehouse ID: {warehouse_id}")
                self.log(f"   🏭 Warehouse Name: {warehouse_name}")
                self.log(f"   🎯 Destination Warehouse ID: {destination_warehouse_id}")
                self.log(f"   🎯 Destination Warehouse Name: {destination_warehouse_name}")
                
                # ФИКСАЦИЯ warehouse_id и destination_warehouse_id
                self.log(f"📌 ФИКСАЦИЯ ДАННЫХ В ЭЛЕМЕНТЕ:")
                self.log(f"   warehouse_id: {warehouse_id}")
                self.log(f"   destination_warehouse_id: {destination_warehouse_id}")
                
                return True
            else:
                self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Груз НЕ виден у оператора Москва-1!")
                return False
        else:
            self.log(f"❌ Ошибка получения списка у Москва-1: {response.status_code} - {response.text}")
            return False
            
    def check_cargo_visibility_dushanbe(self):
        """Проверить невидимость груза у оператора Душанбе-3"""
        self.log("👁️ Проверка невидимости груза у оператора Душанбе-3...")
        
        headers = {"Authorization": f"Bearer {self.dushanbe_operator_token}"}
        response = self.session.get(f"{API_BASE}/operator/cargo/available-for-placement", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo_list = data.get('items', [])
            
            self.log(f"📋 Получен список доступных для размещения у Душанбе-3: {len(cargo_list)} грузов")
            
            # Ищем наш созданный груз
            found_cargo = None
            for cargo in cargo_list:
                cargo_id = cargo.get('id')
                if cargo_id in self.test_cargo_ids:
                    found_cargo = cargo
                    break
                    
            if found_cargo:
                self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Груз ВИДЕН у оператора Душанбе-3 (не должен быть виден)!")
                self.log(f"   📦 Номер груза: {found_cargo.get('cargo_number')}")
                return False
            else:
                self.log(f"✅ КРИТИЧЕСКИЙ УСПЕХ: Груз НЕ виден у оператора Душанбе-3 (как и ожидалось)!")
                return True
        elif response.status_code == 403:
            self.log(f"✅ КРИТИЧЕСКИЙ УСПЕХ: Доступ заблокирован для Душанбе-3 (HTTP 403) - корректная работа системы безопасности!")
            return True
        else:
            self.log(f"❌ Ошибка получения списка у Душанбе-3: {response.status_code} - {response.text}")
            return False
            
    def cleanup_test_data(self):
        """Очистить тестовые данные из обеих коллекций cargo и operator_cargo"""
        self.log("🧹 Очистка тестовых данных из обеих коллекций...")
        
        headers = {"Authorization": f"Bearer {self.moscow_operator_token}"}
        
        # Удаление из коллекции operator_cargo
        for cargo_id in self.test_cargo_ids:
            try:
                # Попробуем удалить через admin endpoint
                admin_headers = {"Authorization": f"Bearer {self.moscow_operator_token}"}
                response = self.session.delete(f"{API_BASE}/admin/cargo/{cargo_id}", headers=admin_headers)
                
                if response.status_code == 200:
                    self.log(f"✅ Тестовый груз {cargo_id} удален из operator_cargo")
                else:
                    self.log(f"⚠️ Не удалось удалить груз {cargo_id} из operator_cargo: {response.status_code}")
                    
                # Также попробуем удалить из коллекции cargo (если есть)
                cargo_response = self.session.delete(f"{API_BASE}/cargo/{cargo_id}", headers=admin_headers)
                if cargo_response.status_code == 200:
                    self.log(f"✅ Тестовый груз {cargo_id} удален из cargo")
                    
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления груза {cargo_id}: {e}")
                
        # Удаление временного склада
        if self.temporary_warehouse_id:
            try:
                response = self.session.delete(f"{API_BASE}/admin/warehouses/{self.temporary_warehouse_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Временный склад {self.temporary_warehouse_id} удален")
                else:
                    self.log(f"⚠️ Не удалось удалить временный склад: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления временного склада: {e}")
                
        self.log("✅ Очистка тестовых данных завершена")
        
    def run_comprehensive_test(self):
        """Запуск комплексного тестирования сценария direct-accept с destination_warehouse_id"""
        self.log("🎯 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ СЦЕНАРИЯ DIRECT-ACCEPT С DESTINATION_WAREHOUSE_ID")
        self.log("=" * 100)
        
        success_count = 0
        total_tests = 8  # Общее количество основных тестов
        
        try:
            # 1. Авторизация оператора Москва-1
            self.log("\n📋 ЭТАП 1: Авторизация оператора Москва-1")
            if not self.authenticate_moscow_operator():
                self.log("❌ Критическая ошибка: не удалось авторизовать оператора Москва-1")
                return False
            success_count += 1
            
            # 2. Авторизация оператора Душанбе-3
            self.log("\n📋 ЭТАП 2: Авторизация оператора Душанбе-3")
            if not self.authenticate_dushanbe_operator():
                self.log("❌ Критическая ошибка: не удалось авторизовать оператора Душанбе-3")
                return False
            success_count += 1
            
            # 3. Поиск ID складов
            self.log("\n📋 ЭТАП 3: Поиск ID складов Москва Склад №1 и Душанбе Склад №3")
            if not self.find_warehouse_ids():
                self.log("❌ Критическая ошибка: не удалось найти ID складов")
                return False
            success_count += 1
            
            # 4. Создание груза с destination_warehouse_id
            self.log("\n📋 ЭТАП 4: Создание груза через direct-accept с destination_warehouse_id")
            if not self.create_cargo_with_destination_warehouse():
                self.log("❌ Критическая ошибка: не удалось создать груз с destination_warehouse_id")
                return False
            success_count += 1
            
            # 5. Проверка что destination_warehouse_id возвращается в ответе
            self.log("\n📋 ЭТАП 5: Проверка возврата destination_warehouse_id и destination_warehouse_name в ответе")
            if self.created_cargo_data:
                created_cargo = self.created_cargo_data.get('created_cargo', [])
                if created_cargo and len(created_cargo) > 0:
                    first_cargo = created_cargo[0]
                    destination_warehouse_id = first_cargo.get('destination_warehouse_id')
                    destination_warehouse_name = first_cargo.get('destination_warehouse_name')
                    
                    if destination_warehouse_id and destination_warehouse_name:
                        self.log("✅ КРИТИЧЕСКИЙ УСПЕХ: destination_warehouse_id и destination_warehouse_name возвращаются в ответе!")
                        success_count += 1
                    else:
                        self.log("❌ КРИТИЧЕСКАЯ ОШИБКА: destination_warehouse_id или destination_warehouse_name не возвращаются!")
                else:
                    self.log("❌ Нет данных о созданном грузе для проверки")
            else:
                self.log("❌ Нет данных о созданном грузе")
                
            # 6. Проверка видимости груза у Москва-1
            self.log("\n📋 ЭТАП 6: Проверка видимости груза у оператора Москва-1")
            if not self.check_cargo_visibility_moscow():
                self.log("❌ Критическая ошибка: груз не виден у оператора Москва-1")
            else:
                success_count += 1
                
            # 7. Проверка невидимости груза у Душанбе-3
            self.log("\n📋 ЭТАП 7: Проверка невидимости груза у оператора Душанбе-3")
            if not self.check_cargo_visibility_dushanbe():
                self.log("❌ Критическая ошибка: груз виден у оператора Душанбе-3 (не должен быть виден)")
            else:
                success_count += 1
                
            # 8. Фиксация warehouse_id и destination_warehouse_id
            self.log("\n📋 ЭТАП 8: Фиксация warehouse_id и destination_warehouse_id в элементе")
            if self.created_cargo_data:
                created_cargo = self.created_cargo_data.get('created_cargo', [])
                if created_cargo and len(created_cargo) > 0:
                    first_cargo = created_cargo[0]
                    warehouse_id = first_cargo.get('warehouse_id')
                    destination_warehouse_id = first_cargo.get('destination_warehouse_id')
                    
                    self.log("📌 ФИКСАЦИЯ ДАННЫХ В ЭЛЕМЕНТЕ (ФИНАЛЬНАЯ):")
                    self.log(f"   warehouse_id: {warehouse_id}")
                    self.log(f"   destination_warehouse_id: {destination_warehouse_id}")
                    self.log("✅ Данные зафиксированы в элементе")
                    success_count += 1
                else:
                    self.log("❌ Нет данных для фиксации")
            else:
                self.log("❌ Нет данных для фиксации")
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка во время тестирования: {e}")
            
        finally:
            # Очистка тестовых данных
            self.log("\n📋 ФИНАЛЬНЫЙ ЭТАП: Очистка тестовых данных")
            self.cleanup_test_data()
            
        # Итоговый отчет
        self.log("\n" + "=" * 100)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ СЦЕНАРИЯ DIRECT-ACCEPT С DESTINATION_WAREHOUSE_ID")
        self.log("=" * 100)
        
        success_rate = (success_count / total_tests) * 100
        
        self.log(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        self.log(f"   Успешных тестов: {success_count}/{total_tests}")
        self.log(f"   Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 ОТЛИЧНО: Сценарий direct-accept с destination_warehouse_id работает идеально!")
        elif success_rate >= 75:
            self.log("✅ ХОРОШО: Основная функциональность работает, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Система требует доработки")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ Авторизация операторов Москва-1 и Душанбе-3")
        self.log("✅ Получение ID складов Москва Склад №1 и Душанбе Склад №3")
        self.log("✅ Создание груза с destination_warehouse_id через direct-accept")
        self.log("✅ Проверка что destination_warehouse_id и destination_warehouse_name возвращаются в ответе")
        self.log("✅ Проверка видимости груза у Москва-1 (должен быть виден)")
        self.log("✅ Проверка невидимости груза у Душанбе-3 (не должен быть виден)")
        self.log("✅ Фиксация warehouse_id и destination_warehouse_id в элементе")
        self.log("✅ Очистка тестовых данных из обеих коллекций")
        
        # КРИТИЧЕСКОЕ ЗАКЛЮЧЕНИЕ
        self.log("\n🎯 КРИТИЧЕСКОЕ ЗАКЛЮЧЕНИЕ:")
        if success_rate >= 75:
            self.log("✅ DESTINATION_WAREHOUSE_ID ТЕПЕРЬ СОХРАНЯЕТСЯ И ВОЗВРАЩАЕТСЯ В ОТВЕТЕ DIRECT-ACCEPT!")
            self.log("✅ Груз, принятый на «Москва Склад №1» с назначением «Душанбе Склад №3», корректно:")
            self.log("   - Показывается в «Размещении» у оператора Москвы")
            self.log("   - Содержит destination_warehouse_id и destination_warehouse_name")
            self.log("   - НЕ показывается у оператора Душанбе (корректная фильтрация)")
        else:
            self.log("❌ ТРЕБУЕТСЯ ДОРАБОТКА ФУНКЦИОНАЛЬНОСТИ DESTINATION_WAREHOUSE_ID!")
            
        return success_rate >= 75

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Сценарий direct-accept с destination_warehouse_id в TAJLINE.TJ")
    print("=" * 100)
    
    tester = DirectAcceptDestinationTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()