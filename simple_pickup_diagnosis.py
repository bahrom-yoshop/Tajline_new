#!/usr/bin/env python3
"""
Простая диагностика проблемы данных плейсхолдера в модальном окне заявки на забор груза TAJLINE.TJ
"""

import requests
import json

def test_pickup_request_100040():
    """Тестирование заявки 100040 на предмет данных плейсхолдера"""
    base_url = "https://tajline-manager-1.preview.emergentagent.com"
    
    print("🚚 ДИАГНОСТИКА ПРОБЛЕМЫ ДАННЫХ ПЛЕЙСХОЛДЕРА В МОДАЛЬНОМ ОКНЕ ЗАЯВКИ НА ЗАБОР ГРУЗА")
    print("="*80)
    
    # 1. Авторизация оператора
    print("\n🔐 ЭТАП 1: Авторизация оператора (+79777888999/warehouse123)")
    
    login_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=login_data)
    
    if response.status_code == 200:
        login_result = response.json()
        token = login_result.get('access_token')
        user = login_result.get('user', {})
        
        print(f"✅ Авторизация успешна: {user.get('full_name')}")
        print(f"👑 Роль: {user.get('role')}")
        print(f"📞 Телефон: {user.get('phone')}")
        print(f"🆔 Номер пользователя: {user.get('user_number')}")
    else:
        print(f"❌ Ошибка авторизации: {response.status_code}")
        return False
    
    # 2. Проверка заявки 100040
    print(f"\n📋 ЭТАП 2: Проверка endpoint GET /api/operator/pickup-requests/100040")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f"{base_url}/api/operator/pickup-requests/100040", headers=headers)
    
    if response.status_code == 200:
        request_data = response.json()
        print("✅ Endpoint работает")
        
        print(f"\n📄 ПОЛНЫЕ ДАННЫЕ ЗАЯВКИ 100040:")
        print(json.dumps(request_data, indent=2, ensure_ascii=False))
        
        # Анализ данных получателя
        print(f"\n🎯 АНАЛИЗ ДАННЫХ ПОЛУЧАТЕЛЯ:")
        recipient_data = request_data.get('recipient_data', {})
        
        if recipient_data:
            print("✅ recipient_data найдены:")
            
            recipient_fields = ['recipient_full_name', 'recipient_phone', 'recipient_address']
            filled_count = 0
            
            for field in recipient_fields:
                value = recipient_data.get(field, '')
                if value and str(value).strip() and str(value).strip() not in ['', 'null', 'None', 'undefined']:
                    filled_count += 1
                    print(f"  ✅ {field}: '{value}' (ЗАПОЛНЕНО)")
                else:
                    print(f"  ❌ {field}: '{value}' (ПУСТОЕ/ПЛЕЙСХОЛДЕР)")
            
            print(f"\n📊 РЕЗУЛЬТАТ: {filled_count}/{len(recipient_fields)} полей заполнено")
            
            if filled_count == len(recipient_fields):
                print("🎉 ВСЕ ДАННЫЕ ПОЛУЧАТЕЛЯ ЗАПОЛНЕНЫ - ПРОБЛЕМА НЕ В ДАННЫХ!")
                print("🔍 Проблема скорее всего в frontend коде отображения модального окна")
                print("💡 РЕКОМЕНДАЦИЯ: Проверить как frontend обрабатывает recipient_data")
            elif filled_count > 0:
                print("⚠️  ДАННЫЕ ПОЛУЧАТЕЛЯ ЗАПОЛНЕНЫ ЧАСТИЧНО")
                print("🔍 Некоторые поля пустые - это может быть причиной плейсхолдеров")
            else:
                print("❌ ВСЕ ДАННЫЕ ПОЛУЧАТЕЛЯ ПУСТЫЕ - ЭТО ПРИЧИНА ПЛЕЙСХОЛДЕРОВ!")
                print("🔍 Курьер не заполнил данные получателя или они не сохранились")
        else:
            print("❌ recipient_data ОТСУТСТВУЮТ - ЭТО ПРИЧИНА ПЛЕЙСХОЛДЕРОВ!")
            print("🔍 Endpoint не возвращает данные получателя")
        
        # Анализ данных груза
        print(f"\n🎯 АНАЛИЗ ДАННЫХ ГРУЗА:")
        cargo_info = request_data.get('cargo_info', {})
        
        if cargo_info:
            print("✅ cargo_info найдены:")
            for key, value in cargo_info.items():
                print(f"  {key}: {value}")
        else:
            print("❌ cargo_info отсутствуют")
        
        # Анализ данных отправителя
        print(f"\n🎯 АНАЛИЗ ДАННЫХ ОТПРАВИТЕЛЯ:")
        sender_data = request_data.get('sender_data', {})
        
        if sender_data:
            print("✅ sender_data найдены:")
            for key, value in sender_data.items():
                print(f"  {key}: {value}")
        else:
            print("❌ sender_data отсутствуют")
        
        return True
    else:
        print(f"❌ Ошибка получения заявки: {response.status_code}")
        try:
            error_data = response.json()
            print(f"📄 Ошибка: {error_data}")
        except:
            print(f"📄 Текст ошибки: {response.text}")
        return False

if __name__ == "__main__":
    test_pickup_request_100040()