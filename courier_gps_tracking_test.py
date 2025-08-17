#!/usr/bin/env python3
"""
GPS Tracking System Testing for TAJLINE.TJ - Courier Map Display Issue
Testing the "Courier not found" problem when displaying couriers on the map

ДИАГНОСТИКА ПРОБЛЕМЫ КАРТЫ КУРЬЕРОВ:
1. Авторизация администратора (+79999888777/admin123)
2. Протестировать GET /api/admin/couriers/locations - проверить структуру ответа
3. Авторизация оператора (+79777888999/warehouse123)
4. Протестировать GET /api/operator/couriers/locations - проверить структуру ответа
5. Проверить есть ли вообще курьеры с GPS данными в системе
6. Авторизация курьера (+79991234567/courier123)
7. Отправить GPS данные POST /api/courier/location/update для создания тестовых данных
8. Повторно протестировать админ и оператор endpoints

ЦЕЛЬ: Найти причину ошибки "Courier not found" при отображении карты курьеров
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class CourierGPSTrackingTester:
    def __init__(self, base_url="https://freight-hub-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🗺️  TAJLINE.TJ GPS TRACKING SYSTEM TESTER")
        print(f"📡 Base URL: {self.base_url}")
        print(f"🎯 ЦЕЛЬ: Диагностика проблемы 'Courier not found' при отображении курьеров на карте")
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
                    if isinstance(result, dict) and len(str(result)) < 500:
                        print(f"   📄 Response: {result}")
                    elif isinstance(result, list) and len(result) <= 5:
                        print(f"   📄 Response: {result}")
                    else:
                        print(f"   📄 Response: {type(result).__name__} with {len(result) if hasattr(result, '__len__') else 'N/A'} items")
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

    def test_courier_gps_tracking_system(self):
        """Test complete GPS tracking system for courier map display issue"""
        print("\n🗺️  COMPREHENSIVE GPS TRACKING SYSTEM TESTING")
        print("   🎯 Диагностика проблемы 'Courier not found' при отображении курьеров на карте")
        
        all_success = True
        
        # ЭТАП 1: АВТОРИЗАЦИЯ АДМИНИСТРАТОРА (+79999888777/admin123)
        print("\n   👑 ЭТАП 1: АВТОРИЗАЦИЯ АДМИНИСТРАТОРА (+79999888777/admin123)...")
        
        admin_login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        success, login_response = self.run_test(
            "Admin Login Authentication",
            "POST",
            "/api/auth/login",
            200,
            admin_login_data
        )
        all_success &= success
        
        admin_token = None
        if success and 'access_token' in login_response:
            admin_token = login_response['access_token']
            admin_user = login_response.get('user', {})
            admin_role = admin_user.get('role')
            admin_name = admin_user.get('full_name')
            admin_phone = admin_user.get('phone')
            admin_user_number = admin_user.get('user_number')
            
            print(f"   ✅ Admin login successful: {admin_name}")
            print(f"   👑 Role: {admin_role}")
            print(f"   📞 Phone: {admin_phone}")
            print(f"   🆔 User Number: {admin_user_number}")
            
            # Verify role is admin
            if admin_role == 'admin':
                print("   ✅ Admin role correctly verified")
            else:
                print(f"   ❌ Admin role incorrect: expected 'admin', got '{admin_role}'")
                all_success = False
            
            self.tokens['admin'] = admin_token
            self.users['admin'] = admin_user
        else:
            print("   ❌ Admin login failed - cannot proceed with GPS testing")
            return False
        
        # ЭТАП 2: ПРОТЕСТИРОВАТЬ GET /api/admin/couriers/locations - ПРОВЕРИТЬ СТРУКТУРУ ОТВЕТА
        print("\n   🗺️  ЭТАП 2: GET /api/admin/couriers/locations - ПРОВЕРИТЬ СТРУКТУРУ ОТВЕТА...")
        
        success, admin_couriers_response = self.run_test(
            "Admin Get Couriers Locations (Check Structure)",
            "GET",
            "/api/admin/couriers/locations",
            200,
            token=admin_token
        )
        
        admin_couriers_working = success
        admin_couriers_data = admin_couriers_response if success else {}
        
        if success:
            print("   ✅ GET /api/admin/couriers/locations endpoint accessible")
            
            # Analyze response structure
            if isinstance(admin_couriers_response, dict):
                locations = admin_couriers_response.get('locations', [])
                total_count = admin_couriers_response.get('total_count', 0)
                active_couriers = admin_couriers_response.get('active_couriers', 0)
                
                print(f"   📊 Response structure: dict with locations array")
                print(f"   📊 Total count: {total_count}")
                print(f"   📊 Active couriers: {active_couriers}")
                print(f"   📊 Locations found: {len(locations)}")
                
                if len(locations) > 0:
                    print("   ✅ Courier locations data found")
                    sample_location = locations[0]
                    required_fields = ['courier_id', 'courier_name', 'latitude', 'longitude', 'status']
                    missing_fields = [field for field in required_fields if field not in sample_location]
                    
                    if not missing_fields:
                        print("   ✅ Location data structure correct")
                        print(f"   📍 Sample courier: {sample_location.get('courier_name', 'Unknown')}")
                        print(f"   📍 Status: {sample_location.get('status', 'Unknown')}")
                    else:
                        print(f"   ❌ Missing required fields in location data: {missing_fields}")
                        all_success = False
                else:
                    print("   ⚠️  No courier locations found - this may be the root cause of 'Courier not found'")
                    
            elif isinstance(admin_couriers_response, list):
                print(f"   📊 Response structure: direct array with {len(admin_couriers_response)} items")
                if len(admin_couriers_response) > 0:
                    print("   ✅ Courier locations data found")
                else:
                    print("   ⚠️  Empty courier locations array - this may be the root cause")
            else:
                print(f"   ❌ Unexpected response structure: {type(admin_couriers_response)}")
                all_success = False
        else:
            print("   ❌ GET /api/admin/couriers/locations endpoint failed")
            print("   🚨 CRITICAL: Admin cannot access courier locations - this is likely the main issue")
            all_success = False
        
        # ЭТАП 3: АВТОРИЗАЦИЯ ОПЕРАТОРА (+79777888999/warehouse123)
        print("\n   🏭 ЭТАП 3: АВТОРИЗАЦИЯ ОПЕРАТОРА (+79777888999/warehouse123)...")
        
        operator_login_data = {
            "phone": "+79777888999",
            "password": "warehouse123"
        }
        
        success, operator_login_response = self.run_test(
            "Warehouse Operator Login Authentication",
            "POST",
            "/api/auth/login",
            200,
            operator_login_data
        )
        all_success &= success
        
        operator_token = None
        if success and 'access_token' in operator_login_response:
            operator_token = operator_login_response['access_token']
            operator_user = operator_login_response.get('user', {})
            operator_role = operator_user.get('role')
            operator_name = operator_user.get('full_name')
            operator_phone = operator_user.get('phone')
            operator_user_number = operator_user.get('user_number')
            
            print(f"   ✅ Operator login successful: {operator_name}")
            print(f"   👑 Role: {operator_role}")
            print(f"   📞 Phone: {operator_phone}")
            print(f"   🆔 User Number: {operator_user_number}")
            
            # Verify role is warehouse_operator
            if operator_role == 'warehouse_operator':
                print("   ✅ Operator role correctly verified")
            else:
                print(f"   ❌ Operator role incorrect: expected 'warehouse_operator', got '{operator_role}'")
                all_success = False
            
            self.tokens['warehouse_operator'] = operator_token
            self.users['warehouse_operator'] = operator_user
        else:
            print("   ❌ Operator login failed")
            all_success = False
            return False
        
        # ЭТАП 4: ПРОТЕСТИРОВАТЬ GET /api/operator/couriers/locations - ПРОВЕРИТЬ СТРУКТУРУ ОТВЕТА
        print("\n   🗺️  ЭТАП 4: GET /api/operator/couriers/locations - ПРОВЕРИТЬ СТРУКТУРУ ОТВЕТА...")
        
        success, operator_couriers_response = self.run_test(
            "Operator Get Couriers Locations (Check Structure)",
            "GET",
            "/api/operator/couriers/locations",
            200,
            token=operator_token
        )
        
        operator_couriers_working = success
        operator_couriers_data = operator_couriers_response if success else {}
        
        if success:
            print("   ✅ GET /api/operator/couriers/locations endpoint accessible")
            
            # Analyze response structure
            if isinstance(operator_couriers_response, dict):
                locations = operator_couriers_response.get('locations', [])
                total_count = operator_couriers_response.get('total_count', 0)
                active_couriers = operator_couriers_response.get('active_couriers', 0)
                message = operator_couriers_response.get('message', '')
                
                print(f"   📊 Response structure: dict with locations array")
                print(f"   📊 Total count: {total_count}")
                print(f"   📊 Active couriers: {active_couriers}")
                print(f"   📊 Locations found: {len(locations)}")
                if message:
                    print(f"   📄 Message: {message}")
                
                if len(locations) > 0:
                    print("   ✅ Courier locations data found for operator")
                else:
                    print("   ⚠️  No courier locations found for operator - may be due to warehouse isolation")
                    
            elif isinstance(operator_couriers_response, list):
                print(f"   📊 Response structure: direct array with {len(operator_couriers_response)} items")
                if len(operator_couriers_response) > 0:
                    print("   ✅ Courier locations data found for operator")
                else:
                    print("   ⚠️  Empty courier locations array for operator")
            else:
                print(f"   ❌ Unexpected response structure: {type(operator_couriers_response)}")
                all_success = False
        else:
            print("   ❌ GET /api/operator/couriers/locations endpoint failed")
            print("   🚨 CRITICAL: Operator cannot access courier locations")
            all_success = False
        
        # ЭТАП 5: ПРОВЕРИТЬ ЕСТЬ ЛИ ВООБЩЕ КУРЬЕРЫ С GPS ДАННЫМИ В СИСТЕМЕ
        print("\n   🔍 ЭТАП 5: ПРОВЕРИТЬ ЕСТЬ ЛИ КУРЬЕРЫ С GPS ДАННЫМИ В СИСТЕМЕ...")
        
        # Check if there are any couriers in the system at all
        success, all_couriers_response = self.run_test(
            "Check All Couriers in System",
            "GET",
            "/api/admin/couriers",
            200,
            token=admin_token
        )
        
        if success:
            if isinstance(all_couriers_response, list):
                courier_count = len(all_couriers_response)
                print(f"   📊 Total couriers in system: {courier_count}")
                
                if courier_count > 0:
                    print("   ✅ Couriers exist in the system")
                    sample_courier = all_couriers_response[0]
                    print(f"   👤 Sample courier: {sample_courier.get('full_name', 'Unknown')}")
                    print(f"   📞 Phone: {sample_courier.get('phone', 'Unknown')}")
                else:
                    print("   ⚠️  No couriers found in the system")
            elif isinstance(all_couriers_response, dict):
                couriers = all_couriers_response.get('couriers', [])
                courier_count = len(couriers)
                print(f"   📊 Total couriers in system: {courier_count}")
                
                if courier_count > 0:
                    print("   ✅ Couriers exist in the system")
                else:
                    print("   ⚠️  No couriers found in the system")
        else:
            print("   ❌ Cannot check couriers in system")
            # Try alternative endpoint
            success, alt_response = self.run_test(
                "Check Couriers Alternative Endpoint",
                "GET",
                "/api/couriers",
                200,
                token=admin_token
            )
            if success:
                print("   ✅ Alternative couriers endpoint accessible")
            else:
                print("   ❌ No accessible couriers endpoint found")
        
        # ЭТАП 6: АВТОРИЗАЦИЯ КУРЬЕРА (+79991234567/courier123)
        print("\n   🚚 ЭТАП 6: АВТОРИЗАЦИЯ КУРЬЕРА (+79991234567/courier123)...")
        
        courier_login_data = {
            "phone": "+79991234567",
            "password": "courier123"
        }
        
        success, courier_login_response = self.run_test(
            "Courier Login Authentication",
            "POST",
            "/api/auth/login",
            200,
            courier_login_data
        )
        all_success &= success
        
        courier_token = None
        if success and 'access_token' in courier_login_response:
            courier_token = courier_login_response['access_token']
            courier_user = courier_login_response.get('user', {})
            courier_role = courier_user.get('role')
            courier_name = courier_user.get('full_name')
            courier_phone = courier_user.get('phone')
            courier_user_number = courier_user.get('user_number')
            
            print(f"   ✅ Courier login successful: {courier_name}")
            print(f"   👑 Role: {courier_role}")
            print(f"   📞 Phone: {courier_phone}")
            print(f"   🆔 User Number: {courier_user_number}")
            
            # Verify role is courier
            if courier_role == 'courier':
                print("   ✅ Courier role correctly verified")
            else:
                print(f"   ❌ Courier role incorrect: expected 'courier', got '{courier_role}'")
                all_success = False
            
            self.tokens['courier'] = courier_token
            self.users['courier'] = courier_user
        else:
            print("   ❌ Courier login failed")
            all_success = False
            return False
        
        # ЭТАП 7: ОТПРАВИТЬ GPS ДАННЫЕ POST /api/courier/location/update ДЛЯ СОЗДАНИЯ ТЕСТОВЫХ ДАННЫХ
        print("\n   📍 ЭТАП 7: ОТПРАВИТЬ GPS ДАННЫЕ POST /api/courier/location/update...")
        
        # Send GPS location data
        gps_data = {
            "latitude": 55.7558,  # Moscow Red Square coordinates
            "longitude": 37.6176,
            "status": "online",
            "current_address": "Москва, Красная площадь",
            "accuracy": 10.5,
            "speed": 0.0,
            "heading": 0.0
        }
        
        success, location_update_response = self.run_test(
            "Send GPS Location Data (Create Test Data)",
            "POST",
            "/api/courier/location/update",
            200,
            gps_data,
            courier_token
        )
        all_success &= success
        
        location_id = None
        if success:
            print("   ✅ GPS location data sent successfully")
            location_id = location_update_response.get('location_id')
            message = location_update_response.get('message', '')
            
            if location_id:
                print(f"   📍 Location ID generated: {location_id}")
            if message:
                print(f"   📄 Response message: {message}")
                
            # Verify GPS data structure
            required_response_fields = ['location_id', 'message']
            missing_fields = [field for field in required_response_fields if field not in location_update_response]
            
            if not missing_fields:
                print("   ✅ GPS location update response structure correct")
            else:
                print(f"   ❌ Missing fields in GPS response: {missing_fields}")
                all_success = False
        else:
            print("   ❌ Failed to send GPS location data")
            print("   🚨 CRITICAL: Cannot create test GPS data")
            all_success = False
        
        # Check courier location status
        print("\n   📊 ПРОВЕРКА СТАТУСА МЕСТОПОЛОЖЕНИЯ КУРЬЕРА...")
        
        success, location_status_response = self.run_test(
            "Check Courier Location Status",
            "GET",
            "/api/courier/location/status",
            200,
            token=courier_token
        )
        
        if success:
            print("   ✅ Courier location status accessible")
            tracking_enabled = location_status_response.get('tracking_enabled')
            current_status = location_status_response.get('current_status')
            current_address = location_status_response.get('current_address')
            
            print(f"   📊 Tracking enabled: {tracking_enabled}")
            print(f"   📊 Current status: {current_status}")
            print(f"   📊 Current address: {current_address}")
        else:
            print("   ❌ Cannot check courier location status")
        
        # ЭТАП 8: ПОВТОРНО ПРОТЕСТИРОВАТЬ АДМИН И ОПЕРАТОР ENDPOINTS
        print("\n   🔄 ЭТАП 8: ПОВТОРНО ПРОТЕСТИРОВАТЬ АДМИН И ОПЕРАТОР ENDPOINTS...")
        
        # Re-test admin endpoint after GPS data creation
        print("\n   👑 ПОВТОРНЫЙ ТЕСТ: GET /api/admin/couriers/locations...")
        
        success, admin_couriers_retest = self.run_test(
            "Admin Get Couriers Locations (After GPS Data)",
            "GET",
            "/api/admin/couriers/locations",
            200,
            token=admin_token
        )
        
        if success:
            print("   ✅ Admin couriers locations endpoint working after GPS data")
            
            if isinstance(admin_couriers_retest, dict):
                locations = admin_couriers_retest.get('locations', [])
                total_count = admin_couriers_retest.get('total_count', 0)
                active_couriers = admin_couriers_retest.get('active_couriers', 0)
                
                print(f"   📊 Updated total count: {total_count}")
                print(f"   📊 Updated active couriers: {active_couriers}")
                print(f"   📊 Updated locations found: {len(locations)}")
                
                if len(locations) > 0:
                    print("   ✅ GPS data now visible to admin!")
                    sample_location = locations[0]
                    print(f"   📍 Sample location: {sample_location.get('courier_name', 'Unknown')} at {sample_location.get('current_address', 'Unknown')}")
                else:
                    print("   ❌ GPS data still not visible to admin - this is the main issue")
                    all_success = False
            else:
                print(f"   ❌ Unexpected response format: {type(admin_couriers_retest)}")
                all_success = False
        else:
            print("   ❌ Admin couriers locations endpoint still failing")
            all_success = False
        
        # Re-test operator endpoint after GPS data creation
        print("\n   🏭 ПОВТОРНЫЙ ТЕСТ: GET /api/operator/couriers/locations...")
        
        success, operator_couriers_retest = self.run_test(
            "Operator Get Couriers Locations (After GPS Data)",
            "GET",
            "/api/operator/couriers/locations",
            200,
            token=operator_token
        )
        
        if success:
            print("   ✅ Operator couriers locations endpoint working after GPS data")
            
            if isinstance(operator_couriers_retest, dict):
                locations = operator_couriers_retest.get('locations', [])
                total_count = operator_couriers_retest.get('total_count', 0)
                active_couriers = operator_couriers_retest.get('active_couriers', 0)
                message = operator_couriers_retest.get('message', '')
                
                print(f"   📊 Updated total count: {total_count}")
                print(f"   📊 Updated active couriers: {active_couriers}")
                print(f"   📊 Updated locations found: {len(locations)}")
                if message:
                    print(f"   📄 Message: {message}")
                
                if len(locations) > 0:
                    print("   ✅ GPS data now visible to operator!")
                else:
                    print("   ⚠️  GPS data still not visible to operator - may be due to warehouse assignment")
            else:
                print(f"   ❌ Unexpected response format: {type(operator_couriers_retest)}")
                all_success = False
        else:
            print("   ❌ Operator couriers locations endpoint still failing")
            all_success = False
        
        # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: ПРОВЕРИТЬ ПРАВА ДОСТУПА ДЛЯ РАЗНЫХ РОЛЕЙ
        print("\n   🔐 ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: ПРОВЕРИТЬ ПРАВА ДОСТУПА...")
        
        # Test access control for different roles
        roles_to_test = [
            ('admin', admin_token, "Admin"),
            ('warehouse_operator', operator_token, "Warehouse Operator"),
            ('courier', courier_token, "Courier")
        ]
        
        for role_key, token, role_name in roles_to_test:
            if token:
                print(f"\n   🔍 Testing {role_name} access to courier locations...")
                
                success, role_response = self.run_test(
                    f"{role_name} Access to Courier Locations",
                    "GET",
                    "/api/admin/couriers/locations",
                    200 if role_key in ['admin'] else 403,  # Only admin should have access
                    token=token
                )
                
                if role_key == 'admin':
                    if success:
                        print(f"   ✅ {role_name} has correct access")
                    else:
                        print(f"   ❌ {role_name} should have access but doesn't")
                        all_success = False
                else:
                    if not success:
                        print(f"   ✅ {role_name} correctly denied access")
                    else:
                        print(f"   ⚠️  {role_name} has unexpected access")
        
        # ФИНАЛЬНАЯ ДИАГНОСТИКА: ПРОВЕРИТЬ СТРУКТУРУ ВОЗВРАЩАЕМЫХ ДАННЫХ
        print("\n   📊 ФИНАЛЬНАЯ ДИАГНОСТИКА: СТРУКТУРА ДАННЫХ...")
        
        if admin_couriers_retest and isinstance(admin_couriers_retest, dict):
            print("   🔍 Analyzing final admin response structure...")
            
            # Check if response has the expected structure
            expected_structure = {
                'locations': list,
                'total_count': int,
                'active_couriers': int
            }
            
            structure_valid = True
            for field_name, expected_type in expected_structure.items():
                if field_name in admin_couriers_retest:
                    field_value = admin_couriers_retest[field_name]
                    if isinstance(field_value, expected_type):
                        print(f"   ✅ {field_name}: {field_value} ({type(field_value).__name__})")
                    else:
                        print(f"   ❌ {field_name}: expected {expected_type.__name__}, got {type(field_value).__name__}")
                        structure_valid = False
                else:
                    print(f"   ❌ Missing field: {field_name}")
                    structure_valid = False
            
            if structure_valid:
                print("   ✅ Response structure is correct")
                
                # Check locations array structure
                locations = admin_couriers_retest.get('locations', [])
                if locations and len(locations) > 0:
                    sample_location = locations[0]
                    location_fields = ['courier_id', 'courier_name', 'latitude', 'longitude', 'status', 'current_address']
                    
                    print("   🔍 Checking location data structure...")
                    for field in location_fields:
                        if field in sample_location:
                            print(f"   ✅ {field}: {sample_location[field]}")
                        else:
                            print(f"   ❌ Missing location field: {field}")
                            structure_valid = False
                            
                    if structure_valid:
                        print("   ✅ Location data structure is correct")
                    else:
                        print("   ❌ Location data structure has issues")
                        all_success = False
                else:
                    print("   ⚠️  No location data to analyze structure")
            else:
                print("   ❌ Response structure has issues")
                all_success = False
        
        # SUMMARY AND DIAGNOSIS
        print("\n" + "="*80)
        print("📊 GPS TRACKING SYSTEM DIAGNOSIS SUMMARY")
        print("="*80)
        
        print(f"\n🔍 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО:")
        print(f"   📈 Tests Run: {self.tests_run}")
        print(f"   ✅ Tests Passed: {self.tests_passed}")
        print(f"   📊 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        print(f"\n🎯 ДИАГНОСТИКА ПРОБЛЕМЫ 'Courier not found':")
        
        # Analyze the root cause
        if admin_couriers_working and admin_couriers_data:
            locations_count = 0
            if isinstance(admin_couriers_data, dict):
                locations_count = len(admin_couriers_data.get('locations', []))
            elif isinstance(admin_couriers_data, list):
                locations_count = len(admin_couriers_data)
            
            if locations_count > 0:
                print("   ✅ ПРОБЛЕМА РЕШЕНА: Курьеры теперь видны на карте")
                print(f"   📍 Найдено {locations_count} местоположений курьеров")
                print("   🎉 GPS tracking система работает корректно")
            else:
                print("   ❌ ПРОБЛЕМА ОСТАЕТСЯ: Курьеры не найдены")
                print("   🔍 Возможные причины:")
                print("     - Курьеры не отправляют GPS данные")
                print("     - Проблема с сохранением GPS данных в базе")
                print("     - Проблема с фильтрацией данных по складам")
        else:
            print("   ❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Admin endpoint не работает")
            print("   🚨 Основная причина 'Courier not found'")
        
        if operator_couriers_working and operator_couriers_data:
            locations_count = 0
            if isinstance(operator_couriers_data, dict):
                locations_count = len(operator_couriers_data.get('locations', []))
            elif isinstance(operator_couriers_data, list):
                locations_count = len(operator_couriers_data)
            
            if locations_count > 0:
                print("   ✅ Операторы могут видеть курьеров")
            else:
                print("   ⚠️  Операторы не видят курьеров (возможно из-за изоляции складов)")
        else:
            print("   ❌ Операторы не могут получить данные курьеров")
        
        print(f"\n🔧 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
        if not admin_couriers_working:
            print("   1. Исправить endpoint GET /api/admin/couriers/locations")
            print("   2. Проверить права доступа администратора")
            print("   3. Проверить сериализацию MongoDB ObjectId")
        
        if not operator_couriers_working:
            print("   4. Исправить endpoint GET /api/operator/couriers/locations")
            print("   5. Проверить систему привязки операторов к складам")
        
        if location_id:
            print("   ✅ GPS данные успешно отправляются курьерами")
        else:
            print("   6. Проверить endpoint POST /api/courier/location/update")
        
        print(f"\n🎯 ЗАКЛЮЧЕНИЕ:")
        if all_success:
            print("   🎉 GPS TRACKING СИСТЕМА РАБОТАЕТ КОРРЕКТНО!")
            print("   ✅ Проблема 'Courier not found' решена")
            print("   ✅ Все endpoints функционируют правильно")
            print("   ✅ Структура данных корректна")
        else:
            print("   ❌ GPS TRACKING СИСТЕМА ИМЕЕТ ПРОБЛЕМЫ")
            print("   🔍 Требуется дополнительная диагностика и исправления")
            print("   📋 Проверьте детали тестирования выше")
        
        return all_success

def main():
    """Main function to run GPS tracking tests"""
    tester = CourierGPSTrackingTester()
    
    try:
        # Run comprehensive GPS tracking system test
        success = tester.test_courier_gps_tracking_system()
        
        print(f"\n{'='*80}")
        if success:
            print("🎉 ALL GPS TRACKING TESTS PASSED!")
            print("✅ Courier map display issue diagnosed and resolved")
            sys.exit(0)
        else:
            print("❌ SOME GPS TRACKING TESTS FAILED")
            print("🔍 Check the detailed results above for specific issues")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed with exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()