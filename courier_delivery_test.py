#!/usr/bin/env python3
"""
🎯 ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ: Проверка фильтрации для courier_requests (доставка)
"""

import requests
import json
import os
from datetime import datetime, timedelta

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://d5f33009-cb8d-4f1e-ae7c-23f5e21662c0.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def log(message):
    """Логирование с временной меткой"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def test_courier_delivery_requests():
    """Тестирование фильтрации для courier_requests (доставка)"""
    log("🎯 ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ: courier_requests (доставка)")
    log("=" * 60)
    
    session = requests.Session()
    
    # Авторизация администратора
    log("🔐 Авторизация администратора...")
    login_data = {"phone": "+79999888777", "password": "admin123"}
    response = session.post(f"{API_BASE}/auth/login", json=login_data)
    
    if response.status_code != 200:
        log("❌ Ошибка авторизации администратора")
        return False
        
    admin_token = response.json().get('access_token')
    log("✅ Администратор авторизован")
    
    # Получение складов
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = session.get(f"{API_BASE}/warehouses", headers=headers)
    
    if response.status_code != 200 or not response.json():
        log("❌ Ошибка получения складов")
        return False
        
    warehouse_id = response.json()[0].get('id')
    log(f"✅ Найден склад: {warehouse_id}")
    
    # Создание тестового курьера
    import random
    phone_suffix = random.randint(1000, 9999)
    phone = f"+7999{phone_suffix}333"
    
    courier_data = {
        "full_name": f"Тестовый Курьер Доставки {phone_suffix}",
        "phone": phone,
        "password": "courier123",
        "address": "Тестовый адрес курьера",
        "transport_type": "car",
        "transport_number": f"TEST{phone[-4:]}",
        "transport_capacity": 500.0,
        "assigned_warehouse_id": warehouse_id
    }
    
    response = session.post(f"{API_BASE}/admin/couriers/create", json=courier_data, headers=headers)
    
    if response.status_code != 200:
        log("❌ Ошибка создания курьера")
        return False
        
    courier_id = response.json().get('courier_id')
    log(f"✅ Курьер создан: {courier_id}")
    
    # Авторизация курьера
    login_data = {"phone": phone, "password": "courier123"}
    response = session.post(f"{API_BASE}/auth/login", json=login_data)
    
    if response.status_code != 200:
        log("❌ Ошибка авторизации курьера")
        return False
        
    courier_token = response.json().get('access_token')
    log("✅ Курьер авторизован")
    
    # Создание тестовой заявки на доставку
    delivery_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    request_data = {
        "sender_full_name": "Тестовый Отправитель Доставки",
        "sender_phone": "+79991234567",
        "recipient_full_name": "Тестовый Получатель Доставки",
        "recipient_phone": "+79987654321",
        "recipient_address": "Тестовый адрес получателя доставки",
        "pickup_address": "Тестовый адрес забора доставки",
        "delivery_date": delivery_date,
        "delivery_time_from": "14:00",
        "delivery_time_to": "16:00",
        "cargo_name": "Тестовый груз для доставки",
        "weight": 15.0,
        "declared_value": 2000.0,
        "description": "Описание тестового груза для доставки",
        "route": "moscow_to_tajikistan",
        "courier_fee": 750.0,
        "delivery_method": "courier",
        "payment_method": "card"
    }
    
    response = session.post(f"{API_BASE}/admin/courier/delivery-request", json=request_data, headers=headers)
    
    if response.status_code != 200:
        log(f"❌ Ошибка создания заявки на доставку: {response.status_code} - {response.text}")
        return False
        
    request_id = response.json().get('request_id')
    log(f"✅ Заявка на доставку создана: {request_id}")
    
    # Проверка новых заявок ДО принятия
    courier_headers = {"Authorization": f"Bearer {courier_token}"}
    response = session.get(f"{API_BASE}/courier/requests/new", headers=courier_headers)
    
    if response.status_code != 200:
        log("❌ Ошибка получения новых заявок")
        return False
        
    new_requests_before = response.json().get('new_requests', [])
    count_before = len(new_requests_before)
    
    # Проверяем, что заявка видна в новых
    delivery_request_visible = any(req.get('id') == request_id for req in new_requests_before)
    
    log(f"📊 ДО принятия: курьер видит {count_before} заявок")
    if delivery_request_visible:
        log("✅ Заявка на доставку видна в новых заявках")
    else:
        log("❌ Заявка на доставку НЕ видна в новых заявках")
        return False
    
    # Принятие заявки
    response = session.post(f"{API_BASE}/courier/requests/{request_id}/accept", headers=courier_headers)
    
    if response.status_code != 200:
        log(f"❌ Ошибка принятия заявки: {response.status_code} - {response.text}")
        return False
        
    log("✅ Заявка на доставку принята")
    
    # Проверка новых заявок ПОСЛЕ принятия
    response = session.get(f"{API_BASE}/courier/requests/new", headers=courier_headers)
    
    if response.status_code != 200:
        log("❌ Ошибка получения новых заявок после принятия")
        return False
        
    new_requests_after = response.json().get('new_requests', [])
    count_after = len(new_requests_after)
    
    # Проверяем, что заявка исчезла из новых
    delivery_request_still_visible = any(req.get('id') == request_id for req in new_requests_after)
    
    log(f"📊 ПОСЛЕ принятия: курьер видит {count_after} заявок")
    if not delivery_request_still_visible:
        log("🎉 ОТЛИЧНО: Принятая заявка на доставку исчезла из новых заявок!")
        success = True
    else:
        log("❌ ПРОБЛЕМА: Принятая заявка на доставку все еще видна в новых заявках")
        success = False
    
    # Проверка принятых заявок
    response = session.get(f"{API_BASE}/courier/requests/accepted", headers=courier_headers)
    
    if response.status_code == 200:
        accepted_requests = response.json().get('accepted_requests', [])
        delivery_in_accepted = any(req.get('id') == request_id for req in accepted_requests)
        
        if delivery_in_accepted:
            log("✅ Принятая заявка на доставку появилась в принятых заявках")
        else:
            log("❌ Принятая заявка на доставку НЕ появилась в принятых заявках")
            success = False
    
    # Очистка
    log("🧹 Очистка тестовых данных...")
    session.delete(f"{API_BASE}/admin/courier-requests/{request_id}", headers=headers)
    session.delete(f"{API_BASE}/admin/couriers/{courier_id}", headers=headers)
    log("✅ Тестовые данные очищены")
    
    return success

if __name__ == "__main__":
    success = test_courier_delivery_requests()
    if success:
        print("\n🎉 ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ ПРОШЛО УСПЕШНО!")
    else:
        print("\n❌ ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")