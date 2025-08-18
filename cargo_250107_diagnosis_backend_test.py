#!/usr/bin/env python3
"""
ТОЧЕЧНАЯ ДИАГНОСТИКА ПО ЗАЯВКЕ 250107
Выполняет диагностику груза по номеру 250107 согласно review request
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"

def test_cargo_250107_diagnosis():
    """Точечная диагностика по заявке 250107"""
    print("🎯 НАЧИНАЕМ ТОЧЕЧНУЮ ДИАГНОСТИКУ ПО ЗАЯВКЕ 250107")
    print("=" * 60)
    
    # Шаг 1: Авторизация администратора
    print("\n1️⃣ АВТОРИЗАЦИЯ АДМИНИСТРАТОРА")
    admin_login_data = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    try:
        login_response = requests.post(f"{BACKEND_URL}/auth/login", json=admin_login_data)
        if login_response.status_code != 200:
            print(f"❌ Ошибка авторизации администратора: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
        
        admin_token = login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("✅ Администратор авторизован успешно")
        
    except Exception as e:
        print(f"❌ Ошибка при авторизации администратора: {e}")
        return False
    
    # Шаг 2: Попытка авторизации оператора Москва-1
    print("\n2️⃣ АВТОРИЗАЦИЯ ОПЕРАТОРА МОСКВА-1")
    operator_login_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    operator_headers = None
    try:
        operator_login_response = requests.post(f"{BACKEND_URL}/auth/login", json=operator_login_data)
        if operator_login_response.status_code == 200:
            operator_token = operator_login_response.json()["access_token"]
            operator_headers = {"Authorization": f"Bearer {operator_token}"}
            print("✅ Оператор Москва-1 авторизован успешно")
        else:
            print(f"⚠️ Оператор Москва-1 недоступен: {operator_login_response.status_code}")
            print("Продолжаем с администратором")
    except Exception as e:
        print(f"⚠️ Ошибка при авторизации оператора: {e}")
        print("Продолжаем с администратором")
    
    # Шаг 3: Выполнение диагностики под администратором
    print("\n3️⃣ ДИАГНОСТИКА ГРУЗА 250107 ПОД АДМИНИСТРАТОРОМ")
    try:
        debug_response = requests.get(
            f"{BACKEND_URL}/debug/find-cargo-by-number/250107",
            headers=admin_headers
        )
        
        if debug_response.status_code != 200:
            print(f"❌ Ошибка диагностики: {debug_response.status_code}")
            print(f"Response: {debug_response.text}")
            return False
        
        admin_diagnosis = debug_response.json()
        print("✅ Диагностика под администратором выполнена успешно")
        
        # Анализ результатов администратора
        print("\n📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ ПОД АДМИНИСТРАТОРОМ:")
        print(f"Запрос: {admin_diagnosis['summary']['query']}")
        print(f"Всего найдено: {admin_diagnosis['summary']['total_found']}")
        print(f"По коллекциям: {admin_diagnosis['summary']['by_collection']}")
        print(f"Статусы скрытия: {admin_diagnosis['summary']['hidden_status_counts']}")
        
        if admin_diagnosis['data']:
            print("\n📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О НАЙДЕННЫХ ГРУЗАХ:")
            for i, cargo in enumerate(admin_diagnosis['data'], 1):
                print(f"\n--- ГРУЗ #{i} ---")
                print(f"Коллекция: {cargo['collection']}")
                print(f"ID: {cargo['id']}")
                print(f"Номер груза: {cargo['cargo_number']}")
                print(f"Базовый номер заявки: {cargo['base_request_number']}")
                print(f"warehouse_id: {cargo['warehouse_id']}")
                print(f"warehouse_name: {cargo['warehouse_name']}")
                print(f"destination_warehouse_id: {cargo['destination_warehouse_id']}")
                print(f"destination_warehouse_name: {cargo['destination_warehouse_name']}")
                print(f"status: {cargo['status']}")
                print(f"processing_status: {cargo['processing_status']}")
                print(f"warehouse_location: {cargo['warehouse_location']}")
                print(f"block/shelf/cell: {cargo['block_number']}/{cargo['shelf_number']}/{cargo['cell_number']}")
                print(f"hidden_reason: {cargo['hidden_reason']}")
                print(f"created_at: {cargo['created_at']}")
                print(f"updated_at: {cargo['updated_at']}")
        
    except Exception as e:
        print(f"❌ Ошибка при диагностике под администратором: {e}")
        return False
    
    # Шаг 4: Выполнение диагностики под оператором (если доступен)
    operator_diagnosis = None
    if operator_headers:
        print("\n4️⃣ ДИАГНОСТИКА ГРУЗА 250107 ПОД ОПЕРАТОРОМ МОСКВА-1")
        try:
            operator_debug_response = requests.get(
                f"{BACKEND_URL}/debug/find-cargo-by-number/250107",
                headers=operator_headers
            )
            
            if operator_debug_response.status_code == 200:
                operator_diagnosis = operator_debug_response.json()
                print("✅ Диагностика под оператором выполнена успешно")
                
                # Сравнение результатов
                print("\n🔍 СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
                admin_count = admin_diagnosis['summary']['total_found']
                operator_count = operator_diagnosis['summary']['total_found']
                
                if admin_count == operator_count:
                    print(f"✅ Количество найденных грузов одинаково: {admin_count}")
                else:
                    print(f"⚠️ Различие в количестве найденных грузов:")
                    print(f"   Администратор: {admin_count}")
                    print(f"   Оператор: {operator_count}")
                
            else:
                print(f"❌ Ошибка диагностики под оператором: {operator_debug_response.status_code}")
                print(f"Response: {operator_debug_response.text}")
                
        except Exception as e:
            print(f"❌ Ошибка при диагностике под оператором: {e}")
    
    # Шаг 5: Анализ причин скрытия
    print("\n5️⃣ АНАЛИЗ ПРИЧИН СКРЫТИЯ В 'РАЗМЕЩЕНИИ'")
    
    diagnosis_data = admin_diagnosis  # Используем данные администратора как основные
    
    if not diagnosis_data['data']:
        print("❌ ГРУЗ 250107 НЕ НАЙДЕН В СИСТЕМЕ")
        print("Возможные причины:")
        print("- Груз с таким номером не существует")
        print("- Номер груза указан неверно")
        print("- Груз был удален из системы")
        
        # Проверим варианты с суффиксами
        print("\n🔍 ПРОВЕРКА ВАРИАНТОВ С СУФФИКСАМИ (250107/01, 250107/02):")
        for suffix in ["01", "02", "03"]:
            try:
                suffix_response = requests.get(
                    f"{BACKEND_URL}/debug/find-cargo-by-number/250107/{suffix}",
                    headers=admin_headers
                )
                if suffix_response.status_code == 200:
                    suffix_data = suffix_response.json()
                    if suffix_data['data']:
                        print(f"✅ Найден груз с номером 250107/{suffix}")
                    else:
                        print(f"❌ Груз 250107/{suffix} не найден")
                else:
                    print(f"❌ Ошибка поиска 250107/{suffix}: {suffix_response.status_code}")
            except Exception as e:
                print(f"❌ Ошибка при поиске 250107/{suffix}: {e}")
        
        return True  # Завершаем успешно, даже если груз не найден
    
    # Анализ найденных грузов
    print(f"✅ НАЙДЕНО ГРУЗОВ: {len(diagnosis_data['data'])}")
    
    for i, cargo in enumerate(diagnosis_data['data'], 1):
        print(f"\n--- АНАЛИЗ ГРУЗА #{i} ---")
        print(f"Номер груза: {cargo['cargo_number']}")
        print(f"Коллекция: {cargo['collection']}")
        
        # Анализ причин скрытия
        hidden_reason = cargo['hidden_reason']
        
        if hidden_reason == "no_warehouse_id":
            print("🔴 ПРИЧИНА СКРЫТИЯ: no_warehouse_id")
            print("   ➤ warehouse_id пуст, из-за этого груз не видно в 'Размещении'")
            print("   ➤ РЕКОМЕНДАЦИЯ: Назначить груз на склад")
            
        elif hidden_reason and "status=" in hidden_reason:
            status = cargo['status']
            print(f"🟡 ПРИЧИНА СКРЫТИЯ: статус = {status}")
            if status in ["placed_in_warehouse", "removed_from_placement"]:
                print("   ➤ Груз имеет статус, который скрывает его из списка размещения")
                print("   ➤ РЕКОМЕНДАЦИЯ: Изменить статус груза для отображения в размещении")
            
        elif hidden_reason == "has_cell_coordinates_or_location":
            print("🟢 ГРУЗ УЖЕ РАЗМЕЩЕН")
            print("   ➤ Груз имеет координаты ячейки или местоположение на складе")
            print(f"   ➤ warehouse_location: {cargo['warehouse_location']}")
            print(f"   ➤ Координаты: Блок {cargo['block_number']}, Полка {cargo['shelf_number']}, Ячейка {cargo['cell_number']}")
            
        else:
            print("✅ ГРУЗ ДОЛЖЕН БЫТЬ ВИДЕН В РАЗМЕЩЕНИИ")
            print("   ➤ Нет очевидных причин для скрытия")
        
        # Дополнительная информация
        print(f"\nДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:")
        print(f"   warehouse_id: {cargo['warehouse_id']} ({cargo['warehouse_name']})")
        print(f"   destination_warehouse_id: {cargo['destination_warehouse_id']} ({cargo['destination_warehouse_name']})")
        print(f"   status: {cargo['status']}")
        print(f"   processing_status: {cargo['processing_status']}")
    
    # Шаг 6: Краткий итог
    print("\n6️⃣ КРАТКИЙ ИТОГ ДИАГНОСТИКИ")
    print("=" * 50)
    
    summary = diagnosis_data['summary']
    print(f"Запрос: {summary['query']}")
    print(f"Найдено грузов: {summary['total_found']}")
    print(f"В коллекции 'cargo': {summary['by_collection']['cargo']}")
    print(f"В коллекции 'operator_cargo': {summary['by_collection']['operator_cargo']}")
    
    if summary['hidden_status_counts']:
        print("\nПричины скрытия:")
        for reason, count in summary['hidden_status_counts'].items():
            if reason == "no_warehouse_id":
                print(f"   🔴 {reason}: {count} груз(ов) - warehouse_id пуст")
            elif "status=" in reason:
                print(f"   🟡 {reason}: {count} груз(ов) - проблемный статус")
            elif reason == "has_cell_coordinates_or_location":
                print(f"   🟢 {reason}: {count} груз(ов) - уже размещен")
            elif reason == "visible_candidate":
                print(f"   ✅ {reason}: {count} груз(ов) - должен быть виден")
            else:
                print(f"   ❓ {reason}: {count} груз(ов)")
    
    print("\n✅ ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО")
    return True

def main():
    """Главная функция"""
    print("🚀 ЗАПУСК ТОЧЕЧНОЙ ДИАГНОСТИКИ ПО ЗАЯВКЕ 250107")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_cargo_250107_diagnosis()
    
    if success:
        print("\n🎉 ВСЕ ТЕСТЫ ДИАГНОСТИКИ ПРОЙДЕНЫ УСПЕШНО!")
        sys.exit(0)
    else:
        print("\n❌ ДИАГНОСТИКА ЗАВЕРШИЛАСЬ С ОШИБКАМИ!")
        sys.exit(1)

if __name__ == "__main__":
    main()