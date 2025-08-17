#!/usr/bin/env python3
"""
ДИАГНОСТИКА ПРОБЛЕМЫ ДАННЫХ ПЛЕЙСХОЛДЕРА В МОДАЛЬНОМ ОКНЕ ЗАЯВКИ НА ЗАБОР ГРУЗА TAJLINE.TJ

Специальный тест для диагностики проблемы с данными плейсхолдера в модальном окне заявки на забор груза.
Цель: Выяснить почему вместо данных курьера показываются плейсхолдеры - проблема в данных или в коде заполнения формы.

КРИТИЧЕСКИЕ ПРОВЕРКИ:
1. Авторизация оператора (+79777888999/warehouse123)
2. Проверить endpoint GET /api/operator/pickup-requests/100040 - какие именно данные он возвращает
3. Проверить recipient_data (данные получателя от курьера)
4. Проверить cargo_info (информация о грузе от курьера)  
5. Проверить sender_data (данные отправителя)
6. Проверить есть ли реальные данные или только пустые поля
7. Проверить другие заявки на забор груза - найти заявку с заполненными данными получателя
8. Попробовать создать новую заявку с курьером и заполнить данные получателя
9. Проверить что курьер действительно заполнил данные получателя в своей заявке
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class PickupRequestModalDataTester:
    def __init__(self, base_url="https://tajline-manager-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🚚 ДИАГНОСТИКА ПРОБЛЕМЫ ДАННЫХ ПЛЕЙСХОЛДЕРА В МОДАЛЬНОМ ОКНЕ ЗАЯВКИ НА ЗАБОР ГРУЗА TAJLINE.TJ")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 80)

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, token: Optional[str] = None, 
                 params: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
                    return True, result
                except:
                    return True, {}
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   📄 Error: {error_detail}")
                except:
                    print(f"   📄 Raw response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"   ❌ FAILED - Exception: {str(e)}")
            return False, {}

    def test_pickup_request_modal_data_diagnosis(self):
        """Диагностика проблемы данных плейсхолдера в модальном окне заявки на забор груза"""
        print("\n🔧 ДИАГНОСТИКА ПРОБЛЕМЫ ДАННЫХ ПЛЕЙСХОЛДЕРА В МОДАЛЬНОМ ОКНЕ")
        print("   🎯 Цель: Выяснить почему вместо данных курьера показываются плейсхолдеры")
        
        all_success = True
        diagnosis_results = {}
        
        # ЭТАП 1: АВТОРИЗАЦИЯ ОПЕРАТОРА (+79777888999/warehouse123)
        print("\n   🔐 ЭТАП 1: АВТОРИЗАЦИЯ ОПЕРАТОРА (+79777888999/warehouse123)...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Авторизация оператора (+79777888999/warehouse123)",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        
        operator_token = None
        if success and 'access_token' in login_response:
            operator_token = login_response['access_token']
            operator_user = login_response.get('user', {})
            operator_role = operator_user.get('role')
            operator_name = operator_user.get('full_name')
            operator_phone = operator_user.get('phone')
            operator_user_number = operator_user.get('user_number')
            
            print(f"   ✅ Авторизация успешна: {operator_name}")
            print(f"   👑 Роль: {operator_role}")
            print(f"   📞 Телефон: {operator_phone}")
            print(f"   🆔 Номер пользователя: {operator_user_number}")
            
            self.tokens['operator'] = operator_token
            self.users['operator'] = operator_user
            
            diagnosis_results['operator_auth'] = {
                'success': True,
                'name': operator_name,
                'role': operator_role,
                'phone': operator_phone,
                'user_number': operator_user_number
            }
        else:
            print("   ❌ Авторизация оператора не удалась")
            all_success = False
            diagnosis_results['operator_auth'] = {'success': False}
            return False
        
        # ЭТАП 2: ПРОВЕРИТЬ ENDPOINT GET /api/operator/pickup-requests/100040
        print("\n   📋 ЭТАП 2: ПРОВЕРИТЬ ENDPOINT GET /api/operator/pickup-requests/100040...")
        print("   🔍 Проверяем какие именно данные возвращает endpoint для заявки 100040")
        
        success, pickup_request_100040 = self.run_test(
            "Получить данные заявки на забор груза 100040",
            "GET",
            "/api/operator/pickup-requests/100040",
            200,
            token=operator_token
        )
        
        if success:
            print("   ✅ Endpoint /api/operator/pickup-requests/100040 работает")
            print("   📄 ДЕТАЛЬНЫЙ АНАЛИЗ ДАННЫХ ЗАЯВКИ 100040:")
            
            # Анализ структуры данных
            request_data = pickup_request_100040
            
            # Проверяем основные поля заявки
            basic_fields = ['id', 'request_number', 'sender_full_name', 'sender_phone', 'pickup_address', 'pickup_date', 'status']
            print("\n   📊 ОСНОВНЫЕ ПОЛЯ ЗАЯВКИ:")
            for field in basic_fields:
                value = request_data.get(field, 'ОТСУТСТВУЕТ')
                print(f"     {field}: {value}")
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: recipient_data (данные получателя от курьера)
            print("\n   🎯 КРИТИЧЕСКАЯ ПРОВЕРКА: recipient_data (данные получателя от курьера)")
            recipient_data = request_data.get('recipient_data', {})
            if recipient_data:
                print("   ✅ recipient_data найдены:")
                for key, value in recipient_data.items():
                    print(f"     {key}: {value}")
                    
                # Проверяем заполненность данных получателя
                recipient_fields = ['recipient_full_name', 'recipient_phone', 'recipient_address']
                filled_fields = 0
                empty_fields = []
                
                for field in recipient_fields:
                    field_value = recipient_data.get(field, '')
                    if field_value and field_value.strip() and field_value not in ['', 'null', 'None', 'undefined']:
                        filled_fields += 1
                        print(f"     ✅ {field}: '{field_value}' (ЗАПОЛНЕНО)")
                    else:
                        empty_fields.append(field)
                        print(f"     ❌ {field}: '{field_value}' (ПУСТОЕ/ПЛЕЙСХОЛДЕР)")
                
                diagnosis_results['recipient_data'] = {
                    'exists': True,
                    'filled_fields': filled_fields,
                    'empty_fields': empty_fields,
                    'total_fields': len(recipient_fields),
                    'data': recipient_data
                }
                
                if filled_fields == len(recipient_fields):
                    print(f"   🎉 ВСЕ ДАННЫЕ ПОЛУЧАТЕЛЯ ЗАПОЛНЕНЫ ({filled_fields}/{len(recipient_fields)})")
                elif filled_fields > 0:
                    print(f"   ⚠️  ЧАСТИЧНО ЗАПОЛНЕНЫ ДАННЫЕ ПОЛУЧАТЕЛЯ ({filled_fields}/{len(recipient_fields)})")
                else:
                    print(f"   ❌ ВСЕ ДАННЫЕ ПОЛУЧАТЕЛЯ ПУСТЫЕ (0/{len(recipient_fields)}) - ЭТО ПРИЧИНА ПЛЕЙСХОЛДЕРОВ!")
            else:
                print("   ❌ recipient_data ОТСУТСТВУЮТ - ЭТО ПРИЧИНА ПЛЕЙСХОЛДЕРОВ!")
                diagnosis_results['recipient_data'] = {'exists': False}
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: cargo_info (информация о грузе от курьера)
            print("\n   🎯 КРИТИЧЕСКАЯ ПРОВЕРКА: cargo_info (информация о грузе от курьера)")
            cargo_info = request_data.get('cargo_info', {})
            if cargo_info:
                print("   ✅ cargo_info найдены:")
                for key, value in cargo_info.items():
                    print(f"     {key}: {value}")
                diagnosis_results['cargo_info'] = {'exists': True, 'data': cargo_info}
            else:
                print("   ❌ cargo_info ОТСУТСТВУЮТ")
                diagnosis_results['cargo_info'] = {'exists': False}
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: sender_data (данные отправителя)
            print("\n   🎯 КРИТИЧЕСКАЯ ПРОВЕРКА: sender_data (данные отправителя)")
            sender_data = request_data.get('sender_data', {})
            if sender_data:
                print("   ✅ sender_data найдены:")
                for key, value in sender_data.items():
                    print(f"     {key}: {value}")
                diagnosis_results['sender_data'] = {'exists': True, 'data': sender_data}
            else:
                # Проверяем основные поля отправителя на верхнем уровне
                sender_fields = ['sender_full_name', 'sender_phone']
                sender_info = {}
                for field in sender_fields:
                    value = request_data.get(field)
                    if value:
                        sender_info[field] = value
                
                if sender_info:
                    print("   ✅ Данные отправителя найдены на верхнем уровне:")
                    for key, value in sender_info.items():
                        print(f"     {key}: {value}")
                    diagnosis_results['sender_data'] = {'exists': True, 'data': sender_info, 'location': 'top_level'}
                else:
                    print("   ❌ sender_data ОТСУТСТВУЮТ")
                    diagnosis_results['sender_data'] = {'exists': False}
            
            diagnosis_results['request_100040'] = {
                'success': True,
                'full_data': request_data
            }
        else:
            print("   ❌ Endpoint /api/operator/pickup-requests/100040 не работает или заявка не найдена")
            diagnosis_results['request_100040'] = {'success': False}
            all_success = False
        
        # ЭТАП 3: ПРОВЕРИТЬ ДРУГИЕ ЗАЯВКИ НА ЗАБОР ГРУЗА - НАЙТИ ЗАЯВКУ С ЗАПОЛНЕННЫМИ ДАННЫМИ ПОЛУЧАТЕЛЯ
        print("\n   🔍 ЭТАП 3: ПОИСК ДРУГИХ ЗАЯВОК НА ЗАБОР ГРУЗА С ЗАПОЛНЕННЫМИ ДАННЫМИ ПОЛУЧАТЕЛЯ...")
        
        # Получаем список всех заявок на забор груза
        success, all_pickup_requests = self.run_test(
            "Получить все заявки на забор груза",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        
        if success and all_pickup_requests:
            print(f"   ✅ Найдено {len(all_pickup_requests)} уведомлений/заявок")
            
            # Ищем заявки с заполненными данными получателя
            requests_with_recipient_data = []
            requests_without_recipient_data = []
            
            # Проверяем первые 10 заявок
            requests_to_check = all_pickup_requests[:10] if len(all_pickup_requests) > 10 else all_pickup_requests
            for i, request in enumerate(requests_to_check):
                request_id = request.get('id', f'unknown_{i}')
                
                # Пытаемся получить детальную информацию о каждой заявке
                success_detail, request_detail = self.run_test(
                    f"Получить детали заявки {request_id}",
                    "GET",
                    f"/api/operator/pickup-requests/{request_id}",
                    200,
                    token=operator_token
                )
                
                if success_detail:
                    recipient_data = request_detail.get('recipient_data', {})
                    if recipient_data:
                        # Проверяем заполненность
                        recipient_fields = ['recipient_full_name', 'recipient_phone', 'recipient_address']
                        filled_count = sum(1 for field in recipient_fields 
                                         if recipient_data.get(field) and 
                                         str(recipient_data.get(field)).strip() not in ['', 'null', 'None', 'undefined'])
                        
                        if filled_count > 0:
                            requests_with_recipient_data.append({
                                'id': request_id,
                                'filled_fields': filled_count,
                                'total_fields': len(recipient_fields),
                                'recipient_data': recipient_data
                            })
                            print(f"   ✅ Заявка {request_id}: {filled_count}/{len(recipient_fields)} полей получателя заполнено")
                        else:
                            requests_without_recipient_data.append(request_id)
                            print(f"   ❌ Заявка {request_id}: данные получателя пустые")
                    else:
                        requests_without_recipient_data.append(request_id)
                        print(f"   ❌ Заявка {request_id}: recipient_data отсутствуют")
            
            diagnosis_results['other_requests'] = {
                'total_checked': len(requests_to_check),
                'with_recipient_data': len(requests_with_recipient_data),
                'without_recipient_data': len(requests_without_recipient_data),
                'filled_requests': requests_with_recipient_data
            }
            
            if requests_with_recipient_data:
                print(f"\n   🎉 НАЙДЕНО {len(requests_with_recipient_data)} ЗАЯВОК С ЗАПОЛНЕННЫМИ ДАННЫМИ ПОЛУЧАТЕЛЯ!")
                print("   📋 Примеры заполненных заявок:")
                for req in requests_with_recipient_data[:3]:  # Показываем первые 3
                    print(f"     Заявка {req['id']}: {req['filled_fields']}/{req['total_fields']} полей")
                    for field, value in req['recipient_data'].items():
                        if value and str(value).strip():
                            print(f"       {field}: {value}")
            else:
                print(f"\n   ❌ НЕ НАЙДЕНО ЗАЯВОК С ЗАПОЛНЕННЫМИ ДАННЫМИ ПОЛУЧАТЕЛЯ")
                print("   🔍 Это может указывать на системную проблему с сохранением данных получателя")
        else:
            print("   ❌ Не удалось получить список заявок на забор груза")
            diagnosis_results['other_requests'] = {'success': False}
        
        # ЭТАП 4: ПОПРОБОВАТЬ СОЗДАТЬ НОВУЮ ЗАЯВКУ С КУРЬЕРОМ И ЗАПОЛНИТЬ ДАННЫЕ ПОЛУЧАТЕЛЯ
        print("\n   🆕 ЭТАП 4: СОЗДАНИЕ НОВОЙ ЗАЯВКИ С КУРЬЕРОМ И ЗАПОЛНЕНИЕ ДАННЫХ ПОЛУЧАТЕЛЯ...")
        
        # Сначала авторизуемся как курьер
        print("\n   🔐 Авторизация курьера (+79991234567/courier123)...")
        
        courier_login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        success, courier_login_response = self.run_test(
            "Авторизация курьера (+79991234567/courier123)",
            "POST",
            "/api/auth/login",
            200,
            courier_login_data
        )
        
        courier_token = None
        if success and 'access_token' in courier_login_response:
            courier_token = courier_login_response['access_token']
            courier_user = courier_login_response.get('user', {})
            courier_name = courier_user.get('full_name')
            
            print(f"   ✅ Курьер авторизован: {courier_name}")
            self.tokens['courier'] = courier_token
            self.users['courier'] = courier_user
            
            # Создаем новую заявку на забор груза от имени оператора
            print("\n   📝 Создание новой заявки на забор груза...")
            
            new_pickup_request_data = {
                "sender_full_name": "Тест Отправитель Диагностика",
                "sender_phone": "+79991234567",
                "pickup_address": "Москва, ул. Диагностическая, 1",
                "pickup_date": "2025-01-20",
                "pickup_time_from": "10:00",
                "pickup_time_to": "18:00",
                "route": "moscow_to_tajikistan",
                "courier_fee": 500.0,
                "cargo_name": "Тестовый груз для диагностики",
                "weight": 2.0,
                "declared_value": 1000.0,
                "description": "Тест диагностики проблемы плейсхолдеров"
            }
            
            success, new_request_response = self.run_test(
                "Создать новую заявку на забор груза",
                "POST",
                "/api/admin/courier/pickup-request",
                200,
                new_pickup_request_data,
                operator_token
            )
            
            if success and 'id' in new_request_response:
                new_request_id = new_request_response['id']
                new_request_number = new_request_response.get('request_number', new_request_id)
                
                print(f"   ✅ Новая заявка создана: ID {new_request_id}, номер {new_request_number}")
                
                # Теперь курьер принимает заявку
                print(f"\n   📋 Курьер принимает заявку {new_request_id}...")
                
                success, accept_response = self.run_test(
                    f"Курьер принимает заявку {new_request_id}",
                    "POST",
                    f"/api/courier/requests/{new_request_id}/accept",
                    200,
                    token=courier_token
                )
                
                if success:
                    print("   ✅ Заявка принята курьером")
                    
                    # Курьер обновляет заявку с данными получателя
                    print(f"\n   ✏️  Курьер заполняет данные получателя в заявке {new_request_id}...")
                    
                    recipient_update_data = {
                        "recipient_full_name": "Диагностика Получатель Тестовый",
                        "recipient_phone": "+992987654321",
                        "recipient_address": "Душанбе, ул. Тестовая Диагностика, 123",
                        "cargo_items": [
                            {
                                "name": "Тестовый груз диагностики",
                                "weight": "2.0",
                                "total_price": "1000"
                            }
                        ],
                        "delivery_method": "pickup",
                        "payment_method": "cash"
                    }
                    
                    success, update_response = self.run_test(
                        f"Курьер обновляет заявку с данными получателя",
                        "PUT",
                        f"/api/courier/requests/{new_request_id}/update",
                        200,
                        recipient_update_data,
                        courier_token
                    )
                    
                    if success:
                        print("   ✅ Данные получателя обновлены курьером")
                        
                        # Проверяем, сохранились ли данные получателя
                        print(f"\n   🔍 Проверка сохранения данных получателя в заявке {new_request_id}...")
                        
                        success, updated_request = self.run_test(
                            f"Проверить обновленную заявку {new_request_id}",
                            "GET",
                            f"/api/operator/pickup-requests/{new_request_id}",
                            200,
                            token=operator_token
                        )
                        
                        if success:
                            print("   ✅ Обновленная заявка получена")
                            
                            # Анализируем сохраненные данные получателя
                            updated_recipient_data = updated_request.get('recipient_data', {})
                            if updated_recipient_data:
                                print("   🎉 ДАННЫЕ ПОЛУЧАТЕЛЯ НАЙДЕНЫ В ОБНОВЛЕННОЙ ЗАЯВКЕ:")
                                
                                recipient_fields = ['recipient_full_name', 'recipient_phone', 'recipient_address']
                                filled_count = 0
                                
                                for field in recipient_fields:
                                    value = updated_recipient_data.get(field, '')
                                    if value and str(value).strip():
                                        filled_count += 1
                                        print(f"     ✅ {field}: '{value}' (ЗАПОЛНЕНО)")
                                    else:
                                        print(f"     ❌ {field}: '{value}' (ПУСТОЕ)")
                                
                                diagnosis_results['new_request_test'] = {
                                    'success': True,
                                    'request_id': new_request_id,
                                    'recipient_data_saved': filled_count > 0,
                                    'filled_fields': filled_count,
                                    'total_fields': len(recipient_fields),
                                    'recipient_data': updated_recipient_data
                                }
                                
                                if filled_count == len(recipient_fields):
                                    print(f"   🎉 ВСЕ ДАННЫЕ ПОЛУЧАТЕЛЯ СОХРАНЕНЫ КОРРЕКТНО ({filled_count}/{len(recipient_fields)})")
                                    print("   ✅ ПРОБЛЕМА НЕ В СОХРАНЕНИИ ДАННЫХ - ПРОБЛЕМА В ОТОБРАЖЕНИИ!")
                                else:
                                    print(f"   ❌ ДАННЫЕ ПОЛУЧАТЕЛЯ СОХРАНЕНЫ ЧАСТИЧНО ({filled_count}/{len(recipient_fields)})")
                                    print("   🔍 ПРОБЛЕМА В ПРОЦЕССЕ СОХРАНЕНИЯ ДАННЫХ КУРЬЕРОМ")
                            else:
                                print("   ❌ ДАННЫЕ ПОЛУЧАТЕЛЯ НЕ НАЙДЕНЫ В ОБНОВЛЕННОЙ ЗАЯВКЕ")
                                print("   🔍 ПРОБЛЕМА В СОХРАНЕНИИ ДАННЫХ ПОЛУЧАТЕЛЯ")
                                diagnosis_results['new_request_test'] = {
                                    'success': True,
                                    'request_id': new_request_id,
                                    'recipient_data_saved': False
                                }
                        else:
                            print("   ❌ Не удалось получить обновленную заявку")
                    else:
                        print("   ❌ Не удалось обновить данные получателя")
                else:
                    print("   ❌ Курьер не смог принять заявку")
            else:
                print("   ❌ Не удалось создать новую заявку на забор груза")
        else:
            print("   ❌ Не удалось авторизовать курьера")
        
        # ФИНАЛЬНАЯ ДИАГНОСТИКА И ВЫВОДЫ
        print("\n" + "="*80)
        print("🔬 ФИНАЛЬНАЯ ДИАГНОСТИКА ПРОБЛЕМЫ ПЛЕЙСХОЛДЕРОВ")
        print("="*80)
        
        # Анализируем результаты диагностики
        print("\n📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:")
        
        # 1. Проверка заявки 100040
        if diagnosis_results.get('request_100040', {}).get('success'):
            recipient_data_result = diagnosis_results.get('recipient_data', {})
            if recipient_data_result.get('exists'):
                filled_fields = recipient_data_result.get('filled_fields', 0)
                total_fields = recipient_data_result.get('total_fields', 3)
                
                if filled_fields == 0:
                    print("❌ ЗАЯВКА 100040: Все данные получателя пустые - ЭТО ПРИЧИНА ПЛЕЙСХОЛДЕРОВ!")
                elif filled_fields < total_fields:
                    print(f"⚠️  ЗАЯВКА 100040: Данные получателя заполнены частично ({filled_fields}/{total_fields})")
                else:
                    print(f"✅ ЗАЯВКА 100040: Все данные получателя заполнены ({filled_fields}/{total_fields})")
            else:
                print("❌ ЗАЯВКА 100040: recipient_data отсутствуют полностью - ЭТО ПРИЧИНА ПЛЕЙСХОЛДЕРОВ!")
        else:
            print("❌ ЗАЯВКА 100040: Не удалось получить данные заявки")
        
        # 2. Проверка других заявок
        other_requests_result = diagnosis_results.get('other_requests', {})
        if other_requests_result.get('with_recipient_data', 0) > 0:
            print(f"✅ ДРУГИЕ ЗАЯВКИ: Найдено {other_requests_result['with_recipient_data']} заявок с заполненными данными получателя")
        else:
            print("❌ ДРУГИЕ ЗАЯВКИ: Не найдено заявок с заполненными данными получателя")
        
        # 3. Проверка нового теста
        new_request_result = diagnosis_results.get('new_request_test', {})
        if new_request_result.get('success'):
            if new_request_result.get('recipient_data_saved'):
                print("✅ НОВЫЙ ТЕСТ: Данные получателя сохраняются корректно при обновлении курьером")
            else:
                print("❌ НОВЫЙ ТЕСТ: Данные получателя НЕ сохраняются при обновлении курьером")
        
        # ВЫВОДЫ И РЕКОМЕНДАЦИИ
        print("\n🎯 ВЫВОДЫ И РЕКОМЕНДАЦИИ:")
        
        # Определяем основную причину проблемы
        if diagnosis_results.get('recipient_data', {}).get('filled_fields', 0) == 0:
            print("\n🔍 ОСНОВНАЯ ПРОБЛЕМА: ДАННЫЕ ПОЛУЧАТЕЛЯ НЕ ЗАПОЛНЕНЫ В ЗАЯВКЕ 100040")
            print("   Причины могут быть:")
            print("   1. Курьер не заполнил данные получателя при обработке заявки")
            print("   2. Данные были заполнены, но не сохранились из-за ошибки в backend")
            print("   3. Данные сохранились в другом поле или структуре")
            print("   4. Проблема в процессе передачи данных от курьера к оператору")
            
            print("\n💡 РЕКОМЕНДАЦИИ:")
            print("   1. Проверить процесс заполнения данных получателя курьером")
            print("   2. Убедиться что endpoint обновления заявки курьером работает корректно")
            print("   3. Проверить структуру данных в базе данных для заявки 100040")
            print("   4. Добавить валидацию обязательных полей получателя")
            
        elif diagnosis_results.get('recipient_data', {}).get('exists'):
            print("\n🔍 ОСНОВНАЯ ПРОБЛЕМА: ДАННЫЕ ПОЛУЧАТЕЛЯ ЕСТЬ, НО ЗАПОЛНЕНЫ ЧАСТИЧНО")
            print("   Возможные причины:")
            print("   1. Курьер заполнил не все обязательные поля")
            print("   2. Некоторые поля не передаются корректно при обновлении")
            print("   3. Проблема валидации данных на frontend или backend")
            
            print("\n💡 РЕКОМЕНДАЦИИ:")
            print("   1. Сделать все поля получателя обязательными для заполнения")
            print("   2. Добавить валидацию на frontend перед отправкой данных")
            print("   3. Улучшить UX для заполнения данных получателя курьером")
        else:
            print("\n🔍 ОСНОВНАЯ ПРОБЛЕМА: СТРУКТУРА recipient_data ОТСУТСТВУЕТ")
            print("   Возможные причины:")
            print("   1. Endpoint /api/operator/pickup-requests/{id} не возвращает recipient_data")
            print("   2. Данные получателя хранятся в другой структуре")
            print("   3. Проблема в маппинге данных между курьерской и операторской системами")
            
            print("\n💡 РЕКОМЕНДАЦИИ:")
            print("   1. Проверить структуру ответа endpoint /api/operator/pickup-requests/{id}")
            print("   2. Убедиться что данные получателя передаются в правильном формате")
            print("   3. Добавить поле recipient_data в ответ endpoint если его нет")
        
        # Проверяем успешность диагностики
        diagnosis_success = (
            diagnosis_results.get('operator_auth', {}).get('success', False) and
            diagnosis_results.get('request_100040', {}).get('success', False)
        )
        
        print(f"\n📈 СТАТУС ДИАГНОСТИКИ: {'ЗАВЕРШЕНА УСПЕШНО' if diagnosis_success else 'ЗАВЕРШЕНА С ОШИБКАМИ'}")
        print(f"🧪 Тестов выполнено: {self.tests_run}")
        print(f"✅ Тестов прошло: {self.tests_passed}")
        print(f"📊 Успешность: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        return diagnosis_success

def main():
    """Запуск диагностики проблемы данных плейсхолдера"""
    tester = PickupRequestModalDataTester()
    
    try:
        success = tester.test_pickup_request_modal_data_diagnosis()
        
        if success:
            print("\n🎉 ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО!")
            print("📋 Все критические проверки выполнены")
            print("🔍 Результаты диагностики показывают причину проблемы плейсхолдеров")
        else:
            print("\n❌ ДИАГНОСТИКА ЗАВЕРШЕНА С ОШИБКАМИ")
            print("🔍 Некоторые критические проверки не удались")
            print("⚠️  Требуется дополнительное исследование проблемы")
            
    except KeyboardInterrupt:
        print("\n⏹️  Диагностика прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка диагностики: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()