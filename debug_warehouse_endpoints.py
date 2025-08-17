#!/usr/bin/env python3
"""
Debug script to check warehouse endpoints
"""

import requests
import json
import os

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://115d3eaa-ee86-43cd-a3c2-5f678c029aa4.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def debug_auth_and_warehouses():
    session = requests.Session()
    
    print("🔐 Тестирование авторизации админа...")
    admin_login_data = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    admin_response = session.post(f"{API_BASE}/auth/login", json=admin_login_data)
    print(f"Статус авторизации админа: {admin_response.status_code}")
    
    if admin_response.status_code == 200:
        admin_data = admin_response.json()
        admin_token = admin_data.get('access_token')
        user_info = admin_data.get('user', {})
        print(f"✅ Админ авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
        
        # Тестируем endpoints складов
        endpoints = [
            "/api/warehouses",
            "/api/operator/warehouses"
        ]
        
        for endpoint in endpoints:
            print(f"\n🏭 Тестирование {endpoint}...")
            headers = {"Authorization": f"Bearer {admin_token}"}
            response = session.get(f"{API_BASE}{endpoint}", headers=headers)
            print(f"Статус: {response.status_code}")
            
            if response.status_code == 200:
                warehouses = response.json()
                print(f"✅ Получено {len(warehouses)} складов")
                for i, warehouse in enumerate(warehouses[:2], 1):
                    print(f"   {i}. {warehouse.get('name')} (ID: {warehouse.get('id')})")
            else:
                print(f"❌ Ошибка: {response.text}")
    else:
        print(f"❌ Ошибка авторизации: {admin_response.text}")
        
    print("\n🔐 Тестирование авторизации оператора...")
    operator_login_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    operator_response = session.post(f"{API_BASE}/auth/login", json=operator_login_data)
    print(f"Статус авторизации оператора: {operator_response.status_code}")
    
    if operator_response.status_code == 200:
        operator_data = operator_response.json()
        operator_token = operator_data.get('access_token')
        user_info = operator_data.get('user', {})
        print(f"✅ Оператор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
        
        # Тестируем endpoint складов оператора
        print(f"\n🏭 Тестирование /api/operator/warehouses для оператора...")
        headers = {"Authorization": f"Bearer {operator_token}"}
        response = session.get(f"{API_BASE}/operator/warehouses", headers=headers)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            warehouses = response.json()
            print(f"✅ Получено {len(warehouses)} складов для оператора")
            for i, warehouse in enumerate(warehouses, 1):
                print(f"   {i}. {warehouse.get('name')} (ID: {warehouse.get('id')})")
                
            # Тестируем endpoint available-for-placement
            print(f"\n📦 Тестирование /api/operator/cargo/available-for-placement...")
            response = session.get(f"{API_BASE}/operator/cargo/available-for-placement", headers=headers)
            print(f"Статус: {response.status_code}")
            
            if response.status_code == 200:
                cargo_list = response.json()
                print(f"✅ Получено {len(cargo_list)} грузов для размещения")
                for i, cargo in enumerate(cargo_list[:3], 1):
                    print(f"   {i}. {cargo.get('cargo_number')} (warehouse_id: {cargo.get('warehouse_id')}, destination: {cargo.get('destination_warehouse_id', 'не указан')})")
            else:
                print(f"❌ Ошибка получения грузов: {response.text}")
        else:
            print(f"❌ Ошибка: {response.text}")
    else:
        print(f"❌ Ошибка авторизации оператора: {operator_response.text}")

if __name__ == "__main__":
    debug_auth_and_warehouses()