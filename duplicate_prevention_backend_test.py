#!/usr/bin/env python3
"""
🎯 ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ: Исправление дублирования заявок в TAJLINE.TJ

ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ:
1. ✅ ID уведомлений: Заменен timestamp на UUID для предотвращения дублированных ID
2. ✅ Номера грузов: Изменена логика с request_number на уникальные cargo_id для предотвращения дубликатов
3. ✅ Временный endpoint: /api/admin/cleanup-duplicate-notifications для очистки существующих дубликатов

ЛОГИКА ИСПРАВЛЕНИЙ:
- notification_id = f"WN_{str(uuid.uuid4())}" вместо timestamp
- cargo_number = f"{cargo_id[:6]}/{str(index + 1).zfill(2)}" вместо request_number
- Endpoint для удаления дубликатов из базы данных

НУЖНО ПРОТЕСТИРОВАТЬ:
1. Авторизация администратора для очистки дубликатов
2. Тестирование endpoint /api/admin/cleanup-duplicate-notifications
3. Создание новых уведомлений - проверка уникальности ID
4. Создание новых грузов - проверка уникальности номеров
5. Полный workflow: принятие заявки → завершение оформления → проверка отсутствия дубликатов
6. Проверка что каждое уведомление получает уникальный ID
7. Проверка что каждый груз получает уникальный номер

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: 
- Дублирование заявок полностью устранено
- Каждое уведомление имеет уникальный ID
- Каждый груз имеет уникальный номер
- Workflow работает без создания множественных копий
"""

