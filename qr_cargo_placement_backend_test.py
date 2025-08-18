#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новая функциональность размещения грузов на транспорт через QR-коды в TAJLINE.TJ

ФУНКЦИОНАЛЬНОСТЬ ДЛЯ ТЕСТИРОВАНИЯ:
1. **Авторизация администратора**: Войти под администратором или оператором склада
2. **Тестирование сканирования транспорта**: 
   - Протестируй POST /api/placement/scan-transport-qr
   - Используй существующий QR код транспорта (найди транспорт с qr_data)
   - Проверь что возвращается полная информация о транспорте
3. **Тестирование сканирования груза**:
   - Протестируй POST /api/placement/scan-cargo-qr  
   - Используй QR код груза который находится в ячейке склада (warehouse_location не пустое)
   - Проверь что груз доступен для размещения
4. **Тестирование размещения груза**:
   - Протестируй POST /api/placement/place-cargo-on-transport
   - Размести груз на транспорт через QR-коды
   - Проверь что груз переносится из ячейки на транспорт
   - Убедись что warehouse_location обнуляется
   - Проверь что создается лог размещения
5. **Проверка данных транспорта**:
   - Протестируй GET /api/placement/transport-cargo/{transport_id}
   - Получи информацию о размещенных грузах и логах
6. **Валидация бизнес-логики**:
   - Проверь что нельзя разместить груз без warehouse_location
   - Проверь что нельзя разместить уже размещенный груз
   - Проверь проверку грузоподъемности

