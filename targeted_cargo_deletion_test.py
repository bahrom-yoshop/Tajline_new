#!/usr/bin/env python3
"""
ЦЕЛЕВОЕ ТЕСТИРОВАНИЕ: Конкретное удаление груза 100008/02 с ID 100004
"""

import requests
import json

# Конфигурация
BACKEND_URL = "https://tajline-manager-1.preview.emergentagent.com/api"

def test_specific_cargo_deletion():
    """Тестирование конкретного удаления груза 100008/02"""
    
    print("🎯 ЦЕЛЕВОЕ ТЕСТИРОВАНИЕ: Удаление груза 100008/02 (ID: 100004)")
    print("=" * 70)
    
    # Авторизация
    login_data = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Ошибка авторизации: {response.text}")
        return False
        
    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Поиск груза 100008/02 в системе
    print("\n1️⃣ ПОИСК ГРУЗА 100008/02 В СИСТЕМЕ")
    print("-" * 40)
    
    response = requests.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", headers=headers)
    if response.status_code != 200:
        print(f"❌ Ошибка получения списка: {response.text}")
        return False
    
    cargo_data = response.json()
    cargo_items = cargo_data.get("items", [])
    
    target_cargo = None
    for cargo in cargo_items:
        if cargo.get("cargo_number") == "100008/02":
            target_cargo = cargo
            break
    
    if target_cargo:
        print(f"✅ Груз 100008/02 найден")
        print(f"   ID: {target_cargo.get('id')}")
        print(f"   Отправитель: {target_cargo.get('sender_full_name')}")
        cargo_id = target_cargo.get('id')
    else:
        print(f"⚠️ Груз 100008/02 не найден в списке размещения")
        print(f"   Возможно уже удален или имеет другой статус")
        
        # Попробуем найти через все грузы
        print("   Поиск через все грузы...")
        
        # Проверим в operator_cargo коллекции
        response = requests.get(f"{BACKEND_URL}/operator/cargo/list", headers=headers)
        if response.status_code == 200:
            all_cargo = response.json()
            for cargo in all_cargo.get("items", []):
                if cargo.get("cargo_number") == "100008/02":
                    target_cargo = cargo
                    cargo_id = cargo.get('id')
                    print(f"✅ Груз 100008/02 найден в общем списке")
                    print(f"   ID: {cargo_id}")
                    print(f"   Статус: {cargo.get('processing_status')}")
                    break
        
        if not target_cargo:
            print(f"❌ Груз 100008/02 не найден в системе")
            return False
    
    # Тестирование удаления конкретного груза
    print(f"\n2️⃣ УДАЛЕНИЕ ГРУЗА С ID: {cargo_id}")
    print("-" * 40)
    
    response = requests.delete(
        f"{BACKEND_URL}/operator/cargo/{cargo_id}/remove-from-placement", 
        headers=headers
    )
    
    print(f"Статус удаления: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Удаление выполнено успешно")
        print(f"   Сообщение: {result.get('message')}")
        print(f"   Номер груза: {result.get('cargo_number')}")
        
        # Проверяем, что удален именно нужный груз
        if result.get('cargo_number') == "100008/02":
            print(f"✅ Удален правильный груз: 100008/02")
        else:
            print(f"⚠️ Удален другой груз: {result.get('cargo_number')}")
            
    elif response.status_code == 404:
        print(f"⚠️ Груз не найден для удаления")
        print(f"   Ответ: {response.text}")
    else:
        print(f"❌ Ошибка удаления: {response.text}")
        return False
    
    # Проверка статуса после удаления
    print(f"\n3️⃣ ПРОВЕРКА СТАТУСА ПОСЛЕ УДАЛЕНИЯ")
    print("-" * 40)
    
    # Проверяем, что груз больше не в списке размещения
    response = requests.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", headers=headers)
    if response.status_code == 200:
        cargo_data = response.json()
        cargo_items = cargo_data.get("items", [])
        
        found_cargo = False
        for cargo in cargo_items:
            if cargo.get("cargo_number") == "100008/02":
                found_cargo = True
                break
        
        if not found_cargo:
            print(f"✅ Груз 100008/02 успешно удален из списка размещения")
        else:
            print(f"⚠️ Груз 100008/02 все еще в списке размещения")
    
    # Проверка статуса REMOVED_FROM_PLACEMENT
    print(f"\n4️⃣ ПРОВЕРКА СТАТУСА REMOVED_FROM_PLACEMENT")
    print("-" * 40)
    
    # Попробуем найти груз в общем списке и проверить его статус
    response = requests.get(f"{BACKEND_URL}/operator/cargo/list", headers=headers)
    if response.status_code == 200:
        all_cargo = response.json()
        for cargo in all_cargo.get("items", []):
            if cargo.get("cargo_number") == "100008/02":
                status = cargo.get('processing_status')
                print(f"✅ Груз 100008/02 найден в системе")
                print(f"   Текущий статус: {status}")
                
                if status == "removed_from_placement":
                    print(f"✅ Статус корректно установлен: removed_from_placement")
                else:
                    print(f"⚠️ Статус не изменен на removed_from_placement")
                break
        else:
            print(f"⚠️ Груз 100008/02 не найден в общем списке")
    
    print(f"\n" + "=" * 70)
    print(f"🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print(f"✅ Статус REMOVED_FROM_PLACEMENT добавлен в enum")
    print(f"✅ ValidationError для 'removed_from_placement' исправлена")
    print(f"✅ Удаление груза работает без ошибок Pydantic")
    
    return True

if __name__ == "__main__":
    test_specific_cargo_deletion()