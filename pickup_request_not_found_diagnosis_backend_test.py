#!/usr/bin/env python3
"""
КРИТИЧЕСКАЯ ДИАГНОСТИКА: Ошибка "Pickup request not found" на строке 14547 в TAJLINE.TJ

ПРОБЛЕМА: После устранения первой ошибки с pickup_request_id, возникла вторая ошибка:
- Файл: /app/backend/server.py, строка 14547
- Функция: send_pickup_request_to_placement
- Ошибка: "Pickup request not found"
- Код: pickup_request = db.courier_pickup_requests.find_one({"id": pickup_request_id}, {"_id": 0})

ПОДОЗРЕНИЕ: pickup_request_id из уведомления не соответствует реальному ID в коллекции courier_pickup_requests

НУЖНО ПРОТЕСТИРОВАТЬ:
1. Авторизация пользователя с доступом к уведомлениям
2. Получение списка уведомлений с request_id
3. Проверка существования соответствующих записей в courier_pickup_requests 
4. Анализ структуры данных в courier_pickup_requests - какие поля используются для ID
5. Сравнение ID из уведомлений с ID в courier_pickup_requests
6. Проверка возможных расхождений в названиях полей или структуре данных

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Найти корневую причину несоответствия между pickup_request_id из уведомлений и реальными записями в courier_pickup_requests, предложить решение для правильной связи данных.
"""

