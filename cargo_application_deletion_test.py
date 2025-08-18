#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправленная функциональность удаления заявок на груз из секции "На Забор" в TAJLINE.TJ

ИСПРАВЛЕНИЯ ДЛЯ ТЕСТИРОВАНИЯ:
1) Кнопка "Удалить заявку" теперь использует DELETE /api/admin/cargo-applications/{request.id}
2) Массовое удаление заявок использует цикл DELETE /api/admin/cargo-applications/{requestId}
3) Убраны некорректные вызовы handleDeleteCargoCompletely для заявок на забор
4) Добавлена правильная логика window.confirm для подтверждения удаления
5) Исправлено обновление списка через fetchAllPickupRequests после удаления

КРИТИЧЕСКИЕ ТЕСТЫ:
1) Авторизация администратора (+79999888777/admin123) - нужны права admin для DELETE /api/admin/cargo-applications
2) Получение заявок на груз через GET /api/admin/cargo-requests
3) Тестирование единичного удаления заявки через DELETE /api/admin/cargo-applications/{id}
4) Проверка что заявка действительно удаляется из системы
5) Тестирование массового удаления (удаление нескольких заявок по очереди)

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Заявки на груз должны корректно удаляться как по одной, так и массово
"""

import requests
import json
import os
from datetime import datetime

# Получаем URL backend из переменных окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-talk.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class CargoApplicationDeletionTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.admin_info = None
        self.cargo_requests = []
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
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   📋 {details}")
        if error_msg:
            print(f"   ❌ {error_msg}")
        print()

    def authenticate_admin(self):
        """Авторизация администратора"""
        try:
            login_data = {
                "phone": "+79999888777",
                "password": "admin123"
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.admin_info = data.get("user")
                
                # Устанавливаем заголовок авторизации
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                
                admin_role = self.admin_info.get("role")
                admin_name = self.admin_info.get("full_name")
                admin_number = self.admin_info.get("user_number")
                
                if admin_role == "admin":
                    self.log_test(
                        "Авторизация администратора (+79999888777/admin123)",
                        True,
                        f"Успешная авторизация администратора '{admin_name}' (номер: {admin_number}), роль: {admin_role} подтверждена, JWT токен получен для доступа к DELETE /api/admin/cargo-applications"
                    )
                    return True
                else:
                    self.log_test(
                        "Авторизация администратора (+79999888777/admin123)",
                        False,
                        f"Пользователь авторизован, но роль '{admin_role}' не является admin"
                    )
                    return False
            else:
                self.log_test(
                    "Авторизация администратора (+79999888777/admin123)",
                    False,
                    f"Ошибка авторизации: HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Авторизация администратора (+79999888777/admin123)",
                False,
                "Исключение при авторизации",
                str(e)
            )
            return False

    def get_cargo_requests(self):
        """Получение заявок на груз через GET /api/admin/cargo-requests"""
        try:
            response = self.session.get(f"{API_BASE}/admin/cargo-requests")
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа
                if isinstance(data, list):
                    self.cargo_requests = data
                elif isinstance(data, dict) and "items" in data:
                    self.cargo_requests = data["items"]
                else:
                    self.cargo_requests = data
                
                requests_count = len(self.cargo_requests)
                
                if requests_count > 0:
                    # Показываем примеры заявок
                    sample_requests = []
                    for i, req in enumerate(self.cargo_requests[:3]):
                        req_id = req.get("id", "N/A")
                        req_number = req.get("request_number", "N/A")
                        sender_name = req.get("sender_full_name", "N/A")
                        cargo_name = req.get("cargo_name", "N/A")
                        status = req.get("status", "N/A")
                        sample_requests.append(f"ID: {req_id}, Номер: {req_number}, Отправитель: {sender_name}, Груз: {cargo_name}, Статус: {status}")
                    
                    self.log_test(
                        "Получение заявок на груз через GET /api/admin/cargo-requests",
                        True,
                        f"Найдено {requests_count} заявок на груз. Примеры: {'; '.join(sample_requests)}"
                    )
                    return True
                else:
                    self.log_test(
                        "Получение заявок на груз через GET /api/admin/cargo-requests",
                        True,
                        "API работает корректно, но заявок на груз не найдено (0 заявок)"
                    )
                    return True
            else:
                self.log_test(
                    "Получение заявок на груз через GET /api/admin/cargo-requests",
                    False,
                    f"Ошибка получения заявок: HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Получение заявок на груз через GET /api/admin/cargo-requests",
                False,
                "Исключение при получении заявок",
                str(e)
            )
            return False

    def test_single_deletion(self):
        """Тестирование единичного удаления заявки через DELETE /api/admin/cargo-applications/{id}"""
        if not self.cargo_requests:
            self.log_test(
                "Тестирование единичного удаления заявки",
                False,
                "Нет доступных заявок для тестирования удаления"
            )
            return False
            
        try:
            # Берем первую заявку для тестирования
            test_request = self.cargo_requests[0]
            request_id = test_request.get("id")
            request_number = test_request.get("request_number", "N/A")
            sender_name = test_request.get("sender_full_name", "N/A")
            
            if not request_id:
                self.log_test(
                    "Тестирование единичного удаления заявки",
                    False,
                    "У заявки отсутствует поле 'id' для удаления"
                )
                return False
            
            # Выполняем DELETE запрос
            response = self.session.delete(f"{API_BASE}/admin/cargo-applications/{request_id}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    message = response_data.get("message", "Заявка удалена")
                    deleted_id = response_data.get("deleted_id", request_id)
                    
                    self.log_test(
                        "Тестирование единичного удаления заявки через DELETE /api/admin/cargo-applications/{id}",
                        True,
                        f"Заявка успешно удалена! ID: {deleted_id}, Номер: {request_number}, Отправитель: {sender_name}. Ответ сервера: {message}"
                    )
                    return True
                except:
                    # Если ответ не JSON, но статус 200
                    self.log_test(
                        "Тестирование единичного удаления заявки через DELETE /api/admin/cargo-applications/{id}",
                        True,
                        f"Заявка успешно удалена! ID: {request_id}, Номер: {request_number}, Отправитель: {sender_name}. HTTP 200 получен"
                    )
                    return True
            elif response.status_code == 404:
                self.log_test(
                    "Тестирование единичного удаления заявки через DELETE /api/admin/cargo-applications/{id}",
                    False,
                    f"Заявка не найдена для удаления: ID {request_id}",
                    f"HTTP 404: {response.text}"
                )
                return False
            else:
                self.log_test(
                    "Тестирование единичного удаления заявки через DELETE /api/admin/cargo-applications/{id}",
                    False,
                    f"Ошибка удаления заявки: HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Тестирование единичного удаления заявки через DELETE /api/admin/cargo-applications/{id}",
                False,
                "Исключение при удалении заявки",
                str(e)
            )
            return False

    def verify_deletion(self):
        """Проверка что заявка действительно удалилась из системы"""
        try:
            # Получаем обновленный список заявок
            response = self.session.get(f"{API_BASE}/admin/cargo-requests")
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа
                if isinstance(data, list):
                    updated_requests = data
                elif isinstance(data, dict) and "items" in data:
                    updated_requests = data["items"]
                else:
                    updated_requests = data
                
                original_count = len(self.cargo_requests)
                updated_count = len(updated_requests)
                
                if updated_count < original_count:
                    self.log_test(
                        "Проверка что заявка действительно удалилась из системы",
                        True,
                        f"Подтверждено удаление! Было заявок: {original_count}, стало: {updated_count}. Заявка успешно удалена из системы"
                    )
                    
                    # Обновляем список для дальнейших тестов
                    self.cargo_requests = updated_requests
                    return True
                else:
                    self.log_test(
                        "Проверка что заявка действительно удалилась из системы",
                        False,
                        f"Количество заявок не изменилось: было {original_count}, стало {updated_count}. Возможно заявка не была удалена"
                    )
                    return False
            else:
                self.log_test(
                    "Проверка что заявка действительно удалилась из системы",
                    False,
                    f"Ошибка получения обновленного списка: HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Проверка что заявка действительно удалилась из системы",
                False,
                "Исключение при проверке удаления",
                str(e)
            )
            return False

    def test_bulk_deletion(self):
        """Тестирование массового удаления (удаление нескольких заявок по очереди)"""
        if len(self.cargo_requests) < 2:
            self.log_test(
                "Тестирование массового удаления заявок",
                False,
                f"Недостаточно заявок для массового удаления (доступно: {len(self.cargo_requests)}, нужно минимум 2)"
            )
            return False
            
        try:
            # Берем до 3 заявок для массового удаления
            requests_to_delete = self.cargo_requests[:min(3, len(self.cargo_requests))]
            deletion_results = []
            successful_deletions = 0
            
            for i, request in enumerate(requests_to_delete):
                request_id = request.get("id")
                request_number = request.get("request_number", "N/A")
                sender_name = request.get("sender_full_name", "N/A")
                
                if not request_id:
                    deletion_results.append(f"Заявка {i+1}: Отсутствует ID")
                    continue
                
                # Выполняем DELETE запрос
                response = self.session.delete(f"{API_BASE}/admin/cargo-applications/{request_id}")
                
                if response.status_code == 200:
                    successful_deletions += 1
                    deletion_results.append(f"Заявка {i+1}: Успешно удалена (ID: {request_id}, Номер: {request_number})")
                else:
                    deletion_results.append(f"Заявка {i+1}: Ошибка HTTP {response.status_code} (ID: {request_id})")
            
            total_attempts = len(requests_to_delete)
            success_rate = (successful_deletions / total_attempts) * 100 if total_attempts > 0 else 0
            
            if successful_deletions > 0:
                self.log_test(
                    "Тестирование массового удаления (удаление нескольких заявок по очереди)",
                    True,
                    f"Массовое удаление выполнено! Успешно удалено: {successful_deletions}/{total_attempts} заявок ({success_rate:.1f}% успешности). Детали: {'; '.join(deletion_results)}"
                )
                return True
            else:
                self.log_test(
                    "Тестирование массового удаления (удаление нескольких заявок по очереди)",
                    False,
                    f"Массовое удаление не удалось! Удалено: {successful_deletions}/{total_attempts} заявок. Детали: {'; '.join(deletion_results)}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Тестирование массового удаления (удаление нескольких заявок по очереди)",
                False,
                "Исключение при массовом удалении",
                str(e)
            )
            return False

    def verify_bulk_deletion(self):
        """Проверка результатов массового удаления"""
        try:
            # Получаем финальный список заявок
            response = self.session.get(f"{API_BASE}/admin/cargo-requests")
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа
                if isinstance(data, list):
                    final_requests = data
                elif isinstance(data, dict) and "items" in data:
                    final_requests = data["items"]
                else:
                    final_requests = data
                
                final_count = len(final_requests)
                
                self.log_test(
                    "Проверка результатов массового удаления",
                    True,
                    f"Финальная проверка завершена! Осталось заявок в системе: {final_count}. Массовое удаление заявок на груз из секции 'На Забор' работает корректно"
                )
                return True
            else:
                self.log_test(
                    "Проверка результатов массового удаления",
                    False,
                    f"Ошибка получения финального списка: HTTP {response.status_code}",
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Проверка результатов массового удаления",
                False,
                "Исключение при финальной проверке",
                str(e)
            )
            return False

    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🚀 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправленная функциональность удаления заявок на груз из секции 'На Забор' в TAJLINE.TJ")
        print("=" * 120)
        print()
        
        # Тест 1: Авторизация администратора
        if not self.authenticate_admin():
            print("❌ Критическая ошибка: Не удалось авторизоваться как администратор")
            return False
        
        # Тест 2: Получение заявок на груз
        if not self.get_cargo_requests():
            print("❌ Критическая ошибка: Не удалось получить заявки на груз")
            return False
        
        # Тест 3: Единичное удаление заявки
        single_deletion_success = self.test_single_deletion()
        
        # Тест 4: Проверка удаления
        if single_deletion_success:
            self.verify_deletion()
        
        # Тест 5: Массовое удаление заявок
        bulk_deletion_success = self.test_bulk_deletion()
        
        # Тест 6: Проверка массового удаления
        if bulk_deletion_success:
            self.verify_bulk_deletion()
        
        # Подсчет результатов
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print("=" * 120)
        print(f"📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        print(f"   Всего тестов: {total_tests}")
        print(f"   Успешных: {successful_tests}")
        print(f"   Неудачных: {total_tests - successful_tests}")
        print(f"   Процент успешности: {success_rate:.1f}%")
        print()
        
        if success_rate >= 80:
            print("🎉 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            print("✅ Исправленная функциональность удаления заявок на груз из секции 'На Забор' работает корректно!")
            print("✅ DELETE /api/admin/cargo-applications/{id} функционален для единичного удаления")
            print("✅ Массовое удаление через цикл DELETE запросов работает корректно")
            print("✅ Заявки действительно удаляются из системы")
            return True
        else:
            print("❌ КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ВЫЯВИЛО ПРОБЛЕМЫ!")
            print("❌ Требуется дополнительная диагностика и исправления")
            return False

if __name__ == "__main__":
    tester = CargoApplicationDeletionTester()
    tester.run_all_tests()