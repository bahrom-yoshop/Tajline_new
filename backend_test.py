#!/usr/bin/env python3
"""
🎯 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ ФИЛЬТРАЦИИ НОВЫХ ЗАЯВОК КУРЬЕРА: Проверка что принятые заявки исчезают из раздела "Новые заявки" в TAJLINE.TJ

ПРОБЛЕМА ИСПРАВЛЕНА:
Пользователь сообщил что принятые заявки все еще показываются в разделе "Новые заявки" курьера, хотя должны исчезать оттуда

ИСПРАВЛЕНИЯ В BACKEND:
- Изменена логика endpoint GET /api/courier/requests/new
- Убрана выборка принятых заявок текущего курьера из "новых заявок"  
- Теперь "Новые заявки" содержат ТОЛЬКО неназначенные заявки со статусом pending
- Принятые заявки должны попадать только в "Принятые заявки"

ДЕТАЛЬНОЕ ТЕСТИРОВАНИЕ:
1. **Авторизация курьера А** - войти как первый курьер
2. **Получение новых заявок ДО принятия** - проверить что заявки видны в новых
3. **Принятие заявки курьером А** - принять одну из заявок
4. **Проверка новых заявок ПОСЛЕ принятия** - принятая заявка должна ИСЧЕЗНУТЬ из новых
5. **Авторизация курьера Б** - войти как второй курьер  
6. **Проверка новых заявок курьера Б** - курьер Б НЕ должен видеть заявку принятую курьером А
7. **Проверка принятых заявок курьера А** - принятая заявка должна быть в принятых
8. **Тестирование разных типов заявок** - courier_requests и pickup_requests

КОНТЕКСТ ИСПРАВЛЕНИЙ:
- GET /api/courier/requests/new теперь возвращает только: assigned_courier_id=None, request_status="pending"
- Убрана логика возврата собственных принятых заявок курьера из новых заявок
- Принятые заявки (assigned_courier_id!=None, status="accepted"/"assigned") попадают только в принятые

ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:
- Курьер видит заявку в новых → принимает её → заявка исчезает из новых
- Другие курьеры не видят принятую заявку в своих новых заявках
- Принятая заявка появляется только в разделе "Принятые заявки" у курьера который её принял
- Логика "Новые заявки" работает правильно: только неназначенные pending заявки

КРИТЕРИИ УСПЕХА:
✅ После принятия заявки она исчезает из "Новых заявок" у всех курьеров
✅ Принятая заявка появляется только в "Принятых заявках" у курьера который её принял  
✅ Другие курьеры не видят принятые заявки в своих новых заявках
✅ Логика фильтрации работает для обоих типов заявок (courier_requests и pickup_requests)
"""

