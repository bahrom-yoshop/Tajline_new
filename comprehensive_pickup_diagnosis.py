#!/usr/bin/env python3
"""
COMPREHENSIVE PICKUP REQUEST DIAGNOSIS
Создание тестовых данных и диагностика проблемы с заявками на забор
"""

import requests
import json
from datetime import datetime

BACKEND_URL = "https://cargo-system-debug.preview.emergentagent.com/api"

def log_step(step_name, details=""):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] 🔍 {step_name}")
    if details:
        print(f"   {details}")

def log_success(message):
    print(f"   ✅ {message}")

def log_error(message):
    print(f"   ❌ {message}")

def log_info(message):
    print(f"   ℹ️ {message}")

def authorize_admin():
    """Авторизация администратора"""
    log_step("АВТОРИЗАЦИЯ АДМИНИСТРАТОРА")
    
    response = requests.post(f"{BACKEND_URL}/auth/login", json={
        "phone": "+79999888777",
        "password": "admin123"
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_info = data.get("user", {})
        log_success(f"Авторизован: {user_info.get('full_name', 'Unknown')}")
        return token
    else:
        log_error(f"Ошибка авторизации: {response.status_code}")
        return None

def authorize_operator():
    """Авторизация оператора склада"""
    log_step("АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА")
    
    response = requests.post(f"{BACKEND_URL}/auth/login", json={
        "phone": "+79777888999",
        "password": "warehouse123"
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_info = data.get("user", {})
        log_success(f"Авторизован: {user_info.get('full_name', 'Unknown')}")
        return token
    else:
        log_error(f"Ошибка авторизации: {response.status_code}")
        return None

def create_test_cargo_with_pickup(admin_token):
    """Создание тестового груза с заявкой на забор"""
    log_step("СОЗДАНИЕ ТЕСТОВОГО ГРУЗА С ЗАЯВКОЙ НА ЗАБОР")
    
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    # Создаем груз с заявкой на забор
    cargo_data = {
        "sender_full_name": "Тестовый Отправитель Диагностики",
        "sender_phone": "+79991234567",
        "recipient_full_name": "Тестовый Получатель Диагностики",
        "recipient_phone": "+992123456789",
        "recipient_address": "Тестовый адрес получателя диагностики",
        "weight": 5.0,
        "cargo_name": "Тестовый груз для диагностики заявок на забор",
        "declared_value": 1000.0,
        "description": "Тестовый груз для диагностики проблемы с заявками на забор после удаления",
        "route": "moscow_to_tajikistan",
        "pickup_required": True,
        "pickup_address": "Москва, ул. Тестовая Диагностика, 123",
        "pickup_date": "2025-08-15",
        "pickup_time_from": "10:00",
        "pickup_time_to": "18:00",
        "delivery_method": "pickup",
        "courier_fee": 500.0
    }
    
    response = requests.post(f"{BACKEND_URL}/operator/cargo", headers=headers, json=cargo_data)
    
    if response.status_code == 201:
        cargo_info = response.json()
        log_success(f"Создан груз: {cargo_info.get('cargo_number', 'N/A')}")
        return cargo_info
    else:
        log_error(f"Ошибка создания груза: {response.status_code} - {response.text}")
        return None

def check_pickup_requests_state(operator_token, stage):
    """Проверка состояния заявок на забор"""
    log_step(f"ПРОВЕРКА ЗАЯВОК НА ЗАБОР - {stage}")
    
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    # Проверяем заявки на забор
    pickup_response = requests.get(f"{BACKEND_URL}/operator/pickup-requests", headers=headers)
    
    if pickup_response.status_code == 200:
        pickup_data = pickup_response.json()
        pickup_requests = pickup_data.get("pickup_requests", [])
        total_count = pickup_data.get("total_count", 0)
        
        log_info(f"Всего заявок на забор: {total_count}")
        log_info(f"Заявок в ответе: {len(pickup_requests)}")
        
        # Ищем заявки с номером 000000/00
        zero_requests = [req for req in pickup_requests if req.get("request_number") == "000000/00"]
        if zero_requests:
            log_error(f"НАЙДЕНО {len(zero_requests)} заявок с номером 000000/00!")
            for i, req in enumerate(zero_requests[:3]):
                log_info(f"  Заявка {i+1}: cargo_name='{req.get('cargo_name', 'N/A')}', sender='{req.get('sender_full_name', 'N/A')}'")
        else:
            log_info("Заявок с номером 000000/00 не найдено")
        
        return pickup_requests
    else:
        log_error(f"Ошибка получения заявок на забор: {pickup_response.status_code}")
        return []

def check_warehouse_notifications_state(admin_token, stage):
    """Проверка состояния уведомлений склада"""
    log_step(f"ПРОВЕРКА УВЕДОМЛЕНИЙ СКЛАДА - {stage}")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    notifications_response = requests.get(f"{BACKEND_URL}/operator/warehouse-notifications", headers=headers)
    
    if notifications_response.status_code == 200:
        data = notifications_response.json()
        notifications = data.get("notifications", [])
        
        log_info(f"Всего уведомлений: {len(notifications)}")
        
        # Ищем уведомления с номером 000000/00
        zero_notifications = [notif for notif in notifications if notif.get("request_number") == "000000/00"]
        if zero_notifications:
            log_error(f"НАЙДЕНО {len(zero_notifications)} уведомлений с номером 000000/00!")
            for i, notif in enumerate(zero_notifications[:3]):
                log_info(f"  Уведомление {i+1}: sender='{notif.get('sender_full_name', 'N/A')}', status='{notif.get('status', 'N/A')}'")
        else:
            log_info("Уведомлений с номером 000000/00 не найдено")
        
        return notifications
    else:
        log_error(f"Ошибка получения уведомлений: {notifications_response.status_code}")
        return []

def get_cargo_for_placement(operator_token):
    """Получение грузов для размещения"""
    log_step("ПОЛУЧЕНИЕ ГРУЗОВ ДЛЯ РАЗМЕЩЕНИЯ")
    
    headers = {"Authorization": f"Bearer {operator_token}"}
    response = requests.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        cargo_items = data.get("items", [])
        log_success(f"Получено {len(cargo_items)} грузов для размещения")
        
        # Показываем первые несколько грузов
        for i, cargo in enumerate(cargo_items[:5]):
            log_info(f"  Груз {i+1}: {cargo.get('cargo_number', 'N/A')} - {cargo.get('sender_full_name', 'N/A')}")
        
        return cargo_items[:3]  # Возвращаем первые 3 для удаления
    else:
        log_error(f"Ошибка получения грузов: {response.status_code}")
        return []

def perform_bulk_deletion(operator_token, cargo_items):
    """Выполнение массового удаления грузов"""
    if not cargo_items:
        log_error("Нет грузов для удаления")
        return False
    
    log_step("МАССОВОЕ УДАЛЕНИЕ ГРУЗОВ ИЗ РАЗМЕЩЕНИЯ")
    
    cargo_ids = [cargo.get("id") for cargo in cargo_items if cargo.get("id")]
    cargo_numbers = [cargo.get("cargo_number") for cargo in cargo_items if cargo.get("cargo_number")]
    
    log_info(f"Удаляем {len(cargo_ids)} грузов: {cargo_numbers}")
    
    headers = {"Authorization": f"Bearer {operator_token}", "Content-Type": "application/json"}
    payload = {"cargo_ids": cargo_ids}
    
    response = requests.delete(f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement", 
                             headers=headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        deleted_count = data.get("deleted_count", 0)
        log_success(f"Успешно удалено {deleted_count} грузов")
        return True
    else:
        log_error(f"Ошибка удаления: {response.status_code} - {response.text}")
        return False

def main():
    print("=" * 80)
    print("🔍 COMPREHENSIVE PICKUP REQUEST DIAGNOSIS")
    print("   Создание тестовых данных и диагностика проблемы")
    print("=" * 80)
    
    # 1. Авторизация
    admin_token = authorize_admin()
    operator_token = authorize_operator()
    
    if not admin_token or not operator_token:
        print("❌ Ошибка авторизации")
        return
    
    # 2. Проверка начального состояния
    log_step("ЭТАП 1: ПРОВЕРКА НАЧАЛЬНОГО СОСТОЯНИЯ")
    pickup_requests_initial = check_pickup_requests_state(operator_token, "НАЧАЛЬНОЕ")
    notifications_initial = check_warehouse_notifications_state(admin_token, "НАЧАЛЬНОЕ")
    
    # 3. Создание тестового груза с заявкой на забор
    log_step("ЭТАП 2: СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ")
    test_cargo = create_test_cargo_with_pickup(admin_token)
    
    # 4. Проверка состояния после создания груза
    log_step("ЭТАП 3: ПРОВЕРКА ПОСЛЕ СОЗДАНИЯ ГРУЗА")
    pickup_requests_after_create = check_pickup_requests_state(operator_token, "ПОСЛЕ СОЗДАНИЯ")
    notifications_after_create = check_warehouse_notifications_state(admin_token, "ПОСЛЕ СОЗДАНИЯ")
    
    # 5. Получение грузов для размещения
    log_step("ЭТАП 4: ПОДГОТОВКА К УДАЛЕНИЮ")
    cargo_items = get_cargo_for_placement(operator_token)
    
    if not cargo_items:
        log_error("Нет грузов для удаления - завершаем диагностику")
        return
    
    # 6. Выполнение массового удаления
    log_step("ЭТАП 5: МАССОВОЕ УДАЛЕНИЕ")
    deletion_success = perform_bulk_deletion(operator_token, cargo_items)
    
    if not deletion_success:
        log_error("Удаление не выполнено")
        return
    
    # 7. Проверка состояния после удаления
    log_step("ЭТАП 6: ПРОВЕРКА ПОСЛЕ УДАЛЕНИЯ")
    pickup_requests_after_delete = check_pickup_requests_state(operator_token, "ПОСЛЕ УДАЛЕНИЯ")
    notifications_after_delete = check_warehouse_notifications_state(admin_token, "ПОСЛЕ УДАЛЕНИЯ")
    
    # 8. Анализ результатов
    log_step("ЭТАП 7: АНАЛИЗ РЕЗУЛЬТАТОВ")
    
    zero_pickup_initial = len([req for req in pickup_requests_initial if req.get("request_number") == "000000/00"])
    zero_pickup_final = len([req for req in pickup_requests_after_delete if req.get("request_number") == "000000/00"])
    
    zero_notif_initial = len([notif for notif in notifications_initial if notif.get("request_number") == "000000/00"])
    zero_notif_final = len([notif for notif in notifications_after_delete if notif.get("request_number") == "000000/00"])
    
    print("\n" + "=" * 80)
    print("📋 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:")
    print("=" * 80)
    
    print(f"ЗАЯВКИ НА ЗАБОР:")
    print(f"  - До удаления: {len(pickup_requests_initial)} (000000/00: {zero_pickup_initial})")
    print(f"  - После удаления: {len(pickup_requests_after_delete)} (000000/00: {zero_pickup_final})")
    
    print(f"УВЕДОМЛЕНИЯ СКЛАДА:")
    print(f"  - До удаления: {len(notifications_initial)} (000000/00: {zero_notif_initial})")
    print(f"  - После удаления: {len(notifications_after_delete)} (000000/00: {zero_notif_final})")
    
    if zero_pickup_final > zero_pickup_initial or zero_notif_final > zero_notif_initial:
        print("\n🚨 ПРОБЛЕМА ОБНАРУЖЕНА:")
        print("   Количество записей с номером 000000/00 увеличилось после удаления!")
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("   1. Проверить логику обновления заявок на забор при удалении грузов")
        print("   2. Добавить синхронизацию между коллекциями")
        print("   3. Исправить обновление полей cargo_name, cargo_number, sender_full_name")
    else:
        print("\n✅ ПРОБЛЕМА НЕ ВОСПРОИЗВЕДЕНА")
        print("   Система работает корректно")
    
    print("=" * 80)

if __name__ == "__main__":
    main()