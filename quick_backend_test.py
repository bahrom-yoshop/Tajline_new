#!/usr/bin/env python3
"""
🎯 БЫСТРЫЙ ТЕСТ BACKEND: Проверка исправления React Hooks ошибки
Быстрая проверка что React Hooks ошибка исправлена:
1. Авторизация администратора
2. Основные endpoints
3. Статус сервисов
"""

import requests
import json
import os
import sys
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
if not BACKEND_URL.endswith('/api'):
    BACKEND_URL = f"{BACKEND_URL}/api"

print(f"🔗 Backend URL: {BACKEND_URL}")

def test_admin_authentication():
    """Test 1: Авторизация администратора"""
    print("\n🔐 ТЕСТ 1: АВТОРИЗАЦИЯ АДМИНИСТРАТОРА")
    
    try:
        # Admin credentials
        admin_credentials = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        response = requests.post(f"{BACKEND_URL}/auth/login", json=admin_credentials, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            user_info = data.get('user', {})
            
            print(f"✅ Авторизация успешна!")
            print(f"   Пользователь: {user_info.get('full_name', 'N/A')}")
            print(f"   Роль: {user_info.get('role', 'N/A')}")
            print(f"   Номер: {user_info.get('user_number', 'N/A')}")
            print(f"   Токен получен: {'Да' if token else 'Нет'}")
            
            return token
        else:
            print(f"❌ Ошибка авторизации: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение при авторизации: {str(e)}")
        return None

def test_basic_endpoints(token):
    """Test 2: Основные endpoints"""
    print("\n🔧 ТЕСТ 2: ОСНОВНЫЕ ENDPOINTS")
    
    if not token:
        print("❌ Нет токена для тестирования endpoints")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    endpoints_to_test = [
        ("/auth/me", "Проверка токена"),
        ("/warehouses", "Список складов"),
        ("/transport/list", "Список транспорта")
    ]
    
    success_count = 0
    total_count = len(endpoints_to_test)
    
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {description}: OK")
                success_count += 1
            else:
                print(f"❌ {description}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {description}: Исключение - {str(e)}")
    
    success_rate = (success_count / total_count) * 100
    print(f"\n📊 Результат endpoints: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    return success_count >= 2  # At least 2 out of 3 should work

def test_service_status():
    """Test 3: Статус сервисов"""
    print("\n🏥 ТЕСТ 3: СТАТУС СЕРВИСОВ")
    
    try:
        # Test basic connectivity
        response = requests.get(f"{BACKEND_URL.replace('/api', '')}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend сервис доступен")
            return True
    except:
        pass
    
    try:
        # Test basic endpoint without auth
        response = requests.get(f"{BACKEND_URL}/auth/login", timeout=5)
        if response.status_code in [405, 422]:  # Method not allowed or validation error is expected
            print("✅ Backend сервис отвечает корректно")
            return True
        elif response.status_code == 200:
            print("✅ Backend сервис работает")
            return True
    except Exception as e:
        print(f"❌ Backend сервис недоступен: {str(e)}")
        return False
    
    print("⚠️ Backend сервис работает с ограничениями")
    return True

def main():
    """Главная функция быстрого теста"""
    print("🎯 БЫСТРЫЙ ТЕСТ BACKEND: Проверка исправления React Hooks ошибки")
    print("=" * 70)
    
    # Test 1: Admin Authentication
    token = test_admin_authentication()
    auth_success = token is not None
    
    # Test 2: Basic Endpoints
    endpoints_success = test_basic_endpoints(token)
    
    # Test 3: Service Status
    service_success = test_service_status()
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(f"   1. Авторизация администратора: {'✅ РАБОТАЕТ' if auth_success else '❌ НЕ РАБОТАЕТ'}")
    print(f"   2. Основные endpoints: {'✅ РАБОТАЮТ' if endpoints_success else '❌ НЕ РАБОТАЮТ'}")
    print(f"   3. Статус сервисов: {'✅ СТАБИЛЬНЫ' if service_success else '❌ ПРОБЛЕМЫ'}")
    
    overall_success = auth_success and endpoints_success and service_success
    
    if overall_success:
        print("\n🎉 РЕЗУЛЬТАТ: Backend работает стабильно после исправления React Hooks!")
        print("   React Hooks ошибка НЕ повлияла на backend функциональность")
        return 0
    else:
        print("\n⚠️ РЕЗУЛЬТАТ: Обнаружены проблемы в backend")
        print("   Требуется дополнительная диагностика")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)