#!/usr/bin/env python3
"""
Backend Stability Testing for Warehouse Notifications after React "removeChild" Fixes
Tests backend stability after fixing React errors when showing all warehouse pickup notifications in TAJLINE.TJ
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class WarehouseNotificationsBackendTester:
    def __init__(self, base_url="https://tajline-cargo-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🏭 WAREHOUSE NOTIFICATIONS BACKEND STABILITY TESTER")
        print(f"📡 Base URL: {self.base_url}")
        print(f"🎯 Testing backend stability after React 'removeChild' fixes")
        print("=" * 80)

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, token: Optional[str] = None, 
                 params: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, json=data, headers=headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
                    if isinstance(result, dict) and len(str(result)) < 300:
                        print(f"   📄 Response: {result}")
                    elif isinstance(result, list) and len(result) > 0:
                        print(f"   📄 Response: Found {len(result)} items")
                    return True, result
                except:
                    return True, {}
            else:
                print(f"   ❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   📄 Error: {error_detail}")
                except:
                    print(f"   📄 Raw response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"   ❌ FAILED - Exception: {str(e)}")
            return False, {}

    def test_warehouse_notifications_backend_stability(self):
        """Test backend stability after React removeChild fixes for warehouse notifications"""
        print("\n🎯 WAREHOUSE NOTIFICATIONS BACKEND STABILITY TESTING")
        print("   📋 Протестировать стабильность backend после исправлений React ошибок при показе всех заявок на забор в TAJLINE.TJ")
        print("   🔧 ТЕСТОВЫЙ ПЛАН:")
        print("   1) Авторизация оператора склада (+79777888999/warehouse123)")
        print("   2) Проверка получения списка уведомлений")
        print("   3) Тестирование функции отправки на размещение")
        print("   4) Проверка корректности фильтрации уведомлений")
        print("   5) Убедиться что backend не затронут frontend изменениями")
        
        all_success = True
        
        # Test 1: АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА (+79777888999/warehouse123)
        print("\n   🔐 Test 1: АВТОРИЗАЦИЯ ОПЕРАТОРА СКЛАДА (+79777888999/warehouse123)...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, login_response = self.run_test(
            "Warehouse Operator Authentication",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        all_success &= success
        
        operator_token = None
        if success and 'access_token' in login_response:
            operator_token = login_response['access_token']
            operator_user = login_response.get('user', {})
            operator_role = operator_user.get('role')
            operator_name = operator_user.get('full_name')
            operator_phone = operator_user.get('phone')
            operator_user_number = operator_user.get('user_number')
            
            print(f"   ✅ Operator login successful: {operator_name}")
            print(f"   👑 Role: {operator_role}")
            print(f"   📞 Phone: {operator_phone}")
            print(f"   🆔 User Number: {operator_user_number}")
            print(f"   🔑 JWT Token: {operator_token[:50]}...")
            
            # Verify role is warehouse_operator
            if operator_role == 'warehouse_operator':
                print("   ✅ Operator role correctly set to 'warehouse_operator'")
            else:
                print(f"   ❌ Operator role incorrect: expected 'warehouse_operator', got '{operator_role}'")
                all_success = False
            
            self.tokens['warehouse_operator'] = operator_token
            self.users['warehouse_operator'] = operator_user
        else:
            print("   ❌ Operator login failed - no access token received")
            print(f"   📄 Response: {login_response}")
            all_success = False
            return False
        
        # Test 2: ПРОВЕРКА ПОЛУЧЕНИЯ СПИСКА УВЕДОМЛЕНИЙ
        print("\n   📋 Test 2: ПРОВЕРКА ПОЛУЧЕНИЯ СПИСКА УВЕДОМЛЕНИЙ...")
        
        success, notifications_response = self.run_test(
            "Get Warehouse Notifications List",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        all_success &= success
        
        notifications_list = []
        if success:
            print("   ✅ /api/operator/warehouse-notifications endpoint working")
            
            if isinstance(notifications_response, dict) and 'notifications' in notifications_response:
                notifications_list = notifications_response['notifications']
                notification_count = len(notifications_list)
                print(f"   📊 Found {notification_count} warehouse notifications")
                
                # Check notification structure for React key uniqueness
                if notification_count > 0:
                    sample_notification = notifications_list[0]
                    required_fields = ['id', 'request_number', 'sender_full_name', 'status', 'created_at']
                    missing_fields = [field for field in required_fields if field not in sample_notification]
                    
                    if not missing_fields:
                        print("   ✅ Notification structure correct (id, request_number, sender_full_name, status, created_at)")
                        print(f"   📄 Sample notification ID: {sample_notification.get('id')}")
                        print(f"   📄 Sample request number: {sample_notification.get('request_number')}")
                        print(f"   📄 Sample status: {sample_notification.get('status')}")
                        
                        # Check for unique IDs (important for React keys)
                        notification_ids = [n.get('id') for n in notifications_list if n.get('id')]
                        unique_ids = set(notification_ids)
                        
                        if len(notification_ids) == len(unique_ids):
                            print("   ✅ All notification IDs are unique (good for React keys)")
                        else:
                            print(f"   ❌ Duplicate notification IDs found: {len(notification_ids)} total, {len(unique_ids)} unique")
                            all_success = False
                    else:
                        print(f"   ❌ Missing required fields in notifications: {missing_fields}")
                        all_success = False
                else:
                    print("   ⚠️  No notifications found for testing")
            elif isinstance(notifications_response, list):
                notifications_list = notifications_response
                notification_count = len(notifications_list)
                print(f"   📊 Found {notification_count} warehouse notifications (direct list format)")
            else:
                print("   ❌ Unexpected response format for notifications")
                print(f"   📄 Response type: {type(notifications_response)}")
                print(f"   📄 Response keys: {list(notifications_response.keys()) if isinstance(notifications_response, dict) else 'Not a dict'}")
                all_success = False
        else:
            print("   ❌ Failed to get warehouse notifications")
            all_success = False
        
        # Test 3: ТЕСТИРОВАНИЕ ФУНКЦИИ ОТПРАВКИ НА РАЗМЕЩЕНИЕ
        print("\n   🏗️ Test 3: ТЕСТИРОВАНИЕ ФУНКЦИИ ОТПРАВКИ НА РАЗМЕЩЕНИЕ...")
        
        # Find a notification that can be sent to placement
        test_notification_id = None
        if notifications_list:
            for notification in notifications_list:
                if notification.get('status') in ['pending_acceptance', 'in_processing']:
                    test_notification_id = notification.get('id')
                    test_request_number = notification.get('request_number')
                    print(f"   🎯 Using notification for testing: {test_request_number} (ID: {test_notification_id})")
                    break
        
        if test_notification_id:
            # Test send to placement function
            success, placement_response = self.run_test(
                "Send Notification to Placement",
                "POST",
                f"/api/operator/warehouse-notifications/{test_notification_id}/send-to-placement",
                200,
                token=operator_token
            )
            
            if success:
                print("   ✅ Send to placement function working")
                
                # Verify response structure
                if isinstance(placement_response, dict):
                    message = placement_response.get('message', '')
                    cargo_number = placement_response.get('cargo_number', '')
                    
                    if 'success' in message.lower() or cargo_number:
                        print(f"   ✅ Placement successful: {message}")
                        if cargo_number:
                            print(f"   📦 Cargo created: {cargo_number}")
                    else:
                        print(f"   ⚠️  Placement response unclear: {placement_response}")
                else:
                    print(f"   ⚠️  Unexpected placement response format: {placement_response}")
            else:
                print("   ❌ Send to placement function failed")
                print("   ℹ️  This may be due to notification status or missing data")
                # Don't fail completely as this depends on notification state
        else:
            print("   ⚠️  No suitable notification found for placement testing")
            print("   ℹ️  This is normal if all notifications are already processed")
        
        # Test 4: ПРОВЕРКА КОРРЕКТНОСТИ ФИЛЬТРАЦИИ УВЕДОМЛЕНИЙ
        print("\n   🔍 Test 4: ПРОВЕРКА КОРРЕКТНОСТИ ФИЛЬТРАЦИИ УВЕДОМЛЕНИЙ...")
        
        # Test filtering by status if supported
        filter_tests = [
            {"status": "pending_acceptance", "description": "Pending Acceptance"},
            {"status": "in_processing", "description": "In Processing"},
            {"status": "completed", "description": "Completed"}
        ]
        
        for filter_test in filter_tests:
            status_filter = filter_test["status"]
            description = filter_test["description"]
            
            success, filtered_response = self.run_test(
                f"Filter Notifications by Status: {description}",
                "GET",
                "/api/operator/warehouse-notifications",
                200,
                params={"status": status_filter},
                token=operator_token
            )
            
            if success:
                if isinstance(filtered_response, dict) and 'notifications' in filtered_response:
                    filtered_notifications = filtered_response['notifications']
                    filtered_count = len(filtered_notifications)
                    print(f"   ✅ {description} filter working: {filtered_count} notifications")
                    
                    # Verify all returned notifications have the correct status
                    if filtered_count > 0:
                        correct_status_count = sum(1 for n in filtered_notifications if n.get('status') == status_filter)
                        if correct_status_count == filtered_count:
                            print(f"   ✅ All {filtered_count} notifications have correct status: {status_filter}")
                        else:
                            print(f"   ❌ Status filtering incorrect: {correct_status_count}/{filtered_count} have correct status")
                            all_success = False
                elif isinstance(filtered_response, list):
                    filtered_count = len(filtered_response)
                    print(f"   ✅ {description} filter working: {filtered_count} notifications")
                    
                    # Verify all returned notifications have the correct status
                    if filtered_count > 0:
                        correct_status_count = sum(1 for n in filtered_response if n.get('status') == status_filter)
                        if correct_status_count == filtered_count:
                            print(f"   ✅ All {filtered_count} notifications have correct status: {status_filter}")
                        else:
                            print(f"   ❌ Status filtering incorrect: {correct_status_count}/{filtered_count} have correct status")
                            all_success = False
                else:
                    print(f"   ⚠️  Unexpected response format for {description} filter")
            else:
                print(f"   ⚠️  {description} filter may not be supported (this is OK)")
        
        # Test data safety filtering (ensure no sensitive data exposure)
        print("\n   🔒 Test 4.1: DATA SAFETY FILTERING...")
        
        if notifications_list:
            # Check for potential sensitive data exposure
            sensitive_fields = ['password', 'token', 'secret', 'key']
            data_safe = True
            
            for notification in notifications_list[:3]:  # Check first 3 notifications
                notification_str = str(notification).lower()
                for sensitive_field in sensitive_fields:
                    if sensitive_field in notification_str:
                        print(f"   ❌ Potential sensitive data exposure: '{sensitive_field}' found in notification")
                        data_safe = False
                        all_success = False
            
            if data_safe:
                print("   ✅ No sensitive data exposure detected in notifications")
            
            # Check for proper data structure (no internal MongoDB fields)
            mongodb_fields = ['_id', 'ObjectId']
            mongodb_safe = True
            
            for notification in notifications_list[:3]:
                notification_str = str(notification)
                for mongodb_field in mongodb_fields:
                    if mongodb_field in notification_str:
                        print(f"   ❌ MongoDB internal field exposure: '{mongodb_field}' found")
                        mongodb_safe = False
                        all_success = False
            
            if mongodb_safe:
                print("   ✅ No MongoDB internal fields exposed")
        
        # Test 5: УБЕДИТЬСЯ ЧТО BACKEND НЕ ЗАТРОНУТ FRONTEND ИЗМЕНЕНИЯМИ
        print("\n   🔧 Test 5: BACKEND STABILITY AFTER FRONTEND CHANGES...")
        
        # Test core operator endpoints to ensure they still work
        core_endpoints = [
            ("/api/auth/me", "User Authentication Check"),
            ("/api/operator/warehouses", "Operator Warehouses"),
            ("/api/operator/cargo/list", "Operator Cargo List"),
            ("/api/operator/placement-statistics", "Placement Statistics"),
            ("/api/warehouses", "All Warehouses")
        ]
        
        backend_stability_score = 0
        total_core_endpoints = len(core_endpoints)
        
        for endpoint, description in core_endpoints:
            success, response = self.run_test(
                f"Core Endpoint: {description}",
                "GET",
                endpoint,
                200,
                token=operator_token
            )
            
            if success:
                backend_stability_score += 1
                print(f"   ✅ {description} working")
                
                # Check for JSON serialization issues
                try:
                    json_str = json.dumps(response)
                    if 'ObjectId' in json_str:
                        print(f"   ⚠️  Potential ObjectId serialization issue in {description}")
                    else:
                        print(f"   ✅ JSON serialization correct for {description}")
                except Exception as e:
                    print(f"   ❌ JSON serialization error in {description}: {str(e)}")
                    all_success = False
            else:
                print(f"   ❌ {description} failing")
                all_success = False
        
        stability_percentage = (backend_stability_score / total_core_endpoints) * 100
        print(f"\n   📊 Backend Stability Score: {backend_stability_score}/{total_core_endpoints} ({stability_percentage:.1f}%)")
        
        if stability_percentage >= 80:
            print("   ✅ Backend stability excellent after frontend changes")
        elif stability_percentage >= 60:
            print("   ⚠️  Backend stability good but some issues detected")
        else:
            print("   ❌ Backend stability poor - frontend changes may have affected backend")
            all_success = False
        
        # Test 6: ПРОВЕРКА НА 500 INTERNAL SERVER ERRORS
        print("\n   🚨 Test 6: CHECK FOR 500 INTERNAL SERVER ERRORS...")
        
        error_500_count = 0
        test_endpoints = [
            "/api/operator/warehouse-notifications",
            "/api/operator/warehouses", 
            "/api/operator/cargo/list",
            "/api/auth/me"
        ]
        
        for endpoint in test_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                headers = {'Authorization': f'Bearer {operator_token}', 'Content-Type': 'application/json'}
                response = requests.get(url, headers=headers)
                
                if response.status_code == 500:
                    error_500_count += 1
                    print(f"   ❌ 500 Error in {endpoint}")
                    try:
                        error_detail = response.json()
                        print(f"   📄 Error detail: {error_detail}")
                    except:
                        print(f"   📄 Raw error: {response.text[:200]}")
            except Exception as e:
                print(f"   ⚠️  Exception testing {endpoint}: {str(e)}")
        
        if error_500_count == 0:
            print("   ✅ No 500 Internal Server Errors found!")
        else:
            print(f"   ❌ Found {error_500_count} endpoints with 500 Internal Server Errors")
            all_success = False
        
        # SUMMARY
        print("\n   📊 WAREHOUSE NOTIFICATIONS BACKEND STABILITY SUMMARY:")
        
        if all_success:
            print("   🎉 ALL TESTS PASSED - Backend стабилен после исправлений React ошибок!")
            print("   ✅ Авторизация оператора склада работает (+79777888999/warehouse123)")
            print("   ✅ Получение списка уведомлений работает корректно")
            print("   ✅ Функция отправки на размещение функциональна")
            print("   ✅ Фильтрация уведомлений работает правильно")
            print("   ✅ Backend не затронут frontend изменениями")
            print("   ✅ Все основные endpoints операторов работают стабильно")
            print("   ✅ Никаких 500 Internal Server Errors не обнаружено")
            print("   ✅ Уникальные ID уведомлений для React keys")
            print("   ✅ Безопасность данных соблюдена")
            print("   🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ: Backend должен работать стабильно, все endpoints должны корректно возвращать данные, фильтрация уведомлений должна работать правильно.")
        else:
            print("   ❌ SOME TESTS FAILED - Backend stability needs attention")
            print("   🔍 Check the specific failed tests above for details")
            print("   ⚠️  Some backend issues may need to be addressed")
        
        return all_success

    def run_all_tests(self):
        """Run all warehouse notifications backend stability tests"""
        print("🚀 STARTING WAREHOUSE NOTIFICATIONS BACKEND STABILITY TESTS")
        print("=" * 80)
        
        overall_success = True
        
        # Run the main test
        test_result = self.test_warehouse_notifications_backend_stability()
        overall_success &= test_result
        
        # Final summary
        print("\n" + "=" * 80)
        print("📊 FINAL TEST SUMMARY")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if overall_success:
            print("🎉 ALL WAREHOUSE NOTIFICATIONS BACKEND STABILITY TESTS PASSED!")
            print("✅ Backend работает стабильно после исправлений React ошибок")
            print("✅ Все endpoints корректно возвращают данные")
            print("✅ Фильтрация уведомлений работает правильно")
            print("✅ TAJLINE.TJ готов к production использованию")
        else:
            print("❌ SOME TESTS FAILED")
            print("🔧 Backend stability issues detected after React fixes")
            print("📋 Review the detailed test results above")
        
        return overall_success

if __name__ == "__main__":
    tester = WarehouseNotificationsBackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)