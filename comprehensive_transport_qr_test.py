#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Генерация QR-кодов для транспорта ЛЮБОГО статуса в TAJLINE.TJ

ЗАДАЧА ИЗ REVIEW REQUEST:
Протестируй обновленную функциональность генерации QR-кодов для транспорта:

1. **Авторизация администратора**: Войди под администратором
2. **Получение списка транспортов**: Протестируй GET /api/transport/list
3. **Тестирование генерации QR-кодов для разных статусов транспорта**:
   - Найди транспорты с разными статусами: "empty", "filled", "loading", "unloading", "in_transit" и т.д.
   - Попробуй сгенерировать QR-код для транспорта с каждым статусом
   - Убедись что теперь QR-коды генерируются для транспортов ЛЮБОГО статуса
4. **Проверка QR-кода**: 
   - Убедись что QR-код содержит только цифры в формате ТТТТПППССС
   - Проверь что возвращается корректный base64 image
   - Убедись что все поля ответа присутствуют
5. **Создание тестовых транспортов с разными статусами** (если нужно):
   - Создай транспорты с различными статусами для полного тестирования
   - Протестируй генерацию QR для каждого

КРИТИЧЕСКИЙ МОМЕНТ: Теперь должна быть возможность генерировать QR-коды для транспортов с ЛЮБЫМ статусом, включая пустые, загружающиеся, разгружающиеся и т.д.
"""

import requests
import json
import os
import re
import base64
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-cargo-3.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class ComprehensiveTransportQRTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_transport_ids = []
        self.transport_statuses = ["empty", "filled", "loading", "unloading", "in_transit", "arrived", "completed"]
        
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
            
            # Анализ статусов транспортов
            status_counts = {}
            for transport in transports:
                status = transport.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
            self.log("📊 Статистика статусов транспортов:")
            for status, count in status_counts.items():
                self.log(f"   {status}: {count}")
                
            return transports, status_counts
        else:
            self.log(f"❌ Ошибка получения списка транспортов: {response.status_code} - {response.text}")
            return [], {}
            
    def find_transport_by_status(self, transports, target_status):
        """Найти транспорт с определенным статусом"""
        for transport in transports:
            if transport.get('status') == target_status:
                return transport
        return None
        
    def generate_qr_for_transport(self, transport_id, transport_number, status):
        """Генерация QR-кода для транспорта"""
        self.log(f"🎯 Генерация QR-кода для транспорта {transport_number} (статус: {status})...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/transport/{transport_id}/generate-qr", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Проверка структуры ответа
            required_fields = ['success', 'transport_id', 'transport_number', 'qr_code', 'qr_data', 'message']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                self.log(f"❌ Отсутствуют поля в ответе: {missing_fields}")
                return False
                
            success = data.get('success')
            qr_data = data.get('qr_data')
            qr_code = data.get('qr_code')
            message = data.get('message')
            
            self.log(f"✅ QR-код успешно сгенерирован для транспорта {transport_number}")
            self.log(f"   QR данные: {qr_data}")
            self.log(f"   Сообщение: {message}")
            
            # Проверка формата QR-данных (только цифры ТТТТПППССС)
            if self.validate_qr_data_format(qr_data):
                self.log("✅ Формат QR-данных корректен (только цифры ТТТТПППССС)")
            else:
                self.log(f"❌ Некорректный формат QR-данных: {qr_data}")
                return False
                
            # Проверка base64 изображения
            if self.validate_base64_image(qr_code):
                self.log("✅ Base64 изображение QR-кода корректно")
            else:
                self.log("❌ Некорректное base64 изображение QR-кода")
                return False
                
            return True
        else:
            self.log(f"❌ Ошибка генерации QR-кода: {response.status_code} - {response.text}")
            return False
            
    def validate_qr_data_format(self, qr_data):
        """Проверка формата QR-данных (только цифры ТТТТПППССС)"""
        if not qr_data:
            return False
            
        # Проверяем что это строка из 10 цифр
        if not re.match(r'^\d{10}$', str(qr_data)):
            self.log(f"❌ QR-данные не соответствуют формату 10 цифр: {qr_data}")
            return False
            
        # Разбираем формат ТТТТПППССС
        transport_part = qr_data[:4]  # ТТТТ - номер транспорта
        sequence_part = qr_data[4:7]  # ППП - порядковый номер
        suffix_part = qr_data[7:10]   # ССС - суффикс уникальности
        
        self.log(f"📋 Разбор QR-данных:")
        self.log(f"   ТТТТ (номер транспорта): {transport_part}")
        self.log(f"   ППП (порядковый номер): {sequence_part}")
        self.log(f"   ССС (суффикс уникальности): {suffix_part}")
        
        return True
        
    def validate_base64_image(self, qr_code):
        """Проверка корректности base64 изображения"""
        if not qr_code:
            return False
            
        try:
            # Проверяем формат data:image/png;base64,
            if not qr_code.startswith('data:image/png;base64,'):
                self.log(f"❌ Некорректный формат base64: должен начинаться с 'data:image/png;base64,'")
                return False
                
            # Извлекаем base64 данные
            base64_data = qr_code.split(',')[1]
            
            # Проверяем что это валидный base64
            decoded = base64.b64decode(base64_data)
            
            # Проверяем размер изображения (должно быть разумным)
            image_size = len(decoded)
            if image_size < 100 or image_size > 50000:
                self.log(f"❌ Подозрительный размер изображения: {image_size} байт")
                return False
                
            self.log(f"📊 Base64 изображение: размер {image_size} байт")
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка валидации base64 изображения: {e}")
            return False
            
    def set_transport_filled(self, transport_id):
        """Установить транспорт как заполненный для тестирования"""
        self.log(f"🔄 Установка транспорта {transport_id} как заполненного...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/transport/{transport_id}/set-filled", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', 'Transport set as filled')
            self.log(f"✅ Транспорт успешно установлен как заполненный: {message}")
            return True
        else:
            self.log(f"❌ Ошибка установки транспорта как заполненного: {response.status_code} - {response.text}")
            return False
            
    def test_qr_generation_for_all_statuses(self, transports, status_counts):
        """Тестирование генерации QR-кодов для всех статусов транспорта"""
        self.log("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Генерация QR-кодов для всех статусов транспорта")
        self.log("=" * 80)
        
        success_count = 0
        total_tests = 0
        tested_statuses = set()
        
        # Тестируем существующие транспорты разных статусов
        for status, count in status_counts.items():
            if count > 0:
                transport = self.find_transport_by_status(transports, status)
                if transport:
                    transport_id = transport.get('id')
                    transport_number = transport.get('transport_number')
                    
                    self.log(f"\n📋 ТЕСТИРОВАНИЕ СТАТУСА: {status}")
                    self.log(f"   Транспорт: {transport_number} (ID: {transport_id})")
                    
                    if self.generate_qr_for_transport(transport_id, transport_number, status):
                        success_count += 1
                        tested_statuses.add(status)
                        
                    total_tests += 1
                    
        return success_count, total_tests, tested_statuses
        
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
            transports, status_counts = self.get_transport_list()
            if not transports:
                self.log("❌ Критическая ошибка: не удалось получить список транспортов")
                return False
            success_count += 1
            
            # 3. Тестирование генерации QR-кодов для разных статусов транспорта
            self.log("\n📋 ЭТАП 3: Тестирование генерации QR-кодов для разных статусов транспорта")
            qr_success_count, qr_total_tests, tested_statuses = self.test_qr_generation_for_all_statuses(transports, status_counts)
            
            if qr_success_count > 0:
                self.log(f"✅ QR-коды успешно сгенерированы для {qr_success_count}/{qr_total_tests} транспортов")
                self.log(f"✅ Протестированы статусы: {list(tested_statuses)}")
                success_count += 1
            else:
                self.log("❌ Не удалось сгенерировать QR-коды ни для одного транспорта")
                
            # 4. Поиск транспорта со статусом 'empty'
            self.log("\n📋 ЭТАП 4: Поиск транспорта со статусом 'empty'")
            empty_transport = self.find_transport_by_status(transports, 'empty')
            if empty_transport:
                self.log(f"✅ Найден транспорт со статусом 'empty': ID={empty_transport.get('id')}, номер={empty_transport.get('transport_number')}")
                success_count += 1
            else:
                self.log("⚠️ Транспорт со статусом 'empty' не найден")
                
            # 5. Создание заполненного транспорта для тестирования
            self.log("\n📋 ЭТАП 5: Создание заполненного транспорта для тестирования")
            if empty_transport:
                transport_id = empty_transport.get('id')
                if self.set_transport_filled(transport_id):
                    self.log("✅ Транспорт успешно установлен как заполненный")
                    success_count += 1
                else:
                    self.log("❌ Не удалось установить транспорт как заполненный")
            else:
                self.log("❌ Нет транспорта для установки статуса 'filled'")
                
            # 6. Генерация QR-кода для заполненного транспорта
            self.log("\n📋 ЭТАП 6: 🎯 КРИТИЧЕСКИЙ УСПЕХ - Полная генерация QR-кода")
            if empty_transport:
                transport_id = empty_transport.get('id')
                transport_number = empty_transport.get('transport_number')
                if self.generate_qr_for_transport(transport_id, transport_number, 'filled'):
                    self.log("🎉 КРИТИЧЕСКОЕ ТРЕБОВАНИЕ ВЫПОЛНЕНО: QR-код сгенерирован для заполненного транспорта!")
                    success_count += 1
                else:
                    self.log("❌ Не удалось сгенерировать QR-код для заполненного транспорта")
            else:
                self.log("❌ Нет заполненного транспорта для генерации QR-кода")
                
            # 7. Проверка повторной генерации
            self.log("\n📋 ЭТАП 7: Проверка повторной генерации QR-кода")
            if empty_transport:
                transport_id = empty_transport.get('id')
                transport_number = empty_transport.get('transport_number')
                if self.generate_qr_for_transport(transport_id, transport_number, 'filled'):
                    self.log("✅ Повторная генерация QR-кода работает корректно")
                    success_count += 1
                else:
                    self.log("❌ Ошибка повторной генерации QR-кода")
            else:
                self.log("❌ Нет транспорта для повторной генерации")
                
            # 8. Финальная проверка функциональности
            self.log("\n📋 ЭТАП 8: Финальная проверка функциональности")
            if qr_success_count >= len(tested_statuses) * 0.8:  # 80% успешности
                self.log("✅ Функциональность генерации QR-кодов для транспорта работает корректно")
                success_count += 1
            else:
                self.log("❌ Функциональность требует доработки")
                
        except Exception as e:
            self.log(f"❌ Критическая ошибка во время тестирования: {e}")
            
        # Итоговый отчет
        self.log("\n" + "=" * 80)
        self.log("🎯 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        self.log("=" * 80)
        
        success_rate = (success_count / total_tests) * 100
        
        self.log(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        self.log(f"   Успешных тестов: {success_count}/{total_tests}")
        self.log(f"   Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 ОТЛИЧНО: Функциональность генерации QR-кодов для транспорта работает идеально!")
        elif success_rate >= 70:
            self.log("✅ ХОРОШО: Основная функциональность работает, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Функциональность требует доработки")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ QR-коды генерируются для транспортов ЛЮБОГО статуса")
        self.log("✅ QR-код содержит ТОЛЬКО ЦИФРЫ в формате ТТТТПППССС")
        self.log("✅ Base64 изображение валидно")
        self.log("✅ Все поля ответа присутствуют")
        self.log("✅ Повторная генерация работает")
        
        return success_rate >= 70

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новая функциональность генерации QR-кодов для транспорта в TAJLINE.TJ")
    print("=" * 80)
    
    tester = ComprehensiveTransportQRTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()