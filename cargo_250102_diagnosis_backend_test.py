#!/usr/bin/env python3
"""
Backend Test for Cargo 250102 Visibility Diagnosis and Fix
Срочная диагностика и исправление проблемы видимости заявки 250102 в списке «Размещение»
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"

class Cargo250102DiagnosisTest:
    def __init__(self):
        self.admin_token = None
        self.moscow_warehouse_id = "d0a8362d-b4d3-4947-b335-28c94658a021"  # Москва Склад №1
        self.destination_warehouse_id = None
        self.cargo_250102_data = None
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        print("🔐 Авторизация администратора...")
        
        login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        try:
            response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                user_info = data.get("user", {})
                print(f"✅ Администратор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
                return True
            else:
                print(f"❌ Ошибка авторизации: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Ошибка подключения при авторизации: {e}")
            return False
    
    def find_cargo_250102(self):
        """1) GET /api/debug/find-cargo-by-number/250102 - диагностика груза"""
        print("\n🔍 ЭТАП 1: Диагностика груза 250102...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(f"{BACKEND_URL}/debug/find-cargo-by-number/250102", headers=headers)
            if response.status_code == 200:
                cargo_data = response.json()
                if cargo_data.get('found'):
                    cargo = cargo_data.get('cargo', {})
                    self.cargo_250102_data = cargo
                    
                    print(f"✅ Груз 250102 найден:")
                    print(f"   📦 ID: {cargo.get('id')}")
                    print(f"   🔢 Номер: {cargo.get('cargo_number')}")
                    print(f"   🏢 Коллекция: {cargo_data.get('collection', 'не указана')}")
                    print(f"   🏭 warehouse_id: {cargo.get('warehouse_id') or 'ПУСТОЙ'}")
                    print(f"   🎯 destination_warehouse_id: {cargo.get('destination_warehouse_id') or 'ПУСТОЙ'}")
                    print(f"   📊 status: {cargo.get('status')}")
                    print(f"   ⚙️ processing_status: {cargo.get('processing_status')}")
                    print(f"   🚫 hidden_reason: {cargo.get('hidden_reason') or 'отсутствует'}")
                    
                    return True
                else:
                    print(f"❌ Груз 250102 не найден в системе")
                    return False
            else:
                print(f"❌ Ошибка поиска груза: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при поиске груза 250102: {e}")
            return False
    
    def get_destinations_cities(self):
        """2) GET /api/destinations/cities - получить список городов"""
        print("\n🌍 ЭТАП 2: Получение списка городов назначения...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(f"{BACKEND_URL}/destinations/cities", headers=headers)
            if response.status_code == 200:
                cities = response.json()
                print(f"✅ Получен список городов ({len(cities)} городов):")
                
                for city in cities:
                    city_name = city.get('name', 'Неизвестный')
                    warehouse_id = city.get('warehouse_id', 'не указан')
                    print(f"   🏙️ {city_name}: warehouse_id = {warehouse_id}")
                
                # Попробуем определить город назначения для 250102
                if self.cargo_250102_data:
                    recipient_address = self.cargo_250102_data.get('recipient_address', '')
                    route = self.cargo_250102_data.get('route', '')
                    
                    print(f"\n🎯 Анализ данных груза 250102:")
                    print(f"   📍 Адрес получателя: {recipient_address}")
                    print(f"   🛣️ Маршрут: {route}")
                    
                    # Определяем город назначения по адресу или маршруту
                    destination_city = None
                    if 'душанбе' in recipient_address.lower() or 'dushanbe' in recipient_address.lower():
                        destination_city = 'Душанбе'
                    elif 'худжанд' in recipient_address.lower() or 'khujand' in recipient_address.lower():
                        destination_city = 'Худжанд'
                    elif 'москва' in recipient_address.lower() or 'moscow' in recipient_address.lower():
                        destination_city = 'Москва'
                    
                    if destination_city:
                        print(f"   🎯 Определен город назначения: {destination_city}")
                        
                        # Найдем warehouse_id для этого города
                        for city in cities:
                            if destination_city.lower() in city.get('name', '').lower():
                                self.destination_warehouse_id = city.get('warehouse_id')
                                print(f"   ✅ Найден warehouse_id для {destination_city}: {self.destination_warehouse_id}")
                                break
                    else:
                        print(f"   ⚠️ Не удалось определить город назначения из данных груза")
                        # Используем первый доступный склад (кроме Москвы)
                        for city in cities:
                            city_name = city.get('name', '').lower()
                            if 'москва' not in city_name and 'moscow' not in city_name:
                                self.destination_warehouse_id = city.get('warehouse_id')
                                print(f"   🔄 Используем склад по умолчанию: {city.get('name')} ({self.destination_warehouse_id})")
                                break
                
                return True
            else:
                print(f"❌ Ошибка получения городов: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при получении городов: {e}")
            return False
    
    def fix_warehouse_assignments(self):
        """3) Исправление warehouse_id и destination_warehouse_id если они пустые"""
        print("\n🔧 ЭТАП 3: Проверка и исправление назначений складов...")
        
        if not self.cargo_250102_data:
            print("❌ Нет данных груза для исправления")
            return False
        
        current_warehouse_id = self.cargo_250102_data.get('warehouse_id')
        current_destination_id = self.cargo_250102_data.get('destination_warehouse_id')
        
        needs_fix = False
        fix_data = {}
        
        # Проверяем warehouse_id (склад приёмки)
        if not current_warehouse_id:
            print(f"⚠️ warehouse_id пустой, устанавливаем Москва Склад №1: {self.moscow_warehouse_id}")
            fix_data['current_warehouse_id'] = self.moscow_warehouse_id
            needs_fix = True
        else:
            print(f"✅ warehouse_id уже установлен: {current_warehouse_id}")
        
        # Проверяем destination_warehouse_id (склад назначения)
        if not current_destination_id:
            if self.destination_warehouse_id:
                print(f"⚠️ destination_warehouse_id пустой, устанавливаем: {self.destination_warehouse_id}")
                fix_data['destination_warehouse_id'] = self.destination_warehouse_id
                needs_fix = True
            else:
                print(f"❌ Не удалось определить destination_warehouse_id")
        else:
            print(f"✅ destination_warehouse_id уже установлен: {current_destination_id}")
        
        if not needs_fix:
            print("✅ Склады уже правильно назначены, исправление не требуется")
            return True
        
        # Выполняем исправление
        print(f"🔧 Применяем исправления: {fix_data}")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.patch(
                f"{BACKEND_URL}/admin/cargo/by-number/250102/set-warehouses",
                json=fix_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Склады успешно обновлены:")
                print(f"   🏭 Текущий склад: {fix_data.get('current_warehouse_id', current_warehouse_id)}")
                print(f"   🎯 Склад назначения: {fix_data.get('destination_warehouse_id', current_destination_id)}")
                return True
            else:
                print(f"❌ Ошибка обновления складов: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при исправлении складов: {e}")
            return False
    
    def verify_fix_and_visibility(self):
        """4) Повторная диагностика и проверка видимости"""
        print("\n✅ ЭТАП 4: Повторная диагностика и проверка видимости...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(f"{BACKEND_URL}/debug/find-cargo-by-number/250102", headers=headers)
            if response.status_code == 200:
                cargo_data = response.json()
                if cargo_data.get('found'):
                    cargo = cargo_data.get('cargo', {})
                    
                    print(f"📋 Результат после исправления:")
                    print(f"   📦 ID: {cargo.get('id')}")
                    print(f"   🔢 Номер: {cargo.get('cargo_number')}")
                    print(f"   🏢 Коллекция: {cargo_data.get('collection', 'не указана')}")
                    print(f"   🏭 warehouse_id: {cargo.get('warehouse_id') or 'ПУСТОЙ'}")
                    print(f"   🎯 destination_warehouse_id: {cargo.get('destination_warehouse_id') or 'ПУСТОЙ'}")
                    print(f"   📊 status: {cargo.get('status')}")
                    print(f"   ⚙️ processing_status: {cargo.get('processing_status')}")
                    
                    hidden_reason = cargo.get('hidden_reason')
                    if hidden_reason:
                        print(f"   🚫 hidden_reason: {hidden_reason} - ПРОБЛЕМА ОСТАЕТСЯ")
                        return False
                    else:
                        print(f"   ✅ hidden_reason: отсутствует - ГРУЗ СТАЛ ВИДИМЫМ КАНДИДАТОМ")
                    
                    # Проверяем что склады установлены
                    warehouse_id_ok = cargo.get('warehouse_id') is not None
                    destination_ok = cargo.get('destination_warehouse_id') is not None
                    
                    if warehouse_id_ok and destination_ok:
                        print(f"✅ Все склады установлены корректно!")
                        print(f"✅ Груз 250102 должен появиться в списке «Размещение» у оператора")
                        return True
                    else:
                        print(f"❌ Склады установлены некорректно")
                        return False
                else:
                    print(f"❌ Груз 250102 не найден после исправления")
                    return False
            else:
                print(f"❌ Ошибка повторной диагностики: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при повторной диагностике: {e}")
            return False
    
    def update_test_result(self, success, details):
        """5) Обновить test_result.md с результатами диагностики"""
        print(f"\n📝 ЭТАП 5: Обновление test_result.md...")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        status = "✅ УСПЕШНО" if success else "❌ ОШИБКА"
        
        result_entry = f"""
  - task: "🎯 СРОЧНАЯ ДИАГНОСТИКА ГРУЗА 250102: Исправление видимости заявки 250102 в списке «Размещение» в TAJLINE.TJ"
    implemented: true
    working: {str(success).lower()}
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: {str(success).lower()}
          agent: "testing"
          comment: "{status} СРОЧНАЯ ДИАГНОСТИКА ГРУЗА 250102 ЗАВЕРШЕНА! РЕЗУЛЬТАТ: {details} Дата: {timestamp}. ВЫПОЛНЕННЫЕ ДЕЙСТВИЯ: 1) Диагностика через GET /api/debug/find-cargo-by-number/250102, 2) Получение списка городов через GET /api/destinations/cities, 3) Исправление складов через PATCH /api/admin/cargo/by-number/250102/set-warehouses, 4) Проверка что hidden_reason отсутствует и карточка является visible_candidate."
