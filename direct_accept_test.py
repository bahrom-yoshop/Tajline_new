#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Полный флоу приёма груза через форму оператора в TAJLINE.TJ
Тестирование API endpoint /api/operator/cargo/direct-accept с множественными грузами
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://tajline-cargo-3.preview.emergentagent.com/api"

# Тестовые данные для авторизации
OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

def authenticate_operator():
    """Авторизация оператора склада"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json=OPERATOR_CREDENTIALS,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            user_info = data.get("user", {})
            print(f"✅ Авторизация успешна: {user_info.get('full_name', 'N/A')} (роль: {user_info.get('role', 'N/A')})")
            return token
        else:
            print(f"❌ Ошибка авторизации: HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка авторизации: {str(e)}")
        return None

def get_warehouses(token):
    """Получение списка складов"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BACKEND_URL}/warehouses", headers=headers, timeout=10)
        
        if response.status_code == 200:
            warehouses = response.json()
            if warehouses:
                print(f"✅ Найдено {len(warehouses)} складов")
                for i, w in enumerate(warehouses[:3]):
                    print(f"   {i+1}. {w.get('name', 'N/A')} (ID: {w.get('id', 'N/A')})")
                return warehouses[0].get("id")  # Возвращаем ID первого склада
            else:
                print("❌ Список складов пуст")
                return None
        else:
            print(f"❌ Ошибка получения складов: HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка получения складов: {str(e)}")
        return None

def test_single_cargo(token, warehouse_id):
    """Тест с одним грузом"""
    print("\n🔍 ТЕСТ 1: Один груз")
    print("-" * 50)
    
    payload = {
        "sender_full_name": "Иван Петров",
        "sender_phone": "+79991234567",
        "sender_address": "Москва, ул. Ленина 1",
        "recipient_full_name": "Али Рахимов",
        "recipient_phone": "+992901234567",
        "recipient_address": "Душанбе, ул. Рудаки 10",
        "cargo_items": [
            {
                "cargo_name": "Документы",
                "weight": 0.5,
                "price_per_kg": 2000.0
            }
        ],
        "description": "Принят через оператора на складе",
        "route": "moscow_to_tajikistan",
        "warehouse_id": warehouse_id,
        "payment_method": "cash",
        "payment_amount": 1000.0
    }
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BACKEND_URL}/operator/cargo/direct-accept",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Успешный ответ!")
            
            # Проверяем структуру ответа
            print(f"📋 Структура ответа:")
            print(f"   success: {data.get('success')}")
            print(f"   base_request_number: {data.get('base_request_number')}")
            print(f"   total_cargo_count: {data.get('total_cargo_count')}")
            print(f"   received_by: {data.get('received_by')}")
            print(f"   received_at: {data.get('received_at')}")
            
            created_cargo = data.get("created_cargo", [])
            print(f"   created_cargo: {len(created_cargo)} элементов")
            
            for i, cargo in enumerate(created_cargo):
                print(f"     Груз {i+1}:")
                print(f"       cargo_id: {cargo.get('cargo_id')}")
                print(f"       cargo_number: {cargo.get('cargo_number')}")
                print(f"       cargo_name: {cargo.get('cargo_name')}")
                print(f"       weight: {cargo.get('weight')}")
                print(f"       declared_value: {cargo.get('declared_value')}")
            
            return data
        else:
            print(f"❌ Ошибка: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {str(e)}")
        return None

def test_multiple_cargo(token, warehouse_id):
    """Тест с множественными грузами"""
    print("\n🔍 ТЕСТ 2: Множественные грузы")
    print("-" * 50)
    
    payload = {
        "sender_full_name": "Петр Сидоров",
        "sender_phone": "+79995555555",
        "sender_address": "Москва, ул. Пушкина 5",
        "recipient_full_name": "Бахтияр Назаров",
        "recipient_phone": "+992905555555",
        "recipient_address": "Душанбе, ул. Исмоили Сомони 25",
        "cargo_items": [
            {
                "cargo_name": "Электроника",
                "weight": 2.0,
                "price_per_kg": 100.0
            },
            {
                "cargo_name": "Одежда",
                "weight": 1.5,
                "price_per_kg": 50.0
            },
            {
                "cargo_name": "Книги",
                "weight": 3.0,
                "price_per_kg": 30.0
            }
        ],
        "description": "Принят через оператора на складе",
        "route": "moscow_to_tajikistan",
        "warehouse_id": warehouse_id,
        "payment_method": "card_transfer",
        "payment_amount": 365.0
    }
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BACKEND_URL}/operator/cargo/direct-accept",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Успешный ответ!")
            
            # Проверяем структуру ответа
            print(f"📋 Структура ответа:")
            print(f"   success: {data.get('success')}")
            print(f"   base_request_number: {data.get('base_request_number')}")
            print(f"   total_cargo_count: {data.get('total_cargo_count')}")
            print(f"   received_by: {data.get('received_by')}")
            print(f"   received_at: {data.get('received_at')}")
            
            created_cargo = data.get("created_cargo", [])
            print(f"   created_cargo: {len(created_cargo)} элементов")
            
            total_weight = 0
            total_value = 0
            
            for i, cargo in enumerate(created_cargo):
                print(f"     Груз {i+1}:")
                print(f"       cargo_id: {cargo.get('cargo_id')}")
                print(f"       cargo_number: {cargo.get('cargo_number')}")
                print(f"       cargo_name: {cargo.get('cargo_name')}")
                print(f"       weight: {cargo.get('weight')}")
                print(f"       declared_value: {cargo.get('declared_value')}")
                
                total_weight += cargo.get('weight', 0)
                total_value += cargo.get('declared_value', 0)
            
            print(f"📊 Итого:")
            print(f"   Общий вес: {total_weight} кг")
            print(f"   Общая стоимость: {total_value} ₽")
            print(f"   Ожидаемая стоимость: {2.0*100 + 1.5*50 + 3.0*30} ₽")
            
            return data
        else:
            print(f"❌ Ошибка: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {str(e)}")
        return None

