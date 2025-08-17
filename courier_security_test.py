#!/usr/bin/env python3
"""
ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ: Безопасность и обработка ошибок DELETE endpoint курьеров
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://tajline-manager-1.preview.emergentagent.com/api"

# Учетные данные для тестирования
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

# Попробуем разные учетные данные оператора
OPERATOR_CREDENTIALS_LIST = [
    {"phone": "+79777888999", "password": "warehouse123"},
    {"phone": "+79777888999", "password": "operator123"},
    {"phone": "+79999888888", "password": "operator123"}
]

def make_request(method, endpoint, headers=None, json_data=None, params=None):
    """Универсальная функция для HTTP запросов"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        response = requests.request(
            method=method,
            url=url, 
            headers=headers,
            json=json_data,
            params=params,
            timeout=30
        )
        return response
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def authenticate_user(credentials, user_type="admin"):
    """Авторизация пользователя"""
    print(f"\n🔐 Авторизация {user_type} ({credentials['phone']})...")
    
    response = make_request("POST", "/auth/login", json_data=credentials)
    
    if not response or response.status_code != 200:
        print(f"❌ Ошибка авторизации {user_type}: {response.status_code if response else 'No response'}")
        if response:
            print(f"Response: {response.text}")
        return None
    
    data = response.json()
    token = data.get("access_token")
    user_info = data.get("user", {})
    
    print(f"✅ Успешная авторизация {user_type}: {user_info.get('full_name', 'Unknown')} (роль: {user_info.get('role', 'Unknown')})")
    return token, user_info.get('role', 'Unknown')