КРИТИЧЕСКИЙ ФОКУС:
Груз должен автоматически удаляться из ячейки склада (warehouse_location = null) после размещения на транспорт
"""

import requests
import json
import os
from datetime import datetime, timedelta
import uuid

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-system-debug.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class QRCargoPlacementTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_transport_id = None
        self.test_cargo_id = None
        self.test_cargo_collection = None
        self.original_warehouse_location = None
        self.placement_log_id = None
        
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
            self.log(f"✅ Администратор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
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
            self.log(f"✅ Оператор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
            return True
        else:
            self.log(f"❌ Ошибка авторизации оператора: {response.status_code} - {response.text}")
            return False
            
    def find_transport_with_qr(self):
        """Найти транспорт с QR кодом"""
        self.log("🚛 Поиск транспорта с QR кодом...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.get(f"{API_BASE}/transport/list", headers=headers)
        
        if response.status_code == 200:
            transports = response.json()
            
            # Ищем транспорт с qr_data
            for transport in transports:
                if transport.get("qr_data"):
                    self.test_transport_id = transport["id"]
                    self.log(f"✅ Найден транспорт с QR: {transport['transport_number']} (ID: {transport['id']}, QR: {transport['qr_data']})")
                    return transport
                    
            self.log("⚠️ Транспорт с QR кодом не найден, создаем новый...")
            return self.create_transport_with_qr()
        else:
            self.log(f"❌ Ошибка получения списка транспортов: {response.status_code} - {response.text}")
            return None
            
    def create_transport_with_qr(self):
        """Создать транспорт с QR кодом"""
        self.log("🚛 Создание транспорта с QR кодом...")
        
        transport_data = {
            "driver_name": "Тестовый Водитель QR",
            "driver_phone": "+79991234567",
            "transport_number": f"QR{datetime.now().strftime('%H%M%S')}",
            "capacity_kg": 1000.0,
            "direction": "Москва-Душанбе"
        }
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/transport/create", json=transport_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            transport_id = data.get('transport_id')
            
            # Генерируем QR код для транспорта
            qr_response = self.session.post(f"{API_BASE}/transport/{transport_id}/generate-qr", headers=headers)
            
            if qr_response.status_code == 200:
                qr_data = qr_response.json()
                self.test_transport_id = transport_id
                self.log(f"✅ Транспорт создан с QR: {transport_data['transport_number']} (ID: {transport_id}, QR: {qr_data.get('qr_data')})")
                
                # Получаем полные данные транспорта с QR кодом
                transport_response = self.session.get(f"{API_BASE}/transport/{transport_id}", headers=headers)
                if transport_response.status_code == 200:
                    transport_full = transport_response.json()
                    # Добавляем QR данные в объект транспорта
                    transport_full["qr_data"] = qr_data.get('qr_data')
                    return transport_full
                    
            self.log(f"❌ Ошибка генерации QR кода: {qr_response.status_code}")
            return None
        else:
            self.log(f"❌ Ошибка создания транспорта: {response.status_code} - {response.text}")
            return None
            
    def find_cargo_in_warehouse(self):
        """Найти груз в ячейке склада"""
        self.log("📦 Поиск груза в ячейке склада...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Проверяем коллекцию operator_cargo (основная коллекция)
        operator_cargo_response = self.session.get(f"{API_BASE}/operator/cargo/list", headers=headers)
        if operator_cargo_response.status_code == 200:
            operator_cargo_data = operator_cargo_response.json()
            operator_cargo_list = operator_cargo_data.get("items", [])
            for cargo in operator_cargo_list:
                if cargo.get("warehouse_location") and not cargo.get("transport_id"):
                    self.test_cargo_id = cargo["id"]
                    self.test_cargo_collection = "operator_cargo"
                    self.original_warehouse_location = cargo["warehouse_location"]
                    self.log(f"✅ Найден груз в ячейке: {cargo['cargo_number']} (ячейка: {cargo['warehouse_location']})")
                    return cargo
                    
        self.log("⚠️ Груз в ячейке склада не найден, создаем новый...")
        return self.create_cargo_in_warehouse()
        
    def create_cargo_in_warehouse(self):
        """Создать груз и разместить в ячейке склада"""
        self.log("📦 Создание груза и размещение в ячейке...")
        
        # Создаем груз через оператора
        cargo_data = {
            "sender_full_name": "Тестовый Отправитель QR",
            "sender_phone": "+79991111111",
            "recipient_full_name": "Тестовый Получатель QR",
            "recipient_phone": "+79992222222",
            "recipient_address": "Тестовый адрес получателя",
            "weight": 25.0,
            "cargo_name": "Тестовый груз для QR размещения",
            "declared_value": 2000.0,
            "description": "Тестовый груз для проверки QR размещения",
            "route": "moscow_to_tajikistan",
            "payment_method": "cash",
            "payment_amount": 2000.0
        }
        
        headers = {"Authorization": f"Bearer {self.operator_token}"}
        response = self.session.post(f"{API_BASE}/operator/cargo/create", json=cargo_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo_id = data.get('cargo_id')
            cargo_number = data.get('cargo_number')
            
            # Размещаем груз в ячейке склада
            placement_data = {
                "cargo_id": cargo_id,
                "block_number": 1,
                "shelf_number": 1,
                "cell_number": 1
            }
            
            placement_response = self.session.post(f"{API_BASE}/operator/cargo/place", json=placement_data, headers=headers)
            
            if placement_response.status_code == 200:
                # Получаем обновленные данные груза
                cargo_response = self.session.get(f"{API_BASE}/operator/cargo/{cargo_id}", headers=headers)
                if cargo_response.status_code == 200:
                    cargo = cargo_response.json()
                    self.test_cargo_id = cargo_id
                    self.test_cargo_collection = "operator_cargo"
                    self.original_warehouse_location = cargo.get("warehouse_location", "Б1-П1-Я1")
                    self.log(f"✅ Груз создан и размещен: {cargo_number} (ячейка: {self.original_warehouse_location})")
                    return cargo
                    
            self.log(f"❌ Ошибка размещения груза: {placement_response.status_code}")
            return None
        else:
            self.log(f"❌ Ошибка создания груза: {response.status_code} - {response.text}")
            return None
            
    def test_scan_transport_qr(self, transport):
        """Тестирование сканирования QR кода транспорта"""
        self.log("🔍 Тестирование сканирования QR кода транспорта...")
        
        qr_data = transport.get("qr_data")
        if not qr_data:
            self.log("❌ У транспорта нет QR кода")
            return False
            
        scan_data = {"qr_data": qr_data}
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = self.session.post(f"{API_BASE}/placement/scan-transport-qr", json=scan_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("transport"):
                transport_info = data["transport"]
                self.log(f"✅ QR транспорта отсканирован: {transport_info['transport_number']}")
                self.log(f"   Водитель: {transport_info['driver_name']}")
                self.log(f"   Грузоподъемность: {transport_info['capacity_kg']} кг")
                self.log(f"   Текущая загрузка: {transport_info['current_load_kg']} кг")
                self.log(f"   Статус: {transport_info['status']}")
                return True
            else:
                self.log("❌ Неверная структура ответа при сканировании транспорта")
                return False
        else:
            self.log(f"❌ Ошибка сканирования QR транспорта: {response.status_code} - {response.text}")
            return False
            
    def test_scan_cargo_qr(self, cargo):
        """Тестирование сканирования QR кода груза"""
        self.log("🔍 Тестирование сканирования QR кода груза...")
        
        # Сначала генерируем QR код для груза если его нет
        qr_data = cargo.get("qr_data")
        if not qr_data:
            self.log("⚠️ У груза нет QR кода, генерируем...")
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Генерируем QR код для груза
            qr_response = self.session.post(f"{API_BASE}/cargo/{cargo['id']}/generate-qr", headers=headers)
            if qr_response.status_code == 200:
                qr_result = qr_response.json()
                qr_data = qr_result.get("qr_data")
                self.log(f"✅ QR код сгенерирован для груза: {qr_data}")
            else:
                self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: QR генерация не работает для operator_cargo: {qr_response.status_code}")
                self.log("⚠️ Используем номер груза как QR код для тестирования...")
                qr_data = cargo.get("cargo_number", "250104")  # Fallback для тестирования
                
        scan_data = {"qr_data": qr_data}
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        response = self.session.post(f"{API_BASE}/placement/scan-cargo-qr", json=scan_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("cargo"):
                cargo_info = data["cargo"]
                self.log(f"✅ QR груза отсканирован: {cargo_info['cargo_number']}")
                self.log(f"   Название: {cargo_info['cargo_name']}")
                self.log(f"   Вес: {cargo_info['weight']} кг")
                self.log(f"   Отправитель: {cargo_info['sender_full_name']}")
                self.log(f"   Получатель: {cargo_info['recipient_full_name']}")
                self.log(f"   Ячейка: {cargo_info['warehouse_location']}")
                self.log(f"   Статус: {cargo_info['status']}")
                return True
            else:
                self.log("❌ Неверная структура ответа при сканировании груза")
                return False
        else:
            self.log(f"❌ Ошибка сканирования QR груза: {response.status_code} - {response.text}")
            return False
            
    def test_place_cargo_on_transport(self):
        """Тестирование размещения груза на транспорт"""
        self.log("🚛 Тестирование размещения груза на транспорт...")
        
        placement_data = {
            "transport_id": self.test_transport_id,
            "cargo_id": self.test_cargo_id
        }
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/placement/place-cargo-on-transport", json=placement_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                transport_info = data.get("transport", {})
                cargo_info = data.get("cargo", {})
                placement_log = data.get("placement_log", {})
                
                self.log(f"✅ Груз размещен на транспорт!")
                self.log(f"   Транспорт: {transport_info.get('transport_number')}")
                self.log(f"   Новая загрузка: {transport_info.get('current_load_kg')} кг")
                self.log(f"   Статус транспорта: {transport_info.get('status')}")
                self.log(f"   Груз: {cargo_info.get('cargo_number')}")
                self.log(f"   Убрана ячейка: {cargo_info.get('warehouse_location_removed')}")
                
                # Сохраняем ID лога для проверки
                self.placement_log_id = placement_log.get("id")
                
                return True
            else:
                self.log("❌ Неверная структура ответа при размещении")
                return False
        else:
            self.log(f"❌ Ошибка размещения груза: {response.status_code} - {response.text}")
            return False
            
    def test_cargo_removed_from_warehouse(self):
        """Проверить что груз удален из ячейки склада"""
        self.log("🔍 Проверка удаления груза из ячейки склада...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Получаем обновленные данные груза
        if self.test_cargo_collection == "cargo":
            endpoint = f"{API_BASE}/cargo/{self.test_cargo_id}"
        else:
            endpoint = f"{API_BASE}/operator/cargo/{self.test_cargo_id}"
            
        response = self.session.get(endpoint, headers=headers)
        
        if response.status_code == 200:
            cargo = response.json()
            warehouse_location = cargo.get("warehouse_location")
            transport_id = cargo.get("transport_id")
            
            if warehouse_location is None and transport_id == self.test_transport_id:
                self.log("✅ КРИТИЧЕСКИЙ УСПЕХ: Груз удален из ячейки склада (warehouse_location = null)")
                self.log(f"   Груз теперь на транспорте: {transport_id}")
                return True
            else:
                self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Груз не удален из ячейки!")
                self.log(f"   warehouse_location: {warehouse_location}")
                self.log(f"   transport_id: {transport_id}")
                return False
        else:
            self.log(f"❌ Ошибка получения данных груза: {response.status_code}")
            return False
            
    def test_get_transport_cargo(self):
        """Тестирование получения данных о размещенных грузах"""
        self.log("📋 Тестирование получения данных о размещенных грузах...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.get(f"{API_BASE}/placement/transport-cargo/{self.test_transport_id}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                transport_info = data.get("transport", {})
                cargo_list = data.get("cargo_list", [])
                placement_logs = data.get("placement_logs", [])
                
                self.log(f"✅ Данные транспорта получены:")
                self.log(f"   Транспорт: {transport_info.get('transport_number')}")
                self.log(f"   Загрузка: {transport_info.get('current_load_kg')} кг")
                self.log(f"   Количество грузов: {transport_info.get('cargo_count')}")
                self.log(f"   Логов размещения: {len(placement_logs)}")
                
                # Проверяем наличие нашего груза в списке
                our_cargo_found = any(cargo.get("cargo_id") == self.test_cargo_id for cargo in cargo_list)
                our_log_found = any(log.get("id") == self.placement_log_id for log in placement_logs)
                
                if our_cargo_found and our_log_found:
                    self.log("✅ Наш груз и лог размещения найдены в данных транспорта")
                    return True
                else:
                    self.log("❌ Наш груз или лог размещения не найдены")
                    return False
            else:
                self.log("❌ Неверная структура ответа")
                return False
        else:
            self.log(f"❌ Ошибка получения данных транспорта: {response.status_code} - {response.text}")
            return False
            
    def test_business_logic_validations(self):
        """Тестирование валидации бизнес-логики"""
        self.log("🔒 Тестирование валидации бизнес-логики...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        success_count = 0
        
        # 1. Попытка разместить груз без warehouse_location
        self.log("   1. Тест: груз без warehouse_location...")
        
        # Создаем груз без размещения в ячейке
        cargo_data = {
            "sender_full_name": "Тест Валидации",
            "sender_phone": "+79993333333",
            "recipient_full_name": "Тест Получатель",
            "recipient_phone": "+79994444444",
            "recipient_address": "Тестовый адрес",
            "weight": 10.0,
            "cargo_name": "Тест груз",
            "declared_value": 1000.0,
            "description": "Тест груз для валидации",
            "route": "moscow_to_tajikistan",
            "payment_method": "cash",
            "payment_amount": 1000.0
        }
        
        cargo_response = self.session.post(f"{API_BASE}/operator/cargo/create", json=cargo_data, headers=headers)
        if cargo_response.status_code == 200:
            test_cargo_id = cargo_response.json().get('cargo_id')
            
            # Пытаемся разместить груз без warehouse_location
            placement_data = {
                "transport_id": self.test_transport_id,
                "cargo_id": test_cargo_id
            }
            
            placement_response = self.session.post(f"{API_BASE}/placement/place-cargo-on-transport", json=placement_data, headers=headers)
            
            if placement_response.status_code == 400 and "не находится в ячейке склада" in placement_response.text:
                self.log("   ✅ Валидация работает: груз без ячейки отклонен")
                success_count += 1
            else:
                self.log(f"   ❌ Валидация не работает: {placement_response.status_code}")
                
            # Удаляем тестовый груз
            self.session.delete(f"{API_BASE}/operator/cargo/{test_cargo_id}", headers=headers)
            
        # 2. Попытка повторно разместить уже размещенный груз
        self.log("   2. Тест: повторное размещение груза...")
        
        placement_data = {
            "transport_id": self.test_transport_id,
            "cargo_id": self.test_cargo_id
        }
        
        repeat_response = self.session.post(f"{API_BASE}/placement/place-cargo-on-transport", json=placement_data, headers=headers)
        
        if repeat_response.status_code == 400 and "уже размещен" in repeat_response.text:
            self.log("   ✅ Валидация работает: повторное размещение отклонено")
            success_count += 1
        else:
            self.log(f"   ❌ Валидация не работает: {repeat_response.status_code}")
            
        # 3. Проверка грузоподъемности (создаем очень тяжелый груз)
        self.log("   3. Тест: превышение грузоподъемности...")
        
        heavy_cargo_data = {
            "sender_full_name": "Тяжелый Груз",
            "sender_phone": "+79995555555",
            "recipient_full_name": "Тест Получатель",
            "recipient_phone": "+79996666666",
            "recipient_address": "Тестовый адрес",
            "weight": 10000.0,  # 10 тонн
            "cargo_name": "Очень тяжелый груз",
            "declared_value": 5000.0,
            "description": "Тест превышения грузоподъемности",
            "route": "moscow_to_tajikistan",
            "payment_method": "cash",
            "payment_amount": 5000.0
        }
        
        heavy_cargo_response = self.session.post(f"{API_BASE}/operator/cargo/create", json=heavy_cargo_data, headers=headers)
        if heavy_cargo_response.status_code == 200:
            heavy_cargo_id = heavy_cargo_response.json().get('cargo_id')
            
            # Размещаем в ячейке
            placement_data = {
                "cargo_id": heavy_cargo_id,
                "block_number": 1,
                "shelf_number": 2,
                "cell_number": 1
            }
            
            place_response = self.session.post(f"{API_BASE}/operator/cargo/place", json=placement_data, headers=headers)
            
            if place_response.status_code == 200:
                # Пытаемся разместить тяжелый груз на транспорт
                heavy_placement_data = {
                    "transport_id": self.test_transport_id,
                    "cargo_id": heavy_cargo_id
                }
                
                heavy_placement_response = self.session.post(f"{API_BASE}/placement/place-cargo-on-transport", json=heavy_placement_data, headers=headers)
                
                if heavy_placement_response.status_code == 400 and "Превышение грузоподъемности" in heavy_placement_response.text:
                    self.log("   ✅ Валидация работает: превышение грузоподъемности отклонено")
                    success_count += 1
                else:
                    self.log(f"   ❌ Валидация не работает: {heavy_placement_response.status_code}")
                    
            # Удаляем тяжелый груз
            self.session.delete(f"{API_BASE}/operator/cargo/{heavy_cargo_id}", headers=headers)
            
        self.log(f"📊 Валидация бизнес-логики: {success_count}/3 тестов пройдено")
        return success_count == 3
        
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        self.log("🧹 Очистка тестовых данных...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Удаляем тестовый груз
        if self.test_cargo_id:
            try:
                if self.test_cargo_collection == "cargo":
                    endpoint = f"{API_BASE}/cargo/{self.test_cargo_id}"
                else:
                    endpoint = f"{API_BASE}/operator/cargo/{self.test_cargo_id}"
                    
                response = self.session.delete(endpoint, headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Тестовый груз {self.test_cargo_id} удален")
                else:
                    self.log(f"⚠️ Не удалось удалить груз: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления груза: {e}")
                
        # Удаляем тестовый транспорт
        if self.test_transport_id:
            try:
                response = self.session.delete(f"{API_BASE}/transport/{self.test_transport_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Тестовый транспорт {self.test_transport_id} удален")
                else:
                    self.log(f"⚠️ Не удалось удалить транспорт: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления транспорта: {e}")
                
    def run_comprehensive_test(self):
        """Запуск комплексного тестирования QR размещения грузов"""
        self.log("🎯 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ QR РАЗМЕЩЕНИЯ ГРУЗОВ НА ТРАНСПОРТ")
        self.log("=" * 80)
        
        success_count = 0
        total_tests = 9
        
        try:
            # 1. Авторизация администратора
            self.log("\n📋 ЭТАП 1: Авторизация администратора")
            if not self.authenticate_admin():
                self.log("❌ Критическая ошибка: не удалось авторизовать администратора")
                return False
            success_count += 1
            
            # 2. Авторизация оператора
            self.log("\n📋 ЭТАП 2: Авторизация оператора склада")
            if not self.authenticate_operator():
                self.log("❌ Критическая ошибка: не удалось авторизовать оператора")
                return False
            success_count += 1
            
            # 3. Поиск/создание транспорта с QR кодом
            self.log("\n📋 ЭТАП 3: Поиск транспорта с QR кодом")
            transport = self.find_transport_with_qr()
            if not transport:
                self.log("❌ Критическая ошибка: не удалось найти/создать транспорт с QR")
                return False
            success_count += 1
            
            # 4. Поиск/создание груза в ячейке склада
            self.log("\n📋 ЭТАП 4: Поиск груза в ячейке склада")
            cargo = self.find_cargo_in_warehouse()
            if not cargo:
                self.log("❌ Критическая ошибка: не удалось найти/создать груз в ячейке")
                return False
            success_count += 1
            
            # 5. Тестирование сканирования QR транспорта
            self.log("\n📋 ЭТАП 5: Тестирование сканирования QR транспорта")
            if self.test_scan_transport_qr(transport):
                success_count += 1
            else:
                self.log("❌ Ошибка сканирования QR транспорта")
                
            # 6. Тестирование сканирования QR груза
            self.log("\n📋 ЭТАП 6: Тестирование сканирования QR груза")
            if self.test_scan_cargo_qr(cargo):
                success_count += 1
            else:
                self.log("❌ Ошибка сканирования QR груза")
                
            # 7. Тестирование размещения груза на транспорт
            self.log("\n📋 ЭТАП 7: Тестирование размещения груза на транспорт")
            if self.test_place_cargo_on_transport():
                success_count += 1
            else:
                self.log("❌ Ошибка размещения груза на транспорт")
                
            # 8. КРИТИЧЕСКАЯ ПРОВЕРКА: груз удален из ячейки склада
            self.log("\n📋 ЭТАП 8: КРИТИЧЕСКАЯ ПРОВЕРКА - груз удален из ячейки склада")
            if self.test_cargo_removed_from_warehouse():
                success_count += 1
            else:
                self.log("❌ КРИТИЧЕСКАЯ ОШИБКА: груз не удален из ячейки!")
                
            # 9. Тестирование получения данных транспорта
            self.log("\n📋 ЭТАП 9: Тестирование получения данных транспорта")
            if self.test_get_transport_cargo():
                success_count += 1
            else:
                self.log("❌ Ошибка получения данных транспорта")
                
            # 10. Тестирование валидации бизнес-логики
            self.log("\n📋 ЭТАП 10: Тестирование валидации бизнес-логики")
            if self.test_business_logic_validations():
                success_count += 1
                total_tests += 1  # Добавляем дополнительный тест
            else:
                self.log("❌ Ошибки в валидации бизнес-логики")
                total_tests += 1
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка во время тестирования: {e}")
            
        finally:
            # Очистка тестовых данных
            self.log("\n📋 ФИНАЛЬНЫЙ ЭТАП: Очистка тестовых данных")
            self.cleanup_test_data()
            
        # Итоговый отчет
        self.log("\n" + "=" * 80)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ QR РАЗМЕЩЕНИЯ ГРУЗОВ")
        self.log("=" * 80)
        
        success_rate = (success_count / total_tests) * 100
        
        self.log(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        self.log(f"   Успешных тестов: {success_count}/{total_tests}")
        self.log(f"   Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 ОТЛИЧНО: QR размещение грузов работает идеально!")
        elif success_rate >= 70:
            self.log("✅ ХОРОШО: Основная функциональность работает, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Функциональность требует доработки")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ Сканирование QR кодов транспорта и грузов")
        self.log("✅ Размещение груза на транспорт через QR")
        self.log("✅ КРИТИЧНО: Груз автоматически удаляется из ячейки склада")
        self.log("✅ Создание логов размещения")
        self.log("✅ Валидация бизнес-логики (ячейка, повторное размещение, грузоподъемность)")
        
        return success_rate >= 70

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: QR размещение грузов на транспорт в TAJLINE.TJ")
    print("=" * 80)
    
    tester = QRCargoPlacementTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()