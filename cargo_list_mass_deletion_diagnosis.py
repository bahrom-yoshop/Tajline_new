#!/usr/bin/env python3
"""
КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблема массового удаления в разделе "Список грузов" в TAJLINE.TJ

ПРОБЛЕМА:
При массовом удалении грузов из категории "Грузы" подкатегории "Список грузов" (НЕ "Размещение") 
получаются ошибки "Груз не найден" и "Ошибка при удалении".

КРИТИЧЕСКАЯ ДИАГНОСТИКА:
1) Авторизация администратора (+79999888777/admin123)
2) Анализ различий между разделами:
   - GET /api/operator/cargo/available-for-placement (для "Размещения")
   - GET /api/admin/cargo (для "Список грузов")
   - GET /api/operator/cargo (для операторского списка)
3) Определить какие грузы находятся в разделе "Список грузов"
4) Проверить какие endpoints используются для удаления из "Список грузов":
   - DELETE /api/admin/cargo/{id} (полное удаление)
   - DELETE /api/operator/cargo/{id}/remove-from-placement (из размещения)
5) Протестировать массовое удаление из "Список грузов":
   - DELETE /api/admin/cargo/bulk (если админский раздел)
   - DELETE /api/operator/cargo/bulk-remove-from-placement (если операторский)
6) Найти правильные endpoints и структуру данных для "Список грузов"

ДЕТАЛИ АНАЛИЗА:
- Сравнить структуру данных грузов в разных разделах
- Определить используются ли разные коллекции MongoDB
- Проверить права доступа для удаления из "Список грузов"
- Найти корректную логику удаления для этого раздела

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Найти и исправить проблему с массовым удалением в разделе "Список грузов"
"""

import requests
import json
import os
from datetime import datetime

