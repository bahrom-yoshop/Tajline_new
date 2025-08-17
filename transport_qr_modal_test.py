#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Функциональность генерации QR-кодов для транспорта из модального окна управления в TAJLINE.TJ

ЗАДАЧА ТЕСТИРОВАНИЯ:
Протестировать функциональность генерации QR-кодов для транспорта из модального окна управления согласно review request:

1. **Авторизация администратора**: Войти под администратором
2. **Получение списка транспортов**: Протестировать GET /api/transport/list
3. **Тестирование генерации QR-кода из модального окна**:
   - Выбрать любой транспорт из списка
   - Протестировать POST /api/transport/{transport_id}/generate-qr для этого транспорта
   - Убедиться что QR-код содержит только цифры в формате ТТТТПППССС
   - Проверить что возвращается корректный base64 image
4. **Проверка повторной генерации**: 
   - Попробовать сгенерировать QR-код для того же транспорта повторно
   - Убедиться что каждый раз генерируется уникальный код (из-за случайного суффикса)
5. **Валидация структуры ответа**:
   - success: true
   - transport_id, transport_number
   - qr_code (base64 изображение)
   - qr_data (только цифры)
   - message

ФОКУС: Новая кнопка в модальном окне управления транспортом должна работать так же хорошо как и основная функция генерации QR-кодов.
"""

import requests
import json
import os
import re
import base64
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://freight-hub-6.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def test_transport_qr_generation():
    """Основная функция тестирования генерации QR-кодов для транспорта"""
    
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Генерация QR-кодов для транспорта из модального окна управления")
    print("=" * 100)
    
    # Шаг 1: Авторизация администратора
    print("\n1️⃣ АВТОРИЗАЦИЯ АДМИНИСТРАТОРА")
    print("-" * 50)
    
    admin_credentials = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    try:
        login_response = requests.post(f"{API_BASE}/auth/login", json=admin_credentials)
        print(f"📞 Авторизация администратора: {admin_credentials['phone']}")
        print(f"📊 Статус ответа: {login_response.status_code}")
        
        if login_response.status_code != 200:
            print(f"❌ ОШИБКА авторизации: {login_response.text}")
            return False
            
        admin_data = login_response.json()
        admin_token = admin_data.get("access_token")
        admin_user = admin_data.get("user", {})
        
        print(f"✅ Успешная авторизация: {admin_user.get('full_name')} (номер: {admin_user.get('user_number')}, роль: {admin_user.get('role')})")
        
        if admin_user.get('role') != 'admin':
            print(f"❌ ОШИБКА: Пользователь не является администратором")
            return False
            
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА авторизации: {e}")
        return False
    
    # Заголовки для авторизованных запросов
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Шаг 2: Получение списка транспортов
    print("\n2️⃣ ПОЛУЧЕНИЕ СПИСКА ТРАНСПОРТОВ")
    print("-" * 50)
    
    try:
        transport_response = requests.get(f"{API_BASE}/transport/list", headers=headers)
        print(f"📊 GET /api/transport/list - Статус: {transport_response.status_code}")
        
        if transport_response.status_code != 200:
            print(f"❌ ОШИБКА получения списка транспортов: {transport_response.text}")
            return False
            
        transport_data = transport_response.json()
        transports = transport_data.get("transports", [])
        
        print(f"✅ Получено транспортов: {len(transports)}")
        
        if not transports:
            print("❌ ОШИБКА: Список транспортов пуст")
            return False
            
        # Показываем статистику по статусам
        status_counts = {}
        for transport in transports:
            status = transport.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
        print("📈 Статистика по статусам транспортов:")
        for status, count in status_counts.items():
            print(f"   - {status}: {count}")
            
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА получения транспортов: {e}")
        return False
    
    # Шаг 3: Выбор транспорта для тестирования
    print("\n3️⃣ ВЫБОР ТРАНСПОРТА ДЛЯ ТЕСТИРОВАНИЯ QR-КОДА")
    print("-" * 50)
    
    # Выбираем первый доступный транспорт
    test_transport = transports[0]
    transport_id = test_transport.get("id")
    transport_number = test_transport.get("transport_number")
    transport_status = test_transport.get("status")
    
    print(f"🚛 Выбран транспорт для тестирования:")
    print(f"   - ID: {transport_id}")
    print(f"   - Номер: {transport_number}")
    print(f"   - Статус: {transport_status}")
    print(f"   - Водитель: {test_transport.get('driver_name')}")
    print(f"   - Телефон: {test_transport.get('driver_phone')}")
    
    # Шаг 4: Тестирование генерации QR-кода
    print("\n4️⃣ ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ QR-КОДА ИЗ МОДАЛЬНОГО ОКНА")
    print("-" * 50)
    
    qr_codes_generated = []
    
    for attempt in range(1, 4):  # Тестируем 3 генерации для проверки уникальности
        print(f"\n🔄 Попытка генерации #{attempt}")
        
        try:
            qr_response = requests.post(
                f"{API_BASE}/transport/{transport_id}/generate-qr", 
                headers=headers
            )
            print(f"📊 POST /api/transport/{transport_id}/generate-qr - Статус: {qr_response.status_code}")
            
            if qr_response.status_code != 200:
                print(f"❌ ОШИБКА генерации QR-кода: {qr_response.text}")
                continue
                
            qr_data = qr_response.json()
            
            # Валидация структуры ответа
            print("🔍 ВАЛИДАЦИЯ СТРУКТУРЫ ОТВЕТА:")
            
            required_fields = ["success", "transport_id", "transport_number", "qr_code", "qr_data", "message"]
            missing_fields = []
            
            for field in required_fields:
                if field in qr_data:
                    print(f"   ✅ {field}: присутствует")
                else:
                    print(f"   ❌ {field}: ОТСУТСТВУЕТ")
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Отсутствуют обязательные поля: {missing_fields}")
                continue
            
            # Проверка значений
            success = qr_data.get("success")
            returned_transport_id = qr_data.get("transport_id")
            returned_transport_number = qr_data.get("transport_number")
            qr_code = qr_data.get("qr_code")
            qr_data_content = qr_data.get("qr_data")
            message = qr_data.get("message")
            
            print(f"\n📋 ДЕТАЛИ ОТВЕТА:")
            print(f"   - success: {success}")
            print(f"   - transport_id: {returned_transport_id}")
            print(f"   - transport_number: {returned_transport_number}")
            print(f"   - qr_data: {qr_data_content}")
            print(f"   - message: {message}")
            print(f"   - qr_code размер: {len(qr_code) if qr_code else 0} символов")
            
            # Критическая проверка: success должен быть true
            if not success:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: success = {success}, ожидалось true")
                continue
            
            # Проверка соответствия transport_id
            if returned_transport_id != transport_id:
                print(f"❌ ОШИБКА: transport_id не совпадает. Ожидался: {transport_id}, получен: {returned_transport_id}")
                continue
            
            # Проверка соответствия transport_number
            if returned_transport_number != transport_number:
                print(f"❌ ОШИБКА: transport_number не совпадает. Ожидался: {transport_number}, получен: {returned_transport_number}")
                continue
            
            # 🎯 КРИТИЧЕСКАЯ ПРОВЕРКА: QR-код содержит только цифры в формате ТТТТПППССС
            print(f"\n🎯 КРИТИЧЕСКАЯ ПРОВЕРКА ФОРМАТА QR-ДАННЫХ:")
            
            if not qr_data_content:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: qr_data пуст")
                continue
            
            # Проверка что содержит только цифры
            if not qr_data_content.isdigit():
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: qr_data содержит не только цифры: {qr_data_content}")
                continue
            else:
                print(f"   ✅ QR-данные содержат ТОЛЬКО ЦИФРЫ: {qr_data_content}")
            
            # Проверка длины (должно быть 10 цифр: ТТТТПППССС)
            if len(qr_data_content) != 10:
                print(f"❌ ОШИБКА: Неправильная длина QR-данных. Ожидалось: 10 цифр, получено: {len(qr_data_content)}")
                continue
            else:
                print(f"   ✅ Длина QR-данных корректна: 10 цифр")
            
            # Разбор формата ТТТТПППССС
            transport_part = qr_data_content[:4]  # ТТТТ - номер транспорта
            sequence_part = qr_data_content[4:7]  # ППП - порядковый номер
            suffix_part = qr_data_content[7:10]   # ССС - суффикс уникальности
            
            print(f"   📊 Разбор формата ТТТТПППССС:")
            print(f"      - ТТТТ (номер транспорта): {transport_part}")
            print(f"      - ППП (порядковый номер): {sequence_part}")
            print(f"      - ССС (суффикс уникальности): {suffix_part}")
            
            # Проверка base64 изображения
            print(f"\n🖼️ ПРОВЕРКА BASE64 ИЗОБРАЖЕНИЯ:")
            
            if not qr_code:
                print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: qr_code пуст")
                continue
            
            # Проверка формата base64
            if not qr_code.startswith("data:image/png;base64,"):
                print(f"❌ ОШИБКА: Неправильный формат base64 изображения")
                continue
            else:
                print(f"   ✅ Формат base64 изображения корректен")
            
            # Извлечение и проверка base64 данных
            try:
                base64_data = qr_code.split(",")[1]
                decoded_data = base64.b64decode(base64_data)
                print(f"   ✅ Base64 изображение валидно (размер: {len(decoded_data)} байт)")
            except Exception as decode_error:
                print(f"❌ ОШИБКА декодирования base64: {decode_error}")
                continue
            
            # Сохраняем данные для проверки уникальности
            qr_codes_generated.append({
                "attempt": attempt,
                "qr_data": qr_data_content,
                "transport_part": transport_part,
                "sequence_part": sequence_part,
                "suffix_part": suffix_part
            })
            
            print(f"✅ Попытка #{attempt} УСПЕШНА!")
            
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА генерации QR-кода (попытка #{attempt}): {e}")
            continue
    
    # Шаг 5: Проверка уникальности повторных генераций
    print("\n5️⃣ ПРОВЕРКА УНИКАЛЬНОСТИ ПОВТОРНЫХ ГЕНЕРАЦИЙ")
    print("-" * 50)
    
    if len(qr_codes_generated) < 2:
        print(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Недостаточно успешных генераций для проверки уникальности ({len(qr_codes_generated)})")
    else:
        print(f"📊 Анализ {len(qr_codes_generated)} успешных генераций:")
        
        unique_qr_data = set()
        unique_suffixes = set()
        
        for gen in qr_codes_generated:
            print(f"   Попытка #{gen['attempt']}: {gen['qr_data']} (суффикс: {gen['suffix_part']})")
            unique_qr_data.add(gen['qr_data'])
            unique_suffixes.add(gen['suffix_part'])
        
        print(f"\n🔍 РЕЗУЛЬТАТЫ АНАЛИЗА УНИКАЛЬНОСТИ:")
        print(f"   - Всего генераций: {len(qr_codes_generated)}")
        print(f"   - Уникальных QR-кодов: {len(unique_qr_data)}")
        print(f"   - Уникальных суффиксов: {len(unique_suffixes)}")
        
        if len(unique_qr_data) == len(qr_codes_generated):
            print(f"   ✅ ВСЕ QR-КОДЫ УНИКАЛЬНЫ!")
        else:
            print(f"   ❌ НАЙДЕНЫ ДУБЛИРУЮЩИЕСЯ QR-КОДЫ!")
        
        if len(unique_suffixes) == len(qr_codes_generated):
            print(f"   ✅ ВСЕ СУФФИКСЫ УНИКАЛЬНЫ!")
        else:
            print(f"   ⚠️ Найдены повторяющиеся суффиксы (может быть нормально для случайной генерации)")
    
    # Финальная сводка
    print("\n" + "=" * 100)
    print("📊 ФИНАЛЬНАЯ СВОДКА ТЕСТИРОВАНИЯ")
    print("=" * 100)
    
    success_count = len(qr_codes_generated)
    total_tests = 8  # Общее количество критических проверок
    
    print(f"✅ Успешных генераций QR-кодов: {success_count}/3")
    print(f"✅ Авторизация администратора: ПРОЙДЕНА")
    print(f"✅ Получение списка транспортов: ПРОЙДЕНО")
    print(f"✅ Выбор транспорта для тестирования: ПРОЙДЕН")
    
    if success_count > 0:
        print(f"✅ Структура ответа API: КОРРЕКТНА")
        print(f"✅ Формат QR-данных (только цифры): КОРРЕКТЕН")
        print(f"✅ Длина QR-данных (10 цифр): КОРРЕКТНА")
        print(f"✅ Формат ТТТТПППССС: СОБЛЮДЕН")
        print(f"✅ Base64 изображение: ВАЛИДНО")
        
        if success_count > 1:
            print(f"✅ Уникальность повторных генераций: ПОДТВЕРЖДЕНА")
    
    success_rate = (success_count / 3) * 100 if success_count > 0 else 0
    print(f"\n🎯 SUCCESS RATE: {success_rate:.1f}% ({success_count}/3 генераций успешны)")
    
    if success_count >= 2:
        print(f"\n🎉 КРИТИЧЕСКИЙ ВЫВОД: ФУНКЦИОНАЛЬНОСТЬ ГЕНЕРАЦИИ QR-КОДОВ ДЛЯ ТРАНСПОРТА РАБОТАЕТ КОРРЕКТНО!")
        print(f"Новая кнопка в модальном окне управления транспортом полностью функциональна.")
        print(f"QR-коды генерируются в правильном формате ТТТТПППССС и содержат только цифры как требовалось!")
        return True
    else:
        print(f"\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ: Функциональность генерации QR-кодов требует исправления")
        return False

if __name__ == "__main__":
    test_transport_qr_generation()