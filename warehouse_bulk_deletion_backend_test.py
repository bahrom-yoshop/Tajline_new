#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Диагностика проблемы массового удаления складов в TAJLINE.TJ

ПРОБЛЕМА:
При массовом удалении складов из списка складов система не удаляет склады, 
но пишет "успешно удалено складов (0)".

ПЛАН ДИАГНОСТИКИ:
1) Авторизация администратора (+79999888777/admin123)
2) Получение списка складов (GET /api/admin/warehouses, GET /api/warehouses)
3) Поиск endpoint для массового удаления складов
4) Тестирование массового удаления складов
5) Проверка единичного удаления складов
6) Анализ backend кода для поиска проблемы
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"
ADMIN_PHONE = "+79999888777"
ADMIN_PASSWORD = "admin123"

class WarehouseBulkDeletionTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.admin_user_info = None
        self.warehouses = []
        
    def log(self, message):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def test_admin_authorization(self):
        """1. КРИТИЧЕСКАЯ ПРОВЕРКА: Авторизация администратора"""
        self.log("🔐 ТЕСТИРОВАНИЕ: Авторизация администратора (+79999888777/admin123)")
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/login", json={
                "phone": ADMIN_PHONE,
                "password": ADMIN_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.admin_user_info = data.get("user")
                
                # Устанавливаем заголовок авторизации
                self.session.headers.update({
                    "Authorization": f"Bearer {self.admin_token}"
                })
                
                user_name = self.admin_user_info.get("full_name", "Unknown")
                user_number = self.admin_user_info.get("user_number", "Unknown")
                user_role = self.admin_user_info.get("role", "Unknown")
                
                self.log(f"✅ УСПЕХ: Авторизация администратора '{user_name}' (номер: {user_number}), роль: {user_role}")
                return True
            else:
                self.log(f"❌ ОШИБКА: Авторизация не удалась. Статус: {response.status_code}")
                self.log(f"Ответ: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ ИСКЛЮЧЕНИЕ при авторизации: {e}")
            return False
    
    def test_get_warehouses_list(self):
        """2. КРИТИЧЕСКАЯ ПРОВЕРКА: Получение списка складов"""
        self.log("📋 ТЕСТИРОВАНИЕ: Получение списка складов")
        
        # Тестируем разные endpoints для получения складов
        endpoints_to_test = [
            "/admin/warehouses",
            "/warehouses",
            "/operator/warehouses"
        ]
        
        successful_endpoint = None
        
        for endpoint in endpoints_to_test:
            try:
                self.log(f"🔍 Проверяем endpoint: GET {endpoint}")
                response = self.session.get(f"{BACKEND_URL}{endpoint}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Проверяем структуру ответа
                    if isinstance(data, list):
                        warehouses = data
                    elif isinstance(data, dict) and "items" in data:
                        warehouses = data["items"]
                    elif isinstance(data, dict) and "warehouses" in data:
                        warehouses = data["warehouses"]
                    else:
                        warehouses = []
                    
                    if warehouses:
                        self.warehouses = warehouses
                        successful_endpoint = endpoint
                        self.log(f"✅ УСПЕХ: Найдено {len(warehouses)} складов через {endpoint}")
                        
                        # Показываем первые несколько складов для анализа
                        for i, warehouse in enumerate(warehouses[:3]):
                            warehouse_id = warehouse.get("id", "Unknown")
                            warehouse_name = warehouse.get("name", "Unknown")
                            warehouse_location = warehouse.get("location", "Unknown")
                            self.log(f"   Склад {i+1}: ID={warehouse_id}, Название='{warehouse_name}', Локация='{warehouse_location}'")
                        
                        break
                    else:
                        self.log(f"⚠️ Endpoint {endpoint} вернул пустой список складов")
                else:
                    self.log(f"❌ Endpoint {endpoint} вернул статус {response.status_code}")
                    
            except Exception as e:
                self.log(f"❌ ИСКЛЮЧЕНИЕ при запросе {endpoint}: {e}")
        
        if successful_endpoint:
            self.log(f"🎯 РЕЗУЛЬТАТ: Успешно получен список складов через {successful_endpoint}")
            return True
        else:
            self.log("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить список складов ни через один endpoint")
            return False
    
    def test_bulk_deletion_endpoints(self):
        """3. КРИТИЧЕСКАЯ ПРОВЕРКА: Поиск и тестирование endpoints массового удаления складов"""
        self.log("🗑️ ТЕСТИРОВАНИЕ: Поиск endpoints для массового удаления складов")
        
        if not self.warehouses:
            self.log("❌ ОШИБКА: Нет складов для тестирования удаления")
            return False
        
        # Endpoints для тестирования массового удаления
        bulk_deletion_endpoints = [
            "/admin/warehouses/bulk",
            "/warehouses/bulk",
            "/admin/warehouses/bulk-delete",
            "/warehouses/bulk-delete"
        ]
        
        # Берем первые 2-3 склада для тестирования (безопасно)
        test_warehouse_ids = [w.get("id") for w in self.warehouses[:2] if w.get("id")]
        
        if not test_warehouse_ids:
            self.log("❌ ОШИБКА: Не найдены ID складов для тестирования")
            return False
        
        self.log(f"🎯 Тестируем удаление складов с ID: {test_warehouse_ids}")
        
        # Тестируем разные структуры данных
        test_data_structures = [
            {"ids": test_warehouse_ids},
            {"warehouse_ids": test_warehouse_ids},
            test_warehouse_ids,  # Прямой список
            {"warehouses": test_warehouse_ids}
        ]
        
        found_working_endpoint = False
        
        for endpoint in bulk_deletion_endpoints:
            self.log(f"🔍 Тестируем endpoint: DELETE {endpoint}")
            
            for i, test_data in enumerate(test_data_structures):
                try:
                    self.log(f"   📝 Структура данных {i+1}: {json.dumps(test_data, indent=2)}")
                    
                    response = self.session.delete(f"{BACKEND_URL}{endpoint}", json=test_data)
                    
                    self.log(f"   📊 Ответ: Статус {response.status_code}")
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        self.log(f"   ✅ УСПЕХ: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                        found_working_endpoint = True
                        
                        # Проверяем, действительно ли удалились склады
                        deleted_count = response_data.get("deleted_count", 0)
                        if deleted_count > 0:
                            self.log(f"   🎉 КРИТИЧЕСКИЙ УСПЕХ: Удалено {deleted_count} складов!")
                        else:
                            self.log(f"   🚨 ПРОБЛЕМА НАЙДЕНА: Endpoint работает, но deleted_count = {deleted_count}")
                        
                    elif response.status_code == 404:
                        self.log(f"   ❌ Endpoint не найден (404)")
                    elif response.status_code == 422:
                        self.log(f"   ⚠️ Ошибка валидации (422): {response.text}")
                    else:
                        self.log(f"   ❌ Ошибка {response.status_code}: {response.text}")
                        
                except Exception as e:
                    self.log(f"   ❌ ИСКЛЮЧЕНИЕ: {e}")
        
        if not found_working_endpoint:
            self.log("🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: Не найден рабочий endpoint для массового удаления складов")
            return False
        
        return True
    
    def test_individual_deletion(self):
        """4. КРИТИЧЕСКАЯ ПРОВЕРКА: Тестирование единичного удаления складов"""
        self.log("🗑️ ТЕСТИРОВАНИЕ: Единичное удаление складов")
        
        if not self.warehouses:
            self.log("❌ ОШИБКА: Нет складов для тестирования единичного удаления")
            return False
        
        # Endpoints для единичного удаления
        individual_deletion_endpoints = [
            "/admin/warehouses/{id}",
            "/warehouses/{id}"
        ]
        
        # Берем последний склад для тестирования единичного удаления
        test_warehouse = self.warehouses[-1]
        test_warehouse_id = test_warehouse.get("id")
        test_warehouse_name = test_warehouse.get("name", "Unknown")
        
        if not test_warehouse_id:
            self.log("❌ ОШИБКА: Не найден ID склада для единичного удаления")
            return False
        
        self.log(f"🎯 Тестируем единичное удаление склада: ID={test_warehouse_id}, Название='{test_warehouse_name}'")
        
        found_working_endpoint = False
        
        for endpoint_template in individual_deletion_endpoints:
            endpoint = endpoint_template.format(id=test_warehouse_id)
            self.log(f"🔍 Тестируем endpoint: DELETE {endpoint}")
            
            try:
                response = self.session.delete(f"{BACKEND_URL}{endpoint}")
                
                self.log(f"📊 Ответ: Статус {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    self.log(f"✅ УСПЕХ: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                    found_working_endpoint = True
                    
                    # Проверяем результат удаления
                    if "deleted" in str(response_data).lower() or "success" in str(response_data).lower():
                        self.log(f"🎉 КРИТИЧЕСКИЙ УСПЕХ: Склад успешно удален!")
                    else:
                        self.log(f"⚠️ Возможная проблема: Неясный результат удаления")
                        
                elif response.status_code == 404:
                    self.log(f"❌ Склад не найден или endpoint не существует (404)")
                elif response.status_code == 403:
                    self.log(f"❌ Недостаточно прав для удаления (403)")
                else:
                    self.log(f"❌ Ошибка {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log(f"❌ ИСКЛЮЧЕНИЕ: {e}")
        
        if found_working_endpoint:
            self.log("✅ РЕЗУЛЬТАТ: Найден рабочий endpoint для единичного удаления складов")
            return True
        else:
            self.log("❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Не найден рабочий endpoint для единичного удаления складов")
            return False
    
    def analyze_backend_code_structure(self):
        """5. АНАЛИЗ: Поиск проблем в backend коде"""
        self.log("🔍 АНАЛИЗ: Поиск проблем в структуре backend кода")
        
        # Проверяем, есть ли endpoints в коде
        try:
            with open("/app/backend/server.py", "r", encoding="utf-8") as f:
                backend_code = f.read()
            
            # Ищем endpoints связанные со складами
            warehouse_endpoints = []
            
            # Поиск DELETE endpoints для складов
            import re
            delete_patterns = [
                r'@app\.delete\(["\'].*warehouses.*["\'].*\)',
                r'async def.*delete.*warehouse.*\(',
                r'def.*delete.*warehouse.*\('
            ]
            
            for pattern in delete_patterns:
                matches = re.findall(pattern, backend_code, re.IGNORECASE)
                warehouse_endpoints.extend(matches)
            
            if warehouse_endpoints:
                self.log("✅ НАЙДЕНЫ endpoints для удаления складов в backend коде:")
                for endpoint in warehouse_endpoints:
                    self.log(f"   📝 {endpoint}")
            else:
                self.log("🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: НЕ НАЙДЕНЫ endpoints для удаления складов в backend коде!")
                self.log("   Это объясняет, почему массовое удаление не работает")
            
            # Ищем модели для массового удаления
            bulk_delete_patterns = [
                r'class.*BulkDelete.*Request.*\(',
                r'class.*Warehouse.*Delete.*\(',
                r'warehouse_ids.*List\[str\]'
            ]
            
            bulk_models = []
            for pattern in bulk_delete_patterns:
                matches = re.findall(pattern, backend_code, re.IGNORECASE)
                bulk_models.extend(matches)
            
            if bulk_models:
                self.log("✅ НАЙДЕНЫ модели для массового удаления:")
                for model in bulk_models:
                    self.log(f"   📝 {model}")
            else:
                self.log("⚠️ НЕ НАЙДЕНЫ специальные модели для массового удаления складов")
            
            return True
            
        except Exception as e:
            self.log(f"❌ ОШИБКА при анализе backend кода: {e}")
            return False
    
    def run_comprehensive_diagnosis(self):
        """Запуск полной диагностики проблемы массового удаления складов"""
        self.log("🚀 НАЧАЛО КРИТИЧЕСКОЙ ДИАГНОСТИКИ: Проблема массового удаления складов в TAJLINE.TJ")
        self.log("=" * 80)
        
        # Этап 1: Авторизация администратора
        if not self.test_admin_authorization():
            self.log("🚨 КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
            return False
        
        self.log("-" * 80)
        
        # Этап 2: Получение списка складов
        if not self.test_get_warehouses_list():
            self.log("🚨 КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить список складов")
            return False
        
        self.log("-" * 80)
        
        # Этап 3: Тестирование массового удаления
        bulk_deletion_works = self.test_bulk_deletion_endpoints()
        
        self.log("-" * 80)
        
        # Этап 4: Тестирование единичного удаления
        individual_deletion_works = self.test_individual_deletion()
        
        self.log("-" * 80)
        
        # Этап 5: Анализ backend кода
        self.analyze_backend_code_structure()
        
        self.log("=" * 80)
        
        # Финальный анализ
        self.log("🎯 ФИНАЛЬНЫЙ АНАЛИЗ ДИАГНОСТИКИ:")
        
        if bulk_deletion_works:
            self.log("✅ Массовое удаление складов: РАБОТАЕТ")
        else:
            self.log("❌ Массовое удаление складов: НЕ РАБОТАЕТ")
        
        if individual_deletion_works:
            self.log("✅ Единичное удаление складов: РАБОТАЕТ")
        else:
            self.log("❌ Единичное удаление складов: НЕ РАБОТАЕТ")
        
        # Определяем корневую причину
        if not bulk_deletion_works and not individual_deletion_works:
            self.log("🚨 КОРНЕВАЯ ПРИЧИНА: Отсутствуют endpoints для удаления складов в backend")
        elif not bulk_deletion_works and individual_deletion_works:
            self.log("🚨 КОРНЕВАЯ ПРИЧИНА: Отсутствует endpoint для массового удаления складов")
        elif bulk_deletion_works:
            self.log("⚠️ ВОЗМОЖНАЯ ПРИЧИНА: Проблема в frontend или в структуре данных запроса")
        
        self.log("🏁 ДИАГНОСТИКА ЗАВЕРШЕНА")
        return True

def main():
    """Главная функция для запуска диагностики"""
    print("🏥 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема массового удаления складов в TAJLINE.TJ")
    print("=" * 80)
    
    tester = WarehouseBulkDeletionTester()
    
    try:
        success = tester.run_comprehensive_diagnosis()
        
        if success:
            print("\n✅ ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО")
            return 0
        else:
            print("\n❌ ДИАГНОСТИКА ЗАВЕРШЕНА С ОШИБКАМИ")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ ДИАГНОСТИКА ПРЕРВАНА ПОЛЬЗОВАТЕЛЕМ")
        return 1
    except Exception as e:
        print(f"\n🚨 КРИТИЧЕСКАЯ ОШИБКА ДИАГНОСТИКИ: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())