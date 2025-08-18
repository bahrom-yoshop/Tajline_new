#!/usr/bin/env python3
"""
🔍 ПОЛУЧЕНИЕ СПИСКА ПОЛЬЗОВАТЕЛЕЙ: Найти рабочие учетные данные для тестирования навигации чата

ЗАДАЧА:
Получить список активных пользователей системы с ролями admin и warehouse_operator для тестирования исправленной навигации чата.

ЦЕЛЬ:
Найти корректные учетные данные (номер телефона и пароль) для авторизации и последующего тестирования UI.

ENDPOINTS ДЛЯ ПРОВЕРКИ:
1. GET /api/admin/users - список пользователей
2. GET /api/users - альтернативный endpoint
3. Если нужно - попробовать стандартные учетные данные admin/operator

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
- Получить номера телефонов и роли активных пользователей
- Найти хотя бы одного админа или оператора для UI тестирования
- Предоставить рабочие credentials для frontend авторизации
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class UserCredentialsFinder:
    def __init__(self):
        self.admin_token = None
        self.test_results = []
        self.found_credentials = []
        
    def log_result(self, test_name, success, details=""):
        """Логирование результатов тестирования"""
        status = "✅" if success else "❌"
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} {test_name}: {details}")
        
    def try_standard_credentials(self):
        """Попробовать стандартные учетные данные"""
        standard_creds = [
            # Известные учетные данные из предыдущих тестов
            {
                "phone": "+79999888777",
                "password": "admin123",
                "expected_role": "admin",
                "description": "Стандартный администратор"
            },
            {
                "phone": "+79777888999", 
                "password": "warehouse123",
                "expected_role": "warehouse_operator",
                "description": "Стандартный оператор склада"
            },
            # Дополнительные возможные варианты
            {
                "phone": "admin",
                "password": "admin",
                "expected_role": "admin",
                "description": "Простые admin/admin"
            },
            {
                "phone": "operator",
                "password": "operator", 
                "expected_role": "warehouse_operator",
                "description": "Простые operator/operator"
            }
        ]
        
        print("\n🔑 ТЕСТИРОВАНИЕ СТАНДАРТНЫХ УЧЕТНЫХ ДАННЫХ")
        print("-" * 60)
        
        for cred in standard_creds:
            try:
                login_data = {
                    "phone": cred["phone"],
                    "password": cred["password"]
                }
                
                response = requests.post(f"{BACKEND_URL}/auth/login", 
                                       json=login_data, headers=HEADERS)
                
                if response.status_code == 200:
                    data = response.json()
                    user_info = data.get("user", {})
                    token = data.get("access_token")
                    
                    # Сохраняем первый успешный админский токен
                    if not self.admin_token and user_info.get("role") == "admin":
                        self.admin_token = token
                    
                    credential_info = {
                        "phone": cred["phone"],
                        "password": cred["password"],
                        "user_info": user_info,
                        "token": token,
                        "description": cred["description"]
                    }
                    self.found_credentials.append(credential_info)
                    
                    self.log_result(f"Авторизация {cred['description']}", True,
                                  f"Пользователь: {user_info.get('full_name')}, "
                                  f"Роль: {user_info.get('role')}, "
                                  f"Номер: {user_info.get('user_number')}, "
                                  f"Телефон: {user_info.get('phone')}")
                else:
                    self.log_result(f"Авторизация {cred['description']}", False,
                                  f"HTTP {response.status_code}: {response.text[:100]}")
                    
            except Exception as e:
                self.log_result(f"Авторизация {cred['description']}", False, f"Ошибка: {str(e)}")
    
    def get_users_via_admin_endpoint(self):
        """Получить список пользователей через /api/admin/users"""
        try:
            if not self.admin_token:
                self.log_result("Получение списка через /api/admin/users", False, 
                              "Нет токена администратора")
                return []
                
            headers = {**HEADERS, "Authorization": f"Bearer {self.admin_token}"}
            
            # Пробуем получить всех пользователей
            response = requests.get(f"{BACKEND_URL}/admin/users", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                users = data.get('items', []) if isinstance(data, dict) else data
                
                # Фильтруем только админов и операторов
                target_users = []
                for user in users:
                    role = user.get('role', '')
                    if role in ['admin', 'warehouse_operator']:
                        target_users.append(user)
                
                self.log_result("Получение списка через /api/admin/users", True,
                              f"Всего пользователей: {len(users)}, "
                              f"Админов и операторов: {len(target_users)}")
                
                return target_users
            else:
                self.log_result("Получение списка через /api/admin/users", False,
                              f"HTTP {response.status_code}: {response.text[:200]}")
                return []
                
        except Exception as e:
            self.log_result("Получение списка через /api/admin/users", False, f"Ошибка: {str(e)}")
            return []
    
    def get_users_via_alternative_endpoint(self):
        """Получить список пользователей через альтернативный endpoint /api/users"""
        try:
            if not self.admin_token:
                self.log_result("Получение списка через /api/users", False, 
                              "Нет токена администратора")
                return []
                
            headers = {**HEADERS, "Authorization": f"Bearer {self.admin_token}"}
            
            response = requests.get(f"{BACKEND_URL}/users", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                users = data.get('items', []) if isinstance(data, dict) else data
                
                # Фильтруем только админов и операторов
                target_users = []
                for user in users:
                    role = user.get('role', '')
                    if role in ['admin', 'warehouse_operator']:
                        target_users.append(user)
                
                self.log_result("Получение списка через /api/users", True,
                              f"Всего пользователей: {len(users)}, "
                              f"Админов и операторов: {len(target_users)}")
                
                return target_users
            else:
                self.log_result("Получение списка через /api/users", False,
                              f"HTTP {response.status_code}: {response.text[:200]}")
                return []
                
        except Exception as e:
            self.log_result("Получение списка через /api/users", False, f"Ошибка: {str(e)}")
            return []
    
    def analyze_user_data(self, users):
        """Анализ данных пользователей"""
        if not users:
            self.log_result("Анализ данных пользователей", False, "Нет данных для анализа")
            return
            
        print(f"\n📊 АНАЛИЗ НАЙДЕННЫХ ПОЛЬЗОВАТЕЛЕЙ ({len(users)} пользователей)")
        print("-" * 60)
        
        admin_count = 0
        operator_count = 0
        active_count = 0
        
        for user in users:
            role = user.get('role', 'unknown')
            is_active = user.get('is_active', False)
            phone = user.get('phone', 'N/A')
            full_name = user.get('full_name', 'N/A')
            user_number = user.get('user_number', 'N/A')
            
            if role == 'admin':
                admin_count += 1
            elif role == 'warehouse_operator':
                operator_count += 1
                
            if is_active:
                active_count += 1
            
            status = "🟢 Активен" if is_active else "🔴 Неактивен"
            print(f"   👤 {full_name} ({user_number})")
            print(f"      📞 Телефон: {phone}")
            print(f"      🎭 Роль: {role}")
            print(f"      {status}")
            print()
        
        self.log_result("Анализ данных пользователей", True,
                      f"Админов: {admin_count}, Операторов: {operator_count}, "
                      f"Активных: {active_count}")
    
    def provide_credentials_summary(self):
        """Предоставить итоговую сводку учетных данных"""
        print("\n🎯 ИТОГОВАЯ СВОДКА РАБОЧИХ УЧЕТНЫХ ДАННЫХ")
        print("=" * 70)
        
        if not self.found_credentials:
            print("❌ НЕ НАЙДЕНО РАБОЧИХ УЧЕТНЫХ ДАННЫХ")
            print("   Рекомендуется создать тестовых пользователей")
            return
        
        admin_creds = []
        operator_creds = []
        
        for cred in self.found_credentials:
            user_info = cred.get('user_info', {})
            role = user_info.get('role', '')
            
            if role == 'admin':
                admin_creds.append(cred)
            elif role == 'warehouse_operator':
                operator_creds.append(cred)
        
        print(f"\n👑 АДМИНИСТРАТОРЫ ({len(admin_creds)} найдено):")
        for cred in admin_creds:
            user_info = cred.get('user_info', {})
            print(f"   📞 Телефон: {cred['phone']}")
            print(f"   🔑 Пароль: {cred['password']}")
            print(f"   👤 Имя: {user_info.get('full_name', 'N/A')}")
            print(f"   🆔 Номер: {user_info.get('user_number', 'N/A')}")
            print(f"   📝 Описание: {cred['description']}")
            print()
        
        print(f"\n🏭 ОПЕРАТОРЫ СКЛАДОВ ({len(operator_creds)} найдено):")
        for cred in operator_creds:
            user_info = cred.get('user_info', {})
            print(f"   📞 Телефон: {cred['phone']}")
            print(f"   🔑 Пароль: {cred['password']}")
            print(f"   👤 Имя: {user_info.get('full_name', 'N/A')}")
            print(f"   🆔 Номер: {user_info.get('user_number', 'N/A')}")
            print(f"   📝 Описание: {cred['description']}")
            print()
        
        # Рекомендации для UI тестирования
        print("🎯 РЕКОМЕНДАЦИИ ДЛЯ UI ТЕСТИРОВАНИЯ:")
        if admin_creds:
            best_admin = admin_creds[0]
            print(f"   👑 Для тестирования как АДМИН используйте:")
            print(f"      Телефон: {best_admin['phone']}")
            print(f"      Пароль: {best_admin['password']}")
        
        if operator_creds:
            best_operator = operator_creds[0]
            print(f"   🏭 Для тестирования как ОПЕРАТОР используйте:")
            print(f"      Телефон: {best_operator['phone']}")
            print(f"      Пароль: {best_operator['password']}")
        
        if not admin_creds and not operator_creds:
            print("   ⚠️ Найдены учетные данные, но не админов или операторов")
    
    def run_comprehensive_search(self):
        """Запуск полного поиска учетных данных"""
        print("🔍 НАЧАЛО ПОИСКА РАБОЧИХ УЧЕТНЫХ ДАННЫХ ДЛЯ ТЕСТИРОВАНИЯ НАВИГАЦИИ ЧАТА")
        print("=" * 80)
        
        try:
            # 1. Тестирование стандартных учетных данных
            self.try_standard_credentials()
            
            # 2. Получение списка пользователей через основной endpoint
            print("\n📋 ПОЛУЧЕНИЕ СПИСКА ПОЛЬЗОВАТЕЛЕЙ ЧЕРЕЗ /api/admin/users")
            print("-" * 60)
            admin_users = self.get_users_via_admin_endpoint()
            
            # 3. Получение списка пользователей через альтернативный endpoint
            print("\n📋 ПОЛУЧЕНИЕ СПИСКА ПОЛЬЗОВАТЕЛЕЙ ЧЕРЕЗ /api/users")
            print("-" * 60)
            alt_users = self.get_users_via_alternative_endpoint()
            
            # 4. Анализ найденных пользователей
            all_users = admin_users + alt_users
            # Удаляем дубликаты по ID
            unique_users = []
            seen_ids = set()
            for user in all_users:
                user_id = user.get('id')
                if user_id and user_id not in seen_ids:
                    unique_users.append(user)
                    seen_ids.add(user_id)
            
            if unique_users:
                self.analyze_user_data(unique_users)
            
            # 5. Итоговая сводка
            self.provide_credentials_summary()
            
        except Exception as e:
            self.log_result("Общая ошибка поиска", False, f"Ошибка: {str(e)}")
        
        finally:
            # Вывод итогового отчета
            self.print_final_report()
    
    def print_final_report(self):
        """Вывод итогового отчета"""
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ПОИСКА УЧЕТНЫХ ДАННЫХ")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 СТАТИСТИКА:")
        print(f"   Всего тестов: {total_tests}")
        print(f"   Успешных: {successful_tests}")
        print(f"   Неуспешных: {total_tests - successful_tests}")
        print(f"   Процент успеха: {success_rate:.1f}%")
        
        print(f"\n🔑 НАЙДЕННЫЕ УЧЕТНЫЕ ДАННЫЕ:")
        print(f"   Всего рабочих аккаунтов: {len(self.found_credentials)}")
        
        admin_count = len([c for c in self.found_credentials 
                          if c.get('user_info', {}).get('role') == 'admin'])
        operator_count = len([c for c in self.found_credentials 
                             if c.get('user_info', {}).get('role') == 'warehouse_operator'])
        
        print(f"   Администраторов: {admin_count}")
        print(f"   Операторов складов: {operator_count}")
        
        print(f"\n🎯 КРИТИЧЕСКИЙ ВЫВОД:")
        if len(self.found_credentials) > 0 and (admin_count > 0 or operator_count > 0):
            print("   ✅ НАЙДЕНЫ РАБОЧИЕ УЧЕТНЫЕ ДАННЫЕ ДЛЯ UI ТЕСТИРОВАНИЯ!")
            print("   ✅ Можно приступать к тестированию исправленной навигации чата")
            if admin_count > 0:
                print("   ✅ Доступны учетные данные администратора")
            if operator_count > 0:
                print("   ✅ Доступны учетные данные оператора склада")
        else:
            print("   ❌ НЕ НАЙДЕНЫ ПОДХОДЯЩИЕ УЧЕТНЫЕ ДАННЫЕ")
            print("   ❌ Требуется создание тестовых пользователей")
        
        print("\n" + "=" * 80)

def main():
    """Главная функция запуска поиска учетных данных"""
    finder = UserCredentialsFinder()
    finder.run_comprehensive_search()

if __name__ == "__main__":
    main()