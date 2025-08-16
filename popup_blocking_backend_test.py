#!/usr/bin/env python3
"""
Backend Stability Testing After Popup Blocking Protection Fixes in TAJLINE.TJ
Tests backend stability after massive fixes for popup blocking protection in all printing functions.

CONTEXT: Fixed 19 places in code where window.open() was used without null checking.
Added protection from popup blocking in all printing functions: invoices, QR codes, labels, 
barcodes, transport lists, invoices, warehouse cell QR codes, bulk QR code printing.

TEST PLAN:
1. Warehouse operator authentication (+79777888999/warehouse123)
2. Core API endpoints stability check
3. Printing and QR code related endpoints testing
4. /api/operator/warehouse-notifications endpoints
5. QR code endpoints (/api/cargo/{id}/qr-code)
6. Placement statistics endpoints (/api/operator/placement-statistics)
7. Ensure backend is not affected by frontend changes
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class PopupBlockingBackendTester:
    def __init__(self):
        # Use the backend URL from frontend/.env
        self.base_url = "https://cargo-tracker-29.preview.emergentagent.com"
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"🎯 TAJLINE.TJ Backend Stability Testing After Popup Blocking Protection Fixes")
        print(f"📡 Base URL: {self.base_url}")
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
                response = requests.put(url, json=data, headers=headers)
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

    def test_warehouse_operator_authentication(self):
        """Test warehouse operator authentication (+79777888999/warehouse123)"""
        print("\n🔐 WAREHOUSE OPERATOR AUTHENTICATION TESTING")
        print("   🎯 Testing warehouse operator login (+79777888999/warehouse123)")
        
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
            print(f"   🔑 JWT Token received: {operator_token[:50]}...")
            
            # Verify role is warehouse_operator
            if operator_role == 'warehouse_operator':
                print("   ✅ Operator role correctly set to 'warehouse_operator'")
            else:
                print(f"   ❌ Operator role incorrect: expected 'warehouse_operator', got '{operator_role}'")
                return False
            
            self.tokens['warehouse_operator'] = operator_token
            self.users['warehouse_operator'] = operator_user
            return True
        else:
            print("   ❌ Operator login failed - no access token received")
            print(f"   📄 Response: {login_response}")
            return False

    def test_core_api_endpoints_stability(self):
        """Test core API endpoints stability"""
        print("\n🏗️ CORE API ENDPOINTS STABILITY TESTING")
        print("   🎯 Testing all core API endpoints for operators after popup blocking fixes")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        operator_token = self.tokens['warehouse_operator']
        all_success = True
        
        # Core endpoints that should work after popup blocking fixes
        core_endpoints = [
            ("/api/auth/me", "Get Current User Info"),
            ("/api/operator/warehouses", "Get Operator Warehouses"),
            ("/api/operator/cargo/list", "Get Operator Cargo List"),
            ("/api/operator/placement-statistics", "Get Placement Statistics"),
            ("/api/warehouses", "Get All Warehouses"),
            ("/api/operator/cargo/available-for-placement", "Get Available Cargo for Placement")
        ]
        
        successful_endpoints = 0
        
        for endpoint, description in core_endpoints:
            print(f"\n   🔍 Testing {description} ({endpoint})...")
            
            success, response = self.run_test(
                description,
                "GET",
                endpoint,
                200,
                token=operator_token
            )
            
            if success:
                print(f"   ✅ {description} working")
                successful_endpoints += 1
                
                # Check for JSON serialization issues (no ObjectId errors)
                if isinstance(response, (dict, list)):
                    response_str = str(response)
                    if 'ObjectId' in response_str:
                        print(f"   ⚠️  Potential ObjectId serialization issue in {description}")
                        all_success = False
                    else:
                        print(f"   ✅ JSON serialization correct for {description}")
            else:
                print(f"   ❌ {description} failing")
                all_success = False
        
        success_rate = (successful_endpoints / len(core_endpoints) * 100) if core_endpoints else 0
        print(f"\n   📊 Core Endpoints Success Rate: {successful_endpoints}/{len(core_endpoints)} ({success_rate:.1f}%)")
        
        return all_success

    def test_printing_and_qr_related_endpoints(self):
        """Test printing and QR code related endpoints"""
        print("\n📱 PRINTING AND QR CODE RELATED ENDPOINTS TESTING")
        print("   🎯 Testing endpoints related to printing and QR codes after popup blocking fixes")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        operator_token = self.tokens['warehouse_operator']
        all_success = True
        
        # First, create a test cargo for QR code testing
        print("\n   📦 Creating test cargo for QR code testing...")
        
        cargo_data = {
            "sender_full_name": "Тест Отправитель Popup Blocking",
            "sender_phone": "+79991234567",
            "recipient_full_name": "Тест Получатель Popup Blocking",
            "recipient_phone": "+992987654321",
            "recipient_address": "Душанбе, ул. Popup Blocking, 1",
            "weight": 5.0,
            "cargo_name": "Тестовый груз для popup blocking",
            "declared_value": 2000.0,
            "description": "Тест стабильности backend после исправлений popup blocking",
            "route": "moscow_dushanbe",
            "payment_method": "cash",
            "payment_amount": 2000.0
        }
        
        success, cargo_response = self.run_test(
            "Create Test Cargo for QR Testing",
            "POST",
            "/api/operator/cargo/accept",
            200,
            cargo_data,
            operator_token
        )
        
        test_cargo_number = None
        test_cargo_id = None
        
        if success and 'cargo_number' in cargo_response:
            test_cargo_number = cargo_response['cargo_number']
            test_cargo_id = cargo_response.get('id')
            print(f"   ✅ Test cargo created: {test_cargo_number}")
        else:
            print("   ❌ Failed to create test cargo for QR testing")
            all_success = False
        
        # Test QR code related endpoints
        qr_endpoints_tests = []
        
        if test_cargo_number:
            # Test cargo tracking endpoint (used for QR scanning)
            success, track_response = self.run_test(
                "Cargo Tracking for QR Scanning",
                "GET",
                f"/api/cargo/track/{test_cargo_number}",
                200,
                token=operator_token
            )
            qr_endpoints_tests.append(("Cargo Tracking", success))
            
            if success:
                print(f"   ✅ Cargo tracking working for QR scanning")
                print(f"   📦 Cargo found: {track_response.get('cargo_number', 'N/A')}")
            else:
                print("   ❌ Cargo tracking failed")
                all_success = False
        
        # Test QR scanning endpoint
        if test_cargo_number:
            success, scan_response = self.run_test(
                "QR Code Scanning",
                "POST",
                "/api/cargo/scan-qr",
                200,
                {"qr_text": test_cargo_number},
                operator_token
            )
            qr_endpoints_tests.append(("QR Scanning", success))
            
            if success:
                print(f"   ✅ QR scanning working")
                operations = scan_response.get('available_operations', [])
                print(f"   🔧 Available operations: {operations}")
            else:
                print("   ❌ QR scanning failed")
                all_success = False
        
        # Test placement statistics (used in printing workflows)
        success, stats_response = self.run_test(
            "Placement Statistics for Printing",
            "GET",
            "/api/operator/placement-statistics",
            200,
            token=operator_token
        )
        qr_endpoints_tests.append(("Placement Statistics", success))
        
        if success:
            print(f"   ✅ Placement statistics working")
            operator_name = stats_response.get('operator_name', 'N/A')
            today_placements = stats_response.get('today_placements', 0)
            print(f"   👤 Operator: {operator_name}")
            print(f"   📊 Today placements: {today_placements}")
        else:
            print("   ❌ Placement statistics failed")
            all_success = False
        
        # Summary of QR/Printing related endpoints
        successful_qr_tests = sum(1 for _, success in qr_endpoints_tests if success)
        total_qr_tests = len(qr_endpoints_tests)
        qr_success_rate = (successful_qr_tests / total_qr_tests * 100) if total_qr_tests > 0 else 0
        
        print(f"\n   📊 QR/Printing Endpoints Success Rate: {successful_qr_tests}/{total_qr_tests} ({qr_success_rate:.1f}%)")
        
        return all_success

    def test_warehouse_notifications_endpoints(self):
        """Test /api/operator/warehouse-notifications endpoints"""
        print("\n🔔 WAREHOUSE NOTIFICATIONS ENDPOINTS TESTING")
        print("   🎯 Testing warehouse notifications endpoints after popup blocking fixes")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        operator_token = self.tokens['warehouse_operator']
        all_success = True
        
        # Test getting warehouse notifications
        success, notifications_response = self.run_test(
            "Get Warehouse Notifications",
            "GET",
            "/api/operator/warehouse-notifications",
            200,
            token=operator_token
        )
        
        if success:
            notification_count = len(notifications_response) if isinstance(notifications_response, list) else 0
            print(f"   ✅ Warehouse notifications endpoint working")
            print(f"   📊 Found {notification_count} warehouse notifications")
            
            # Test accepting a notification if available
            if notification_count > 0:
                sample_notification = notifications_response[0]
                notification_id = sample_notification.get('id')
                notification_status = sample_notification.get('status')
                
                print(f"   📋 Sample notification: {notification_id} (status: {notification_status})")
                
                # Only test accept if notification is in pending_acceptance status
                if notification_status == 'pending_acceptance':
                    success_accept, accept_response = self.run_test(
                        "Accept Warehouse Notification",
                        "POST",
                        f"/api/operator/warehouse-notifications/{notification_id}/accept",
                        200,
                        token=operator_token
                    )
                    
                    if success_accept:
                        print(f"   ✅ Notification acceptance working")
                        print(f"   📄 Accept response: {accept_response}")
                    else:
                        print(f"   ❌ Notification acceptance failed")
                        all_success = False
                else:
                    print(f"   ℹ️  Notification not in pending_acceptance status, skipping accept test")
            else:
                print(f"   ℹ️  No notifications available for acceptance testing")
        else:
            print("   ❌ Warehouse notifications endpoint failed")
            all_success = False
        
        return all_success

    def test_cargo_qr_code_endpoints(self):
        """Test /api/cargo/{id}/qr-code endpoints"""
        print("\n🏷️ CARGO QR CODE ENDPOINTS TESTING")
        print("   🎯 Testing cargo QR code generation endpoints after popup blocking fixes")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        operator_token = self.tokens['warehouse_operator']
        all_success = True
        
        # Get available cargo for QR code testing
        success, available_cargo = self.run_test(
            "Get Available Cargo for QR Code Testing",
            "GET",
            "/api/operator/cargo/available-for-placement",
            200,
            token=operator_token
        )
        
        if success:
            cargo_items = available_cargo.get('items', []) if isinstance(available_cargo, dict) else available_cargo if isinstance(available_cargo, list) else []
            cargo_count = len(cargo_items)
            print(f"   ✅ Available cargo endpoint working")
            print(f"   📦 Found {cargo_count} cargo items for QR testing")
            
            if cargo_count > 0:
                # Test QR code generation for first available cargo
                sample_cargo = cargo_items[0]
                cargo_id = sample_cargo.get('id')
                cargo_number = sample_cargo.get('cargo_number')
                
                if cargo_id:
                    print(f"   🏷️ Testing QR code generation for cargo: {cargo_number}")
                    
                    success_qr, qr_response = self.run_test(
                        "Generate Cargo QR Code",
                        "GET",
                        f"/api/cargo/{cargo_id}/qr-code",
                        200,
                        token=operator_token
                    )
                    
                    if success_qr:
                        print(f"   ✅ Cargo QR code generation working")
                        qr_code = qr_response.get('qr_code', '')
                        if qr_code and qr_code.startswith('data:image/png;base64,'):
                            print(f"   ✅ QR code format correct (base64 PNG)")
                        else:
                            print(f"   ❌ QR code format incorrect")
                            all_success = False
                    else:
                        print(f"   ❌ Cargo QR code generation failed")
                        all_success = False
                else:
                    print(f"   ⚠️  No cargo ID available for QR testing")
            else:
                print(f"   ℹ️  No cargo available for QR code testing")
        else:
            print("   ❌ Available cargo endpoint failed")
            all_success = False
        
        return all_success

    def test_backend_stability_after_frontend_changes(self):
        """Test that backend is not affected by frontend changes"""
        print("\n🔧 BACKEND STABILITY AFTER FRONTEND CHANGES TESTING")
        print("   🎯 Ensuring backend is not affected by frontend popup blocking fixes")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
        
        operator_token = self.tokens['warehouse_operator']
        all_success = True
        
        # Test session management stability
        print("\n   🔐 Testing session management stability...")
        
        session_tests = []
        
        # Multiple requests with same token to test session stability
        for i in range(3):
            success, me_response = self.run_test(
                f"Session Stability Test {i+1}",
                "GET",
                "/api/auth/me",
                200,
                token=operator_token
            )
            session_tests.append(success)
            
            if success:
                user_role = me_response.get('role')
                print(f"   ✅ Session test {i+1} passed (role: {user_role})")
            else:
                print(f"   ❌ Session test {i+1} failed")
                all_success = False
        
        successful_sessions = sum(session_tests)
        session_success_rate = (successful_sessions / len(session_tests) * 100) if session_tests else 0
        print(f"   📊 Session stability: {successful_sessions}/{len(session_tests)} ({session_success_rate:.1f}%)")
        
        # Test for 500 Internal Server Errors
        print("\n   🚨 Testing for 500 Internal Server Errors...")
        
        error_500_count = 0
        test_endpoints = [
            "/api/auth/me",
            "/api/operator/warehouses", 
            "/api/operator/cargo/list",
            "/api/operator/placement-statistics",
            "/api/warehouses"
        ]
        
        for endpoint in test_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                headers = {'Authorization': f'Bearer {operator_token}', 'Content-Type': 'application/json'}
                response = requests.get(url, headers=headers)
                
                if response.status_code == 500:
                    error_500_count += 1
                    print(f"   ❌ 500 Error in {endpoint}")
                else:
                    print(f"   ✅ No 500 error in {endpoint} (status: {response.status_code})")
            except Exception as e:
                print(f"   ⚠️  Exception testing {endpoint}: {str(e)}")
        
        if error_500_count == 0:
            print("   ✅ No 500 Internal Server Errors found!")
        else:
            print(f"   ❌ Found {error_500_count} endpoints with 500 Internal Server Errors")
            all_success = False
        
        # Test JSON serialization (no ObjectId errors)
        print("\n   🔍 Testing JSON serialization...")
        
        serialization_issues = 0
        for endpoint in test_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                headers = {'Authorization': f'Bearer {operator_token}', 'Content-Type': 'application/json'}
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        json_str = json.dumps(response_data)
                        if 'ObjectId' in json_str:
                            serialization_issues += 1
                            print(f"   ❌ ObjectId serialization issue in {endpoint}")
                        else:
                            print(f"   ✅ JSON serialization correct for {endpoint}")
                    except Exception as e:
                        serialization_issues += 1
                        print(f"   ❌ JSON serialization error in {endpoint}: {str(e)}")
            except Exception as e:
                print(f"   ⚠️  Exception testing serialization for {endpoint}: {str(e)}")
        
        if serialization_issues == 0:
            print("   ✅ All endpoints have correct JSON serialization!")
        else:
            print(f"   ❌ Found {serialization_issues} endpoints with JSON serialization issues")
            all_success = False
        
        return all_success

    def run_comprehensive_test(self):
        """Run comprehensive backend stability test"""
        print("\n🎯 STARTING COMPREHENSIVE BACKEND STABILITY TEST")
        print("   📋 Testing backend stability after popup blocking protection fixes")
        
        test_results = []
        
        # Test 1: Warehouse Operator Authentication
        print("\n" + "="*80)
        result1 = self.test_warehouse_operator_authentication()
        test_results.append(("Warehouse Operator Authentication", result1))
        
        if not result1:
            print("\n❌ CRITICAL: Cannot proceed without operator authentication")
            return False
        
        # Test 2: Core API Endpoints Stability
        print("\n" + "="*80)
        result2 = self.test_core_api_endpoints_stability()
        test_results.append(("Core API Endpoints Stability", result2))
        
        # Test 3: Printing and QR Related Endpoints
        print("\n" + "="*80)
        result3 = self.test_printing_and_qr_related_endpoints()
        test_results.append(("Printing and QR Related Endpoints", result3))
        
        # Test 4: Warehouse Notifications Endpoints
        print("\n" + "="*80)
        result4 = self.test_warehouse_notifications_endpoints()
        test_results.append(("Warehouse Notifications Endpoints", result4))
        
        # Test 5: Cargo QR Code Endpoints
        print("\n" + "="*80)
        result5 = self.test_cargo_qr_code_endpoints()
        test_results.append(("Cargo QR Code Endpoints", result5))
        
        # Test 6: Backend Stability After Frontend Changes
        print("\n" + "="*80)
        result6 = self.test_backend_stability_after_frontend_changes()
        test_results.append(("Backend Stability After Frontend Changes", result6))
        
        # Final Summary
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE BACKEND STABILITY TEST SUMMARY")
        print("="*80)
        
        successful_tests = sum(1 for _, result in test_results if result)
        total_tests = len(test_results)
        overall_success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Individual Test Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        print(f"   Test Categories Passed: {successful_tests}/{total_tests}")
        print(f"   Overall Success Rate: {overall_success_rate:.1f}%")
        
        print(f"\n📋 DETAILED RESULTS:")
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status} - {test_name}")
        
        if overall_success_rate >= 90:
            print(f"\n🎉 EXCELLENT: Backend stability confirmed after popup blocking fixes!")
            print(f"   ✅ Warehouse operator authentication working (+79777888999/warehouse123)")
            print(f"   ✅ Core API endpoints stable")
            print(f"   ✅ Printing and QR code related endpoints functional")
            print(f"   ✅ Warehouse notifications endpoints working")
            print(f"   ✅ Cargo QR code endpoints operational")
            print(f"   ✅ Backend not affected by frontend changes")
            print(f"   🎯 EXPECTED RESULT ACHIEVED: Backend should work stably after popup blocking fixes")
        elif overall_success_rate >= 70:
            print(f"\n⚠️  GOOD: Most backend functionality stable with minor issues")
            print(f"   🔍 Check specific failed tests above for details")
        else:
            print(f"\n❌ CRITICAL: Significant backend stability issues detected")
            print(f"   🚨 Immediate attention required for failed tests")
        
        return overall_success_rate >= 90

if __name__ == "__main__":
    tester = PopupBlockingBackendTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print(f"\n🎉 SUCCESS: Backend stability confirmed after popup blocking protection fixes!")
        sys.exit(0)
    else:
        print(f"\n❌ FAILURE: Backend stability issues detected after popup blocking fixes!")
        sys.exit(1)