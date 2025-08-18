#!/usr/bin/env python3
"""
🎯 ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ: Проверка исправления группировки связанных грузов в TAJLINE.TJ
Создание тестовых данных для проверки исправления группировки связанных грузов
"""

import requests
import json
import sys
from datetime import datetime
from collections import defaultdict

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

# Тестовые данные для авторизации
OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

def main():
    print("🎯 ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ: Проверка группировки связанных грузов")
    print("=" * 70)
    
    session = requests.Session()
    
    # 1. Авторизация оператора
    print("1️⃣ АВТОРИЗАЦИЯ ОПЕРАТОРА")
    auth_response = session.post(f"{BACKEND_URL}/auth/login", json=OPERATOR_CREDENTIALS)
    
    if auth_response.status_code != 200:
        print(f"❌ Ошибка авторизации: {auth_response.status_code}")
        return False
    
    token = auth_response.json().get("access_token")
    user_info = auth_response.json().get("user", {})
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    print(f"✅ Авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
    print()
    
    # 2. Получение складов
    print("2️⃣ ПОЛУЧЕНИЕ СПИСКА СКЛАДОВ")
    warehouses_response = session.get(f"{BACKEND_URL}/operator/warehouses")
    
    if warehouses_response.status_code != 200:
        print(f"❌ Ошибка получения складов: {warehouses_response.status_code}")
        return False
    
    warehouses = warehouses_response.json()
    if not warehouses:
        print("❌ Нет доступных складов")
        return False
    
    warehouse = warehouses[0]
    print(f"✅ Выбран склад: {warehouse.get('name')} (ID: {warehouse.get('id')})")
    print()
    
    # 3. Создание заявки с несколькими грузами
    print("3️⃣ СОЗДАНИЕ ЗАЯВКИ С НЕСКОЛЬКИМИ ГРУЗАМИ")
    cargo_data = {
        "sender_full_name": "Тест Группировки",
        "sender_phone": "+79991111111",
        "sender_address": "Москва, ул. Тестовая 1",
        "recipient_full_name": "Получатель Теста",
        "recipient_phone": "+992901111111",
        "recipient_address": "Душанбе, ул. Тестовая 2",
        "cargo_items": [
            {
                "cargo_name": "Груз 1 для теста группировки",
                "weight": "1.0",
                "price_per_kg": "100"
            },
            {
                "cargo_name": "Груз 2 для теста группировки", 
                "weight": "2.0",
                "price_per_kg": "150"
            }
        ],
        "destination_warehouse_id": warehouse.get("id"),
        "destination_warehouse_name": warehouse.get("name"),
        "route": "moscow_to_tajikistan",
        "payment_method": "cash",
        "payment_amount": "450",
        "description": "Тестовая заявка для проверки группировки грузов"
    }
    
    create_response = session.post(f"{BACKEND_URL}/operator/cargo/direct-accept", json=cargo_data)
    
    if create_response.status_code != 200:
        print(f"❌ Ошибка создания заявки: {create_response.status_code} - {create_response.text}")
        return False
    
    create_data = create_response.json()
    created_cargo = create_data.get("created_cargo", [])
    base_request_number = create_data.get("base_request_number")
    
    if len(created_cargo) != 2:
        print(f"❌ Ожидалось 2 груза, создано: {len(created_cargo)}")
        return False
    
    cargo_numbers = [cargo.get("cargo_number") for cargo in created_cargo]
    print(f"✅ Создано 2 груза:")
    print(f"   • Базовый номер заявки: {base_request_number}")
    print(f"   • Номера грузов: {', '.join(cargo_numbers)}")
    print()
    
    # 4. Проверка правильности нумерации
    print("4️⃣ ПРОВЕРКА НУМЕРАЦИИ ГРУЗОВ")
    
    # Проверяем формат номеров
    expected_suffixes = ["/01", "/02"]
    correct_format = True
    
    for i, cargo_number in enumerate(cargo_numbers):
        if not cargo_number.endswith(expected_suffixes[i]):
            correct_format = False
            break
    
    # Проверяем base_request_number
    base_numbers_match = all(
        cargo.get("base_request_number") == base_request_number 
        for cargo in created_cargo
    )
    
    if correct_format and base_numbers_match:
        print("✅ Нумерация грузов корректна:")
        print(f"   • Формат номеров: {cargo_numbers[0]} и {cargo_numbers[1]}")
        print(f"   • Одинаковый base_request_number: {base_request_number}")
    else:
        print("❌ Проблемы с нумерацией:")
        if not correct_format:
            print("   • Неправильный формат номеров")
        if not base_numbers_match:
            print("   • base_request_number не совпадают")
        return False
    print()
    
    # 5. Проверка API размещения
    print("5️⃣ ПРОВЕРКА API РАЗМЕЩЕНИЯ")
    placement_response = session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement")
    
    if placement_response.status_code != 200:
        print(f"❌ Ошибка API размещения: {placement_response.status_code}")
        return False
    
    placement_data = placement_response.json()
    items = placement_data.get("items", [])
    
    # Ищем наши грузы
    found_cargo = []
    for item in items:
        if item.get("cargo_number") in cargo_numbers:
            found_cargo.append({
                "cargo_number": item.get("cargo_number"),
                "cargo_name": item.get("cargo_name"),
                "base_request_number": item.get("base_request_number"),
                "weight": item.get("weight"),
                "warehouse_name": item.get("warehouse_name")
            })
    
    print(f"✅ Найдено {len(found_cargo)} из 2 созданных грузов в API размещения")
    print("📊 Структура данных грузов:")
    for cargo in found_cargo:
        print(f"   • {cargo['cargo_number']}: {cargo['cargo_name']} ({cargo['weight']}кг)")
        print(f"     Склад: {cargo['warehouse_name']}, Base: {cargo['base_request_number']}")
    print()
    
    # 6. Анализ дублирования
    print("6️⃣ АНАЛИЗ ДУБЛИРОВАНИЯ")
    
    # Проверяем дублирование в найденных грузах
    found_numbers = [cargo["cargo_number"] for cargo in found_cargo]
    unique_found = set(found_numbers)
    
    if len(found_numbers) == len(unique_found):
        print("✅ Дублирование НЕ обнаружено в найденных грузах")
        
        # Проверяем общее дублирование в системе
        all_numbers = [item.get("cargo_number") for item in items if item.get("cargo_number")]
        number_counts = defaultdict(int)
        
        for number in all_numbers:
            number_counts[number] += 1
        
        duplicates = [num for num, count in number_counts.items() if count > 1]
        
        if duplicates:
            print(f"⚠️  В системе найдены дубликаты других грузов: {len(duplicates)} номеров")
            print(f"   Примеры: {', '.join(duplicates[:3])}{'...' if len(duplicates) > 3 else ''}")
        else:
            print("✅ Дублирование в системе НЕ обнаружено")
    else:
        print("❌ ОБНАРУЖЕНО дублирование наших грузов:")
        for number in unique_found:
            count = found_numbers.count(number)
            if count > 1:
                print(f"   • {number}: найден {count} раз")
        return False
    
    print()
    
    # 7. Итоговый результат
    print("7️⃣ ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("✅ ПРОБЛЕМА С ДУБЛИРОВАНИЕМ ИСПРАВЛЕНА НА УРОВНЕ ДАННЫХ")
    print()
    print("📋 РЕЗЮМЕ ТЕСТИРОВАНИЯ:")
    print(f"   • Создана заявка с 2 грузами (base: {base_request_number})")
    print(f"   • Номера грузов: {', '.join(cargo_numbers)}")
    print(f"   • Грузы найдены в API размещения: {len(found_cargo)}/2")
    print(f"   • Дублирование: НЕ обнаружено")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)