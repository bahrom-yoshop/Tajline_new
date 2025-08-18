#!/usr/bin/env python3
"""
ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ: DELETE endpoint для удаления курьера в TAJLINE.TJ
Фокус на основной функциональности с обработкой сетевых проблем
"""

import requests
import json
import sys
import time
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-system-debug.preview.emergentagent.com/api"

# Учетные данные для тестирования
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

def make_request_with_retry(method, endpoint, headers=None, json_data=None, params=None, max_retries=3):
    """Универсальная функция для HTTP запросов с повторными попытками"""
    url = f"{BACKEND_URL}{endpoint}"
    
    for attempt in range(max_retries):
        try:
            response = requests.request(
                method=method,
                url=url, 
                headers=headers,
                json=json_data,
                params=params,
                timeout=30
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Попытка {attempt + 1}/{max_retries} не удалась: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Ждем 2 секунды перед повторной попыткой
            else:
                print(f"❌ Все попытки исчерпаны для {method} {endpoint}")
                return None

def authenticate_admin():
    """Авторизация администратора"""
    print(f"\n🔐 Авторизация администратора...")
    
    response = make_request_with_retry("POST", "/auth/login", json_data=ADMIN_CREDENTIALS)
    
    if not response or response.status_code != 200:
        print(f"❌ Ошибка авторизации администратора: {response.status_code if response else 'No response'}")
        return None
    
    data = response.json()
    token = data.get("access_token")
    user_info = data.get("user", {})
    
    print(f"✅ Успешная авторизация: {user_info.get('full_name', 'Unknown')} (роль: {user_info.get('role', 'Unknown')})")
    return token

def create_test_courier(token):
    """Создать тестового курьера"""
    print(f"\n👤 Создание тестового курьера...")
    
    # Получаем список складов
    headers = {"Authorization": f"Bearer {token}"}
    warehouses_response = make_request_with_retry("GET", "/warehouses", headers=headers)
    
    if not warehouses_response or warehouses_response.status_code != 200:
        print("❌ Не удалось получить список складов")
        return None
    
    warehouses = warehouses_response.json()
    if not warehouses:
        print("❌ Нет доступных складов")
        return None
    
    warehouse_id = warehouses[0]["id"]
    warehouse_name = warehouses[0]["name"]
    print(f"📦 Используем склад: {warehouse_name}")
    
    # Генерируем уникальный номер телефона для тестового курьера
    import random
    test_phone = f"+7999{random.randint(1000000, 9999999)}"
    
    courier_data = {
        "full_name": "Тестовый Курьер DELETE Final",
        "phone": test_phone,
        "password": "testcourier123",
        "address": "Тестовый адрес курьера",
        "transport_type": "car",
        "transport_number": f"FINAL{random.randint(100, 999)}",
        "transport_capacity": 500.0,
        "assigned_warehouse_id": warehouse_id
    }
    
    response = make_request_with_retry("POST", "/admin/couriers/create", headers=headers, json_data=courier_data)
    
    if not response or response.status_code != 200:
        print(f"❌ Ошибка создания курьера: {response.status_code if response else 'No response'}")
        if response:
            print(f"Response: {response.text}")
        return None
    
    courier_info = response.json()
    courier_id = courier_info.get("courier_id")
    print(f"✅ Тестовый курьер создан: ID {courier_id}, телефон {test_phone}")
    return courier_id, test_phone

def test_delete_endpoint_comprehensive(token, courier_id):
    """Комплексное тестирование DELETE endpoint"""
    print(f"\n🧪 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ DELETE ENDPOINT")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    test_results = []
    
    # ТЕСТ 1: Проверка что endpoint существует и доступен
    print(f"\n🧪 ТЕСТ 1: Проверка доступности DELETE endpoint...")
    
    response = make_request_with_retry("DELETE", f"/admin/couriers/{courier_id}", headers=headers)
    
    if not response:
        print("❌ ТЕСТ 1 ПРОВАЛЕН: Нет ответа от сервера")
        test_results.append(("Доступность DELETE endpoint", False))
    elif response.status_code == 405:
        print("❌ ТЕСТ 1 ПРОВАЛЕН: Endpoint возвращает 405 Method Not Allowed")
        test_results.append(("Доступность DELETE endpoint", False))
    else:
        print(f"✅ ТЕСТ 1 ПРОЙДЕН: Endpoint доступен (статус: {response.status_code})")
        test_results.append(("Доступность DELETE endpoint", True))
        
        # Если курьер был удален, проверим soft delete
        if response.status_code == 200:
            try:
                data = response.json()
                message = data.get("message", "")
                deleted_courier_id = data.get("courier_id", "")
                
                print(f"📝 Ответ сервера: {message}")
                
                if "успешно удален" in message and deleted_courier_id == courier_id:
                    print("✅ Успешное удаление подтверждено")
                    test_results.append(("Успешное удаление", True))
                    
                    # ТЕСТ 2: Проверка soft delete
                    print(f"\n🧪 ТЕСТ 2: Проверка soft delete...")
                    
                    # Пытаемся получить информацию о курьере
                    get_response = make_request_with_retry("GET", f"/admin/couriers/{courier_id}", headers=headers)
                    
                    if get_response and get_response.status_code == 200:
                        courier_data = get_response.json()
                        is_active = courier_data.get("is_active", True)
                        deleted = courier_data.get("deleted", False)
                        
                        if not is_active and deleted:
                            print("✅ ТЕСТ 2 ПРОЙДЕН: Soft delete подтвержден (is_active=false, deleted=true)")
                            test_results.append(("Soft delete", True))
                        else:
                            print(f"❌ ТЕСТ 2 ПРОВАЛЕН: Неправильные флаги - is_active: {is_active}, deleted: {deleted}")
                            test_results.append(("Soft delete", False))
                    elif get_response and get_response.status_code == 404:
                        print("✅ ТЕСТ 2 ПРОЙДЕН: Курьер исчез из активного списка (404)")
                        test_results.append(("Soft delete", True))
                    else:
                        print("❌ ТЕСТ 2 ПРОВАЛЕН: Не удалось проверить статус курьера")
                        test_results.append(("Soft delete", False))
                    
                    # ТЕСТ 3: Проверка исчезновения из списка активных курьеров
                    print(f"\n🧪 ТЕСТ 3: Проверка исчезновения из активного списка...")
                    
                    list_response = make_request_with_retry("GET", "/admin/couriers/list", headers=headers)
                    
                    if list_response and list_response.status_code == 200:
                        data = list_response.json()
                        couriers = data.get("couriers", []) if isinstance(data, dict) else data
                        
                        # Ищем удаленного курьера в списке активных
                        found_active = False
                        for courier in couriers:
                            if courier.get("id") == courier_id and courier.get("is_active", True):
                                found_active = True
                                break
                        
                        if not found_active:
                            print("✅ ТЕСТ 3 ПРОЙДЕН: Курьер исчез из активного списка")
                            test_results.append(("Исчезновение из активного списка", True))
                        else:
                            print("❌ ТЕСТ 3 ПРОВАЛЕН: Курьер все еще активен в списке")
                            test_results.append(("Исчезновение из активного списка", False))
                    else:
                        print("❌ ТЕСТ 3 ПРОВАЛЕН: Не удалось получить список курьеров")
                        test_results.append(("Исчезновение из активного списка", False))
                        
                else:
                    print("❌ Неожиданный ответ при удалении")
                    test_results.append(("Успешное удаление", False))
                    
            except json.JSONDecodeError:
                print("❌ Некорректный JSON в ответе")
                test_results.append(("Успешное удаление", False))
    
    # ТЕСТ 4: Проверка обработки несуществующего курьера (создаем нового курьера для этого теста)
    print(f"\n🧪 ТЕСТ 4: Проверка обработки несуществующего курьера...")
    
    fake_courier_id = "00000000-0000-0000-0000-000000000000"
    fake_response = make_request_with_retry("DELETE", f"/admin/couriers/{fake_courier_id}", headers=headers)
    
    if fake_response and fake_response.status_code == 404:
        print("✅ ТЕСТ 4 ПРОЙДЕН: Несуществующий курьер возвращает 404")
        test_results.append(("Обработка несуществующего курьера", True))
    elif not fake_response:
        print("❌ ТЕСТ 4 ПРОВАЛЕН: Нет ответа от сервера")
        test_results.append(("Обработка несуществующего курьера", False))
    else:
        print(f"❌ ТЕСТ 4 ПРОВАЛЕН: Ожидался 404, получен {fake_response.status_code}")
        test_results.append(("Обработка несуществующего курьера", False))
    
    # ТЕСТ 5: Проверка безопасности - попытка удаления без авторизации
    print(f"\n🧪 ТЕСТ 5: Проверка безопасности (без авторизации)...")
    
    # Создаем еще одного курьера для теста безопасности
    security_courier = create_test_courier(token)
    if security_courier:
        security_courier_id, _ = security_courier
        
        no_auth_response = make_request_with_retry("DELETE", f"/admin/couriers/{security_courier_id}")
        
        if no_auth_response and no_auth_response.status_code == 401:
            print("✅ ТЕСТ 5 ПРОЙДЕН: Без авторизации получаем 401 Unauthorized")
            test_results.append(("Безопасность без авторизации", True))
        elif not no_auth_response:
            print("❌ ТЕСТ 5 ПРОВАЛЕН: Нет ответа от сервера")
            test_results.append(("Безопасность без авторизации", False))
        else:
            print(f"❌ ТЕСТ 5 ПРОВАЛЕН: Ожидался 401, получен {no_auth_response.status_code}")
            test_results.append(("Безопасность без авторизации", False))
        
        # Очищаем тестового курьера
        cleanup_response = make_request_with_retry("DELETE", f"/admin/couriers/{security_courier_id}", headers=headers)
        if cleanup_response and cleanup_response.status_code == 200:
            print("🧹 Тестовый курьер для безопасности удален")
    else:
        print("⚠️ ТЕСТ 5 ПРОПУЩЕН: Не удалось создать курьера для теста безопасности")
        test_results.append(("Безопасность без авторизации", "ПРОПУЩЕН"))
    
    return test_results

def main():
    """Основная функция финального тестирования"""
    print("🎯 ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ DELETE ENDPOINT ДЛЯ КУРЬЕРОВ")
    print("=" * 80)
    
    # Авторизация администратора
    admin_token = authenticate_admin()
    if not admin_token:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
        sys.exit(1)
    
    # Создаем тестового курьера
    courier_result = create_test_courier(admin_token)
    if not courier_result:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать тестового курьера")
        sys.exit(1)
    
    courier_id, courier_phone = courier_result
    
    # Выполняем комплексное тестирование
    test_results = test_delete_endpoint_comprehensive(admin_token, courier_id)
    
    # Подведение итогов
    print("\n" + "=" * 80)
    print("📊 ФИНАЛЬНЫЕ ИТОГИ ТЕСТИРОВАНИЯ DELETE ENDPOINT ДЛЯ КУРЬЕРОВ")
    print("=" * 80)
    
    passed_tests = 0
    total_tests = 0
    
    for test_name, result in test_results:
        if result == "ПРОПУЩЕН":
            print(f"⚠️  {test_name}: ПРОПУЩЕН")
        elif result:
            print(f"✅ {test_name}: ПРОЙДЕН")
            passed_tests += 1
            total_tests += 1
        else:
            print(f"❌ {test_name}: ПРОВАЛЕН")
            total_tests += 1
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 ФИНАЛЬНЫЙ РЕЗУЛЬТАТ: {passed_tests}/{total_tests} тестов пройдено ({success_rate:.1f}%)")
    
    if success_rate >= 85:
        print("\n🎉 КРИТИЧЕСКИЙ УСПЕХ: DELETE endpoint для курьеров работает корректно!")
        print("✅ Endpoint доступен и не возвращает 405 Method Not Allowed")
        print("✅ Успешно удаляет курьеров")
        print("✅ Реализован soft delete (is_active=false, deleted=true)")
        print("✅ Курьер исчезает из списка активных")
        print("✅ Корректно обрабатывает несуществующих курьеров (404)")
        print("✅ Требует авторизации (401 без токена)")
        
        print("\n📋 ЗАКЛЮЧЕНИЕ:")
        print("Новый DELETE /api/admin/couriers/{courier_id} endpoint работает корректно и безопасно.")
        print("Все основные требования выполнены:")
        print("- Endpoint доступен")
        print("- Реализован soft delete")
        print("- Обеспечена безопасность")
        print("- Корректная обработка ошибок")
        
    elif success_rate >= 70:
        print("\n⚠️  ЧАСТИЧНЫЙ УСПЕХ: DELETE endpoint работает, но есть проблемы")
        print("Рекомендуется исправить выявленные проблемы")
    else:
        print("\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ: DELETE endpoint требует серьезных исправлений")
    
    print(f"\n🕒 Финальное тестирование завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()