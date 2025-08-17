#!/usr/bin/env python3
"""
🎯 ДИАГНОСТИКА: Исследование API endpoints для фильтрации грузов
"""

import requests
import json
import os
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-manager-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def log(message):
    """Логирование с временной меткой"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def investigate_api_endpoints():
    """Исследование API endpoints"""
    log("🔍 ДИАГНОСТИКА API ENDPOINTS")
    log("=" * 50)
    
    session = requests.Session()
    
    try:
        # 1. Авторизация оператора
        log("\n📋 ЭТАП 1: Авторизация оператора")
        login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        response = session.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            operator_token = data.get('access_token')
            user_info = data.get('user', {})
            log(f"✅ Оператор авторизован: {user_info.get('full_name')}")
        else:
            log(f"❌ Ошибка авторизации: {response.status_code}")
            return
            
        headers = {"Authorization": f"Bearer {operator_token}"}
        
        # 2. Исследование endpoint available-for-placement
        log("\n📋 ЭТАП 2: Исследование /api/operator/cargo/available-for-placement")
        response = session.get(f"{API_BASE}/operator/cargo/available-for-placement", headers=headers)
        
        if response.status_code == 200:
            cargo_list = response.json()
            log(f"✅ Получен список: {len(cargo_list)} грузов")
            
            for i, cargo in enumerate(cargo_list):
                if i >= 3:  # Показываем только первые 3
                    break
                log(f"   📦 Груз {i+1}:")
                if isinstance(cargo, dict):
                    log(f"      ID: {cargo.get('id')}")
                    log(f"      Номер: {cargo.get('cargo_number')}")
                    log(f"      Статус: {cargo.get('status')}")
                    log(f"      Warehouse ID: {cargo.get('warehouse_id')}")
                    log(f"      Destination Warehouse ID: {cargo.get('destination_warehouse_id')}")
                else:
                    log(f"      Тип данных: {type(cargo)}")
                    log(f"      Содержимое: {cargo}")
        else:
            log(f"❌ Ошибка получения списка: {response.status_code} - {response.text}")
            
        # 3. Создание тестового груза с детальным логированием
        log("\n📋 ЭТАП 3: Создание тестового груза")
        cargo_data = {
            "sender_full_name": "Диагностический Отправитель",
            "sender_phone": "+79991234567",
            "recipient_full_name": "Диагностический Получатель",
            "recipient_phone": "+79929876543",
            "recipient_address": "Душанбе, проспект Рудаки, 123",
            "cargo_items": [
                {
                    "cargo_name": "Диагностический груз",
                    "weight": 5.0,
                    "price_per_kg": 100.0
                }
            ],
            "description": "Груз для диагностики API",
            "route": "moscow_to_tajikistan",
            "payment_method": "cash",
            "payment_amount": 500.0
        }
        
        response = session.post(f"{API_BASE}/operator/cargo/direct-accept", json=cargo_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            log(f"✅ Груз создан:")
            log(f"   📋 Base request number: {data.get('base_request_number')}")
            
            created_cargo = data.get('created_cargo', [])
            test_cargo_id = None
            
            for cargo in created_cargo:
                cargo_id = cargo.get('id')
                cargo_number = cargo.get('cargo_number')
                test_cargo_id = cargo_id
                
                log(f"   📦 Груз: {cargo_number}")
                log(f"      ID: {cargo_id}")
                log(f"      Warehouse ID: {cargo.get('warehouse_id')}")
                log(f"      Destination Warehouse ID: {cargo.get('destination_warehouse_id')}")
                log(f"      Status: {cargo.get('status')}")
                
            # 4. Повторная проверка списка available-for-placement
            log("\n📋 ЭТАП 4: Повторная проверка available-for-placement")
            response = session.get(f"{API_BASE}/operator/cargo/available-for-placement", headers=headers)
            
            if response.status_code == 200:
                cargo_list = response.json()
                log(f"✅ Обновленный список: {len(cargo_list)} грузов")
                
                found = False
                for cargo in cargo_list:
                    if isinstance(cargo, dict) and cargo.get('id') == test_cargo_id:
                        found = True
                        log(f"🎯 НАЙДЕН созданный груз:")
                        log(f"   📦 Номер: {cargo.get('cargo_number')}")
                        log(f"   🏭 Warehouse ID: {cargo.get('warehouse_id')}")
                        log(f"   🎯 Destination Warehouse ID: {cargo.get('destination_warehouse_id')}")
                        log(f"   📊 Статус: {cargo.get('status')}")
                        break
                        
                if not found:
                    log("❌ Созданный груз НЕ найден в списке")
                    
            # 5. Проверка других endpoints
            log("\n📋 ЭТАП 5: Проверка других endpoints")
            
            # Попробуем найти груз через другие endpoints
            endpoints_to_try = [
                f"/api/operator/cargo/list",
                f"/api/admin/cargo/list",
                f"/api/cargo/search"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    response = session.get(f"{API_BASE}{endpoint}", headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, dict) and 'items' in data:
                            items = data['items']
                            log(f"✅ {endpoint}: {len(items)} элементов")
                        elif isinstance(data, list):
                            log(f"✅ {endpoint}: {len(data)} элементов")
                        else:
                            log(f"✅ {endpoint}: ответ получен")
                    else:
                        log(f"⚠️ {endpoint}: {response.status_code}")
                except Exception as e:
                    log(f"⚠️ {endpoint}: ошибка - {e}")
                    
            # 6. Авторизация администратора для очистки
            log("\n📋 ЭТАП 6: Очистка")
            admin_login = {
                "phone": "+79999888777",
                "password": "admin123"
            }
            
            admin_response = session.post(f"{API_BASE}/auth/login", json=admin_login)
            
            if admin_response.status_code == 200:
                admin_data = admin_response.json()
                admin_token = admin_data.get('access_token')
                admin_headers = {"Authorization": f"Bearer {admin_token}"}
                
                if test_cargo_id:
                    delete_response = session.delete(f"{API_BASE}/admin/cargo/{test_cargo_id}", headers=admin_headers)
                    if delete_response.status_code == 200:
                        log(f"✅ Тестовый груз удален")
                    else:
                        log(f"⚠️ Не удалось удалить груз: {delete_response.status_code}")
        else:
            log(f"❌ Ошибка создания груза: {response.status_code} - {response.text}")
            
    except Exception as e:
        log(f"❌ Критическая ошибка: {e}")

def main():
    investigate_api_endpoints()

if __name__ == "__main__":
    main()