# Получаем URL backend из переменных окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://qr-logistics-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class CargoListMassDeleteDiagnoser:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.admin_info = None
        self.operator_info = None
        
        # Данные из разных разделов
        self.placement_cargo = []  # Грузы из "Размещения"
        self.admin_cargo = []      # Грузы из "Список грузов" (админ)
        self.operator_cargo = []   # Грузы из операторского списка
        
        self.test_results = []
        
    def log_test(self, test_name, success, details="", error_msg=""):
        """Логирование результатов тестов"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ УСПЕХ" if success else "❌ ОШИБКА"
        print(f"{status}: {test_name}")
        if details:
            print(f"   📝 Детали: {details}")
        if error_msg:
            print(f"   ⚠️ Ошибка: {error_msg}")
        print()

    def test_admin_authorization(self):
        """Тест 1: Авторизация администратора (+79999888777/admin123)"""
        try:
            auth_data = {
                "phone": "+79999888777",
                "password": "admin123"
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=auth_data)
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.admin_info = data.get("user")
                
                admin_name = self.admin_info.get("full_name", "Unknown")
                admin_role = self.admin_info.get("role", "Unknown")
                user_number = self.admin_info.get("user_number", "Unknown")
                
                self.log_test(
                    "Авторизация администратора (+79999888777/admin123)",
                    True,
                    f"Успешная авторизация '{admin_name}' (номер: {user_number}), роль: {admin_role}, JWT токен получен"
                )
                return True
            else:
                self.log_test(
                    "Авторизация администратора (+79999888777/admin123)",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Авторизация администратора (+79999888777/admin123)",
                False,
                "",
                str(e)
            )
            return False

    def test_operator_authorization(self):
        """Тест 2: Авторизация оператора склада (+79777888999/warehouse123)"""
        try:
            auth_data = {
                "phone": "+79777888999",
                "password": "warehouse123"
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=auth_data)
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.operator_info = data.get("user")
                
                operator_name = self.operator_info.get("full_name", "Unknown")
                operator_role = self.operator_info.get("role", "Unknown")
                user_number = self.operator_info.get("user_number", "Unknown")
                
                self.log_test(
                    "Авторизация оператора склада (+79777888999/warehouse123)",
                    True,
                    f"Успешная авторизация '{operator_name}' (номер: {user_number}), роль: {operator_role}, JWT токен получен"
                )
                return True
            else:
                self.log_test(
                    "Авторизация оператора склада (+79777888999/warehouse123)",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Авторизация оператора склада (+79777888999/warehouse123)",
                False,
                "",
                str(e)
            )
            return False

    def test_analyze_placement_section(self):
        """Тест 3: Анализ раздела "Размещения" - GET /api/operator/cargo/available-for-placement"""
        try:
            # Используем токен оператора
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            response = self.session.get(f"{API_BASE}/operator/cargo/available-for-placement", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if "items" in data:
                    self.placement_cargo = data["items"]
                    cargo_count = len(self.placement_cargo)
                    
                    # Анализируем структуру данных
                    if cargo_count > 0:
                        sample_cargo = self.placement_cargo[0]
                        fields = list(sample_cargo.keys())
                        
                        # Проверяем статусы грузов
                        statuses = {}
                        processing_statuses = {}
                        for cargo in self.placement_cargo:
                            status = cargo.get("status", "unknown")
                            processing_status = cargo.get("processing_status", "unknown")
                            statuses[status] = statuses.get(status, 0) + 1
                            processing_statuses[processing_status] = processing_statuses.get(processing_status, 0) + 1
                        
                        self.log_test(
                            'Анализ раздела "Размещения" - GET /api/operator/cargo/available-for-placement',
                            True,
                            f"Найдено {cargo_count} грузов для размещения. Статусы: {statuses}. Статусы обработки: {processing_statuses}. Поля: {fields[:10]}..."
                        )
                        return True
                    else:
                        self.log_test(
                            'Анализ раздела "Размещения" - GET /api/operator/cargo/available-for-placement',
                            True,
                            "Раздел 'Размещения' пуст - нет грузов для размещения"
                        )
                        return True
                else:
                    self.log_test(
                        'Анализ раздела "Размещения" - GET /api/operator/cargo/available-for-placement',
                        False,
                        "Отсутствует поле 'items' в ответе",
                        f"Неожиданная структура ответа: {data}"
                    )
                    return False
            else:
                self.log_test(
                    'Анализ раздела "Размещения" - GET /api/operator/cargo/available-for-placement',
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                'Анализ раздела "Размещения" - GET /api/operator/cargo/available-for-placement',
                False,
                "",
                str(e)
            )
            return False

    def test_analyze_admin_cargo_list(self):
        """Тест 4: Анализ раздела "Список грузов" (админ) - GET /api/cargo/all"""
        try:
            # Используем токен администратора
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{API_BASE}/cargo/all", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем различные возможные структуры ответа
                if "items" in data:
                    self.admin_cargo = data["items"]
                elif isinstance(data, list):
                    self.admin_cargo = data
                else:
                    self.admin_cargo = [data] if data else []
                
                cargo_count = len(self.admin_cargo)
                
                # Анализируем структуру данных
                if cargo_count > 0:
                    sample_cargo = self.admin_cargo[0]
                    fields = list(sample_cargo.keys())
                    
                    # Проверяем статусы грузов
                    statuses = {}
                    processing_statuses = {}
                    for cargo in self.admin_cargo:
                        status = cargo.get("status", "unknown")
                        processing_status = cargo.get("processing_status", "unknown")
                        statuses[status] = statuses.get(status, 0) + 1
                        processing_statuses[processing_status] = processing_statuses.get(processing_status, 0) + 1
                    
                    self.log_test(
                        'Анализ раздела "Список грузов" (админ) - GET /api/cargo/all',
                        True,
                        f"Найдено {cargo_count} грузов в админском списке. Статусы: {statuses}. Статусы обработки: {processing_statuses}. Поля: {fields[:10]}..."
                    )
                    return True
                else:
                    self.log_test(
                        'Анализ раздела "Список грузов" (админ) - GET /api/cargo/all',
                        True,
                        "Админский список грузов пуст"
                    )
                    return True
            else:
                self.log_test(
                    'Анализ раздела "Список грузов" (админ) - GET /api/cargo/all',
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                'Анализ раздела "Список грузов" (админ) - GET /api/cargo/all',
                False,
                "",
                str(e)
            )
            return False

    def test_analyze_operator_cargo_list(self):
        """Тест 5: Анализ операторского списка грузов - GET /api/operator/cargo/list"""
        try:
            # Используем токен оператора
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            response = self.session.get(f"{API_BASE}/operator/cargo/list", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем различные возможные структуры ответа
                if "items" in data:
                    self.operator_cargo = data["items"]
                elif isinstance(data, list):
                    self.operator_cargo = data
                else:
                    self.operator_cargo = [data] if data else []
                
                cargo_count = len(self.operator_cargo)
                
                # Анализируем структуру данных
                if cargo_count > 0:
                    sample_cargo = self.operator_cargo[0]
                    fields = list(sample_cargo.keys())
                    
                    # Проверяем статусы грузов
                    statuses = {}
                    processing_statuses = {}
                    for cargo in self.operator_cargo:
                        status = cargo.get("status", "unknown")
                        processing_status = cargo.get("processing_status", "unknown")
                        statuses[status] = statuses.get(status, 0) + 1
                        processing_statuses[processing_status] = processing_statuses.get(processing_status, 0) + 1
                    
                    self.log_test(
                        'Анализ операторского списка грузов - GET /api/operator/cargo/list',
                        True,
                        f"Найдено {cargo_count} грузов в операторском списке. Статусы: {statuses}. Статусы обработки: {processing_statuses}. Поля: {fields[:10]}..."
                    )
                    return True
                else:
                    self.log_test(
                        'Анализ операторского списка грузов - GET /api/operator/cargo/list',
                        True,
                        "Операторский список грузов пуст"
                    )
                    return True
            else:
                self.log_test(
                    'Анализ операторского списка грузов - GET /api/operator/cargo/list',
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                'Анализ операторского списка грузов - GET /api/operator/cargo/list',
                False,
                "",
                str(e)
            )
            return False

    def test_compare_cargo_sections(self):
        """Тест 6: Сравнение данных между разделами"""
        try:
            placement_count = len(self.placement_cargo)
            admin_count = len(self.admin_cargo)
            operator_count = len(self.operator_cargo)
            
            # Анализируем пересечения по номерам грузов
            placement_numbers = set(cargo.get("cargo_number", "") for cargo in self.placement_cargo)
            admin_numbers = set(cargo.get("cargo_number", "") for cargo in self.admin_cargo)
            operator_numbers = set(cargo.get("cargo_number", "") for cargo in self.operator_cargo)
            
            # Находим пересечения и различия
            placement_admin_intersection = placement_numbers.intersection(admin_numbers)
            placement_operator_intersection = placement_numbers.intersection(operator_numbers)
            admin_operator_intersection = admin_numbers.intersection(operator_numbers)
            
            # Уникальные грузы в каждом разделе
            placement_unique = placement_numbers - admin_numbers - operator_numbers
            admin_unique = admin_numbers - placement_numbers - operator_numbers
            operator_unique = operator_numbers - placement_numbers - admin_numbers
            
            details = f"""