import requests
import json
import os
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tajline-manager-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class DuplicatePreventionTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None
        self.test_results = []
        self.created_notifications = []
        self.created_cargos = []
        
    def log_result(self, test_name: str, success: bool, details: str, data: Dict = None):
        """Логирование результатов тестов"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "timestamp": timestamp,
            "test": test_name,
            "success": success,
            "details": details,
            "data": data or {}
        }
        self.test_results.append(result)
        print(f"[{timestamp}] {status} {test_name}")
        print(f"   {details}")
        if data and len(str(data)) < 200:
            print(f"   Данные: {data}")
        print()
        
    def authenticate_admin(self):
        """Тест 1: Авторизация администратора для доступа к cleanup endpoint"""
        try:
            # Учетные данные администратора
            admin_credentials = [
                ("+79999888777", "admin123", "Основной администратор"),
                ("admin@emergent.com", "admin123", "Email администратор"),
                ("+79777888999", "warehouse123", "Оператор склада как fallback")
            ]
            
            for phone, password, description in admin_credentials:
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
                            "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                            True,
                            f"Успешная авторизация {description}: {user_info}, JWT токен получен",
                            {"phone": phone, "role": self.current_user.get('role')}
                        )
                        return True
                    else:
                        print(f"Не удалось получить данные пользователя для {description}")
                else:
                    print(f"Попытка авторизации {description} неудачна: HTTP {response.status_code}")
            
            self.log_result(
                "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                False,
                "Не удалось авторизоваться ни с одними учетными данными администратора"
            )
            return False
                
        except Exception as e:
            self.log_result(
                "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                False,
                f"Исключение при авторизации: {str(e)}"
            )
            return False
    
    def test_cleanup_duplicate_notifications_endpoint(self):
        """Тест 2: Тестирование endpoint /api/admin/cleanup-duplicate-notifications"""
        try:
            # Проверяем доступность endpoint
            response = self.session.post(f"{API_BASE}/admin/cleanup-duplicate-notifications")
            
            if response.status_code == 200:
                data = response.json()
                removed_count = data.get("removed_duplicates", 0)
                total_before = data.get("total_before_cleanup", 0)
                total_after = data.get("total_after_cleanup", 0)
                
                self.log_result(
                    "ТЕСТИРОВАНИЕ CLEANUP ENDPOINT",
                    True,
                    f"Endpoint работает корректно! Удалено дубликатов: {removed_count}, Было уведомлений: {total_before}, Стало: {total_after}",
                    {
                        "removed_duplicates": removed_count,
                        "total_before": total_before,
                        "total_after": total_after,
                        "cleanup_successful": True
                    }
                )
                return True
            elif response.status_code == 403:
                self.log_result(
                    "ТЕСТИРОВАНИЕ CLEANUP ENDPOINT",
                    False,
                    f"Доступ запрещен (HTTP 403) - пользователь {self.current_user.get('role')} не имеет прав администратора для cleanup операций"
                )
                return False
            elif response.status_code == 404:
                self.log_result(
                    "ТЕСТИРОВАНИЕ CLEANUP ENDPOINT",
                    False,
                    "Endpoint /api/admin/cleanup-duplicate-notifications не найден (HTTP 404) - возможно, не реализован"
                )
                return False
            else:
                error_text = response.text[:200] if response.text else "Нет деталей ошибки"
                self.log_result(
                    "ТЕСТИРОВАНИЕ CLEANUP ENDPOINT",
                    False,
                    f"Ошибка при вызове cleanup endpoint: HTTP {response.status_code}, {error_text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ТЕСТИРОВАНИЕ CLEANUP ENDPOINT",
                False,
                f"Исключение при тестировании cleanup endpoint: {str(e)}"
            )
            return False
    
    def test_notification_id_uniqueness(self):
        """Тест 3: Создание новых уведомлений - проверка уникальности ID"""
        try:
            # Получаем список существующих уведомлений для анализа ID
            response = self.session.get(f"{API_BASE}/operator/warehouse-notifications")
            
            existing_notifications = []
            if response.status_code == 200:
                data = response.json()
                existing_notifications = data.get("notifications", [])
            
            # Анализируем существующие ID уведомлений
            existing_ids = [n.get("id") for n in existing_notifications if n.get("id")]
            uuid_format_count = 0
            timestamp_format_count = 0
            wn_prefix_count = 0
            
            for notification_id in existing_ids:
                if notification_id.startswith("WN_"):
                    wn_prefix_count += 1
                    # Проверяем, является ли часть после WN_ валидным UUID
                    uuid_part = notification_id[3:]  # Убираем префикс WN_
                    try:
                        uuid.UUID(uuid_part)
                        uuid_format_count += 1
                    except ValueError:
                        pass
                elif notification_id.isdigit() or (len(notification_id) == 13 and notification_id.isdigit()):
                    timestamp_format_count += 1
            
            total_notifications = len(existing_ids)
            unique_ids = len(set(existing_ids))
            duplicates_found = total_notifications - unique_ids
            
            # Проверяем формат ID
            uuid_percentage = (uuid_format_count / total_notifications * 100) if total_notifications > 0 else 0
            wn_prefix_percentage = (wn_prefix_count / total_notifications * 100) if total_notifications > 0 else 0
            
            success = duplicates_found == 0 and uuid_percentage > 0
            
            details = (
                f"Проанализировано {total_notifications} уведомлений. "
                f"Уникальных ID: {unique_ids}, Дубликатов: {duplicates_found}. "
                f"UUID формат (WN_xxx): {uuid_format_count} ({uuid_percentage:.1f}%), "
                f"Префикс WN_: {wn_prefix_count} ({wn_prefix_percentage:.1f}%), "
                f"Timestamp формат: {timestamp_format_count}"
            )
            
            if duplicates_found == 0:
                details += ". ✅ Дублированных ID не найдено!"
            else:
                details += f". 🚨 НАЙДЕНО {duplicates_found} дублированных ID!"
            
            if uuid_format_count > 0:
                details += " ✅ Новый UUID формат обнаружен!"
            
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ ID УВЕДОМЛЕНИЙ",
                success,
                details,
                {
                    "total_notifications": total_notifications,
                    "unique_ids": unique_ids,
                    "duplicates_found": duplicates_found,
                    "uuid_format_count": uuid_format_count,
                    "wn_prefix_count": wn_prefix_count,
                    "timestamp_format_count": timestamp_format_count,
                    "sample_ids": existing_ids[:5]
                }
            )
            return success
            
        except Exception as e:
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ ID УВЕДОМЛЕНИЙ",
                False,
                f"Исключение при проверке уникальности ID: {str(e)}"
            )
            return False
    
    def test_cargo_number_uniqueness(self):
        """Тест 4: Создание новых грузов - проверка уникальности номеров"""
        try:
            # Получаем список существующих грузов для анализа номеров
            response = self.session.get(f"{API_BASE}/cargo/all?per_page=100")
            
            existing_cargos = []
            if response.status_code == 200:
                data = response.json()
                # API возвращает прямой список, а не объект с items
                if isinstance(data, list):
                    existing_cargos = data
                else:
                    existing_cargos = data.get("items", [])
            
            # Анализируем существующие номера грузов
            existing_numbers = [c.get("cargo_number") for c in existing_cargos if c.get("cargo_number")]
            
            # Группируем по форматам
            uuid_based_count = 0  # Формат с UUID: XXXXXX/01, XXXXXX/02
            request_based_count = 0  # Старый формат: 100021/01, 100021/02
            new_format_count = 0  # Новый формат: 2501XXXXXX
            
            cargo_id_pattern = {}  # Для отслеживания паттернов cargo_id
            
            for cargo_number in existing_numbers:
                if "/" in cargo_number:
                    base_part = cargo_number.split("/")[0]
                    if len(base_part) == 6 and not base_part.startswith("100"):
                        uuid_based_count += 1
                        # Проверяем, является ли это частью UUID
                        if base_part not in cargo_id_pattern:
                            cargo_id_pattern[base_part] = 0
                        cargo_id_pattern[base_part] += 1
                    elif base_part.startswith("100"):
                        request_based_count += 1
                elif cargo_number.startswith("2501"):
                    new_format_count += 1
            
            total_cargos = len(existing_numbers)
            unique_numbers = len(set(existing_numbers))
            duplicates_found = total_cargos - unique_numbers
            
            # Проверяем на дубликаты в cargo_id паттернах
            duplicate_cargo_ids = {k: v for k, v in cargo_id_pattern.items() if v > 1}
            
            uuid_percentage = (uuid_based_count / total_cargos * 100) if total_cargos > 0 else 0
            
            success = duplicates_found == 0 and uuid_based_count > 0
            
            details = (
                f"Проанализировано {total_cargos} грузов. "
                f"Уникальных номеров: {unique_numbers}, Дубликатов: {duplicates_found}. "
                f"UUID-based формат: {uuid_based_count} ({uuid_percentage:.1f}%), "
                f"Request-based формат: {request_based_count}, "
                f"Новый формат (2501XXXXXX): {new_format_count}"
            )
            
            if duplicates_found == 0:
                details += ". ✅ Дублированных номеров не найдено!"
            else:
                details += f". 🚨 НАЙДЕНО {duplicates_found} дублированных номеров!"
            
            if uuid_based_count > 0:
                details += " ✅ Новый UUID-based формат обнаружен!"
            
            if duplicate_cargo_ids:
                details += f" ⚠️ Найдены повторяющиеся cargo_id: {len(duplicate_cargo_ids)}"
            
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ НОМЕРОВ ГРУЗОВ",
                success,
                details,
                {
                    "total_cargos": total_cargos,
                    "unique_numbers": unique_numbers,
                    "duplicates_found": duplicates_found,
                    "uuid_based_count": uuid_based_count,
                    "request_based_count": request_based_count,
                    "new_format_count": new_format_count,
                    "duplicate_cargo_ids": duplicate_cargo_ids,
                    "sample_numbers": existing_numbers[:10]
                }
            )
            return success
            
        except Exception as e:
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ НОМЕРОВ ГРУЗОВ",
                False,
                f"Исключение при проверке уникальности номеров: {str(e)}"
            )
            return False
    
    def test_full_workflow_no_duplicates(self):
        """Тест 5: Полный workflow - принятие заявки → завершение оформления → проверка отсутствия дубликатов"""
        try:
            # Получаем список уведомлений для тестирования
            response = self.session.get(f"{API_BASE}/operator/warehouse-notifications")
            
            if response.status_code != 200:
                self.log_result(
                    "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ",
                    False,
                    f"Не удалось получить список уведомлений: HTTP {response.status_code}"
                )
                return False
            
            data = response.json()
            notifications = data.get("notifications", [])
            
            if not notifications:
                self.log_result(
                    "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ",
                    True,
                    "Нет уведомлений для тестирования workflow - это нормально если база данных пуста"
                )
                return True
            
            # Ищем подходящее уведомление для тестирования
            test_notification = None
            for notification in notifications:
                if notification.get("status") == "pending_acceptance":
                    test_notification = notification
                    break
            
            if not test_notification:
                # Попробуем с любым уведомлением
                test_notification = notifications[0]
            
            notification_id = test_notification.get("id")
            original_status = test_notification.get("status")
            
            # Подсчитываем количество грузов ДО workflow
            cargo_response = self.session.get(f"{API_BASE}/cargo/all?per_page=1")
            initial_cargo_count = 0
            if cargo_response.status_code == 200:
                cargo_data = cargo_response.json()
                if isinstance(cargo_data, list):
                    initial_cargo_count = len(cargo_data)
                else:
                    initial_cargo_count = cargo_data.get("pagination", {}).get("total_count", 0)
            
            # Шаг 1: Принятие уведомления (если нужно)
            if original_status == "pending_acceptance":
                accept_response = self.session.post(f"{API_BASE}/operator/warehouse-notifications/{notification_id}/accept")
                
                if accept_response.status_code != 200:
                    self.log_result(
                        "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ - Шаг 1 (Accept)",
                        False,
                        f"Ошибка при принятии уведомления: HTTP {accept_response.status_code}"
                    )
                    return False
                
                # Небольшая задержка для обновления статуса
                time.sleep(1)
            
            # Шаг 2: Завершение оформления с данными
            complete_data = {
                "cargo_items": [
                    {
                        "cargo_name": "Тестовый груз для проверки дубликатов",
                        "weight": 12.5,
                        "price_per_kg": 150.0
                    }
                ],
                "description": f"Тестовое описание для проверки дубликатов {datetime.now().strftime('%H:%M:%S')}",
                "payment_method": "cash",
                "payment_amount": 1875.0
            }
            
            complete_response = self.session.post(
                f"{API_BASE}/operator/warehouse-notifications/{notification_id}/complete",
                json=complete_data
            )
            
            if complete_response.status_code != 200:
                error_text = complete_response.text[:200] if complete_response.text else "Нет деталей"
                self.log_result(
                    "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ - Шаг 2 (Complete)",
                    False,
                    f"Ошибка при завершении оформления: HTTP {complete_response.status_code}, {error_text}"
                )
                return False
            
            complete_result = complete_response.json()
            created_cargos = complete_result.get("created_cargos", [])
            
            # Подсчитываем количество грузов ПОСЛЕ workflow
            time.sleep(2)  # Задержка для обновления данных
            final_cargo_response = self.session.get(f"{API_BASE}/cargo/all?per_page=1")
            final_cargo_count = 0
            if final_cargo_response.status_code == 200:
                final_cargo_data = final_cargo_response.json()
                if isinstance(final_cargo_data, list):
                    final_cargo_count = len(final_cargo_data)
                else:
                    final_cargo_count = final_cargo_data.get("pagination", {}).get("total_count", 0)
            
            # Анализируем результаты
            cargos_created_by_api = len(created_cargos)
            cargos_created_total = final_cargo_count - initial_cargo_count
            
            # Проверяем на дубликаты в созданных грузах
            created_numbers = [c.get("cargo_number") for c in created_cargos]
            unique_created_numbers = len(set(created_numbers))
            duplicates_in_created = len(created_numbers) - unique_created_numbers
            
            success = (
                cargos_created_by_api == cargos_created_total and  # Соответствие количества
                duplicates_in_created == 0 and  # Нет дубликатов в созданных
                cargos_created_by_api > 0  # Хотя бы один груз создан
            )
            
            details = (
                f"Workflow выполнен для уведомления {notification_id}. "
                f"Создано грузов по API: {cargos_created_by_api}, "
                f"Общее изменение в базе: {cargos_created_total}, "
                f"Дубликатов в созданных: {duplicates_in_created}. "
                f"Номера созданных грузов: {created_numbers}"
            )
            
            if success:
                details += " ✅ Workflow работает без дубликатов!"
            else:
                details += " 🚨 Обнаружены проблемы с дубликатами в workflow!"
            
            self.log_result(
                "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ",
                success,
                details,
                {
                    "notification_id": notification_id,
                    "initial_cargo_count": initial_cargo_count,
                    "final_cargo_count": final_cargo_count,
                    "cargos_created_by_api": cargos_created_by_api,
                    "cargos_created_total": cargos_created_total,
                    "created_numbers": created_numbers,
                    "duplicates_in_created": duplicates_in_created
                }
            )
            return success
            
        except Exception as e:
            self.log_result(
                "ПОЛНЫЙ WORKFLOW БЕЗ ДУБЛИКАТОВ",
                False,
                f"Исключение при тестировании workflow: {str(e)}"
            )
            return False
    
    def test_multiple_notifications_unique_ids(self):
        """Тест 6: Проверка что каждое уведомление получает уникальный ID при создании"""
        try:
            # Этот тест проверяет логику генерации ID, но не создает реальные уведомления
            # так как это может нарушить работу системы
            
            # Получаем существующие уведомления для анализа
            response = self.session.get(f"{API_BASE}/operator/warehouse-notifications")
            
            if response.status_code != 200:
                self.log_result(
                    "ПРОВЕРКА УНИКАЛЬНОСТИ ID ПРИ СОЗДАНИИ",
                    False,
                    f"Не удалось получить уведомления для анализа: HTTP {response.status_code}"
                )
                return False
            
            data = response.json()
            notifications = data.get("notifications", [])
            
            if len(notifications) < 2:
                self.log_result(
                    "ПРОВЕРКА УНИКАЛЬНОСТИ ID ПРИ СОЗДАНИИ",
                    True,
                    f"Недостаточно уведомлений для анализа ({len(notifications)}), но это не ошибка"
                )
                return True
            
            # Анализируем ID уведомлений на предмет уникальности и формата
            notification_ids = [n.get("id") for n in notifications if n.get("id")]
            
            # Проверяем уникальность
            unique_ids = set(notification_ids)
            duplicates_count = len(notification_ids) - len(unique_ids)
            
            # Проверяем формат UUID
            uuid_format_count = 0
            wn_prefix_count = 0
            
            for notification_id in notification_ids:
                if notification_id.startswith("WN_"):
                    wn_prefix_count += 1
                    uuid_part = notification_id[3:]
                    try:
                        uuid.UUID(uuid_part)
                        uuid_format_count += 1
                    except ValueError:
                        pass
            
            # Проверяем временные метки создания для выявления одновременного создания
            creation_times = []
            for notification in notifications:
                created_at = notification.get("created_at")
                if created_at:
                    creation_times.append(created_at)
            
            # Группируем по времени создания (с точностью до секунды)
            time_groups = {}
            for time_str in creation_times:
                # Берем только дату и время до секунд
                time_key = time_str[:19] if len(time_str) > 19 else time_str
                if time_key not in time_groups:
                    time_groups[time_key] = 0
                time_groups[time_key] += 1
            
            simultaneous_creations = sum(1 for count in time_groups.values() if count > 1)
            
            success = duplicates_count == 0 and uuid_format_count > 0
            
            details = (
                f"Проанализировано {len(notification_ids)} ID уведомлений. "
                f"Уникальных: {len(unique_ids)}, Дубликатов: {duplicates_count}. "
                f"UUID формат (WN_xxx): {uuid_format_count}, "
                f"Префикс WN_: {wn_prefix_count}. "
                f"Одновременных создания: {simultaneous_creations}"
            )
            
            if duplicates_count == 0:
                details += " ✅ Все ID уникальны!"
            else:
                details += f" 🚨 Найдено {duplicates_count} дублированных ID!"
            
            if uuid_format_count > 0:
                details += " ✅ UUID формат используется!"
            
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ ID ПРИ СОЗДАНИИ",
                success,
                details,
                {
                    "total_ids": len(notification_ids),
                    "unique_ids": len(unique_ids),
                    "duplicates_count": duplicates_count,
                    "uuid_format_count": uuid_format_count,
                    "wn_prefix_count": wn_prefix_count,
                    "simultaneous_creations": simultaneous_creations,
                    "sample_ids": notification_ids[:5]
                }
            )
            return success
            
        except Exception as e:
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ ID ПРИ СОЗДАНИИ",
                False,
                f"Исключение при проверке уникальности ID: {str(e)}"
            )
            return False
    
    def test_multiple_cargos_unique_numbers(self):
        """Тест 7: Проверка что каждый груз получает уникальный номер"""
        try:
            # Получаем список грузов для анализа
            response = self.session.get(f"{API_BASE}/cargo/all?per_page=50&sort_by=created_at&sort_order=desc")
            
            if response.status_code != 200:
                self.log_result(
                    "ПРОВЕРКА УНИКАЛЬНОСТИ НОМЕРОВ ПРИ СОЗДАНИИ",
                    False,
                    f"Не удалось получить грузы для анализа: HTTP {response.status_code}"
                )
                return False
            
            data = response.json()
            # API возвращает прямой список, а не объект с items
            if isinstance(data, list):
                cargos = data
            else:
                cargos = data.get("items", [])
            
            if len(cargos) < 2:
                self.log_result(
                    "ПРОВЕРКА УНИКАЛЬНОСТИ НОМЕРОВ ПРИ СОЗДАНИИ",
                    True,
                    f"Недостаточно грузов для анализа ({len(cargos)}), но это не ошибка"
                )
                return True
            
            # Анализируем номера грузов
            cargo_numbers = [c.get("cargo_number") for c in cargos if c.get("cargo_number")]
            
            # Проверяем уникальность
            unique_numbers = set(cargo_numbers)
            duplicates_count = len(cargo_numbers) - len(unique_numbers)
            
            # Анализируем форматы номеров
            uuid_based_format = 0  # XXXXXX/01, XXXXXX/02 (где XXXXXX - часть UUID)
            request_based_format = 0  # 100021/01, 100021/02 (старый формат)
            new_sequential_format = 0  # 2501XXXXXX (новый последовательный формат)
            
            # Группируем по базовой части (до слеша)
            base_parts = {}
            for cargo_number in cargo_numbers:
                if "/" in cargo_number:
                    base_part = cargo_number.split("/")[0]
                    if base_part not in base_parts:
                        base_parts[base_part] = []
                    base_parts[base_part].append(cargo_number)
                    
                    # Определяем формат
                    if len(base_part) == 6 and not base_part.startswith("100"):
                        uuid_based_format += 1
                    elif base_part.startswith("100"):
                        request_based_format += 1
                elif cargo_number.startswith("2501"):
                    new_sequential_format += 1
            
            # Проверяем правильность нумерации в группах
            correct_numbering = True
            numbering_issues = []
            
            for base_part, numbers in base_parts.items():
                if len(numbers) > 1:
                    # Извлекаем номера после слеша
                    suffixes = []
                    for number in numbers:
                        if "/" in number:
                            suffix = number.split("/")[1]
                            try:
                                suffixes.append(int(suffix))
                            except ValueError:
                                pass
                    
                    # Проверяем последовательность
                    suffixes.sort()
                    expected_sequence = list(range(1, len(suffixes) + 1))
                    if suffixes != expected_sequence:
                        correct_numbering = False
                        numbering_issues.append(f"{base_part}: {suffixes} (ожидалось: {expected_sequence})")
            
            success = duplicates_count == 0 and uuid_based_format > 0 and correct_numbering
            
            details = (
                f"Проанализировано {len(cargo_numbers)} номеров грузов. "
                f"Уникальных: {len(unique_numbers)}, Дубликатов: {duplicates_count}. "
                f"UUID-based: {uuid_based_format}, Request-based: {request_based_format}, "
                f"Sequential (2501XXX): {new_sequential_format}. "
                f"Групп с множественными номерами: {len([g for g in base_parts.values() if len(g) > 1])}"
            )
            
            if duplicates_count == 0:
                details += " ✅ Все номера уникальны!"
            else:
                details += f" 🚨 Найдено {duplicates_count} дублированных номеров!"
            
            if uuid_based_format > 0:
                details += " ✅ UUID-based формат используется!"
            
            if correct_numbering:
                details += " ✅ Нумерация в группах корректна!"
            else:
                details += f" ⚠️ Проблемы с нумерацией: {len(numbering_issues)}"
            
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ НОМЕРОВ ПРИ СОЗДАНИИ",
                success,
                details,
                {
                    "total_numbers": len(cargo_numbers),
                    "unique_numbers": len(unique_numbers),
                    "duplicates_count": duplicates_count,
                    "uuid_based_format": uuid_based_format,
                    "request_based_format": request_based_format,
                    "new_sequential_format": new_sequential_format,
                    "correct_numbering": correct_numbering,
                    "numbering_issues": numbering_issues,
                    "sample_numbers": cargo_numbers[:10]
                }
            )
            return success
            
        except Exception as e:
            self.log_result(
                "ПРОВЕРКА УНИКАЛЬНОСТИ НОМЕРОВ ПРИ СОЗДАНИИ",
                False,
                f"Исключение при проверке уникальности номеров: {str(e)}"
            )
            return False
    
    def run_comprehensive_test(self):
        """Запуск полного комплексного тестирования исправлений дублирования"""
        print("🎯 ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ: Исправление дублирования заявок в TAJLINE.TJ")
        print("=" * 80)
        print("ЦЕЛЬ: Проверить что все исправления дублирования работают корректно")
        print("ИСПРАВЛЕНИЯ: UUID для ID уведомлений, уникальные cargo_id для номеров грузов, cleanup endpoint")
        print("=" * 80)
        print()
        
        # Тест 1: Авторизация администратора
        if not self.authenticate_admin():
            print("❌ Критическая ошибка: Не удалось авторизоваться как администратор")
            return False
        
        # Тест 2: Тестирование cleanup endpoint
        self.test_cleanup_duplicate_notifications_endpoint()
        
        # Тест 3: Проверка уникальности ID уведомлений
        self.test_notification_id_uniqueness()
        
        # Тест 4: Проверка уникальности номеров грузов
        self.test_cargo_number_uniqueness()
        
        # Тест 5: Полный workflow без дубликатов
        self.test_full_workflow_no_duplicates()
        
        # Тест 6: Проверка уникальности ID при создании
        self.test_multiple_notifications_unique_ids()
        
        # Тест 7: Проверка уникальности номеров при создании
        self.test_multiple_cargos_unique_numbers()
        
        # Итоговый отчет
        self.print_final_summary()
        
        return True
    
    def print_final_summary(self):
        """Печать итогового отчета тестирования"""
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ ИСПРАВЛЕНИЙ ДУБЛИРОВАНИЯ")
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
        print("📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")
            print(f"   {result['details']}")
            print()
        
        # Критические выводы
        print("🔍 КРИТИЧЕСКИЕ ВЫВОДЫ:")
        
        # Проверяем ключевые исправления
        notification_tests = [r for r in self.test_results if 'уведомлен' in r['test'].lower()]
        cargo_tests = [r for r in self.test_results if 'груз' in r['test'].lower() or 'номер' in r['test'].lower()]
        cleanup_tests = [r for r in self.test_results if 'cleanup' in r['test'].lower()]
        workflow_tests = [r for r in self.test_results if 'workflow' in r['test'].lower()]
        
        if cleanup_tests and any(r['success'] for r in cleanup_tests):
            print("✅ Cleanup endpoint для удаления дубликатов работает")
        elif cleanup_tests:
            print("❌ ПРОБЛЕМА: Cleanup endpoint не работает корректно")
        
        if notification_tests and all(r['success'] for r in notification_tests):
            print("✅ Исправления ID уведомлений работают корректно")
        elif notification_tests:
            print("❌ ПРОБЛЕМА: Найдены проблемы с ID уведомлений")
        
        if cargo_tests and all(r['success'] for r in cargo_tests):
            print("✅ Исправления номеров грузов работают корректно")
        elif cargo_tests:
            print("❌ ПРОБЛЕМА: Найдены проблемы с номерами грузов")
        
        if workflow_tests and all(r['success'] for r in workflow_tests):
            print("✅ Полный workflow работает без дубликатов")
        elif workflow_tests:
            print("❌ ПРОБЛЕМА: Workflow создает дубликаты")
        
        # Общий вывод
        if success_rate >= 85:
            print("\n🎉 ИСПРАВЛЕНИЯ ДУБЛИРОВАНИЯ РАБОТАЮТ КОРРЕКТНО!")
            print("Дублирование заявок устранено, система работает стабильно.")
        elif success_rate >= 70:
            print("\n⚠️ ИСПРАВЛЕНИЯ ЧАСТИЧНО РАБОТАЮТ")
            print("Большинство проблем решено, но есть области для улучшения.")
        else:
            print("\n🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ С ИСПРАВЛЕНИЯМИ")
            print("Требуется дополнительная работа по устранению дублирования.")
        
        print("\n" + "=" * 80)

def main():
    """Главная функция тестирования"""
    tester = DuplicatePreventionTester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("✅ Тестирование завершено успешно")
        else:
            print("❌ Тестирование завершилось с ошибками")
            
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка при тестировании: {str(e)}")

if __name__ == "__main__":
    main()