#!/usr/bin/env python3
"""
КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема "Груз не найден" при массовом удалении в системе TAJLINE.TJ
Тестирование всех возможных endpoints для массового удаления грузов
"""

import requests
import json
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://freight-hub-6.preview.emergentagent.com/api"

def test_bulk_deletion_diagnosis():
    """Диагностика проблемы массового удаления грузов"""
    print("🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема 'Груз не найден' при массовом удалении")
    print("=" * 80)
    
    # Инициализация переменных
    test_cargo_ids = []
    test_cargo_numbers = []
    headers = {}
    
    # Шаг 1: Авторизация оператора склада
    print("\n1️⃣ АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА (+79777888999/warehouse123)")
    login_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
        print(f"Статус авторизации: {response.status_code}")
        
        if response.status_code == 200:
            auth_result = response.json()
            token = auth_result.get("access_token")
            user_info = auth_result.get("user")
            print(f"✅ Успешная авторизация: {user_info.get('full_name')} (роль: {user_info.get('role')})")
            
            headers = {"Authorization": f"Bearer {token}"}
        else:
            print(f"❌ Ошибка авторизации: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Исключение при авторизации: {e}")
        return
    
    # Шаг 2: Получение реальных ID грузов
    print("\n2️⃣ ПОЛУЧЕНИЕ РЕАЛЬНЫХ ID ГРУЗОВ ИЗ /api/operator/cargo/available-for-placement")
    
    try:
        response = requests.get(f"{BACKEND_URL}/operator/cargo/available-for-placement", headers=headers)
        print(f"Статус получения грузов: {response.status_code}")
        
        if response.status_code == 200:
            cargo_data = response.json()
            available_cargo = cargo_data.get("items", [])
            print(f"✅ Найдено {len(available_cargo)} грузов для размещения")
            
            if len(available_cargo) >= 2:
                # Берем первые 2 груза для безопасного тестирования
                test_cargo_ids = [cargo["id"] for cargo in available_cargo[:2]]
                test_cargo_numbers = [cargo["cargo_number"] for cargo in available_cargo[:2]]
                print(f"🎯 Тестовые грузы: {test_cargo_numbers} (IDs: {test_cargo_ids})")
            else:
                print("⚠️ Недостаточно грузов для тестирования массового удаления")
                return
                
        else:
            print(f"❌ Ошибка получения грузов: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Исключение при получении грузов: {e}")
        return
    
    # Шаг 3: Тестирование основного endpoint DELETE /api/admin/cargo/bulk
    print("\n3️⃣ ТЕСТИРОВАНИЕ ENDPOINT DELETE /api/admin/cargo/bulk")
    
    bulk_data_1 = {"ids": test_cargo_ids}
    
    try:
        response = requests.delete(f"{BACKEND_URL}/admin/cargo/bulk", json=bulk_data_1, headers=headers)
        print(f"Статус DELETE /api/admin/cargo/bulk: {response.status_code}")
        print(f"Ответ: {response.text}")
        
        if response.status_code == 200:
            print("✅ Endpoint /api/admin/cargo/bulk работает!")
            result = response.json()
            print(f"Результат: {result}")
            return  # Успешно найден рабочий endpoint
        else:
            print(f"❌ Endpoint /api/admin/cargo/bulk не работает: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Исключение при тестировании /api/admin/cargo/bulk: {e}")
    
    # Шаг 4: Тестирование альтернативного формата данных
    print("\n4️⃣ ТЕСТИРОВАНИЕ АЛЬТЕРНАТИВНОГО ФОРМАТА ДАННЫХ {{cargo_ids: [...]}}")
    
    bulk_data_2 = {"cargo_ids": test_cargo_ids}
    
    try:
        response = requests.delete(f"{BACKEND_URL}/admin/cargo/bulk", json=bulk_data_2, headers=headers)
        print(f"Статус с cargo_ids: {response.status_code}")
        print(f"Ответ: {response.text}")
        
        if response.status_code == 200:
            print("✅ Формат {{cargo_ids: [...]}} работает!")
            result = response.json()
            print(f"Результат: {result}")
            return
        else:
            print(f"❌ Формат {{cargo_ids: [...]}} не работает")
            
    except Exception as e:
        print(f"❌ Исключение при тестировании cargo_ids формата: {e}")
    
    # Шаг 5: Тестирование старого endpoint DELETE /api/operator/cargo/bulk-remove-from-placement
    print("\n5️⃣ ТЕСТИРОВАНИЕ СТАРОГО ENDPOINT DELETE /api/operator/cargo/bulk-remove-from-placement")
    
    bulk_data_3 = {"cargo_ids": test_cargo_ids}
    
    try:
        response = requests.delete(f"{BACKEND_URL}/operator/cargo/bulk-remove-from-placement", json=bulk_data_3, headers=headers)
        print(f"Статус bulk-remove-from-placement: {response.status_code}")
        print(f"Ответ: {response.text}")
        
        if response.status_code == 200:
            print("✅ Старый endpoint bulk-remove-from-placement работает!")
            result = response.json()
            print(f"Результат: {result}")
            return
        else:
            print(f"❌ Старый endpoint не работает: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Исключение при тестировании старого endpoint: {e}")
    
    # Шаг 6: Тестирование DELETE /api/admin/cargo/bulk-delete
    print("\n6️⃣ ТЕСТИРОВАНИЕ ENDPOINT DELETE /api/admin/cargo/bulk-delete")
    
    try:
        response = requests.delete(f"{BACKEND_URL}/admin/cargo/bulk-delete", json=bulk_data_2, headers=headers)
        print(f"Статус bulk-delete: {response.status_code}")
        print(f"Ответ: {response.text}")
        
        if response.status_code == 200:
            print("✅ Endpoint bulk-delete работает!")
            result = response.json()
            print(f"Результат: {result}")
            return
        else:
            print(f"❌ Endpoint bulk-delete не работает: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Исключение при тестировании bulk-delete: {e}")
    
    # Шаг 7: Тестирование POST /api/admin/cargo/bulk с method DELETE
    print("\n7️⃣ ТЕСТИРОВАНИЕ POST /api/admin/cargo/bulk С METHOD DELETE")
    
    bulk_data_4 = {
        "method": "DELETE",
        "cargo_ids": test_cargo_ids
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/admin/cargo/bulk", json=bulk_data_4, headers=headers)
        print(f"Статус POST с method DELETE: {response.status_code}")
        print(f"Ответ: {response.text}")
        
        if response.status_code == 200:
            print("✅ POST с method DELETE работает!")
            result = response.json()
            print(f"Результат: {result}")
            return
        else:
            print(f"❌ POST с method DELETE не работает: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Исключение при тестировании POST с method DELETE: {e}")
    
    # Шаг 8: Проверка доступных endpoints через OPTIONS
    print("\n8️⃣ ПРОВЕРКА ДОСТУПНЫХ ENDPOINTS ЧЕРЕЗ OPTIONS")
    
    endpoints_to_check = [
        "/admin/cargo/bulk",
        "/admin/cargo/bulk-delete", 
        "/operator/cargo/bulk-remove-from-placement",
        "/admin/cargo/delete-multiple"
    ]
    
    for endpoint in endpoints_to_check:
        try:
            response = requests.options(f"{BACKEND_URL}{endpoint}", headers=headers)
            print(f"OPTIONS {endpoint}: {response.status_code}")
            if response.status_code == 200:
                allowed_methods = response.headers.get("Allow", "")
                print(f"  Разрешенные методы: {allowed_methods}")
        except Exception as e:
            print(f"  Ошибка OPTIONS {endpoint}: {e}")
    
    # Шаг 9: Тестирование единичного удаления для сравнения
    print("\n9️⃣ ТЕСТИРОВАНИЕ ЕДИНИЧНОГО УДАЛЕНИЯ ДЛЯ СРАВНЕНИЯ")
    
    if test_cargo_ids:
        single_cargo_id = test_cargo_ids[0]
        
        try:
            response = requests.delete(f"{BACKEND_URL}/admin/cargo/{single_cargo_id}", headers=headers)
            print(f"Статус единичного удаления: {response.status_code}")
            print(f"Ответ: {response.text}")
            
            if response.status_code == 200:
                print("✅ Единичное удаление работает!")
            else:
                print(f"❌ Единичное удаление не работает: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Исключение при единичном удалении: {e}")
    
    print("\n" + "=" * 80)
    print("🔍 ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("❌ НИ ОДИН ИЗ ENDPOINTS ДЛЯ МАССОВОГО УДАЛЕНИЯ НЕ РАБОТАЕТ")
    print("📋 РЕКОМЕНДАЦИИ:")
    print("1. Проверить реализацию endpoint'ов в backend/server.py")
    print("2. Убедиться в правильности структуры данных")
    print("3. Проверить права доступа для роли warehouse_operator")
    print("4. Рассмотреть использование единичного удаления в цикле как временное решение")

if __name__ == "__main__":
    test_bulk_deletion_diagnosis()