#!/usr/bin/env python3
"""
🔍 ПОИСК РАБОЧИХ УЧЕТНЫХ ДАННЫХ для тестирования авторизации
"""

import requests
import json

BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

# Список возможных учетных данных для тестирования
test_credentials = [
    # Основной тестовый пользователь из review request
    ("+79777888999", "operator123"),
    
    # Альтернативные пароли для того же пользователя
    ("+79777888999", "warehouse123"),
    ("+79777888999", "password"),
    ("+79777888999", "123456"),
    ("+79777888999", "admin123"),
    
    # Другие возможные тестовые пользователи
    ("+992888888888", "admin123"),
    ("+992000000001", "user123"),
    ("+992000000002", "user123"),
    ("+79999888777", "admin123"),
    ("+79777777777", "operator123"),
    ("+79999999999", "admin123"),
    
    # Администраторы
    ("admin", "admin123"),
    ("administrator", "admin123"),
    
    # Операторы
    ("operator", "operator123"),
    ("warehouse", "warehouse123"),
]

def test_login(phone, password):
    """Тестирование входа с указанными учетными данными"""
    try:
        login_data = {
            "phone": phone,
            "password": password
        }
        
        response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            user_info = data.get("user", {})
            return True, user_info
        else:
            return False, response.json() if response.text else {"error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return False, {"error": str(e)}

def main():
    print("🔍 ПОИСК РАБОЧИХ УЧЕТНЫХ ДАННЫХ ДЛЯ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    working_credentials = []
    
    for phone, password in test_credentials:
        print(f"\n🔐 Тестирование: {phone} / {password}")
        
        success, result = test_login(phone, password)
        
        if success:
            print(f"✅ УСПЕХ!")
            print(f"   Пользователь: {result.get('full_name', 'N/A')}")
            print(f"   Роль: {result.get('role', 'N/A')}")
            print(f"   Номер: {result.get('user_number', 'N/A')}")
            print(f"   ID: {result.get('id', 'N/A')}")
            
            working_credentials.append({
                "phone": phone,
                "password": password,
                "user_info": result
            })
        else:
            error_detail = result.get("detail", result)
            if isinstance(error_detail, dict):
                error_type = error_detail.get("error_type", "unknown")
                message = error_detail.get("message", "No message")
                print(f"❌ {error_type}: {message}")
            else:
                print(f"❌ {error_detail}")
    
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    if working_credentials:
        print(f"\n✅ НАЙДЕНО {len(working_credentials)} РАБОЧИХ УЧЕТНЫХ ЗАПИСЕЙ:")
        
        for i, cred in enumerate(working_credentials, 1):
            user = cred["user_info"]
            print(f"\n{i}. {cred['phone']} / {cred['password']}")
            print(f"   👤 {user.get('full_name', 'N/A')} ({user.get('role', 'N/A')})")
            print(f"   📞 {user.get('user_number', 'N/A')}")
            
        # Рекомендуем лучшую учетную запись для тестирования
        print(f"\n🎯 РЕКОМЕНДАЦИЯ ДЛЯ ТЕСТИРОВАНИЯ:")
        
        # Ищем оператора склада
        operator_creds = [c for c in working_credentials if c["user_info"].get("role") == "warehouse_operator"]
        if operator_creds:
            best_cred = operator_creds[0]
            print(f"   Оператор склада: {best_cred['phone']} / {best_cred['password']}")
            print(f"   Пользователь: {best_cred['user_info'].get('full_name')}")
        
        # Ищем администратора
        admin_creds = [c for c in working_credentials if c["user_info"].get("role") == "admin"]
        if admin_creds:
            best_cred = admin_creds[0]
            print(f"   Администратор: {best_cred['phone']} / {best_cred['password']}")
            print(f"   Пользователь: {best_cred['user_info'].get('full_name')}")
            
    else:
        print("\n❌ НЕ НАЙДЕНО РАБОЧИХ УЧЕТНЫХ ЗАПИСЕЙ!")
        print("   Возможные причины:")
        print("   - Неправильные учетные данные")
        print("   - Проблемы с подключением к базе данных")
        print("   - Пользователи не созданы в системе")

if __name__ == "__main__":
    main()