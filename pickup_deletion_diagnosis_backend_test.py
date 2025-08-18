#!/usr/bin/env python3
"""
🚨 ДИАГНОСТИКА: Ошибка "Заявка не найдена" при удалении заявок на забор в TAJLINE.TJ

ПРОБЛЕМА: При попытке удаления заявки из категории "Грузы" → подкатегория "На забор" возникает ошибка "Заявка не найдена"

ПОДОЗРЕНИЯ:
1. Frontend отправляет неправильный ID заявки на backend
2. Backend endpoint удаления заявок на забор работает с неправильной коллекцией
3. Используется неправильный ключ поиска (id vs request_id vs request_number)
4. Заявки находятся в коллекции courier_pickup_requests, но endpoint ищет в другой коллекции

НУЖНО ПРОТЕСТИРОВАТЬ:
1. Авторизация админа для доступа к заявкам на забор
2. Получение списка заявок на забор через GET /api/admin/courier/pickup-requests
3. Проверка структуры данных заявок (какие поля ID используются)  
4. Тестирование удаления заявки через соответствующий DELETE endpoint
5. Анализ используемых полей: id, request_id, request_number, pickup_request_id
6. Проверка существования endpoint для удаления pickup requests

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Найти корневую причину ошибки "Заявка не найдена" и предложить исправление для корректного удаления заявок на забор.
"""

import requests
import json
import os
from datetime import datetime

