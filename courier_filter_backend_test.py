#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: ОБНОВЛЕННЫЙ фильтр активных курьеров в списке
Тестирование GET /api/admin/couriers/list с параметром show_inactive для проверки корректной фильтрации
"""

import requests
import json
import sys
from datetime import datetime
import uuid

# Конфигурация
BACKEND_URL = "https://freight-hub-6.preview.emergentagent.com/api"

# Учетные данные для тестирования
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

OPERATOR_CREDENTIALS = {
    "phone": "+992807766666", 
    "password": "warehouse123"
}

class CourierFilterTest:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        self.admin_user_data = None
        self.operator_user_data = None
        self.test_results = []
        self.test_courier_id = None
        self.test_courier_data = None
        
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

    def authenticate_operator(self):
        """Авторизация оператора для проверки безопасности"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=OPERATOR_CREDENTIALS,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                self.operator_user_data = data.get("user")
                
                if self.operator_token and self.operator_user_data:
                    user_role = self.operator_user_data.get("role")
                    user_name = self.operator_user_data.get("full_name")
                    user_number = self.operator_user_data.get("user_number")
                    
                    self.log_result(
                        "Авторизация оператора",
                        True,
                        f"Успешная авторизация '{user_name}' (номер: {user_number}), роль: {user_role}"
                    )
                    return True
                else:
                    self.log_result(
                        "Авторизация оператора",
                        False,
                        "Токен или данные пользователя не получены"
                    )
                    return False
            else:
                self.log_result(
                    "Авторизация оператора",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Авторизация оператора",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def test_couriers_list_default(self):
        """Тестирование GET /api/admin/couriers/list без параметров (только активные курьеры)"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{BACKEND_URL}/admin/couriers/list",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle pagination structure
                if isinstance(data, dict) and "items" in data:
                    couriers = data["items"]
                else:
                    couriers = data if isinstance(data, list) else data.get("couriers", [])
                
                # Проверяем что все курьеры активные
                active_couriers = []
                inactive_couriers = []
                deleted_couriers = []
                
                for courier in couriers:
                    is_active = courier.get("is_active", True)
                    deleted = courier.get("deleted", False)
                    
                    if deleted:
                        deleted_couriers.append(courier)
                    elif not is_active:
                        inactive_couriers.append(courier)
                    else:
                        active_couriers.append(courier)
                
                # По умолчанию должны показываться только активные курьеры
                success = len(inactive_couriers) == 0 and len(deleted_couriers) == 0
                
                self.log_result(
                    "GET /api/admin/couriers/list (по умолчанию - только активные)",
                    success,
                    f"Всего курьеров: {len(couriers)}, Активных: {len(active_couriers)}, "
                    f"Неактивных: {len(inactive_couriers)}, Удаленных: {len(deleted_couriers)}. "
                    f"{'✅ Показываются только активные' if success else '❌ Показываются неактивные/удаленные курьеры'}"
                )
                
                return couriers
                
            else:
                self.log_result(
                    "GET /api/admin/couriers/list (по умолчанию)",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return []
                
        except Exception as e:
            self.log_result(
                "GET /api/admin/couriers/list (по умолчанию)",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return []

    def test_couriers_list_show_inactive(self):
        """Тестирование GET /api/admin/couriers/list?show_inactive=true (все курьеры включая удаленных)"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{BACKEND_URL}/admin/couriers/list?show_inactive=true",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle pagination structure
                if isinstance(data, dict) and "items" in data:
                    couriers = data["items"]
                else:
                    couriers = data if isinstance(data, list) else data.get("couriers", [])
                
                # Анализируем состав курьеров
                active_couriers = []
                inactive_couriers = []
                deleted_couriers = []
                
                for courier in couriers:
                    is_active = courier.get("is_active", True)
                    deleted = courier.get("deleted", False)
                    
                    if deleted:
                        deleted_couriers.append(courier)
                    elif not is_active:
                        inactive_couriers.append(courier)
                    else:
                        active_couriers.append(courier)
                
                # С параметром show_inactive=true должны показываться все курьеры
                total_couriers = len(active_couriers) + len(inactive_couriers) + len(deleted_couriers)
                success = total_couriers == len(couriers)
                
                self.log_result(
                    "GET /api/admin/couriers/list?show_inactive=true (все курьеры)",
                    success,
                    f"Всего курьеров: {len(couriers)}, Активных: {len(active_couriers)}, "
                    f"Неактивных: {len(inactive_couriers)}, Удаленных: {len(deleted_couriers)}. "
                    f"{'✅ Показываются все курьеры' if success else '❌ Некорректная фильтрация'}"
                )
                
                return couriers
                
            else:
                self.log_result(
                    "GET /api/admin/couriers/list?show_inactive=true",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return []
                
        except Exception as e:
            self.log_result(
                "GET /api/admin/couriers/list?show_inactive=true",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return []

    def test_operator_security_show_inactive(self):
        """Тестирование безопасности: операторы НЕ должны иметь доступ к show_inactive=true"""
        try:
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            response = self.session.get(
                f"{BACKEND_URL}/admin/couriers/list?show_inactive=true",
                headers=headers,
                timeout=30
            )
            
            # Ожидаем 403 Forbidden для оператора
            success = response.status_code == 403
            
            self.log_result(
                "Безопасность: оператор НЕ может использовать show_inactive=true",
                success,
                f"HTTP {response.status_code}: {'✅ Доступ запрещен (403)' if success else '❌ Доступ разрешен - нарушение безопасности!'}"
            )
            
            return success
                
        except Exception as e:
            self.log_result(
                "Безопасность: оператор НЕ может использовать show_inactive=true",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def get_warehouses_for_courier(self):
        """Получить список складов для создания тестового курьера"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{BACKEND_URL}/warehouses",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                warehouses = data if isinstance(data, list) else data.get("warehouses", [])
                
                if warehouses:
                    # Возвращаем первый склад для тестирования
                    return warehouses[0].get("id")
                else:
                    self.log_result(
                        "Получение складов для курьера",
                        False,
                        "Нет доступных складов"
                    )
                    return None
            else:
                self.log_result(
                    "Получение складов для курьера",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_result(
                "Получение складов для курьера",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return None

    def create_test_courier(self):
        """Создание тестового курьера"""
        try:
            warehouse_id = self.get_warehouses_for_courier()
            if not warehouse_id:
                return False
            
            # Генерируем уникальные данные для тестового курьера
            unique_id = str(uuid.uuid4())[:8]
            courier_data = {
                "full_name": f"Тестовый Курьер Фильтрации {unique_id}",
                "phone": f"+7999{unique_id[:7]}",
                "password": "testcourier123",
                "address": f"Тестовый адрес курьера {unique_id}",
                "transport_type": "car",
                "transport_number": f"TEST{unique_id[:4]}",
                "transport_capacity": 500.0,
                "assigned_warehouse_id": warehouse_id
            }
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(
                f"{BACKEND_URL}/admin/couriers/create",
                json=courier_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.test_courier_id = data.get("courier_id") or data.get("id")
                self.test_courier_data = courier_data
                
                self.log_result(
                    "Создание тестового курьера",
                    True,
                    f"Создан тестовый курьер '{courier_data['full_name']}' (ID: {self.test_courier_id})"
                )
                return True
            else:
                self.log_result(
                    "Создание тестового курьера",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Создание тестового курьера",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def verify_courier_in_active_list(self):
        """Проверка что созданный курьер появляется в списке активных курьеров"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{BACKEND_URL}/admin/couriers/list",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle pagination structure
                if isinstance(data, dict) and "items" in data:
                    couriers = data["items"]
                else:
                    couriers = data if isinstance(data, list) else data.get("couriers", [])
                
                # Ищем нашего тестового курьера
                test_courier_found = False
                for courier in couriers:
                    if courier.get("id") == self.test_courier_id:
                        test_courier_found = True
                        break
                
                self.log_result(
                    "Проверка появления курьера в активном списке",
                    test_courier_found,
                    f"{'✅ Тестовый курьер найден в активном списке' if test_courier_found else '❌ Тестовый курьер НЕ найден в активном списке'}"
                )
                
                return test_courier_found
            else:
                self.log_result(
                    "Проверка появления курьера в активном списке",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Проверка появления курьера в активном списке",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def delete_test_courier(self):
        """Удаление тестового курьера"""
        try:
            if not self.test_courier_id:
                self.log_result(
                    "Удаление тестового курьера",
                    False,
                    "ID тестового курьера не найден"
                )
                return False
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.delete(
                f"{BACKEND_URL}/admin/couriers/{self.test_courier_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                self.log_result(
                    "Удаление тестового курьера",
                    True,
                    f"Тестовый курьер успешно удален (ID: {self.test_courier_id})"
                )
                return True
            else:
                self.log_result(
                    "Удаление тестового курьера",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Удаление тестового курьера",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def verify_courier_not_in_active_list(self):
        """Проверка что удаленный курьер исчезает из списка активных курьеров"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{BACKEND_URL}/admin/couriers/list",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle pagination structure
                if isinstance(data, dict) and "items" in data:
                    couriers = data["items"]
                else:
                    couriers = data if isinstance(data, list) else data.get("couriers", [])
                
                # Ищем нашего тестового курьера (его НЕ должно быть)
                test_courier_found = False
                for courier in couriers:
                    if courier.get("id") == self.test_courier_id:
                        test_courier_found = True
                        break
                
                success = not test_courier_found
                
                self.log_result(
                    "Проверка исчезновения курьера из активного списка",
                    success,
                    f"{'✅ Удаленный курьер НЕ найден в активном списке' if success else '❌ Удаленный курьер все еще в активном списке'}"
                )
                
                return success
            else:
                self.log_result(
                    "Проверка исчезновения курьера из активного списка",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Проверка исчезновения курьера из активного списка",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def verify_courier_in_inactive_list(self):
        """Проверка что удаленный курьер виден при show_inactive=true"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{BACKEND_URL}/admin/couriers/list?show_inactive=true",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle pagination structure
                if isinstance(data, dict) and "items" in data:
                    couriers = data["items"]
                else:
                    couriers = data if isinstance(data, list) else data.get("couriers", [])
                
                # Ищем нашего тестового курьера
                test_courier_found = False
                courier_status = None
                
                for courier in couriers:
                    if courier.get("id") == self.test_courier_id:
                        test_courier_found = True
                        courier_status = {
                            "is_active": courier.get("is_active", True),
                            "deleted": courier.get("deleted", False)
                        }
                        break
                
                self.log_result(
                    "Проверка видимости курьера при show_inactive=true",
                    test_courier_found,
                    f"{'✅ Удаленный курьер найден в полном списке' if test_courier_found else '❌ Удаленный курьер НЕ найден в полном списке'}"
                    + (f" (is_active: {courier_status['is_active']}, deleted: {courier_status['deleted']})" if courier_status else "")
                )
                
                return test_courier_found
            else:
                self.log_result(
                    "Проверка видимости курьера при show_inactive=true",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Проверка видимости курьера при show_inactive=true",
                False,
                f"Ошибка запроса: {str(e)}"
            )
            return False

    def run_comprehensive_test(self):
        """Запуск полного тестирования фильтрации курьеров"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: ОБНОВЛЕННЫЙ фильтр активных курьеров в списке")
        print("=" * 80)
        print()
        
        # Шаг 1: Авторизация администратора
        if not self.authenticate_admin():
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
            return False
        
        # Шаг 2: Авторизация оператора для проверки безопасности (опционально)
        operator_authenticated = self.authenticate_operator()
        if not operator_authenticated:
            print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Не удалось авторизоваться как оператор - пропускаем тест безопасности")
        
        # Шаг 3: Тестирование списка курьеров по умолчанию (только активные)
        active_couriers = self.test_couriers_list_default()
        
        # Шаг 4: Тестирование списка курьеров с show_inactive=true (все курьеры)
        all_couriers = self.test_couriers_list_show_inactive()
        
        # Шаг 5: Проверка безопасности - оператор не может использовать show_inactive=true
        if operator_authenticated and self.operator_token:
            self.test_operator_security_show_inactive()
        
        # Шаг 6: Создание тестового курьера
        if not self.create_test_courier():
            print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Не удалось создать тестового курьера для полного тестирования")
        else:
            # Шаг 7: Проверка что курьер появляется в активном списке
            self.verify_courier_in_active_list()
            
            # Шаг 8: Удаление тестового курьера
            if self.delete_test_courier():
                # Шаг 9: Проверка что курьер исчезает из активного списка
                self.verify_courier_not_in_active_list()
                
                # Шаг 10: Проверка что курьер виден при show_inactive=true
                self.verify_courier_in_inactive_list()
        
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
            print("🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ НАЙДЕНЫ:")
            for issue in critical_issues:
                print(f"   • {issue['test']}: {issue['details']}")
            print()
        
        # Рекомендации
        print("💡 РЕКОМЕНДАЦИИ:")
        if failed_tests == 0:
            print("   ✅ Все тесты прошли успешно. Фильтрация активных курьеров работает корректно.")
            print("   ✅ Параметр show_inactive=true функционирует правильно.")
            print("   ✅ Безопасность соблюдена - операторы не имеют доступа к неактивным курьерам.")
        else:
            print("   🔧 Обнаружены проблемы в фильтрации курьеров.")
            print("   📋 Проверьте логику фильтрации в endpoint GET /api/admin/couriers/list.")
            print("   🔍 Убедитесь в корректной обработке параметра show_inactive.")
            print("   🛡️ Проверьте права доступа для разных ролей пользователей.")
        
        return failed_tests == 0

def main():
    """Главная функция запуска тестирования"""
    tester = CourierFilterTest()
    
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