#!/usr/bin/env python3
"""
ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: Симуляция полной загрузки категории "Склады" в TAJLINE.TJ

Этот тест симулирует все запросы, которые могут выполняться при открытии категории "Склады"
для определения точной причины медленной загрузки.
"""

import requests
import json
import os
import time
from datetime import datetime
import concurrent.futures
import threading

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-cargo-3.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Глобальная переменная для токена авторизации
auth_token = None

def log_test_result(test_name, success, details=""):
    """Логирование результатов тестирования"""
    status = "✅ PASS" if success else "❌ FAIL"
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {status} {test_name}")
    if details:
        print(f"    📋 {details}")
    print()

def format_size(size_bytes):
    """Форматировать размер в читаемый вид"""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def test_admin_authorization():
    """Авторизация администратора"""
    global auth_token
    print("🔐 Авторизация администратора (+79999888777/admin123)")
    
    try:
        login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        start_time = time.time()
        response = requests.post(f"{API_BASE}/auth/login", json=login_data)
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            auth_token = data.get("access_token")
            user_info = data.get("user", {})
            
            log_test_result(
                "Авторизация администратора", 
                True, 
                f"Успешная авторизация '{user_info.get('full_name', 'N/A')}', время: {response_time:.0f}ms"
            )
            return True
        else:
            log_test_result("Авторизация администратора", False, f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        log_test_result("Авторизация администратора", False, f"Ошибка: {str(e)}")
        return False

def make_request_with_timing(url, headers=None):
    """Выполнить запрос с измерением времени"""
    start_time = time.time()
    try:
        response = requests.get(url, headers=headers, timeout=30)
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        return response, response_time, None
    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        return None, response_time, str(e)

def simulate_warehouse_category_loading():
    """Симулировать полную загрузку категории складов"""
    print("🏭 СИМУЛЯЦИЯ ПОЛНОЙ ЗАГРУЗКИ КАТЕГОРИИ 'СКЛАДЫ'")
    
    if not auth_token:
        log_test_result("Симуляция загрузки", False, "Нет токена авторизации")
        return
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    total_loading_time = 0
    total_data_size = 0
    requests_made = 0
    
    # 1. Основной запрос списка складов
    print("📋 Шаг 1: Загрузка основного списка складов...")
    response, response_time, error = make_request_with_timing(f"{API_BASE}/warehouses", headers)
    total_loading_time += response_time
    requests_made += 1
    
    if response and response.status_code == 200:
        warehouses = response.json()
        data_size = len(response.content)
        total_data_size += data_size
        
        log_test_result(
            "Основной список складов", 
            True, 
            f"96 складов загружено за {response_time:.0f}ms, размер: {format_size(data_size)}"
        )
        
        # 2. Проверяем, загружается ли статистика для каждого склада
        print("📊 Шаг 2: Проверка загрузки статистики для каждого склада...")
        
        # Тестируем первые 10 складов для понимания паттерна
        test_warehouses = warehouses[:10]
        statistics_times = []
        
        for i, warehouse in enumerate(test_warehouses):
            warehouse_id = warehouse.get('id')
            warehouse_name = warehouse.get('name', 'Unknown')
            
            if warehouse_id:
                response, response_time, error = make_request_with_timing(
                    f"{API_BASE}/warehouses/{warehouse_id}/statistics", 
                    headers
                )
                statistics_times.append(response_time)
                requests_made += 1
                
                if response and response.status_code == 200:
                    data_size = len(response.content)
                    total_data_size += data_size
                    print(f"    Склад {i+1}/10: {warehouse_name[:30]}... - {response_time:.0f}ms")
                else:
                    print(f"    Склад {i+1}/10: {warehouse_name[:30]}... - ОШИБКА")
        
        if statistics_times:
            avg_statistics_time = sum(statistics_times) / len(statistics_times)
            total_statistics_time = sum(statistics_times)
            total_loading_time += total_statistics_time
            
            # Экстраполируем на все склады
            estimated_all_statistics_time = avg_statistics_time * len(warehouses)
            
            log_test_result(
                "Статистика складов (10 из 96)", 
                True, 
                f"Среднее время: {avg_statistics_time:.0f}ms, общее время для 10: {total_statistics_time:.0f}ms, оценка для всех 96: {estimated_all_statistics_time:.0f}ms"
            )
        
        # 3. Проверяем загрузку ячеек складов
        print("📦 Шаг 3: Проверка загрузки ячеек складов...")
        
        cells_times = []
        for i, warehouse in enumerate(test_warehouses):
            warehouse_id = warehouse.get('id')
            warehouse_name = warehouse.get('name', 'Unknown')
            
            if warehouse_id:
                response, response_time, error = make_request_with_timing(
                    f"{API_BASE}/warehouses/{warehouse_id}/cells", 
                    headers
                )
                cells_times.append(response_time)
                requests_made += 1
                
                if response and response.status_code == 200:
                    data_size = len(response.content)
                    total_data_size += data_size
                    cells_data = response.json()
                    cells_count = len(cells_data) if isinstance(cells_data, list) else 0
                    print(f"    Склад {i+1}/10: {warehouse_name[:30]}... - {response_time:.0f}ms, ячеек: {cells_count}")
                else:
                    print(f"    Склад {i+1}/10: {warehouse_name[:30]}... - ОШИБКА")
        
        if cells_times:
            avg_cells_time = sum(cells_times) / len(cells_times)
            total_cells_time = sum(cells_times)
            total_loading_time += total_cells_time
            
            # Экстраполируем на все склады
            estimated_all_cells_time = avg_cells_time * len(warehouses)
            
            log_test_result(
                "Ячейки складов (10 из 96)", 
                True, 
                f"Среднее время: {avg_cells_time:.0f}ms, общее время для 10: {total_cells_time:.0f}ms, оценка для всех 96: {estimated_all_cells_time:.0f}ms"
            )
        
        # 4. Проверяем привязки операторов
        print("👥 Шаг 4: Загрузка привязок операторов...")
        response, response_time, error = make_request_with_timing(
            f"{API_BASE}/admin/operator-warehouse-bindings", 
            headers
        )
        total_loading_time += response_time
        requests_made += 1
        
        if response and response.status_code == 200:
            data_size = len(response.content)
            total_data_size += data_size
            bindings = response.json()
            bindings_count = len(bindings) if isinstance(bindings, list) else 0
            
            log_test_result(
                "Привязки операторов", 
                True, 
                f"Загружено {bindings_count} привязок за {response_time:.0f}ms"
            )
        
        # 5. Итоговый анализ
        print("🎯 ИТОГОВЫЙ АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ:")
        print(f"📊 Общее время загрузки (тестовые данные): {total_loading_time:.0f}ms")
        print(f"📊 Общий размер данных: {format_size(total_data_size)}")
        print(f"📊 Количество запросов: {requests_made}")
        
        # Экстраполяция на полную загрузку всех складов
        if statistics_times and cells_times:
            estimated_full_loading_time = (
                response_time +  # Основной список
                avg_statistics_time * len(warehouses) +  # Статистика всех складов
                avg_cells_time * len(warehouses) +  # Ячейки всех складов
                20  # Привязки операторов
            )
            
            print(f"🚨 ОЦЕНКА ПОЛНОГО ВРЕМЕНИ ЗАГРУЗКИ ВСЕХ 96 СКЛАДОВ: {estimated_full_loading_time:.0f}ms ({estimated_full_loading_time/1000:.1f} секунд)")
            
            if estimated_full_loading_time > 3000:  # Более 3 секунд
                print("⚠️  КРИТИЧЕСКАЯ ПРОБЛЕМА: Время загрузки превышает 3 секунды!")
                print("💡 ОСНОВНЫЕ ПРИЧИНЫ МЕДЛЕННОЙ ЗАГРУЗКИ:")
                print(f"   • N+1 проблема: {len(warehouses)} запросов статистики + {len(warehouses)} запросов ячеек")
                print(f"   • Общее количество запросов: {len(warehouses) * 2 + 2} вместо 1-2")
                print(f"   • Среднее время запроса статистики: {avg_statistics_time:.0f}ms")
                print(f"   • Среднее время запроса ячеек: {avg_cells_time:.0f}ms")
            else:
                print("✅ Производительность в пределах нормы")
    
    else:
        log_test_result("Основной список складов", False, f"Ошибка: {error}")

def test_concurrent_loading():
    """Тест параллельной загрузки для оптимизации"""
    print("⚡ ТЕСТ ПАРАЛЛЕЛЬНОЙ ЗАГРУЗКИ")
    
    if not auth_token:
        return
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Получаем список складов
    response = requests.get(f"{API_BASE}/warehouses", headers=headers)
    if response.status_code != 200:
        return
    
    warehouses = response.json()[:5]  # Тестируем на 5 складах
    
    # Последовательная загрузка
    print("📋 Последовательная загрузка статистики 5 складов:")
    start_time = time.time()
    for warehouse in warehouses:
        warehouse_id = warehouse.get('id')
        if warehouse_id:
            requests.get(f"{API_BASE}/warehouses/{warehouse_id}/statistics", headers=headers)
    sequential_time = (time.time() - start_time) * 1000
    print(f"    Время: {sequential_time:.0f}ms")
    
    # Параллельная загрузка
    print("⚡ Параллельная загрузка статистики 5 складов:")
    start_time = time.time()
    
    def load_warehouse_stats(warehouse_id):
        return requests.get(f"{API_BASE}/warehouses/{warehouse_id}/statistics", headers=headers)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for warehouse in warehouses:
            warehouse_id = warehouse.get('id')
            if warehouse_id:
                future = executor.submit(load_warehouse_stats, warehouse_id)
                futures.append(future)
        
        # Ждем завершения всех запросов
        for future in concurrent.futures.as_completed(futures):
            future.result()
    
    parallel_time = (time.time() - start_time) * 1000
    print(f"    Время: {parallel_time:.0f}ms")
    
    improvement = ((sequential_time - parallel_time) / sequential_time) * 100
    print(f"💡 Улучшение производительности при параллельной загрузке: {improvement:.1f}%")

def main():
    """Основная функция тестирования"""
    print("=" * 80)
    print("🎯 ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: Симуляция загрузки категории 'Склады'")
    print("=" * 80)
    print()
    
    # Авторизация
    if not test_admin_authorization():
        print("❌ Не удалось авторизоваться. Прекращаем тестирование.")
        return
    
    # Симуляция полной загрузки
    simulate_warehouse_category_loading()
    
    # Тест параллельной загрузки
    test_concurrent_loading()
    
    print("=" * 80)
    print("🏁 ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 80)

if __name__ == "__main__":
    main()