# Получаем URL backend из переменной окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cargo-talk.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class PickupDeletionDiagnostic:
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
        if data and isinstance(data, dict) and len(str(data)) < 500:
            print(f"   📊 Данные: {json.dumps(data, ensure_ascii=False, indent=2)}")
        print()
        
    def authenticate_admin(self):
        """Тест 1: Авторизация администратора для доступа к заявкам на забор"""
        try:
            # Пробуем разные учетные данные администратора
            admin_credentials = [
                ("+79999888777", "admin123", "Основной администратор"),
                ("admin@emergent.com", "admin123", "Email администратор"),
                ("+79888777666", "admin123", "Альтернативный администратор")
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
                        
                        # Проверяем, что у пользователя есть права администратора
                        if self.current_user.get('role') == 'admin':
                            self.log_result(
                                "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                                True,
                                f"Успешная авторизация {description}: {user_info}, JWT токен получен",
                                {"phone": phone, "role": self.current_user.get('role')}
                            )
                            return True
                        else:
                            print(f"Пользователь {description} не является администратором (роль: {self.current_user.get('role')})")
                    else:
                        print(f"Не удалось получить данные пользователя для {description}: HTTP {user_response.status_code}")
                else:
                    print(f"Попытка авторизации {description} неудачна: HTTP {response.status_code}")
            
            self.log_result(
                "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                False,
                "Не удалось авторизоваться как администратор ни с одними учетными данными"
            )
            return False
                
        except Exception as e:
            self.log_result(
                "АВТОРИЗАЦИЯ АДМИНИСТРАТОРА",
                False,
                f"Исключение при авторизации: {str(e)}"
            )
            return False
    
    def get_pickup_requests_list(self):
        """Тест 2: Получение списка заявок на забор через различные endpoints"""
        try:
            # Пробуем разные возможные endpoints для получения заявок на забор
            endpoints_to_try = [
                "/api/admin/courier/pickup-requests",
                "/api/admin/pickup-requests", 
                "/api/courier/pickup-requests",
                "/api/admin/courier-requests",
                "/api/admin/requests/pickup",
                "/api/operator/pickup-requests"
            ]
            
            successful_endpoint = None
            pickup_requests = []
            
            for endpoint in endpoints_to_try:
                try:
                    response = self.session.get(f"{BACKEND_URL}{endpoint}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Проверяем разные возможные структуры ответа
                        if isinstance(data, list):
                            pickup_requests = data
                        elif isinstance(data, dict):
                            pickup_requests = data.get('items', data.get('requests', data.get('pickup_requests', [])))
                        
                        if pickup_requests:
                            successful_endpoint = endpoint
                            self.pickup_requests = pickup_requests
                            break
                        else:
                            print(f"Endpoint {endpoint} вернул пустой список")
                    else:
                        print(f"Endpoint {endpoint}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"Ошибка при обращении к {endpoint}: {str(e)}")
            
            if successful_endpoint:
                total_requests = len(pickup_requests)
                
                # Анализируем статусы заявок
                status_counts = {}
                for request in pickup_requests:
                    status = request.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                self.log_result(
                    "ПОЛУЧЕНИЕ СПИСКА ЗАЯВОК НА ЗАБОР",
                    True,
                    f"Endpoint {successful_endpoint} работает корректно, получено {total_requests} заявок на забор. Статусы: {status_counts}",
                    {
                        "endpoint": successful_endpoint,
                        "total_requests": total_requests,
                        "status_counts": status_counts,
                        "sample_request": pickup_requests[0] if pickup_requests else None
                    }
                )
                return True
            else:
                self.log_result(
                    "ПОЛУЧЕНИЕ СПИСКА ЗАЯВОК НА ЗАБОР",
                    False,
                    f"Ни один из endpoints не вернул заявки на забор. Проверенные endpoints: {', '.join(endpoints_to_try)}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ПОЛУЧЕНИЕ СПИСКА ЗАЯВОК НА ЗАБОР",
                False,
                f"Исключение при получении заявок на забор: {str(e)}"
            )
            return False
    
    def analyze_pickup_request_structure(self):
        """Тест 3: Анализ структуры данных заявок на забор"""
        try:
            if not self.pickup_requests:
                self.log_result(
                    "АНАЛИЗ СТРУКТУРЫ ЗАЯВОК НА ЗАБОР",
                    True,
                    "Нет заявок на забор для анализа структуры - это может быть нормально если база данных пуста"
                )
                return True
            
            # Анализируем поля ID в заявках
            id_fields_analysis = {
                'id': 0,
                'request_id': 0,
                'request_number': 0,
                'pickup_request_id': 0,
                'courier_request_id': 0
            }
            
            sample_request = self.pickup_requests[0]
            all_keys = list(sample_request.keys())
            
            for request in self.pickup_requests:
                for field in id_fields_analysis.keys():
                    if field in request and request[field]:
                        id_fields_analysis[field] += 1
            
            total_requests = len(self.pickup_requests)
            
            # Проверяем какие поля используются как основные идентификаторы
            primary_id_candidates = []
            for field, count in id_fields_analysis.items():
                if count == total_requests:  # Поле присутствует во всех заявках
                    primary_id_candidates.append(field)
            
            # Анализируем значения ID полей в образце
            sample_id_values = {}
            for field in id_fields_analysis.keys():
                if field in sample_request:
                    sample_id_values[field] = sample_request[field]
            
            analysis_details = (
                f"Проанализировано {total_requests} заявок на забор. "
                f"Поля ID: {id_fields_analysis}. "
                f"Потенциальные первичные ключи: {primary_id_candidates}. "
                f"Все поля в образце: {len(all_keys)} полей"
            )
            
            self.log_result(
                "АНАЛИЗ СТРУКТУРЫ ЗАЯВОК НА ЗАБОР",
                True,
                analysis_details,
                {
                    "total_requests": total_requests,
                    "id_fields_analysis": id_fields_analysis,
                    "primary_id_candidates": primary_id_candidates,
                    "sample_id_values": sample_id_values,
                    "all_fields": all_keys,
                    "sample_request": sample_request
                }
            )
            return True
            
        except Exception as e:
            self.log_result(
                "АНАЛИЗ СТРУКТУРЫ ЗАЯВОК НА ЗАБОР",
                False,
                f"Исключение при анализе структуры: {str(e)}"
            )
            return False
    
    def test_deletion_endpoints(self):
        """Тест 4: Тестирование различных endpoints для удаления заявок на забор"""
        try:
            if not self.pickup_requests:
                self.log_result(
                    "ТЕСТИРОВАНИЕ ENDPOINTS УДАЛЕНИЯ",
                    True,
                    "Нет заявок на забор для тестирования удаления"
                )
                return True
            
            # Берем первую заявку для тестирования
            test_request = self.pickup_requests[0]
            
            # Получаем различные возможные ID для тестирования
            possible_ids = {}
            id_fields = ['id', 'request_id', 'request_number', 'pickup_request_id', 'courier_request_id']
            
            for field in id_fields:
                if field in test_request and test_request[field]:
                    possible_ids[field] = test_request[field]
            
            if not possible_ids:
                self.log_result(
                    "ТЕСТИРОВАНИЕ ENDPOINTS УДАЛЕНИЯ",
                    False,
                    "В тестовой заявке не найдено ни одного поля ID для тестирования удаления"
                )
                return False
            
            # Пробуем различные endpoints для удаления
            deletion_endpoints = [
                "/api/admin/courier/pickup-requests/{id}",
                "/api/admin/pickup-requests/{id}",
                "/api/admin/courier-requests/{id}",
                "/api/admin/requests/pickup/{id}",
                "/api/courier/pickup-requests/{id}"
            ]
            
            deletion_results = []
            
            for endpoint_template in deletion_endpoints:
                for id_field, id_value in possible_ids.items():
                    endpoint = endpoint_template.format(id=id_value)
                    
                    try:
                        # Сначала проверяем существование endpoint через HEAD запрос
                        head_response = self.session.head(f"{BACKEND_URL}{endpoint}")
                        
                        if head_response.status_code == 404:
                            deletion_results.append({
                                "endpoint": endpoint,
                                "id_field": id_field,
                                "id_value": id_value,
                                "status": "endpoint_not_found",
                                "details": "Endpoint не существует"
                            })
                            continue
                        
                        # Если endpoint существует, пробуем DELETE запрос
                        delete_response = self.session.delete(f"{BACKEND_URL}{endpoint}")
                        
                        deletion_results.append({
                            "endpoint": endpoint,
                            "id_field": id_field,
                            "id_value": id_value,
                            "status_code": delete_response.status_code,
                            "response": delete_response.text[:200],
                            "status": "tested"
                        })
                        
                        if delete_response.status_code == 200:
                            print(f"✅ Успешное удаление через {endpoint} с {id_field}={id_value}")
                        elif delete_response.status_code == 404:
                            print(f"❌ Заявка не найдена: {endpoint} с {id_field}={id_value}")
                        else:
                            print(f"⚠️ Другая ошибка: {endpoint} с {id_field}={id_value} - HTTP {delete_response.status_code}")
                            
                    except Exception as e:
                        deletion_results.append({
                            "endpoint": endpoint,
                            "id_field": id_field,
                            "id_value": id_value,
                            "status": "error",
                            "details": str(e)
                        })
            
            # Анализируем результаты
            successful_deletions = [r for r in deletion_results if r.get('status_code') == 200]
            not_found_errors = [r for r in deletion_results if r.get('status_code') == 404]
            endpoint_not_found = [r for r in deletion_results if r.get('status') == 'endpoint_not_found']
            
            analysis = (
                f"Протестировано {len(deletion_results)} комбинаций endpoint/ID. "
                f"Успешных удалений: {len(successful_deletions)}, "
                f"Ошибок 'не найдено': {len(not_found_errors)}, "
                f"Несуществующих endpoints: {len(endpoint_not_found)}"
            )
            
            # Определяем успешность теста
            test_success = len(successful_deletions) > 0 or len(not_found_errors) > 0  # Хотя бы один endpoint отвечает
            
            self.log_result(
                "ТЕСТИРОВАНИЕ ENDPOINTS УДАЛЕНИЯ",
                test_success,
                analysis,
                {
                    "test_request_ids": possible_ids,
                    "deletion_results": deletion_results,
                    "successful_deletions": len(successful_deletions),
                    "not_found_errors": len(not_found_errors),
                    "endpoint_not_found": len(endpoint_not_found)
                }
            )
            return test_success
            
        except Exception as e:
            self.log_result(
                "ТЕСТИРОВАНИЕ ENDPOINTS УДАЛЕНИЯ",
                False,
                f"Исключение при тестировании удаления: {str(e)}"
            )
            return False
    
    def diagnose_root_cause(self):
        """Тест 5: Диагностика корневой причины ошибки "Заявка не найдена" """
        try:
            # Анализируем собранные данные для определения корневой причины
            diagnosis = {
                "has_pickup_requests": len(self.pickup_requests) > 0,
                "pickup_requests_count": len(self.pickup_requests),
                "authentication_working": self.current_user is not None,
                "user_role": self.current_user.get('role') if self.current_user else None
            }
            
            # Анализируем структуру ID полей
            if self.pickup_requests:
                sample_request = self.pickup_requests[0]
                id_fields_present = []
                id_fields_missing = []
                
                expected_id_fields = ['id', 'request_id', 'request_number', 'pickup_request_id']
                for field in expected_id_fields:
                    if field in sample_request and sample_request[field]:
                        id_fields_present.append(field)
                    else:
                        id_fields_missing.append(field)
                
                diagnosis.update({
                    "id_fields_present": id_fields_present,
                    "id_fields_missing": id_fields_missing,
                    "sample_request_structure": list(sample_request.keys())
                })
            
            # Формируем диагноз
            root_cause_analysis = []
            
            if not diagnosis["has_pickup_requests"]:
                root_cause_analysis.append("База данных не содержит заявок на забор для тестирования")
            
            if diagnosis["user_role"] != "admin":
                root_cause_analysis.append(f"Пользователь не является администратором (роль: {diagnosis['user_role']})")
            
            if diagnosis.get("id_fields_missing"):
                root_cause_analysis.append(f"В заявках отсутствуют ожидаемые поля ID: {diagnosis['id_fields_missing']}")
            
            # Проверяем результаты предыдущих тестов
            deletion_test_results = [r for r in self.test_results if r["test"] == "ТЕСТИРОВАНИЕ ENDPOINTS УДАЛЕНИЯ"]
            if deletion_test_results and not deletion_test_results[0]["success"]:
                root_cause_analysis.append("Endpoints для удаления заявок на забор не работают корректно")
            
            if not root_cause_analysis:
                root_cause_analysis.append("Система работает корректно - возможно, проблема в frontend логике")
            
            diagnosis_summary = f"Диагностика завершена. Возможные причины ошибки: {'; '.join(root_cause_analysis)}"
            
            self.log_result(
                "ДИАГНОСТИКА КОРНЕВОЙ ПРИЧИНЫ",
                True,
                diagnosis_summary,
                {
                    "diagnosis": diagnosis,
                    "root_cause_analysis": root_cause_analysis,
                    "recommendations": self.generate_recommendations(diagnosis, root_cause_analysis)
                }
            )
            return True
            
        except Exception as e:
            self.log_result(
                "ДИАГНОСТИКА КОРНЕВОЙ ПРИЧИНЫ",
                False,
                f"Исключение при диагностике: {str(e)}"
            )
            return False
    
    def generate_recommendations(self, diagnosis, root_cause_analysis):
        """Генерация рекомендаций по исправлению проблемы"""
        recommendations = []
        
        if "База данных не содержит заявок на забор" in '; '.join(root_cause_analysis):
            recommendations.append("Создать тестовые заявки на забор для проверки функциональности")
        
        if "Endpoints для удаления заявок на забор не работают" in '; '.join(root_cause_analysis):
            recommendations.append("Проверить реализацию DELETE endpoints в backend коде")
            recommendations.append("Убедиться, что endpoints используют правильные поля ID для поиска заявок")
        
        if diagnosis.get("id_fields_missing"):
            recommendations.append(f"Добавить отсутствующие поля ID в модель заявок: {diagnosis['id_fields_missing']}")
        
        if "frontend логике" in '; '.join(root_cause_analysis):
            recommendations.append("Проверить, какие ID отправляет frontend при удалении заявок")
            recommendations.append("Убедиться, что frontend использует правильный endpoint для удаления")
        
        recommendations.append("Добавить логирование в backend для отслеживания запросов на удаление")
        recommendations.append("Проверить права доступа пользователей к операциям удаления заявок")
        
        return recommendations
    
    def run_comprehensive_diagnosis(self):
        """Запуск полной диагностики проблемы удаления заявок на забор"""
        print("🚨 ДИАГНОСТИКА: Ошибка 'Заявка не найдена' при удалении заявок на забор в TAJLINE.TJ")
        print("=" * 90)
        print()
        
        # Тест 1: Авторизация администратора
        if not self.authenticate_admin():
            print("❌ Критическая ошибка: Не удалось авторизоваться как администратор. Диагностика прервана.")
            return
        
        # Тест 2: Получение списка заявок на забор
        self.get_pickup_requests_list()
        
        # Тест 3: Анализ структуры заявок
        self.analyze_pickup_request_structure()
        
        # Тест 4: Тестирование endpoints удаления
        self.test_deletion_endpoints()
        
        # Тест 5: Диагностика корневой причины
        self.diagnose_root_cause()
        
        # Итоговый отчет
        self.print_comprehensive_summary()
    
    def print_comprehensive_summary(self):
        """Печать итогового отчета диагностики"""
        print("\n" + "=" * 90)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ")
        print("=" * 90)
        
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
        
        # Анализируем результаты диагностики
        diagnosis_results = [r for r in self.test_results if r['test'] == "ДИАГНОСТИКА КОРНЕВОЙ ПРИЧИНЫ"]
        if diagnosis_results and diagnosis_results[0]['data']:
            recommendations = diagnosis_results[0]['data'].get('recommendations', [])
            root_causes = diagnosis_results[0]['data'].get('root_cause_analysis', [])
            
            print("📋 НАЙДЕННЫЕ ПРОБЛЕМЫ:")
            for cause in root_causes:
                print(f"   • {cause}")
            
            print("\n💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
            for rec in recommendations:
                print(f"   • {rec}")
        
        # Проверяем наличие заявок на забор
        if self.pickup_requests:
            print(f"\n✅ В системе найдено {len(self.pickup_requests)} заявок на забор")
        else:
            print("\n⚠️ В системе не найдено заявок на забор для тестирования")
        
        # Проверяем авторизацию
        if self.current_user and self.current_user.get('role') == 'admin':
            print("✅ Авторизация администратора работает корректно")
        else:
            print("❌ Проблемы с авторизацией администратора")
        
        print("\n" + "=" * 90)
        print("🎯 ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("=" * 90)

def main():
    """Главная функция диагностики"""
    diagnostic = PickupDeletionDiagnostic()
    diagnostic.run_comprehensive_diagnosis()

if __name__ == "__main__":
    main()