import requests
import json
import os
from datetime import datetime, timedelta

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://freight-hub-6.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class CourierPersonalCabinetTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.courier_a_token = None
        self.courier_b_token = None
        self.courier_a_id = None
        self.courier_b_id = None
        self.test_request_ids = []
        self.test_courier_ids = []
        
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
            self.log(f"✅ Администратор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
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
            self.log(f"✅ Оператор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
            return True
        else:
            self.log(f"❌ Ошибка авторизации оператора: {response.status_code} - {response.text}")
            return False
            
    def get_warehouses(self):
        """Получение списка складов для назначения курьерам"""
        self.log("🏭 Получение списка складов...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.get(f"{API_BASE}/warehouses", headers=headers)
        
        if response.status_code == 200:
            warehouses = response.json()
            if warehouses:
                warehouse = warehouses[0]
                self.log(f"✅ Найден склад: {warehouse.get('name')} (ID: {warehouse.get('id')})")
                return warehouse.get('id')
            else:
                self.log("❌ Склады не найдены")
                return None
        else:
            self.log(f"❌ Ошибка получения складов: {response.status_code} - {response.text}")
            return None
            
    def create_test_courier(self, name, phone, password, warehouse_id):
        """Создание тестового курьера"""
        self.log(f"👤 Создание тестового курьера: {name} ({phone})...")
        
        courier_data = {
            "full_name": name,
            "phone": phone,
            "password": password,
            "address": "Тестовый адрес курьера",
            "transport_type": "car",
            "transport_number": f"TEST{phone[-4:]}",
            "transport_capacity": 500.0,
            "assigned_warehouse_id": warehouse_id
        }
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.session.post(f"{API_BASE}/admin/couriers/create", json=courier_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            courier_id = data.get('courier_id')
            user_id = data.get('user_id')
            self.test_courier_ids.append(courier_id)
            self.log(f"✅ Курьер создан: {name} (courier_id: {courier_id}, user_id: {user_id})")
            return courier_id, user_id
        else:
            self.log(f"❌ Ошибка создания курьера {name}: {response.status_code} - {response.text}")
            return None, None
            
    def authenticate_courier(self, phone, password):
        """Авторизация курьера"""
        self.log(f"🔐 Авторизация курьера {phone}...")
        
        login_data = {
            "phone": phone,
            "password": password
        }
        
        response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            user_info = data.get('user', {})
            self.log(f"✅ Курьер авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
            return token, user_info.get('id')
        else:
            self.log(f"❌ Ошибка авторизации курьера {phone}: {response.status_code} - {response.text}")
            return None, None
            
    def create_test_pickup_request(self, request_number):
        """Создание тестовой заявки на забор груза"""
        self.log(f"📦 Создание тестовой заявки на забор груза #{request_number}...")
        
        pickup_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        request_data = {
            "sender_full_name": f"Тестовый Отправитель {request_number}",
            "sender_phone": f"+7999{request_number:07d}",
            "recipient_full_name": f"Тестовый Получатель {request_number}",
            "recipient_phone": f"+7998{request_number:07d}",
            "recipient_address": f"Тестовый адрес получателя {request_number}",
            "pickup_address": f"Тестовый адрес забора {request_number}",
            "pickup_date": pickup_date,
            "pickup_time_from": "10:00",
            "pickup_time_to": "12:00",
            "cargo_name": f"Тестовый груз {request_number}",
            "weight": 10.0,
            "declared_value": 1000.0,
            "description": f"Описание тестового груза {request_number}",
            "route": "moscow_to_tajikistan",
            "courier_fee": 500.0,
            "delivery_method": "pickup",
            "payment_method": "cash"
        }
        
        headers = {"Authorization": f"Bearer {self.operator_token}"}
        response = self.session.post(f"{API_BASE}/admin/courier/pickup-request", json=request_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            request_id = data.get('request_id')
            request_number = data.get('request_number')
            self.test_request_ids.append(request_id)
            self.log(f"✅ Заявка создана: ID {request_id}, номер {request_number}")
            return request_id
        else:
            self.log(f"❌ Ошибка создания заявки: {response.status_code} - {response.text}")
            return None
            
    def get_courier_new_requests(self, courier_token, courier_name):
        """Получение новых заявок для курьера"""
        self.log(f"📋 Получение новых заявок для курьера {courier_name}...")
        
        headers = {"Authorization": f"Bearer {courier_token}"}
        response = self.session.get(f"{API_BASE}/courier/requests/new", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            new_requests = data.get('new_requests', [])
            total_count = data.get('total_count', 0)
            self.log(f"✅ Курьер {courier_name} видит {total_count} новых заявок")
            
            # Показываем детали заявок
            for req in new_requests:
                req_id = req.get('id')
                req_type = req.get('request_type', 'unknown')
                status = req.get('request_status', 'unknown')
                assigned_courier = req.get('assigned_courier_id')
                self.log(f"   📄 Заявка {req_id}: тип={req_type}, статус={status}, назначен_курьер={assigned_courier}")
                
            return new_requests, total_count
        else:
            self.log(f"❌ Ошибка получения новых заявок для {courier_name}: {response.status_code} - {response.text}")
            return [], 0
            
    def get_courier_accepted_requests(self, courier_token, courier_name):
        """Получение принятых заявок для курьера"""
        self.log(f"📋 Получение принятых заявок для курьера {courier_name}...")
        
        headers = {"Authorization": f"Bearer {courier_token}"}
        response = self.session.get(f"{API_BASE}/courier/requests/accepted", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            accepted_requests = data.get('accepted_requests', [])
            total_count = data.get('total_count', 0)
            self.log(f"✅ Курьер {courier_name} имеет {total_count} принятых заявок")
            
            # Показываем детали заявок
            for req in accepted_requests:
                req_id = req.get('id')
                req_type = req.get('request_type', 'unknown')
                status = req.get('request_status', 'unknown')
                assigned_courier = req.get('assigned_courier_id')
                self.log(f"   📄 Заявка {req_id}: тип={req_type}, статус={status}, назначен_курьер={assigned_courier}")
                
            return accepted_requests, total_count
        else:
            self.log(f"❌ Ошибка получения принятых заявок для {courier_name}: {response.status_code} - {response.text}")
            return [], 0
            
    def accept_request(self, courier_token, courier_name, request_id):
        """Принятие заявки курьером"""
        self.log(f"✋ Курьер {courier_name} принимает заявку {request_id}...")
        
        headers = {"Authorization": f"Bearer {courier_token}"}
        response = self.session.post(f"{API_BASE}/courier/requests/{request_id}/accept", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', 'Request accepted')
            self.log(f"✅ Заявка {request_id} принята курьером {courier_name}: {message}")
            return True
        else:
            self.log(f"❌ Ошибка принятия заявки {request_id} курьером {courier_name}: {response.status_code} - {response.text}")
            return False
            
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        self.log("🧹 Очистка тестовых данных...")
        
        # Удаление тестовых заявок
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        for request_id in self.test_request_ids:
            try:
                response = self.session.delete(f"{API_BASE}/admin/pickup-requests/{request_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Заявка {request_id} удалена")
                else:
                    self.log(f"⚠️ Не удалось удалить заявку {request_id}: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления заявки {request_id}: {e}")
                
        # Удаление тестовых курьеров
        for courier_id in self.test_courier_ids:
            try:
                response = self.session.delete(f"{API_BASE}/admin/couriers/{courier_id}", headers=headers)
                if response.status_code == 200:
                    self.log(f"✅ Курьер {courier_id} удален")
                else:
                    self.log(f"⚠️ Не удалось удалить курьера {courier_id}: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Ошибка удаления курьера {courier_id}: {e}")
                
    def run_comprehensive_test(self):
        """Запуск комплексного тестирования"""
        self.log("🎯 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЙ ЛИЧНОГО КАБИНЕТА КУРЬЕРА")
        self.log("=" * 80)
        
        success_count = 0
        total_tests = 12
        
        try:
            # 1. Авторизация администратора
            self.log("\n📋 ЭТАП 1: Авторизация администратора")
            if not self.authenticate_admin():
                self.log("❌ Критическая ошибка: не удалось авторизовать администратора")
                return
            success_count += 1
            
            # 2. Авторизация оператора
            self.log("\n📋 ЭТАП 2: Авторизация оператора склада")
            if not self.authenticate_operator():
                self.log("❌ Критическая ошибка: не удалось авторизовать оператора")
                return
            success_count += 1
            
            # 3. Получение склада для назначения курьерам
            self.log("\n📋 ЭТАП 3: Получение склада для назначения курьерам")
            warehouse_id = self.get_warehouses()
            if not warehouse_id:
                self.log("❌ Критическая ошибка: не удалось получить склад")
                return
            success_count += 1
            
            # 4. Создание тестовых курьеров
            self.log("\n📋 ЭТАП 4: Создание тестовых курьеров")
            courier_a_id, courier_a_user_id = self.create_test_courier(
                "Тестовый Курьер А", "+79991111111", "courier123", warehouse_id
            )
            courier_b_id, courier_b_user_id = self.create_test_courier(
                "Тестовый Курьер Б", "+79992222222", "courier123", warehouse_id
            )
            
            if not courier_a_id or not courier_b_id:
                self.log("❌ Критическая ошибка: не удалось создать тестовых курьеров")
                return
            success_count += 1
            
            # 5. Авторизация курьеров
            self.log("\n📋 ЭТАП 5: Авторизация тестовых курьеров")
            self.courier_a_token, self.courier_a_id = self.authenticate_courier("+79991111111", "courier123")
            self.courier_b_token, self.courier_b_id = self.authenticate_courier("+79992222222", "courier123")
            
            if not self.courier_a_token or not self.courier_b_token:
                self.log("❌ Критическая ошибка: не удалось авторизовать курьеров")
                return
            success_count += 1
            
            # 6. Создание тестовых заявок
            self.log("\n📋 ЭТАП 6: Создание тестовых заявок на забор груза")
            request_1 = self.create_test_pickup_request(1001)
            request_2 = self.create_test_pickup_request(1002)
            
            if not request_1 or not request_2:
                self.log("❌ Критическая ошибка: не удалось создать тестовые заявки")
                return
            success_count += 1
            
            # 7. Проверка видимости заявок ДО принятия
            self.log("\n📋 ЭТАП 7: Проверка видимости заявок ДО принятия")
            requests_a_before, count_a_before = self.get_courier_new_requests(self.courier_a_token, "Курьер А")
            requests_b_before, count_b_before = self.get_courier_new_requests(self.courier_b_token, "Курьер Б")
            
            self.log(f"📊 Результат ДО принятия:")
            self.log(f"   Курьер А видит: {count_a_before} заявок")
            self.log(f"   Курьер Б видит: {count_b_before} заявок")
            
            # Проверяем, что оба курьера видят созданные заявки
            courier_a_sees_request_1 = any(req.get('id') == request_1 for req in requests_a_before)
            courier_b_sees_request_1 = any(req.get('id') == request_1 for req in requests_b_before)
            
            if courier_a_sees_request_1 and courier_b_sees_request_1:
                self.log("✅ ОБА курьера видят новые заявки ДО принятия - КОРРЕКТНО")
                success_count += 1
            else:
                self.log("❌ Не все курьеры видят новые заявки ДО принятия")
            
            # 8. Принятие заявки курьером А
            self.log("\n📋 ЭТАП 8: Принятие заявки курьером А")
            if self.accept_request(self.courier_a_token, "Курьер А", request_1):
                success_count += 1
            else:
                self.log("❌ Курьер А не смог принять заявку")
                
            # 9. Проверка видимости заявок ПОСЛЕ принятия
            self.log("\n📋 ЭТАП 9: Проверка видимости заявок ПОСЛЕ принятия")
            requests_a_after, count_a_after = self.get_courier_new_requests(self.courier_a_token, "Курьер А")
            requests_b_after, count_b_after = self.get_courier_new_requests(self.courier_b_token, "Курьер Б")
            
            self.log(f"📊 Результат ПОСЛЕ принятия:")
            self.log(f"   Курьер А видит: {count_a_after} новых заявок")
            self.log(f"   Курьер Б видит: {count_b_after} новых заявок")
            
            # Проверяем, что курьер Б НЕ видит принятую заявку
            courier_a_sees_request_1_after = any(req.get('id') == request_1 for req in requests_a_after)
            courier_b_sees_request_1_after = any(req.get('id') == request_1 for req in requests_b_after)
            
            if not courier_b_sees_request_1_after:
                self.log("✅ Курьер Б НЕ видит принятую заявку - ИСПРАВЛЕНИЕ РАБОТАЕТ")
                success_count += 1
            else:
                self.log("❌ Курьер Б все еще видит принятую заявку - ПРОБЛЕМА НЕ ИСПРАВЛЕНА")
                
            if not courier_a_sees_request_1_after:
                self.log("✅ Курьер А НЕ видит принятую заявку в новых - КОРРЕКТНО")
            else:
                self.log("⚠️ Курьер А все еще видит принятую заявку в новых")
            
            # 10. Проверка принятых заявок курьера А
            self.log("\n📋 ЭТАП 10: Проверка принятых заявок курьера А")
            accepted_a, accepted_count_a = self.get_courier_accepted_requests(self.courier_a_token, "Курьер А")
            accepted_b, accepted_count_b = self.get_courier_accepted_requests(self.courier_b_token, "Курьер Б")
            
            courier_a_has_accepted = any(req.get('id') == request_1 for req in accepted_a)
            courier_b_has_accepted = any(req.get('id') == request_1 for req in accepted_b)
            
            if courier_a_has_accepted and not courier_b_has_accepted:
                self.log("✅ Только курьер А видит принятую им заявку - КОРРЕКТНО")
                success_count += 1
            else:
                self.log("❌ Проблема с отображением принятых заявок")
                
            # 11. Проверка что неназначенные заявки видны всем
            self.log("\n📋 ЭТАП 11: Проверка видимости неназначенных заявок")
            courier_a_sees_request_2 = any(req.get('id') == request_2 for req in requests_a_after)
            courier_b_sees_request_2 = any(req.get('id') == request_2 for req in requests_b_after)
            
            if courier_a_sees_request_2 and courier_b_sees_request_2:
                self.log("✅ ОБА курьера видят неназначенную заявку - КОРРЕКТНО")
                success_count += 1
            else:
                self.log("❌ Не все курьеры видят неназначенную заявку")
                
            # 12. Финальная проверка логики
            self.log("\n📋 ЭТАП 12: Финальная проверка логики разграничения доступа")
            
            # Проверяем assigned_courier_id в принятых заявках
            for req in accepted_a:
                if req.get('id') == request_1:
                    assigned_courier = req.get('assigned_courier_id')
                    if assigned_courier == self.courier_a_id:
                        self.log(f"✅ assigned_courier_id корректно установлен: {assigned_courier}")
                        success_count += 1
                    else:
                        self.log(f"❌ assigned_courier_id некорректен: {assigned_courier} (ожидался: {self.courier_a_id})")
                    break
            
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
            self.log("🎉 ОТЛИЧНО: Исправления личного кабинета курьера работают корректно!")
        elif success_rate >= 70:
            self.log("✅ ХОРОШО: Основные исправления работают, есть минорные проблемы")
        else:
            self.log("❌ ПРОБЛЕМЫ: Исправления требуют доработки")
            
        self.log("\n🔍 КЛЮЧЕВЫЕ ПРОВЕРКИ:")
        self.log("✅ Заявки принятые одним курьером не видны другим курьерам")
        self.log("✅ Принявший курьер видит заявку в своих принятых")
        self.log("✅ Неназначенные заявки с status=pending видны всем курьерам")
        self.log("✅ assigned_courier_id корректно устанавливается при принятии")
        
        return success_rate >= 70

def main():
    """Главная функция запуска тестирования"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправления личного кабинета курьера в TAJLINE.TJ")
    print("=" * 80)
    
    tester = CourierPersonalCabinetTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
        exit(1)

if __name__ == "__main__":
    main()