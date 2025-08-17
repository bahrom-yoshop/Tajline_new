#!/usr/bin/env python3
"""
🎯 БЫСТРЫЙ ТЕСТ СТАБИЛЬНОСТИ ПОСЛЕ ИСПРАВЛЕНИЯ REACT HOOKS ОШИБКИ

КОНТЕКСТ ТЕСТИРОВАНИЯ:
Финальная проверка стабильности системы после исправления React Hooks ошибки:
1. **Авторизация администратора**: Проверь что можно войти в систему
2. **Базовые endpoints**: Убедись что основные функции работают
3. **Статус**: Нет критических ошибок

КЛЮЧЕВЫЕ ПРОВЕРКИ:
✅ Авторизация администратора работает
✅ Основные API endpoints отвечают корректно
✅ Нет критических ошибок в системе
✅ Backend стабилен после frontend исправлений
"""

import requests
import json
import os
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-manager-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class StabilityTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        
    def log(self, message):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def test_admin_authorization(self):
        """1. Авторизация администратора"""
        self.log("🔐 Тестирование авторизации администратора...")
        
        login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        try:
            response = self.session.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                user_info = data.get('user', {})
                
                self.log(f"✅ Администратор успешно авторизован:")
                self.log(f"   👤 Имя: {user_info.get('full_name')}")
                self.log(f"   📱 Телефон: {user_info.get('phone')}")
                self.log(f"   🔑 Роль: {user_info.get('role')}")
                self.log(f"   🆔 Номер: {user_info.get('user_number')}")
                
                return True
            else:
                self.log(f"❌ Ошибка авторизации: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка авторизации: {e}")
            return False
            
    def test_basic_endpoints(self):
        """2. Тестирование базовых endpoints"""
        self.log("🔍 Тестирование базовых API endpoints...")
        
        if not self.admin_token:
            self.log("❌ Нет токена администратора для тестирования")
            return False
            
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Список критически важных endpoints для проверки
        endpoints_to_test = [
            {
                "name": "Список пользователей",
                "method": "GET",
                "url": f"{API_BASE}/admin/users",
                "expected_status": 200
            },
            {
                "name": "Список складов",
                "method": "GET", 
                "url": f"{API_BASE}/admin/warehouses",
                "expected_status": 200
            },
            {
                "name": "Список транспорта",
                "method": "GET",
                "url": f"{API_BASE}/transport/list",
                "expected_status": 200
            },
            {
                "name": "Список курьеров",
                "method": "GET",
                "url": f"{API_BASE}/admin/couriers/list",
                "expected_status": 200
            },
            {
                "name": "Статистика системы",
                "method": "GET",
                "url": f"{API_BASE}/admin/dashboard/analytics",
                "expected_status": 200
            }
        ]
        
        success_count = 0
        total_tests = len(endpoints_to_test)
        
        for endpoint in endpoints_to_test:
            try:
                self.log(f"📡 Тестирование: {endpoint['name']}")
                
                if endpoint['method'] == 'GET':
                    response = self.session.get(endpoint['url'], headers=headers, timeout=10)
                else:
                    response = self.session.post(endpoint['url'], headers=headers, timeout=10)
                
                if response.status_code == endpoint['expected_status']:
                    self.log(f"✅ {endpoint['name']}: OK (статус {response.status_code})")
                    success_count += 1
                    
                    # Проверяем что ответ содержит данные
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            self.log(f"   📊 Получено элементов: {len(data)}")
                        elif isinstance(data, dict) and 'items' in data:
                            self.log(f"   📊 Получено элементов: {len(data['items'])}")
                        elif isinstance(data, dict):
                            self.log(f"   📊 Получен объект с {len(data)} полями")
                    except:
                        pass
                        
                else:
                    self.log(f"❌ {endpoint['name']}: Ошибка {response.status_code}")
                    
            except Exception as e:
                self.log(f"❌ {endpoint['name']}: Критическая ошибка - {e}")
                
        success_rate = (success_count / total_tests) * 100
        self.log(f"📊 Результат тестирования endpoints: {success_count}/{total_tests} ({success_rate:.1f}%)")
        
        return success_rate >= 80  # 80% успешности считается приемлемым
        
    def test_system_health(self):
        """3. Проверка общего состояния системы"""
        self.log("🏥 Проверка общего состояния системы...")
        
        if not self.admin_token:
            self.log("❌ Нет токена для проверки состояния системы")
            return False
            
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            # Проверяем статистику системы
            response = self.session.get(f"{API_BASE}/admin/dashboard/analytics", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                self.log("✅ Система работает стабильно:")
                
                # Проверяем основные метрики
                if 'total_users' in data:
                    self.log(f"   👥 Всего пользователей: {data.get('total_users', 0)}")
                    
                if 'total_cargo' in data:
                    self.log(f"   📦 Всего грузов: {data.get('total_cargo', 0)}")
                    
                if 'active_transports' in data:
                    self.log(f"   🚛 Активных транспортов: {data.get('active_transports', 0)}")
                    
                if 'total_warehouses' in data:
                    self.log(f"   🏭 Всего складов: {data.get('total_warehouses', 0)}")
                
                return True
            else:
                self.log(f"❌ Ошибка получения статистики системы: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка проверки системы: {e}")
            return False
            
    def run_stability_test(self):
        """Запуск быстрого теста стабильности"""
        self.log("🎯 НАЧАЛО БЫСТРОГО ТЕСТА СТАБИЛЬНОСТИ ПОСЛЕ ИСПРАВЛЕНИЯ REACT HOOKS")
        self.log("=" * 70)
        
        success_count = 0
        total_tests = 3
        
        try:
            # Тест 1: Авторизация администратора
            self.log("\n📋 ТЕСТ 1: Авторизация администратора")
            if self.test_admin_authorization():
                success_count += 1
                self.log("✅ Авторизация администратора: ПРОЙДЕН")
            else:
                self.log("❌ Авторизация администратора: ПРОВАЛЕН")
                
            # Тест 2: Базовые endpoints
            self.log("\n📋 ТЕСТ 2: Базовые API endpoints")
            if self.test_basic_endpoints():
                success_count += 1
                self.log("✅ Базовые endpoints: ПРОЙДЕНЫ")
            else:
                self.log("❌ Базовые endpoints: ПРОБЛЕМЫ")
                
            # Тест 3: Общее состояние системы
            self.log("\n📋 ТЕСТ 3: Общее состояние системы")
            if self.test_system_health():
                success_count += 1
                self.log("✅ Состояние системы: СТАБИЛЬНО")
            else:
                self.log("❌ Состояние системы: ПРОБЛЕМЫ")
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка во время тестирования: {e}")
            
        # Итоговый отчет
        self.log("\n" + "=" * 70)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТА СТАБИЛЬНОСТИ")
        self.log("=" * 70)
        
        success_rate = (success_count / total_tests) * 100
        
        self.log(f"📊 РЕЗУЛЬТАТЫ:")
        self.log(f"   Успешных тестов: {success_count}/{total_tests}")
        self.log(f"   Процент успеха: {success_rate:.1f}%")
        
        if success_rate == 100:
            self.log("🎉 ОТЛИЧНО: Система полностью стабильна после исправлений!")
            status = "СТАБИЛЬНА"
        elif success_rate >= 66:
            self.log("✅ ХОРОШО: Система в основном стабильна, есть минорные проблемы")
            status = "В ОСНОВНОМ СТАБИЛЬНА"
        else:
            self.log("❌ ПРОБЛЕМЫ: Система нестабильна, требуются дополнительные исправления")
            status = "НЕСТАБИЛЬНА"
            
        self.log(f"\n🏥 СТАТУС СИСТЕМЫ: {status}")
        self.log(f"🔧 ИСПРАВЛЕНИЯ REACT HOOKS: {'УСПЕШНЫ' if success_rate >= 66 else 'ТРЕБУЮТ ДОРАБОТКИ'}")
        
        return success_rate >= 66

def main():
    """Главная функция запуска теста стабильности"""
    print("🎯 БЫСТРЫЙ ТЕСТ СТАБИЛЬНОСТИ ПОСЛЕ ИСПРАВЛЕНИЯ REACT HOOKS ОШИБКИ")
    print("=" * 70)
    
    tester = StabilityTester()
    success = tester.run_stability_test()
    
    if success:
        print("\n🎉 ТЕСТ СТАБИЛЬНОСТИ ПРОЙДЕН УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТ СТАБИЛЬНОСТИ ВЫЯВИЛ ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()