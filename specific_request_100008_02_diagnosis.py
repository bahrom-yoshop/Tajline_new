#!/usr/bin/env python3
"""
КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема с удалением конкретной заявки на забор 100008/02 в TAJLINE.TJ

Этот тест диагностирует проблему с удалением заявки на груз с номером 100008/02,
которая не удаляется ни при одиночном, ни при массовом удалении из секции "На Забор".
"""

import requests
import json
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://freight-hub-6.preview.emergentagent.com/api"

# Учетные данные администратора
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

class SpecificRequestDiagnosisTest:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.target_request_number = "100008/02"
        self.target_request_data = None
        self.target_request_id = None
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        print("🔐 Авторизация администратора...")
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                user_info = data.get("user", {})
                
                print(f"✅ Успешная авторизация администратора:")
                print(f"   - Имя: {user_info.get('full_name', 'N/A')}")
                print(f"   - Номер: {user_info.get('user_number', 'N/A')}")
                print(f"   - Роль: {user_info.get('role', 'N/A')}")
                
                # Устанавливаем токен для всех последующих запросов
                self.session.headers.update({
                    "Authorization": f"Bearer {self.admin_token}"
                })
                
                return True
            else:
                print(f"❌ Ошибка авторизации: {response.status_code}")
                print(f"   Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при авторизации: {e}")
            return False
    
    def search_request_in_cargo_requests(self):
        """Поиск заявки 100008/02 в GET /api/admin/cargo-requests"""
        print(f"\n🔍 Поиск заявки {self.target_request_number} в /api/admin/cargo-requests...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/admin/cargo-requests",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                requests_list = data if isinstance(data, list) else data.get('items', [])
                
                print(f"📊 Всего заявок в системе: {len(requests_list)}")
                
                # Ищем конкретную заявку 100008/02
                target_request = None
                for request in requests_list:
                    request_number = request.get('request_number', '')
                    if request_number == self.target_request_number:
                        target_request = request
                        break
                
                if target_request:
                    self.target_request_data = target_request
                    self.target_request_id = target_request.get('id')
                    
                    print(f"🎯 НАЙДЕНА заявка {self.target_request_number}!")
                    print(f"   - ID: {self.target_request_id}")
                    print(f"   - Статус: {target_request.get('status', 'N/A')}")
                    print(f"   - Отправитель: {target_request.get('sender_full_name', 'N/A')}")
                    print(f"   - Получатель: {target_request.get('recipient_full_name', 'N/A')}")
                    print(f"   - Груз: {target_request.get('cargo_name', 'N/A')}")
                    print(f"   - Создана: {target_request.get('created_at', 'N/A')}")
                    
                    # Показываем все поля для полного анализа
                    print(f"\n📋 Полная информация о заявке {self.target_request_number}:")
                    for key, value in target_request.items():
                        print(f"   - {key}: {value}")
                    
                    return True
                else:
                    print(f"❌ Заявка {self.target_request_number} НЕ НАЙДЕНА в /api/admin/cargo-requests")
                    
                    # Показываем все номера заявок для анализа
                    print("\n📋 Все номера заявок в системе:")
                    for i, request in enumerate(requests_list[:10], 1):  # Показываем первые 10
                        print(f"   {i}. {request.get('request_number', 'N/A')} (ID: {request.get('id', 'N/A')})")
                    
                    if len(requests_list) > 10:
                        print(f"   ... и еще {len(requests_list) - 10} заявок")
                    
                    return False
            else:
                print(f"❌ Ошибка получения заявок: {response.status_code}")
                print(f"   Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при поиске в cargo-requests: {e}")
            return False
    
    def search_request_in_pickup_requests(self):
        """Поиск заявки 100008/02 в GET /api/operator/pickup-requests"""
        print(f"\n🔍 Поиск заявки {self.target_request_number} в /api/operator/pickup-requests...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/pickup-requests",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                pickup_requests = data.get('pickup_requests', [])
                
                print(f"📊 Всего заявок на забор: {len(pickup_requests)}")
                
                # Ищем конкретную заявку 100008/02
                target_pickup = None
                for request in pickup_requests:
                    request_number = request.get('request_number', '')
                    if request_number == self.target_request_number:
                        target_pickup = request
                        break
                
                if target_pickup:
                    print(f"🎯 НАЙДЕНА заявка на забор {self.target_request_number}!")
                    print(f"   - ID: {target_pickup.get('id', 'N/A')}")
                    print(f"   - Статус: {target_pickup.get('status', 'N/A')}")
                    print(f"   - Тип: {target_pickup.get('request_type', 'N/A')}")
                    
                    # Показываем все поля
                    print(f"\n📋 Полная информация о заявке на забор {self.target_request_number}:")
                    for key, value in target_pickup.items():
                        print(f"   - {key}: {value}")
                    
                    return True
                else:
                    print(f"❌ Заявка на забор {self.target_request_number} НЕ НАЙДЕНА в /api/operator/pickup-requests")
                    
                    # Показываем все номера заявок на забор
                    print("\n📋 Все номера заявок на забор:")
                    for i, request in enumerate(pickup_requests[:10], 1):
                        print(f"   {i}. {request.get('request_number', 'N/A')} (ID: {request.get('id', 'N/A')})")
                    
                    return False
            else:
                print(f"❌ Ошибка получения заявок на забор: {response.status_code}")
                print(f"   Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при поиске в pickup-requests: {e}")
            return False
    
    def analyze_request_relationships(self):
        """Анализ связанных данных заявки 100008/02"""
        if not self.target_request_id:
            print("\n⚠️ Невозможно проанализировать связи - заявка не найдена")
            return False
        
        print(f"\n🔗 Анализ связанных данных для заявки {self.target_request_number}...")
        
        # Проверяем уведомления склада
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/warehouse-notifications",
                timeout=10
            )
            
            if response.status_code == 200:
                notifications = response.json()
                related_notifications = []
                
                for notification in notifications:
                    if (notification.get('pickup_request_id') == self.target_request_id or 
                        notification.get('request_number') == self.target_request_number):
                        related_notifications.append(notification)
                
                if related_notifications:
                    print(f"🔗 Найдено {len(related_notifications)} связанных уведомлений:")
                    for i, notif in enumerate(related_notifications, 1):
                        print(f"   {i}. ID: {notif.get('id', 'N/A')}")
                        print(f"      Статус: {notif.get('status', 'N/A')}")
                        print(f"      Тип: {notif.get('request_type', 'N/A')}")
                else:
                    print("📭 Связанных уведомлений не найдено")
            
        except Exception as e:
            print(f"❌ Ошибка при анализе уведомлений: {e}")
        
        # Проверяем курьерские заявки
        try:
            response = self.session.get(
                f"{BACKEND_URL}/admin/courier-requests",
                timeout=10
            )
            
            if response.status_code == 200:
                courier_requests = response.json()
                related_courier_requests = []
                
                for request in courier_requests:
                    if request.get('request_number') == self.target_request_number:
                        related_courier_requests.append(request)
                
                if related_courier_requests:
                    print(f"🚚 Найдено {len(related_courier_requests)} связанных курьерских заявок:")
                    for i, req in enumerate(related_courier_requests, 1):
                        print(f"   {i}. ID: {req.get('id', 'N/A')}")
                        print(f"      Статус: {req.get('request_status', 'N/A')}")
                        print(f"      Курьер: {req.get('assigned_courier_name', 'N/A')}")
                else:
                    print("🚚 Связанных курьерских заявок не найдено")
            
        except Exception as e:
            print(f"❌ Ошибка при анализе курьерских заявок: {e}")
        
        return True
    
    def attempt_deletion_via_cargo_applications(self):
        """Попытка удаления через DELETE /api/admin/cargo-applications/{id}"""
        if not self.target_request_id:
            print("\n⚠️ Невозможно удалить - ID заявки не найден")
            return False
        
        print(f"\n🗑️ Попытка удаления заявки {self.target_request_number} через /api/admin/cargo-applications/{self.target_request_id}...")
        
        try:
            response = self.session.delete(
                f"{BACKEND_URL}/admin/cargo-applications/{self.target_request_id}",
                timeout=10
            )
            
            print(f"📊 Статус ответа: {response.status_code}")
            print(f"📄 Ответ сервера: {response.text}")
            
            if response.status_code == 200:
                print(f"✅ Заявка {self.target_request_number} успешно удалена!")
                return True
            elif response.status_code == 404:
                print(f"❌ Заявка {self.target_request_number} не найдена для удаления")
                return False
            elif response.status_code == 403:
                print(f"❌ Недостаточно прав для удаления заявки {self.target_request_number}")
                return False
            else:
                print(f"❌ Ошибка удаления заявки {self.target_request_number}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при удалении: {e}")
            return False
    
    def verify_deletion(self):
        """Проверка успешности удаления"""
        print(f"\n✅ Проверка удаления заявки {self.target_request_number}...")
        
        # Повторно ищем заявку в системе
        try:
            response = self.session.get(
                f"{BACKEND_URL}/admin/cargo-requests",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                requests_list = data if isinstance(data, list) else data.get('items', [])
                
                # Ищем удаленную заявку
                found = False
                for request in requests_list:
                    if request.get('request_number') == self.target_request_number:
                        found = True
                        break
                
                if found:
                    print(f"❌ Заявка {self.target_request_number} ВСЕ ЕЩЕ СУЩЕСТВУЕТ в системе!")
                    return False
                else:
                    print(f"✅ Заявка {self.target_request_number} успешно удалена из системы!")
                    return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке удаления: {e}")
            return False
    
    def try_alternative_deletion_methods(self):
        """Попытка альтернативных способов удаления"""
        if not self.target_request_id:
            print("\n⚠️ Невозможно попробовать альтернативные методы - ID заявки не найден")
            return False
        
        print(f"\n🔄 Попытка альтернативных способов удаления заявки {self.target_request_number}...")
        
        # Метод 1: Попробовать через другой endpoint
        alternative_endpoints = [
            f"/admin/cargo-requests/{self.target_request_id}",
            f"/operator/pickup-requests/{self.target_request_id}",
            f"/admin/requests/{self.target_request_id}"
        ]
        
        for endpoint in alternative_endpoints:
            print(f"\n🔄 Попытка удаления через {endpoint}...")
            try:
                response = self.session.delete(
                    f"{BACKEND_URL}{endpoint}",
                    timeout=10
                )
                
                print(f"   Статус: {response.status_code}")
                print(f"   Ответ: {response.text}")
                
                if response.status_code == 200:
                    print(f"✅ Успешное удаление через {endpoint}!")
                    return True
                    
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        return False
    
    def run_comprehensive_diagnosis(self):
        """Запуск полной диагностики проблемы с заявкой 100008/02"""
        print("=" * 80)
        print("🎯 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема с удалением заявки 100008/02")
        print("=" * 80)
        
        # Шаг 1: Авторизация
        if not self.authenticate_admin():
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
            return False
        
        # Шаг 2: Поиск заявки в cargo-requests
        found_in_cargo = self.search_request_in_cargo_requests()
        
        # Шаг 3: Поиск заявки в pickup-requests
        found_in_pickup = self.search_request_in_pickup_requests()
        
        # Если заявка не найдена нигде
        if not found_in_cargo and not found_in_pickup:
            print(f"\n🎯 РЕЗУЛЬТАТ ДИАГНОСТИКИ:")
            print(f"❌ Заявка {self.target_request_number} НЕ НАЙДЕНА в системе!")
            print(f"   Возможные причины:")
            print(f"   1. Заявка уже была удалена")
            print(f"   2. Номер заявки изменился")
            print(f"   3. Заявка находится в другой коллекции")
            return False
        
        # Шаг 4: Анализ связанных данных
        self.analyze_request_relationships()
        
        # Шаг 5: Попытка удаления
        if found_in_cargo:
            deletion_success = self.attempt_deletion_via_cargo_applications()
            
            if deletion_success:
                # Шаг 6: Проверка удаления
                self.verify_deletion()
            else:
                # Шаг 7: Альтернативные методы удаления
                self.try_alternative_deletion_methods()
        
        print(f"\n🎯 ФИНАЛЬНЫЙ РЕЗУЛЬТАТ ДИАГНОСТИКИ:")
        if found_in_cargo:
            print(f"✅ Заявка {self.target_request_number} найдена в системе")
            print(f"   - ID: {self.target_request_id}")
            print(f"   - Статус: {self.target_request_data.get('status', 'N/A') if self.target_request_data else 'N/A'}")
        else:
            print(f"❌ Заявка {self.target_request_number} не найдена в основной системе")
        
        if found_in_pickup:
            print(f"✅ Заявка {self.target_request_number} найдена в заявках на забор")
        
        return True

def main():
    """Главная функция для запуска диагностики"""
    test = SpecificRequestDiagnosisTest()
    
    try:
        success = test.run_comprehensive_diagnosis()
        
        if success:
            print("\n🎉 Диагностика завершена успешно!")
        else:
            print("\n❌ Диагностика завершена с ошибками!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Диагностика прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка диагностики: {e}")

if __name__ == "__main__":
    main()