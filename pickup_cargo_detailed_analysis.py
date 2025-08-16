#!/usr/bin/env python3
"""
УГЛУБЛЕННЫЙ АНАЛИЗ: Поиск связей между заявками на грузы и секцией "На Забор"

Поскольку в /api/operator/pickup-requests нет активных заявок, 
проверим связи через другие коллекции:
1. /admin/cargo-requests - заявки на грузы
2. /operator/warehouse-notifications - уведомления склада
3. Поиск грузов со статусами связанными с забором
"""

import requests
import json
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-tracker-29.preview.emergentagent.com/api"

class PickupCargoDetailedAnalysis:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        
    def log(self, message):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def authenticate_warehouse_operator(self):
        """Авторизация оператора склада"""
        self.log("🔐 Авторизация оператора склада (+79777888999/warehouse123)")
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/login", json={
                "phone": "+79777888999",
                "password": "warehouse123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                
                self.log(f"✅ Успешная авторизация: {data.get('user', {}).get('full_name')}")
                return True
            else:
                self.log(f"❌ Ошибка авторизации: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Исключение при авторизации: {e}")
            return False
    
    def analyze_cargo_requests(self):
        """Анализ заявок на грузы"""
        self.log("📋 АНАЛИЗ ЗАЯВОК НА ГРУЗЫ (/admin/cargo-requests)")
        
        try:
            response = self.session.get(f"{BACKEND_URL}/admin/cargo-requests")
            
            if response.status_code == 200:
                cargo_requests = response.json()
                self.log(f"✅ Найдено заявок на грузы: {len(cargo_requests)}")
                
                if cargo_requests:
                    # Анализируем структуру
                    first_request = cargo_requests[0]
                    self.log(f"   📄 Поля в заявке на груз: {list(first_request.keys())}")
                    
                    # Ищем поля связанные с забором
                    pickup_fields = []
                    for key in first_request.keys():
                        if 'pickup' in key.lower():
                            pickup_fields.append(key)
                    
                    if pickup_fields:
                        self.log(f"   🎯 Поля связанные с забором: {pickup_fields}")
                        
                        # Показываем примеры значений
                        for field in pickup_fields:
                            value = first_request.get(field)
                            self.log(f"     - {field}: {value}")
                    
                    # Анализируем статусы
                    statuses = {}
                    for request in cargo_requests:
                        status = request.get('status', 'unknown')
                        statuses[status] = statuses.get(status, 0) + 1
                    
                    self.log(f"   📊 Статусы заявок: {statuses}")
                    
                    # Ищем заявки со статусом связанным с забором
                    pickup_related_requests = []
                    for request in cargo_requests:
                        status = request.get('status', '').lower()
                        if 'pickup' in status or 'забор' in status or status == 'pending':
                            pickup_related_requests.append(request)
                    
                    if pickup_related_requests:
                        self.log(f"   🎯 Заявки связанные с забором: {len(pickup_related_requests)}")
                        
                        # Показываем детали первых заявок
                        for i, request in enumerate(pickup_related_requests[:3]):
                            self.log(f"     📄 Заявка #{i+1}:")
                            self.log(f"       - ID: {request.get('id')}")
                            self.log(f"       - Номер: {request.get('request_number')}")
                            self.log(f"       - Статус: {request.get('status')}")
                            self.log(f"       - Груз: {request.get('cargo_name')}")
                            self.log(f"       - Отправитель: {request.get('sender_full_name')}")
                    
                    return cargo_requests
                else:
                    self.log("   ⚠️ Заявки на грузы отсутствуют")
                    return []
            else:
                self.log(f"❌ Ошибка получения заявок: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"❌ Исключение при анализе заявок: {e}")
            return None
    
    def analyze_warehouse_notifications(self):
        """Анализ уведомлений склада"""
        self.log("🔔 АНАЛИЗ УВЕДОМЛЕНИЙ СКЛАДА (/operator/warehouse-notifications)")
        
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/warehouse-notifications")
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Получены уведомления склада")
                self.log(f"   📊 Структура ответа: {list(data.keys())}")
                
                notifications = data.get('notifications', [])
                if notifications:
                    self.log(f"   📋 Количество уведомлений: {len(notifications)}")
                    
                    # Анализируем структуру уведомлений
                    if notifications:
                        first_notification = notifications[0]
                        self.log(f"   📄 Поля в уведомлении: {list(first_notification.keys())}")
                        
                        # Ищем поля связанные с заявками на забор
                        pickup_fields = []
                        for key in first_notification.keys():
                            if 'pickup' in key.lower() or 'request' in key.lower():
                                pickup_fields.append(key)
                        
                        if pickup_fields:
                            self.log(f"   🎯 Поля связанные с заявками: {pickup_fields}")
                            
                            # Показываем значения
                            for field in pickup_fields:
                                value = first_notification.get(field)
                                self.log(f"     - {field}: {value}")
                        
                        # Анализируем типы уведомлений
                        notification_types = {}
                        for notif in notifications:
                            notif_type = notif.get('type', 'unknown')
                            notification_types[notif_type] = notification_types.get(notif_type, 0) + 1
                        
                        self.log(f"   📊 Типы уведомлений: {notification_types}")
                        
                        # Ищем уведомления связанные с забором
                        pickup_notifications = []
                        for notif in notifications:
                            message = notif.get('message', '').lower()
                            notif_type = notif.get('type', '').lower()
                            
                            if ('pickup' in message or 'забор' in message or 
                                'pickup' in notif_type or 'забор' in notif_type):
                                pickup_notifications.append(notif)
                        
                        if pickup_notifications:
                            self.log(f"   🎯 Уведомления о заборе: {len(pickup_notifications)}")
                            
                            for i, notif in enumerate(pickup_notifications[:3]):
                                self.log(f"     📄 Уведомление #{i+1}:")
                                self.log(f"       - ID: {notif.get('id')}")
                                self.log(f"       - Тип: {notif.get('type')}")
                                self.log(f"       - Сообщение: {notif.get('message', '')[:100]}...")
                                
                                # Ищем связанные ID
                                for key, value in notif.items():
                                    if 'id' in key.lower() and key != 'id':
                                        self.log(f"       - {key}: {value}")
                    
                    return notifications
                else:
                    self.log("   ⚠️ Уведомления отсутствуют")
                    return []
            else:
                self.log(f"❌ Ошибка получения уведомлений: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"❌ Исключение при анализе уведомлений: {e}")
            return None
    
    def search_pickup_related_cargo(self):
        """Поиск грузов связанных с забором"""
        self.log("🔍 ПОИСК ГРУЗОВ СВЯЗАННЫХ С ЗАБОРОМ")
        
        # Проверяем различные endpoints для поиска грузов
        cargo_endpoints = [
            "/operator/cargo/available-for-placement",
            "/admin/cargo",
            "/operator/cargo/placed"
        ]
        
        pickup_related_cargo = []
        
        for endpoint in cargo_endpoints:
            try:
                self.log(f"   🔧 Проверяем {endpoint}")
                response = self.session.get(f"{BACKEND_URL}{endpoint}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Извлекаем список грузов из разных форматов ответа
                    cargo_list = []
                    if isinstance(data, list):
                        cargo_list = data
                    elif isinstance(data, dict):
                        if 'items' in data:
                            cargo_list = data['items']
                        elif 'cargo' in data:
                            cargo_list = data['cargo']
                        else:
                            # Пробуем найти список в значениях
                            for value in data.values():
                                if isinstance(value, list) and value:
                                    cargo_list = value
                                    break
                    
                    if cargo_list:
                        self.log(f"     ✅ Найдено грузов: {len(cargo_list)}")
                        
                        # Ищем грузы со статусами связанными с забором
                        for cargo in cargo_list:
                            if isinstance(cargo, dict):
                                status = cargo.get('status', '').lower()
                                processing_status = cargo.get('processing_status', '').lower()
                                
                                if ('pickup' in status or 'забор' in status or
                                    'pickup' in processing_status or 'забор' in processing_status):
                                    pickup_related_cargo.append(cargo)
                    else:
                        self.log(f"     ⚠️ Грузы не найдены")
                else:
                    self.log(f"     ❌ Ошибка: {response.status_code}")
                    
            except Exception as e:
                self.log(f"     ❌ Исключение: {e}")
        
        if pickup_related_cargo:
            self.log(f"   🎯 НАЙДЕНО ГРУЗОВ СВЯЗАННЫХ С ЗАБОРОМ: {len(pickup_related_cargo)}")
            
            for i, cargo in enumerate(pickup_related_cargo[:3]):
                self.log(f"     📦 Груз #{i+1}:")
                self.log(f"       - ID: {cargo.get('id')}")
                self.log(f"       - Номер: {cargo.get('cargo_number')}")
                self.log(f"       - Статус: {cargo.get('status')}")
                self.log(f"       - Статус обработки: {cargo.get('processing_status')}")
        else:
            self.log(f"   ⚠️ НЕ НАЙДЕНО грузов связанных с забором")
        
        return pickup_related_cargo
    
    def test_deletion_endpoints_with_real_data(self, cargo_requests, notifications):
        """Тестирование endpoints удаления с реальными данными"""
        self.log("🗑️ ТЕСТИРОВАНИЕ ENDPOINTS УДАЛЕНИЯ С РЕАЛЬНЫМИ ДАННЫМИ")
        
        # Собираем ID для тестирования
        test_ids = {
            'cargo_request_ids': [],
            'notification_ids': [],
            'pickup_request_ids': []
        }
        
        # Из заявок на грузы
        if cargo_requests:
            for request in cargo_requests[:3]:  # Берем первые 3
                if request.get('id'):
                    test_ids['cargo_request_ids'].append(request['id'])
        
        # Из уведомлений
        if notifications:
            for notif in notifications[:3]:  # Берем первые 3
                if notif.get('id'):
                    test_ids['notification_ids'].append(notif['id'])
                
                # Ищем pickup_request_id в уведомлениях
                for key, value in notif.items():
                    if 'pickup_request_id' in key.lower() and value:
                        test_ids['pickup_request_ids'].append(value)
        
        self.log(f"   🎯 ДОСТУПНЫЕ ID ДЛЯ ТЕСТИРОВАНИЯ:")
        for key, ids in test_ids.items():
            self.log(f"     - {key}: {len(ids)} шт. {ids[:2] if ids else '[]'}")
        
        # Тестируем различные endpoints
        deletion_endpoints = [
            # Для заявок на грузы
            ("DELETE", "/admin/cargo-requests/{id}", "cargo_request_ids"),
            ("DELETE", "/operator/cargo-requests/{id}", "cargo_request_ids"),
            
            # Для заявок на забор (если найдем ID)
            ("DELETE", "/admin/pickup-requests/{id}", "pickup_request_ids"),
            ("DELETE", "/operator/pickup-requests/{id}", "pickup_request_ids"),
            
            # Для уведомлений
            ("DELETE", "/operator/warehouse-notifications/{id}", "notification_ids"),
            ("DELETE", "/admin/notifications/{id}", "notification_ids"),
        ]
        
        working_endpoints = []
        
        for method, endpoint_template, id_type in deletion_endpoints:
            if not test_ids[id_type]:
                self.log(f"   ⏭️ ПРОПУЩЕН {endpoint_template} - нет {id_type}")
                continue
            
            test_id = test_ids[id_type][0]
            endpoint = endpoint_template.format(id=test_id)
            
            try:
                self.log(f"   🔧 ТЕСТИРУЕМ: {method} {endpoint}")
                
                if method == "DELETE":
                    # НЕ ВЫПОЛНЯЕМ реальное удаление, только проверяем доступность
                    # Вместо этого делаем HEAD запрос или проверяем OPTIONS
                    response = self.session.options(f"{BACKEND_URL}{endpoint}")
                    
                    if response.status_code in [200, 204, 405]:  # 405 = Method Not Allowed, но endpoint существует
                        self.log(f"     ✅ ENDPOINT СУЩЕСТВУЕТ (статус: {response.status_code})")
                        working_endpoints.append((method, endpoint, response.status_code))
                    elif response.status_code == 404:
                        self.log(f"     ❌ ENDPOINT НЕ НАЙДЕН")
                    elif response.status_code == 403:
                        self.log(f"     ⚠️ НЕТ ПРАВ ДОСТУПА")
                    else:
                        self.log(f"     ⚠️ НЕОЖИДАННЫЙ СТАТУС: {response.status_code}")
                        
            except Exception as e:
                self.log(f"     ❌ ИСКЛЮЧЕНИЕ: {e}")
        
        return working_endpoints
    
    def run_detailed_analysis(self):
        """Запуск углубленного анализа"""
        self.log("🚀 НАЧАЛО УГЛУБЛЕННОГО АНАЛИЗА СВЯЗЕЙ ЗАЯВОК И СЕКЦИИ 'НА ЗАБОР'")
        self.log("=" * 80)
        
        # Авторизация
        if not self.authenticate_warehouse_operator():
            return
        
        # Анализ заявок на грузы
        cargo_requests = self.analyze_cargo_requests()
        
        # Анализ уведомлений склада
        notifications = self.analyze_warehouse_notifications()
        
        # Поиск грузов связанных с забором
        pickup_cargo = self.search_pickup_related_cargo()
        
        # Тестирование endpoints удаления
        working_endpoints = self.test_deletion_endpoints_with_real_data(cargo_requests, notifications)
        
        # Финальный отчет
        self.log("=" * 80)
        self.log("📊 ФИНАЛЬНЫЙ ОТЧЕТ УГЛУБЛЕННОГО АНАЛИЗА:")
        
        self.log(f"   📋 НАЙДЕННЫЕ ДАННЫЕ:")
        self.log(f"     - Заявки на грузы: {len(cargo_requests) if cargo_requests else 0}")
        self.log(f"     - Уведомления склада: {len(notifications) if notifications else 0}")
        self.log(f"     - Грузы связанные с забором: {len(pickup_cargo) if pickup_cargo else 0}")
        
        self.log(f"   🔧 ENDPOINTS:")
        self.log(f"     - Потенциально рабочих: {len(working_endpoints) if working_endpoints else 0}")
        
        if working_endpoints:
            self.log(f"   ✅ ВОЗМОЖНЫЕ СПОСОБЫ УДАЛЕНИЯ:")
            for method, endpoint, status in working_endpoints:
                self.log(f"     - {method} {endpoint} (статус: {status})")
        
        # Рекомендации
        self.log(f"   💡 РЕКОМЕНДАЦИИ:")
        
        if cargo_requests:
            self.log(f"     1. ✅ СТРАТЕГИЯ ЧЕРЕЗ ЗАЯВКИ НА ГРУЗЫ:")
            self.log(f"        - Удалять заявки на грузы через /admin/cargo-requests/{id}")
            self.log(f"        - Это может автоматически убрать груз из секции 'На Забор'")
        
        if notifications:
            self.log(f"     2. ✅ СТРАТЕГИЯ ЧЕРЕЗ УВЕДОМЛЕНИЯ:")
            self.log(f"        - Удалять уведомления склада через /operator/warehouse-notifications/{id}")
            self.log(f"        - Проверить связи pickup_request_id в уведомлениях")
        
        if not working_endpoints:
            self.log(f"     3. ❌ ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНОЕ ИССЛЕДОВАНИЕ:")
            self.log(f"        - Проверить backend код для понимания связей")
            self.log(f"        - Возможно нужны специальные endpoints для секции 'На Забор'")
        
        self.log("🏁 УГЛУБЛЕННЫЙ АНАЛИЗ ЗАВЕРШЕН")

if __name__ == "__main__":
    analysis = PickupCargoDetailedAnalysis()
    analysis.run_detailed_analysis()