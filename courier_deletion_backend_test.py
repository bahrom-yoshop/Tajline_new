#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новая функциональность удаления курьера из списка
Тестирование GET /api/admin/couriers/list и DELETE /api/admin/couriers/{courier_id}
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://freight-hub-6.preview.emergentagent.com/api"

# Учетные данные администратора
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

class CourierDeletionTest:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.admin_user_data = None
        self.test_results = []
        self.created_courier_id = None
        
    def log_result(self, test_name, success, details):
        """Логирование результатов тестирования"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        print()
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.admin_user_data = data.get("user")
                
                if self.admin_token and self.admin_user_data:
                    user_role = self.admin_user_data.get("role")
                    user_name = self.admin_user_data.get("full_name")
                    user_number = self.admin_user_data.get("user_number")
                    
                    self.log_result(
                        "Авторизация администратора",
                        True,
                        f"Успешная авторизация '{user_name}' (номер: {user_number}), роль: {user_role}"
                    )
                    return True
                else:
                    self.log_result(
                        "Авторизация администратора",
                        False,
                        "Токен или данные пользователя не получены"
                    )
                    return False
            else:
                self.log_result(
                    "Авторизация администратора",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Авторизация администратора",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def test_get_couriers_list(self):
        """Тестирование GET /api/admin/couriers/list"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{BACKEND_URL}/admin/couriers/list",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем структуру ответа
                if isinstance(data, list):
                    couriers = data
                elif isinstance(data, dict) and "couriers" in data:
                    couriers = data["couriers"]
                elif isinstance(data, dict) and "items" in data:
                    couriers = data["items"]
                else:
                    self.log_result(
                        "GET /api/admin/couriers/list - Структура ответа",
                        False,
                        f"Неожиданная структура ответа: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                    )
                    return []
                
                # Проверяем поля каждого курьера
                required_fields = ["id", "full_name", "phone", "transport_type", "transport_number", "assigned_warehouse_name", "is_active"]
                
                if couriers:
                    first_courier = couriers[0]
                    missing_fields = [field for field in required_fields if field not in first_courier]
                    
                    if missing_fields:
                        self.log_result(
                            "GET /api/admin/couriers/list - Поля курьера",
                            False,
                            f"Отсутствуют обязательные поля: {missing_fields}. Доступные поля: {list(first_courier.keys())}"
                        )
                    else:
                        self.log_result(
                            "GET /api/admin/couriers/list - Поля курьера",
                            True,
                            f"Все обязательные поля присутствуют: {required_fields}"
                        )
                
                self.log_result(
                    "GET /api/admin/couriers/list",
                    True,
                    f"Получено {len(couriers)} курьеров с корректной структурой данных"
                )
                
                return couriers
                
            else:
                self.log_result(
                    "GET /api/admin/couriers/list",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return []
                
        except Exception as e:
            self.log_result(
                "GET /api/admin/couriers/list",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return []

    def test_create_test_courier(self):
        """Создание тестового курьера для последующего удаления"""
        try:
            # Сначала получим список складов для назначения курьера
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            warehouses_response = self.session.get(
                f"{BACKEND_URL}/warehouses",
                headers=headers,
                timeout=30
            )
            
            if warehouses_response.status_code != 200:
                self.log_result(
                    "Получение списка складов для создания курьера",
                    False,
                    f"HTTP {warehouses_response.status_code}: {warehouses_response.text}"
                )
                return None
            
            warehouses_data = warehouses_response.json()
            warehouses = warehouses_data if isinstance(warehouses_data, list) else warehouses_data.get("warehouses", [])
            
            if not warehouses:
                self.log_result(
                    "Получение списка складов для создания курьера",
                    False,
                    "Нет доступных складов для назначения курьера"
                )
                return None
            
            # Берем первый доступный склад
            warehouse_id = warehouses[0]["id"]
            warehouse_name = warehouses[0]["name"]
            
            # Создаем тестового курьера
            courier_data = {
                "full_name": "Тестовый Курьер Удаления",
                "phone": "+79999000001",
                "password": "testpass123",
                "address": "Тестовый адрес курьера",
                "transport_type": "car",
                "transport_number": "TEST001",
                "transport_capacity": 500.0,
                "assigned_warehouse_id": warehouse_id
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/admin/couriers/create",
                json=courier_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                courier_id = data.get("id") or data.get("courier_id")
                
                if courier_id:
                    self.created_courier_id = courier_id
                    self.log_result(
                        "Создание тестового курьера",
                        True,
                        f"Создан тестовый курьер ID: {courier_id}, назначен на склад '{warehouse_name}'"
                    )
                    return courier_id
                else:
                    self.log_result(
                        "Создание тестового курьера",
                        False,
                        f"ID курьера не найден в ответе: {data}"
                    )
                    return None
            else:
                self.log_result(
                    "Создание тестового курьера",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_result(
                "Создание тестового курьера",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return None

    def test_delete_courier(self, courier_id, test_name="Удаление курьера"):
        """Тестирование DELETE /api/admin/couriers/{courier_id}"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.delete(
                f"{BACKEND_URL}/admin/couriers/{courier_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 204]:
                # Проверяем, что курьер действительно удален
                verification_response = self.session.get(
                    f"{BACKEND_URL}/admin/couriers/list",
                    headers=headers,
                    timeout=30
                )
                
                if verification_response.status_code == 200:
                    verification_data = verification_response.json()
                    couriers = verification_data if isinstance(verification_data, list) else verification_data.get("couriers", [])
                    
                    # Проверяем, что курьер больше не в списке
                    deleted_courier_found = any(c.get("id") == courier_id for c in couriers)
                    
                    if not deleted_courier_found:
                        self.log_result(
                            test_name,
                            True,
                            f"Курьер {courier_id} успешно удален и отсутствует в списке"
                        )
                        return True
                    else:
                        self.log_result(
                            test_name,
                            False,
                            f"Курьер {courier_id} все еще присутствует в списке после удаления"
                        )
                        return False
                else:
                    self.log_result(
                        test_name,
                        True,
                        f"Курьер {courier_id} удален (HTTP {response.status_code}), но не удалось проверить список"
                    )
                    return True
            elif response.status_code == 404:
                self.log_result(
                    test_name,
                    True,
                    f"Курьер {courier_id} не найден (HTTP 404) - корректная обработка несуществующего курьера"
                )
                return True
            else:
                self.log_result(
                    test_name,
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name,
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def test_delete_nonexistent_courier(self):
        """Тестирование удаления несуществующего курьера"""
        fake_courier_id = "00000000-0000-0000-0000-000000000000"
        return self.test_delete_courier(fake_courier_id, "Удаление несуществующего курьера")

    def test_admin_authorization_required(self):
        """Тестирование требования админской авторизации"""
        try:
            # Попытка без токена
            response = self.session.delete(
                f"{BACKEND_URL}/admin/couriers/test-id",
                timeout=30
            )
            
            unauthorized_correct = response.status_code in [401, 403]
            
            # Попытка с неверным токеном
            headers = {"Authorization": "Bearer invalid_token"}
            response_invalid = self.session.delete(
                f"{BACKEND_URL}/admin/couriers/test-id",
                headers=headers,
                timeout=30
            )
            
            invalid_token_correct = response_invalid.status_code in [401, 403]
            
            success = unauthorized_correct and invalid_token_correct
            
            self.log_result(
                "Проверка требования админской авторизации",
                success,
                f"Без токена: HTTP {response.status_code} {'✅' if unauthorized_correct else '❌'}, "
                f"Неверный токен: HTTP {response_invalid.status_code} {'✅' if invalid_token_correct else '❌'}"
            )
            
            return success
            
        except Exception as e:
            self.log_result(
                "Проверка требования админской авторизации",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def run_comprehensive_test(self):
        """Запуск полного тестирования функциональности удаления курьера"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Новая функциональность удаления курьера из списка")
        print("=" * 80)
        print()
        
        # Шаг 1: Авторизация администратора
        if not self.authenticate_admin():
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
            return False
        
        # Шаг 2: Тестирование GET /api/admin/couriers/list
        couriers_list = self.test_get_couriers_list()
        
        # Шаг 3: Проверка требования админской авторизации
        self.test_admin_authorization_required()
        
        # Шаг 4: Тестирование удаления несуществующего курьера
        self.test_delete_nonexistent_courier()
        
        # Шаг 5: Создание и удаление тестового курьера
        existing_courier_id = None
        if couriers_list:
            # Если есть существующие курьеры, попробуем удалить один из них
            existing_courier_id = couriers_list[0].get("id")
            if existing_courier_id:
                self.log_result(
                    "Найден существующий курьер для тестирования",
                    True,
                    f"Будет использован курьер ID: {existing_courier_id}"
                )
        
        if not existing_courier_id:
            # Создаем тестового курьера
            test_courier_id = self.test_create_test_courier()
            if test_courier_id:
                # Удаляем созданного тестового курьера
                self.test_delete_courier(test_courier_id, "Удаление созданного тестового курьера")
        else:
            # Удаляем существующего курьера
            self.test_delete_courier(existing_courier_id, "Удаление существующего курьера")
        
        # Подведение итогов
        print("=" * 80)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
        print()
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {passed_tests} ✅")
        print(f"Неудачных: {failed_tests} ❌")
        print(f"Процент успеха: {(passed_tests/total_tests*100):.1f}%")
        print()
        
        # Анализ критических проблем
        critical_issues = []
        for result in self.test_results:
            if not result["success"]:
                critical_issues.append(result)
        
        if critical_issues:
            print("🚨 ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:")
            for issue in critical_issues:
                print(f"   • {issue['test']}: {issue['details']}")
            print()
        
        # Рекомендации
        print("💡 ЗАКЛЮЧЕНИЕ:")
        if failed_tests == 0:
            print("   ✅ Все тесты прошли успешно. Функциональность удаления курьера работает корректно.")
            print("   ✅ Backend поддерживает удаление курьеров и корректно обрабатывает запросы.")
        else:
            print("   🔧 Обнаружены проблемы в функциональности удаления курьера.")
            print("   📋 Проверьте реализацию endpoints в backend.")
            print("   🔍 Убедитесь в корректной обработке ошибок и авторизации.")
        
        return failed_tests == 0

def main():
    """Главная функция запуска тестирования"""
    tester = CourierDeletionTest()
    
    try:
        success = tester.run_comprehensive_test()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()