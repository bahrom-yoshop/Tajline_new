#!/usr/bin/env python3
"""
ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ: Реальное удаление грузов из секции "На Забор"

На основе анализа найдены:
1. Заявки на грузы (/admin/cargo-requests) - 9 заявок pending
2. Уведомления склада с pickup_request_id
3. Потенциальные endpoints для удаления

Протестируем реальное удаление и найдем рабочий способ.
"""

import requests
import json
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

class PickupCargoDeletionTest:
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
    
    def get_current_pickup_data(self):
        """Получение текущих данных для тестирования"""
        self.log("📋 ПОЛУЧЕНИЕ ТЕКУЩИХ ДАННЫХ ДЛЯ ТЕСТИРОВАНИЯ")
        
        data = {
            'cargo_requests': [],
            'notifications': [],
            'pickup_request_ids': []
        }
        
        # Получаем заявки на грузы
        try:
            response = self.session.get(f"{BACKEND_URL}/admin/cargo-requests")
            if response.status_code == 200:
                data['cargo_requests'] = response.json()
                self.log(f"   ✅ Заявки на грузы: {len(data['cargo_requests'])}")
            else:
                self.log(f"   ❌ Ошибка получения заявок: {response.status_code}")
        except Exception as e:
            self.log(f"   ❌ Исключение при получении заявок: {e}")
        
        # Получаем уведомления склада
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/warehouse-notifications")
            if response.status_code == 200:
                notif_data = response.json()
                data['notifications'] = notif_data.get('notifications', [])
                self.log(f"   ✅ Уведомления склада: {len(data['notifications'])}")
                
                # Извлекаем pickup_request_id
                for notif in data['notifications']:
                    pickup_id = notif.get('pickup_request_id')
                    if pickup_id and pickup_id not in data['pickup_request_ids']:
                        data['pickup_request_ids'].append(pickup_id)
                
                self.log(f"   ✅ Уникальные pickup_request_id: {len(data['pickup_request_ids'])}")
            else:
                self.log(f"   ❌ Ошибка получения уведомлений: {response.status_code}")
        except Exception as e:
            self.log(f"   ❌ Исключение при получении уведомлений: {e}")
        
        return data
    
    def test_cargo_request_deletion(self, cargo_requests):
        """Тестирование удаления заявок на грузы"""
        self.log("🗑️ ТЕСТИРОВАНИЕ УДАЛЕНИЯ ЗАЯВОК НА ГРУЗЫ")
        
        if not cargo_requests:
            self.log("   ❌ Нет заявок для тестирования")
            return False
        
        # Берем первую заявку для тестирования
        test_request = cargo_requests[0]
        request_id = test_request.get('id')
        request_number = test_request.get('request_number')
        
        self.log(f"   🎯 Тестовая заявка:")
        self.log(f"     - ID: {request_id}")
        self.log(f"     - Номер: {request_number}")
        self.log(f"     - Груз: {test_request.get('cargo_name')}")
        
        # Тестируем DELETE /admin/cargo-requests/{id}
        try:
            self.log(f"   🔧 ТЕСТИРУЕМ: DELETE /admin/cargo-requests/{request_id}")
            response = self.session.delete(f"{BACKEND_URL}/admin/cargo-requests/{request_id}")
            
            self.log(f"     - Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                self.log(f"     - ✅ УСПЕШНОЕ УДАЛЕНИЕ!")
                self.log(f"     - Ответ: {response.text}")
                
                # Проверяем, что заявка действительно удалена
                check_response = self.session.get(f"{BACKEND_URL}/admin/cargo-requests")
                if check_response.status_code == 200:
                    remaining_requests = check_response.json()
                    remaining_ids = [r.get('id') for r in remaining_requests]
                    
                    if request_id not in remaining_ids:
                        self.log(f"     - ✅ ПОДТВЕРЖДЕНО: Заявка удалена из списка")
                        return True
                    else:
                        self.log(f"     - ⚠️ ВНИМАНИЕ: Заявка все еще в списке")
                        return False
                        
            elif response.status_code == 404:
                self.log(f"     - ❌ ЗАЯВКА НЕ НАЙДЕНА")
                return False
            elif response.status_code == 403:
                self.log(f"     - ❌ НЕТ ПРАВ ДОСТУПА")
                return False
            elif response.status_code == 405:
                self.log(f"     - ❌ МЕТОД НЕ ПОДДЕРЖИВАЕТСЯ")
                return False
            else:
                self.log(f"     - ❌ НЕОЖИДАННАЯ ОШИБКА: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"     - ❌ ИСКЛЮЧЕНИЕ: {e}")
            return False
    
    def test_pickup_request_deletion(self, pickup_request_ids):
        """Тестирование удаления заявок на забор"""
        self.log("🗑️ ТЕСТИРОВАНИЕ УДАЛЕНИЯ ЗАЯВОК НА ЗАБОР")
        
        if not pickup_request_ids:
            self.log("   ❌ Нет pickup_request_id для тестирования")
            return False
        
        # Берем первый ID для тестирования
        test_pickup_id = pickup_request_ids[0]
        
        self.log(f"   🎯 Тестовый pickup_request_id: {test_pickup_id}")
        
        # Тестируем DELETE /operator/pickup-requests/{id}
        try:
            self.log(f"   🔧 ТЕСТИРУЕМ: DELETE /operator/pickup-requests/{test_pickup_id}")
            response = self.session.delete(f"{BACKEND_URL}/operator/pickup-requests/{test_pickup_id}")
            
            self.log(f"     - Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                self.log(f"     - ✅ УСПЕШНОЕ УДАЛЕНИЕ!")
                self.log(f"     - Ответ: {response.text}")
                return True
            elif response.status_code == 404:
                self.log(f"     - ❌ ЗАЯВКА НА ЗАБОР НЕ НАЙДЕНА")
                return False
            elif response.status_code == 403:
                self.log(f"     - ❌ НЕТ ПРАВ ДОСТУПА")
                return False
            elif response.status_code == 405:
                self.log(f"     - ❌ МЕТОД НЕ ПОДДЕРЖИВАЕТСЯ")
                return False
            else:
                self.log(f"     - ❌ НЕОЖИДАННАЯ ОШИБКА: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"     - ❌ ИСКЛЮЧЕНИЕ: {e}")
            return False
    
    def test_notification_based_deletion(self, notifications):
        """Тестирование удаления через уведомления"""
        self.log("🔔 ТЕСТИРОВАНИЕ УДАЛЕНИЯ ЧЕРЕЗ УВЕДОМЛЕНИЯ")
        
        if not notifications:
            self.log("   ❌ Нет уведомлений для тестирования")
            return False
        
        # Берем первое уведомление
        test_notification = notifications[0]
        notif_id = test_notification.get('id')
        pickup_request_id = test_notification.get('pickup_request_id')
        
        self.log(f"   🎯 Тестовое уведомление:")
        self.log(f"     - ID: {notif_id}")
        self.log(f"     - pickup_request_id: {pickup_request_id}")
        self.log(f"     - Номер заявки: {test_notification.get('request_number')}")
        
        # Пробуем различные endpoints для удаления уведомлений
        notification_endpoints = [
            f"/operator/warehouse-notifications/{notif_id}",
            f"/admin/notifications/{notif_id}",
            f"/operator/notifications/{notif_id}"
        ]
        
        for endpoint in notification_endpoints:
            try:
                self.log(f"   🔧 ТЕСТИРУЕМ: DELETE {endpoint}")
                response = self.session.delete(f"{BACKEND_URL}{endpoint}")
                
                self.log(f"     - Статус ответа: {response.status_code}")
                
                if response.status_code == 200:
                    self.log(f"     - ✅ УСПЕШНОЕ УДАЛЕНИЕ УВЕДОМЛЕНИЯ!")
                    self.log(f"     - Ответ: {response.text}")
                    return True
                elif response.status_code == 404:
                    self.log(f"     - ❌ ENDPOINT НЕ НАЙДЕН")
                elif response.status_code == 403:
                    self.log(f"     - ❌ НЕТ ПРАВ ДОСТУПА")
                elif response.status_code == 405:
                    self.log(f"     - ❌ МЕТОД НЕ ПОДДЕРЖИВАЕТСЯ")
                else:
                    self.log(f"     - ❌ ОШИБКА: {response.text}")
                    
            except Exception as e:
                self.log(f"     - ❌ ИСКЛЮЧЕНИЕ: {e}")
        
        return False
    
    def test_bulk_deletion_approaches(self, data):
        """Тестирование массового удаления"""
        self.log("📦 ТЕСТИРОВАНИЕ МАССОВОГО УДАЛЕНИЯ")
        
        # Пробуем различные подходы к массовому удалению
        bulk_endpoints = [
            ("/admin/cargo-requests/bulk-delete", "cargo_request_ids"),
            ("/operator/pickup-requests/bulk-delete", "pickup_request_ids"),
            ("/operator/warehouse-notifications/bulk-delete", "notification_ids")
        ]
        
        for endpoint, data_type in bulk_endpoints:
            try:
                self.log(f"   🔧 ТЕСТИРУЕМ: POST {endpoint}")
                
                # Подготавливаем данные для массового удаления
                test_data = {}
                if data_type == "cargo_request_ids" and data['cargo_requests']:
                    test_data = {"ids": [r['id'] for r in data['cargo_requests'][:2]]}
                elif data_type == "pickup_request_ids" and data['pickup_request_ids']:
                    test_data = {"ids": data['pickup_request_ids'][:2]}
                elif data_type == "notification_ids" and data['notifications']:
                    test_data = {"ids": [n['id'] for n in data['notifications'][:2]]}
                
                if not test_data:
                    self.log(f"     - ⏭️ ПРОПУЩЕН: Нет данных для {data_type}")
                    continue
                
                response = self.session.post(f"{BACKEND_URL}{endpoint}", json=test_data)
                
                self.log(f"     - Статус ответа: {response.status_code}")
                
                if response.status_code == 200:
                    self.log(f"     - ✅ МАССОВОЕ УДАЛЕНИЕ РАБОТАЕТ!")
                    self.log(f"     - Ответ: {response.text}")
                    return True
                elif response.status_code == 404:
                    self.log(f"     - ❌ ENDPOINT НЕ НАЙДЕН")
                elif response.status_code == 403:
                    self.log(f"     - ❌ НЕТ ПРАВ ДОСТУПА")
                else:
                    self.log(f"     - ❌ ОШИБКА: {response.text}")
                    
            except Exception as e:
                self.log(f"     - ❌ ИСКЛЮЧЕНИЕ: {e}")
        
        return False
    
    def run_deletion_test(self):
        """Запуск финального тестирования удаления"""
        self.log("🚀 НАЧАЛО ФИНАЛЬНОГО ТЕСТИРОВАНИЯ УДАЛЕНИЯ ГРУЗОВ ИЗ СЕКЦИИ 'НА ЗАБОР'")
        self.log("=" * 80)
        
        # Авторизация
        if not self.authenticate_warehouse_operator():
            return
        
        # Получение текущих данных
        data = self.get_current_pickup_data()
        
        if not any([data['cargo_requests'], data['notifications'], data['pickup_request_ids']]):
            self.log("❌ НЕТ ДАННЫХ ДЛЯ ТЕСТИРОВАНИЯ")
            return
        
        # Результаты тестирования
        results = {
            'cargo_request_deletion': False,
            'pickup_request_deletion': False,
            'notification_deletion': False,
            'bulk_deletion': False
        }
        
        # Тестирование различных подходов
        if data['cargo_requests']:
            results['cargo_request_deletion'] = self.test_cargo_request_deletion(data['cargo_requests'])
        
        if data['pickup_request_ids']:
            results['pickup_request_deletion'] = self.test_pickup_request_deletion(data['pickup_request_ids'])
        
        if data['notifications']:
            results['notification_deletion'] = self.test_notification_based_deletion(data['notifications'])
        
        # Тестирование массового удаления
        results['bulk_deletion'] = self.test_bulk_deletion_approaches(data)
        
        # Финальный отчет
        self.log("=" * 80)
        self.log("📊 ФИНАЛЬНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ УДАЛЕНИЯ:")
        
        working_methods = []
        for method, success in results.items():
            status = "✅ РАБОТАЕТ" if success else "❌ НЕ РАБОТАЕТ"
            self.log(f"   {method}: {status}")
            if success:
                working_methods.append(method)
        
        self.log(f"   📈 ИТОГО РАБОЧИХ МЕТОДОВ: {len(working_methods)}")
        
        if working_methods:
            self.log("   🎯 РЕКОМЕНДУЕМЫЕ РЕШЕНИЯ:")
            
            if 'cargo_request_deletion' in working_methods:
                self.log("     1. ✅ УДАЛЕНИЕ ЗАЯВОК НА ГРУЗЫ:")
                self.log("        - Использовать DELETE /admin/cargo-requests/{id}")
                self.log("        - Это удаляет заявку и связанные данные")
            
            if 'pickup_request_deletion' in working_methods:
                self.log("     2. ✅ УДАЛЕНИЕ ЗАЯВОК НА ЗАБОР:")
                self.log("        - Использовать DELETE /operator/pickup-requests/{id}")
                self.log("        - Прямое удаление заявки на забор")
            
            if 'notification_deletion' in working_methods:
                self.log("     3. ✅ УДАЛЕНИЕ УВЕДОМЛЕНИЙ:")
                self.log("        - Удалять уведомления склада")
                self.log("        - Может убрать элементы из секции 'На Забор'")
            
            if 'bulk_deletion' in working_methods:
                self.log("     4. ✅ МАССОВОЕ УДАЛЕНИЕ:")
                self.log("        - Использовать bulk endpoints")
                self.log("        - Эффективно для множественного удаления")
        else:
            self.log("   ❌ НЕ НАЙДЕНО РАБОЧИХ МЕТОДОВ УДАЛЕНИЯ")
            self.log("   💡 ТРЕБУЕТСЯ:")
            self.log("     - Проверка backend кода")
            self.log("     - Возможно нужны специальные endpoints")
            self.log("     - Или изменение логики frontend")
        
        self.log("🏁 ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    test = PickupCargoDeletionTest()
    test.run_deletion_test()