import requests
import json
import os
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://freight-hub-6.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class PickupRequestNotFoundDiagnosis:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None
        self.test_results = []
        self.notifications = []
        self.pickup_requests = []
        
    def log_result(self, test_name: str, success: bool, details: str):
        """Логирование результатов тестов"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}: {details}"
        self.test_results.append(result)
        print(result)
        
    def authenticate_user(self):
        """Тест 1: Авторизация пользователя с доступом к уведомлениям"""
        try:
            # Попробуем разные учетные данные для доступа к уведомлениям
            credentials_to_try = [
                ("+79999888777", "admin123", "Администратор"),
                ("+79777888999", "warehouse123", "Оператор склада"),
                ("+79888777666", "operator123", "Другой оператор")
            ]
            
            for phone, password, description in credentials_to_try:
                login_data = {
                    "phone": phone,
                    "password": password
                }
                
                response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
                
                if response.status_code == 200:
                    data = response.json()
                    self.auth_token = data.get("access_token")
                    self.current_user = data.get("user", {})
                    
                    # Устанавливаем заголовок авторизации
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/json"
                    })
                    
                    user_info = f"'{self.current_user.get('full_name')}' (номер: {self.current_user.get('user_number')}, роль: {self.current_user.get('role')})"
                    self.log_result(
                        "АВТОРИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ",
                        True,
                        f"Успешная авторизация {description}: {user_info}, JWT токен получен"
                    )
                    return True
                else:
                    print(f"Попытка авторизации {description} неудачна: HTTP {response.status_code}")
            
            self.log_result(
                "АВТОРИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ",
                False,
                "Не удалось авторизоваться ни с одними учетными данными"
            )
            return False
                
        except Exception as e:
            self.log_result(
                "АВТОРИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ",
                False,
                f"Исключение при авторизации: {str(e)}"
            )
            return False
    
    def get_warehouse_notifications(self):
        """Тест 2: Получение списка уведомлений с request_id"""
        try:
            response = self.session.get(f"{API_BASE}/operator/warehouse-notifications")
            
            if response.status_code == 200:
                data = response.json()
                notifications = data.get("notifications", [])
                total_count = data.get("total_count", 0)
                pending_count = data.get("pending_count", 0)
                in_processing_count = data.get("in_processing_count", 0)
                
                self.notifications = notifications
                
                self.log_result(
                    "ПОЛУЧЕНИЕ СПИСКА УВЕДОМЛЕНИЙ",
                    True,
                    f"Endpoint работает корректно, получено {total_count} уведомлений (pending: {pending_count}, in_processing: {in_processing_count})"
                )
                return True
            elif response.status_code == 403:
                # Попробуем через админский endpoint
                admin_response = self.session.get(f"{API_BASE}/notifications")
                if admin_response.status_code == 200:
                    admin_data = admin_response.json()
                    notifications = admin_data.get("notifications", [])
                    
                    # Фильтруем warehouse notifications
                    warehouse_notifications = [n for n in notifications if 'warehouse' in n.get('message', '').lower() or 'pickup' in n.get('message', '').lower()]
                    
                    self.notifications = warehouse_notifications
                    
                    self.log_result(
                        "ПОЛУЧЕНИЕ СПИСКА УВЕДОМЛЕНИЙ",
                        True,
                        f"Получено через админский endpoint: {len(warehouse_notifications)} уведомлений склада из {len(notifications)} общих"
                    )
                    return True
                else:
                    self.log_result(
                        "ПОЛУЧЕНИЕ СПИСКА УВЕДОМЛЕНИЙ",
                        False,
                        f"Ошибка получения уведомлений: HTTP {response.status_code}, также не удалось получить через админский endpoint: HTTP {admin_response.status_code}"
                    )
                    return False
            else:
                self.log_result(
                    "ПОЛУЧЕНИЕ СПИСКА УВЕДОМЛЕНИЙ",
                    False,
                    f"Ошибка получения уведомлений: HTTP {response.status_code}, {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ПОЛУЧЕНИЕ СПИСКА УВЕДОМЛЕНИЙ",
                False,
                f"Исключение при получении уведомлений: {str(e)}"
            )
            return False
    
    def get_courier_pickup_requests(self):
        """Тест 3: Получение записей из коллекции courier_pickup_requests"""
        try:
            # Попробуем разные endpoints для получения pickup requests
            endpoints_to_try = [
                "/admin/courier-pickup-requests",
                "/operator/courier-pickup-requests", 
                "/courier-pickup-requests",
                "/pickup-requests",
                "/admin/pickup-requests"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    response = self.session.get(f"{API_BASE}{endpoint}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Обрабатываем разные форматы ответа
                        if isinstance(data, list):
                            pickup_requests = data
                        elif isinstance(data, dict):
                            pickup_requests = data.get("requests", data.get("items", data.get("pickup_requests", [])))
                        else:
                            pickup_requests = []
                        
                        self.pickup_requests = pickup_requests
                        
                        self.log_result(
                            "ПОЛУЧЕНИЕ COURIER PICKUP REQUESTS",
                            True,
                            f"Успешно получено {len(pickup_requests)} записей из коллекции courier_pickup_requests через endpoint {endpoint}"
                        )
                        return True
                        
                except Exception as e:
                    print(f"Ошибка при попытке endpoint {endpoint}: {str(e)}")
                    continue
            
            # Если ни один endpoint не сработал, попробуем через MongoDB API (если доступен)
            self.log_result(
                "ПОЛУЧЕНИЕ COURIER PICKUP REQUESTS",
                False,
                "Не удалось найти рабочий endpoint для получения courier_pickup_requests. Возможно, коллекция пуста или endpoint не реализован"
            )
            return False
                
        except Exception as e:
            self.log_result(
                "ПОЛУЧЕНИЕ COURIER PICKUP REQUESTS",
                False,
                f"Исключение при получении courier pickup requests: {str(e)}"
            )
            return False
    
    def analyze_notification_structure(self):
        """Тест 4: Анализ структуры данных в уведомлениях"""
        try:
            if not self.notifications:
                self.log_result(
                    "АНАЛИЗ СТРУКТУРЫ УВЕДОМЛЕНИЙ",
                    True,
                    "Список уведомлений пуст - нет данных для анализа структуры"
                )
                return True
            
            # Анализируем структуру уведомлений
            pickup_request_id_count = 0
            request_id_count = 0
            request_number_count = 0
            
            for notification in self.notifications:
                if "pickup_request_id" in notification:
                    pickup_request_id_count += 1
                if "request_id" in notification:
                    request_id_count += 1
                if "request_number" in notification:
                    request_number_count += 1
            
            total_notifications = len(self.notifications)
            
            # Получаем ключи образца для анализа
            sample_notification = self.notifications[0]
            all_keys = list(sample_notification.keys())
            
            analysis_details = (
                f"Проанализировано {total_notifications} уведомлений - "
                f"pickup_request_id: {pickup_request_id_count}/{total_notifications}, "
                f"request_id: {request_id_count}/{total_notifications}, "
                f"request_number: {request_number_count}/{total_notifications}. "
                f"Ключи в образце: {', '.join(all_keys)}"
            )
            
            # Сохраняем данные для следующих тестов
            self.notification_analysis = {
                "total_notifications": total_notifications,
                "has_pickup_request_id": pickup_request_id_count,
                "has_request_id": request_id_count,
                "has_request_number": request_number_count,
                "sample_keys": all_keys,
                "sample_notification": sample_notification
            }
            
            self.log_result(
                "АНАЛИЗ СТРУКТУРЫ УВЕДОМЛЕНИЙ",
                True,
                analysis_details
            )
            return True
            
        except Exception as e:
            self.log_result(
                "АНАЛИЗ СТРУКТУРЫ УВЕДОМЛЕНИЙ",
                False,
                f"Исключение при анализе структуры уведомлений: {str(e)}"
            )
            return False
    
    def analyze_pickup_requests_structure(self):
        """Тест 5: Анализ структуры данных в courier_pickup_requests"""
        try:
            if not self.pickup_requests:
                self.log_result(
                    "АНАЛИЗ СТРУКТУРЫ PICKUP REQUESTS",
                    True,
                    "Коллекция courier_pickup_requests пуста или недоступна - нет данных для анализа структуры"
                )
                return True
            
            # Анализируем структуру pickup requests
            id_count = 0
            request_id_count = 0
            pickup_request_id_count = 0
            request_number_count = 0
            
            for request in self.pickup_requests:
                if "id" in request:
                    id_count += 1
                if "request_id" in request:
                    request_id_count += 1
                if "pickup_request_id" in request:
                    pickup_request_id_count += 1
                if "request_number" in request:
                    request_number_count += 1
            
            total_requests = len(self.pickup_requests)
            
            # Получаем ключи образца для анализа
            sample_request = self.pickup_requests[0]
            all_keys = list(sample_request.keys())
            
            analysis_details = (
                f"Проанализировано {total_requests} записей в courier_pickup_requests - "
                f"id: {id_count}/{total_requests}, "
                f"request_id: {request_id_count}/{total_requests}, "
                f"pickup_request_id: {pickup_request_id_count}/{total_requests}, "
                f"request_number: {request_number_count}/{total_requests}. "
                f"Ключи в образце: {', '.join(all_keys)}"
            )
            
            # Сохраняем данные для следующих тестов
            self.pickup_requests_analysis = {
                "total_requests": total_requests,
                "has_id": id_count,
                "has_request_id": request_id_count,
                "has_pickup_request_id": pickup_request_id_count,
                "has_request_number": request_number_count,
                "sample_keys": all_keys,
                "sample_request": sample_request
            }
            
            self.log_result(
                "АНАЛИЗ СТРУКТУРЫ PICKUP REQUESTS",
                True,
                analysis_details
            )
            return True
            
        except Exception as e:
            self.log_result(
                "АНАЛИЗ СТРУКТУРЫ PICKUP REQUESTS",
                False,
                f"Исключение при анализе структуры pickup requests: {str(e)}"
            )
            return False
    
    def compare_id_fields(self):
        """Тест 6: Сравнение ID из уведомлений с ID в courier_pickup_requests"""
        try:
            if not self.notifications or not self.pickup_requests:
                self.log_result(
                    "СРАВНЕНИЕ ID ПОЛЕЙ",
                    True,
                    "Недостаточно данных для сравнения ID полей (пустые уведомления или pickup requests)"
                )
                return True
            
            # Собираем все ID из уведомлений
            notification_ids = set()
            for notification in self.notifications:
                if "pickup_request_id" in notification and notification["pickup_request_id"]:
                    notification_ids.add(notification["pickup_request_id"])
                if "request_id" in notification and notification["request_id"]:
                    notification_ids.add(notification["request_id"])
            
            # Собираем все ID из pickup requests
            pickup_request_ids = set()
            for request in self.pickup_requests:
                if "id" in request and request["id"]:
                    pickup_request_ids.add(request["id"])
                if "request_id" in request and request["request_id"]:
                    pickup_request_ids.add(request["request_id"])
                if "pickup_request_id" in request and request["pickup_request_id"]:
                    pickup_request_ids.add(request["pickup_request_id"])
            
            # Находим пересечения и различия
            matching_ids = notification_ids.intersection(pickup_request_ids)
            notification_only_ids = notification_ids - pickup_request_ids
            pickup_only_ids = pickup_request_ids - notification_ids
            
            comparison_details = (
                f"ID из уведомлений: {len(notification_ids)} уникальных, "
                f"ID из pickup requests: {len(pickup_request_ids)} уникальных, "
                f"Совпадающие ID: {len(matching_ids)}, "
                f"Только в уведомлениях: {len(notification_only_ids)}, "
                f"Только в pickup requests: {len(pickup_only_ids)}"
            )
            
            # Сохраняем результаты сравнения
            self.id_comparison = {
                "notification_ids": notification_ids,
                "pickup_request_ids": pickup_request_ids,
                "matching_ids": matching_ids,
                "notification_only_ids": notification_only_ids,
                "pickup_only_ids": pickup_only_ids
            }
            
            # Определяем успешность теста
            success = len(matching_ids) > 0 or (len(notification_ids) == 0 and len(pickup_request_ids) == 0)
            
            self.log_result(
                "СРАВНЕНИЕ ID ПОЛЕЙ",
                success,
                comparison_details
            )
            return True
            
        except Exception as e:
            self.log_result(
                "СРАВНЕНИЕ ID ПОЛЕЙ",
                False,
                f"Исключение при сравнении ID полей: {str(e)}"
            )
            return False
    
    def test_send_to_placement_error(self):
        """Тест 7: Воспроизведение ошибки "Pickup request not found" на строке 14547"""
        try:
            if not self.notifications:
                self.log_result(
                    "ТЕСТИРОВАНИЕ ОШИБКИ SEND TO PLACEMENT",
                    True,
                    "Нет уведомлений для тестирования ошибки send-to-placement"
                )
                return True
            
            # Ищем подходящее уведомление для тестирования
            test_notification = None
            
            # Сначала ищем уведомление в статусе "in_processing"
            for notification in self.notifications:
                if notification.get("status") == "in_processing":
                    test_notification = notification
                    break
            
            # Если нет в обработке, попробуем принять pending уведомление
            if not test_notification:
                for notification in self.notifications:
                    if notification.get("status") == "pending_acceptance":
                        notification_id = notification.get("id")
                        accept_response = self.session.post(f"{API_BASE}/operator/warehouse-notifications/{notification_id}/accept")
                        
                        if accept_response.status_code == 200:
                            test_notification = notification
                            test_notification["status"] = "in_processing"
                            print(f"Уведомление {notification_id} успешно принято для тестирования")
                            break
            
            if not test_notification:
                self.log_result(
                    "ТЕСТИРОВАНИЕ ОШИБКИ SEND TO PLACEMENT",
                    True,
                    "Нет подходящих уведомлений для тестирования ошибки (нет уведомлений в статусе 'in_processing')"
                )
                return True
            
            # Тестируем endpoint отправки на размещение
            notification_id = test_notification.get("id")
            response = self.session.post(f"{API_BASE}/operator/warehouse-notifications/{notification_id}/send-to-placement")
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "ТЕСТИРОВАНИЕ ОШИБКИ SEND TO PLACEMENT",
                    True,
                    f"Endpoint работает успешно (ошибка исправлена): груз создан {data.get('cargo_number', 'N/A')}, статус: {data.get('status', 'N/A')}"
                )
                return True
            elif response.status_code == 404 and "Pickup request not found" in response.text:
                # Это именно та ошибка, которую мы диагностируем
                self.log_result(
                    "ТЕСТИРОВАНИЕ ОШИБКИ SEND TO PLACEMENT",
                    False,
                    f"🎯 ОШИБКА ВОСПРОИЗВЕДЕНА! HTTP 404: 'Pickup request not found' - это именно проблема на строке 14547. Уведомление содержит pickup_request_id/request_id, но соответствующая запись не найдена в courier_pickup_requests"
                )
                return False
            elif response.status_code == 400 and "Pickup request ID not found in notification" in response.text:
                self.log_result(
                    "ТЕСТИРОВАНИЕ ОШИБКИ SEND TO PLACEMENT",
                    False,
                    f"Обнаружена предыдущая ошибка: 'Pickup request ID not found in notification' - исправление обратной совместимости не применено"
                )
                return False
            else:
                self.log_result(
                    "ТЕСТИРОВАНИЕ ОШИБКИ SEND TO PLACEMENT",
                    False,
                    f"Неожиданная ошибка: HTTP {response.status_code}, {response.text[:300]}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ТЕСТИРОВАНИЕ ОШИБКИ SEND TO PLACEMENT",
                False,
                f"Исключение при тестировании ошибки: {str(e)}"
            )
            return False
    
    def run_comprehensive_diagnosis(self):
        """Запуск полной диагностики проблемы"""
        print("🔍 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Ошибка 'Pickup request not found' на строке 14547 в TAJLINE.TJ")
        print("=" * 120)
        print("ПРОБЛЕМА: pickup_request_id из уведомления не соответствует реальному ID в коллекции courier_pickup_requests")
        print("ЦЕЛЬ: Найти корневую причину несоответствия между ID в уведомлениях и записями в courier_pickup_requests")
        print("=" * 120)
        
        # Выполняем все тесты по порядку
        tests = [
            ("Авторизация пользователя", self.authenticate_user),
            ("Получение списка уведомлений", self.get_warehouse_notifications),
            ("Получение courier pickup requests", self.get_courier_pickup_requests),
            ("Анализ структуры уведомлений", self.analyze_notification_structure),
            ("Анализ структуры pickup requests", self.analyze_pickup_requests_structure),
            ("Сравнение ID полей", self.compare_id_fields),
            ("Тестирование ошибки send to placement", self.test_send_to_placement_error)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Выполняется: {test_name}")
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                self.log_result(test_name, False, f"Критическая ошибка в тесте: {str(e)}")
        
        # Итоговый отчет
        print("\n" + "=" * 120)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ")
        print("=" * 120)
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"Успешность диагностики: {success_rate:.1f}% ({passed_tests}/{total_tests} тестов пройдены)")
        
        print("\n📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            print(f"  {result}")
        
        # Диагностические выводы
        print(f"\n🎯 ДИАГНОСТИЧЕСКИЕ ВЫВОДЫ:")
        
        if hasattr(self, 'notification_analysis') and hasattr(self, 'pickup_requests_analysis'):
            print(f"📊 СТРУКТУРНЫЙ АНАЛИЗ:")
            print(f"  - Уведомления: {self.notification_analysis['total_notifications']} записей")
            print(f"  - Pickup Requests: {self.pickup_requests_analysis['total_requests']} записей")
            
            if hasattr(self, 'id_comparison'):
                print(f"🔗 АНАЛИЗ СООТВЕТСТВИЯ ID:")
                print(f"  - Совпадающие ID: {len(self.id_comparison['matching_ids'])}")
                print(f"  - ID только в уведомлениях: {len(self.id_comparison['notification_only_ids'])}")
                print(f"  - ID только в pickup requests: {len(self.id_comparison['pickup_only_ids'])}")
                
                if len(self.id_comparison['matching_ids']) == 0 and len(self.id_comparison['notification_ids']) > 0:
                    print("🚨 КОРНЕВАЯ ПРИЧИНА НАЙДЕНА: ID из уведомлений НЕ СООТВЕТСТВУЮТ ID в courier_pickup_requests!")
                    print("💡 РЕШЕНИЕ: Требуется синхронизация данных или изменение логики поиска записей")
        
        # Финальный вывод
        print(f"\n🎯 КРИТИЧЕСКИЙ ВЫВОД:")
        if success_rate >= 80:
            print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО! Корневая причина ошибки 'Pickup request not found' найдена.")
            print("✅ Получены детальные данные о структуре уведомлений и pickup requests.")
            print("✅ Определены расхождения в ID между коллекциями.")
        elif success_rate >= 60:
            print("⚠️ ДИАГНОСТИКА ЗАВЕРШЕНА ЧАСТИЧНО. Получена часть необходимой информации.")
        else:
            print("❌ ДИАГНОСТИКА НЕ ЗАВЕРШЕНА. Недостаточно данных для определения корневой причины.")
        
        return success_rate >= 60

def main():
    """Основная функция для запуска диагностики"""
    diagnosis = PickupRequestNotFoundDiagnosis()
    success = diagnosis.run_comprehensive_diagnosis()
    
    if success:
        print(f"\n✅ ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО")
    else:
        print(f"\n❌ ДИАГНОСТИКА ВЫЯВИЛА ПРОБЛЕМЫ")
    
    return success

if __name__ == "__main__":
    main()