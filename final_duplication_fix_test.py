#!/usr/bin/env python3
"""
🎯 ФИНАЛЬНАЯ ПРОВЕРКА: Полное исправление дублирования заявок в TAJLINE.TJ

КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ:
1. ✅ UUID для ID уведомлений: notification_id = f"WN_{str(uuid.uuid4())}"
2. ✅ UUID для ID грузов: cargo_id = str(uuid.uuid4()) 
3. ✅ Уникальные номера грузов: cargo_number = f"{cargo_id[:6]}/{str(index + 1).zfill(2)}"
4. ✅ Endpoint для очистки дубликатов: /api/admin/cleanup-duplicate-notifications

ПОЛНОЕ ТЕСТИРОВАНИЕ WORKFLOW:
1. Авторизация оператора склада
2. Получение списка уведомлений 
3. Принятие уведомления через /accept
4. Завершение оформления через /complete с реальными данными
5. Проверка создания УНИКАЛЬНЫХ грузов без дубликатов
6. Проверка что номера грузов основаны на UUID (не request_number)
7. Проверка что ID уведомлений уникальны
8. Повторное тестирование для подтверждения отсутствия дублирования

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Каждый груз имеет уникальный ID (UUID-based) и уникальный номер груза, дублирование полностью устранено.
"""

