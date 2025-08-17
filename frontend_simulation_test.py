#!/usr/bin/env python3
"""
🎯 FRONTEND SIMULATION TEST: Симуляция точного поведения frontend при создании курьера

Цель: Воспроизвести точно такие же запросы, которые делает frontend,
чтобы найти причину 404 ошибки при создании курьера.

Тестируем:
1. Использование точного URL из REACT_APP_BACKEND_URL
2. Точные заголовки как в frontend
3. Точную структуру данных
4. Авторизацию с Bearer token
5. Проверку CORS
"""

import requests
import json
import sys
import os
from datetime import datetime

# Используем точно тот же URL что и frontend
FRONTEND_BACKEND_URL = "https://tajline-manager-1.preview.emergentagent.com"
API_BASE = f"{FRONTEND_BACKEND_URL}/api"

class FrontendSimulationTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_results = []
        self.available_warehouses = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def log_test(self, test_name, success, details=""):
        """Логирование результатов тестов"""
        status = "✅" if success else "❌"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        self.log(f"{status} {test_name}: {details}")
    
    def test_frontend_auth(self):
        """Авторизация с точно такими же параметрами как frontend"""
        try:
            self.log("🔐 Авторизация администратора (симуляция frontend)...")
            
            # Точно такие же заголовки как в frontend
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (compatible; Frontend-Test/1.0)'
            }
            
            auth_data = {
                "phone": "+79999888777",
                "password": "admin123"
            }
            
            response = self.session.post(
                f"{API_BASE}/auth/login",
                json=auth_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                user_info = data["user"]
                
                self.log_test(
                    "FRONTEND АВТОРИЗАЦИЯ",
                    True,
                    f"Успешная авторизация '{user_info['full_name']}' через frontend URL"
                )
                return True
            else:
                self.log_test(
                    "FRONTEND АВТОРИЗАЦИЯ",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("FRONTEND АВТОРИЗАЦИЯ", False, f"Ошибка: {str(e)}")
            return False
    
    def get_warehouses_frontend_style(self):
        """Получить склады точно как frontend"""
        try:
            self.log("🏢 Получение складов (симуляция frontend)...")
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.admin_token}',
                'User-Agent': 'Mozilla/5.0 (compatible; Frontend-Test/1.0)'
            }
            
            response = self.session.get(f"{API_BASE}/warehouses", headers=headers)
            
            if response.status_code == 200:
                warehouses = response.json()
                self.available_warehouses = warehouses
                
                self.log_test(
                    "ПОЛУЧЕНИЕ СКЛАДОВ FRONTEND",
                    True,
                    f"Получено {len(warehouses)} складов через frontend URL"
                )
                return len(warehouses) > 0
            else:
                self.log_test(
                    "ПОЛУЧЕНИЕ СКЛАДОВ FRONTEND",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("ПОЛУЧЕНИЕ СКЛАДОВ FRONTEND", False, f"Ошибка: {str(e)}")
            return False
    
    def test_courier_creation_exact_frontend(self):
        """Тестирование создания курьера точно как frontend"""
        try:
            self.log("🎯 КРИТИЧЕСКИЙ ТЕСТ: Создание курьера (точная симуляция frontend)")
            
            if not self.available_warehouses:
                self.log_test(
                    "СОЗДАНИЕ КУРЬЕРА FRONTEND",
                    False,
                    "Нет доступных складов"
                )
                return False
            
            # Точно такие же заголовки как в frontend apiCall
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.admin_token}',
                'User-Agent': 'Mozilla/5.0 (compatible; Frontend-Test/1.0)',
                'Origin': FRONTEND_BACKEND_URL,
                'Referer': f"{FRONTEND_BACKEND_URL}/"
            }
            
            # Точно такие же данные как в frontend форме
            courier_data = {
                "full_name": "Тестовый Курьер Иванов",
                "phone": "+79991234567",
                "password": "courier123",
                "address": "Тестовый адрес",
                "transport_type": "car",
                "transport_number": "A123BC777",
                "transport_capacity": 100.0,
                "assigned_warehouse_id": self.available_warehouses[0]["id"]
            }
            
            self.log(f"Отправляем POST запрос на: {API_BASE}/admin/couriers/create")
            self.log(f"Данные: {json.dumps(courier_data, indent=2)}")
            self.log(f"Заголовки: {json.dumps(dict(headers), indent=2)}")
            
            response = self.session.post(
                f"{API_BASE}/admin/couriers/create",
                json=courier_data,
                headers=headers
            )
            
            self.log(f"Получен ответ: HTTP {response.status_code}")
            self.log(f"Заголовки ответа: {dict(response.headers)}")
            self.log(f"Тело ответа: {response.text}")
            
            if response.status_code == 404:
                self.log_test(
                    "СОЗДАНИЕ КУРЬЕРА FRONTEND",
                    False,
                    f"🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: HTTP 404 при точной симуляции frontend! Response: {response.text}"
                )
                return False
            elif response.status_code == 200:
                data = response.json()
                courier_id = data.get("courier_id")
                
                self.log_test(
                    "СОЗДАНИЕ КУРЬЕРА FRONTEND",
                    True,
                    f"✅ Курьер успешно создан через frontend URL! ID: {courier_id}"
                )
                
                # Удаляем тестового курьера
                if courier_id:
                    delete_response = self.session.delete(
                        f"{API_BASE}/admin/couriers/{courier_id}",
                        headers=headers
                    )
                    self.log(f"Тестовый курьер удален: HTTP {delete_response.status_code}")
                
                return True
            elif response.status_code in [400, 422]:
                self.log_test(
                    "СОЗДАНИЕ КУРЬЕРА FRONTEND",
                    True,
                    f"✅ Endpoint доступен (ошибка валидации): HTTP {response.status_code} - {response.text}"
                )
                return True
            else:
                self.log_test(
                    "СОЗДАНИЕ КУРЬЕРА FRONTEND",
                    False,
                    f"Неожиданный HTTP код: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test("СОЗДАНИЕ КУРЬЕРА FRONTEND", False, f"Ошибка: {str(e)}")
            return False
    
    def test_cors_preflight(self):
        """Тестирование CORS preflight запроса"""
        try:
            self.log("🌐 ТЕСТ: Проверка CORS preflight запроса")
            
            headers = {
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type,authorization',
                'Origin': FRONTEND_BACKEND_URL,
                'User-Agent': 'Mozilla/5.0 (compatible; Frontend-Test/1.0)'
            }
            
            response = self.session.options(
                f"{API_BASE}/admin/couriers/create",
                headers=headers
            )
            
            self.log(f"CORS preflight ответ: HTTP {response.status_code}")
            self.log(f"CORS заголовки: {dict(response.headers)}")
            
            if response.status_code in [200, 204]:
                cors_headers = response.headers
                allow_origin = cors_headers.get('Access-Control-Allow-Origin', '')
                allow_methods = cors_headers.get('Access-Control-Allow-Methods', '')
                allow_headers = cors_headers.get('Access-Control-Allow-Headers', '')
                
                self.log_test(
                    "CORS PREFLIGHT",
                    True,
                    f"CORS работает: Origin={allow_origin}, Methods={allow_methods}, Headers={allow_headers}"
                )
                return True
            else:
                self.log_test(
                    "CORS PREFLIGHT",
                    False,
                    f"CORS preflight неудачен: HTTP {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_test("CORS PREFLIGHT", False, f"Ошибка: {str(e)}")
            return False
    
    def test_different_http_methods(self):
        """Тестирование различных HTTP методов для диагностики"""
        try:
            self.log("🔍 ТЕСТ: Проверка различных HTTP методов")
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.admin_token}',
                'User-Agent': 'Mozilla/5.0 (compatible; Frontend-Test/1.0)'
            }
            
            methods_results = []
            
            # GET запрос (должен вернуть 405 Method Not Allowed)
            try:
                response = self.session.get(f"{API_BASE}/admin/couriers/create", headers=headers)
                methods_results.append(f"GET: HTTP {response.status_code}")
            except Exception as e:
                methods_results.append(f"GET: Ошибка {str(e)}")
            
            # PUT запрос (должен вернуть 405 Method Not Allowed)
            try:
                response = self.session.put(f"{API_BASE}/admin/couriers/create", 
                                          json={"test": "data"}, headers=headers)
                methods_results.append(f"PUT: HTTP {response.status_code}")
            except Exception as e:
                methods_results.append(f"PUT: Ошибка {str(e)}")
            
            # DELETE запрос (должен вернуть 405 Method Not Allowed)
            try:
                response = self.session.delete(f"{API_BASE}/admin/couriers/create", headers=headers)
                methods_results.append(f"DELETE: HTTP {response.status_code}")
            except Exception as e:
                methods_results.append(f"DELETE: Ошибка {str(e)}")
            
            self.log_test(
                "ТЕСТИРОВАНИЕ HTTP МЕТОДОВ",
                True,
                f"Результаты: {', '.join(methods_results)}"
            )
            return True
                
        except Exception as e:
            self.log_test("ТЕСТИРОВАНИЕ HTTP МЕТОДОВ", False, f"Ошибка: {str(e)}")
            return False
    
    def test_url_variations(self):
        """Тестирование различных вариаций URL"""
        try:
            self.log("🔗 ТЕСТ: Проверка различных вариаций URL")
            
            if not self.available_warehouses:
                self.log_test("ТЕСТИРОВАНИЕ URL ВАРИАЦИЙ", False, "Нет складов")
                return False
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.admin_token}',
                'User-Agent': 'Mozilla/5.0 (compatible; Frontend-Test/1.0)'
            }
            
            courier_data = {
                "full_name": "URL Test Курьер",
                "phone": "+79991234568",
                "password": "courier123",
                "address": "Тестовый адрес",
                "transport_type": "car",
                "transport_number": "URL001",
                "transport_capacity": 100.0,
                "assigned_warehouse_id": self.available_warehouses[0]["id"]
            }
            
            url_variations = [
                f"{API_BASE}/admin/couriers/create",  # Основной URL
                f"{API_BASE}/admin/couriers/create/",  # С trailing slash
                f"{FRONTEND_BACKEND_URL}/api/admin/couriers/create",  # Полный URL
            ]
            
            url_results = []
            
            for url in url_variations:
                try:
                    response = self.session.post(url, json=courier_data, headers=headers)
                    url_results.append(f"{url}: HTTP {response.status_code}")
                    
                    # Если курьер создался, удаляем его
                    if response.status_code == 200:
                        data = response.json()
                        courier_id = data.get("courier_id")
                        if courier_id:
                            self.session.delete(f"{API_BASE}/admin/couriers/{courier_id}", headers=headers)
                            
                except Exception as e:
                    url_results.append(f"{url}: Ошибка {str(e)}")
            
            self.log_test(
                "ТЕСТИРОВАНИЕ URL ВАРИАЦИЙ",
                True,
                f"Результаты: {'; '.join(url_results)}"
            )
            return True
                
        except Exception as e:
            self.log_test("ТЕСТИРОВАНИЕ URL ВАРИАЦИЙ", False, f"Ошибка: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        self.log("🎯 FRONTEND SIMULATION TEST: Симуляция точного поведения frontend при создании курьера")
        self.log("=" * 100)
        
        # Список всех тестов
        tests = [
            ("Frontend авторизация", self.test_frontend_auth),
            ("Получение складов frontend", self.get_warehouses_frontend_style),
            ("🎯 КРИТИЧЕСКИЙ: Создание курьера frontend", self.test_courier_creation_exact_frontend),
            ("CORS preflight проверка", self.test_cors_preflight),
            ("Тестирование HTTP методов", self.test_different_http_methods),
            ("Тестирование URL вариаций", self.test_url_variations)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n📋 ТЕСТ: {test_name}")
            self.log("-" * 80)
            
            try:
                result = test_func()
                if result:
                    passed_tests += 1
                    self.log(f"✅ ТЕСТ ПРОЙДЕН: {test_name}")
                else:
                    self.log(f"❌ ТЕСТ НЕ ПРОЙДЕН: {test_name}")
            except Exception as e:
                self.log(f"❌ ИСКЛЮЧЕНИЕ В ТЕСТЕ {test_name}: {e}", "ERROR")
        
        # Итоговый отчет
        self.log("\n" + "=" * 100)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ FRONTEND SIMULATION")
        self.log("=" * 100)
        
        success_rate = (passed_tests / total_tests) * 100
        self.log(f"📊 РЕЗУЛЬТАТ: {passed_tests}/{total_tests} тестов пройдено ({success_rate:.1f}%)")
        
        self.log("\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            self.log(f"   {status} {result['test']}: {result['details']}")
        
        # КРИТИЧЕСКИЕ ВЫВОДЫ
        self.log("\n🔍 ДИАГНОСТИЧЕСКИЕ ВЫВОДЫ:")
        
        frontend_test = next((r for r in self.test_results if "СОЗДАНИЕ КУРЬЕРА FRONTEND" in r["test"]), None)
        if frontend_test:
            if frontend_test["success"]:
                self.log("✅ FRONTEND URL И ENDPOINT РАБОТАЮТ КОРРЕКТНО")
                self.log("✅ Проблема 404 НЕ воспроизводится при точной симуляции frontend")
                self.log("🔍 ВОЗМОЖНЫЕ ПРИЧИНЫ ПРОБЛЕМЫ ПОЛЬЗОВАТЕЛЯ:")
                self.log("   1. Проблема в конкретном браузере пользователя")
                self.log("   2. Кэширование старой версии frontend")
                self.log("   3. Проблемы с сетью или прокси пользователя")
                self.log("   4. Временная проблема с сервером (уже исправлена)")
                self.log("   5. Проблема с конкретными данными формы")
            else:
                self.log("🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: 404 ВОСПРОИЗВОДИТСЯ!")
                self.log("❌ Требуется немедленное исправление endpoint'а или маршрутизации")
        
        return success_rate >= 75

def main():
    """Главная функция"""
    print("🎯 FRONTEND SIMULATION TEST: Симуляция точного поведения frontend при создании курьера")
    print("=" * 100)
    
    tester = FrontendSimulationTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()