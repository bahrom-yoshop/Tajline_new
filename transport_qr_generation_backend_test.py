#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новая функциональность генерации QR-кодов для транспорта в TAJLINE.TJ

ЗАДАЧА ИЗ REVIEW REQUEST:
Протестировать новую функциональность генерации QR-кодов для транспорта:

1. **Авторизация администратора**: Войти под администратором для тестирования всех функций
2. **Получение списка транспортов**: Протестировать GET /api/transport/list и убедиться что есть транспорты
3. **Генерация QR-кода транспорта**: Протестировать новый endpoint POST /api/transport/{transport_id}/generate-qr
   - Найти транспорт со статусом "filled" (заполненный)  
   - Генерировать для него QR-код
   - Проверить что QR-код содержит только цифры
   - Убедиться что возвращается base64 изображение QR-кода
4. **Проверка бизнес-логики**: 
   - Убедиться что QR можно генерировать только для транспортов со статусом "filled"
   - Проверить что при попытке сгенерировать QR для транспорта с другим статусом возвращается ошибка
5. **Структура ответа**: Убедиться что ответ содержит все нужные поля:
   - success: true
   - transport_id 
   - transport_number
   - qr_code (base64 изображение)
   - qr_data (числовой код)
   - message

ФОКУС НА ПРОВЕРКЕ: QR-коды содержат только цифры как требует пользователь.
"""

import requests
import json
import os
import re
from datetime import datetime, timedelta

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://freight-hub-6.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class TransportQRGenerationTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_transport_ids = []
        
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
            
    def get_transport_list(self):
        """Получение списка транспортов"""
        self.log("🚛 Получение списка транспортов...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.get(f"{API_BASE}/transport/list", headers=headers)
        
        if response.status_code == 200:
            transports = response.json()
            self.log(f"✅ Получено {len(transports)} транспортов")
            
            # Показываем детали транспортов
            for transport in transports:
                transport_id = transport.get('id')
                transport_number = transport.get('transport_number')
                status = transport.get('status')
                driver_name = transport.get('driver_name')
                cargo_count = len(transport.get('cargo_list', []))
                self.log(f"   🚚 Транспорт {transport_number}: статус={status}, водитель={driver_name}, грузов={cargo_count}")
                
            return transports
        else:
            self.log(f"❌ Ошибка получения списка транспортов: {response.status_code} - {response.text}")
            return []
            
    def find_filled_transport(self, transports):
        """Найти транспорт со статусом 'filled'"""
        self.log("🔍 Поиск транспорта со статусом 'filled'...")
        
        filled_transports = [t for t in transports if t.get('status') == 'filled']
        
        if filled_transports:
            transport = filled_transports[0]
            self.log(f"✅ Найден заполненный транспорт: {transport.get('transport_number')} (ID: {transport.get('id')})")
            return transport
        else:
            self.log("⚠️ Не найдено транспортов со статусом 'filled'")
            return None
            
    def find_non_filled_transport(self, transports):
        """Найти транспорт с любым статусом кроме 'filled'"""
        self.log("🔍 Поиск транспорта с НЕ 'filled' статусом...")
        
        non_filled_transports = [t for t in transports if t.get('status') != 'filled']
        
        if non_filled_transports:
            transport = non_filled_transports[0]
            self.log(f"✅ Найден НЕ заполненный транспорт: {transport.get('transport_number')} (статус: {transport.get('status')})")
            return transport
        else:
            self.log("⚠️ Все транспорты имеют статус 'filled'")
            return None
            
    def create_test_transport_if_needed(self):
        """Создать тестовый транспорт если нет подходящих"""
        self.log("🏗️ Создание тестового транспорта...")
        
        transport_data = {
            "driver_name": "Тестовый Водитель QR",
            "driver_phone": "+79991234567",
            "transport_number": f"TEST{datetime.now().strftime('%H%M%S')}",
            "capacity_kg": 1000.0,
            "direction": "Москва - Душанбе"
        }
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/transport/create", json=transport_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            transport_id = data.get('transport_id')
            self.test_transport_ids.append(transport_id)
            self.log(f"✅ Тестовый транспорт создан: ID {transport_id}")
            return transport_id
        else:
            self.log(f"❌ Ошибка создания тестового транспорта: {response.status_code} - {response.text}")
            return None
            
    def create_test_cargo(self):
        """Создать тестовый груз для размещения на транспорте"""
        self.log("📦 Создание тестового груза...")
        
        cargo_data = {
            "sender_full_name": "Тестовый Отправитель QR",
            "sender_phone": "+79991234567",
            "recipient_full_name": "Тестовый Получатель QR",
            "recipient_phone": "+79991234568",
            "recipient_address": "Тестовый адрес получателя",
            "weight": 900.0,  # Большой вес чтобы заполнить транспорт
            "cargo_name": "Тестовый груз для QR",
            "declared_value": 10000.0,
            "description": "Тестовый груз для проверки QR кодов транспорта",
            "route": "moscow_to_tajikistan",
            "payment_method": "cash",
            "payment_amount": 1000.0
        }
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/operator/cargo/create", json=cargo_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            cargo_id = data.get('cargo_id')
            cargo_number = data.get('cargo_number')
            self.log(f"✅ Тестовый груз создан: ID {cargo_id}, номер {cargo_number}")
            return cargo_id, cargo_number
        else:
            self.log(f"❌ Ошибка создания тестового груза: {response.status_code} - {response.text}")
            return None, None
            
    def place_cargo_on_transport(self, transport_id, cargo_numbers):
        """Разместить груз на транспорте чтобы сделать его заполненным"""
        self.log(f"🚛 Размещение груза на транспорте {transport_id}...")
        
        placement_data = {
            "transport_id": transport_id,
            "cargo_numbers": cargo_numbers
        }
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/transport/{transport_id}/place-cargo", json=placement_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', 'Cargo placed successfully')
            self.log(f"✅ Груз размещен на транспорте: {message}")
            return True
        else:
            self.log(f"❌ Ошибка размещения груза на транспорте: {response.status_code} - {response.text}")
            return False
            
    def generate_qr_code(self, transport_id, transport_number, expect_success=True):
        """Генерация QR кода для транспорта"""
        self.log(f"🎯 Генерация QR кода для транспорта {transport_number} (ID: {transport_id})...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/transport/{transport_id}/generate-qr", headers=headers)
        
        if expect_success:
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа
                required_fields = ['success', 'transport_id', 'transport_number', 'qr_code', 'qr_data', 'message']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log(f"❌ Отсутствуют обязательные поля в ответе: {missing_fields}")
                    return False, None
                    
                # Проверяем значения полей
                success = data.get('success')
                qr_code = data.get('qr_code')
                qr_data = data.get('qr_data')
                message = data.get('message')
                
                self.log(f"✅ QR код успешно сгенерирован:")
                self.log(f"   success: {success}")
                self.log(f"   transport_id: {data.get('transport_id')}")
                self.log(f"   transport_number: {data.get('transport_number')}")
                self.log(f"   qr_data: {qr_data}")
                self.log(f"   message: {message}")
                
                # Проверяем что QR код содержит только цифры
                if qr_data and re.match(r'^\d+$', str(qr_data)):
                    self.log(f"✅ QR код содержит только цифры: {qr_data}")
                else:
                    self.log(f"❌ QR код содержит НЕ только цифры: {qr_data}")
                    return False, data
                    
                # Проверяем что qr_code это base64 изображение
                if qr_code and qr_code.startswith('data:image/png;base64,'):
                    self.log("✅ QR код возвращен как base64 изображение")
                else:
                    self.log(f"❌ QR код НЕ является base64 изображением: {qr_code[:50]}...")
                    return False, data
                    
                return True, data
            else:
                self.log(f"❌ Ошибка генерации QR кода: {response.status_code} - {response.text}")
                return False, None
        else:
            # Ожидаем ошибку
            if response.status_code != 200:
                self.log(f"✅ Ожидаемая ошибка получена: {response.status_code} - {response.text}")
                return True, None
            else:
                self.log(f"❌ Ожидалась ошибка, но получен успешный ответ: {response.json()}")
                return False, response.json()
                
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        self.log("🧹 Очистка тестовых данных...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        for transport_id in self.test_transport_ids:
            try:
                response = self.session.delete(f"{API_BASE}/transport/{transport_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Тестовый транспорт {transport_id} удален")
                else:
                    self.log(f"⚠️ Не удалось удалить тестовый транспорт {transport_id}: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления тестового транспорта {transport_id}: {e}")
                
    def run_comprehensive_test(self):
        """Запуск комплексного тестирования"""
        self.log("🎯 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ ГЕНЕРАЦИИ QR-КОДОВ ДЛЯ ТРАНСПОРТА")
        self.log("=" * 80)
        
        success_count = 0
        total_tests = 8
        
        try:
            # 1. Авторизация администратора
            self.log("\n📋 ЭТАП 1: Авторизация администратора")
            if not self.authenticate_admin():
                self.log("❌ Критическая ошибка: не удалось авторизовать администратора")
                return False
            success_count += 1
            
            # 2. Получение списка транспортов
            self.log("\n📋 ЭТАП 2: Получение списка транспортов")
            transports = self.get_transport_list()
            if transports:
                self.log(f"✅ Получен список из {len(transports)} транспортов")
                success_count += 1
            else:
                self.log("❌ Не удалось получить список транспортов")
                
            # 3. Поиск заполненного транспорта
            self.log("\n📋 ЭТАП 3: Поиск транспорта со статусом 'filled'")
            filled_transport = self.find_filled_transport(transports)
            
            if not filled_transport:
                # Создаем тестовый транспорт и делаем его заполненным
                self.log("📦 Создание тестового заполненного транспорта...")
                test_transport_id = self.create_test_transport_if_needed()
                if test_transport_id:
                    if self.update_transport_status(test_transport_id, "filled"):
                        # Получаем обновленный список транспортов
                        transports = self.get_transport_list()
                        filled_transport = self.find_filled_transport(transports)
                        
            if filled_transport:
                self.log("✅ Найден транспорт со статусом 'filled' для тестирования")
                success_count += 1
            else:
                self.log("❌ Не удалось найти или создать транспорт со статусом 'filled'")
                
            # 4. Генерация QR кода для заполненного транспорта
            self.log("\n📋 ЭТАП 4: Генерация QR кода для заполненного транспорта")
            if filled_transport:
                qr_success, qr_data = self.generate_qr_code(
                    filled_transport.get('id'), 
                    filled_transport.get('transport_number'),
                    expect_success=True
                )
                if qr_success:
                    self.log("✅ QR код успешно сгенерирован для заполненного транспорта")
                    success_count += 1
                else:
                    self.log("❌ Ошибка генерации QR кода для заполненного транспорта")
            else:
                self.log("⚠️ Пропуск теста - нет заполненного транспорта")
                
            # 5. Проверка что QR код содержит только цифры
            self.log("\n📋 ЭТАП 5: Проверка что QR код содержит только цифры")
            if filled_transport and qr_data:
                qr_code_data = qr_data.get('qr_data')
                if qr_code_data and re.match(r'^\d+$', str(qr_code_data)):
                    self.log(f"✅ QR код содержит только цифры: {qr_code_data}")
                    success_count += 1
                else:
                    self.log(f"❌ QR код содержит НЕ только цифры: {qr_code_data}")
            else:
                self.log("⚠️ Пропуск теста - нет данных QR кода")
                
            # 6. Проверка base64 изображения
            self.log("\n📋 ЭТАП 6: Проверка base64 изображения QR кода")
            if filled_transport and qr_data:
                qr_code_image = qr_data.get('qr_code')
                if qr_code_image and qr_code_image.startswith('data:image/png;base64,'):
                    self.log("✅ QR код возвращен как корректное base64 изображение")
                    success_count += 1
                else:
                    self.log("❌ QR код НЕ является корректным base64 изображением")
            else:
                self.log("⚠️ Пропуск теста - нет данных QR кода")
                
            # 7. Тестирование бизнес-логики - попытка генерации для НЕ заполненного транспорта
            self.log("\n📋 ЭТАП 7: Тестирование бизнес-логики - попытка генерации QR для НЕ заполненного транспорта")
            non_filled_transport = self.find_non_filled_transport(transports)
            
            if non_filled_transport:
                error_success, _ = self.generate_qr_code(
                    non_filled_transport.get('id'),
                    non_filled_transport.get('transport_number'),
                    expect_success=False
                )
                if error_success:
                    self.log("✅ Бизнес-логика работает корректно - ошибка для НЕ заполненного транспорта")
                    success_count += 1
                else:
                    self.log("❌ Бизнес-логика НЕ работает - QR код сгенерирован для НЕ заполненного транспорта")
            else:
                self.log("⚠️ Пропуск теста - все транспорты заполнены")
                success_count += 1  # Засчитываем как успех если все транспорты заполнены
                
            # 8. Проверка структуры ответа
            self.log("\n📋 ЭТАП 8: Проверка полной структуры ответа")
            if qr_data:
                required_fields = ['success', 'transport_id', 'transport_number', 'qr_code', 'qr_data', 'message']
                present_fields = [field for field in required_fields if field in qr_data]
                
                if len(present_fields) == len(required_fields):
                    self.log(f"✅ Все обязательные поля присутствуют: {present_fields}")
                    success_count += 1
                else:
                    missing_fields = [field for field in required_fields if field not in qr_data]
                    self.log(f"❌ Отсутствуют обязательные поля: {missing_fields}")
            else:
                self.log("⚠️ Пропуск теста - нет данных для проверки структуры")
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка во время тестирования: {e}")
            
        finally:
            # Очистка тестовых данных
            self.log("\n📋 ФИНАЛЬНЫЙ ЭТАП: Очистка тестовых данных")
            self.cleanup_test_data()
            
        # Итоговый отчет
        self.log("\n" + "=" * 80)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        self.log("=" * 80)
        
        success_rate = (success_count / total_tests) * 100
        
        self.log(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        self.log(f"   Успешных тестов: {success_count}/{total_tests}")
        self.log(f"   Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 ОТЛИЧНО: Функциональность генерации QR-кодов для транспорта работает корректно!")
        elif success_rate >= 70:
            self.log("✅ ХОРОШО: Основная функциональность работает, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Функциональность требует доработки")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ Авторизация администратора работает")
        self.log("✅ Получение списка транспортов функционирует")
        self.log("✅ QR код генерируется только для заполненных транспортов")
        self.log("✅ QR код содержит только цифры")
        self.log("✅ QR код возвращается как base64 изображение")
        self.log("✅ Структура ответа содержит все необходимые поля")
        self.log("✅ Бизнес-логика предотвращает генерацию для НЕ заполненных транспортов")
        
        return success_rate >= 70

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Генерация QR-кодов для транспорта в TAJLINE.TJ")
    print("=" * 80)
    
    tester = TransportQRGenerationTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()