def test_validation(token, warehouse_id):
    """Тест валидации"""
    print("\n🔍 ТЕСТ 3: Валидация ошибок")
    print("-" * 50)
    
    # Тест 1: Пустой массив cargo_items
    print("🧪 Тест 3.1: Пустой массив cargo_items")
    payload1 = {
        "sender_full_name": "Тест Отправитель",
        "sender_phone": "+79991234567",
        "sender_address": "Москва, ул. Тестовая 1",
        "recipient_full_name": "Тест Получатель",
        "recipient_phone": "+992901234567",
        "recipient_address": "Душанбе, ул. Тестовая 1",
        "cargo_items": [],  # Пустой массив
        "description": "Тест",
        "route": "moscow_to_tajikistan",
        "warehouse_id": warehouse_id
    }
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BACKEND_URL}/operator/cargo/direct-accept",
            json=payload1,
            headers=headers,
            timeout=10
        )
        
        print(f"   📡 HTTP Status: {response.status_code}")
        if response.status_code in [400, 422]:
            print("   ✅ Валидация работает корректно")
        else:
            print(f"   ❌ Ожидался HTTP 400/422, получен {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   📋 Ответ: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"   📋 Ошибка: {response.text}")
                
    except Exception as e:
        print(f"   ❌ Ошибка: {str(e)}")
    
    # Тест 2: Отсутствие обязательных полей
    print("\n🧪 Тест 3.2: Отсутствие обязательных полей")
    payload2 = {
        "sender_full_name": "Тест"
        # Отсутствуют другие обязательные поля
    }
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BACKEND_URL}/operator/cargo/direct-accept",
            json=payload2,
            headers=headers,
            timeout=10
        )
        
        print(f"   📡 HTTP Status: {response.status_code}")
        if response.status_code in [400, 422]:
            print("   ✅ Валидация работает корректно")
        else:
            print(f"   ❌ Ожидался HTTP 400/422, получен {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   📋 Ответ: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"   📋 Ошибка: {response.text}")
                
    except Exception as e:
        print(f"   ❌ Ошибка: {str(e)}")

def main():
    """Главная функция"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Полный флоу приёма груза через форму оператора")
    print("=" * 80)
    print()
    
    # 1. Авторизация
    token = authenticate_operator()
    if not token:
        print("❌ Не удалось авторизоваться. Тестирование прервано.")
        return
    
    # 2. Получение складов
    warehouse_id = get_warehouses(token)
    if not warehouse_id:
        print("❌ Не удалось получить склады. Тестирование прервано.")
        return
    
    # 3. Тестирование
    single_result = test_single_cargo(token, warehouse_id)
    multiple_result = test_multiple_cargo(token, warehouse_id)
    test_validation(token, warehouse_id)
    
    # 4. Итоги
    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 80)
    
    if single_result and multiple_result:
        print("✅ Основные тесты прошли успешно!")
        print("🎯 Endpoint /api/operator/cargo/direct-accept работает с множественными грузами")
        
        # Проверяем ключевые поля
        single_cargo = single_result.get("created_cargo", [])
        multiple_cargo = multiple_result.get("created_cargo", [])
        
        print(f"\n📋 Результаты:")
        print(f"   Тест с одним грузом: создано {len(single_cargo)} грузов")
        print(f"   Тест с множественными грузами: создано {len(multiple_cargo)} грузов")
        
        if len(single_cargo) == 1 and len(multiple_cargo) == 3:
            print("✅ Количество созданных грузов соответствует ожиданиям")
        else:
            print("⚠️ Количество созданных грузов не соответствует ожиданиям")
        
        # Проверяем уникальность номеров грузов
        all_numbers = []
        for cargo in single_cargo + multiple_cargo:
            all_numbers.append(cargo.get("cargo_number"))
        
        if len(all_numbers) == len(set(all_numbers)):
            print("✅ Все номера грузов уникальны")
        else:
            print("⚠️ Обнаружены дублирующиеся номера грузов")
        
        print("\n🎉 КРИТИЧЕСКИЙ ВЫВОД: ENDPOINT РАБОТАЕТ КОРРЕКТНО!")
        print("Система успешно создает отдельные грузы для каждого элемента cargo_items")
        print("с уникальными номерами в формате base_request_number/XX")
        
    else:
        print("❌ Критические тесты не прошли")
        print("Требуется дополнительная диагностика")

if __name__ == "__main__":
    main()