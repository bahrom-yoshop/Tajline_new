#!/usr/bin/env python3
"""
Check cargo system and create test cargo if needed
"""

import requests
import json

# Configuration
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

def authenticate_admin():
    """Авторизация администратора"""
    print("🔐 Авторизация администратора...")
    
    login_data = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            admin_token = data.get("access_token")
            user_info = data.get("user", {})
            print(f"✅ Администратор авторизован: {user_info.get('full_name')}")
            return admin_token
        else:
            print(f"❌ Ошибка авторизации: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return None

def check_available_endpoints(admin_token):
    """Проверить доступные endpoints для работы с грузами"""
    print("\n🔍 Проверка доступных endpoints...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    endpoints_to_check = [
        ("/operator/cargo/available-for-placement", "GET"),
        ("/operator/cargo/list", "GET"),
        ("/cargo/list", "GET"),
        ("/admin/cargo/search", "POST"),
        ("/destinations/cities", "GET"),
        ("/warehouses", "GET")
    ]
    
    working_endpoints = []
    
    for endpoint, method in endpoints_to_check:
        try:
            if method == "GET":
                response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers)
            else:
                response = requests.post(f"{BACKEND_URL}{endpoint}", json={}, headers=headers)
            
            print(f"   {method} {endpoint}: {response.status_code}")
            
            if response.status_code in [200, 201]:
                working_endpoints.append((endpoint, method))
                
                # Show some data for successful endpoints
                if endpoint == "/destinations/cities":
                    cities = response.json()
                    print(f"      📍 Найдено городов: {len(cities)}")
                    for city in cities[:3]:
                        print(f"         🏙️ {city.get('name')}: {city.get('warehouse_id')}")
                        
                elif endpoint == "/warehouses":
                    warehouses = response.json()
                    print(f"      🏢 Найдено складов: {len(warehouses)}")
                    for warehouse in warehouses[:3]:
                        print(f"         🏭 {warehouse.get('name')}: {warehouse.get('id')}")
                        
                elif "cargo" in endpoint:
                    data = response.json()
                    if isinstance(data, dict) and 'items' in data:
                        items = data.get('items', [])
                        print(f"      📦 Найдено грузов: {len(items)}")
                        for cargo in items[:3]:
                            print(f"         📦 {cargo.get('cargo_number', 'N/A')}: {cargo.get('status', 'N/A')}")
                    elif isinstance(data, list):
                        print(f"      📦 Найдено грузов: {len(data)}")
                        for cargo in data[:3]:
                            print(f"         📦 {cargo.get('cargo_number', 'N/A')}: {cargo.get('status', 'N/A')}")
                            
        except Exception as e:
            print(f"   {method} {endpoint}: ERROR - {e}")
    
    return working_endpoints

def create_test_cargo_250102(admin_token):
    """Создать тестовый груз с номером 250102 для диагностики"""
    print("\n🏗️ Создание тестового груза 250102...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Try to create via operator cargo endpoint
    cargo_data = {
        "sender_full_name": "Тестовый Отправитель 250102",
        "sender_phone": "+992000250102",
        "recipient_full_name": "Тестовый Получатель 250102",
        "recipient_phone": "+992000250103",
        "recipient_address": "Душанбе, тестовый адрес для груза 250102",
        "weight": 25.0,
        "cargo_name": "Тестовый груз 250102",
        "declared_value": 2000.0,
        "description": "Тестовый груз для диагностики видимости в списке размещения",
        "route": "moscow_to_tajikistan",
        "payment_method": "not_paid"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/operator/cargo/direct-accept", json=cargo_data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            created_cargo = data.get('created_cargo', [])
            if created_cargo:
                cargo = created_cargo[0]
                print(f"✅ Тестовый груз создан:")
                print(f"   📦 ID: {cargo.get('id')}")
                print(f"   🔢 Номер: {cargo.get('cargo_number')}")
                print(f"   🏭 Склад: {cargo.get('warehouse_id')}")
                return cargo
        else:
            print(f"❌ Ошибка создания груза: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при создании груза: {e}")
    
    return None

def manually_set_cargo_number(admin_token, cargo_id, target_number="250102"):
    """Попытаться вручную установить номер груза на 250102"""
    print(f"\n🔧 Попытка установить номер груза {target_number}...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # This would require a special admin endpoint to modify cargo number
    # For now, we'll just report what we have
    print(f"⚠️ Прямое изменение номера груза требует специального endpoint")
    print(f"   Созданный груз можно использовать для тестирования логики")
    
    return False

def main():
    admin_token = authenticate_admin()
    if not admin_token:
        return
    
    # Check available endpoints
    working_endpoints = check_available_endpoints(admin_token)
    print(f"\n✅ Работающих endpoints: {len(working_endpoints)}")
    
    # Try to create test cargo
    test_cargo = create_test_cargo_250102(admin_token)
    
    if test_cargo:
        cargo_number = test_cargo.get('cargo_number')
        print(f"\n🎯 РЕЗУЛЬТАТ:")
        print(f"   ✅ Создан тестовый груз: {cargo_number}")
        print(f"   📝 Можно использовать для тестирования диагностики")
        print(f"   🔧 Для тестирования замените '250102' на '{cargo_number}' в скрипте")
    else:
        print(f"\n❌ Не удалось создать тестовый груз")
        print(f"   Возможно, требуется авторизация оператора склада")

if __name__ == "__main__":
    main()