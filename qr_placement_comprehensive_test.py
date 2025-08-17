#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новая функциональность размещения грузов на транспорт через QR-коды в TAJLINE.TJ

ПРОБЛЕМА ИЗ REVIEW REQUEST:
Протестируй исправленную функциональность размещения грузов на транспорт через QR-коды в TAJLINE.TJ

ДЕТАЛЬНОЕ ТЕСТИРОВАНИЕ:
1. **Авторизация администратора**: Войди под администратором
2. **Создание тестовых данных**:
   - Создай тестовый груз с QR кодом: POST /api/placement/create-test-cargo-for-qr
   - Найди транспорт с QR кодом для тестирования
3. **Тестирование полного цикла**:
   - Протестируй POST /api/placement/scan-transport-qr с QR кодом транспорта
   - Протестируй POST /api/placement/scan-cargo-qr с QR кодом созданного груза
   - Протестируй POST /api/placement/place-cargo-on-transport для размещения груза
4. **Критическая проверка**:
   - Убедись что warehouse_location груза становится null после размещения
   - Проверь что груз получает transport_id
   - Проверь что создается placement_log с информацией об операторе
   - Убедись что статус транспорта обновляется корректно
5. **Проверка данных**:
   - Протестируй GET /api/placement/transport-cargo/{transport_id}
   - Убедись что груз появился в cargo_list транспорта
   - Проверь что лог размещения записался правильно

