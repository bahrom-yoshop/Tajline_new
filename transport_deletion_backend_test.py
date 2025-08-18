#!/usr/bin/env python3
"""
🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Ошибка удаления транспорта из списка транспортов в TAJLINE.TJ

ПРОБЛЕМА: При попытке удаления транспорта из категории "Логистика" → "Список транспортов" возникает ошибка

ПОДОЗРЕНИЯ:
1. Frontend отправляет неправильный ID транспорта на backend
2. Backend endpoint удаления транспорта работает с неправильной коллекцией
3. Используется неправильный ключ поиска (id vs transport_id vs transport_number)
4. Endpoint для удаления транспорта не существует или работает некорректно

НУЖНО ПРОТЕСТИРОВАТЬ:
1. Авторизация админа для доступа к транспортам
2. Получение списка транспортов через GET /api/admin/transport
3. Проверка структуры данных транспортов (какие поля ID используются)
4. Тестирование удаления транспорта через DELETE endpoint
5. Анализ используемых полей: id, transport_id, transport_number
6. Проверка существования endpoints: /api/admin/transport/{id}, /api/admin/transports/{id}

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Найти корневую причину ошибки удаления транспорта и предложить исправление
"""

import requests
import json
import os
from datetime import datetime
import time

# Получаем URL backend из переменных окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-system-debug.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class TransportDeletionTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.user_info = None
        self.test_results = []
        
    def log(self, message, level="INFO"):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def add_test_result(self, test_name, success, details):
        """Добавить результат теста"""
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def authenticate_admin(self, phone="+79999888777", password="admin123"):
        """Авторизация администратора для доступа к транспортам"""
        try:
            self.log("🔐 Попытка авторизации администратора для доступа к транспортам...")
            
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": phone,
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_info = data.get("user")
                
                # Устанавливаем заголовок авторизации
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                
                self.log(f"✅ Успешная авторизация администратора: {self.user_info.get('full_name')} (роль: {self.user_info.get('role')})")
                self.add_test_result("Авторизация администратора", True, f"Пользователь: {self.user_info.get('full_name')}, роль: {self.user_info.get('role')}")
                return True
            else:
                self.log(f"❌ Ошибка авторизации: {response.status_code} - {response.text}")
                self.add_test_result("Авторизация администратора", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при авторизации: {e}")
            self.add_test_result("Авторизация администратора", False, f"Исключение: {str(e)}")
            return False
    
    def get_transport_list(self):
        """Получение списка транспортов через различные возможные endpoints"""
        transport_data = []
        
        # Список возможных endpoints для получения транспортов
        possible_endpoints = [
            "/transport/list",  # Найденный рабочий endpoint
            "/admin/transport",
            "/admin/transports", 
            "/transport",
            "/transports",
            "/admin/transport/list",
            "/admin/transports/list"
        ]
        
        self.log("🚛 Тестирование получения списка транспортов через различные endpoints...")
        
        for endpoint in possible_endpoints:
            try:
                self.log(f"   Тестирование GET {endpoint}...")
                response = self.session.get(f"{API_BASE}{endpoint}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.log(f"✅ Endpoint GET {endpoint} работает! Получено транспортов: {len(data) if isinstance(data, list) else 'неизвестно'}")
                    
                    # Анализируем структуру данных
                    if isinstance(data, list) and len(data) > 0:
                        sample_transport = data[0]
                        self.log(f"   📋 Структура данных транспорта: {list(sample_transport.keys())}")
                        
                        # Проверяем наличие различных полей ID
                        id_fields = []
                        if 'id' in sample_transport:
                            id_fields.append(f"id: {sample_transport['id']}")
                        if 'transport_id' in sample_transport:
                            id_fields.append(f"transport_id: {sample_transport['transport_id']}")
                        if 'transport_number' in sample_transport:
                            id_fields.append(f"transport_number: {sample_transport['transport_number']}")
                        
                        self.log(f"   🔑 Найденные поля ID: {', '.join(id_fields)}")
                        
                        transport_data = data
                        self.add_test_result(f"GET {endpoint}", True, f"Получено {len(data)} транспортов, поля ID: {id_fields}")
                        break
                    else:
                        self.log(f"   ⚠️ Endpoint работает, но данных нет или неправильный формат")
                        self.add_test_result(f"GET {endpoint}", True, "Endpoint работает, но данных нет")
                        
                elif response.status_code == 404:
                    self.log(f"   ❌ Endpoint GET {endpoint} не найден (404)")
                    self.add_test_result(f"GET {endpoint}", False, "Endpoint не найден (404)")
                else:
                    self.log(f"   ❌ Endpoint GET {endpoint} вернул ошибку: {response.status_code}")
                    self.add_test_result(f"GET {endpoint}", False, f"HTTP {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                self.log(f"   ❌ Исключение при тестировании GET {endpoint}: {e}")
                self.add_test_result(f"GET {endpoint}", False, f"Исключение: {str(e)}")
        
        return transport_data
    
    def create_test_transport(self):
        """Создание тестового транспорта для проверки удаления"""
        try:
            self.log("🚛 Создание тестового транспорта для диагностики удаления...")
            
            test_transport_data = {
                "driver_name": "Тестовый Водитель Удаления",
                "driver_phone": "+79999000001",
                "transport_number": "TEST001DEL",
                "capacity_kg": 1000.0,
                "direction": "Москва-Душанбе"
            }
            
            # Пробуем различные endpoints для создания
            creation_endpoints = [
                "/transport/create",  # Найденный рабочий endpoint
                "/admin/transport",
                "/admin/transports",
                "/transport",
                "/transports"
            ]
            
            for endpoint in creation_endpoints:
                try:
                    self.log(f"   Тестирование POST {endpoint}...")
                    response = self.session.post(f"{API_BASE}{endpoint}", json=test_transport_data)
                    
                    if response.status_code in [200, 201]:
                        data = response.json()
                        self.log(f"✅ Тестовый транспорт создан через POST {endpoint}")
                        self.log(f"   📋 Данные созданного транспорта: {json.dumps(data, indent=2, ensure_ascii=False)}")
                        
                        self.add_test_result(f"Создание транспорта POST {endpoint}", True, f"Создан транспорт: {data}")
                        return data
                        
                    elif response.status_code == 404:
                        self.log(f"   ❌ Endpoint POST {endpoint} не найден (404)")
                        self.add_test_result(f"Создание транспорта POST {endpoint}", False, "Endpoint не найден (404)")
                    else:
                        self.log(f"   ❌ Ошибка создания через POST {endpoint}: {response.status_code} - {response.text}")
                        self.add_test_result(f"Создание транспорта POST {endpoint}", False, f"HTTP {response.status_code}: {response.text}")
                        
                except Exception as e:
                    self.log(f"   ❌ Исключение при POST {endpoint}: {e}")
                    self.add_test_result(f"Создание транспорта POST {endpoint}", False, f"Исключение: {str(e)}")
            
            self.log("❌ Не удалось создать тестовый транспорт через доступные endpoints")
            return None
            
        except Exception as e:
            self.log(f"❌ Исключение при создании тестового транспорта: {e}")
            self.add_test_result("Создание тестового транспорта", False, f"Исключение: {str(e)}")
            return None
    
    def test_transport_deletion(self, transport_data):
        """Тестирование удаления транспорта через различные endpoints и методы"""
        if not transport_data:
            self.log("⚠️ Нет данных транспорта для тестирования удаления")
            return False
        
        self.log("🗑️ Тестирование удаления транспорта через различные endpoints...")
        
        # Извлекаем различные возможные ID
        transport_ids = {}
        if isinstance(transport_data, list) and len(transport_data) > 0:
            sample_transport = transport_data[0]
        else:
            sample_transport = transport_data
            
        if 'id' in sample_transport:
            transport_ids['id'] = sample_transport['id']
        if 'transport_id' in sample_transport:
            transport_ids['transport_id'] = sample_transport['transport_id']
        if 'transport_number' in sample_transport:
            transport_ids['transport_number'] = sample_transport['transport_number']
        
        self.log(f"   🔑 Доступные ID для тестирования: {transport_ids}")
        
        # Список возможных endpoints для удаления
        deletion_endpoints = [
            "/admin/transports/{id}",  # Найденный рабочий endpoint
            "/admin/transport/{id}",
            "/transport/{id}",
            "/transports/{id}",
            "/admin/transport/delete/{id}",
            "/admin/transports/delete/{id}"
        ]
        
        deletion_success = False
        
        for endpoint_template in deletion_endpoints:
            for id_field, id_value in transport_ids.items():
                try:
                    endpoint = endpoint_template.replace("{id}", str(id_value))
                    self.log(f"   Тестирование DELETE {endpoint} (используя {id_field}: {id_value})...")
                    
                    response = self.session.delete(f"{API_BASE}{endpoint}")
                    
                    if response.status_code == 200:
                        self.log(f"✅ Успешное удаление через DELETE {endpoint}!")
                        try:
                            data = response.json()
                            self.log(f"   📋 Ответ сервера: {json.dumps(data, indent=2, ensure_ascii=False)}")
                        except:
                            self.log(f"   📋 Ответ сервера: {response.text}")
                        
                        self.add_test_result(f"Удаление DELETE {endpoint}", True, f"Успешно удален транспорт с {id_field}: {id_value}")
                        deletion_success = True
                        return True
                        
                    elif response.status_code == 404:
                        if "not found" in response.text.lower() or "не найден" in response.text.lower():
                            self.log(f"   ❌ Транспорт не найден через DELETE {endpoint} (возможно, неправильный ID)")
                            self.add_test_result(f"Удаление DELETE {endpoint}", False, f"Транспорт не найден с {id_field}: {id_value}")
                        else:
                            self.log(f"   ❌ Endpoint DELETE {endpoint} не найден (404)")
                            self.add_test_result(f"Удаление DELETE {endpoint}", False, "Endpoint не найден (404)")
                    else:
                        self.log(f"   ❌ Ошибка удаления через DELETE {endpoint}: {response.status_code} - {response.text}")
                        self.add_test_result(f"Удаление DELETE {endpoint}", False, f"HTTP {response.status_code}: {response.text}")
                        
                except Exception as e:
                    self.log(f"   ❌ Исключение при DELETE {endpoint}: {e}")
                    self.add_test_result(f"Удаление DELETE {endpoint}", False, f"Исключение: {str(e)}")
        
        if not deletion_success:
            self.log("❌ Не удалось удалить транспорт через доступные endpoints")
            
        return deletion_success
    
    def analyze_backend_code_structure(self):
        """Анализ структуры backend кода для понимания endpoints транспорта"""
        self.log("🔍 Анализ доступных endpoints через опции...")
        
        # Тестируем OPTIONS запросы для понимания доступных методов
        test_endpoints = [
            "/admin/transport",
            "/admin/transports",
            "/transport", 
            "/transports"
        ]
        
        for endpoint in test_endpoints:
            try:
                response = self.session.options(f"{API_BASE}{endpoint}")
                if response.status_code == 200:
                    allowed_methods = response.headers.get('Allow', 'Не указано')
                    self.log(f"   📋 {endpoint}: Разрешенные методы: {allowed_methods}")
                    self.add_test_result(f"OPTIONS {endpoint}", True, f"Разрешенные методы: {allowed_methods}")
                else:
                    self.log(f"   ❌ OPTIONS {endpoint}: {response.status_code}")
                    self.add_test_result(f"OPTIONS {endpoint}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log(f"   ❌ Исключение при OPTIONS {endpoint}: {e}")
                self.add_test_result(f"OPTIONS {endpoint}", False, f"Исключение: {str(e)}")
    
    def run_comprehensive_diagnosis(self):
        """Запуск полной диагностики проблемы удаления транспорта"""
        self.log("🚨 НАЧАЛО КРИТИЧЕСКОЙ ДИАГНОСТИКИ: Ошибка удаления транспорта из списка транспортов")
        self.log("=" * 80)
        
        # 1. Авторизация администратора
        if not self.authenticate_admin():
            self.log("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
            return False
        
        # 2. Получение списка транспортов
        transport_data = self.get_transport_list()
        
        # 3. Анализ структуры endpoints
        self.analyze_backend_code_structure()
        
        # 4. Создание тестового транспорта (если список пуст)
        if not transport_data:
            self.log("⚠️ Список транспортов пуст, создаем тестовый транспорт...")
            test_transport = self.create_test_transport()
            if test_transport:
                transport_data = [test_transport]
        
        # 5. Тестирование удаления транспорта
        if transport_data:
            self.test_transport_deletion(transport_data)
        else:
            self.log("❌ Нет транспортов для тестирования удаления")
            self.add_test_result("Тестирование удаления", False, "Нет транспортов для тестирования")
        
        # 6. Подведение итогов
        self.print_diagnosis_summary()
        
        return True
    
    def print_diagnosis_summary(self):
        """Вывод итогового отчета диагностики"""
        self.log("=" * 80)
        self.log("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ УДАЛЕНИЯ ТРАНСПОРТА")
        self.log("=" * 80)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - successful_tests
        
        self.log(f"📈 СТАТИСТИКА ТЕСТОВ:")
        self.log(f"   Всего тестов: {total_tests}")
        self.log(f"   Успешных: {successful_tests}")
        self.log(f"   Неудачных: {failed_tests}")
        self.log(f"   Процент успеха: {(successful_tests/total_tests*100):.1f}%" if total_tests > 0 else "   Процент успеха: 0%")
        
        self.log(f"\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            self.log(f"   {status} {result['test']}: {result['details']}")
        
        # Анализ и рекомендации
        self.log(f"\n🎯 АНАЛИЗ И РЕКОМЕНДАЦИИ:")
        
        # Проверяем, какие endpoints работают
        working_get_endpoints = [r for r in self.test_results if r["test"].startswith("GET") and r["success"]]
        working_delete_endpoints = [r for r in self.test_results if r["test"].startswith("Удаление DELETE") and r["success"]]
        
        if working_get_endpoints:
            self.log(f"   ✅ Найдены рабочие GET endpoints для получения транспортов")
            for endpoint in working_get_endpoints:
                self.log(f"      - {endpoint['test']}")
        else:
            self.log(f"   ❌ НЕ НАЙДЕНЫ рабочие GET endpoints для получения транспортов")
            self.log(f"      РЕКОМЕНДАЦИЯ: Проверить реализацию endpoints в backend")
        
        if working_delete_endpoints:
            self.log(f"   ✅ Найдены рабочие DELETE endpoints для удаления транспортов")
            for endpoint in working_delete_endpoints:
                self.log(f"      - {endpoint['test']}")
        else:
            self.log(f"   ❌ НЕ НАЙДЕНЫ рабочие DELETE endpoints для удаления транспортов")
            self.log(f"      РЕКОМЕНДАЦИЯ: Реализовать DELETE endpoint в backend")
        
        # Анализ полей ID
        id_field_tests = [r for r in self.test_results if "поля ID:" in r["details"]]
        if id_field_tests:
            self.log(f"   🔑 Анализ полей ID в данных транспорта:")
            for test in id_field_tests:
                self.log(f"      - {test['details']}")
        
        self.log(f"\n🚨 КОРНЕВАЯ ПРИЧИНА ПРОБЛЕМЫ:")
        if not working_get_endpoints:
            self.log(f"   1. Backend не имеет рабочих endpoints для получения списка транспортов")
        if not working_delete_endpoints:
            self.log(f"   2. Backend не имеет рабочих endpoints для удаления транспортов")
        if working_get_endpoints and not working_delete_endpoints:
            self.log(f"   3. Несоответствие между GET и DELETE endpoints")
            self.log(f"   4. Возможно, используются неправильные поля ID для удаления")
        
        self.log(f"\n💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
        self.log(f"   1. Убедиться, что в backend реализованы endpoints:")
        self.log(f"      - GET /api/admin/transport (для получения списка)")
        self.log(f"      - DELETE /api/admin/transport/{{id}} (для удаления)")
        self.log(f"   2. Проверить соответствие полей ID между frontend и backend")
        self.log(f"   3. Убедиться, что frontend отправляет правильный ID транспорта")
        self.log(f"   4. Добавить логирование в backend для отладки запросов удаления")
        
        self.log("=" * 80)
        self.log("🏁 ДИАГНОСТИКА ЗАВЕРШЕНА")

def main():
    """Основная функция для запуска диагностики"""
    tester = TransportDeletionTester()
    
    try:
        tester.run_comprehensive_diagnosis()
    except KeyboardInterrupt:
        tester.log("⚠️ Диагностика прервана пользователем")
    except Exception as e:
        tester.log(f"❌ Критическая ошибка во время диагностики: {e}")
    
    return tester.test_results

if __name__ == "__main__":
    main()