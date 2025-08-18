#!/usr/bin/env python3
"""
УГЛУБЛЕННАЯ ДИАГНОСТИКА: Проблема с удалением груза 100008/01 и 100008/02
Исследует почему при удалении груза 100004 удаляется груз 100012/02
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"
ADMIN_PHONE = "+79999888777"
ADMIN_PASSWORD = "admin123"

class CargoIDMismatchDiagnostic:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        login_data = {
            "phone": ADMIN_PHONE,
            "password": ADMIN_PASSWORD
        }
        
        response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data.get("access_token")
            self.session.headers.update({
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            })
            return True
        return False
    
    def get_all_placement_cargo(self):
        """Получить все грузы в размещении с детальной информацией"""
        print("🔍 ПОЛУЧЕНИЕ ВСЕХ ГРУЗОВ В РАЗМЕЩЕНИИ...")
        
        response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement")
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            
            print(f"   📋 Всего грузов в размещении: {len(items)}")
            
            # Группируем по ID для поиска дубликатов
            id_groups = {}
            for item in items:
                cargo_id = item.get("id")
                if cargo_id not in id_groups:
                    id_groups[cargo_id] = []
                id_groups[cargo_id].append(item)
            
            print(f"   📋 Уникальных ID: {len(id_groups)}")
            
            # Ищем дубликаты ID
            duplicates = {k: v for k, v in id_groups.items() if len(v) > 1}
            if duplicates:
                print(f"   ⚠️ НАЙДЕНЫ ДУБЛИКАТЫ ID:")
                for cargo_id, cargo_list in duplicates.items():
                    print(f"      ID {cargo_id} используется {len(cargo_list)} раз:")
                    for i, cargo in enumerate(cargo_list):
                        print(f"         {i+1}. Номер: {cargo.get('cargo_number')}, Отправитель: {cargo.get('sender_full_name')}")
            
            # Ищем конкретные грузы
            target_cargo = {}
            for item in items:
                cargo_number = item.get("cargo_number")
                if cargo_number in ["100008/01", "100008/02", "100012/02"]:
                    target_cargo[cargo_number] = item
                    print(f"   🎯 Найден целевой груз {cargo_number}:")
                    print(f"      ID: {item.get('id')}")
                    print(f"      Отправитель: {item.get('sender_full_name')}")
                    print(f"      Получатель: {item.get('recipient_full_name')}")
                    print(f"      Статус обработки: {item.get('processing_status')}")
                    print(f"      Статус оплаты: {item.get('payment_status')}")
            
            return items, target_cargo, id_groups
        
        return [], {}, {}
    
    def test_specific_cargo_deletion(self, target_cargo):
        """Тестирование удаления конкретных грузов"""
        print(f"\n🗑️ ТЕСТИРОВАНИЕ УДАЛЕНИЯ КОНКРЕТНЫХ ГРУЗОВ...")
        
        if "100008/01" in target_cargo:
            cargo_100008_01 = target_cargo["100008/01"]
            cargo_id = cargo_100008_01.get("id")
            
            print(f"\n   🎯 УДАЛЕНИЕ ГРУЗА 100008/01 (ID: {cargo_id}):")
            
            # Запоминаем состояние до удаления
            print(f"      📋 Состояние до удаления:")
            print(f"         Номер груза: {cargo_100008_01.get('cargo_number')}")
            print(f"         ID: {cargo_id}")
            print(f"         Отправитель: {cargo_100008_01.get('sender_full_name')}")
            
            # Выполняем удаление
            response = self.session.delete(f"{BACKEND_URL}/operator/cargo/{cargo_id}/remove-from-placement")
            print(f"      🗑️ DELETE /operator/cargo/{cargo_id}/remove-from-placement")
            print(f"      📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"      📄 Ответ сервера: {json.dumps(response_data, indent=8, ensure_ascii=False)}")
                
                deleted_cargo_number = response_data.get("cargo_number")
                if deleted_cargo_number != "100008/01":
                    print(f"      🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА!")
                    print(f"      ❌ Запросили удаление: 100008/01 (ID: {cargo_id})")
                    print(f"      ❌ Фактически удален: {deleted_cargo_number}")
                    print(f"      🔍 Это указывает на проблему с маппингом ID -> номер груза")
                    
                    return True  # Проблема подтверждена
            else:
                print(f"      ❌ Ошибка удаления: {response.text}")
        
        return False
    
    def investigate_id_mapping_issue(self, items, target_cargo):
        """Исследование проблемы маппинга ID на номера грузов"""
        print(f"\n🔬 ИССЛЕДОВАНИЕ ПРОБЛЕМЫ МАППИНГА ID -> НОМЕР ГРУЗА...")
        
        # Создаем карту ID -> список номеров грузов
        id_to_numbers = {}
        for item in items:
            cargo_id = item.get("id")
            cargo_number = item.get("cargo_number")
            
            if cargo_id not in id_to_numbers:
                id_to_numbers[cargo_id] = []
            id_to_numbers[cargo_id].append(cargo_number)
        
        # Ищем ID, которые связаны с несколькими номерами
        problematic_ids = {k: v for k, v in id_to_numbers.items() if len(set(v)) > 1}
        
        if problematic_ids:
            print(f"   🚨 НАЙДЕНЫ ПРОБЛЕМНЫЕ ID (один ID -> несколько номеров):")
            for cargo_id, numbers in problematic_ids.items():
                unique_numbers = list(set(numbers))
                print(f"      ID {cargo_id} связан с номерами: {unique_numbers}")
                
                # Проверяем, есть ли среди них наши целевые грузы
                target_numbers = ["100008/01", "100008/02", "100012/02"]
                intersection = set(unique_numbers) & set(target_numbers)
                if intersection:
                    print(f"         ⚠️ Включает целевые грузы: {list(intersection)}")
        else:
            print(f"   ✅ Проблемных ID не найдено - каждый ID связан только с одним номером")
        
        # Создаем обратную карту номер -> список ID
        number_to_ids = {}
        for item in items:
            cargo_id = item.get("id")
            cargo_number = item.get("cargo_number")
            
            if cargo_number not in number_to_ids:
                number_to_ids[cargo_number] = []
            number_to_ids[cargo_number].append(cargo_id)
        
        # Ищем номера, которые связаны с несколькими ID
        problematic_numbers = {k: v for k, v in number_to_ids.items() if len(set(v)) > 1}
        
        if problematic_numbers:
            print(f"\n   🚨 НАЙДЕНЫ ПРОБЛЕМНЫЕ НОМЕРА (один номер -> несколько ID):")
            for cargo_number, ids in problematic_numbers.items():
                unique_ids = list(set(ids))
                print(f"      Номер {cargo_number} связан с ID: {unique_ids}")
        else:
            print(f"   ✅ Проблемных номеров не найдено - каждый номер связан только с одним ID")
        
        # Специальная проверка для наших целевых грузов
        print(f"\n   🎯 ДЕТАЛЬНАЯ ПРОВЕРКА ЦЕЛЕВЫХ ГРУЗОВ:")
        target_numbers = ["100008/01", "100008/02", "100012/02"]
        
        for number in target_numbers:
            if number in number_to_ids:
                ids = list(set(number_to_ids[number]))
                print(f"      {number} -> ID: {ids}")
                
                if len(ids) > 1:
                    print(f"         ⚠️ ПРОБЛЕМА: Один номер связан с несколькими ID!")
            else:
                print(f"      {number} -> НЕ НАЙДЕН")
        
        return problematic_ids, problematic_numbers
    
    def check_database_consistency(self):
        """Проверка консистентности данных в базе"""
        print(f"\n🗄️ ПРОВЕРКА КОНСИСТЕНТНОСТИ ДАННЫХ...")
        
        # Пытаемся получить информацию о структуре данных
        endpoints_to_check = [
            "/admin/cargo",
            "/operator/cargo",
            "/admin/system/stats"
        ]
        
        for endpoint in endpoints_to_check:
            try:
                response = self.session.get(f"{BACKEND_URL}{endpoint}")
                print(f"   📊 {endpoint} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and "items" in data:
                        items = data["items"]
                        print(f"      📋 Найдено записей: {len(items)}")
                    elif isinstance(data, list):
                        print(f"      📋 Найдено записей: {len(data)}")
                    else:
                        print(f"      📋 Структура данных: {type(data)}")
                        
            except Exception as e:
                print(f"   ❌ Ошибка при проверке {endpoint}: {e}")
    
    def run_investigation(self):
        """Запуск полного исследования"""
        print("=" * 80)
        print("🔬 УГЛУБЛЕННАЯ ДИАГНОСТИКА ПРОБЛЕМЫ УДАЛЕНИЯ ГРУЗОВ")
        print("=" * 80)
        
        # Авторизация
        if not self.authenticate_admin():
            print("❌ Ошибка авторизации")
            return False
        
        # Получение всех грузов в размещении
        items, target_cargo, id_groups = self.get_all_placement_cargo()
        
        # Исследование проблемы маппинга
        problematic_ids, problematic_numbers = self.investigate_id_mapping_issue(items, target_cargo)
        
        # Тестирование удаления
        deletion_issue_confirmed = self.test_specific_cargo_deletion(target_cargo)
        
        # Проверка консистентности базы данных
        self.check_database_consistency()
        
        # Итоговый отчет
        print(f"\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ИССЛЕДОВАНИЯ")
        print("=" * 80)
        
        print(f"📋 Всего грузов в размещении: {len(items)}")
        print(f"📋 Уникальных ID: {len(id_groups)}")
        print(f"🎯 Найдено целевых грузов: {len(target_cargo)}")
        
        if problematic_ids:
            print(f"🚨 Проблемные ID (один ID -> несколько номеров): {len(problematic_ids)}")
        
        if problematic_numbers:
            print(f"🚨 Проблемные номера (один номер -> несколько ID): {len(problematic_numbers)}")
        
        if deletion_issue_confirmed:
            print(f"🚨 ПОДТВЕРЖДЕНА ПРОБЛЕМА: При удалении груза по ID удаляется неправильный груз!")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ ДЛЯ ИСПРАВЛЕНИЯ:")
        print(f"   1. Проверить логику поиска груза по ID в backend коде")
        print(f"   2. Убедиться что ID грузов уникальны в базе данных")
        print(f"   3. Проверить индексы MongoDB для коллекций грузов")
        print(f"   4. Исследовать возможные race conditions при создании/удалении грузов")
        print(f"   5. Добавить дополнительное логирование операций удаления")
        
        return True

def main():
    diagnostic = CargoIDMismatchDiagnostic()
    
    try:
        success = diagnostic.run_investigation()
        
        if success:
            print(f"\n✅ Исследование завершено успешно")
            sys.exit(0)
        else:
            print(f"\n❌ Исследование завершено с ошибками")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()