#!/usr/bin/env python3
"""
COMPLETE WORKFLOW TEST: Test the full recipient information workflow
"""

import requests
import json

BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"

WAREHOUSE_OPERATOR = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

COURIER = {
    "phone": "+79991234567", 
    "password": "courier123"
}

def authenticate_user(phone, password, role_name):
    print(f"\n🔐 Авторизация {role_name} ({phone})...")
    response = requests.post(f"{BACKEND_URL}/auth/login", json={
        "phone": phone,
        "password": password
    })
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_info = data.get("user")
        print(f"✅ Успешная авторизация: {user_info.get('full_name')}")
        return token
    else:
        print(f"❌ Ошибка авторизации: {response.status_code}")
        return None

def create_pickup_request_with_recipient(operator_token):
    print(f"\n📦 Создание заявки на забор с данными получателя...")
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    request_data = {
        "sender_full_name": "Workflow Test Отправитель",
        "sender_phone": "+79991112233",
        "pickup_address": "Москва, ул. Workflow Test, 123",
        "pickup_date": "2025-01-20",
        "pickup_time_from": "10:00",
        "pickup_time_to": "18:00",
        "route": "moscow_to_tajikistan",
        "courier_fee": 500.0,
        "destination": "Workflow Test груз",
        # КРИТИЧЕСКИЕ ПОЛЯ ПОЛУЧАТЕЛЯ
        "recipient_full_name": "Workflow Test Получатель",
        "recipient_phone": "+992900123456",
        "recipient_address": "Душанбе, ул. Workflow Test, 456"
    }
    
    response = requests.post(f"{BACKEND_URL}/admin/courier/pickup-request", 
                           json=request_data, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        request_id = data.get("request_id")
        print(f"✅ Заявка создана: {request_id}")
        print(f"📋 Данные получателя:")
        print(f"   - ФИО: {request_data['recipient_full_name']}")
        print(f"   - Телефон: {request_data['recipient_phone']}")
        print(f"   - Адрес: {request_data['recipient_address']}")
        return request_id
    else:
        print(f"❌ Ошибка создания заявки: {response.status_code} - {response.text}")
        return None

def complete_courier_workflow(courier_token, request_id):
    print(f"\n🚚 Выполнение workflow курьера для заявки {request_id}...")
    headers = {"Authorization": f"Bearer {courier_token}"}
    
    # Accept
    response = requests.post(f"{BACKEND_URL}/courier/requests/{request_id}/accept", headers=headers)
    if response.status_code != 200:
        print(f"❌ Ошибка принятия заявки: {response.status_code}")
        return False
    print("✅ Заявка принята курьером")
    
    # Pickup
    response = requests.post(f"{BACKEND_URL}/courier/requests/{request_id}/pickup", headers=headers)
    if response.status_code != 200:
        print(f"❌ Ошибка забора груза: {response.status_code}")
        return False
    print("✅ Груз забран курьером")
    
    # Deliver to warehouse
    response = requests.post(f"{BACKEND_URL}/courier/requests/{request_id}/deliver-to-warehouse", headers=headers)
    if response.status_code != 200:
        print(f"❌ Ошибка доставки на склад: {response.status_code}")
        return False
    print("✅ Груз доставлен на склад")
    
    return True

def find_notification_for_request(operator_token, request_id):
    print(f"\n📬 Поиск уведомления для заявки {request_id}...")
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.get(f"{BACKEND_URL}/operator/warehouse-notifications", headers=headers)
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("notifications", [])
        
        for notification in notifications:
            if notification.get("request_number") == request_id:
                notification_id = notification.get("id")
                status = notification.get("status")
                print(f"✅ Уведомление найдено: {notification_id} (статус: {status})")
                return notification_id, status
        
        print(f"❌ Уведомление для заявки {request_id} не найдено")
        return None, None
    else:
        print(f"❌ Ошибка получения уведомлений: {response.status_code}")
        return None, None

def accept_warehouse_notification(operator_token, notification_id):
    print(f"\n📋 Принятие уведомления {notification_id} оператором склада...")
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.post(f"{BACKEND_URL}/operator/warehouse-notifications/{notification_id}/accept", 
                           headers=headers)
    
    if response.status_code == 200:
        print("✅ Уведомление принято оператором склада")
        return True
    else:
        print(f"❌ Ошибка принятия уведомления: {response.status_code} - {response.text}")
        return False

def send_to_placement(operator_token, notification_id):
    print(f"\n📤 Отправка заявки на размещение...")
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.post(f"{BACKEND_URL}/operator/warehouse-notifications/{notification_id}/send-to-placement", 
                           headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        cargo_number = data.get("cargo_number")
        print(f"✅ Заявка отправлена на размещение! Груз: {cargo_number}")
        return cargo_number
    else:
        print(f"❌ Ошибка отправки на размещение: {response.status_code} - {response.text}")
        return None

def verify_recipient_data_in_placement(operator_token, cargo_number):
    print(f"\n🏭 Проверка данных получателя в списке размещения...")
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        
        for item in items:
            if item.get("cargo_number") == cargo_number:
                print(f"✅ Груз найден в списке размещения!")
                
                recipient_name = item.get("recipient_full_name", "")
                recipient_phone = item.get("recipient_phone", "")
                recipient_address = item.get("recipient_address", "")
                
                print(f"📋 ДАННЫЕ ПОЛУЧАТЕЛЯ В ГРУЗЕ:")
                print(f"   - recipient_full_name: '{recipient_name}'")
                print(f"   - recipient_phone: '{recipient_phone}'")
                print(f"   - recipient_address: '{recipient_address}'")
                
                # Проверяем соответствие ожидаемым данным
                expected_name = "Workflow Test Получатель"
                expected_phone = "+992900123456"
                expected_address = "Душанбе, ул. Workflow Test, 456"
                
                if (recipient_name == expected_name and 
                    recipient_phone == expected_phone and 
                    recipient_address == expected_address):
                    print(f"🎉 КРИТИЧЕСКИЙ УСПЕХ: Данные получателя корректны!")
                    return True
                else:
                    print(f"❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Данные получателя неверные!")
                    print(f"   Ожидалось: {expected_name} / {expected_phone} / {expected_address}")
                    print(f"   Получено: {recipient_name} / {recipient_phone} / {recipient_address}")
                    return False
        
        print(f"❌ Груз {cargo_number} не найден в списке размещения")
        return False
    else:
        print(f"❌ Ошибка получения списка размещения: {response.status_code}")
        return False

def main():
    print("🎯 ПОЛНЫЙ ТЕСТ WORKFLOW ОТОБРАЖЕНИЯ ИНФОРМАЦИИ О ПОЛУЧАТЕЛЕ")
    print("=" * 80)
    
    test_results = []
    
    # 1. Авторизация
    operator_token = authenticate_user(WAREHOUSE_OPERATOR["phone"], WAREHOUSE_OPERATOR["password"], "Оператор склада")
    courier_token = authenticate_user(COURIER["phone"], COURIER["password"], "Курьер")
    
    if not operator_token or not courier_token:
        print("❌ Ошибка авторизации")
        return
    test_results.append("✅ Авторизация")
    
    # 2. Создание заявки с данными получателя
    request_id = create_pickup_request_with_recipient(operator_token)
    if not request_id:
        print("❌ Не удалось создать заявку")
        return
    test_results.append("✅ Создание заявки с данными получателя")
    
    # 3. Выполнение workflow курьера
    if not complete_courier_workflow(courier_token, request_id):
        print("❌ Ошибка в workflow курьера")
        return
    test_results.append("✅ Workflow курьера выполнен")
    
    # 4. Поиск уведомления
    notification_id, status = find_notification_for_request(operator_token, request_id)
    if not notification_id:
        print("❌ Уведомление не найдено")
        return
    test_results.append("✅ Уведомление найдено")
    
    # 5. Принятие уведомления оператором (КРИТИЧЕСКИЙ ШАГ!)
    if not accept_warehouse_notification(operator_token, notification_id):
        print("❌ Ошибка принятия уведомления")
        return
    test_results.append("✅ Уведомление принято оператором")
    
    # 6. Отправка на размещение
    cargo_number = send_to_placement(operator_token, notification_id)
    if not cargo_number:
        print("❌ Ошибка отправки на размещение")
        return
    test_results.append("✅ Отправка на размещение")
    
    # 7. ФИНАЛЬНАЯ ПРОВЕРКА: данные получателя в размещении
    if verify_recipient_data_in_placement(operator_token, cargo_number):
        test_results.append("✅ КРИТИЧЕСКИЙ УСПЕХ: Данные получателя в размещении")
    else:
        test_results.append("❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Данные получателя отсутствуют")
    
    # Итоговый отчет
    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 80)
    
    success_count = len([r for r in test_results if r.startswith("✅")])
    total_count = len(test_results)
    success_rate = (success_count / total_count) * 100
    
    for result in test_results:
        print(result)
    
    print(f"\n📈 SUCCESS RATE: {success_rate:.1f}% ({success_count}/{total_count})")
    
    if success_rate == 100:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ:")
        print("   - Полный цикл от создания заявки до отображения в размещении")
        print("   - Данные получателя (ФИО, телефон, адрес) сохраняются и передаются корректно")
        print("   - Backend chain работает: создание → send_pickup_request_to_placement → available-for-placement")
    else:
        print(f"\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ: {total_count - success_count} из {total_count} тестов не пройдены")

if __name__ == "__main__":
    main()