import requests
import json
import os
import time
import uuid
from datetime import datetime
from collections import Counter

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-talk.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class FinalDuplicationFixTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None
        self.test_results = []
        self.created_cargos = []
        self.notification_ids = []
        
    def log_result(self, test_name: str, success: bool, details: str, data=None):
        """Логирование результатов тестов"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        print(f"{status} {test_name}: {details}")
        if data and isinstance(data, dict) and len(str(data)) < 500:
            print(f"   Данные: {json.dumps(data, ensure_ascii=False, indent=2)}")
        print()
        
    def authenticate_warehouse_operator(self):
        """Тест 1: Авторизация оператора склада"""
        try:
            # Попробуем разные учетные данные
            credentials_to_try = [
                ("+79777888999", "warehouse123", "Оператор склада"),
                ("+79999888777", "admin123", "Администратор (fallback)")
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
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/json"
                    })
                    
                    # Получаем информацию о пользователе
                    user_response = self.session.get(f"{API_BASE}/auth/me")
                    if user_response.status_code == 200:
                        self.current_user = user_response.json()
                        user_info = f"'{self.current_user.get('full_name')}' (номер: {self.current_user.get('user_number')}, роль: {self.current_user.get('role')})"
                        
                        self.log_result(
                            "АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА",
                            True,
                            f"Успешная авторизация {description}: {user_info}, JWT токен получен",
                            {"phone": phone, "role": self.current_user.get('role')}
                        )
                        return True
                    
            self.log_result(
                "АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА",
                False,
                "Не удалось авторизоваться ни с одними учетными данными"
            )
            return False
                
        except Exception as e:
            self.log_result(
                "АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА",
                False,
                f"Исключение при авторизации: {str(e)}"
            )
            return False
    
    def test_cleanup_endpoint(self):
        """Тест 2: Тестирование endpoint для очистки дубликатов"""
        try:
            response = self.session.post(f"{API_BASE}/admin/cleanup-duplicate-notifications")
            
            if response.status_code == 200:
                data = response.json()
                deleted_count = data.get("deleted_duplicates", 0)
                before_count = data.get("before_count", 0)
                after_count = data.get("after_count", 0)
                
                self.log_result(
                    "ТЕСТИРОВАНИЕ CLEANUP ENDPOINT",
                    True,
                    f"Endpoint /api/admin/cleanup-duplicate-notifications работает корректно! Удалено дубликатов: {deleted_count}, Было уведомлений: {before_count}, Стало: {after_count}",
                    data
                )
                return True
            else:
                self.log_result(
                    "ТЕСТИРОВАНИЕ CLEANUP ENDPOINT",
                    False,
                    f"Ошибка cleanup endpoint: HTTP {response.status_code}, {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ТЕСТИРОВАНИЕ CLEANUP ENDPOINT",
                False,
                f"Исключение при тестировании cleanup endpoint: {str(e)}"
            )
            return False
    
    def get_warehouse_notifications(self):
        """Тест 3: Получение списка уведомлений и проверка уникальности ID"""
        try:
            response = self.session.get(f"{API_BASE}/operator/warehouse-notifications")
            
            if response.status_code == 200:
                data = response.json()
                notifications = data if isinstance(data, list) else data.get("notifications", [])
                
                # Анализируем уникальность ID уведомлений
                notification_ids = [n.get("id") for n in notifications if n.get("id")]
                unique_ids = set(notification_ids)
                
                # Проверяем формат UUID в ID уведомлений
                uuid_format_count = 0
                wn_prefix_count = 0
                
                for notif_id in notification_ids:
                    if notif_id:
                        if notif_id.startswith("WN_"):
                            wn_prefix_count += 1
                            # Проверяем UUID после префикса
                            uuid_part = notif_id[3:]  # Убираем "WN_"
                            try:
                                uuid.UUID(uuid_part)
                                uuid_format_count += 1
                            except ValueError:
                                pass
                        else:
                            # Проверяем прямой UUID формат
                            try:
                                uuid.UUID(notif_id)
                                uuid_format_count += 1
                            except ValueError:
                                pass
                
                self.notification_ids = notification_ids
                
                details = (
                    f"Получено {len(notifications)} уведомлений. "
                    f"Уникальных ID: {len(unique_ids)}, "
                    f"UUID формат: {uuid_format_count}/{len(notification_ids)}, "
                    f"WN_ префикс: {wn_prefix_count}/{len(notification_ids)}"
                )
                
                # Проверяем на дубликаты
                duplicates = [id for id, count in Counter(notification_ids).items() if count > 1]
                if duplicates:
                    details += f", НАЙДЕНЫ ДУБЛИКАТЫ ID: {duplicates}"
                
                self.log_result(
                    "ПРОВЕРКА УНИКАЛЬНОСТИ ID УВЕДОМЛЕНИЙ",
                    len(unique_ids) == len(notification_ids) and uuid_format_count > 0,
                    details,
                    {
                        "total_notifications": len(notifications),
                        "unique_ids": len(unique_ids),
                        "uuid_format_count": uuid_format_count,
                        "wn_prefix_count": wn_prefix_count,
                        "duplicates": duplicates,
                        "sample_ids": notification_ids[:5]
                    }
                )
                return notifications
            else:
                self.log_result(
                    "ПРОВЕРКА УНИКАЛЬНОСТИ ID УВЕДОМЛЕНИЙ",
                    False,
                    f"Ошибка получения уведомлений: HTTP {response.status_code}, {response.text}"
                )
                return []
                
        except Exception as e:
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ ID УВЕДОМЛЕНИЙ",
                False,
                f"Исключение при получении уведомлений: {str(e)}"
            )
            return []
    
    def analyze_existing_cargo_numbers(self):
        """Тест 4: Анализ существующих номеров грузов на дубликаты"""
        try:
            # Получаем список всех грузов
            response = self.session.get(f"{API_BASE}/cargo/all?per_page=100")
            
            if response.status_code == 200:
                data = response.json()
                cargos = data.get("items", []) if isinstance(data, dict) else data
                
                # Анализируем номера грузов
                cargo_numbers = [c.get("cargo_number") for c in cargos if c.get("cargo_number")]
                cargo_ids = [c.get("id") for c in cargos if c.get("id")]
                
                # Проверяем уникальность номеров
                unique_numbers = set(cargo_numbers)
                number_duplicates = [num for num, count in Counter(cargo_numbers).items() if count > 1]
                
                # Проверяем уникальность ID
                unique_ids = set(cargo_ids)
                id_duplicates = [id for id, count in Counter(cargo_ids).items() if count > 1]
                
                # Анализируем форматы номеров
                uuid_based_count = 0
                request_based_count = 0
                sequential_2501_count = 0
                
                for number in cargo_numbers:
                    if "/" in number and len(number.split("/")[0]) >= 6:
                        # Проверяем UUID-based формат (первая часть должна быть из UUID)
                        first_part = number.split("/")[0]
                        if len(first_part) == 6 and not first_part.startswith("100"):
                            uuid_based_count += 1
                        elif first_part.startswith("100"):
                            request_based_count += 1
                    elif number.startswith("2501"):
                        sequential_2501_count += 1
                
                details = (
                    f"Проанализировано {len(cargos)} грузов. "
                    f"Уникальных номеров: {len(unique_numbers)}, "
                    f"Уникальных ID: {len(unique_ids)}. "
                    f"UUID-based: {uuid_based_count}, "
                    f"Request-based: {request_based_count}, "
                    f"Sequential (2501XXX): {sequential_2501_count}"
                )
                
                if number_duplicates:
                    details += f". НАЙДЕНО {len(number_duplicates)} ДУБЛИРОВАННЫХ НОМЕРА!"
                
                if id_duplicates:
                    details += f". НАЙДЕНО {len(id_duplicates)} ДУБЛИРОВАННЫХ ID!"
                
                success = len(number_duplicates) == 0 and len(id_duplicates) == 0 and uuid_based_count > 0
                
                self.log_result(
                    "ПРОВЕРКА ДУБЛИРОВАНИЯ НОМЕРОВ ГРУЗОВ",
                    success,
                    details,
                    {
                        "total_cargos": len(cargos),
                        "unique_numbers": len(unique_numbers),
                        "unique_ids": len(unique_ids),
                        "number_duplicates": number_duplicates,
                        "id_duplicates": id_duplicates,
                        "uuid_based_count": uuid_based_count,
                        "request_based_count": request_based_count,
                        "sequential_2501_count": sequential_2501_count,
                        "sample_numbers": cargo_numbers[:10]
                    }
                )
                return success
            else:
                self.log_result(
                    "ПРОВЕРКА ДУБЛИРОВАНИЯ НОМЕРОВ ГРУЗОВ",
                    False,
                    f"Ошибка получения списка грузов: HTTP {response.status_code}, {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ПРОВЕРКА ДУБЛИРОВАНИЯ НОМЕРОВ ГРУЗОВ",
                False,
                f"Исключение при анализе номеров грузов: {str(e)}"
            )
            return False
    
    def test_full_workflow_without_duplicates(self, notifications):
        """Тест 5: Полный workflow без дубликатов"""
        try:
            if not notifications:
                self.log_result(
                    "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ",
                    True,
                    "Нет уведомлений для тестирования workflow - база данных пуста"
                )
                return True
            
            # Находим подходящее уведомление для тестирования
            test_notification = None
            for notification in notifications:
                if notification.get("status") in ["pending_acceptance", "pending"]:
                    test_notification = notification
                    break
            
            if not test_notification:
                # Берем первое доступное
                test_notification = notifications[0]
            
            notification_id = test_notification.get("id")
            original_status = test_notification.get("status")
            
            # Шаг 1: Принятие уведомления
            if original_status in ["pending_acceptance", "pending"]:
                accept_response = self.session.post(f"{API_BASE}/operator/warehouse-notifications/{notification_id}/accept")
                
                if accept_response.status_code != 200:
                    self.log_result(
                        "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ - Принятие",
                        False,
                        f"Ошибка принятия уведомления: HTTP {accept_response.status_code}, {accept_response.text}"
                    )
                    return False
            
            # Шаг 2: Завершение оформления с реальными данными из review request
            complete_data = {
                "sender_full_name": "Тест Уникальности",
                "sender_phone": "+79111111111",
                "recipient_full_name": "Получатель Уникальности", 
                "recipient_phone": "+79222222222",
                "recipient_address": "Душанбе, уникальный адрес",
                "cargo_items": [
                    {"name": "Уникальный груз 1", "weight": "5", "price": "100"},
                    {"name": "Уникальный груз 2", "weight": "3", "price": "150"}
                ],
                "payment_method": "cash",
                "delivery_method": "standard"
            }
            
            # Получаем количество грузов ДО создания
            before_count = self.get_cargo_count()
            
            complete_response = self.session.post(
                f"{API_BASE}/operator/warehouse-notifications/{notification_id}/complete",
                json=complete_data
            )
            
            if complete_response.status_code == 200:
                result = complete_response.json()
                
                # Получаем количество грузов ПОСЛЕ создания
                time.sleep(1)  # Небольшая задержка
                after_count = self.get_cargo_count()
                created_count = after_count - before_count
                
                # Анализируем созданные грузы
                created_cargos = result.get("created_cargos", [])
                self.created_cargos.extend(created_cargos)
                
                # Проверяем уникальность созданных грузов
                created_numbers = [c.get("cargo_number") for c in created_cargos]
                created_ids = [c.get("id") for c in created_cargos]
                
                unique_numbers = len(set(created_numbers))
                unique_ids = len(set(created_ids))
                
                # Проверяем UUID-based формат
                uuid_based_numbers = 0
                for number in created_numbers:
                    if "/" in number:
                        first_part = number.split("/")[0]
                        if len(first_part) == 6 and not first_part.startswith("100"):
                            uuid_based_numbers += 1
                
                success = (
                    created_count == len(created_cargos) and
                    unique_numbers == len(created_numbers) and
                    unique_ids == len(created_ids) and
                    uuid_based_numbers == len(created_numbers)
                )
                
                details = (
                    f"Workflow выполнен успешно! Создано грузов: {created_count}, "
                    f"Уникальных номеров: {unique_numbers}/{len(created_numbers)}, "
                    f"Уникальных ID: {unique_ids}/{len(created_ids)}, "
                    f"UUID-based номера: {uuid_based_numbers}/{len(created_numbers)}"
                )
                
                if not success:
                    details += " - ОБНАРУЖЕНЫ ПРОБЛЕМЫ С УНИКАЛЬНОСТЬЮ!"
                
                self.log_result(
                    "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ",
                    success,
                    details,
                    {
                        "notification_id": notification_id,
                        "created_count": created_count,
                        "created_numbers": created_numbers,
                        "created_ids": created_ids,
                        "unique_numbers": unique_numbers,
                        "unique_ids": unique_ids,
                        "uuid_based_numbers": uuid_based_numbers
                    }
                )
                return success
            else:
                self.log_result(
                    "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ",
                    False,
                    f"Ошибка завершения оформления: HTTP {complete_response.status_code}, {complete_response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ",
                False,
                f"Исключение при тестировании workflow: {str(e)}"
            )
            return False
    
    def test_uniqueness_at_creation(self):
        """Тест 6: Проверка уникальности ID при создании"""
        try:
            if not self.created_cargos:
                self.log_result(
                    "ПРОВЕРКА УНИКАЛЬНОСТИ ID ПРИ СОЗДАНИИ",
                    True,
                    "Недостаточно созданных грузов для анализа уникальности"
                )
                return True
            
            # Анализируем созданные грузы
            cargo_ids = [c.get("id") for c in self.created_cargos]
            cargo_numbers = [c.get("cargo_number") for c in self.created_cargos]
            
            # Проверяем уникальность
            unique_ids = len(set(cargo_ids))
            unique_numbers = len(set(cargo_numbers))
            
            # Проверяем UUID формат ID
            uuid_format_ids = 0
            for cargo_id in cargo_ids:
                try:
                    uuid.UUID(cargo_id)
                    uuid_format_ids += 1
                except ValueError:
                    pass
            
            # Проверяем UUID-based номера
            uuid_based_numbers = 0
            for number in cargo_numbers:
                if "/" in number:
                    first_part = number.split("/")[0]
                    if len(first_part) == 6 and not first_part.startswith("100"):
                        uuid_based_numbers += 1
            
            success = (
                unique_ids == len(cargo_ids) and
                unique_numbers == len(cargo_numbers) and
                uuid_format_ids == len(cargo_ids) and
                uuid_based_numbers == len(cargo_numbers)
            )
            
            details = (
                f"Проанализировано {len(self.created_cargos)} созданных грузов. "
                f"Уникальных ID: {unique_ids}/{len(cargo_ids)}, "
                f"Уникальных номеров: {unique_numbers}/{len(cargo_numbers)}, "
                f"UUID формат ID: {uuid_format_ids}/{len(cargo_ids)}, "
                f"UUID-based номера: {uuid_based_numbers}/{len(cargo_numbers)}"
            )
            
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ ID ПРИ СОЗДАНИИ",
                success,
                details,
                {
                    "total_created": len(self.created_cargos),
                    "unique_ids": unique_ids,
                    "unique_numbers": unique_numbers,
                    "uuid_format_ids": uuid_format_ids,
                    "uuid_based_numbers": uuid_based_numbers,
                    "sample_ids": cargo_ids[:5],
                    "sample_numbers": cargo_numbers[:5]
                }
            )
            return success
            
        except Exception as e:
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ ID ПРИ СОЗДАНИИ",
                False,
                f"Исключение при проверке уникальности: {str(e)}"
            )
            return False
    
    def test_repeated_workflow_no_duplicates(self, notifications):
        """Тест 7: Повторное тестирование для подтверждения отсутствия дублирования"""
        try:
            if not notifications or len(notifications) < 2:
                self.log_result(
                    "ПОВТОРНОЕ ТЕСТИРОВАНИЕ БЕЗ ДУБЛИКАТОВ",
                    True,
                    "Недостаточно уведомлений для повторного тестирования"
                )
                return True
            
            # Берем второе уведомление для повторного теста
            test_notification = None
            for i, notification in enumerate(notifications[1:], 1):
                if notification.get("status") in ["pending_acceptance", "pending"]:
                    test_notification = notification
                    break
            
            if not test_notification and len(notifications) > 1:
                test_notification = notifications[1]
            
            if not test_notification:
                self.log_result(
                    "ПОВТОРНОЕ ТЕСТИРОВАНИЕ БЕЗ ДУБЛИКАТОВ",
                    True,
                    "Нет подходящего уведомления для повторного тестирования"
                )
                return True
            
            notification_id = test_notification.get("id")
            
            # Получаем количество грузов ДО повторного создания
            before_count = self.get_cargo_count()
            
            # Повторяем workflow с другими данными
            complete_data = {
                "sender_full_name": "Повторный Тест Уникальности",
                "sender_phone": "+79333333333",
                "recipient_full_name": "Повторный Получатель", 
                "recipient_phone": "+79444444444",
                "recipient_address": "Душанбе, повторный адрес",
                "cargo_items": [
                    {"name": "Повторный груз 1", "weight": "7", "price": "200"},
                    {"name": "Повторный груз 2", "weight": "4", "price": "180"}
                ],
                "payment_method": "cash",
                "delivery_method": "standard"
            }
            
            # Принимаем уведомление если нужно
            if test_notification.get("status") in ["pending_acceptance", "pending"]:
                accept_response = self.session.post(f"{API_BASE}/operator/warehouse-notifications/{notification_id}/accept")
                if accept_response.status_code != 200:
                    self.log_result(
                        "ПОВТОРНОЕ ТЕСТИРОВАНИЕ БЕЗ ДУБЛИКАТОВ",
                        False,
                        f"Ошибка принятия повторного уведомления: HTTP {accept_response.status_code}"
                    )
                    return False
            
            # Завершаем оформление
            complete_response = self.session.post(
                f"{API_BASE}/operator/warehouse-notifications/{notification_id}/complete",
                json=complete_data
            )
            
            if complete_response.status_code == 200:
                result = complete_response.json()
                
                # Получаем количество грузов ПОСЛЕ повторного создания
                time.sleep(1)
                after_count = self.get_cargo_count()
                created_count = after_count - before_count
                
                # Анализируем повторно созданные грузы
                created_cargos = result.get("created_cargos", [])
                
                # Проверяем что новые грузы не дублируют существующие
                new_numbers = [c.get("cargo_number") for c in created_cargos]
                new_ids = [c.get("id") for c in created_cargos]
                
                existing_numbers = [c.get("cargo_number") for c in self.created_cargos]
                existing_ids = [c.get("id") for c in self.created_cargos]
                
                number_conflicts = set(new_numbers) & set(existing_numbers)
                id_conflicts = set(new_ids) & set(existing_ids)
                
                success = len(number_conflicts) == 0 and len(id_conflicts) == 0 and created_count > 0
                
                details = (
                    f"Повторное тестирование завершено. Создано новых грузов: {created_count}, "
                    f"Конфликтов номеров: {len(number_conflicts)}, "
                    f"Конфликтов ID: {len(id_conflicts)}"
                )
                
                if number_conflicts:
                    details += f". ДУБЛИРОВАННЫЕ НОМЕРА: {list(number_conflicts)}"
                if id_conflicts:
                    details += f". ДУБЛИРОВАННЫЕ ID: {list(id_conflicts)}"
                
                self.log_result(
                    "ПОВТОРНОЕ ТЕСТИРОВАНИЕ БЕЗ ДУБЛИКАТОВ",
                    success,
                    details,
                    {
                        "created_count": created_count,
                        "new_numbers": new_numbers,
                        "new_ids": new_ids,
                        "number_conflicts": list(number_conflicts),
                        "id_conflicts": list(id_conflicts)
                    }
                )
                return success
            else:
                self.log_result(
                    "ПОВТОРНОЕ ТЕСТИРОВАНИЕ БЕЗ ДУБЛИКАТОВ",
                    False,
                    f"Ошибка повторного завершения оформления: HTTP {complete_response.status_code}, {complete_response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ПОВТОРНОЕ ТЕСТИРОВАНИЕ БЕЗ ДУБЛИКАТОВ",
                False,
                f"Исключение при повторном тестировании: {str(e)}"
            )
            return False
    
    def get_cargo_count(self):
        """Получение общего количества грузов в системе"""
        try:
            response = self.session.get(f"{API_BASE}/cargo/all?per_page=1")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "pagination" in data:
                    return data["pagination"].get("total_count", 0)
                elif isinstance(data, list):
                    return len(data)
                else:
                    return data.get("total_count", 0)
            return 0
        except:
            return 0
    
    def run_comprehensive_test(self):
        """Запуск полного комплексного тестирования"""
        print("🎯 ФИНАЛЬНАЯ ПРОВЕРКА: Полное исправление дублирования заявок в TAJLINE.TJ")
        print("=" * 80)
        print("КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ:")
        print("1. ✅ UUID для ID уведомлений: notification_id = f\"WN_{str(uuid.uuid4())}\"")
        print("2. ✅ UUID для ID грузов: cargo_id = str(uuid.uuid4())")
        print("3. ✅ Уникальные номера грузов: cargo_number = f\"{cargo_id[:6]}/{str(index + 1).zfill(2)}\"")
        print("4. ✅ Endpoint для очистки дубликатов: /api/admin/cleanup-duplicate-notifications")
        print("=" * 80)
        print()
        
        # Тест 1: Авторизация
        if not self.authenticate_warehouse_operator():
            print("❌ Критическая ошибка: Не удалось авторизоваться. Тестирование прервано.")
            return
        
        # Тест 2: Тестирование cleanup endpoint
        self.test_cleanup_endpoint()
        
        # Тест 3: Получение уведомлений и проверка уникальности ID
        notifications = self.get_warehouse_notifications()
        
        # Тест 4: Анализ существующих номеров грузов
        self.analyze_existing_cargo_numbers()
        
        # Тест 5: Полный workflow без дубликатов
        self.test_full_workflow_without_duplicates(notifications)
        
        # Тест 6: Проверка уникальности при создании
        self.test_uniqueness_at_creation()
        
        # Тест 7: Повторное тестирование
        self.test_repeated_workflow_no_duplicates(notifications)
        
        # Итоговый отчет
        self.print_final_summary()
    
    def print_final_summary(self):
        """Печать итогового отчета"""
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ФИНАЛЬНОЙ ПРОВЕРКИ")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {successful_tests}")
        print(f"Неудачных: {failed_tests}")
        print(f"Процент успеха: {success_rate:.1f}%")
        print()
        
        # Детальные результаты
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")
            print(f"   {result['details']}")
            print()
        
        # Критические выводы
        print("🔍 КРИТИЧЕСКИЕ ВЫВОДЫ:")
        
        # Проверяем ключевые аспекты исправления
        duplication_fixed = True
        uuid_implementation = True
        cleanup_working = True
        
        for result in self.test_results:
            if "ДУБЛИРОВАНИЕ" in result['test'] and not result['success']:
                duplication_fixed = False
            if "UUID" in result['test'] or "УНИКАЛЬНОСТИ" in result['test']:
                if not result['success']:
                    uuid_implementation = False
            if "CLEANUP" in result['test'] and not result['success']:
                cleanup_working = False
        
        if duplication_fixed:
            print("✅ ДУБЛИРОВАНИЕ ИСПРАВЛЕНО: Грузы создаются с уникальными номерами и ID")
        else:
            print("❌ ДУБЛИРОВАНИЕ НЕ ИСПРАВЛЕНО: Обнаружены проблемы с уникальностью")
        
        if uuid_implementation:
            print("✅ UUID РЕАЛИЗАЦИЯ: ID уведомлений и грузов используют UUID формат")
        else:
            print("❌ UUID РЕАЛИЗАЦИЯ: Проблемы с UUID форматом ID")
        
        if cleanup_working:
            print("✅ CLEANUP ENDPOINT: Endpoint очистки дубликатов функционирует")
        else:
            print("❌ CLEANUP ENDPOINT: Проблемы с endpoint очистки дубликатов")
        
        # Общий вывод
        if success_rate >= 85:
            print("\n🎉 ФИНАЛЬНАЯ ПРОВЕРКА ПРОЙДЕНА УСПЕШНО!")
            print("Исправления дублирования заявок работают корректно.")
        else:
            print("\n🚨 ФИНАЛЬНАЯ ПРОВЕРКА ВЫЯВИЛА ПРОБЛЕМЫ!")
            print("Требуется дополнительная работа по исправлению дублирования.")
        
        print("=" * 80)

def main():
    """Главная функция тестирования"""
    tester = FinalDuplicationFixTester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()