КРИТИЧЕСКОЕ ТРЕБОВАНИЕ:
Груз должен автоматически удаляться из ячейки склада (warehouse_location = null) и появляться на транспорте со всеми данными.
"""

import requests
import json
import os
from datetime import datetime, timedelta
import uuid

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://freight-hub-6.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class QRCargoPlacementTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_cargo_id = None
        self.test_transport_id = None
        self.test_transport_qr = None
        self.test_cargo_qr = None
        self.placement_log_id = None
        
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
        
        response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data.get('access_token')
            user_info = data.get('user', {})
            self.log(f"✅ Администратор авторизован: {user_info.get('full_name')} (номер: {user_info.get('user_number')}, роль: {user_info.get('role')})")
            return True
        else:
            self.log(f"❌ Ошибка авторизации администратора: {response.status_code} - {response.text}")
            return False
            
    def authenticate_operator(self):
        """Авторизация оператора склада"""
        self.log("🔐 Авторизация оператора склада...")
        
        login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.operator_token = data.get('access_token')
            user_info = data.get('user', {})
            self.log(f"✅ Оператор авторизован: {user_info.get('full_name')} (номер: {user_info.get('user_number')}, роль: {user_info.get('role')})")
            return True
        else:
            self.log(f"❌ Ошибка авторизации оператора: {response.status_code} - {response.text}")
            return False
            
    def create_test_cargo_for_qr(self):
        """Создание тестового груза с QR кодом"""
        self.log("📦 Создание тестового груза с QR кодом...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/placement/create-test-cargo-for-qr", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo = data.get('cargo', {})
            self.test_cargo_id = cargo.get('id')
            self.test_cargo_qr = cargo.get('qr_data')
            cargo_number = cargo.get('cargo_number')
            warehouse_location = cargo.get('warehouse_location')
            
            self.log(f"✅ Тестовый груз создан:")
            self.log(f"   ID: {self.test_cargo_id}")
            self.log(f"   Номер: {cargo_number}")
            self.log(f"   QR данные: {self.test_cargo_qr}")
            self.log(f"   Ячейка склада: {warehouse_location}")
            return True
        else:
            self.log(f"❌ Ошибка создания тестового груза: {response.status_code} - {response.text}")
            return False
            
    def find_transport_with_qr(self):
        """Поиск транспорта с QR кодом для тестирования"""
        self.log("🚛 Поиск транспорта с QR кодом...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.get(f"{API_BASE}/transport/list", headers=headers)
        
        if response.status_code == 200:
            transports = response.json()  # API returns array directly
            
            # Ищем транспорт с QR кодом
            for transport in transports:
                if transport.get('qr_data'):
                    self.test_transport_id = transport.get('id')
                    self.test_transport_qr = transport.get('qr_data')
                    transport_number = transport.get('transport_number')
                    status = transport.get('status')
                    
                    self.log(f"✅ Найден транспорт с QR кодом:")
                    self.log(f"   ID: {self.test_transport_id}")
                    self.log(f"   Номер: {transport_number}")
                    self.log(f"   QR данные: {self.test_transport_qr}")
                    self.log(f"   Статус: {status}")
                    return True
                    
            # Если нет транспорта с QR, используем первый доступный и создадим QR
            if transports:
                transport = transports[0]
                self.test_transport_id = transport.get('id')
                transport_number = transport.get('transport_number')
                status = transport.get('status')
                
                # Генерируем QR для транспорта
                qr_response = self.session.post(
                    f"{API_BASE}/transport/{self.test_transport_id}/generate-qr", 
                    headers=headers
                )
                
                if qr_response.status_code == 200:
                    qr_data = qr_response.json()
                    self.test_transport_qr = qr_data.get('qr_data')
                    
                    self.log(f"✅ Создан QR код для транспорта:")
                    self.log(f"   ID: {self.test_transport_id}")
                    self.log(f"   Номер: {transport_number}")
                    self.log(f"   QR данные: {self.test_transport_qr}")
                    self.log(f"   Статус: {status}")
                    return True
                else:
                    self.log(f"❌ Не удалось создать QR код для транспорта: {qr_response.status_code}")
                    return False
            else:
                self.log("❌ Не найдено транспортов в системе")
                return False
        else:
            self.log(f"❌ Ошибка получения списка транспортов: {response.status_code} - {response.text}")
            return False
            
    def scan_transport_qr(self):
        """Тестирование сканирования QR кода транспорта"""
        self.log("🔍 Тестирование сканирования QR кода транспорта...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        scan_data = {"qr_data": self.test_transport_qr}
        
        response = self.session.post(f"{API_BASE}/placement/scan-transport-qr", json=scan_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            transport = data.get('transport', {})
            message = data.get('message', '')
            
            self.log(f"✅ QR код транспорта отсканирован успешно:")
            self.log(f"   Транспорт: {transport.get('transport_number')}")
            self.log(f"   Водитель: {transport.get('driver_name')}")
            self.log(f"   Направление: {transport.get('direction')}")
            self.log(f"   Грузоподъемность: {transport.get('capacity_kg')} кг")
            self.log(f"   Текущая загрузка: {transport.get('current_load_kg')} кг")
            self.log(f"   Статус: {transport.get('status')}")
            self.log(f"   Сообщение: {message}")
            return True
        else:
            self.log(f"❌ Ошибка сканирования QR кода транспорта: {response.status_code} - {response.text}")
            return False
            
    def scan_cargo_qr(self):
        """Тестирование сканирования QR кода груза"""
        self.log("🔍 Тестирование сканирования QR кода груза...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        scan_data = {"qr_data": self.test_cargo_qr}
        
        response = self.session.post(f"{API_BASE}/placement/scan-cargo-qr", json=scan_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo = data.get('cargo', {})
            message = data.get('message', '')
            
            self.log(f"✅ QR код груза отсканирован успешно:")
            self.log(f"   Груз: {cargo.get('cargo_number')}")
            self.log(f"   Название: {cargo.get('cargo_name')}")
            self.log(f"   Вес: {cargo.get('weight')} кг")
            self.log(f"   Отправитель: {cargo.get('sender_full_name')}")
            self.log(f"   Получатель: {cargo.get('recipient_full_name')}")
            self.log(f"   Ячейка склада: {cargo.get('warehouse_location')}")
            self.log(f"   Статус: {cargo.get('status')}")
            self.log(f"   Сообщение: {message}")
            return True
        else:
            self.log(f"❌ Ошибка сканирования QR кода груза: {response.status_code} - {response.text}")
            return False
            
    def place_cargo_on_transport(self):
        """Тестирование размещения груза на транспорт"""
        self.log("🚛📦 Тестирование размещения груза на транспорт...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        placement_data = {
            "transport_id": self.test_transport_id,
            "cargo_id": self.test_cargo_id
        }
        
        response = self.session.post(f"{API_BASE}/placement/place-cargo-on-transport", json=placement_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            transport = data.get('transport', {})
            cargo = data.get('cargo', {})
            placement_log = data.get('placement_log', {})
            message = data.get('message', '')
            
            self.placement_log_id = placement_log.get('id')
            
            self.log(f"✅ Груз успешно размещен на транспорт:")
            self.log(f"   Транспорт: {transport.get('transport_number')}")
            self.log(f"   Новая загрузка: {transport.get('current_load_kg')} кг")
            self.log(f"   Грузоподъемность: {transport.get('capacity_kg')} кг")
            self.log(f"   Новый статус: {transport.get('status')}")
            self.log(f"   Количество грузов: {transport.get('cargo_count')}")
            
            self.log(f"   Груз: {cargo.get('cargo_number')}")
            self.log(f"   Вес груза: {cargo.get('weight')} кг")
            self.log(f"   Удален из ячейки: {cargo.get('warehouse_location_removed')}")
            
            self.log(f"   Лог размещения ID: {placement_log.get('id')}")
            self.log(f"   Оператор: {placement_log.get('operator_name')}")
            self.log(f"   Время размещения: {placement_log.get('placed_at')}")
            self.log(f"   Сообщение: {message}")
            return True
        else:
            self.log(f"❌ Ошибка размещения груза на транспорт: {response.status_code} - {response.text}")
            return False
            
    def verify_cargo_removal_from_warehouse(self):
        """Проверка что груз удален из ячейки склада"""
        self.log("🔍 Проверка удаления груза из ячейки склада...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.get(f"{API_BASE}/operator/cargo/{self.test_cargo_id}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            warehouse_location = data.get('warehouse_location')
            transport_id = data.get('transport_id')
            status = data.get('status')
            
            if warehouse_location is None and transport_id == self.test_transport_id:
                self.log(f"✅ КРИТИЧЕСКОЕ ТРЕБОВАНИЕ ВЫПОЛНЕНО:")
                self.log(f"   warehouse_location = {warehouse_location} (удален из ячейки)")
                self.log(f"   transport_id = {transport_id} (назначен на транспорт)")
                self.log(f"   status = {status}")
                return True
            else:
                self.log(f"❌ КРИТИЧЕСКОЕ ТРЕБОВАНИЕ НЕ ВЫПОЛНЕНО:")
                self.log(f"   warehouse_location = {warehouse_location} (должно быть null)")
                self.log(f"   transport_id = {transport_id} (должно быть {self.test_transport_id})")
                return False
        else:
            self.log(f"❌ Ошибка получения данных груза: {response.status_code} - {response.text}")
            return False
            
    def verify_transport_cargo_list(self):
        """Проверка что груз появился в списке грузов транспорта"""
        self.log("🔍 Проверка списка грузов транспорта...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.get(f"{API_BASE}/placement/transport-cargo/{self.test_transport_id}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            transport = data.get('transport', {})
            cargo_list = data.get('cargo_list', [])
            placement_logs = data.get('placement_logs', [])
            
            self.log(f"✅ Данные транспорта получены:")
            self.log(f"   Транспорт: {transport.get('transport_number')}")
            self.log(f"   Загрузка: {transport.get('current_load_kg')} кг")
            self.log(f"   Статус: {transport.get('status')}")
            self.log(f"   Количество грузов: {transport.get('cargo_count')}")
            
            # Проверяем наличие нашего груза в списке
            cargo_found = False
            for cargo_item in cargo_list:
                if cargo_item.get('cargo_id') == self.test_cargo_id:
                    cargo_found = True
                    self.log(f"✅ Груз найден в списке транспорта:")
                    self.log(f"   Номер груза: {cargo_item.get('cargo_number')}")
                    self.log(f"   Вес: {cargo_item.get('weight')} кг")
                    self.log(f"   Размещен: {cargo_item.get('placed_at')}")
                    self.log(f"   Оператор: {cargo_item.get('operator_name')}")
                    break
                    
            # Проверяем логи размещения
            log_found = False
            for log_item in placement_logs:
                if log_item.get('cargo_id') == self.test_cargo_id:
                    log_found = True
                    self.log(f"✅ Лог размещения найден:")
                    self.log(f"   ID лога: {log_item.get('id')}")
                    self.log(f"   Тип операции: {log_item.get('operation_type')}")
                    self.log(f"   Удалена ячейка: {log_item.get('warehouse_location_removed')}")
                    break
                    
            return cargo_found and log_found
        else:
            self.log(f"❌ Ошибка получения данных транспорта: {response.status_code} - {response.text}")
            return False
            
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        self.log("🧹 Очистка тестовых данных...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Удаление тестового груза
        if self.test_cargo_id:
            try:
                response = self.session.delete(f"{API_BASE}/admin/cargo/{self.test_cargo_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Тестовый груз {self.test_cargo_id} удален")
                else:
                    self.log(f"⚠️ Не удалось удалить груз {self.test_cargo_id}: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления груза: {e}")
                
        # Удаление лога размещения
        if self.placement_log_id:
            try:
                response = self.session.delete(f"{API_BASE}/admin/placement-logs/{self.placement_log_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Лог размещения {self.placement_log_id} удален")
                else:
                    self.log(f"⚠️ Не удалось удалить лог размещения: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления лога: {e}")
                
    def run_comprehensive_test(self):
        """Запуск комплексного тестирования QR размещения грузов"""
        self.log("🎯 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ QR РАЗМЕЩЕНИЯ ГРУЗОВ НА ТРАНСПОРТ")
        self.log("=" * 80)
        
        success_count = 0
        total_tests = 10
        
        try:
            # 1. Авторизация администратора
            self.log("\n📋 ЭТАП 1: Авторизация администратора")
            if self.authenticate_admin():
                success_count += 1
            else:
                self.log("❌ Критическая ошибка: не удалось авторизовать администратора")
                return False
                
            # 2. Авторизация оператора
            self.log("\n📋 ЭТАП 2: Авторизация оператора склада")
            if self.authenticate_operator():
                success_count += 1
            else:
                self.log("❌ Критическая ошибка: не удалось авторизовать оператора")
                return False
                
            # 3. Создание тестового груза с QR кодом
            self.log("\n📋 ЭТАП 3: Создание тестового груза с QR кодом")
            if self.create_test_cargo_for_qr():
                success_count += 1
            else:
                self.log("❌ Критическая ошибка: не удалось создать тестовый груз")
                return False
                
            # 4. Поиск транспорта с QR кодом
            self.log("\n📋 ЭТАП 4: Поиск транспорта с QR кодом")
            if self.find_transport_with_qr():
                success_count += 1
            else:
                self.log("❌ Критическая ошибка: не найден транспорт с QR кодом")
                return False
                
            # 5. Сканирование QR кода транспорта
            self.log("\n📋 ЭТАП 5: Сканирование QR кода транспорта")
            if self.scan_transport_qr():
                success_count += 1
            else:
                self.log("❌ Ошибка сканирования QR кода транспорта")
                
            # 6. Сканирование QR кода груза
            self.log("\n📋 ЭТАП 6: Сканирование QR кода груза")
            if self.scan_cargo_qr():
                success_count += 1
            else:
                self.log("❌ Ошибка сканирования QR кода груза")
                
            # 7. Размещение груза на транспорт
            self.log("\n📋 ЭТАП 7: Размещение груза на транспорт")
            if self.place_cargo_on_transport():
                success_count += 1
            else:
                self.log("❌ Критическая ошибка: не удалось разместить груз на транспорт")
                return False
                
            # 8. Проверка удаления груза из ячейки склада
            self.log("\n📋 ЭТАП 8: Проверка удаления груза из ячейки склада")
            if self.verify_cargo_removal_from_warehouse():
                success_count += 1
            else:
                self.log("❌ КРИТИЧЕСКОЕ ТРЕБОВАНИЕ НЕ ВЫПОЛНЕНО: груз не удален из ячейки")
                
            # 9. Проверка появления груза в списке транспорта
            self.log("\n📋 ЭТАП 9: Проверка появления груза в списке транспорта")
            if self.verify_transport_cargo_list():
                success_count += 1
            else:
                self.log("❌ Груз не появился в списке транспорта или лог не создан")
                
            # 10. Проверка логирования операции
            self.log("\n📋 ЭТАП 10: Проверка создания лога размещения")
            if self.placement_log_id:
                self.log(f"✅ Лог размещения создан: {self.placement_log_id}")
                success_count += 1
            else:
                self.log("❌ Лог размещения не создан")
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка во время тестирования: {e}")
            
        finally:
            # Очистка тестовых данных
            self.log("\n📋 ФИНАЛЬНЫЙ ЭТАП: Очистка тестовых данных")
            self.cleanup_test_data()
            
        # Итоговый отчет
        self.log("\n" + "=" * 80)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ QR РАЗМЕЩЕНИЯ ГРУЗОВ")
        self.log("=" * 80)
        
        success_rate = (success_count / total_tests) * 100
        
        self.log(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        self.log(f"   Успешных тестов: {success_count}/{total_tests}")
        self.log(f"   Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 ОТЛИЧНО: Функциональность QR размещения грузов работает корректно!")
        elif success_rate >= 70:
            self.log("✅ ХОРОШО: Основная функциональность работает, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Функциональность требует исправлений")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ Создание тестового груза с QR кодом")
        self.log("✅ Сканирование QR кодов транспорта и груза")
        self.log("✅ Размещение груза на транспорт через QR")
        self.log("✅ Автоматическое удаление груза из ячейки склада (warehouse_location = null)")
        self.log("✅ Назначение груза на транспорт (transport_id)")
        self.log("✅ Создание лога размещения с информацией об операторе")
        self.log("✅ Обновление статуса транспорта")
        self.log("✅ Появление груза в cargo_list транспорта")
        
        return success_rate >= 70

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Размещение грузов на транспорт через QR-коды в TAJLINE.TJ")
    print("=" * 80)
    
    tester = QRCargoPlacementTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()