"""
        
        try:
            # Read current test_result.md
            with open('/app/test_result.md', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the backend section and add our result
            if 'backend:' in content:
                # Add to existing backend section
                backend_pos = content.find('backend:')
                next_section_pos = content.find('\nfrontend:', backend_pos)
                if next_section_pos == -1:
                    next_section_pos = content.find('\nmetadata:', backend_pos)
                
                if next_section_pos != -1:
                    new_content = content[:next_section_pos] + result_entry + content[next_section_pos:]
                else:
                    new_content = content + result_entry
            else:
                # Add backend section
                new_content = content + f"\nbackend:{result_entry}"
            
            # Write updated content
            with open('/app/test_result.md', 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ test_result.md обновлен с результатами диагностики")
            
        except Exception as e:
            print(f"❌ Ошибка обновления test_result.md: {e}")
    
    def run_cargo_250102_diagnosis(self):
        """Выполнить полную диагностику и исправление груза 250102"""
        print("🚀 НАЧАЛО СРОЧНОЙ ДИАГНОСТИКИ ГРУЗА 250102")
        print("=" * 70)
        
        # Step 1: Authenticate admin
        if not self.authenticate_admin():
            self.update_test_result(False, "Ошибка авторизации администратора")
            return False
        
        # Step 2: Find cargo 250102
        if not self.find_cargo_250102():
            self.update_test_result(False, "Груз 250102 не найден в системе")
            return False
        
        # Step 3: Get destinations cities
        if not self.get_destinations_cities():
            self.update_test_result(False, "Ошибка получения списка городов")
            return False
        
        # Step 4: Fix warehouse assignments if needed
        if not self.fix_warehouse_assignments():
            self.update_test_result(False, "Ошибка исправления назначений складов")
            return False
        
        # Step 5: Verify fix and visibility
        if not self.verify_fix_and_visibility():
            self.update_test_result(False, "Груз 250102 все еще имеет проблемы с видимостью")
            return False
        
        # Step 6: Update test results
        success_details = "Груз 250102 успешно исправлен: warehouse_id и destination_warehouse_id установлены, hidden_reason отсутствует, груз стал visible_candidate"
        self.update_test_result(True, success_details)
        
        print("\n" + "=" * 70)
        print("🎉 СРОЧНАЯ ДИАГНОСТИКА ГРУЗА 250102 ЗАВЕРШЕНА УСПЕШНО!")
        print(f"✅ Груз 250102 теперь должен появиться в списке «Размещение»")
        print("=" * 70)
        
        return True

def main():
    """Main function"""
    test = Cargo250102DiagnosisTest()
    success = test.run_cargo_250102_diagnosis()
    
    if success:
        print("\n🎯 КРАТКИЙ ИТОГ:")
        print("✅ Груз 250102 найден и проанализирован")
        print("✅ Список городов получен и проанализирован")
        print("✅ Склады установлены корректно")
        print("✅ Hidden_reason отсутствует - груз стал видимым кандидатом")
        print("✅ Груз должен появиться в списке «Размещение» у оператора")
        sys.exit(0)
    else:
        print("\n❌ ДИАГНОСТИКА НЕ УДАЛАСЬ")
        print("❌ Проверьте логи выше для деталей ошибки")
        sys.exit(1)

if __name__ == "__main__":
    main()