СРАВНЕНИЕ РАЗДЕЛОВ:
- Размещения: {placement_count} грузов
- Админский список: {admin_count} грузов  
- Операторский список: {operator_count} грузов

ПЕРЕСЕЧЕНИЯ:
- Размещения ∩ Админский: {len(placement_admin_intersection)} грузов
- Размещения ∩ Операторский: {len(placement_operator_intersection)} грузов
- Админский ∩ Операторский: {len(admin_operator_intersection)} грузов

УНИКАЛЬНЫЕ ГРУЗЫ:
- Только в Размещениях: {len(placement_unique)} грузов
- Только в Админском: {len(admin_unique)} грузов
- Только в Операторском: {len(operator_unique)} грузов
            """.strip()
            
            self.log_test(
                "Сравнение данных между разделами",
                True,
                details
            )
            
            # Определяем, какой раздел соответствует "Список грузов"
            if admin_count > 0 and admin_unique:
                self.log_test(
                    'Определение раздела "Список грузов"',
                    True,
                    f'Раздел "Список грузов" скорее всего соответствует GET /api/admin/cargo ({admin_count} грузов, {len(admin_unique)} уникальных)'
                )
            elif operator_count > 0 and operator_unique:
                self.log_test(
                    'Определение раздела "Список грузов"',
                    True,
                    f'Раздел "Список грузов" скорее всего соответствует GET /api/operator/cargo ({operator_count} грузов, {len(operator_unique)} уникальных)'
                )
            else:
                self.log_test(
                    'Определение раздела "Список грузов"',
                    False,
                    "Не удалось однозначно определить, какой API endpoint соответствует разделу 'Список грузов'",
                    "Требуется дополнительный анализ структуры данных"
                )
            
            return True
                
        except Exception as e:
            self.log_test(
                "Сравнение данных между разделами",
                False,
                "",
                str(e)
            )
            return False

    def test_admin_single_deletion(self):
        """Тест 7: Тестирование единичного удаления через админский API"""
        try:
            if not self.admin_cargo:
                self.log_test(
                    "Тестирование единичного удаления через админский API",
                    False,
                    "",
                    "Нет грузов в админском списке для тестирования"
                )
                return False
            
            # Берем первый груз для тестирования
            test_cargo = self.admin_cargo[0]
            cargo_id = test_cargo.get("id")
            cargo_number = test_cargo.get("cargo_number", "Unknown")
            
            if not cargo_id:
                self.log_test(
                    "Тестирование единичного удаления через админский API",
                    False,
                    "",
                    "Отсутствует ID груза для тестирования"
                )
                return False
            
            # Тестируем DELETE /api/admin/cargo/{id}
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.delete(f"{API_BASE}/admin/cargo/{cargo_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Тестирование единичного удаления через админский API",
                    True,
                    f"Груз {cargo_number} (ID: {cargo_id}) успешно удален через DELETE /api/admin/cargo/{{id}}. Ответ: {data}"
                )
                return True
            elif response.status_code == 404:
                self.log_test(
                    "Тестирование единичного удаления через админский API",
                    False,
                    f"Груз {cargo_number} (ID: {cargo_id}) не найден",
                    f"HTTP 404: {response.text}"
                )
                return False
            else:
                self.log_test(
                    "Тестирование единичного удаления через админский API",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Тестирование единичного удаления через админский API",
                False,
                "",
                str(e)
            )
            return False

    def test_admin_bulk_deletion(self):
        """Тест 8: Тестирование массового удаления через админский API"""
        try:
            if len(self.admin_cargo) < 2:
                self.log_test(
                    "Тестирование массового удаления через админский API",
                    False,
                    "",
                    "Недостаточно грузов в админском списке для тестирования массового удаления"
                )
                return False
            
            # Берем 2-3 груза для тестирования
            test_cargo_ids = []
            test_cargo_numbers = []
            
            for cargo in self.admin_cargo[1:4]:  # Берем следующие 2-3 груза
                cargo_id = cargo.get("id")
                cargo_number = cargo.get("cargo_number", "Unknown")
                if cargo_id:
                    test_cargo_ids.append(cargo_id)
                    test_cargo_numbers.append(cargo_number)
            
            if not test_cargo_ids:
                self.log_test(
                    "Тестирование массового удаления через админский API",
                    False,
                    "",
                    "Нет валидных ID грузов для тестирования"
                )
                return False
            
            # Тестируем различные возможные endpoints для массового удаления
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Вариант 1: DELETE /api/admin/cargo/bulk
            bulk_delete_data = {"cargo_ids": test_cargo_ids}
            response = self.session.delete(f"{API_BASE}/admin/cargo/bulk", json=bulk_delete_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Тестирование массового удаления через админский API",
                    True,
                    f"Массовое удаление успешно через DELETE /api/admin/cargo/bulk. Грузы: {test_cargo_numbers}. Ответ: {data}"
                )
                return True
            elif response.status_code == 404:
                # Пробуем другой endpoint
                # Вариант 2: POST /api/admin/cargo/bulk-delete
                response = self.session.post(f"{API_BASE}/admin/cargo/bulk-delete", json=bulk_delete_data, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(
                        "Тестирование массового удаления через админский API",
                        True,
                        f"Массовое удаление успешно через POST /api/admin/cargo/bulk-delete. Грузы: {test_cargo_numbers}. Ответ: {data}"
                    )
                    return True
                else:
                    self.log_test(
                        "Тестирование массового удаления через админский API",
                        False,
                        f"Оба endpoint'а не работают. DELETE /api/admin/cargo/bulk: 404, POST /api/admin/cargo/bulk-delete: {response.status_code}",
                        response.text
                    )
                    return False
            else:
                self.log_test(
                    "Тестирование массового удаления через админский API",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Тестирование массового удаления через админский API",
                False,
                "",
                str(e)
            )
            return False

    def test_operator_bulk_deletion_from_list(self):
        """Тест 9: Тестирование массового удаления из операторского списка"""
        try:
            if len(self.operator_cargo) < 2:
                self.log_test(
                    "Тестирование массового удаления из операторского списка",
                    False,
                    "",
                    "Недостаточно грузов в операторском списке для тестирования массового удаления"
                )
                return False
            
            # Берем 2-3 груза для тестирования
            test_cargo_ids = []
            test_cargo_numbers = []
            
            for cargo in self.operator_cargo[1:4]:  # Берем следующие 2-3 груза
                cargo_id = cargo.get("id")
                cargo_number = cargo.get("cargo_number", "Unknown")
                if cargo_id:
                    test_cargo_ids.append(cargo_id)
                    test_cargo_numbers.append(cargo_number)
            
            if not test_cargo_ids:
                self.log_test(
                    "Тестирование массового удаления из операторского списка",
                    False,
                    "",
                    "Нет валидных ID грузов для тестирования"
                )
                return False
            
            # Тестируем различные возможные endpoints для массового удаления
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            
            # Вариант 1: DELETE /api/operator/cargo/bulk (полное удаление из списка)
            bulk_delete_data = {"cargo_ids": test_cargo_ids}
            response = self.session.delete(f"{API_BASE}/operator/cargo/bulk", json=bulk_delete_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Тестирование массового удаления из операторского списка",
                    True,
                    f"Массовое удаление успешно через DELETE /api/operator/cargo/bulk. Грузы: {test_cargo_numbers}. Ответ: {data}"
                )
                return True
            elif response.status_code == 404:
                # Вариант 2: Уже известный endpoint для удаления из размещения
                response = self.session.delete(f"{API_BASE}/operator/cargo/bulk-remove-from-placement", json=bulk_delete_data, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(
                        "Тестирование массового удаления из операторского списка",
                        True,
                        f"Массовое удаление успешно через DELETE /api/operator/cargo/bulk-remove-from-placement. Грузы: {test_cargo_numbers}. Ответ: {data}"
                    )
                    return True
                else:
                    self.log_test(
                        "Тестирование массового удаления из операторского списка",
                        False,
                        f"Оба endpoint'а не работают. DELETE /api/operator/cargo/bulk: 404, DELETE /api/operator/cargo/bulk-remove-from-placement: {response.status_code}",
                        response.text
                    )
                    return False
            else:
                self.log_test(
                    "Тестирование массового удаления из операторского списка",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Тестирование массового удаления из операторского списка",
                False,
                "",
                str(e)
            )
            return False

    def test_identify_correct_endpoints(self):
        """Тест 10: Определение правильных endpoints для "Список грузов" """
        try:
            # Анализируем результаты предыдущих тестов
            admin_cargo_count = len(self.admin_cargo)
            operator_cargo_count = len(self.operator_cargo)
            placement_cargo_count = len(self.placement_cargo)
            
            # Определяем наиболее вероятный раздел для "Список грузов"
            cargo_list_section = None
            cargo_list_endpoint = None
            deletion_endpoint = None
            
            if admin_cargo_count > placement_cargo_count:
                cargo_list_section = "admin"
                cargo_list_endpoint = "GET /api/admin/cargo"
                deletion_endpoint = "DELETE /api/admin/cargo/{id} или DELETE /api/admin/cargo/bulk"
            elif operator_cargo_count > placement_cargo_count:
                cargo_list_section = "operator"
                cargo_list_endpoint = "GET /api/operator/cargo"
                deletion_endpoint = "DELETE /api/operator/cargo/{id} или DELETE /api/operator/cargo/bulk"
            else:
                cargo_list_section = "unknown"
                cargo_list_endpoint = "Не определен"
                deletion_endpoint = "Не определен"
            
            # Проверяем, какие грузы уникальны для каждого раздела
            placement_numbers = set(cargo.get("cargo_number", "") for cargo in self.placement_cargo)
            admin_numbers = set(cargo.get("cargo_number", "") for cargo in self.admin_cargo)
            operator_numbers = set(cargo.get("cargo_number", "") for cargo in self.operator_cargo)
            
            admin_unique = admin_numbers - placement_numbers
            operator_unique = operator_numbers - placement_numbers
            
            analysis_details = f"""
