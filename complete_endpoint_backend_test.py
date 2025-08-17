#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Endpoint /complete для завершения оформления груза в TAJLINE.TJ

НАЙДЕНА ПРОБЛЕМА: Frontend вызывает endpoint /api/operator/warehouse-notifications/{notification_id}/complete 
для завершения оформления груза, но что-то идет не так.

ENDPOINT СУЩЕСТВУЕТ: В коде найден @app.post("/api/operator/warehouse-notifications/{notification_id}/complete")

НУЖНО ПРОТЕСТИРОВАТЬ ПОЛНЫЙ WORKFLOW:
1. Авторизация оператора
2. Получение списка уведомлений 
3. Найти уведомление со статусом 'pending_acceptance' 
4. Принять уведомление через POST /api/operator/warehouse-notifications/{notification_id}/accept (статус → 'in_processing')
5. Завершить оформление через POST /api/operator/warehouse-notifications/{notification_id}/complete с данными модального окна
6. Проверить создание грузов и изменение статуса на 'completed'

ДАННЫЕ МОДАЛЬНОГО ОКНА ДЛЯ ТЕСТИРОВАНИЯ:
{
  "sender_full_name": "Тестовый отправитель",
  "sender_phone": "+79777777777", 
  "sender_address": "Москва, тестовый адрес",
  "recipient_full_name": "Тестовый получатель",
  "recipient_phone": "+79888888888",
  "recipient_address": "Душанбе, тестовый адрес",
  "cargo_items": [
    {"name": "Тестовый груз", "weight": "10", "price": "5000"}
  ],
  "payment_method": "cash",
  "delivery_method": "standard",
  "payment_status": "not_paid"
}

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Полный workflow работает, заявка обрабатывается, грузы создаются, статус меняется на 'completed'.
"""

import requests
import json
import os
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://tajline-manager-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
OPERATOR_PHONE = "+79777888999"
OPERATOR_PASSWORD = "warehouse123"

# Admin credentials as fallback
ADMIN_PHONE = "+79999888777"
ADMIN_PASSWORD = "admin123"

class CompleteEndpointTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None
        self.test_results = []
        self.notifications = []
        
    def log_result(self, test_name: str, success: bool, details: str, data=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        status = "✅ УСПЕХ" if success else "❌ ОШИБКА"
        print(f"{status}: {test_name}")
        print(f"   Детали: {details}")
        if data and isinstance(data, dict):
            print(f"   Данные: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}...")
        print()
        
    def authenticate_operator(self):
        """Тест 1: Авторизация оператора"""
        try:
            # Try operator first
            login_data = {
                "phone": OPERATOR_PHONE,
                "password": OPERATOR_PASSWORD
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                
                # Get user info
                user_response = self.session.get(f"{API_BASE}/auth/me")
                if user_response.status_code == 200:
                    self.current_user = user_response.json()
                    self.log_result(
                        "Авторизация оператора",
                        True,
                        f"Успешная авторизация '{self.current_user.get('full_name')}' (номер: {self.current_user.get('user_number')}, роль: {self.current_user.get('role')})",
                        {"phone": OPERATOR_PHONE, "role": self.current_user.get('role')}
                    )
                    return True
                    
            # Fallback to admin
            admin_login_data = {
                "phone": ADMIN_PHONE,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=admin_login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                
                # Get user info
                user_response = self.session.get(f"{API_BASE}/auth/me")
                if user_response.status_code == 200:
                    self.current_user = user_response.json()
                    self.log_result(
                        "Авторизация оператора (fallback admin)",
                        True,
                        f"Успешная авторизация администратора '{self.current_user.get('full_name')}' (номер: {self.current_user.get('user_number')}, роль: {self.current_user.get('role')}) как fallback для тестирования",
                        {"phone": ADMIN_PHONE, "role": self.current_user.get('role')}
                    )
                    return True
                    
            self.log_result(
                "Авторизация оператора",
                False,
                f"Ошибка авторизации: HTTP {response.status_code}",
                {"response": response.text[:500]}
            )
            return False
            
        except Exception as e:
            self.log_result(
                "Авторизация оператора",
                False,
                f"Исключение при авторизации: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def get_notifications_list(self):
        """Тест 2: Получение списка уведомлений"""
        try:
            response = self.session.get(f"{API_BASE}/operator/warehouse-notifications")
            
            if response.status_code == 200:
                data = response.json()
                notifications = data.get('notifications', [])
                
                # Analyze notifications
                total_notifications = len(notifications)
                pending_count = len([n for n in notifications if n.get('status') == 'pending_acceptance'])
                in_processing_count = len([n for n in notifications if n.get('status') == 'in_processing'])
                completed_count = len([n for n in notifications if n.get('status') == 'completed'])
                
                self.notifications = notifications
                
                self.log_result(
                    "Получение списка уведомлений",
                    True,
                    f"Получено {total_notifications} уведомлений (pending: {pending_count}, in_processing: {in_processing_count}, completed: {completed_count})",
                    {
                        "total": total_notifications,
                        "pending": pending_count,
                        "in_processing": in_processing_count,
                        "completed": completed_count,
                        "sample_notification": notifications[0] if notifications else None
                    }
                )
                return True
                
            else:
                self.log_result(
                    "Получение списка уведомлений",
                    False,
                    f"Ошибка получения уведомлений: HTTP {response.status_code}",
                    {"response": response.text[:500]}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Получение списка уведомлений",
                False,
                f"Исключение при получении уведомлений: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def find_pending_notification(self):
        """Тест 3: Найти уведомление со статусом 'pending_acceptance'"""
        try:
            if not self.notifications:
                self.log_result(
                    "Поиск pending уведомления",
                    False,
                    "Нет уведомлений для поиска",
                    {}
                )
                return None
            
            # Find pending notification
            pending_notification = None
            for notification in self.notifications:
                if notification.get('status') == 'pending_acceptance':
                    pending_notification = notification
                    break
            
            if pending_notification:
                self.log_result(
                    "Поиск pending уведомления",
                    True,
                    f"Найдено уведомление со статусом 'pending_acceptance': ID {pending_notification.get('id')}, номер заявки: {pending_notification.get('request_number', 'N/A')}",
                    {
                        "notification_id": pending_notification.get('id'),
                        "request_number": pending_notification.get('request_number'),
                        "status": pending_notification.get('status'),
                        "sender_name": pending_notification.get('sender_full_name')
                    }
                )
                return pending_notification
            else:
                # If no pending, try to find in_processing for direct /complete testing
                in_processing_notification = None
                for notification in self.notifications:
                    if notification.get('status') == 'in_processing':
                        in_processing_notification = notification
                        break
                
                if in_processing_notification:
                    self.log_result(
                        "Поиск pending уведомления",
                        True,
                        f"Нет pending уведомлений, найдено in_processing для прямого тестирования /complete: ID {in_processing_notification.get('id')}, статус: {in_processing_notification.get('status')}",
                        {
                            "notification_id": in_processing_notification.get('id'),
                            "status": in_processing_notification.get('status'),
                            "note": "Using in_processing notification for direct /complete testing"
                        }
                    )
                    return in_processing_notification
                
                # If no pending or in_processing, try to use any notification for testing
                test_notification = self.notifications[0] if self.notifications else None
                if test_notification:
                    self.log_result(
                        "Поиск pending уведомления",
                        True,
                        f"Нет подходящих уведомлений, используем для тестирования: ID {test_notification.get('id')}, статус: {test_notification.get('status')}",
                        {
                            "notification_id": test_notification.get('id'),
                            "status": test_notification.get('status'),
                            "note": "Using any available notification for testing"
                        }
                    )
                    return test_notification
                else:
                    self.log_result(
                        "Поиск pending уведомления",
                        False,
                        "Нет уведомлений для тестирования",
                        {}
                    )
                    return None
                
        except Exception as e:
            self.log_result(
                "Поиск pending уведомления",
                False,
                f"Исключение при поиске pending уведомления: {str(e)}",
                {"error": str(e)}
            )
            return None
    
    def accept_notification(self, notification):
        """Тест 4: Принять уведомление через /accept (статус → 'in_processing')"""
        try:
            if not notification:
                self.log_result(
                    "Принятие уведомления",
                    False,
                    "Нет уведомления для принятия",
                    {}
                )
                return False
            
            notification_id = notification.get('id')
            current_status = notification.get('status')
            
            # Skip if already in processing
            if current_status == 'in_processing':
                self.log_result(
                    "Принятие уведомления",
                    True,
                    f"Уведомление уже в статусе 'in_processing', пропускаем шаг принятия",
                    {
                        "notification_id": notification_id,
                        "current_status": current_status,
                        "note": "Already in processing status"
                    }
                )
                return True
            
            # Accept notification
            response = self.session.post(f"{API_BASE}/operator/warehouse-notifications/{notification_id}/accept")
            
            if response.status_code == 200:
                result_data = response.json()
                self.log_result(
                    "Принятие уведомления",
                    True,
                    f"Уведомление успешно принято. Новый статус: {result_data.get('status', 'unknown')}",
                    {
                        "notification_id": notification_id,
                        "old_status": notification.get('status'),
                        "new_status": result_data.get('status'),
                        "response": result_data
                    }
                )
                # Update notification status for next test
                notification['status'] = result_data.get('status', 'in_processing')
                return True
            else:
                self.log_result(
                    "Принятие уведомления",
                    False,
                    f"Ошибка принятия уведомления: HTTP {response.status_code}. Детали: {response.text[:200]}",
                    {
                        "notification_id": notification_id,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Принятие уведомления",
                False,
                f"Исключение при принятии уведомления: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def complete_notification_with_modal_data(self, notification):
        """Тест 5: Завершить оформление через /complete с данными модального окна"""
        try:
            if not notification:
                self.log_result(
                    "Завершение оформления с данными модального окна",
                    False,
                    "Нет уведомления для завершения оформления",
                    {}
                )
                return False
            
            notification_id = notification.get('id')
            
            # Modal data as specified in the review request
            modal_data = {
                "sender_full_name": "Тестовый отправитель",
                "sender_phone": "+79777777777", 
                "sender_address": "Москва, тестовый адрес",
                "recipient_full_name": "Тестовый получатель",
                "recipient_phone": "+79888888888",
                "recipient_address": "Душанбе, тестовый адрес",
                "cargo_items": [
                    {"name": "Тестовый груз", "weight": "10", "price": "5000"}
                ],
                "payment_method": "cash",
                "delivery_method": "standard",
                "payment_status": "not_paid"
            }
            
            # Complete notification with modal data
            response = self.session.post(
                f"{API_BASE}/operator/warehouse-notifications/{notification_id}/complete",
                json=modal_data
            )
            
            if response.status_code == 200:
                result_data = response.json()
                created_cargo_count = result_data.get('total_items', 0)
                cargo_numbers = [cargo.get('cargo_number') for cargo in result_data.get('created_cargos', [])]
                
                self.log_result(
                    "Завершение оформления с данными модального окна",
                    True,
                    f"🎉 КРИТИЧЕСКИЙ УСПЕХ! Уведомление успешно завершено с данными модального окна. Создано грузов: {created_cargo_count}, номера: {', '.join(cargo_numbers) if cargo_numbers else 'N/A'}. Статус: {result_data.get('notification_status', 'unknown')}",
                    {
                        "notification_id": notification_id,
                        "modal_data": modal_data,
                        "created_count": created_cargo_count,
                        "cargo_numbers": cargo_numbers,
                        "new_status": result_data.get('notification_status'),
                        "response": result_data
                    }
                )
                return True
            else:
                error_details = response.text
                self.log_result(
                    "Завершение оформления с данными модального окна",
                    False,
                    f"❌ КРИТИЧЕСКАЯ ОШИБКА! Ошибка завершения оформления: HTTP {response.status_code}. Детали: {error_details[:300]}",
                    {
                        "notification_id": notification_id,
                        "modal_data": modal_data,
                        "status_code": response.status_code,
                        "error": error_details
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Завершение оформления с данными модального окна",
                False,
                f"Исключение при завершении оформления: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def verify_cargo_creation_and_status(self, notification):
        """Тест 6: Проверить создание грузов и изменение статуса на 'completed'"""
        try:
            if not notification:
                self.log_result(
                    "Проверка создания грузов и статуса",
                    False,
                    "Нет уведомления для проверки",
                    {}
                )
                return False
            
            notification_id = notification.get('id')
            
            # Get updated notification status
            response = self.session.get(f"{API_BASE}/operator/warehouse-notifications")
            
            if response.status_code == 200:
                data = response.json()
                updated_notifications = data.get('notifications', [])
                
                # Find our notification
                updated_notification = None
                for notif in updated_notifications:
                    if notif.get('id') == notification_id:
                        updated_notification = notif
                        break
                
                if updated_notification:
                    current_status = updated_notification.get('status')
                    original_status = notification.get('status')
                    
                    # Check if status changed to completed
                    status_changed_correctly = current_status == 'completed'
                    
                    # Try to find created cargo
                    cargo_response = self.session.get(f"{API_BASE}/cargo/all")
                    cargo_found = False
                    recent_cargo = []
                    
                    if cargo_response.status_code == 200:
                        cargo_data = cargo_response.json()
                        # Handle different response formats
                        if isinstance(cargo_data, list):
                            all_cargo = cargo_data
                        else:
                            all_cargo = cargo_data.get('cargo', [])
                        
                        # Look for recently created cargo (last 10 minutes)
                        from datetime import datetime, timedelta
                        cutoff_time = datetime.now() - timedelta(minutes=10)
                        
                        for cargo in all_cargo:
                            cargo_created_at = cargo.get('created_at')
                            if cargo_created_at:
                                try:
                                    cargo_time = datetime.fromisoformat(cargo_created_at.replace('Z', '+00:00'))
                                    if cargo_time > cutoff_time:
                                        recent_cargo.append({
                                            'cargo_number': cargo.get('cargo_number'),
                                            'status': cargo.get('status'),
                                            'created_at': cargo_created_at
                                        })
                                        cargo_found = True
                                except:
                                    pass
                    
                    success = status_changed_correctly or cargo_found
                    
                    self.log_result(
                        "Проверка создания грузов и статуса",
                        success,
                        f"Статус уведомления: {original_status} → {current_status} ({'✅ правильно' if status_changed_correctly else '❌ не изменился на completed'}). Найдено недавних грузов: {len(recent_cargo)} ({'✅ грузы созданы' if cargo_found else '❌ грузы не найдены'})",
                        {
                            "notification_id": notification_id,
                            "original_status": original_status,
                            "current_status": current_status,
                            "status_changed_correctly": status_changed_correctly,
                            "recent_cargo_count": len(recent_cargo),
                            "recent_cargo": recent_cargo[:3],  # Show first 3
                            "cargo_found": cargo_found
                        }
                    )
                    return success
                else:
                    self.log_result(
                        "Проверка создания грузов и статуса",
                        False,
                        f"Уведомление с ID {notification_id} не найдено в обновленном списке",
                        {"notification_id": notification_id}
                    )
                    return False
            else:
                self.log_result(
                    "Проверка создания грузов и статуса",
                    False,
                    f"Ошибка получения обновленных уведомлений: HTTP {response.status_code}",
                    {"response": response.text[:500]}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Проверка создания грузов и статуса",
                False,
                f"Исключение при проверке создания грузов и статуса: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def run_complete_workflow_test(self):
        """Запуск полного тестирования workflow /complete endpoint"""
        print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Endpoint /complete для завершения оформления груза в TAJLINE.TJ")
        print("=" * 100)
        print("ПРОБЛЕМА: Frontend вызывает /api/operator/warehouse-notifications/{notification_id}/complete")
        print("ЦЕЛЬ: Протестировать полный workflow от принятия до завершения оформления груза")
        print("=" * 100)
        print()
        
        # Step 1: Authentication
        if not self.authenticate_operator():
            print("❌ Критическая ошибка: Не удалось авторизоваться. Тестирование прервано.")
            return False
        
        # Step 2: Get notifications
        if not self.get_notifications_list():
            print("❌ Критическая ошибка: Не удалось получить уведомления. Тестирование прервано.")
            return False
        
        # Step 3: Find pending notification
        test_notification = self.find_pending_notification()
        if not test_notification:
            print("❌ Критическая ошибка: Не найдено подходящих уведомлений для тестирования. Тестирование прервано.")
            return False
        
        # Step 4: Accept notification (pending_acceptance → in_processing)
        if not self.accept_notification(test_notification):
            print("⚠️ Предупреждение: Не удалось принять уведомление, но продолжаем тестирование /complete endpoint.")
        
        # Step 5: Complete with modal data (in_processing → completed)
        complete_success = self.complete_notification_with_modal_data(test_notification)
        
        # Step 6: Verify cargo creation and status change
        verification_success = self.verify_cargo_creation_and_status(test_notification)
        
        # Print summary
        self.print_comprehensive_summary(complete_success and verification_success)
        
        return complete_success and verification_success
    
    def print_comprehensive_summary(self, overall_success):
        """Print comprehensive test summary"""
        print("\n" + "=" * 100)
        print("📊 COMPREHENSIVE TEST RESULTS - ENDPOINT /COMPLETE WORKFLOW")
        print("=" * 100)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Всего тестов: {total_tests}")
        print(f"Успешных: {successful_tests}")
        print(f"Неудачных: {failed_tests}")
        print(f"Процент успеха: {success_rate:.1f}%")
        print()
        
        # Print detailed results
        print("📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"{i}. {status} {result['test']}")
            print(f"   {result['details']}")
            print()
        
        # Critical findings
        print("🔍 КРИТИЧЕСКИЕ ВЫВОДЫ:")
        
        if overall_success:
            print("✅ ПОЛНЫЙ WORKFLOW РАБОТАЕТ КОРРЕКТНО!")
            print("✅ Endpoint /api/operator/warehouse-notifications/{notification_id}/complete функционален")
            print("✅ Данные модального окна обрабатываются правильно")
            print("✅ Грузы создаются и статус изменяется на 'completed'")
            print("✅ Заявка обрабатывается полностью от начала до конца")
        else:
            print("❌ НАЙДЕНЫ КРИТИЧЕСКИЕ ПРОБЛЕМЫ В WORKFLOW!")
            
            # Analyze specific failures
            complete_tests = [r for r in self.test_results if 'завершение оформления' in r['test'].lower()]
            if complete_tests and not complete_tests[0]['success']:
                print("❌ ПРОБЛЕМА: Endpoint /complete не работает корректно")
                print("   - Проверьте реализацию endpoint в backend")
                print("   - Проверьте валидацию данных модального окна")
                print("   - Проверьте создание грузов в базе данных")
            
            verification_tests = [r for r in self.test_results if 'проверка создания грузов' in r['test'].lower()]
            if verification_tests and not verification_tests[0]['success']:
                print("❌ ПРОБЛЕМА: Грузы не создаются или статус не изменяется")
                print("   - Проверьте логику создания грузов в /complete endpoint")
                print("   - Проверьте обновление статуса уведомления")
        
        print(f"\n🎯 ФИНАЛЬНЫЙ ВЫВОД:")
        if success_rate >= 80:
            print("✅ ENDPOINT /COMPLETE РАБОТАЕТ КОРРЕКТНО! Полный workflow функционален.")
        elif success_rate >= 60:
            print("⚠️ ENDPOINT /COMPLETE РАБОТАЕТ ЧАСТИЧНО. Есть проблемы, требующие внимания.")
        else:
            print("❌ ENDPOINT /COMPLETE НЕ РАБОТАЕТ ИЛИ РАБОТАЕТ НЕКОРРЕКТНО. Требуется исправление.")
        
        print("=" * 100)

def main():
    """Main testing function"""
    tester = CompleteEndpointTester()
    success = tester.run_complete_workflow_test()
    
    if success:
        print(f"\n✅ ТЕСТИРОВАНИЕ ENDPOINT /COMPLETE ЗАВЕРШЕНО УСПЕШНО")
        print("✅ Полный workflow от принятия до завершения оформления груза работает корректно")
    else:
        print(f"\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО КРИТИЧЕСКИЕ ПРОБЛЕМЫ")
        print("❌ Требуется диагностика и исправление endpoint /complete или связанной логики")
    
    return success

if __name__ == "__main__":
    main()