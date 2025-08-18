#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: API endpoint для получения грузов на размещение
Тестирование /api/operator/available-cargo-for-placement согласно review request
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

# Тестовые данные для авторизации
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

class AvailableCargoPlacementTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        self.created_cargo_ids = []  # Для очистки тестовых данных
        
    def log_test(self, test_name, success, details=""):
        """Логирование результатов тестов"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   📝 {details}")
        print()

    def authenticate_admin(self):
        """Авторизация администратора"""
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
                self.log_test(
                    "Авторизация администратора",
                    True,
                    f"Пользователь: {user_info.get('full_name', 'N/A')} (номер: {user_info.get('user_number', 'N/A')}, роль: {user_info.get('role', 'N/A')})"
                )
                return True
            else:
                self.log_test("Авторизация администратора", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Авторизация администратора", False, f"Ошибка: {str(e)}")
            return False

    def authenticate_operator(self):
        """Авторизация оператора склада"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=OPERATOR_CREDENTIALS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                
                user_info = data.get("user", {})
                self.log_test(
                    "Авторизация оператора склада",
                    True,
                    f"Пользователь: {user_info.get('full_name', 'N/A')} (номер: {user_info.get('user_number', 'N/A')}, роль: {user_info.get('role', 'N/A')})"
                )
                return True
            else:
                self.log_test("Авторизация оператора склада", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Авторизация оператора склада", False, f"Ошибка: {str(e)}")
            return False

    def get_warehouses(self):
        """Получение списка складов"""
        try:
            # Используем токен администратора
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            response = self.session.get(f"{BACKEND_URL}/warehouses", timeout=10)
            
            if response.status_code == 200:
                warehouses = response.json()
                if warehouses:
                    warehouse_info = []
                    for w in warehouses[:3]:  # Показываем первые 3 склада
                        warehouse_info.append(f"{w.get('name', 'N/A')} (ID: {w.get('id', 'N/A')})")
                    
                    self.log_test(
                        "Получение списка складов",
                        True,
                        f"Найдено {len(warehouses)} складов. Примеры: {'; '.join(warehouse_info)}"
                    )
                    return warehouses
                else:
                    self.log_test("Получение списка складов", False, "Список складов пуст")
                    return []
            else:
                self.log_test("Получение списка складов", False, f"HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.log_test("Получение списка складов", False, f"Ошибка: {str(e)}")
            return []

    def create_test_cargo_with_different_payment_methods(self, warehouse_id):
        """Создание тестовых грузов с разными способами оплаты"""
        try:
            # Переключаемся на токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            # Различные способы оплаты для тестирования
            payment_methods = [
                {
                    "payment_method": "cash",
                    "payment_amount": 1500.0,
                    "cargo_name": "Документы (наличные)",
                    "sender_name": "Иван Петров",
                    "recipient_name": "Али Рахимов"
                },
                {
                    "payment_method": "card_transfer", 
                    "payment_amount": 2000.0,
                    "cargo_name": "Электроника (карта)",
                    "sender_name": "Петр Сидоров",
                    "recipient_name": "Бахтияр Назаров"
                },
                {
                    "payment_method": "cash_on_delivery",
                    "payment_amount": None,  # При получении
                    "cargo_name": "Одежда (при получении)",
                    "sender_name": "Мария Иванова",
                    "recipient_name": "Фарида Каримова"
                },
                {
                    "payment_method": "credit",
                    "payment_amount": 3000.0,
                    "debt_due_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                    "cargo_name": "Книги (в долг)",
                    "sender_name": "Александр Смирнов",
                    "recipient_name": "Джамшед Рахимов"
                },
                {
                    "payment_method": "not_paid",
                    "payment_amount": None,
                    "cargo_name": "Подарки (не оплачено)",
                    "sender_name": "Елена Козлова",
                    "recipient_name": "Нигора Юсупова"
                }
            ]
            
            created_cargo_data = []
            
            for i, payment_data in enumerate(payment_methods):
                payload = {
                    "sender_full_name": payment_data["sender_name"],
                    "sender_phone": f"+7999123456{i}",
                    "sender_address": f"Москва, ул. Тестовая {i+1}",
                    "recipient_full_name": payment_data["recipient_name"],
                    "recipient_phone": f"+99290123456{i}",
                    "recipient_address": f"Душанбе, ул. Рудаки {i+10}",
                    "cargo_items": [
                        {
                            "cargo_name": payment_data["cargo_name"],
                            "weight": 1.0 + i * 0.5,  # Разный вес
                            "price_per_kg": 100.0 + i * 50  # Разная цена за кг
                        }
                    ],
                    "description": f"Тестовый груз для проверки способа оплаты: {payment_data['payment_method']}",
                    "route": "moscow_to_tajikistan",
                    "warehouse_id": warehouse_id,
                    "payment_method": payment_data["payment_method"],
                    "payment_amount": payment_data.get("payment_amount"),
                    "debt_due_date": payment_data.get("debt_due_date")
                }
                
                response = self.session.post(
                    f"{BACKEND_URL}/operator/cargo/direct-accept",
                    json=payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    created_cargo = data.get("created_cargo", [])
                    if created_cargo:
                        cargo_info = created_cargo[0]
                        created_cargo_data.append({
                            "cargo_id": cargo_info.get("cargo_id"),
                            "cargo_number": cargo_info.get("cargo_number"),
                            "base_request_number": data.get("base_request_number"),
                            "payment_method": payment_data["payment_method"],
                            "payment_amount": payment_data.get("payment_amount"),
                            "debt_due_date": payment_data.get("debt_due_date"),
                            "cargo_name": payment_data["cargo_name"]
                        })
                        self.created_cargo_ids.append(cargo_info.get("cargo_id"))
                else:
                    self.log_test(
                        f"Создание груза с оплатой {payment_data['payment_method']}",
                        False,
                        f"HTTP {response.status_code}: {response.text}"
                    )
            
            if created_cargo_data:
                self.log_test(
                    "Создание тестовых грузов с разными способами оплаты",
                    True,
                    f"Создано {len(created_cargo_data)} грузов с различными способами оплаты"
                )
                return created_cargo_data
            else:
                self.log_test(
                    "Создание тестовых грузов с разными способами оплаты",
                    False,
                    "Не удалось создать ни одного груза"
                )
                return []
                
        except Exception as e:
            self.log_test("Создание тестовых грузов с разными способами оплаты", False, f"Ошибка: {str(e)}")
            return []

    def create_related_cargo_with_same_base_number(self, warehouse_id):
        """Создание связанных грузов с одинаковым базовым номером"""
        try:
            # Создаем заявку с несколькими грузами (они получат одинаковый base_request_number)
            payload = {
                "sender_full_name": "Тест Связанные Грузы",
                "sender_phone": "+79991111111",
                "sender_address": "Москва, ул. Связанная 1",
                "recipient_full_name": "Получатель Связанных",
                "recipient_phone": "+992901111111",
                "recipient_address": "Душанбе, ул. Связанная 10",
                "cargo_items": [
                    {
                        "cargo_name": "Связанный груз 1",
                        "weight": 2.0,
                        "price_per_kg": 80.0
                    },
                    {
                        "cargo_name": "Связанный груз 2", 
                        "weight": 3.0,
                        "price_per_kg": 80.0
                    },
                    {
                        "cargo_name": "Связанный груз 3",
                        "weight": 1.5,
                        "price_per_kg": 80.0
                    }
                ],
                "description": "Тестовые связанные грузы для проверки группировки по базовому номеру",
                "route": "moscow_to_tajikistan",
                "warehouse_id": warehouse_id,
                "payment_method": "cash",
                "payment_amount": 520.0  # (2*80 + 3*80 + 1.5*80) = 520
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/direct-accept",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                created_cargo = data.get("created_cargo", [])
                base_request_number = data.get("base_request_number")
                
                if created_cargo and len(created_cargo) == 3:
                    related_cargo_data = []
                    for cargo in created_cargo:
                        related_cargo_data.append({
                            "cargo_id": cargo.get("cargo_id"),
                            "cargo_number": cargo.get("cargo_number"),
                            "base_request_number": base_request_number,
                            "cargo_name": cargo.get("cargo_name")
                        })
                        self.created_cargo_ids.append(cargo.get("cargo_id"))
                    
                    self.log_test(
                        "Создание связанных грузов с одинаковым базовым номером",
                        True,
                        f"Создано {len(related_cargo_data)} связанных грузов с базовым номером {base_request_number}"
                    )
                    return related_cargo_data
                else:
                    self.log_test(
                        "Создание связанных грузов с одинаковым базовым номером",
                        False,
                        f"Ожидалось 3 груза, получено {len(created_cargo)}"
                    )
            else:
                self.log_test(
                    "Создание связанных грузов с одинаковым базовым номером",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_test("Создание связанных грузов с одинаковым базовым номером", False, f"Ошибка: {str(e)}")
            
        return []

    def test_available_cargo_for_placement_endpoint(self):
        """Основное тестирование endpoint /api/operator/available-cargo-for-placement"""
        try:
            # Переключаемся на токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа с пагинацией
                required_top_level_fields = ["items", "pagination"]
                missing_top_fields = [field for field in required_top_level_fields if field not in data]
                
                if missing_top_fields:
                    self.log_test(
                        "Структура ответа API - верхний уровень",
                        False,
                        f"Отсутствуют поля: {missing_top_fields}"
                    )
                    return None
                
                items = data.get("items", [])
                pagination = data.get("pagination", {})
                
                # Проверяем структуру пагинации
                pagination_fields = ["total_count", "page", "per_page", "total_pages", "has_next", "has_prev"]
                missing_pagination_fields = [field for field in pagination_fields if field not in pagination]
                
                if missing_pagination_fields:
                    self.log_test(
                        "Структура пагинации",
                        False,
                        f"Отсутствуют поля пагинации: {missing_pagination_fields}"
                    )
                else:
                    self.log_test(
                        "Структура пагинации",
                        True,
                        f"Всего грузов: {pagination.get('total_count')}, страница: {pagination.get('page')}/{pagination.get('total_pages')}"
                    )
                
                if items:
                    self.log_test(
                        "Получение списка грузов для размещения",
                        True,
                        f"Получено {len(items)} грузов для размещения"
                    )
                    return data
                else:
                    self.log_test(
                        "Получение списка грузов для размещения",
                        True,
                        "Список грузов пуст (это нормально, если нет грузов для размещения)"
                    )
                    return data
                    
            else:
                self.log_test(
                    "Тестирование endpoint /api/operator/cargo/available-for-placement",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_test("Тестирование endpoint /api/operator/cargo/available-for-placement", False, f"Ошибка: {str(e)}")
            return None

    def validate_cargo_fields(self, cargo_data):
        """Проверка наличия всех необходимых полей в данных груза"""
        if not cargo_data or not cargo_data.get("items"):
            return False
            
        items = cargo_data.get("items", [])
        
        # Поля, которые должны присутствовать согласно review request
        required_fields = [
            "payment_method",      # cash, card_transfer, cash_on_delivery, credit, not_paid
            "payment_amount",      # сумма оплаты
            "debt_due_date",       # дата погашения долга
            "cargo_number",        # для группировки связанных грузов
            "base_request_number", # базовый номер заявки
        ]
        
        # Дополнительные важные поля
        additional_fields = [
            "declared_value",      # или total_cost - стоимость груза
            "accepting_operator",  # ФИО оператора (received_by_operator)
            "id",                  # ID груза
            "cargo_name",          # название груза
            "weight",              # вес
            "status",              # статус
            "created_at"           # дата создания
        ]
        
        field_validation_results = []
        cargo_examples = []
        
        for i, cargo in enumerate(items[:5]):  # Проверяем первые 5 грузов
            missing_required = [field for field in required_fields if field not in cargo or cargo[field] is None]
            missing_additional = [field for field in additional_fields if field not in cargo or cargo[field] is None]
            
            # Проверяем альтернативные поля
            has_cost_field = any(field in cargo and cargo[field] is not None for field in ["declared_value", "total_cost"])
            has_operator_field = any(field in cargo and cargo[field] is not None for field in ["accepting_operator", "received_by_operator"])
            
            cargo_info = {
                "cargo_number": cargo.get("cargo_number", "N/A"),
                "payment_method": cargo.get("payment_method", "N/A"),
                "payment_amount": cargo.get("payment_amount", "N/A"),
                "debt_due_date": cargo.get("debt_due_date", "N/A"),
                "base_request_number": cargo.get("base_request_number", "N/A"),
                "accepting_operator": cargo.get("accepting_operator", cargo.get("received_by_operator", "N/A")),
                "declared_value": cargo.get("declared_value", cargo.get("total_cost", "N/A")),
                "missing_required": missing_required,
                "missing_additional": missing_additional,
                "has_cost_field": has_cost_field,
                "has_operator_field": has_operator_field
            }
            
            cargo_examples.append(cargo_info)
            
            # Груз считается валидным, если у него есть все обязательные поля
            is_valid = (
                len(missing_required) == 0 and 
                has_cost_field and 
                has_operator_field
            )
            field_validation_results.append(is_valid)
        
        # Подсчитываем результаты
        total_checked = len(field_validation_results)
        valid_cargo = sum(field_validation_results)
        
        success = valid_cargo > 0  # Хотя бы один груз должен быть валидным
        
        # Формируем детальный отчет
        details_parts = [
            f"Проверено {total_checked} грузов, валидных: {valid_cargo}"
        ]
        
        # Показываем примеры грузов
        for i, cargo_info in enumerate(cargo_examples[:3]):  # Показываем первые 3
            details_parts.append(
                f"Груз {i+1}: {cargo_info['cargo_number']} - "
                f"оплата: {cargo_info['payment_method']} ({cargo_info['payment_amount']}), "
                f"оператор: {cargo_info['accepting_operator']}, "
                f"стоимость: {cargo_info['declared_value']}, "
                f"базовый номер: {cargo_info['base_request_number']}"
            )
            
            if cargo_info['missing_required']:
                details_parts.append(f"   ⚠️ Отсутствуют обязательные поля: {cargo_info['missing_required']}")
        
        self.log_test(
            "Проверка структуры данных каждого груза",
            success,
            "; ".join(details_parts)
        )
        
        return success

    def test_payment_methods_variety(self, cargo_data):
        """Проверка разнообразия способов оплаты"""
        if not cargo_data or not cargo_data.get("items"):
            return False
            
        items = cargo_data.get("items", [])
        
        # Собираем статистику по способам оплаты
        payment_methods = {}
        for cargo in items:
            method = cargo.get("payment_method", "unknown")
            if method not in payment_methods:
                payment_methods[method] = 0
            payment_methods[method] += 1
        
        # Ожидаемые способы оплаты
        expected_methods = ["cash", "card_transfer", "cash_on_delivery", "credit", "not_paid"]
        found_methods = list(payment_methods.keys())
        
        # Проверяем наличие разных способов оплаты
        variety_score = len([method for method in expected_methods if method in found_methods])
        
        details = f"Найдено способов оплаты: {len(found_methods)} из {len(expected_methods)} ожидаемых. "
        details += f"Статистика: {dict(payment_methods)}"
        
        success = variety_score >= 2  # Хотя бы 2 разных способа оплаты
        
        self.log_test(
            "Проверка разнообразия способов оплаты",
            success,
            details
        )
        
        return success

    def test_related_cargo_grouping(self, cargo_data):
        """Проверка возможности группировки связанных грузов"""
        if not cargo_data or not cargo_data.get("items"):
            return False
            
        items = cargo_data.get("items", [])
        
        # Группируем грузы по базовому номеру
        base_number_groups = {}
        for cargo in items:
            base_number = cargo.get("base_request_number")
            if base_number:
                if base_number not in base_number_groups:
                    base_number_groups[base_number] = []
                base_number_groups[base_number].append({
                    "cargo_number": cargo.get("cargo_number"),
                    "cargo_name": cargo.get("cargo_name", "N/A")
                })
        
        # Ищем группы с несколькими грузами
        multi_cargo_groups = {k: v for k, v in base_number_groups.items() if len(v) > 1}
        
        details_parts = [
            f"Всего базовых номеров: {len(base_number_groups)}, "
            f"групп с несколькими грузами: {len(multi_cargo_groups)}"
        ]
        
        # Показываем примеры групп
        for base_number, cargo_list in list(multi_cargo_groups.items())[:2]:  # Первые 2 группы
            cargo_numbers = [cargo["cargo_number"] for cargo in cargo_list]
            details_parts.append(
                f"Группа {base_number}: {len(cargo_list)} грузов ({', '.join(cargo_numbers)})"
            )
        
        success = len(multi_cargo_groups) > 0  # Есть хотя бы одна группа связанных грузов
        
        self.log_test(
            "Проверка группировки связанных грузов по базовому номеру",
            success,
            "; ".join(details_parts)
        )
        
        return success

    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        if not self.created_cargo_ids:
            return
            
        try:
            # Переключаемся на токен администратора
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            cleanup_count = 0
            
            for cargo_id in self.created_cargo_ids:
                response = self.session.delete(
                    f"{BACKEND_URL}/admin/cargo/{cargo_id}",
                    timeout=10
                )
                
                if response.status_code in [200, 204]:
                    cleanup_count += 1
            
            self.log_test(
                "Очистка тестовых данных",
                cleanup_count > 0,
                f"Удалено {cleanup_count} из {len(self.created_cargo_ids)} тестовых грузов"
            )
            
        except Exception as e:
            self.log_test("Очистка тестовых данных", False, f"Ошибка: {str(e)}")

    def run_comprehensive_test(self):
        """Запуск полного тестирования"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: API endpoint для получения грузов на размещение")
        print("=" * 80)
        print()
        
        # 1. Авторизация
        if not self.authenticate_admin():
            print("❌ Не удалось авторизоваться как администратор. Тестирование прервано.")
            return False
            
        if not self.authenticate_operator():
            print("❌ Не удалось авторизоваться как оператор. Тестирование прервано.")
            return False
        
        # 2. Получение складов
        warehouses = self.get_warehouses()
        if not warehouses:
            print("❌ Не удалось получить список складов. Тестирование прервано.")
            return False
        
        warehouse_id = warehouses[0].get("id")
        
        # 3. Создание тестовых данных
        print("🔧 Создание тестовых данных")
        print("-" * 60)
        
        # Создаем грузы с разными способами оплаты
        payment_cargo = self.create_test_cargo_with_different_payment_methods(warehouse_id)
        
        # Создаем связанные грузы
        related_cargo = self.create_related_cargo_with_same_base_number(warehouse_id)
        
        # 4. Основное тестирование endpoint
        print("🔍 Тестирование endpoint /api/operator/cargo/available-for-placement")
        print("-" * 60)
        cargo_data = self.test_available_cargo_for_placement_endpoint()
        
        if cargo_data:
            # 5. Проверка структуры данных
            print("🔍 Проверка структуры данных грузов")
            print("-" * 60)
            self.validate_cargo_fields(cargo_data)
            
            # 6. Проверка разнообразия способов оплаты
            print("🔍 Проверка способов оплаты")
            print("-" * 60)
            self.test_payment_methods_variety(cargo_data)
            
            # 7. Проверка группировки связанных грузов
            print("🔍 Проверка группировки связанных грузов")
            print("-" * 60)
            self.test_related_cargo_grouping(cargo_data)
        
        # 8. Очистка тестовых данных
        print("🧹 Очистка тестовых данных")
        print("-" * 60)
        self.cleanup_test_data()
        
        # 9. Подведение итогов
        self.print_summary()
        
        return True

    def print_summary(self):
        """Вывод итогового отчета"""
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {passed_tests} ✅")
        print(f"Неудачных: {failed_tests} ❌")
        print(f"Процент успеха: {success_rate:.1f}%")
        print()
        
        # Группировка результатов по категориям
        categories = {
            "Авторизация": [],
            "Подготовка данных": [],
            "API Endpoint": [],
            "Структура данных": [],
            "Очистка": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if "авторизация" in test_name.lower():
                categories["Авторизация"].append(result)
            elif "создание" in test_name.lower() or "склад" in test_name.lower():
                categories["Подготовка данных"].append(result)
            elif "endpoint" in test_name.lower() or "получение" in test_name.lower():
                categories["API Endpoint"].append(result)
            elif "проверка" in test_name.lower() or "структура" in test_name.lower() or "группировка" in test_name.lower():
                categories["Структура данных"].append(result)
            elif "очистка" in test_name.lower():
                categories["Очистка"].append(result)
        
        for category, tests in categories.items():
            if tests:
                passed = sum(1 for t in tests if t["success"])
                total = len(tests)
                print(f"{category}: {passed}/{total} ✅")
        
        print("\n" + "=" * 80)
        
        # Критические выводы
        if success_rate >= 90:
            print("🎉 КРИТИЧЕСКИЙ ВЫВОД: ENDPOINT РАБОТАЕТ ОТЛИЧНО!")
            print("API /api/operator/cargo/available-for-placement возвращает корректные данные")
            print("со всеми необходимыми полями для обновленной карточки груза.")
        elif success_rate >= 70:
            print("⚠️ КРИТИЧЕСКИЙ ВЫВОД: ENDPOINT РАБОТАЕТ С ПРЕДУПРЕЖДЕНИЯМИ!")
            print("Основная функциональность работает, но есть минорные проблемы с полями.")
        else:
            print("❌ КРИТИЧЕСКИЙ ВЫВОД: ОБНАРУЖЕНЫ СЕРЬЕЗНЫЕ ПРОБЛЕМЫ!")
            print("Требуется исправление критических ошибок в структуре данных.")
        
        print("=" * 80)

def main():
    """Главная функция"""
    tester = AvailableCargoPlacementTester()
    
    try:
        success = tester.run_comprehensive_test()
        if success:
            print("\n✅ Тестирование завершено успешно!")
        else:
            print("\n❌ Тестирование завершено с ошибками!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка тестирования: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()