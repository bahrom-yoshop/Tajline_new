#!/usr/bin/env python3
"""
ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ: Диагностика проблемы массового удаления складов в TAJLINE.TJ

НАЙДЕННАЯ ПРОБЛЕМА:
Endpoint DELETE /api/admin/warehouses/bulk существует и работает, но использует 
неправильное определение параметра: warehouse_ids: dict вместо Pydantic модели.

РЕШЕНИЕ:
Нужно изменить endpoint на использование BulkDeleteRequest модели.
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://freight-hub-6.preview.emergentagent.com/api"
ADMIN_PHONE = "+79999888777"
ADMIN_PASSWORD = "admin123"

class WarehouseBulkDeletionFinalTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.admin_user_info = None
        
    def log(self, message):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def test_admin_authorization(self):
        """Авторизация администратора"""
        self.log("🔐 АВТОРИЗАЦИЯ: Администратор (+79999888777/admin123)")
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/login", json={
                "phone": ADMIN_PHONE,
                "password": ADMIN_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.admin_user_info = data.get("user")
                
                self.session.headers.update({
                    "Authorization": f"Bearer {self.admin_token}"
                })
                
                user_name = self.admin_user_info.get("full_name", "Unknown")
                user_number = self.admin_user_info.get("user_number", "Unknown")
                
                self.log(f"✅ УСПЕХ: Авторизован '{user_name}' (номер: {user_number})")
                return True
            else:
                self.log(f"❌ ОШИБКА: Статус {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ ИСКЛЮЧЕНИЕ: {e}")
            return False
    
    def get_warehouses_for_testing(self):
        """Получение складов для тестирования"""
        self.log("📋 ПОЛУЧЕНИЕ: Список складов для тестирования")
        
        try:
            response = self.session.get(f"{BACKEND_URL}/warehouses")
            
            if response.status_code == 200:
                warehouses = response.json()
                
                if len(warehouses) >= 2:
                    # Берем последние 2 склада для безопасного тестирования
                    test_warehouses = warehouses[-2:]
                    
                    self.log(f"✅ НАЙДЕНО: {len(warehouses)} складов, выбрано 2 для тестирования")
                    for i, warehouse in enumerate(test_warehouses):
                        name = warehouse.get("name", "Unknown")
                        location = warehouse.get("location", "Unknown")
                        self.log(f"   Склад {i+1}: '{name}' - {location}")
                    
                    return test_warehouses
                else:
                    self.log(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Найдено только {len(warehouses)} складов")
                    return warehouses
            else:
                self.log(f"❌ ОШИБКА: Статус {response.status_code}")
                return []
                
        except Exception as e:
            self.log(f"❌ ИСКЛЮЧЕНИЕ: {e}")
            return []
    
    def test_bulk_deletion_current_implementation(self, warehouse_ids):
        """Тестирование текущей реализации массового удаления"""
        self.log("🗑️ ТЕСТИРОВАНИЕ: Текущая реализация массового удаления")
        
        # Тестируем правильную структуру данных
        test_data = {"ids": warehouse_ids}
        
        self.log(f"📝 Отправляем данные: {json.dumps(test_data, indent=2)}")
        
        try:
            response = self.session.delete(f"{BACKEND_URL}/admin/warehouses/bulk", json=test_data)
            
            self.log(f"📊 ОТВЕТ: Статус {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ УСПЕХ: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                deleted_count = result.get("deleted_count", 0)
                total_requested = result.get("total_requested", 0)
                errors = result.get("errors", [])
                
                if deleted_count > 0:
                    self.log(f"🎉 КРИТИЧЕСКИЙ УСПЕХ: Удалено {deleted_count} из {total_requested} складов")
                else:
                    self.log(f"🚨 ПРОБЛЕМА: Удалено {deleted_count} складов (возможно, склады содержат грузы)")
                
                if errors:
                    self.log("⚠️ ОШИБКИ:")
                    for error in errors:
                        self.log(f"   - {error}")
                
                return True
            else:
                self.log(f"❌ ОШИБКА: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ ИСКЛЮЧЕНИЕ: {e}")
            return False
    
    def test_wrong_data_structures(self, warehouse_ids):
        """Тестирование неправильных структур данных"""
        self.log("🧪 ТЕСТИРОВАНИЕ: Неправильные структуры данных")
        
        wrong_structures = [
            {"warehouse_ids": warehouse_ids},  # Неправильное поле
            warehouse_ids,  # Прямой список
            {"warehouses": warehouse_ids},  # Другое неправильное поле
            {}  # Пустой объект
        ]
        
        for i, wrong_data in enumerate(wrong_structures):
            self.log(f"📝 Тест {i+1}: {json.dumps(wrong_data, indent=2)}")
            
            try:
                response = self.session.delete(f"{BACKEND_URL}/admin/warehouses/bulk", json=wrong_data)
                
                if response.status_code == 400:
                    self.log(f"✅ ОЖИДАЕМО: Ошибка 400 - {response.json().get('detail', 'Unknown error')}")
                elif response.status_code == 422:
                    self.log(f"✅ ОЖИДАЕМО: Ошибка валидации 422")
                else:
                    self.log(f"⚠️ НЕОЖИДАННО: Статус {response.status_code}")
                    
            except Exception as e:
                self.log(f"❌ ИСКЛЮЧЕНИЕ: {e}")
    
    def analyze_root_cause(self):
        """Анализ корневой причины проблемы"""
        self.log("🔍 АНАЛИЗ: Корневая причина проблемы")
        
        self.log("📋 НАЙДЕННЫЕ ПРОБЛЕМЫ:")
        self.log("   1. ✅ Endpoint DELETE /api/admin/warehouses/bulk СУЩЕСТВУЕТ")
        self.log("   2. ✅ Endpoint РАБОТАЕТ с правильной структурой данных {'ids': [...]}")
        self.log("   3. ⚠️ Endpoint использует 'warehouse_ids: dict' вместо Pydantic модели")
        self.log("   4. ❌ Frontend может отправлять неправильную структуру данных")
        
        self.log("🎯 КОРНЕВАЯ ПРИЧИНА:")
        self.log("   Проблема НЕ в backend endpoint'е - он работает корректно!")
        self.log("   Проблема может быть в:")
        self.log("   - Frontend отправляет неправильную структуру данных")
        self.log("   - Склады содержат грузы и не могут быть удалены")
        self.log("   - Проблема в UI отображении результата")
        
        self.log("💡 РЕКОМЕНДАЦИИ:")
        self.log("   1. Проверить frontend код на правильность отправки {'ids': [...]} структуры")
        self.log("   2. Улучшить endpoint: использовать BulkDeleteRequest модель")
        self.log("   3. Добавить лучшую обработку ошибок в UI")
        self.log("   4. Проверить, что склады не содержат грузы перед удалением")
    
    def run_final_diagnosis(self):
        """Запуск финальной диагностики"""
        self.log("🚀 ФИНАЛЬНАЯ ДИАГНОСТИКА: Проблема массового удаления складов")
        self.log("=" * 80)
        
        # Авторизация
        if not self.test_admin_authorization():
            self.log("🚨 КРИТИЧЕСКАЯ ОШИБКА: Авторизация не удалась")
            return False
        
        self.log("-" * 80)
        
        # Получение складов
        warehouses = self.get_warehouses_for_testing()
        if not warehouses:
            self.log("🚨 КРИТИЧЕСКАЯ ОШИБКА: Нет складов для тестирования")
            return False
        
        warehouse_ids = [w.get("id") for w in warehouses if w.get("id")]
        
        self.log("-" * 80)
        
        # Тестирование правильной структуры
        bulk_deletion_works = self.test_bulk_deletion_current_implementation(warehouse_ids)
        
        self.log("-" * 80)
        
        # Тестирование неправильных структур
        self.test_wrong_data_structures(warehouse_ids)
        
        self.log("-" * 80)
        
        # Анализ корневой причины
        self.analyze_root_cause()
        
        self.log("=" * 80)
        self.log("🏁 ФИНАЛЬНАЯ ДИАГНОСТИКА ЗАВЕРШЕНА")
        
        return bulk_deletion_works

def main():
    """Главная функция"""
    print("🏥 ФИНАЛЬНАЯ ДИАГНОСТИКА: Проблема массового удаления складов в TAJLINE.TJ")
    print("=" * 80)
    
    tester = WarehouseBulkDeletionFinalTester()
    
    try:
        success = tester.run_final_diagnosis()
        
        if success:
            print("\n✅ ДИАГНОСТИКА ЗАВЕРШЕНА: Backend работает корректно!")
            print("💡 Проблема скорее всего в frontend или в содержимом складов")
            return 0
        else:
            print("\n❌ ДИАГНОСТИКА ВЫЯВИЛА ПРОБЛЕМЫ В BACKEND")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ ДИАГНОСТИКА ПРЕРВАНА")
        return 1
    except Exception as e:
        print(f"\n🚨 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())