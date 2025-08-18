#!/usr/bin/env python3
"""
🏗️ СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ ДЛЯ ТЕСТИРОВАНИЯ ФОРМЫ ПРИЁМА ЗАЯВОК
"""

import requests
import json
import uuid
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

def setup_test_data():
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
    
    # Создаем дополнительные склады
    warehouses_to_create = [
        {
            "name": "Душанбе Склад №1",
            "location": "Душанбе, Таджикистан",
            "address": "Душанбе, проспект Рудаки, 123",
            "blocks_count": 2,
            "shelves_per_block": 2,
            "cells_per_shelf": 10
        },
        {
            "name": "Худжанд Склад №1",
            "location": "Худжанд, Таджикистан",
            "address": "Худжанд, ул. Ленина, 456",
            "blocks_count": 1,
            "shelves_per_block": 3,
            "cells_per_shelf": 15
        }
    ]
    
    created_warehouses = []
    
    for warehouse_data in warehouses_to_create:
        try:
            response = session.post(
                f"{BACKEND_URL}/admin/warehouses",
                json=warehouse_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                warehouse = response.json()
                created_warehouses.append(warehouse)
                print(f"✅ Создан склад: {warehouse_data['name']}")
            else:
                print(f"❌ Ошибка создания склада {warehouse_data['name']}: HTTP {response.status_code}")
                print(f"   Ответ: {response.text}")
                
        except Exception as e:
            print(f"❌ Ошибка создания склада {warehouse_data['name']}: {e}")
    
    # Создаем тестовые уведомления о поступивших грузах
    # Сначала нужно создать заявку на забор груза
    pickup_request_data = {
        "sender_full_name": "Тестовый Отправитель Заявки",
        "sender_phone": "+79991234567",
        "cargo_name": "Тестовый груз для приёма",
        "pickup_address": "Москва, ул. Тестовая, 789",
        "pickup_date": "2025-01-16",
        "pickup_time_from": "10:00",
        "pickup_time_to": "18:00",
        "delivery_method": "pickup",
        "courier_fee": 500.0,
        "weight": 10.0,
        "declared_value": 3600.0,
        "description": "Тестовое описание груза для проверки формы приёма"
    }
    
    try:
        # Создаем заявку на забор груза через админа
        response = session.post(
            f"{BACKEND_URL}/admin/courier/pickup-request",
            json=pickup_request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            pickup_request = response.json()
            print(f"✅ Создана заявка на забор груза: {pickup_request.get('request_number', 'N/A')}")
            
            # Теперь создаем уведомление для оператора склада
            notification_data = {
                "request_id": pickup_request.get("id"),
                "request_number": pickup_request.get("request_number"),
                "request_type": "pickup_delivery",
                "courier_name": "Тестовый Курьер",
                "courier_id": "test-courier-id",
                "sender_full_name": pickup_request_data["sender_full_name"],
                "sender_phone": pickup_request_data["sender_phone"],
                "pickup_address": pickup_request_data["pickup_address"],
                "destination": "Склад для размещения",
                "courier_fee": pickup_request_data["courier_fee"],
                "payment_method": "cash",
                "delivered_at": datetime.utcnow().isoformat(),
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Добавляем уведомление напрямую в базу данных (симуляция)
            print(f"✅ Подготовлены данные для уведомления оператора склада")
            
        else:
            print(f"❌ Ошибка создания заявки на забор: HTTP {response.status_code}")
            print(f"   Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка создания заявки на забор: {e}")
    
    # Выводим итоговую информацию
    print(f"\n📊 ИТОГИ СОЗДАНИЯ ТЕСТОВЫХ ДАННЫХ:")
    print(f"✅ Создано складов: {len(created_warehouses)}")
    
    # Получаем обновленный список складов
    try:
        response = session.get(f"{BACKEND_URL}/warehouses")
        if response.status_code == 200:
            all_warehouses = response.json()
            print(f"📦 Всего складов в системе: {len(all_warehouses)}")
            for warehouse in all_warehouses:
                print(f"   - {warehouse.get('name', 'N/A')} (Локация: {warehouse.get('location', 'N/A')})")
        else:
            print(f"❌ Ошибка получения складов: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка получения складов: {e}")

if __name__ == "__main__":
    setup_test_data()