#!/usr/bin/env python3
"""
РАСШИРЕННАЯ ДИАГНОСТИКА: Поиск заявки 100008/02 во всех коллекциях системы TAJLINE.TJ

Поскольку заявка 100008/02 не найдена в основных коллекциях, проведем расширенный поиск
во всех возможных местах системы, включая грузы, курьерские заявки и другие коллекции.
"""

import requests
import json
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-system-debug.preview.emergentagent.com/api"

# Учетные данные администратора
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

class ExtendedRequestSearchTest:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.target_request_number = "100008/02"
        self.search_results = {}
        
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
                
                print(f"✅ Успешная авторизация: {user_info.get('full_name', 'N/A')} ({user_info.get('role', 'N/A')})")
                
                # Устанавливаем токен для всех последующих запросов
                self.session.headers.update({
                    "Authorization": f"Bearer {self.admin_token}"
                })
                
                return True
            else:
                print(f"❌ Ошибка авторизации: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при авторизации: {e}")
            return False
    
    def search_in_cargo_collections(self):
        """Поиск в коллекциях грузов"""
        print(f"\n🔍 Поиск заявки {self.target_request_number} в коллекциях грузов...")
        
        # Поиск в operator/cargo/available-for-placement
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                cargo_items = data.get('items', [])
                
                print(f"📦 Проверка {len(cargo_items)} грузов в размещении...")
                
                found_cargo = []
                for cargo in cargo_items:
                    cargo_number = cargo.get('cargo_number', '')
                    if self.target_request_number in cargo_number or cargo_number in self.target_request_number:
                        found_cargo.append(cargo)
                
                if found_cargo:
                    print(f"🎯 Найдено {len(found_cargo)} похожих грузов:")
                    for cargo in found_cargo:
                        print(f"   - Номер: {cargo.get('cargo_number', 'N/A')}")
                        print(f"     ID: {cargo.get('id', 'N/A')}")
                        print(f"     Статус: {cargo.get('processing_status', 'N/A')}")
                        print(f"     Отправитель: {cargo.get('sender_full_name', 'N/A')}")
                    
                    self.search_results['cargo_placement'] = found_cargo
                else:
                    print("❌ Похожих грузов в размещении не найдено")
            
        except Exception as e:
            print(f"❌ Ошибка поиска в грузах размещения: {e}")
        
        # Поиск в admin/cargo (все грузы)
        try:
            response = self.session.get(
                f"{BACKEND_URL}/admin/cargo",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                all_cargo = data.get('items', []) if isinstance(data, dict) else data
                
                print(f"📦 Проверка {len(all_cargo)} всех грузов в системе...")
                
                found_cargo = []
                for cargo in all_cargo:
                    cargo_number = cargo.get('cargo_number', '')
                    if self.target_request_number in cargo_number or cargo_number in self.target_request_number:
                        found_cargo.append(cargo)
                
                if found_cargo:
                    print(f"🎯 Найдено {len(found_cargo)} похожих грузов в системе:")
                    for cargo in found_cargo:
                        print(f"   - Номер: {cargo.get('cargo_number', 'N/A')}")
                        print(f"     ID: {cargo.get('id', 'N/A')}")
                        print(f"     Статус: {cargo.get('status', 'N/A')}")
                        print(f"     Отправитель: {cargo.get('sender_full_name', 'N/A')}")
                    
                    self.search_results['all_cargo'] = found_cargo
                else:
                    print("❌ Похожих грузов в системе не найдено")
            
        except Exception as e:
            print(f"❌ Ошибка поиска во всех грузах: {e}")
    
    def search_in_courier_collections(self):
        """Поиск в курьерских коллекциях"""
        print(f"\n🚚 Поиск заявки {self.target_request_number} в курьерских коллекциях...")
        
        # Поиск в courier-requests
        try:
            response = self.session.get(
                f"{BACKEND_URL}/admin/courier-requests",
                timeout=10
            )
            
            if response.status_code == 200:
                courier_requests = response.json()
                
                print(f"🚚 Проверка {len(courier_requests)} курьерских заявок...")
                
                found_requests = []
                for request in courier_requests:
                    request_number = request.get('request_number', '')
                    cargo_name = request.get('cargo_name', '')
                    
                    if (self.target_request_number in request_number or 
                        request_number in self.target_request_number or
                        self.target_request_number in cargo_name):
                        found_requests.append(request)
                
                if found_requests:
                    print(f"🎯 Найдено {len(found_requests)} похожих курьерских заявок:")
                    for request in found_requests:
                        print(f"   - Номер: {request.get('request_number', 'N/A')}")
                        print(f"     ID: {request.get('id', 'N/A')}")
                        print(f"     Статус: {request.get('request_status', 'N/A')}")
                        print(f"     Груз: {request.get('cargo_name', 'N/A')}")
                    
                    self.search_results['courier_requests'] = found_requests
                else:
                    print("❌ Похожих курьерских заявок не найдено")
            
        except Exception as e:
            print(f"❌ Ошибка поиска в курьерских заявках: {e}")
    
    def search_in_warehouse_notifications(self):
        """Поиск в уведомлениях склада"""
        print(f"\n📬 Поиск заявки {self.target_request_number} в уведомлениях склада...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/warehouse-notifications",
                timeout=10
            )
            
            if response.status_code == 200:
                notifications = response.json()
                
                print(f"📬 Проверка {len(notifications)} уведомлений склада...")
                
                found_notifications = []
                for notification in notifications:
                    request_number = notification.get('request_number', '')
                    
                    if (self.target_request_number in request_number or 
                        request_number in self.target_request_number):
                        found_notifications.append(notification)
                
                if found_notifications:
                    print(f"🎯 Найдено {len(found_notifications)} похожих уведомлений:")
                    for notification in found_notifications:
                        print(f"   - Номер: {notification.get('request_number', 'N/A')}")
                        print(f"     ID: {notification.get('id', 'N/A')}")
                        print(f"     Статус: {notification.get('status', 'N/A')}")
                        print(f"     Тип: {notification.get('request_type', 'N/A')}")
                    
                    self.search_results['warehouse_notifications'] = found_notifications
                else:
                    print("❌ Похожих уведомлений не найдено")
            
        except Exception as e:
            print(f"❌ Ошибка поиска в уведомлениях: {e}")
    
    def search_by_pattern_variations(self):
        """Поиск по различным вариациям номера"""
        print(f"\n🔄 Поиск по вариациям номера {self.target_request_number}...")
        
        # Различные варианты номера
        variations = [
            "100008/02",
            "100008-02", 
            "100008_02",
            "10000802",
            "100008.02",
            "100008 02",
            "000008/02",
            "008/02",
            "100008",
            "02"
        ]
        
        print(f"🔍 Проверяем {len(variations)} вариаций номера...")
        
        # Поиск в заявках на грузы
        try:
            response = self.session.get(
                f"{BACKEND_URL}/admin/cargo-requests",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                requests_list = data if isinstance(data, list) else data.get('items', [])
                
                found_by_variation = []
                for request in requests_list:
                    request_number = request.get('request_number', '')
                    cargo_name = request.get('cargo_name', '')
                    
                    for variation in variations:
                        if (variation in request_number or 
                            variation in cargo_name or
                            request_number.endswith(variation) or
                            cargo_name.endswith(variation)):
                            found_by_variation.append({
                                'request': request,
                                'matched_variation': variation
                            })
                            break
                
                if found_by_variation:
                    print(f"🎯 Найдено {len(found_by_variation)} заявок по вариациям:")
                    for item in found_by_variation:
                        request = item['request']
                        variation = item['matched_variation']
                        print(f"   - Номер: {request.get('request_number', 'N/A')} (совпадение: {variation})")
                        print(f"     ID: {request.get('id', 'N/A')}")
                        print(f"     Груз: {request.get('cargo_name', 'N/A')}")
                    
                    self.search_results['pattern_variations'] = found_by_variation
                else:
                    print("❌ Заявок по вариациям не найдено")
            
        except Exception as e:
            print(f"❌ Ошибка поиска по вариациям: {e}")
    
    def check_deleted_or_archived_data(self):
        """Проверка удаленных или архивных данных"""
        print(f"\n🗂️ Проверка возможных архивных или удаленных данных...")
        
        # Проверяем различные endpoints, которые могут содержать архивные данные
        endpoints_to_check = [
            "/admin/deleted-requests",
            "/admin/archived-requests", 
            "/operator/completed-requests",
            "/admin/history",
            "/operator/pickup-history"
        ]
        
        for endpoint in endpoints_to_check:
            try:
                response = self.session.get(
                    f"{BACKEND_URL}{endpoint}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"✅ Endpoint {endpoint} доступен")
                    data = response.json()
                    
                    # Попытка найти данные
                    items = []
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        items = data.get('items', []) or data.get('requests', []) or data.get('history', [])
                    
                    if items:
                        print(f"   📊 Найдено {len(items)} записей")
                        
                        # Поиск по номеру
                        found = []
                        for item in items:
                            item_number = item.get('request_number', '') or item.get('cargo_number', '')
                            if self.target_request_number in item_number:
                                found.append(item)
                        
                        if found:
                            print(f"   🎯 Найдено {len(found)} совпадений!")
                            for item in found:
                                print(f"      - Номер: {item.get('request_number', 'N/A')}")
                                print(f"        ID: {item.get('id', 'N/A')}")
                    else:
                        print(f"   📭 Записей не найдено")
                        
                elif response.status_code == 404:
                    print(f"❌ Endpoint {endpoint} не найден")
                else:
                    print(f"⚠️ Endpoint {endpoint} вернул статус {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Ошибка проверки {endpoint}: {e}")
    
    def analyze_similar_requests(self):
        """Анализ похожих заявок для понимания формата"""
        print(f"\n📊 Анализ похожих заявок для понимания формата номеров...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/admin/cargo-requests",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                requests_list = data if isinstance(data, list) else data.get('items', [])
                
                print(f"📋 Анализ {len(requests_list)} заявок в системе:")
                
                # Анализируем форматы номеров
                number_formats = {}
                for request in requests_list:
                    request_number = request.get('request_number', '')
                    
                    # Определяем формат
                    if request_number.startswith('REQ'):
                        format_type = 'REQ_FORMAT'
                    elif '/' in request_number:
                        format_type = 'SLASH_FORMAT'
                    elif '-' in request_number:
                        format_type = 'DASH_FORMAT'
                    elif request_number.isdigit():
                        format_type = 'NUMERIC_FORMAT'
                    else:
                        format_type = 'OTHER_FORMAT'
                    
                    if format_type not in number_formats:
                        number_formats[format_type] = []
                    number_formats[format_type].append(request_number)
                
                print(f"\n📊 Форматы номеров в системе:")
                for format_type, numbers in number_formats.items():
                    print(f"   {format_type}: {len(numbers)} заявок")
                    for number in numbers[:3]:  # Показываем первые 3 примера
                        print(f"      - {number}")
                    if len(numbers) > 3:
                        print(f"      ... и еще {len(numbers) - 3}")
                
                # Ищем заявки с похожими номерами (содержащие цифры из 100008/02)
                target_digits = ['100008', '02', '008', '100']
                similar_requests = []
                
                for request in requests_list:
                    request_number = request.get('request_number', '')
                    cargo_name = request.get('cargo_name', '')
                    
                    for digit in target_digits:
                        if digit in request_number or digit in cargo_name:
                            similar_requests.append({
                                'request': request,
                                'match': digit
                            })
                            break
                
                if similar_requests:
                    print(f"\n🎯 Найдено {len(similar_requests)} заявок с похожими номерами:")
                    for item in similar_requests:
                        request = item['request']
                        match = item['match']
                        print(f"   - {request.get('request_number', 'N/A')} (совпадение: {match})")
                        print(f"     Груз: {request.get('cargo_name', 'N/A')}")
                        print(f"     Статус: {request.get('status', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Ошибка анализа похожих заявок: {e}")
    
    def run_extended_search(self):
        """Запуск расширенного поиска заявки 100008/02"""
        print("=" * 80)
        print("🔍 РАСШИРЕННАЯ ДИАГНОСТИКА: Поиск заявки 100008/02 во всех коллекциях")
        print("=" * 80)
        
        # Шаг 1: Авторизация
        if not self.authenticate_admin():
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться")
            return False
        
        # Шаг 2: Поиск в коллекциях грузов
        self.search_in_cargo_collections()
        
        # Шаг 3: Поиск в курьерских коллекциях
        self.search_in_courier_collections()
        
        # Шаг 4: Поиск в уведомлениях склада
        self.search_in_warehouse_notifications()
        
        # Шаг 5: Поиск по вариациям номера
        self.search_by_pattern_variations()
        
        # Шаг 6: Проверка архивных данных
        self.check_deleted_or_archived_data()
        
        # Шаг 7: Анализ похожих заявок
        self.analyze_similar_requests()
        
        # Финальный отчет
        print(f"\n" + "=" * 80)
        print(f"🎯 ФИНАЛЬНЫЙ ОТЧЕТ РАСШИРЕННОГО ПОИСКА")
        print(f"=" * 80)
        
        total_found = sum(len(results) for results in self.search_results.values())
        
        if total_found > 0:
            print(f"✅ Найдено {total_found} потенциальных совпадений:")
            for collection, results in self.search_results.items():
                if results:
                    print(f"   📂 {collection}: {len(results)} результатов")
        else:
            print(f"❌ Заявка {self.target_request_number} НЕ НАЙДЕНА ни в одной коллекции!")
            print(f"\n🔍 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
            print(f"   1. Заявка была полностью удалена из системы")
            print(f"   2. Номер заявки имеет другой формат")
            print(f"   3. Заявка находится в недоступной коллекции")
            print(f"   4. Заявка была создана в другой системе")
            print(f"   5. Произошла ошибка в номере заявки")
        
        return True

def main():
    """Главная функция для запуска расширенного поиска"""
    test = ExtendedRequestSearchTest()
    
    try:
        success = test.run_extended_search()
        
        if success:
            print("\n🎉 Расширенный поиск завершен!")
        else:
            print("\n❌ Расширенный поиск завершен с ошибками!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Поиск прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка поиска: {e}")

if __name__ == "__main__":
    main()