def test_operator_authorization():
    """Тестирование авторизации оператора и проверка безопасности"""
    print("\n🔒 ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ БЕЗОПАСНОСТИ")
    print("=" * 60)
    
    # Авторизация администратора
    admin_result = authenticate_user(ADMIN_CREDENTIALS, "администратора")
    if not admin_result:
        print("❌ Не удалось авторизоваться как администратор")
        return False
    
    admin_token, admin_role = admin_result
    
    # Создаем тестового курьера для тестирования безопасности
    print("\n👤 Создание тестового курьера для тестирования безопасности...")
    
    # Получаем склады
    headers = {"Authorization": f"Bearer {admin_token}"}
    warehouses_response = make_request("GET", "/warehouses", headers=headers)
    
    if not warehouses_response or warehouses_response.status_code != 200:
        print("❌ Не удалось получить список складов")
        return False
    
    warehouses = warehouses_response.json()
    if not warehouses:
        print("❌ Нет доступных складов")
        return False
    
    warehouse_id = warehouses[0]["id"]
    
    # Создаем курьера
    import random
    test_phone = f"+7999{random.randint(1000000, 9999999)}"
    
    courier_data = {
        "full_name": "Тестовый Курьер Безопасность",
        "phone": test_phone,
        "password": "testcourier123",
        "address": "Тестовый адрес курьера",
        "transport_type": "car",
        "transport_number": f"SEC{random.randint(100, 999)}",
        "transport_capacity": 500.0,
        "assigned_warehouse_id": warehouse_id
    }
    
    courier_response = make_request("POST", "/admin/couriers/create", headers=headers, json_data=courier_data)
    
    if not courier_response or courier_response.status_code != 200:
        print("❌ Не удалось создать тестового курьера")
        return False
    
    courier_info = courier_response.json()
    courier_id = courier_info.get("courier_id")
    print(f"✅ Тестовый курьер создан: ID {courier_id}")
    
    # Пробуем найти оператора
    operator_token = None
    operator_role = None
    
    for credentials in OPERATOR_CREDENTIALS_LIST:
        result = authenticate_user(credentials, "оператора")
        if result:
            operator_token, operator_role = result
            if operator_role in ["warehouse_operator", "operator"]:
                break
    
    if not operator_token:
        print("⚠️ Не удалось найти действующего оператора, создаем нового...")
        
        # Создаем оператора для тестирования
        operator_phone = f"+7999{random.randint(1000000, 9999999)}"
        operator_data = {
            "full_name": "Тестовый Оператор Безопасность",
            "phone": operator_phone,
            "password": "testoperator123",
            "address": "Тестовый адрес оператора",
            "warehouse_id": warehouse_id
        }
        
        operator_response = make_request("POST", "/admin/operators/create", headers=headers, json_data=operator_data)
        
        if operator_response and operator_response.status_code == 200:
            print(f"✅ Тестовый оператор создан: {operator_phone}")
            
            # Авторизуемся как новый оператор
            operator_credentials = {"phone": operator_phone, "password": "testoperator123"}
            result = authenticate_user(operator_credentials, "нового оператора")
            if result:
                operator_token, operator_role = result
        
        if not operator_token:
            print("⚠️ Не удалось создать или авторизовать оператора, тестируем без авторизации")
    
    # Тестируем безопасность
    security_tests = []
    
    # ТЕСТ 1: Попытка удаления курьера оператором
    if operator_token:
        print(f"\n🧪 ТЕСТ БЕЗОПАСНОСТИ 1: Попытка удаления курьера оператором (роль: {operator_role})...")
        
        operator_headers = {"Authorization": f"Bearer {operator_token}"}
        delete_response = make_request("DELETE", f"/admin/couriers/{courier_id}", headers=operator_headers)
        
        if not delete_response:
            print("❌ ТЕСТ БЕЗОПАСНОСТИ 1 ПРОВАЛЕН: Нет ответа от сервера")
            security_tests.append(False)
        elif delete_response.status_code == 403:
            print("✅ ТЕСТ БЕЗОПАСНОСТИ 1 ПРОЙДЕН: Оператор получает 403 Forbidden")
            security_tests.append(True)
        else:
            print(f"❌ ТЕСТ БЕЗОПАСНОСТИ 1 ПРОВАЛЕН: Ожидался 403, получен {delete_response.status_code}")
            print(f"Response: {delete_response.text}")
            security_tests.append(False)
    else:
        print("⚠️ ТЕСТ БЕЗОПАСНОСТИ 1: ПРОПУЩЕН (нет токена оператора)")
        security_tests.append("ПРОПУЩЕН")
    
    # ТЕСТ 2: Попытка удаления без авторизации
    print(f"\n🧪 ТЕСТ БЕЗОПАСНОСТИ 2: Попытка удаления курьера без авторизации...")
    
    no_auth_response = make_request("DELETE", f"/admin/couriers/{courier_id}")
    
    if not no_auth_response:
        print("❌ ТЕСТ БЕЗОПАСНОСТИ 2 ПРОВАЛЕН: Нет ответа от сервера")
        security_tests.append(False)
    elif no_auth_response.status_code == 401:
        print("✅ ТЕСТ БЕЗОПАСНОСТИ 2 ПРОЙДЕН: Без авторизации получаем 401 Unauthorized")
        security_tests.append(True)
    else:
        print(f"❌ ТЕСТ БЕЗОПАСНОСТИ 2 ПРОВАЛЕН: Ожидался 401, получен {no_auth_response.status_code}")
        security_tests.append(False)
    
    # ТЕСТ 3: Попытка удаления несуществующего курьера (повторный тест)
    print(f"\n🧪 ТЕСТ БЕЗОПАСНОСТИ 3: Попытка удаления несуществующего курьера...")
    
    fake_courier_id = "00000000-0000-0000-0000-000000000000"
    fake_delete_response = make_request("DELETE", f"/admin/couriers/{fake_courier_id}", headers=headers)
    
    if not fake_delete_response:
        print("❌ ТЕСТ БЕЗОПАСНОСТИ 3 ПРОВАЛЕН: Нет ответа от сервера")
        security_tests.append(False)
    elif fake_delete_response.status_code == 404:
        print("✅ ТЕСТ БЕЗОПАСНОСТИ 3 ПРОЙДЕН: Несуществующий курьер возвращает 404")
        security_tests.append(True)
    else:
        print(f"❌ ТЕСТ БЕЗОПАСНОСТИ 3 ПРОВАЛЕН: Ожидался 404, получен {fake_delete_response.status_code}")
        print(f"Response: {fake_delete_response.text}")
        security_tests.append(False)
    
    # Удаляем тестового курьера
    print(f"\n🧹 Очистка: Удаление тестового курьера...")
    cleanup_response = make_request("DELETE", f"/admin/couriers/{courier_id}", headers=headers)
    if cleanup_response and cleanup_response.status_code == 200:
        print("✅ Тестовый курьер успешно удален")
    
    # Подведение итогов тестов безопасности
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ БЕЗОПАСНОСТИ")
    print("=" * 60)
    
    passed_security = 0
    total_security = 0
    
    test_names = [
        "Защита от удаления оператором",
        "Защита от удаления без авторизации", 
        "Обработка несуществующего курьера"
    ]
    
    for i, result in enumerate(security_tests):
        if result == "ПРОПУЩЕН":
            print(f"⚠️  {test_names[i]}: ПРОПУЩЕН")
        elif result:
            print(f"✅ {test_names[i]}: ПРОЙДЕН")
            passed_security += 1
            total_security += 1
        else:
            print(f"❌ {test_names[i]}: ПРОВАЛЕН")
            total_security += 1
    
    security_rate = (passed_security / total_security * 100) if total_security > 0 else 0
    print(f"\n🔒 БЕЗОПАСНОСТЬ: {passed_security}/{total_security} тестов пройдено ({security_rate:.1f}%)")
    
    return security_rate >= 80

def main():
    """Основная функция дополнительного тестирования"""
    print("🔒 ДОПОЛНИТЕЛЬНОЕ ТЕСТИРОВАНИЕ БЕЗОПАСНОСТИ DELETE ENDPOINT КУРЬЕРОВ")
    print("=" * 80)
    
    success = test_operator_authorization()
    
    if success:
        print("\n🎉 ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ БЕЗОПАСНОСТИ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("\n⚠️ ОБНАРУЖЕНЫ ПРОБЛЕМЫ В ТЕСТАХ БЕЗОПАСНОСТИ")
    
    print(f"\n🕒 Дополнительное тестирование завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()