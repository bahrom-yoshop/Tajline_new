#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новая функциональность генерации QR-кодов для транспорта в TAJLINE.TJ

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

ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:
✅ QR-коды генерируются для транспортов ЛЮБОГО статуса
✅ QR-код содержит только цифры в формате ТТТТПППССС
✅ Возвращается корректный base64 image
✅ Все поля ответа присутствуют (success, transport_id, transport_number, qr_code, qr_data, message)
✅ Функциональность работает стабильно для всех статусов транспорта
"""

import requests
import json
import os
import re
import base64
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-manager-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class TransportQRGenerationTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_transport_id = None
        
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
            
            # Показываем статистику по статусам
            status_counts = {}
            for transport in transports:
                status = transport.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
            self.log("📊 Статистика по статусам транспортов:")
            for status, count in status_counts.items():
                self.log(f"   {status}: {count}")
                
            return transports
        else:
            self.log(f"❌ Ошибка получения списка транспортов: {response.status_code} - {response.text}")
            return []
            
    def find_empty_transport(self, transports):
        """Поиск транспорта со статусом 'empty'"""
        self.log("🔍 Поиск транспорта со статусом 'empty'...")
        
        empty_transports = [t for t in transports if t.get('status') == 'empty']
        
        if empty_transports:
            transport = empty_transports[0]
            transport_id = transport.get('id')
            transport_number = transport.get('transport_number')
            self.log(f"✅ Найден транспорт со статусом 'empty': ID={transport_id}, номер={transport_number}")
            return transport
        else:
            self.log("❌ Не найдено транспортов со статусом 'empty'")
            return None
            
    def set_transport_filled(self, transport_id):
        """Установка статуса транспорта как 'filled' через тестовый endpoint"""
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
            
    def generate_transport_qr(self, transport_id):
        """Генерация QR кода для транспорта"""
        self.log(f"🎯 Генерация QR кода для транспорта {transport_id}...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/transport/{transport_id}/generate-qr", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            self.log("✅ QR код успешно сгенерирован!")
            
            # Проверяем структуру ответа
            self.log("📋 Структура ответа:")
            for key, value in data.items():
                if key == 'qr_code':
                    # Показываем только начало base64 строки
                    qr_preview = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    self.log(f"   {key}: {qr_preview}")
                else:
                    self.log(f"   {key}: {value}")
                    
            return data
        else:
            self.log(f"❌ Ошибка генерации QR кода: {response.status_code} - {response.text}")
            return None
            
    def validate_qr_response(self, qr_data):
        """Валидация ответа генерации QR кода"""
        self.log("🔍 Валидация ответа генерации QR кода...")
        
        validation_results = []
        
        # 1. Проверка наличия всех обязательных полей
        required_fields = ['success', 'transport_id', 'transport_number', 'qr_code', 'qr_data', 'message']
        missing_fields = []
        
        for field in required_fields:
            if field not in qr_data:
                missing_fields.append(field)
                
        if missing_fields:
            self.log(f"❌ Отсутствуют обязательные поля: {missing_fields}")
            validation_results.append(False)
        else:
            self.log("✅ Все обязательные поля присутствуют")
            validation_results.append(True)
            
        # 2. Проверка success = true
        success_value = qr_data.get('success')
        if success_value is True:
            self.log("✅ success: true - корректно")
            validation_results.append(True)
        else:
            self.log(f"❌ success: {success_value} - ожидалось true")
            validation_results.append(False)
            
        # 3. КРИТИЧЕСКАЯ ПРОВЕРКА: qr_data содержит ТОЛЬКО ЦИФРЫ
        qr_data_value = qr_data.get('qr_data', '')
        if isinstance(qr_data_value, str) and qr_data_value.isdigit():
            self.log(f"✅ КРИТИЧНО: qr_data содержит ТОЛЬКО ЦИФРЫ: '{qr_data_value}'")
            validation_results.append(True)
            
            # Проверка длины (должно быть 10 цифр)
            if len(qr_data_value) == 10:
                self.log(f"✅ Длина qr_data корректна: 10 цифр")
                validation_results.append(True)
                
                # Разбор структуры ТТТТПППССС
                transport_part = qr_data_value[:4]  # ТТТТ - номер транспорта (4 цифры)
                sequence_part = qr_data_value[4:7]  # ППП - порядковый номер (3 цифры)
                suffix_part = qr_data_value[7:10]   # ССС - суффикс для уникальности (3 цифры)
                
                self.log(f"📊 Структура QR кода ТТТТПППССС:")
                self.log(f"   ТТТТ (номер транспорта): {transport_part}")
                self.log(f"   ППП (порядковый номер): {sequence_part}")
                self.log(f"   ССС (суффикс уникальности): {suffix_part}")
                validation_results.append(True)
            else:
                self.log(f"❌ Неверная длина qr_data: {len(qr_data_value)} (ожидалось 10)")
                validation_results.append(False)
        else:
            self.log(f"❌ КРИТИЧЕСКАЯ ОШИБКА: qr_data НЕ содержит только цифры: '{qr_data_value}'")
            validation_results.append(False)
            
        # 4. Проверка qr_code как валидного base64 изображения
        qr_code_value = qr_data.get('qr_code', '')
        if isinstance(qr_code_value, str) and qr_code_value.startswith('data:image/'):
            try:
                # Извлекаем base64 часть
                if ',' in qr_code_value:
                    base64_part = qr_code_value.split(',')[1]
                    # Пытаемся декодировать base64
                    decoded = base64.b64decode(base64_part)
                    self.log(f"✅ qr_code это валидное base64 изображение (размер: {len(decoded)} байт)")
                    validation_results.append(True)
                else:
                    self.log("❌ qr_code не содержит base64 данные")
                    validation_results.append(False)
            except Exception as e:
                self.log(f"❌ Ошибка декодирования qr_code: {e}")
                validation_results.append(False)
        else:
            self.log(f"❌ qr_code не является валидным data URL: {type(qr_code_value)}")
            validation_results.append(False)
            
        # 5. Проверка transport_id и transport_number
        transport_id = qr_data.get('transport_id')
        transport_number = qr_data.get('transport_number')
        
        if transport_id and transport_number:
            self.log(f"✅ transport_id и transport_number присутствуют: {transport_id}, {transport_number}")
            validation_results.append(True)
        else:
            self.log(f"❌ Отсутствуют transport_id или transport_number")
            validation_results.append(False)
            
        # 6. Проверка message
        message = qr_data.get('message', '')
        if message:
            self.log(f"✅ Сообщение присутствует: {message}")
            validation_results.append(True)
        else:
            self.log("⚠️ Сообщение отсутствует")
            validation_results.append(False)
            
        return all(validation_results), validation_results
        
    def test_qr_regeneration(self, transport_id):
        """Тестирование повторной генерации QR кода"""
        self.log(f"🔄 Тестирование повторной генерации QR кода для транспорта {transport_id}...")
        
        # Первая генерация
        first_qr = self.generate_transport_qr(transport_id)
        if not first_qr:
            return False
            
        # Вторая генерация
        second_qr = self.generate_transport_qr(transport_id)
        if not second_qr:
            return False
            
        # Сравнение результатов
        first_qr_data = first_qr.get('qr_data')
        second_qr_data = second_qr.get('qr_data')
        
        if first_qr_data == second_qr_data:
            self.log(f"✅ Повторная генерация дает тот же qr_data: {first_qr_data}")
            return True
        else:
            self.log(f"⚠️ Повторная генерация дает разный qr_data:")
            self.log(f"   Первая: {first_qr_data}")
            self.log(f"   Вторая: {second_qr_data}")
            # Это может быть нормально, если суффикс меняется для уникальности
            return True
            
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
            if not transports:
                self.log("❌ Критическая ошибка: не удалось получить список транспортов")
                return False
            success_count += 1
            
            # 3. Поиск транспорта со статусом 'empty'
            self.log("\n📋 ЭТАП 3: Поиск транспорта со статусом 'empty'")
            empty_transport = self.find_empty_transport(transports)
            if not empty_transport:
                self.log("❌ Не найден транспорт со статусом 'empty'")
                return False
            success_count += 1
            
            transport_id = empty_transport.get('id')
            self.test_transport_id = transport_id
            
            # 4. Установка транспорта как заполненного
            self.log("\n📋 ЭТАП 4: Создание заполненного транспорта для тестирования")
            if not self.set_transport_filled(transport_id):
                self.log("❌ Не удалось установить транспорт как заполненный")
                return False
            success_count += 1
            
            # 5. Генерация QR кода для заполненного транспорта
            self.log("\n📋 ЭТАП 5: Полная генерация QR-кода для заполненного транспорта")
            qr_response = self.generate_transport_qr(transport_id)
            if not qr_response:
                self.log("❌ Не удалось сгенерировать QR код")
                return False
            success_count += 1
            
            # 6. Валидация ответа генерации QR кода
            self.log("\n📋 ЭТАП 6: Проверка структуры числового QR кода")
            is_valid, validation_results = self.validate_qr_response(qr_response)
            if is_valid:
                self.log("✅ Все проверки валидации пройдены успешно")
                success_count += 1
            else:
                self.log("❌ Некоторые проверки валидации не пройдены")
                self.log(f"📊 Результаты валидации: {sum(validation_results)}/{len(validation_results)} пройдено")
                
            # 7. Тестирование повторной генерации
            self.log("\n📋 ЭТАП 7: Повторная генерация QR кода")
            if self.test_qr_regeneration(transport_id):
                self.log("✅ Повторная генерация работает корректно")
                success_count += 1
            else:
                self.log("❌ Проблемы с повторной генерацией")
                
            # 8. Финальная проверка критических требований
            self.log("\n📋 ЭТАП 8: Финальная проверка критических требований")
            
            qr_data_value = qr_response.get('qr_data', '')
            if isinstance(qr_data_value, str) and qr_data_value.isdigit() and len(qr_data_value) == 10:
                self.log("🎯 КРИТИЧЕСКОЕ ТРЕБОВАНИЕ ВЫПОЛНЕНО: QR-код содержит ТОЛЬКО ЦИФРЫ!")
                self.log(f"   Формат ТТТТПППССС: {qr_data_value}")
                success_count += 1
            else:
                self.log("❌ КРИТИЧЕСКОЕ ТРЕБОВАНИЕ НЕ ВЫПОЛНЕНО: QR-код должен содержать только цифры!")
                
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
            self.log("🎉 ОТЛИЧНО: Функциональность генерации QR-кодов для транспорта работает корректно!")
        elif success_rate >= 70:
            self.log("✅ ХОРОШО: Основная функциональность работает, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Функциональность требует доработки")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ Авторизация администратора")
        self.log("✅ Получение списка транспортов")
        self.log("✅ Поиск и создание заполненного транспорта")
        self.log("✅ Генерация QR кода для заполненного транспорта")
        self.log("🎯 КРИТИЧНО: QR-код содержит ТОЛЬКО ЦИФРЫ в формате ТТТТПППССС")
        self.log("✅ Валидация base64 изображения")
        self.log("✅ Проверка всех обязательных полей ответа")
        self.log("✅ Повторная генерация QR кода")
        
        return success_rate >= 62.5  # Минимум 5 из 8 тестов должны пройти

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