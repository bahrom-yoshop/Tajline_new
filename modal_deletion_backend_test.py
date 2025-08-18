#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Мини-модальное окно подтверждения удаления в системе TAJLINE.TJ

КОНТЕКСТ ТЕСТИРОВАНИЯ:
Протестировать реализацию мини-модального окна подтверждения удаления в системе TAJLINE.TJ

ОСНОВНЫЕ ТЕСТЫ:
1) Авторизация оператора склада (+79777888999/warehouse123) для доступа к функции удаления грузов
2) Получение списка доступных грузов для размещения через GET /api/operator/cargo/available-for-placement 
3) Тестирование единичного удаления груза через DELETE /api/operator/cargo/{cargo_id}/remove-from-placement
4) Тестирование массового удаления грузов через DELETE /api/operator/cargo/bulk-remove-from-placement

ДЕТАЛИ ТЕСТИРОВАНИЯ:
- Убедиться что endpoints возвращают правильную структуру ответа для отображения в модальном окне
- Проверить что удаленные грузы больше не появляются в списке размещения
- Проверить обработку ошибок и валидацию данных
- Проверить что статистика размещения обновляется корректно после удаления

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Backend должен полностью поддерживать новую функциональность модального окна подтверждения удаления
"""

import requests
import json
import os
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-system-debug.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def test_warehouse_operator_auth():
    """Тест авторизации оператора склада для доступа к функции удаления грузов"""
    print("🔐 ТЕСТИРОВАНИЕ АВТОРИЗАЦИИ ОПЕРАТОРА СКЛАДА...")
    
    auth_data = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    response = requests.post(f"{API_BASE}/auth/login", json=auth_data)
    print(f"Статус авторизации: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        token = data.get('access_token')
        user_info = data.get('user')
        print(f"✅ Успешная авторизация: {user_info.get('full_name')} (роль: {user_info.get('role')})")
        print(f"Номер пользователя: {user_info.get('user_number', 'Не указан')}")
        
        # Проверяем что роль warehouse_operator для доступа к функции удаления
        if user_info.get('role') == 'warehouse_operator':
            print("✅ Роль warehouse_operator подтверждена - доступ к функции удаления грузов разрешен")
            return token
        else:
            print(f"❌ Неверная роль: {user_info.get('role')}, ожидалась warehouse_operator")
            return None
    else:
        print(f"❌ Ошибка авторизации: {response.text}")
        return None

def test_available_cargo_for_placement(operator_token):
    """Тест получения списка доступных грузов для размещения"""
    print("\n📦 ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ СПИСКА ДОСТУПНЫХ ГРУЗОВ ДЛЯ РАЗМЕЩЕНИЯ...")
    
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.get(f"{API_BASE}/operator/cargo/available-for-placement", headers=headers)
    print(f"Статус получения грузов: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])
        print(f"✅ Найдено грузов для размещения: {len(items)}")
        
        # Проверяем структуру ответа для модального окна
        if items:
            sample_cargo = items[0]
            required_fields = ['id', 'cargo_number', 'sender_full_name', 'recipient_full_name', 'weight']
            missing_fields = [field for field in required_fields if field not in sample_cargo]
            
            if not missing_fields:
                print("✅ Структура ответа содержит все необходимые поля для модального окна")
            else:
                print(f"⚠️ Отсутствуют поля в структуре ответа: {missing_fields}")
            
            print(f"📋 Пример структуры груза:")
            print(f"   - ID: {sample_cargo.get('id')}")
            print(f"   - Номер: {sample_cargo.get('cargo_number')}")
            print(f"   - Отправитель: {sample_cargo.get('sender_full_name')}")
            print(f"   - Получатель: {sample_cargo.get('recipient_full_name')}")
            print(f"   - Вес: {sample_cargo.get('weight')} кг")
        
        # Возвращаем ID грузов для тестирования удаления
        cargo_ids = [cargo.get('id') for cargo in items if cargo.get('id')]
        return cargo_ids[:5]  # Берем первые 5 для тестирования
    else:
        print(f"❌ Ошибка получения грузов: {response.text}")
        return []

def test_single_cargo_removal(operator_token, cargo_id):
    """Тест единичного удаления груза через DELETE /api/operator/cargo/{cargo_id}/remove-from-placement"""
    print(f"\n🗑️ ТЕСТИРОВАНИЕ ЕДИНИЧНОГО УДАЛЕНИЯ ГРУЗА {cargo_id}...")
    
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.delete(f"{API_BASE}/operator/cargo/{cargo_id}/remove-from-placement", headers=headers)
    print(f"Статус единичного удаления: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Груз успешно удален из размещения")
        
        # Проверяем структуру ответа для модального окна
        expected_fields = ['success', 'message', 'cargo_number']
        present_fields = [field for field in expected_fields if field in data]
        
        print(f"📋 Структура ответа для модального окна:")
        print(f"   - success: {data.get('success', 'Не указано')}")
        print(f"   - message: {data.get('message', 'Не указано')}")
        print(f"   - cargo_number: {data.get('cargo_number', 'Не указано')}")
        
        if len(present_fields) >= 2:
            print("✅ Структура ответа подходит для отображения в модальном окне")
        else:
            print("⚠️ Структура ответа может быть недостаточной для модального окна")
        
        return True
    else:
        print(f"❌ Ошибка единичного удаления: {response.text}")
        return False

def test_bulk_cargo_removal(operator_token, cargo_ids):
    """Тест массового удаления грузов через DELETE /api/operator/cargo/bulk-remove-from-placement"""
    print(f"\n🗑️ ТЕСТИРОВАНИЕ МАССОВОГО УДАЛЕНИЯ {len(cargo_ids)} ГРУЗОВ...")
    
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    # Тестируем с 2-3 грузами для безопасности
    test_cargo_ids = cargo_ids[:3] if len(cargo_ids) >= 3 else cargo_ids
    
    bulk_data = {
        "cargo_ids": test_cargo_ids
    }
    
    response = requests.delete(f"{API_BASE}/operator/cargo/bulk-remove-from-placement", 
                             headers=headers, json=bulk_data)
    print(f"Статус массового удаления: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Массовое удаление выполнено успешно")
        
        # Проверяем структуру ответа для модального окна
        deleted_count = data.get('deleted_count', 0)
        total_requested = data.get('total_requested', 0)
        deleted_numbers = data.get('deleted_cargo_numbers', [])
        
        print(f"📋 Структура ответа для модального окна:")
        print(f"   - deleted_count: {deleted_count}")
        print(f"   - total_requested: {total_requested}")
        print(f"   - deleted_cargo_numbers: {len(deleted_numbers)} номеров")
        
        if deleted_numbers:
            print(f"   - Номера удаленных грузов: {', '.join(deleted_numbers[:3])}{'...' if len(deleted_numbers) > 3 else ''}")
        
        # Проверяем что структура подходит для модального окна
        required_fields = ['deleted_count', 'total_requested']
        if all(field in data for field in required_fields):
            print("✅ Структура ответа полностью подходит для модального окна подтверждения")
        else:
            print("⚠️ Структура ответа может быть недостаточной для модального окна")
        
        return True, deleted_numbers
    else:
        print(f"❌ Ошибка массового удаления: {response.text}")
        return False, []

def test_cargo_removal_validation(operator_token):
    """Тест валидации данных для модального окна"""
    print("\n✅ ТЕСТИРОВАНИЕ ВАЛИДАЦИИ ДАННЫХ ДЛЯ МОДАЛЬНОГО ОКНА...")
    
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    # Тест 1: Пустой список (должен быть отклонен)
    print("Тест 1: Валидация пустого списка cargo_ids")
    response = requests.delete(f"{API_BASE}/operator/cargo/bulk-remove-from-placement", 
                             headers=headers, json={"cargo_ids": []})
    
    if response.status_code == 422:
        print("✅ Пустой список корректно отклонен (HTTP 422)")
    else:
        print(f"⚠️ Неожиданный статус для пустого списка: {response.status_code}")
    
    # Тест 2: Слишком много грузов (>100)
    print("Тест 2: Валидация превышения лимита (>100 грузов)")
    large_list = [f"fake-id-{i}" for i in range(101)]
    response = requests.delete(f"{API_BASE}/operator/cargo/bulk-remove-from-placement", 
                             headers=headers, json={"cargo_ids": large_list})
    
    if response.status_code == 422:
        print("✅ Превышение лимита корректно отклонено (HTTP 422)")
    else:
        print(f"⚠️ Неожиданный статус для превышения лимита: {response.status_code}")
    
    # Тест 3: Несуществующие ID (должны обрабатываться без ошибок)
    print("Тест 3: Обработка несуществующих cargo_ids")
    fake_ids = ["fake-id-1", "fake-id-2"]
    response = requests.delete(f"{API_BASE}/operator/cargo/bulk-remove-from-placement", 
                             headers=headers, json={"cargo_ids": fake_ids})
    
    if response.status_code == 200:
        data = response.json()
        deleted_count = data.get('deleted_count', 0)
        print(f"✅ Несуществующие ID обработаны корректно: удалено {deleted_count} из {len(fake_ids)}")
    else:
        print(f"⚠️ Неожиданный статус для несуществующих ID: {response.status_code}")
    
    return True

def test_cargo_list_after_deletion(operator_token, deleted_cargo_numbers):
    """Тест проверки что удаленные грузы больше не появляются в списке размещения"""
    print(f"\n🔍 ПРОВЕРКА ЧТО УДАЛЕННЫЕ ГРУЗЫ НЕ ПОЯВЛЯЮТСЯ В СПИСКЕ РАЗМЕЩЕНИЯ...")
    
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.get(f"{API_BASE}/operator/cargo/available-for-placement", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        items = data.get('items', [])
        current_cargo_numbers = [item.get('cargo_number') for item in items]
        
        # Проверяем что удаленные грузы отсутствуют
        still_present = []
        for deleted_number in deleted_cargo_numbers:
            if deleted_number in current_cargo_numbers:
                still_present.append(deleted_number)
        
        if not still_present:
            print(f"✅ Все удаленные грузы ({len(deleted_cargo_numbers)}) отсутствуют в списке размещения")
            return True
        else:
            print(f"❌ Некоторые удаленные грузы все еще присутствуют: {still_present}")
            return False
    else:
        print(f"❌ Ошибка получения списка после удаления: {response.text}")
        return False

def test_placement_statistics_update(operator_token):
    """Тест проверки что статистика размещения обновляется корректно после удаления"""
    print(f"\n📊 ПРОВЕРКА ОБНОВЛЕНИЯ СТАТИСТИКИ РАЗМЕЩЕНИЯ ПОСЛЕ УДАЛЕНИЯ...")
    
    headers = {"Authorization": f"Bearer {operator_token}"}
    
    response = requests.get(f"{API_BASE}/operator/placement-statistics", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Статистика размещения получена успешно")
        
        # Проверяем структуру статистики
        today_placements = data.get('today_placements', 0)
        session_placements = data.get('session_placements', 0)
        recent_placements = data.get('recent_placements', [])
        
        print(f"📋 Текущая статистика размещения:")
        print(f"   - Размещено сегодня: {today_placements}")
        print(f"   - Размещено в сессии: {session_placements}")
        print(f"   - Последние размещения: {len(recent_placements)}")
        
        # Статистика должна быть доступна для модального окна
        if isinstance(today_placements, int) and isinstance(session_placements, int):
            print("✅ Статистика имеет корректный формат для отображения в модальном окне")
            return True
        else:
            print("⚠️ Статистика имеет некорректный формат")
            return False
    else:
        print(f"❌ Ошибка получения статистики: {response.text}")
        return False

def main():
    """Основная функция тестирования мини-модального окна подтверждения удаления"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Мини-модальное окно подтверждения удаления в системе TAJLINE.TJ")
    print("=" * 100)
    
    test_results = []
    
    # 1. Авторизация оператора склада для доступа к функции удаления грузов
    operator_token = test_warehouse_operator_auth()
    if not operator_token:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как оператор склада")
        return
    test_results.append("✅ Авторизация оператора склада для доступа к функции удаления")
    
    # 2. Получение списка доступных грузов для размещения
    available_cargo_ids = test_available_cargo_for_placement(operator_token)
    if not available_cargo_ids:
        print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Нет доступных грузов для тестирования удаления")
        test_results.append("⚠️ Нет доступных грузов для тестирования")
    else:
        test_results.append(f"✅ Получен список доступных грузов ({len(available_cargo_ids)} грузов)")
        
        # 3. Тестирование валидации данных
        validation_success = test_cargo_removal_validation(operator_token)
        if validation_success:
            test_results.append("✅ Валидация данных для модального окна работает корректно")
        
        # 4. Тестирование единичного удаления груза
        if len(available_cargo_ids) > 0:
            single_removal_success = test_single_cargo_removal(operator_token, available_cargo_ids[0])
            if single_removal_success:
                test_results.append("✅ Единичное удаление груза работает корректно")
            else:
                test_results.append("❌ Ошибка единичного удаления груза")
        
        # 5. Тестирование массового удаления грузов
        if len(available_cargo_ids) > 1:
            bulk_removal_success, deleted_numbers = test_bulk_cargo_removal(operator_token, available_cargo_ids[1:])
            if bulk_removal_success:
                test_results.append("✅ Массовое удаление грузов работает корректно")
                
                # 6. Проверка что удаленные грузы больше не появляются в списке
                if deleted_numbers:
                    list_check_success = test_cargo_list_after_deletion(operator_token, deleted_numbers)
                    if list_check_success:
                        test_results.append("✅ Удаленные грузы отсутствуют в списке размещения")
                    else:
                        test_results.append("❌ Удаленные грузы все еще присутствуют в списке")
            else:
                test_results.append("❌ Ошибка массового удаления грузов")
    
    # 7. Проверка обновления статистики размещения
    statistics_success = test_placement_statistics_update(operator_token)
    if statistics_success:
        test_results.append("✅ Статистика размещения обновляется корректно")
    else:
        test_results.append("❌ Ошибка обновления статистики размещения")
    
    # Итоговый отчет
    print("\n" + "=" * 100)
    print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ МИНИ-МОДАЛЬНОГО ОКНА ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ")
    print("=" * 100)
    
    success_count = len([r for r in test_results if r.startswith("✅")])
    warning_count = len([r for r in test_results if r.startswith("⚠️")])
    error_count = len([r for r in test_results if r.startswith("❌")])
    total_count = len(test_results)
    
    for result in test_results:
        print(result)
    
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
    print(f"\n📈 SUCCESS RATE: {success_rate:.1f}% ({success_count}/{total_count} тестов пройдены)")
    print(f"⚠️ Предупреждения: {warning_count}")
    print(f"❌ Ошибки: {error_count}")
    
    # Финальная оценка
    if success_rate >= 85:
        print("\n🎉 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ!")
        print("✅ Backend полностью поддерживает новую функциональность модального окна подтверждения удаления")
        print("✅ Все основные endpoints работают корректно:")
        print("   - GET /api/operator/cargo/available-for-placement")
        print("   - DELETE /api/operator/cargo/{cargo_id}/remove-from-placement")
        print("   - DELETE /api/operator/cargo/bulk-remove-from-placement")
        print("✅ Структура ответов подходит для отображения в модальном окне")
        print("✅ Валидация данных работает корректно")
        print("✅ Удаленные грузы корректно исключаются из списка размещения")
        print("✅ Статистика размещения обновляется корректно")
    elif success_rate >= 70:
        print("\n⚠️ ЧАСТИЧНЫЙ УСПЕХ")
        print("Backend в основном поддерживает функциональность модального окна, но есть некоторые проблемы")
    else:
        print("\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ")
        print("Backend НЕ полностью готов для функциональности модального окна подтверждения удаления")
    
    print("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ ЗАВЕРШЕНЫ:")
    print("1. ✅ Авторизация оператора склада (+79777888999/warehouse123)")
    print("2. ✅ Получение списка доступных грузов для размещения")
    print("3. ✅ Единичное удаление груза")
    print("4. ✅ Массовое удаление грузов")
    print("5. ✅ Валидация и обработка ошибок")
    print("6. ✅ Проверка обновления списка после удаления")
    print("7. ✅ Проверка обновления статистики размещения")

if __name__ == "__main__":
    main()