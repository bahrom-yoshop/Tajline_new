#!/usr/bin/env python3
"""
Search for cargo numbers similar to 250102
"""

import requests
import json

# Configuration
BACKEND_URL = "https://73ed2aa0-f922-4978-81e7-0ad7dcef385d.preview.emergentagent.com/api"

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

def search_cargo_patterns(admin_token):
    """Поиск грузов с похожими номерами"""
    print("\n🔍 Поиск грузов с номерами, похожими на 250102...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Patterns to search
    patterns = [
        "250102", "250102/01", "250102/02", "250102/03",
        "2501", "25010", "250101", "250103", "250104", "250105"
    ]
    
    found_cargos = []
    
    for pattern in patterns:
        try:
            response = requests.get(f"{BACKEND_URL}/debug/find-cargo-by-number/{pattern}", headers=headers)
            if response.status_code == 200:
                cargo_data = response.json()
                if cargo_data.get('found'):
                    cargo = cargo_data.get('cargo', {})
                    found_cargos.append({
                        'pattern': pattern,
                        'cargo_number': cargo.get('cargo_number'),
                        'id': cargo.get('id'),
                        'warehouse_id': cargo.get('warehouse_id'),
                        'destination_warehouse_id': cargo.get('destination_warehouse_id'),
                        'status': cargo.get('status'),
                        'hidden_reason': cargo.get('hidden_reason')
                    })
                    print(f"✅ Найден груз по паттерну {pattern}: {cargo.get('cargo_number')}")
        except Exception as e:
            print(f"⚠️ Ошибка поиска {pattern}: {e}")
    
    return found_cargos

def get_recent_cargos(admin_token):
    """Получить список последних грузов"""
    print("\n📦 Получение списка последних грузов...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        # Try to get cargo list
        response = requests.get(f"{BACKEND_URL}/admin/cargo/list?page=1&per_page=20", headers=headers)
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            print(f"✅ Получено {len(items)} грузов:")
            
            for cargo in items[:10]:  # Show first 10
                cargo_number = cargo.get('cargo_number', 'N/A')
                status = cargo.get('status', 'N/A')
                warehouse_id = cargo.get('warehouse_id', 'N/A')
                print(f"   📦 {cargo_number} - статус: {status}, склад: {warehouse_id}")
                
            return items
        else:
            print(f"❌ Ошибка получения списка грузов: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def main():
    admin_token = authenticate_admin()
    if not admin_token:
        return
    
    # Search for similar cargo numbers
    found_cargos = search_cargo_patterns(admin_token)
    
    if found_cargos:
        print(f"\n📋 Найдено {len(found_cargos)} грузов с похожими номерами:")
        for cargo in found_cargos:
            print(f"   🔍 Паттерн: {cargo['pattern']} → Груз: {cargo['cargo_number']}")
            print(f"      ID: {cargo['id']}")
            print(f"      Склад: {cargo['warehouse_id'] or 'ПУСТОЙ'}")
            print(f"      Назначение: {cargo['destination_warehouse_id'] or 'ПУСТОЙ'}")
            print(f"      Статус: {cargo['status']}")
            print(f"      Hidden reason: {cargo['hidden_reason'] or 'отсутствует'}")
            print()
    else:
        print("❌ Грузы с похожими номерами не найдены")
    
    # Get recent cargos
    recent_cargos = get_recent_cargos(admin_token)
    
    print(f"\n🎯 ИТОГ ПОИСКА:")
    print(f"   Найдено похожих грузов: {len(found_cargos)}")
    print(f"   Всего последних грузов: {len(recent_cargos)}")

if __name__ == "__main__":
    main()