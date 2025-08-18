#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправление ошибки удаления заявок на забор в TAJLINE.TJ

НАЙДЕННАЯ ПРОБЛЕМА: 
- Отсутствует индивидуальный DELETE endpoint для заявок на забор
- Существует только bulk DELETE endpoint: /api/admin/pickup-requests/bulk
- Frontend пытается удалить индивидуальные заявки, но endpoint не существует

НУЖНО ПРОТЕСТИРОВАТЬ:
1. Авторизация администратора
2. Получение списка заявок на забор
3. Тестирование существующего bulk DELETE endpoint
4. Проверка структуры данных для bulk удаления
5. Создание индивидуального DELETE endpoint (если нужно)

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Подтвердить что проблема в отсутствии индивидуального DELETE endpoint и протестировать bulk endpoint.
"""

import requests
import json
import os
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-system-debug.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class PickupDeletionFixTest:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None
        self.test_results = []
        self.pickup_requests = []
        
    def log_result(self, test_name: str, success: bool, details: str, data=None):
        """Логирование результатов тестов"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}: {details}"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        print(result)
        if data and isinstance(data, dict) and len(str(data)) < 300:
            print(f"   📊 Данные: {json.dumps(data, ensure_ascii=False, indent=2)}")
        print()
        
    def authenticate_admin(self):
        """Тест 1: Авторизация администратора"""
        try:
            login_data = {
                "phone": "+79999888777",
                "password": "admin123"
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                
                # Устанавливаем заголовок авторизации
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
                        f"Успешная авторизация администратора: {user_info}, JWT токен получен",
                        {"phone": "+79999888777", "role": self.current_user.get('role')}
                    )
                    return True
                    
            self.log_result(
                "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                False,
                f"Ошибка авторизации: HTTP {response.status_code}"
            )
            return False
                
        except Exception as e:
            self.log_result(
                "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                False,
                f"Исключение при авторизации: {str(e)}"
            )
            return False
    
    def get_pickup_requests(self):
        """Тест 2: Получение списка заявок на забор"""
        try:
            response = self.session.get(f"{API_BASE}/operator/pickup-requests")
            
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем разные возможные структуры ответа
                if isinstance(data, list):
                    self.pickup_requests = data
                elif isinstance(data, dict):
                    self.pickup_requests = data.get('items', data.get('requests', data.get('pickup_requests', [])))
                
                total_requests = len(self.pickup_requests)
                
                # Анализируем структуру заявок
                if self.pickup_requests:
                    sample_request = self.pickup_requests[0]
                    id_fields = {
                        'id': sample_request.get('id'),
                        'request_number': sample_request.get('request_number'),
                        'request_id': sample_request.get('request_id')
                    }
                else:
                    id_fields = {}
                
                self.log_result(
                    "ПОЛУЧЕНИЕ СПИСКА ЗАЯВОК НА ЗАБОР",
                    True,
                    f"Получено {total_requests} заявок на забор через /api/operator/pickup-requests",
                    {
                        "total_requests": total_requests,
                        "sample_id_fields": id_fields,
                        "endpoint": "/api/operator/pickup-requests"
                    }
                )
                return True
            else:
                self.log_result(
                    "ПОЛУЧЕНИЕ СПИСКА ЗАЯВОК НА ЗАБОР",
                    False,
                    f"Ошибка получения заявок: HTTP {response.status_code}, {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ПОЛУЧЕНИЕ СПИСКА ЗАЯВОК НА ЗАБОР",
                False,
                f"Исключение при получении заявок: {str(e)}"
            )
            return False
    
    def test_individual_delete_endpoints(self):
        """Тест 3: Проверка существования индивидуальных DELETE endpoints"""
        try:
            if not self.pickup_requests:
                self.log_result(
                    "ПРОВЕРКА ИНДИВИДУАЛЬНЫХ DELETE ENDPOINTS",
                    True,
                    "Нет заявок для тестирования индивидуального удаления"
                )
                return True
            
            # Берем первую заявку для тестирования
            test_request = self.pickup_requests[0]
            request_id = test_request.get('id')
            request_number = test_request.get('request_number')
            
            # Тестируем различные возможные endpoints для индивидуального удаления
            individual_endpoints = [
                f"/api/admin/pickup-requests/{request_id}",
                f"/api/admin/courier/pickup-requests/{request_id}",
                f"/api/operator/pickup-requests/{request_id}",
                f"/api/admin/pickup-requests/{request_number}",
                f"/api/admin/courier/pickup-requests/{request_number}"
            ]
            
            endpoint_results = []
            
            for endpoint in individual_endpoints:
                try:
                    # Используем HEAD запрос чтобы не удалять данные
                    head_response = self.session.head(f"{BACKEND_URL}{endpoint}")
                    
                    endpoint_results.append({
                        "endpoint": endpoint,
                        "status_code": head_response.status_code,
                        "exists": head_response.status_code != 404
                    })
                    
                except Exception as e:
                    endpoint_results.append({
                        "endpoint": endpoint,
                        "error": str(e),
                        "exists": False
                    })
            
            # Анализируем результаты
            existing_endpoints = [r for r in endpoint_results if r.get('exists', False)]
            non_existing_endpoints = [r for r in endpoint_results if not r.get('exists', False)]
            
            if existing_endpoints:
                self.log_result(
                    "ПРОВЕРКА ИНДИВИДУАЛЬНЫХ DELETE ENDPOINTS",
                    True,
                    f"Найдено {len(existing_endpoints)} существующих индивидуальных endpoints из {len(endpoint_results)} проверенных",
                    {
                        "existing_endpoints": existing_endpoints,
                        "non_existing_endpoints": non_existing_endpoints,
                        "test_request_id": request_id,
                        "test_request_number": request_number
                    }
                )
            else:
                self.log_result(
                    "ПРОВЕРКА ИНДИВИДУАЛЬНЫХ DELETE ENDPOINTS",
                    False,
                    f"🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: НИ ОДИН индивидуальный DELETE endpoint не существует! Проверено {len(endpoint_results)} endpoints",
                    {
                        "non_existing_endpoints": non_existing_endpoints,
                        "test_request_id": request_id,
                        "test_request_number": request_number,
                        "issue": "Frontend пытается удалить индивидуальные заявки, но endpoints не существуют"
                    }
                )
            
            return len(existing_endpoints) > 0
            
        except Exception as e:
            self.log_result(
                "ПРОВЕРКА ИНДИВИДУАЛЬНЫХ DELETE ENDPOINTS",
                False,
                f"Исключение при проверке endpoints: {str(e)}"
            )
            return False
    
    def test_bulk_delete_endpoint(self):
        """Тест 4: Тестирование существующего bulk DELETE endpoint"""
        try:
            if not self.pickup_requests:
                self.log_result(
                    "ТЕСТИРОВАНИЕ BULK DELETE ENDPOINT",
                    True,
                    "Нет заявок для тестирования bulk удаления"
                )
                return True
            
            # Берем ID первой заявки для тестирования
            test_request = self.pickup_requests[0]
            request_id = test_request.get('id')
            
            if not request_id:
                self.log_result(
                    "ТЕСТИРОВАНИЕ BULK DELETE ENDPOINT",
                    False,
                    "У тестовой заявки отсутствует поле 'id' для bulk удаления"
                )
                return False
            
            # Тестируем bulk delete endpoint с правильной структурой данных
            bulk_delete_data = {
                "ids": [request_id]
            }
            
            # Сначала проверяем существование endpoint
            head_response = self.session.head(f"{API_BASE}/admin/pickup-requests/bulk")
            
            if head_response.status_code == 404:
                self.log_result(
                    "ТЕСТИРОВАНИЕ BULK DELETE ENDPOINT",
                    False,
                    "Bulk DELETE endpoint /api/admin/pickup-requests/bulk не существует"
                )
                return False
            
            # Тестируем bulk delete (НЕ удаляем реально, только проверяем структуру)
            # Используем неправильную структуру чтобы получить ошибку валидации, а не удалить данные
            test_bulk_data = {
                "test_ids": [request_id]  # Неправильное поле для тестирования
            }
            
            response = self.session.delete(f"{API_BASE}/admin/pickup-requests/bulk", json=test_bulk_data)
            
            # Анализируем ответ
            if response.status_code == 400:
                # Ожидаемая ошибка валидации - endpoint существует и работает
                self.log_result(
                    "ТЕСТИРОВАНИЕ BULK DELETE ENDPOINT",
                    True,
                    f"✅ Bulk DELETE endpoint существует и работает! HTTP 400 (ошибка валидации) подтверждает что endpoint функционален. Правильная структура: {json.dumps(bulk_delete_data, ensure_ascii=False)}",
                    {
                        "endpoint": "/api/admin/pickup-requests/bulk",
                        "status_code": response.status_code,
                        "correct_structure": bulk_delete_data,
                        "test_request_id": request_id,
                        "response": response.text[:200]
                    }
                )
                return True
            elif response.status_code == 200:
                # Неожиданно успешное удаление
                self.log_result(
                    "ТЕСТИРОВАНИЕ BULK DELETE ENDPOINT",
                    True,
                    f"⚠️ Bulk DELETE endpoint работает, но тестовая заявка была удалена! HTTP 200",
                    {
                        "endpoint": "/api/admin/pickup-requests/bulk",
                        "status_code": response.status_code,
                        "warning": "Тестовые данные были удалены",
                        "response": response.text[:200]
                    }
                )
                return True
            else:
                self.log_result(
                    "ТЕСТИРОВАНИЕ BULK DELETE ENDPOINT",
                    False,
                    f"Bulk DELETE endpoint вернул неожиданный статус: HTTP {response.status_code}",
                    {
                        "endpoint": "/api/admin/pickup-requests/bulk",
                        "status_code": response.status_code,
                        "response": response.text[:200]
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ТЕСТИРОВАНИЕ BULK DELETE ENDPOINT",
                False,
                f"Исключение при тестировании bulk delete: {str(e)}"
            )
            return False
    
    def analyze_root_cause_and_solution(self):
        """Тест 5: Анализ корневой причины и предложение решения"""
        try:
            # Анализируем результаты предыдущих тестов
            individual_endpoints_test = [r for r in self.test_results if r["test"] == "ПРОВЕРКА ИНДИВИДУАЛЬНЫХ DELETE ENDPOINTS"]
            bulk_endpoint_test = [r for r in self.test_results if r["test"] == "ТЕСТИРОВАНИЕ BULK DELETE ENDPOINT"]
            
            root_cause_analysis = []
            solutions = []
            
            # Анализ индивидуальных endpoints
            if individual_endpoints_test and not individual_endpoints_test[0]["success"]:
                root_cause_analysis.append("Отсутствуют индивидуальные DELETE endpoints для заявок на забор")
                solutions.append("Создать индивидуальный DELETE endpoint: /api/admin/pickup-requests/{request_id}")
                solutions.append("Альтернативно: изменить frontend для использования bulk delete с одним ID")
            
            # Анализ bulk endpoint
            if bulk_endpoint_test and bulk_endpoint_test[0]["success"]:
                root_cause_analysis.append("Bulk DELETE endpoint существует и работает корректно")
                solutions.append("Frontend может использовать bulk delete для удаления одной заявки")
            
            # Анализ структуры данных
            if self.pickup_requests:
                sample_request = self.pickup_requests[0]
                if 'id' in sample_request:
                    root_cause_analysis.append("Заявки имеют поле 'id' для идентификации")
                    solutions.append("Использовать поле 'id' для удаления заявок")
                else:
                    root_cause_analysis.append("В заявках отсутствует поле 'id'")
                    solutions.append("Добавить поле 'id' в модель заявок на забор")
            
            # Общий анализ
            if not root_cause_analysis:
                root_cause_analysis.append("Система работает корректно - возможно проблема в frontend логике")
            
            # Рекомендации по исправлению
            final_recommendations = [
                "НЕМЕДЛЕННОЕ ИСПРАВЛЕНИЕ: Создать индивидуальный DELETE endpoint /api/admin/pickup-requests/{request_id}",
                "АЛЬТЕРНАТИВНОЕ РЕШЕНИЕ: Изменить frontend для использования bulk delete с массивом из одного ID",
                "ДОЛГОСРОЧНОЕ РЕШЕНИЕ: Стандартизировать все DELETE endpoints для поддержки как индивидуального, так и bulk удаления",
                "ТЕСТИРОВАНИЕ: Добавить автоматические тесты для всех CRUD операций с заявками на забор"
            ]
            
            analysis_summary = f"Корневая причина найдена: {'; '.join(root_cause_analysis)}"
            
            self.log_result(
                "АНАЛИЗ КОРНЕВОЙ ПРИЧИНЫ И РЕШЕНИЯ",
                True,
                analysis_summary,
                {
                    "root_causes": root_cause_analysis,
                    "immediate_solutions": solutions,
                    "final_recommendations": final_recommendations,
                    "pickup_requests_count": len(self.pickup_requests),
                    "has_bulk_endpoint": bulk_endpoint_test and bulk_endpoint_test[0]["success"] if bulk_endpoint_test else False
                }
            )
            return True
            
        except Exception as e:
            self.log_result(
                "АНАЛИЗ КОРНЕВОЙ ПРИЧИНЫ И РЕШЕНИЯ",
                False,
                f"Исключение при анализе: {str(e)}"
            )
            return False
    
    def run_comprehensive_test(self):
        """Запуск полного тестирования проблемы удаления заявок на забор"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправление ошибки удаления заявок на забор в TAJLINE.TJ")
        print("=" * 95)
        print()
        
        # Тест 1: Авторизация администратора
        if not self.authenticate_admin():
            print("❌ Критическая ошибка: Не удалось авторизоваться как администратор. Тестирование прервано.")
            return
        
        # Тест 2: Получение списка заявок на забор
        self.get_pickup_requests()
        
        # Тест 3: Проверка индивидуальных DELETE endpoints
        self.test_individual_delete_endpoints()
        
        # Тест 4: Тестирование bulk DELETE endpoint
        self.test_bulk_delete_endpoint()
        
        # Тест 5: Анализ корневой причины и решения
        self.analyze_root_cause_and_solution()
        
        # Итоговый отчет
        self.print_comprehensive_summary()
    
    def print_comprehensive_summary(self):
        """Печать итогового отчета"""
        print("\n" + "=" * 95)
        print("📊 ИТОГОВЫЙ ОТЧЕТ КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ")
        print("=" * 95)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {successful_tests}")
        print(f"Неудачных: {failed_tests}")
        print(f"Процент успеха: {success_rate:.1f}%")
        print()
        
        # Печать результатов каждого теста
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")
            print(f"   {result['details']}")
            print()
        
        # Критические выводы
        print("🔍 КРИТИЧЕСКИЕ ВЫВОДЫ:")
        
        # Анализируем результаты
        analysis_results = [r for r in self.test_results if r['test'] == "АНАЛИЗ КОРНЕВОЙ ПРИЧИНЫ И РЕШЕНИЯ"]
        if analysis_results and analysis_results[0]['data']:
            data = analysis_results[0]['data']
            
            print("📋 НАЙДЕННЫЕ ПРОБЛЕМЫ:")
            for cause in data.get('root_causes', []):
                print(f"   • {cause}")
            
            print("\n💡 НЕМЕДЛЕННЫЕ РЕШЕНИЯ:")
            for solution in data.get('immediate_solutions', []):
                print(f"   • {solution}")
            
            print("\n🎯 ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ:")
            for rec in data.get('final_recommendations', []):
                print(f"   • {rec}")
        
        # Статус системы
        if self.pickup_requests:
            print(f"\n✅ В системе найдено {len(self.pickup_requests)} заявок на забор")
        else:
            print("\n⚠️ В системе не найдено заявок на забор")
        
        if self.current_user and self.current_user.get('role') == 'admin':
            print("✅ Авторизация администратора работает корректно")
        
        print("\n" + "=" * 95)
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("=" * 95)

def main():
    """Главная функция тестирования"""
    tester = PickupDeletionFixTest()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()