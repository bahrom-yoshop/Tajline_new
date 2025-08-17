#!/usr/bin/env python3
"""
Backend Test for Cargo 250107 Warehouse Assignment Fix
Выполни точечное исправление для заявки 250107:
1) Найди ID складов: Москва Склад №1 → d0a8362d-b4d3-4947-b335-28c94658a021, Худжанд Склад №2 → 52761d8b-6407-49a5-8c4c-e28db520cdff
2) Под админом вызови PATCH /api/admin/cargo/by-number/250107/set-warehouses
3) Проверь через GET /api/debug/find-cargo-by-number/250107
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "https://73ed2aa0-f922-4978-81e7-0ad7dcef385d.preview.emergentagent.com/api"

class Cargo250107FixTest:
    def __init__(self):
        self.admin_token = None
        self.moscow_warehouse_id = "d0a8362d-b4d3-4947-b335-28c94658a021"  # Expected Moscow ID
        self.khujand_warehouse_id = "52761d8b-6407-49a5-8c4c-e28db520cdff"  # Expected Khujand ID
        self.cargo_number = "250107"
        
    def log(self, message):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        self.log("🔐 Авторизация администратора...")
        
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
                self.log(f"✅ Администратор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
                return True
            else:
                self.log(f"❌ Ошибка авторизации: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Ошибка подключения при авторизации: {e}")
            return False
    
    def verify_warehouse_ids(self):
        """Проверить и найти ID складов"""
        self.log("🏢 Проверка ID складов...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(f"{BACKEND_URL}/warehouses", headers=headers)
            if response.status_code == 200:
                warehouses = response.json()
                self.log(f"📦 Найдено складов: {len(warehouses)}")
                
                moscow_found = False
                khujand_found = False
                
                for warehouse in warehouses:
                    name = warehouse.get('name', '')
                    warehouse_id = warehouse.get('id')
                    
                    if warehouse_id == self.moscow_warehouse_id:
                        moscow_found = True
                        self.log(f"✅ Москва Склад №1 найден: {name} → {warehouse_id}")
                    elif warehouse_id == self.khujand_warehouse_id:
                        khujand_found = True
                        self.log(f"✅ Худжанд Склад №2 найден: {name} → {warehouse_id}")
                
                if not moscow_found:
                    self.log(f"⚠️ Москва Склад №1 с ID {self.moscow_warehouse_id} не найден, но будем использовать ожидаемый ID")
                if not khujand_found:
                    self.log(f"⚠️ Худжанд Склад №2 с ID {self.khujand_warehouse_id} не найден, но будем использовать ожидаемый ID")
                
                return True
            else:
                self.log(f"❌ Ошибка получения складов: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Ошибка при проверке складов: {e}")
            return False
    
    def check_cargo_before_fix(self):
        """Проверить состояние груза до исправления"""
        self.log(f"🔍 Проверка груза {self.cargo_number} до исправления...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(f"{BACKEND_URL}/debug/find-cargo-by-number/{self.cargo_number}", headers=headers)
            if response.status_code == 200:
                cargo_data = response.json()
                if cargo_data.get('found'):
                    cargo = cargo_data.get('cargo', {})
                    self.log(f"✅ Груз {self.cargo_number} найден:")
                    self.log(f"   ID: {cargo.get('id')}")
                    self.log(f"   Номер: {cargo.get('cargo_number')}")
                    self.log(f"   Текущий склад (warehouse_id): {cargo.get('warehouse_id')}")
                    self.log(f"   Склад назначения (destination_warehouse_id): {cargo.get('destination_warehouse_id')}")
                    self.log(f"   Статус: {cargo.get('status')}")
                    self.log(f"   Hidden reason: {cargo.get('hidden_reason')}")
                    return cargo
                else:
                    self.log(f"❌ Груз {self.cargo_number} не найден")
                    return None
            else:
                self.log(f"❌ Ошибка поиска груза: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            self.log(f"❌ Ошибка при поиске груза: {e}")
            return None
    
    def apply_warehouse_fix(self):
        """Применить исправление складов"""
        self.log(f"🔧 Применение исправления складов для груза {self.cargo_number}...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
        
        fix_data = {
            "current_warehouse_id": self.moscow_warehouse_id,
            "destination_warehouse_id": self.khujand_warehouse_id
        }
        
        self.log(f"📋 Данные для исправления:")
        self.log(f"   current_warehouse_id: {self.moscow_warehouse_id} (Москва Склад №1)")
        self.log(f"   destination_warehouse_id: {self.khujand_warehouse_id} (Худжанд Склад №2)")
        
        try:
            response = requests.patch(
                f"{BACKEND_URL}/admin/cargo/by-number/{self.cargo_number}/set-warehouses",
                json=fix_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Исправление применено успешно!")
                self.log(f"📋 Ответ сервера: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return True
            else:
                self.log(f"❌ Ошибка применения исправления: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log(f"❌ Ошибка при применении исправления: {e}")
            return False
    
    def verify_fix_applied(self):
        """Проверить что исправление применено корректно"""
        self.log(f"✅ Проверка применения исправления для груза {self.cargo_number}...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = requests.get(f"{BACKEND_URL}/debug/find-cargo-by-number/{self.cargo_number}", headers=headers)
            if response.status_code == 200:
                cargo_data = response.json()
                if cargo_data.get('found'):
                    cargo = cargo_data.get('cargo', {})
                    
                    self.log(f"📋 Состояние груза после исправления:")
                    self.log(f"   ID: {cargo.get('id')}")
                    self.log(f"   Номер: {cargo.get('cargo_number')}")
                    
                    current_warehouse = cargo.get('warehouse_id')
                    destination_warehouse = cargo.get('destination_warehouse_id')
                    hidden_reason = cargo.get('hidden_reason')
                    
                    self.log(f"   Текущий склад (warehouse_id): {current_warehouse}")
                    self.log(f"   Склад назначения (destination_warehouse_id): {destination_warehouse}")
                    self.log(f"   Hidden reason: {hidden_reason}")
                    
                    # Проверяем корректность исправления
                    warehouse_id_correct = current_warehouse == self.moscow_warehouse_id
                    destination_id_correct = destination_warehouse == self.khujand_warehouse_id
                    hidden_reason_resolved = hidden_reason is None or hidden_reason == "visible_candidate"
                    
                    if warehouse_id_correct:
                        self.log(f"✅ Текущий склад установлен корректно: {current_warehouse}")
                    else:
                        self.log(f"❌ Текущий склад некорректен. Ожидался: {self.moscow_warehouse_id}, получен: {current_warehouse}")
                    
                    if destination_id_correct:
                        self.log(f"✅ Склад назначения установлен корректно: {destination_warehouse}")
                    else:
                        self.log(f"❌ Склад назначения некорректен. Ожидался: {self.khujand_warehouse_id}, получен: {destination_warehouse}")
                    
                    if hidden_reason_resolved:
                        self.log(f"✅ Hidden reason исчез или стал visible_candidate: {hidden_reason}")
                    else:
                        self.log(f"❌ Hidden reason все еще присутствует: {hidden_reason}")
                    
                    all_correct = warehouse_id_correct and destination_id_correct and hidden_reason_resolved
                    
                    if all_correct:
                        self.log(f"🎉 ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ КОРРЕКТНО!")
                    else:
                        self.log(f"⚠️ Не все исправления применены корректно")
                    
                    return all_correct, cargo
                else:
                    self.log(f"❌ Груз {self.cargo_number} не найден после исправления")
                    return False, None
            else:
                self.log(f"❌ Ошибка проверки груза: {response.status_code} - {response.text}")
                return False, None
        except Exception as e:
            self.log(f"❌ Ошибка при проверке исправления: {e}")
            return False, None
    
    def update_test_result(self, success, details):
        """Обновить test_result.md с результатами"""
        self.log("📝 Обновление test_result.md...")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        status = "✅ УСПЕШНО" if success else "❌ ОШИБКА"
        
        result_entry = f"""
  - task: "🎯 ТОЧЕЧНОЕ ИСПРАВЛЕНИЕ ГРУЗА 250107: Установка правильных складов для заявки 250107 в TAJLINE.TJ"
    implemented: true
    working: {str(success).lower()}
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: {str(success).lower()}
          agent: "testing"
          comment: "{status} ТОЧЕЧНОЕ ИСПРАВЛЕНИЕ ЗАЯВКИ 250107 ЗАВЕРШЕНО! РЕЗУЛЬТАТ: {details} Дата: {timestamp}. ИТОГ: Груз 250107 теперь имеет warehouse_id (Москва Склад №1: {self.moscow_warehouse_id}) и destination_warehouse_id (Худжанд Склад №2: {self.khujand_warehouse_id}), поле hidden_reason исчезло или стало visible_candidate."
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
            
            self.log("✅ test_result.md обновлен с результатами исправления")
            
        except Exception as e:
            self.log(f"❌ Ошибка обновления test_result.md: {e}")
    
    def run_complete_fix(self):
        """Выполнить полное исправление груза 250107"""
        self.log("🚀 НАЧАЛО ТОЧЕЧНОГО ИСПРАВЛЕНИЯ ГРУЗА 250107")
        self.log("=" * 80)
        
        # Step 1: Authenticate admin
        if not self.authenticate_admin():
            self.update_test_result(False, "Ошибка авторизации администратора")
            return False
        
        # Step 2: Verify warehouse IDs
        if not self.verify_warehouse_ids():
            self.update_test_result(False, "Ошибка проверки ID складов")
            return False
        
        # Step 3: Check cargo before fix
        cargo_before = self.check_cargo_before_fix()
        if not cargo_before:
            self.update_test_result(False, f"Груз {self.cargo_number} не найден в системе")
            return False
        
        # Step 4: Apply warehouse fix
        if not self.apply_warehouse_fix():
            self.update_test_result(False, f"Ошибка применения исправления складов для груза {self.cargo_number}")
            return False
        
        # Step 5: Verify the fix
        fix_success, cargo_after = self.verify_fix_applied()
        if not fix_success:
            self.update_test_result(False, f"Исправление не применено корректно для груза {self.cargo_number}")
            return False
        
        # Step 6: Update test results
        success_details = f"Груз {self.cargo_number} успешно исправлен: warehouse_id установлен на Москва Склад №1 ({self.moscow_warehouse_id}), destination_warehouse_id установлен на Худжанд Склад №2 ({self.khujand_warehouse_id}), hidden_reason исчез"
        self.update_test_result(True, success_details)
        
        self.log("\n" + "=" * 80)
        self.log("🎉 ТОЧЕЧНОЕ ИСПРАВЛЕНИЕ ГРУЗА 250107 ЗАВЕРШЕНО УСПЕШНО!")
        self.log(f"✅ Груз {self.cargo_number} теперь имеет правильные склады:")
        self.log(f"   • Текущий склад: Москва Склад №1 ({self.moscow_warehouse_id})")
        self.log(f"   • Склад назначения: Худжанд Склад №2 ({self.khujand_warehouse_id})")
        self.log(f"   • Hidden reason: {cargo_after.get('hidden_reason', 'отсутствует')}")
        self.log("=" * 80)
        
        return True

def main():
    """Main function"""
    test = Cargo250107FixTest()
    success = test.run_complete_fix()
    
    if success:
        print("\n🎯 КРАТКИЙ ИТОГ:")
        print("✅ Заявка 250107 успешно исправлена")
        print("✅ Установлены правильные склады: Москва → Худжанд")
        print("✅ Hidden_reason исчез или стал visible_candidate")
        print("✅ Груз теперь должен быть видимым кандидатом в системе")
        sys.exit(0)
    else:
        print("\n❌ ИСПРАВЛЕНИЕ НЕ УДАЛОСЬ")
        print("❌ Проверьте логи выше для деталей ошибки")
        sys.exit(1)

if __name__ == "__main__":
    main()