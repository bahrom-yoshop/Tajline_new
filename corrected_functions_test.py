#!/usr/bin/env python3
"""
CORRECTED FUNCTIONS TESTING for TAJLINE.TJ Application
Tests the FIXED cargo numbering system (2501XX format) and FIXED unpaid orders API
Based on review request for testing corrected implementations
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class CorrectedFunctionsTester:
    def __init__(self, base_url="https://cargo-system-debug.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.cargo_numbers = []
        self.unpaid_orders = []
        
        print(f"🔧 CORRECTED FUNCTIONS TESTER - TAJLINE.TJ")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 70)

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
                response = requests.delete(url, headers=headers)

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

    def setup_test_users(self):
        """Setup test users for testing"""
        print("\n👥 SETTING UP TEST USERS")
        
        # Test users as specified in requirements
        test_users = [
            {
                "name": "Bahrom Client User",
                "data": {
                    "full_name": "Бахром Клиент",
                    "phone": "+992900000000",
                    "password": "123456",
                    "role": "user"
                }
            },
            {
                "name": "Administrator", 
                "data": {
                    "full_name": "Админ Системы",
                    "phone": "+79999888777",
                    "password": "admin123",
                    "role": "admin"
                }
            }
        ]
        
        all_success = True
        for user_info in test_users:
            # Try login first (user might already exist)
            success, response = self.run_test(
                f"Login {user_info['name']}", 
                "POST", 
                "/api/auth/login", 
                200,
                {"phone": user_info['data']['phone'], "password": user_info['data']['password']}
            )
            
            if success and 'access_token' in response:
                role = user_info['data']['role']
                self.tokens[role] = response['access_token']
                self.users[role] = response['user']
                print(f"   🔑 Logged in existing {role}")
            else:
                # Try registration if login failed
                success, response = self.run_test(
                    f"Register {user_info['name']}", 
                    "POST", 
                    "/api/auth/register", 
                    200, 
                    user_info['data']
                )
                
                if success and 'access_token' in response:
                    role = user_info['data']['role']
                    self.tokens[role] = response['access_token']
                    self.users[role] = response['user']
                    print(f"   🔑 Registered new {role}")
                else:
                    all_success = False
                    
        return all_success

    def test_corrected_cargo_numbering_system(self):
        """Test the CORRECTED cargo numbering system - should start with 2501 (January 2025)"""
        print("\n🔢 TESTING CORRECTED CARGO NUMBERING SYSTEM (2501XX FORMAT)")
        print("   Expected: Numbers starting with 2501 (January 2025)")
        print("   Format: 6-10 digits total (2501XX to 2501XXXXXX)")
        
        if 'user' not in self.tokens or 'admin' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        generated_numbers = []
        
        # Test 1: Create multiple cargo orders to test numbering
        print("\n   📦 Creating cargo orders to test numbering...")
        for i in range(5):
            cargo_data = {
                "recipient_name": f"Получатель Тест {i+1}",
                "recipient_phone": f"+99244455566{i}",
                "route": "moscow_dushanbe",
                "weight": 10.0 + i,
                "cargo_name": f"Тестовый груз {i+1}",
                "description": f"Тестовый груз для проверки номеров {i+1}",
                "declared_value": 5000.0 + (i * 1000),
                "sender_address": f"Москва, ул. Тестовая, {i+1}",
                "recipient_address": f"Душанбе, ул. Получателя, {i+1}"
            }
            
            success, response = self.run_test(
                f"Create Cargo Order #{i+1}",
                "POST",
                "/api/cargo/create",
                200,
                cargo_data,
                self.tokens['user']
            )
            all_success &= success
            
            if success and 'cargo_number' in response:
                cargo_number = response['cargo_number']
                generated_numbers.append(cargo_number)
                print(f"   🏷️  Generated: {cargo_number}")
                
                # Verify format: should start with 2501 and be 6-10 digits total
                if cargo_number.startswith('2501'):
                    print(f"   ✅ Starts with 2501 (January 2025): {cargo_number}")
                else:
                    print(f"   ❌ Does NOT start with 2501: {cargo_number}")
                    all_success = False
                
                # Verify length (6-10 digits total)
                if 6 <= len(cargo_number) <= 10:
                    print(f"   ✅ Valid length ({len(cargo_number)} digits): {cargo_number}")
                else:
                    print(f"   ❌ Invalid length ({len(cargo_number)} digits): {cargo_number}")
                    all_success = False
                    
                # Verify all digits
                if cargo_number.isdigit():
                    print(f"   ✅ All digits: {cargo_number}")
                else:
                    print(f"   ❌ Contains non-digits: {cargo_number}")
                    all_success = False
        
        # Test 2: Test operator cargo creation
        print("\n   🏭 Testing operator cargo creation...")
        for i in range(3):
            cargo_data = {
                "sender_full_name": f"Отправитель Оператор {i+1}",
                "sender_phone": f"+79111222{333+i}",
                "recipient_full_name": f"Получатель Оператор {i+1}",
                "recipient_phone": f"+99277788{899+i}",
                "recipient_address": f"Душанбе, ул. Операторская, {i+1}",
                "weight": 20.0 + i,
                "cargo_name": f"Груз оператора {i+1}",
                "declared_value": 8000.0 + (i * 500),
                "description": f"Груз оператора для тестирования номеров {i+1}",
                "route": "moscow_dushanbe"
            }
            
            success, response = self.run_test(
                f"Operator Cargo Creation #{i+1}",
                "POST",
                "/api/operator/cargo/accept",
                200,
                cargo_data,
                self.tokens['admin']
            )
            all_success &= success
            
            if success and 'cargo_number' in response:
                cargo_number = response['cargo_number']
                generated_numbers.append(cargo_number)
                print(f"   🏷️  Operator Generated: {cargo_number}")
                
                # Same format checks
                if cargo_number.startswith('2501'):
                    print(f"   ✅ Starts with 2501: {cargo_number}")
                else:
                    print(f"   ❌ Does NOT start with 2501: {cargo_number}")
                    all_success = False
        
        # Test 3: Verify uniqueness
        print("\n   🔍 Testing number uniqueness...")
        unique_numbers = set(generated_numbers)
        if len(unique_numbers) == len(generated_numbers):
            print(f"   ✅ All {len(generated_numbers)} numbers are unique")
        else:
            print(f"   ❌ Found duplicates! Generated: {len(generated_numbers)}, Unique: {len(unique_numbers)}")
            all_success = False
        
        # Test 4: Verify format compliance summary
        print("\n   📊 FORMAT COMPLIANCE SUMMARY:")
        format_compliant = 0
        for number in generated_numbers:
            if (number.startswith('2501') and 
                6 <= len(number) <= 10 and 
                number.isdigit()):
                format_compliant += 1
        
        compliance_rate = (format_compliant / len(generated_numbers)) * 100 if generated_numbers else 0
        print(f"   📈 Format compliance: {format_compliant}/{len(generated_numbers)} ({compliance_rate:.1f}%)")
        
        if compliance_rate == 100.0:
            print(f"   ✅ 100% format compliance - CORRECTED system working!")
        else:
            print(f"   ❌ {100-compliance_rate:.1f}% format non-compliance - system needs fixing")
            all_success = False
        
        # Store numbers for later tests
        self.cargo_numbers = generated_numbers
        
        return all_success

    def test_corrected_unpaid_orders_system(self):
        """Test the CORRECTED unpaid orders system with JSON body for mark-paid"""
        print("\n💰 TESTING CORRECTED UNPAID ORDERS SYSTEM")
        print("   Expected: POST /api/admin/unpaid-orders/{order_id}/mark-paid")
        print("   Body: {\"payment_method\": \"cash\"}")
        
        if 'user' not in self.tokens or 'admin' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # Step 1: Create cargo request from Bahrom user
        print("\n   📋 Step 1: Creating cargo request from Bahrom user...")
        request_data = {
            "recipient_full_name": "Получатель Заявки Бахром",
            "recipient_phone": "+992555666777",
            "recipient_address": "Душанбе, ул. Заявочная, 1",
            "pickup_address": "Москва, ул. Забора, 1",
            "cargo_name": "Заявочный груз Бахром",
            "weight": 15.0,
            "declared_value": 7000.0,
            "description": "Груз из заявки пользователя Бахром",
            "route": "moscow_dushanbe"
        }
        
        success, request_response = self.run_test(
            "Bahrom Creates Cargo Request",
            "POST",
            "/api/user/cargo-request",
            200,
            request_data,
            self.tokens['user']
        )
        all_success &= success
        
        request_id = None
        if success and 'id' in request_response:
            request_id = request_response['id']
            print(f"   📋 Created cargo request: {request_id}")
        else:
            print("   ❌ Failed to create cargo request")
            return False
        
        # Step 2: Admin accepts the request (creates unpaid order)
        print("\n   👑 Step 2: Admin accepts request (creates unpaid order)...")
        success, accept_response = self.run_test(
            "Admin Accepts Cargo Request",
            "POST",
            f"/api/admin/cargo-requests/{request_id}/accept",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        cargo_number = None
        if success and 'cargo_number' in accept_response:
            cargo_number = accept_response['cargo_number']
            print(f"   🏷️  Created cargo: {cargo_number}")
            print(f"   💰 Amount: {accept_response.get('amount', 'N/A')} руб")
        else:
            print("   ❌ Failed to accept cargo request")
            return False
        
        # Step 3: Get unpaid orders to find our order
        print("\n   📊 Step 3: Getting unpaid orders...")
        success, unpaid_orders = self.run_test(
            "Get Unpaid Orders",
            "GET",
            "/api/admin/unpaid-orders",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        target_order_id = None
        if success and isinstance(unpaid_orders, list):
            print(f"   📋 Found {len(unpaid_orders)} unpaid orders")
            
            # Find our order by cargo number
            for order in unpaid_orders:
                if order.get('cargo_number') == cargo_number:
                    target_order_id = order.get('id')
                    print(f"   🎯 Found our order: {target_order_id}")
                    print(f"   💰 Amount: {order.get('amount')} руб")
                    print(f"   👤 Client: {order.get('client_name')}")
                    break
            
            if not target_order_id:
                print("   ❌ Could not find our unpaid order")
                return False
        else:
            print("   ❌ Failed to get unpaid orders")
            return False
        
        # Step 4: Test CORRECTED mark-paid API with JSON body
        print("\n   💳 Step 4: Testing CORRECTED mark-paid API...")
        print("   📝 Using JSON body: {\"payment_method\": \"cash\"}")
        
        payment_data = {
            "payment_method": "cash"
        }
        
        success, payment_response = self.run_test(
            "Mark Order as Paid (CORRECTED API)",
            "POST",
            f"/api/admin/unpaid-orders/{target_order_id}/mark-paid",
            200,
            payment_data,
            self.tokens['admin']
        )
        all_success &= success
        
        if success:
            print(f"   ✅ Successfully marked order as paid!")
            print(f"   📄 Response: {payment_response}")
        else:
            print("   ❌ Failed to mark order as paid - API still has issues")
            return False
        
        # Step 5: Verify order status updated
        print("\n   🔍 Step 5: Verifying order status updated...")
        success, updated_orders = self.run_test(
            "Get Unpaid Orders After Payment",
            "GET",
            "/api/admin/unpaid-orders",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success:
            # Check if our order is still in unpaid list (should not be)
            still_unpaid = False
            for order in updated_orders:
                if order.get('id') == target_order_id:
                    still_unpaid = True
                    break
            
            if not still_unpaid:
                print(f"   ✅ Order successfully removed from unpaid list")
            else:
                print(f"   ❌ Order still appears in unpaid list")
                all_success = False
        
        return all_success

    def test_full_workflow_corrected(self):
        """Test complete workflow with corrected functions"""
        print("\n🔄 TESTING FULL WORKFLOW WITH CORRECTED FUNCTIONS")
        print("   User → Request → Admin Accept → Unpaid Order → Payment → Completion")
        
        if 'user' not in self.tokens or 'admin' not in self.tokens:
            print("   ❌ Required tokens not available")
            return False
            
        all_success = True
        
        # Step 1: User creates request
        print("\n   👤 Step 1: User creates cargo request...")
        request_data = {
            "recipient_full_name": "Получатель Полного Теста",
            "recipient_phone": "+992777888999",
            "recipient_address": "Душанбе, ул. Полного Теста, 1",
            "pickup_address": "Москва, ул. Отправки, 1",
            "cargo_name": "Груз полного теста",
            "weight": 25.0,
            "declared_value": 10000.0,
            "description": "Груз для полного тестирования workflow",
            "route": "moscow_dushanbe"
        }
        
        success, request_response = self.run_test(
            "User Creates Full Workflow Request",
            "POST",
            "/api/user/cargo-request",
            200,
            request_data,
            self.tokens['user']
        )
        all_success &= success
        
        if not success:
            return False
            
        request_id = request_response.get('id')
        print(f"   📋 Created request: {request_id}")
        
        # Step 2: Admin accepts request
        print("\n   👑 Step 2: Admin accepts request...")
        success, accept_response = self.run_test(
            "Admin Accepts Full Workflow Request",
            "POST",
            f"/api/admin/cargo-requests/{request_id}/accept",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if not success:
            return False
            
        cargo_number = accept_response.get('cargo_number')
        print(f"   🏷️  Created cargo: {cargo_number}")
        
        # Verify cargo number format (should be corrected 2501XX format)
        if cargo_number and cargo_number.startswith('2501'):
            print(f"   ✅ Cargo number uses corrected format: {cargo_number}")
        else:
            print(f"   ❌ Cargo number does NOT use corrected format: {cargo_number}")
            all_success = False
        
        # Step 3: Find unpaid order
        print("\n   💰 Step 3: Finding unpaid order...")
        success, unpaid_orders = self.run_test(
            "Get Unpaid Orders for Full Workflow",
            "GET",
            "/api/admin/unpaid-orders",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if not success:
            return False
            
        target_order = None
        for order in unpaid_orders:
            if order.get('cargo_number') == cargo_number:
                target_order = order
                break
        
        if not target_order:
            print("   ❌ Could not find unpaid order for our cargo")
            return False
            
        print(f"   💳 Found unpaid order: {target_order.get('id')}")
        print(f"   💰 Amount: {target_order.get('amount')} руб")
        
        # Step 4: Mark as paid using corrected API
        print("\n   💳 Step 4: Marking as paid with corrected API...")
        payment_data = {
            "payment_method": "cash"
        }
        
        success, payment_response = self.run_test(
            "Mark Full Workflow Order as Paid",
            "POST",
            f"/api/admin/unpaid-orders/{target_order.get('id')}/mark-paid",
            200,
            payment_data,
            self.tokens['admin']
        )
        all_success &= success
        
        if not success:
            return False
            
        print(f"   ✅ Payment processed successfully!")
        
        # Step 5: Verify completion
        print("\n   🔍 Step 5: Verifying workflow completion...")
        
        # Check cargo tracking
        success, cargo_info = self.run_test(
            "Track Completed Cargo",
            "GET",
            f"/api/cargo/track/{cargo_number}",
            200
        )
        all_success &= success
        
        if success:
            print(f"   📦 Cargo status: {cargo_info.get('status')}")
            print(f"   💰 Payment status: {cargo_info.get('payment_status', 'N/A')}")
        
        # Verify order no longer in unpaid list
        success, final_unpaid = self.run_test(
            "Final Check - Unpaid Orders",
            "GET",
            "/api/admin/unpaid-orders",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success:
            still_unpaid = any(order.get('cargo_number') == cargo_number for order in final_unpaid)
            if not still_unpaid:
                print(f"   ✅ Order successfully completed and removed from unpaid list")
            else:
                print(f"   ❌ Order still in unpaid list")
                all_success = False
        
        return all_success

    def test_verification_corrected_functions(self):
        """Final verification that corrected functions work as expected"""
        print("\n✅ VERIFICATION TEST - CORRECTED FUNCTIONS")
        
        all_success = True
        
        # Verification 1: Cargo numbers format
        print("\n   🔢 Verification 1: Cargo Numbers Format")
        if self.cargo_numbers:
            correct_format_count = 0
            for number in self.cargo_numbers:
                if (number.startswith('2501') and 
                    6 <= len(number) <= 10 and 
                    number.isdigit()):
                    correct_format_count += 1
            
            format_percentage = (correct_format_count / len(self.cargo_numbers)) * 100
            print(f"   📊 Correct format: {correct_format_count}/{len(self.cargo_numbers)} ({format_percentage:.1f}%)")
            
            if format_percentage == 100.0:
                print(f"   ✅ All cargo numbers use corrected 2501XX format")
            else:
                print(f"   ❌ Some cargo numbers still use old format")
                all_success = False
        else:
            print(f"   ⚠️  No cargo numbers generated to verify")
        
        # Verification 2: Unpaid orders API
        print("\n   💰 Verification 2: Unpaid Orders API")
        if 'admin' in self.tokens:
            # Test the corrected API endpoint structure
            success, unpaid_orders = self.run_test(
                "Verify Unpaid Orders API Works",
                "GET",
                "/api/admin/unpaid-orders",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print(f"   ✅ GET /api/admin/unpaid-orders works correctly")
                print(f"   📊 Found {len(unpaid_orders)} unpaid orders")
                
                # If we have unpaid orders, test the mark-paid structure
                if unpaid_orders and len(unpaid_orders) > 0:
                    test_order_id = unpaid_orders[0].get('id')
                    print(f"   🧪 Testing mark-paid API structure with order: {test_order_id}")
                    
                    # This should work with JSON body now
                    payment_data = {"payment_method": "cash"}
                    success, _ = self.run_test(
                        "Verify Mark-Paid API Structure",
                        "POST",
                        f"/api/admin/unpaid-orders/{test_order_id}/mark-paid",
                        200,  # Should work now
                        payment_data,
                        self.tokens['admin']
                    )
                    
                    if success:
                        print(f"   ✅ POST mark-paid with JSON body works correctly")
                    else:
                        print(f"   ❌ POST mark-paid with JSON body still has issues")
                        all_success = False
                else:
                    print(f"   ℹ️  No unpaid orders available to test mark-paid API")
            else:
                print(f"   ❌ GET /api/admin/unpaid-orders has issues")
                all_success = False
        
        # Verification 3: Full workflow integration
        print("\n   🔄 Verification 3: Full Workflow Integration")
        print(f"   📊 Tests run: {self.tests_run}")
        print(f"   ✅ Tests passed: {self.tests_passed}")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"   📈 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 90.0:
            print(f"   ✅ High success rate - corrected functions working well")
        else:
            print(f"   ❌ Low success rate - corrected functions need more work")
            all_success = False
        
        return all_success

    def run_all_corrected_tests(self):
        """Run all corrected function tests"""
        print("\n🚀 STARTING CORRECTED FUNCTIONS TESTING")
        
        # Setup
        if not self.setup_test_users():
            print("\n❌ FAILED TO SETUP TEST USERS")
            return False
        
        # Test corrected cargo numbering
        print("\n" + "="*70)
        cargo_numbering_success = self.test_corrected_cargo_numbering_system()
        
        # Test corrected unpaid orders
        print("\n" + "="*70)
        unpaid_orders_success = self.test_corrected_unpaid_orders_system()
        
        # Test full workflow
        print("\n" + "="*70)
        full_workflow_success = self.test_full_workflow_corrected()
        
        # Final verification
        print("\n" + "="*70)
        verification_success = self.test_verification_corrected_functions()
        
        # Summary
        print("\n" + "="*70)
        print("🏁 CORRECTED FUNCTIONS TESTING SUMMARY")
        print("="*70)
        
        results = {
            "Corrected Cargo Numbering (2501XX)": cargo_numbering_success,
            "Corrected Unpaid Orders API": unpaid_orders_success,
            "Full Workflow Integration": full_workflow_success,
            "Final Verification": verification_success
        }
        
        for test_name, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {status} - {test_name}")
        
        overall_success = all(results.values())
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"   Tests run: {self.tests_run}")
        print(f"   Tests passed: {self.tests_passed}")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"   Success rate: {success_rate:.1f}%")
        
        if overall_success:
            print(f"\n🎉 ALL CORRECTED FUNCTIONS WORKING CORRECTLY!")
            print(f"   ✅ Cargo numbers start with 2501 (January 2025)")
            print(f"   ✅ Cargo numbers are 6-10 digits (2501XX - 2501XXXXXX)")
            print(f"   ✅ All cargo numbers are unique")
            print(f"   ✅ Unpaid orders API works with JSON body")
            print(f"   ✅ Full workflow completes successfully")
        else:
            print(f"\n⚠️  SOME CORRECTED FUNCTIONS STILL HAVE ISSUES")
            failed_tests = [name for name, success in results.items() if not success]
            for failed_test in failed_tests:
                print(f"   ❌ {failed_test}")
        
        return overall_success

if __name__ == "__main__":
    tester = CorrectedFunctionsTester()
    success = tester.run_all_corrected_tests()
    sys.exit(0 if success else 1)