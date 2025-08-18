#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Диагностика и исправление заявки 250101
Проверка и исправление проблем с грузом 250101 согласно review request
"""

import requests
import json
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

def test_cargo_250101_diagnosis():
    """Диагностика и исправление заявки 250101"""
    
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Диагностика и исправление заявки 250101")
    print("=" * 80)
    
    # Шаг 1: Авторизация администратора
    print("\n1️⃣ АВТОРИЗАЦИЯ АДМИНИСТРАТОРА")
    print("-" * 40)
    
    admin_login_data = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    try:
        login_response = requests.post(f"{BACKEND_URL}/auth/login", json=admin_login_data)
        print(f"Статус авторизации: {login_response.status_code}")
        
        if login_response.status_code == 200:
            admin_token = login_response.json().get("access_token")
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            print("✅ Авторизация администратора успешна")
        else:
            print(f"❌ Ошибка авторизации: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при авторизации: {e}")
        return False
    
    # Шаг 2: Вызов GET /api/debug/find-cargo-by-number/250101
    print("\n2️⃣ ДИАГНОСТИКА ГРУЗА 250101")
    print("-" * 40)
    
    try:
        debug_response = requests.get(f"{BACKEND_URL}/debug/find-cargo-by-number/250101", headers=admin_headers)
        print(f"Статус диагностики: {debug_response.status_code}")
        
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            print("✅ Груз 250101 найден!")
            print(f"📋 Данные диагностики:")
            
            # Извлекаем данные из правильной структуры
            cargo_data = debug_data.get("data", [])
            summary = debug_data.get("summary", {})
            
            print(f"   - Всего найдено: {summary.get('total_found', 0)}")
            print(f"   - По коллекциям: {summary.get('by_collection', {})}")
            print(f"   - Статусы скрытия: {summary.get('hidden_status_counts', {})}")
            
            # Берем первый найденный груз для анализа
            if cargo_data:
                first_cargo = cargo_data[0]
                collections = [item.get("collection") for item in cargo_data]
                warehouse_id = first_cargo.get("warehouse_id")
                destination_warehouse_id = first_cargo.get("destination_warehouse_id")
                status = first_cargo.get("status")
                hidden_reason = first_cargo.get("hidden_reason")
                
                print(f"   - Коллекции: {collections}")
                print(f"   - warehouse_id: {warehouse_id}")
                print(f"   - destination_warehouse_id: {destination_warehouse_id}")
                print(f"   - Статус: {status}")
                print(f"   - hidden_reason: {hidden_reason}")
            else:
                collections = []
                warehouse_id = None
                destination_warehouse_id = None
                status = None
                hidden_reason = None
                print("   - Данные груза не найдены")
            
        elif debug_response.status_code == 404:
            print("❌ Груз 250101 не найден в системе")
            return False
        else:
            print(f"❌ Ошибка диагностики: {debug_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при диагностике: {e}")
        return False
    
    # Шаг 3: Проверка городов назначения
    print("\n3️⃣ ПРОВЕРКА ГОРОДА 'ЯВАН'")
    print("-" * 40)
    
    yavan_warehouse_id = None
    
    try:
        cities_response = requests.get(f"{BACKEND_URL}/destinations/cities", headers=admin_headers)
        print(f"Статус получения городов: {cities_response.status_code}")
        
        if cities_response.status_code == 200:
            cities_response_data = cities_response.json()
            cities_data = cities_response_data.get("items", [])
            print(f"✅ Получено городов: {len(cities_data)}")
            print(f"📋 Структура данных: {cities_data[:3]}...")  # Показываем первые 3 для краткости
            
            # Ищем город "Яван"
            for city in cities_data:
                city_name = city.get("city", "").lower()
                if "яван" in city_name:
                    yavan_warehouse_id = city.get("warehouse_id")
                    print(f"✅ Город 'Яван' найден! warehouse_id: {yavan_warehouse_id}")
                    break
            
            if not yavan_warehouse_id:
                print("⚠️ Город 'Яван' не найден в списке городов")
                print("📋 Доступные города:")
                for city in cities_data[:10]:  # Показываем первые 10
                    print(f"   - {city.get('city', 'N/A')}")
                    
        else:
            print(f"❌ Ошибка получения городов: {cities_response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при получении городов: {e}")
        print(f"📋 Тип данных: {type(cities_data) if 'cities_data' in locals() else 'Неизвестно'}")
    
    # Шаг 4: Исправление warehouse_id если пустой
    print("\n4️⃣ ИСПРАВЛЕНИЕ WAREHOUSE_ID")
    print("-" * 40)
    
    moscow_warehouse_id = "d0a8362d-b4d3-4947-b335-28c94658a021"
    needs_warehouse_fix = not warehouse_id
    needs_destination_fix = yavan_warehouse_id and not destination_warehouse_id
    
    if needs_warehouse_fix or needs_destination_fix:
        patch_data = {}
        
        if needs_warehouse_fix:
            patch_data["current_warehouse_id"] = moscow_warehouse_id
            print(f"🔧 Устанавливаем current_warehouse_id: {moscow_warehouse_id}")
        
        if needs_destination_fix:
            patch_data["destination_warehouse_id"] = yavan_warehouse_id
            print(f"🔧 Устанавливаем destination_warehouse_id: {yavan_warehouse_id}")
        
        try:
            patch_response = requests.patch(
                f"{BACKEND_URL}/admin/cargo/by-number/250101/set-warehouses",
                json=patch_data,
                headers=admin_headers
            )
            print(f"Статус исправления: {patch_response.status_code}")
            
            if patch_response.status_code == 200:
                print("✅ Склады успешно обновлены!")
                print(f"📋 Ответ: {patch_response.json()}")
            else:
                print(f"❌ Ошибка обновления складов: {patch_response.text}")
                
        except Exception as e:
            print(f"❌ Ошибка при обновлении складов: {e}")
    else:
        print("ℹ️ Исправления не требуются:")
        print(f"   - warehouse_id уже установлен: {warehouse_id}")
        print(f"   - destination_warehouse_id: {destination_warehouse_id}")
    
    # Шаг 5: Повторная проверка груза 250101
    print("\n5️⃣ ПОВТОРНАЯ ДИАГНОСТИКА ГРУЗА 250101")
    print("-" * 40)
    
    try:
        final_debug_response = requests.get(f"{BACKEND_URL}/debug/find-cargo-by-number/250101", headers=admin_headers)
        print(f"Статус финальной диагностики: {final_debug_response.status_code}")
        
        if final_debug_response.status_code == 200:
            final_debug_data = final_debug_response.json()
            print("✅ Финальная диагностика завершена!")
            
            # Проверяем изменения
            final_cargo_data = final_debug_data.get("data", [])
            final_summary = final_debug_data.get("summary", {})
            
            print(f"📋 Финальная диагностика:")
            print(f"   - Всего найдено: {final_summary.get('total_found', 0)}")
            print(f"   - По коллекциям: {final_summary.get('by_collection', {})}")
            print(f"   - Статусы скрытия: {final_summary.get('hidden_status_counts', {})}")
            
            if final_cargo_data:
                final_first_cargo = final_cargo_data[0]
                final_warehouse_id = final_first_cargo.get("warehouse_id")
                final_destination_warehouse_id = final_first_cargo.get("destination_warehouse_id")
                final_status = final_first_cargo.get("status")
                final_hidden_reason = final_first_cargo.get("hidden_reason")
                
                print(f"📋 Финальные данные груза:")
                print(f"   - warehouse_id: {final_warehouse_id}")
                print(f"   - destination_warehouse_id: {final_destination_warehouse_id}")
                print(f"   - Статус: {final_status}")
                print(f"   - hidden_reason: {final_hidden_reason}")
                
                # Проверяем результат исправления
                if final_warehouse_id and not final_hidden_reason:
                    print("🎉 УСПЕХ! Груз 250101 теперь виден для размещения!")
                    print("   ✅ warehouse_id установлен")
                    print("   ✅ hidden_reason исчез")
                else:
                    print("⚠️ Проблемы остались:")
                    if not final_warehouse_id:
                        print("   ❌ warehouse_id все еще пустой")
                    if final_hidden_reason:
                        print(f"   ❌ hidden_reason: {final_hidden_reason}")
            else:
                print("❌ Финальные данные груза не найдены")
                final_warehouse_id = None
                final_destination_warehouse_id = None
                final_status = None
                final_hidden_reason = None
                    
        else:
            print(f"❌ Ошибка финальной диагностики: {final_debug_response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при финальной диагностике: {e}")
    
    # Шаг 6: Итоговый отчет
    print("\n6️⃣ ИТОГОВЫЙ ОТЧЕТ")
    print("-" * 40)
    
    print("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ И ИСПРАВЛЕНИЯ ЗАЯВКИ 250101:")
    print(f"   🔍 Груз найден в коллекциях: {collections}")
    print(f"   🏢 Исходный warehouse_id: {warehouse_id}")
    print(f"   🎯 Исходный destination_warehouse_id: {destination_warehouse_id}")
    print(f"   📍 Город 'Яван' найден: {'Да' if yavan_warehouse_id else 'Нет'}")
    if yavan_warehouse_id:
        print(f"   🏪 warehouse_id для 'Яван': {yavan_warehouse_id}")
    
    if needs_warehouse_fix or needs_destination_fix:
        print(f"   🔧 Исправления применены:")
        if needs_warehouse_fix:
            print(f"      - Установлен warehouse_id: {moscow_warehouse_id}")
        if needs_destination_fix:
            print(f"      - Установлен destination_warehouse_id: {yavan_warehouse_id}")
    
    print(f"   🏁 Финальный статус: Груз {'виден' if final_warehouse_id and not final_hidden_reason else 'скрыт'} для размещения")
    
    return True

if __name__ == "__main__":
    success = test_cargo_250101_diagnosis()
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ОШИБКАМИ!")