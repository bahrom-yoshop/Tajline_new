#!/usr/bin/env python3
"""
🏭 СОЗДАНИЕ ОПЕРАТОРА СКЛАДА ДЛЯ ТЕСТИРОВАНИЯ
"""

import requests
import json

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

def create_warehouse_operator():
    session = requests.Session()
    
    # Авторизация администратора
    try:
        response = session.post(
            f"{BACKEND_URL}/auth/login",
            json=ADMIN_CREDENTIALS,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            admin_token = data["access_token"]
            session.headers.update({
                "Authorization": f"Bearer {admin_token}"
            })
            print("✅ Авторизация администратора успешна")
        else:
            print(f"❌ Ошибка авторизации администратора: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return
    
    # Получаем список складов
    try:
        response = session.get(f"{BACKEND_URL}/warehouses")
        
        if response.status_code == 200:
            warehouses = response.json()
            if warehouses:
                warehouse_id = warehouses[0].get('id')
                warehouse_name = warehouses[0].get('name', 'Неизвестный склад')
                print(f"✅ Найден склад для привязки: {warehouse_name} (ID: {warehouse_id})")
            else:
                print("❌ Нет доступных складов")
                return
        else:
            print(f"❌ Ошибка получения складов: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Ошибка получения складов: {e}")
        return
    
    # Создаем оператора склада
    operator_data = {
        "full_name": "Тестовый Оператор Приёма Заявок",
        "phone": "+79777888999",
        "address": "Москва, ул. Тестовая, 123",
        "password": "warehouse123",
        "warehouse_id": warehouse_id
    }
    
    try:
        response = session.post(
            f"{BACKEND_URL}/admin/create-operator",
            json=operator_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ОПЕРАТОР СКЛАДА СОЗДАН УСПЕШНО!")
            print(f"   Имя: {data.get('full_name', 'N/A')}")
            print(f"   Телефон: {data.get('phone', 'N/A')}")
            print(f"   Склад: {data.get('warehouse_name', 'N/A')}")
            print(f"   ID: {data.get('id', 'N/A')}")
            
            # Тестируем авторизацию
            test_credentials = {
                "phone": operator_data["phone"],
                "password": operator_data["password"]
            }
            
            print(f"\n🔐 ТЕСТИРОВАНИЕ АВТОРИЗАЦИИ НОВОГО ОПЕРАТОРА:")
            test_response = requests.post(
                f"{BACKEND_URL}/auth/login",
                json=test_credentials,
                headers={"Content-Type": "application/json"}
            )
            
            if test_response.status_code == 200:
                test_data = test_response.json()
                print(f"   ✅ АВТОРИЗАЦИЯ УСПЕШНА!")
                print(f"   Пользователь: {test_data['user']['full_name']}")
                print(f"   Роль: {test_data['user']['role']}")
                print(f"   Номер: {test_data['user'].get('user_number', 'N/A')}")
            else:
                print(f"   ❌ АВТОРИЗАЦИЯ НЕУСПЕШНА: HTTP {test_response.status_code}")
                print(f"   Ответ: {test_response.text}")
            
        else:
            print(f"❌ Ошибка создания оператора: HTTP {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка создания оператора: {e}")

if __name__ == "__main__":
    create_warehouse_operator()