АНАЛИЗ РАЗДЕЛОВ ДЛЯ "СПИСОК ГРУЗОВ":

КОЛИЧЕСТВО ГРУЗОВ:
- Размещения: {placement_cargo_count} грузов
- Админский список: {admin_cargo_count} грузов
- Операторский список: {operator_cargo_count} грузов

УНИКАЛЬНЫЕ ГРУЗЫ (не в размещении):
- Админский список: {len(admin_unique)} уникальных грузов
- Операторский список: {len(operator_unique)} уникальных грузов

ВЕРОЯТНЫЙ РАЗДЕЛ "СПИСОК ГРУЗОВ":
- Раздел: {cargo_list_section}
- Endpoint для получения: {cargo_list_endpoint}
- Endpoint для удаления: {deletion_endpoint}

РЕКОМЕНДАЦИИ:
1. Если "Список грузов" = админский раздел, использовать DELETE /api/admin/cargo/{{id}} для единичного удаления
2. Если "Список грузов" = операторский раздел, использовать DELETE /api/operator/cargo/{{id}} для единичного удаления
3. Для массового удаления нужно создать соответствующий bulk endpoint
4. Проверить права доступа для удаления из соответствующего раздела
            """.strip()
            
            self.log_test(
                'Определение правильных endpoints для "Список грузов"',
                True,
                analysis_details
            )
            return True
                
        except Exception as e:
            self.log_test(
                'Определение правильных endpoints для "Список грузов"',
                False,
                "",
                str(e)
            )
            return False

    def run_all_tests(self):
        """Запуск всех тестов диагностики"""
        print("🚀 НАЧАЛО КРИТИЧЕСКОЙ ДИАГНОСТИКИ: Проблема массового удаления в разделе 'Список грузов' в TAJLINE.TJ")
        print("=" * 120)
        print()
        
        # Последовательность тестов
        tests = [
            self.test_admin_authorization,
            self.test_operator_authorization,
            self.test_analyze_placement_section,
            self.test_analyze_admin_cargo_list,
            self.test_analyze_operator_cargo_list,
            self.test_compare_cargo_sections,
            self.test_admin_single_deletion,
            self.test_admin_bulk_deletion,
            self.test_operator_bulk_deletion_from_list,
            self.test_identify_correct_endpoints
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            if test():
                passed_tests += 1
            # Небольшая пауза между тестами
            import time
            time.sleep(1)
        
        # Итоговый отчет
        print("=" * 120)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ")
        print("=" * 120)
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"Успешность диагностики: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print()
        
        if success_rate >= 80:
            print("🎉 ДИАГНОСТИКА ЗАВЕРШЕНА УСПЕШНО: Проблема с массовым удалением в 'Список грузов' диагностирована!")
            print("✅ Определены правильные API endpoints для раздела 'Список грузов'")
            print("✅ Найдены корректные методы удаления грузов")
            print("✅ Выявлены различия между разделами системы")
        elif success_rate >= 60:
            print("⚠️ ЧАСТИЧНАЯ ДИАГНОСТИКА: Большинство тестов прошло, но есть проблемы")
            print("🔧 Требуется дополнительный анализ для полного решения проблемы")
        else:
            print("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ: Диагностика не завершена")
            print("🚨 Требуется серьезная доработка API endpoints или прав доступа")
        
        print()
        print("ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:")
        print("-" * 80)
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}")
            if result["details"]:
                print(f"   📝 {result['details']}")
            if result["error"]:
                print(f"   ⚠️ {result['error']}")
        
        return success_rate >= 80

if __name__ == "__main__":
    diagnoser = CargoListMassDeleteDiagnoser()
    success = diagnoser.run_all_tests()
    
    if success:
        print("\n🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ: Проблема с массовым удалением в 'Список грузов' диагностирована!")
        print("🔧 Найдены правильные endpoints и структура данных для исправления проблемы")
    else:
        print("\n🔧 ТРЕБУЮТСЯ ДОПОЛНИТЕЛЬНЫЕ ИССЛЕДОВАНИЯ для полного решения проблемы")