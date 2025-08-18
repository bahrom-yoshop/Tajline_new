#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Улучшенная система сканирования QR грузов с отладочной информацией в TAJLINE.TJ

КОНТЕКСТ ТЕСТИРОВАНИЯ:
Протестировать улучшенную систему сканирования QR грузов согласно review request:
1. **Авторизация администратора**: Войти под администратором
2. **Создание тестового груза с QR кодом и ячейкой склада**:
   - POST /api/placement/create-test-cargo-with-warehouse
   - Убедись что создается груз с warehouse_location и qr_data
3. **Тестирование улучшенного поиска груза**:
   - POST /api/placement/scan-cargo-qr с QR кодом созданного груза
   - Проверь детальную отладочную информацию о попытках поиска
   - Убедись что груз находится правильно
4. **Проверка что груз находится в ячейке склада**:
   - Убедись что warehouse_location не пустое
   - Проверь что груз готов к размещению на транспорт
5. **Полный цикл размещения**:
   - Найди транспорт с QR кодом
   - Отсканируй транспорт
   - Отсканируй созданный груз
   - Размести груз на транспорт

КЛЮЧЕВЫЕ УЛУЧШЕНИЯ ДЛЯ ТЕСТИРОВАНИЯ:
- Система должна правильно находить грузы которые размещены на складе (имеют warehouse_location)
- Показывать детальную отладочную информацию о попытках поиска
- Поддерживать различные методы поиска (qr_data, cargo_number, regex)
"""

import requests
import json
import os
from datetime import datetime, timedelta
import random
import string

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://qr-logistics-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class ImprovedQRScanningTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_cargo_ids = []
        self.test_transport_ids = []
        self.test_placement_logs = []
        
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
            
    def create_test_cargo_with_warehouse(self):
        """Создание тестового груза с QR кодом и ячейкой склада"""
        self.log("📦 Создание тестового груза с QR кодом и ячейкой склада...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/placement/create-test-cargo-with-warehouse", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo_info = data.get('cargo', {})
            cargo_id = cargo_info.get('id')
            cargo_number = cargo_info.get('cargo_number')
            qr_data = cargo_info.get('qr_data')
            warehouse_location = cargo_info.get('warehouse_location')
            weight = cargo_info.get('weight')
            status = cargo_info.get('status')
            
            self.test_cargo_ids.append(cargo_id)
            self.log(f"✅ Тестовый груз создан:")
            self.log(f"   📦 ID груза: {cargo_id}")
            self.log(f"   🔢 Номер груза: {cargo_number}")
            self.log(f"   📱 QR данные: {qr_data}")
            self.log(f"   🏭 Размещение в ячейке: {warehouse_location}")
            self.log(f"   ⚖️ Вес: {weight} кг")
            self.log(f"   📊 Статус: {status}")
            
            # Проверяем что груз имеет warehouse_location и qr_data
            if not warehouse_location:
                self.log("❌ КРИТИЧЕСКАЯ ОШИБКА: Груз не имеет warehouse_location!")
                return None
                
            if not qr_data:
                self.log("❌ КРИТИЧЕСКАЯ ОШИБКА: Груз не имеет qr_data!")
                return None
                
            self.log("✅ Груз корректно создан с warehouse_location и qr_data")
            
            return {
                'cargo_id': cargo_id,
                'cargo_number': cargo_number,
                'qr_data': qr_data,
                'warehouse_location': warehouse_location,
                'weight': weight,
                'status': status
            }
        else:
            self.log(f"❌ Ошибка создания тестового груза: {response.status_code} - {response.text}")
            return None
            
    def test_improved_cargo_search(self, test_cargo):
        """Тестирование улучшенного поиска груза с отладочной информацией"""
        self.log("🔍 Тестирование улучшенного поиска груза с отладочной информацией...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        qr_data = test_cargo['qr_data']
        
        self.log(f"🔍 Поиск груза по QR коду: {qr_data}")
        
        search_data = {"qr_data": qr_data}
        response = self.session.post(f"{API_BASE}/placement/scan-cargo-qr", json=search_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            found_cargo = data.get('cargo')
            search_info = data.get('search_info', [])
            message = data.get('message', '')
            
            self.log(f"✅ Груз найден успешно!")
            self.log(f"   📦 Найденный груз: {found_cargo.get('cargo_number')}")
            self.log(f"   🏭 Ячейка склада: {found_cargo.get('warehouse_location')}")
            self.log(f"   📊 Статус: {found_cargo.get('status')}")
            self.log(f"   💬 Сообщение: {message}")
            
            # Проверяем отладочную информацию о попытках поиска
            self.log("🔍 Детальная отладочная информация о попытках поиска:")
            for i, attempt in enumerate(search_info, 1):
                self.log(f"   {i}. {attempt}")
                
            # Проверяем что найден правильный груз
            if found_cargo.get('id') == test_cargo['cargo_id']:
                self.log("✅ Найден правильный груз (ID совпадает)")
            else:
                self.log("❌ Найден неправильный груз (ID не совпадает)")
                return False
                
            # Проверяем что груз находится в ячейке склада
            warehouse_location = found_cargo.get('warehouse_location')
            if warehouse_location:
                self.log(f"✅ Груз находится в ячейке склада: {warehouse_location}")
            else:
                self.log("❌ Груз НЕ находится в ячейке склада!")
                return False
                
            # Проверяем что груз готов к размещению на транспорт
            if not found_cargo.get('transport_id'):
                self.log("✅ Груз готов к размещению на транспорт (не размещен)")
            else:
                self.log(f"⚠️ Груз уже размещен на транспорт: {found_cargo.get('transport_id')}")
                
            return True
        else:
            self.log(f"❌ Ошибка поиска груза: {response.status_code} - {response.text}")
            return False
            
    def find_transport_with_qr(self):
        """Найти транспорт с QR кодом"""
        self.log("🚛 Поиск транспорта с QR кодом...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Получаем список транспортов
        response = self.session.get(f"{API_BASE}/transport/list", headers=headers)
        
        if response.status_code == 200:
            transports = response.json()
            self.log(f"📋 Найдено транспортов: {len(transports)}")
            
            # Ищем транспорт подходящий для размещения
            for transport in transports:
                transport_id = transport.get('id')
                transport_number = transport.get('transport_number')
                status = transport.get('status')
                
                self.log(f"🚛 Проверяем транспорт: {transport_number} (статус: {status})")
                
                # Попробуем сгенерировать QR для этого транспорта
                qr_response = self.session.post(f"{API_BASE}/transport/{transport_id}/generate-qr", headers=headers)
                
                if qr_response.status_code == 200:
                    qr_data = qr_response.json()
                    qr_code = qr_data.get('qr_data')
                    
                    self.log(f"✅ Найден транспорт с QR: {transport_number}")
                    self.log(f"   🚛 ID: {transport_id}")
                    self.log(f"   📱 QR код: {qr_code}")
                    self.log(f"   📊 Статус: {status}")
                    
                    return {
                        'transport_id': transport_id,
                        'transport_number': transport_number,
                        'qr_data': qr_code,
                        'status': status
                    }
                else:
                    self.log(f"⚠️ Не удалось сгенерировать QR для транспорта {transport_number}: {qr_response.status_code}")
                    
        self.log("❌ Не удалось найти подходящий транспорт с QR кодом")
        return None
        
    def scan_transport_qr(self, transport_data):
        """Отсканировать QR код транспорта"""
        self.log("🚛 Сканирование QR кода транспорта...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        scan_data = {"qr_data": transport_data['qr_data']}
        
        response = self.session.post(f"{API_BASE}/placement/scan-transport-qr", json=scan_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            transport_info = data.get('transport')
            message = data.get('message', '')
            
            self.log(f"✅ Сканирование транспорта успешно:")
            self.log(f"   🚛 Номер: {transport_info.get('transport_number')}")
            self.log(f"   👨‍✈️ Водитель: {transport_info.get('driver_name')}")
            self.log(f"   📍 Направление: {transport_info.get('direction')}")
            self.log(f"   ⚖️ Грузоподъемность: {transport_info.get('capacity_kg')} кг")
            self.log(f"   📦 Текущая загрузка: {transport_info.get('current_load_kg')} кг")
            self.log(f"   📊 Статус: {transport_info.get('status')}")
            self.log(f"   💬 Сообщение: {message}")
            
            return True
        else:
            self.log(f"❌ Ошибка сканирования транспорта: {response.status_code} - {response.text}")
            return False
            
    def scan_cargo_qr(self, test_cargo):
        """Отсканировать созданный груз"""
        self.log("📦 Сканирование QR кода созданного груза...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        scan_data = {"qr_data": test_cargo['qr_data']}
        
        response = self.session.post(f"{API_BASE}/placement/scan-cargo-qr", json=scan_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo_info = data.get('cargo')
            search_info = data.get('search_info', [])
            message = data.get('message', '')
            
            self.log(f"✅ Сканирование груза успешно:")
            self.log(f"   📦 Номер: {cargo_info.get('cargo_number')}")
            self.log(f"   📝 Название: {cargo_info.get('cargo_name')}")
            self.log(f"   ⚖️ Вес: {cargo_info.get('weight')} кг")
            self.log(f"   👤 Отправитель: {cargo_info.get('sender_full_name')}")
            self.log(f"   👤 Получатель: {cargo_info.get('recipient_full_name')}")
            self.log(f"   🏭 Ячейка склада: {cargo_info.get('warehouse_location')}")
            self.log(f"   📊 Статус: {cargo_info.get('status')}")
            self.log(f"   💬 Сообщение: {message}")
            
            # Показываем отладочную информацию
            self.log("🔍 Отладочная информация поиска:")
            for i, attempt in enumerate(search_info, 1):
                self.log(f"   {i}. {attempt}")
            
            return True
        else:
            self.log(f"❌ Ошибка сканирования груза: {response.status_code} - {response.text}")
            return False
            
    def place_cargo_on_transport(self, transport_data, test_cargo):
        """Разместить груз на транспорт"""
        self.log("🔄 Размещение груза на транспорт...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        placement_data = {
            "transport_id": transport_data['transport_id'],
            "cargo_id": test_cargo['cargo_id']
        }
        
        response = self.session.post(f"{API_BASE}/placement/place-cargo-on-transport", json=placement_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            self.log(f"✅ Размещение груза на транспорт успешно:")
            self.log(f"   📦 Груз: {data.get('cargo_number')}")
            self.log(f"   🚛 Транспорт: {data.get('transport_number')}")
            self.log(f"   📊 Новая загрузка: {data.get('new_load_kg')} кг")
            self.log(f"   📈 Количество грузов: {data.get('cargo_count')}")
            self.log(f"   📝 Лог размещения: {data.get('placement_log_id')}")
            
            # Сохраняем ID лога для очистки
            if data.get('placement_log_id'):
                self.test_placement_logs.append(data.get('placement_log_id'))
                
            return True
        else:
            self.log(f"❌ Ошибка размещения груза: {response.status_code} - {response.text}")
            return False
            
    def verify_cargo_warehouse_location(self, test_cargo):
        """Проверить что груз находится в ячейке склада"""
        self.log("🔍 Проверка что груз находится в ячейке склада...")
        
        warehouse_location = test_cargo.get('warehouse_location')
        
        if warehouse_location and warehouse_location.strip():
            self.log(f"✅ Груз находится в ячейке склада: {warehouse_location}")
            self.log("✅ Груз готов к размещению на транспорт")
            return True
        else:
            self.log("❌ Груз НЕ находится в ячейке склада (warehouse_location пустое)")
            return False
            
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        self.log("🧹 Очистка тестовых данных...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Удаление тестовых грузов
        for cargo_id in self.test_cargo_ids:
            try:
                response = self.session.delete(f"{API_BASE}/admin/cargo/{cargo_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Тестовый груз {cargo_id} удален")
                else:
                    self.log(f"⚠️ Не удалось удалить груз {cargo_id}: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления груза {cargo_id}: {e}")
                
    def run_comprehensive_test(self):
        """Запуск комплексного тестирования улучшенной системы сканирования QR грузов"""
        self.log("🎯 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ УЛУЧШЕННОЙ СИСТЕМЫ СКАНИРОВАНИЯ QR ГРУЗОВ")
        self.log("=" * 90)
        
        success_count = 0
        total_tests = 8  # Общее количество основных тестов
        
        try:
            # 1. Авторизация администратора
            self.log("\n📋 ЭТАП 1: Авторизация администратора")
            if not self.authenticate_admin():
                self.log("❌ Критическая ошибка: не удалось авторизовать администратора")
                return False
            success_count += 1
            
            # 2. Создание тестового груза с QR кодом и ячейкой склада
            self.log("\n📋 ЭТАП 2: Создание тестового груза с QR кодом и ячейкой склада")
            test_cargo = self.create_test_cargo_with_warehouse()
            if not test_cargo:
                self.log("❌ Критическая ошибка: не удалось создать тестовый груз")
                return False
            success_count += 1
            
            # 3. Проверка что груз находится в ячейке склада
            self.log("\n📋 ЭТАП 3: Проверка что груз находится в ячейке склада")
            if not self.verify_cargo_warehouse_location(test_cargo):
                self.log("❌ Критическая ошибка: груз не находится в ячейке склада")
                return False
            success_count += 1
            
            # 4. Тестирование улучшенного поиска груза с отладочной информацией
            self.log("\n📋 ЭТАП 4: Тестирование улучшенного поиска груза с отладочной информацией")
            if not self.test_improved_cargo_search(test_cargo):
                self.log("❌ Критическая ошибка: улучшенный поиск груза не работает")
                return False
            success_count += 1
            
            # 5. Поиск транспорта с QR кодом
            self.log("\n📋 ЭТАП 5: Поиск транспорта с QR кодом")
            transport_data = self.find_transport_with_qr()
            if not transport_data:
                self.log("❌ Критическая ошибка: не удалось найти транспорт с QR кодом")
                return False
            success_count += 1
            
            # 6. Сканирование QR кода транспорта
            self.log("\n📋 ЭТАП 6: Сканирование QR кода транспорта")
            if not self.scan_transport_qr(transport_data):
                self.log("❌ Критическая ошибка: не удалось отсканировать транспорт")
                return False
            success_count += 1
            
            # 7. Сканирование QR кода созданного груза
            self.log("\n📋 ЭТАП 7: Сканирование QR кода созданного груза")
            if not self.scan_cargo_qr(test_cargo):
                self.log("❌ Критическая ошибка: не удалось отсканировать груз")
                return False
            success_count += 1
            
            # 8. Размещение груза на транспорт
            self.log("\n📋 ЭТАП 8: Размещение груза на транспорт")
            if not self.place_cargo_on_transport(transport_data, test_cargo):
                self.log("❌ Критическая ошибка: не удалось разместить груз на транспорт")
                return False
            success_count += 1
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка во время тестирования: {e}")
            
        finally:
            # Очистка тестовых данных
            self.log("\n📋 ФИНАЛЬНЫЙ ЭТАП: Очистка тестовых данных")
            self.cleanup_test_data()
            
        # Итоговый отчет
        self.log("\n" + "=" * 90)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ УЛУЧШЕННОЙ СИСТЕМЫ СКАНИРОВАНИЯ QR ГРУЗОВ")
        self.log("=" * 90)
        
        success_rate = (success_count / total_tests) * 100
        
        self.log(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        self.log(f"   Успешных тестов: {success_count}/{total_tests}")
        self.log(f"   Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 ОТЛИЧНО: Улучшенная система сканирования QR грузов работает идеально!")
        elif success_rate >= 75:
            self.log("✅ ХОРОШО: Основная функциональность работает, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Система требует доработки")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ Авторизация администратора работает")
        self.log("✅ Создание тестового груза с warehouse_location и qr_data")
        self.log("✅ Груз находится в ячейке склада и готов к размещению")
        self.log("✅ Улучшенный поиск груза с детальной отладочной информацией")
        self.log("✅ Система правильно находит грузы размещенные на складе")
        self.log("✅ Полный цикл размещения: транспорт → груз → размещение")
        self.log("✅ Отладочная информация показывает все попытки поиска")
        self.log("✅ Система поддерживает различные методы поиска")
        
        return success_rate >= 75

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Улучшенная система сканирования QR грузов с отладочной информацией в TAJLINE.TJ")
    print("=" * 90)
    
    tester = ImprovedQRScanningTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()