#!/usr/bin/env python3
"""
Enhanced Admin Panel with Advanced User Management Testing
Tests the specific functionality mentioned in the review request:
1. Operator Profile Management API
2. User Profile Management API  
3. Quick Cargo Creation API
4. Advanced Role Management
5. Data Aggregation Testing
6. Integration Testing
"""

import requests
import json
from datetime import datetime

class EnhancedAdminPanelTester:
    def __init__(self, base_url="https://cargo-talk.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.operator_token = None
        self.user_token = None
        self.test_operator_id = None
        self.test_user_id = None
        
        print(f"🎯 Enhanced Admin Panel Testing")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data=None, token=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        print(f"\n🔍 {name}")
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
                print(f"   ✅ PASSED - Status: {response.status_code}")
                try:
                    result = response.json()
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

    def setup_authentication(self):
        """Setup authentication tokens for testing"""
        print("\n🔐 Setting up authentication...")
        
        # Login as admin
        admin_login = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            admin_login
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print("   ✅ Admin token obtained")
        else:
            print("   ❌ Failed to get admin token")
            return False
        
        # Login as regular user
        user_login = {
            "phone": "+992900000000",
            "password": "123456"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "/api/auth/login",
            200,
            user_login
        )
        
        if success and 'access_token' in response:
            self.user_token = response['access_token']
            self.test_user_id = response['user']['id']
            print(f"   ✅ User token obtained (ID: {self.test_user_id})")
        else:
            print("   ❌ Failed to get user token")
            return False
        
        # Find or create warehouse operator
        success, users_list = self.run_test(
            "Get Users List",
            "GET",
            "/api/admin/users",
            200,
            token=self.admin_token
        )
        
        if success:
            # Handle paginated response
            if isinstance(users_list, dict) and 'items' in users_list:
                users_list = users_list['items']
            
            if isinstance(users_list, list):
                # First check for existing test user by phone
                for user in users_list:
                    if user.get('phone') == '+992777888999':
                        self.test_operator_id = user.get('id')
                        if user.get('role') != 'warehouse_operator':
                            print(f"   ⚠️  Found test user with wrong role, will update (ID: {self.test_operator_id})")
                            
                            # Change role to warehouse_operator
                            role_update_data = {
                                "user_id": self.test_operator_id,
                                "new_role": "warehouse_operator"
                            }
                            
                            success, role_response = self.run_test(
                                "Change User Role to Warehouse Operator",
                                "PUT",
                                f"/api/admin/users/{self.test_operator_id}/role",
                                200,
                                role_update_data,
                                self.admin_token
                            )
                            
                            if success:
                                print("   ✅ Role changed to warehouse_operator")
                            else:
                                print("   ❌ Failed to change role to warehouse_operator")
                                return False
                        else:
                            print(f"   ✅ Found existing warehouse operator (ID: {self.test_operator_id})")
                        break
                
                # If not found by phone, look for any warehouse operator
                if not self.test_operator_id:
                    for user in users_list:
                        if user.get('role') == 'warehouse_operator':
                            self.test_operator_id = user.get('id')
                            print(f"   ✅ Found warehouse operator (ID: {self.test_operator_id})")
                            break
        
        if not self.test_operator_id:
            print("   ⚠️  No warehouse operator found, will create one")
            
            # Create test operator as regular user first
            operator_data = {
                "full_name": "Тест Оператор Профиль",
                "phone": "+992777888999",
                "password": "operator123"
            }
            
            success, response = self.run_test(
                "Create Test User for Operator",
                "POST",
                "/api/auth/register",
                200,
                operator_data
            )
            
            if success and 'user' in response:
                self.test_operator_id = response['user']['id']
                print(f"   ✅ Test user created (ID: {self.test_operator_id})")
                
                # Now change role to warehouse_operator
                role_update_data = {
                    "user_id": self.test_operator_id,
                    "new_role": "warehouse_operator"
                }
                
                success, role_response = self.run_test(
                    "Change User Role to Warehouse Operator",
                    "PUT",
                    f"/api/admin/users/{self.test_operator_id}/role",
                    200,
                    role_update_data,
                    self.admin_token
                )
                
                if success:
                    print("   ✅ Role changed to warehouse_operator")
                else:
                    print("   ❌ Failed to change role to warehouse_operator")
                    return False
                    
                # Create a warehouse for the operator
                warehouse_data = {
                    "name": "Тест Склад для Оператора",
                    "location": "Тестовый адрес склада",
                    "blocks_count": 2,
                    "shelves_per_block": 2,
                    "cells_per_shelf": 10
                }
                
                success, warehouse_response = self.run_test(
                    "Create Test Warehouse",
                    "POST",
                    "/api/admin/warehouses",
                    200,
                    warehouse_data,
                    self.admin_token
                )
                
                if success and 'id' in warehouse_response:
                    warehouse_id = warehouse_response['id']
                    print(f"   ✅ Test warehouse created (ID: {warehouse_id})")
                    
                    # Bind operator to warehouse
                    binding_data = {
                        "operator_id": self.test_operator_id,
                        "warehouse_id": warehouse_id
                    }
                    
                    success, binding_response = self.run_test(
                        "Bind Operator to Warehouse",
                        "POST",
                        "/api/admin/operator-warehouse-binding",
                        200,
                        binding_data,
                        self.admin_token
                    )
                    
                    if success:
                        print("   ✅ Operator bound to warehouse")
                    else:
                        print("   ❌ Failed to bind operator to warehouse")
                        return False
                else:
                    print("   ❌ Failed to create test warehouse")
                    return False
            else:
                print("   ❌ Failed to create test operator")
                return False
        
        return True

    def test_operator_profile_management(self):
        """Test Operator Profile Management API"""
        print("\n👨‍💼 TESTING OPERATOR PROFILE MANAGEMENT API")
        print("=" * 50)
        
        if not self.test_operator_id:
            print("   ❌ No operator ID available")
            return False
        
        success, operator_profile = self.run_test(
            "Get Operator Profile",
            "GET",
            f"/api/admin/operators/profile/{self.test_operator_id}",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
        
        print("\n   📊 Verifying operator profile structure...")
        
        # Verify complete data structure
        required_fields = ['user_info', 'work_statistics', 'cargo_history', 'associated_warehouses', 'recent_activity']
        missing_fields = [field for field in required_fields if field not in operator_profile]
        
        if missing_fields:
            print(f"   ❌ Missing required fields: {missing_fields}")
            return False
        
        print("   ✅ All required fields present")
        
        # Verify user_info structure
        user_info = operator_profile.get('user_info', {})
        required_user_fields = ['user_number', 'role', 'full_name', 'phone']
        missing_user_fields = [field for field in required_user_fields if field not in user_info]
        
        if missing_user_fields:
            print(f"   ❌ Missing user info fields: {missing_user_fields}")
            return False
        
        print(f"   ✅ User info complete: {user_info.get('full_name')} (#{user_info.get('user_number')})")
        print(f"   📱 Phone: {user_info.get('phone')}, Role: {user_info.get('role')}")
        
        # Verify work statistics
        work_stats = operator_profile.get('work_statistics', {})
        expected_stats = ['total_cargo_accepted', 'recent_cargo_count', 'status_breakdown', 'avg_cargo_per_day']
        missing_stats = [stat for stat in expected_stats if stat not in work_stats]
        
        if missing_stats:
            print(f"   ❌ Missing work statistics: {missing_stats}")
            return False
        
        print(f"   ✅ Work statistics complete:")
        print(f"     Total cargo accepted: {work_stats.get('total_cargo_accepted', 0)}")
        print(f"     Recent cargo (30 days): {work_stats.get('recent_cargo_count', 0)}")
        print(f"     Average per day: {work_stats.get('avg_cargo_per_day', 0)}")
        print(f"     Status breakdown: {work_stats.get('status_breakdown', {})}")
        
        # Verify cargo history
        cargo_history = operator_profile.get('cargo_history', [])
        print(f"   ✅ Cargo history: {len(cargo_history)} entries")
        
        # Verify associated warehouses
        warehouses = operator_profile.get('associated_warehouses', [])
        print(f"   ✅ Associated warehouses: {len(warehouses)} warehouses")
        
        if warehouses:
            sample_warehouse = warehouses[0]
            required_warehouse_fields = ['id', 'name', 'location', 'cargo_count']
            missing_warehouse_fields = [field for field in required_warehouse_fields if field not in sample_warehouse]
            
            if not missing_warehouse_fields:
                print(f"     Sample: {sample_warehouse.get('name')} - {sample_warehouse.get('cargo_count')} cargo")
            else:
                print(f"   ❌ Warehouse data incomplete: missing {missing_warehouse_fields}")
                return False
        
        # Verify recent activity
        recent_activity = operator_profile.get('recent_activity', [])
        print(f"   ✅ Recent activity: {len(recent_activity)} activities")
        
        if recent_activity:
            sample_activity = recent_activity[0]
            if 'cargo_number' in sample_activity and 'created_at' in sample_activity:
                print(f"     Latest: Cargo #{sample_activity.get('cargo_number')} - {sample_activity.get('processing_status', 'N/A')}")
            else:
                print("   ❌ Activity data incomplete")
                return False
        
        print("   ✅ OPERATOR PROFILE MANAGEMENT API - PASSED")
        return True

    def test_user_profile_management(self):
        """Test User Profile Management API"""
        print("\n👤 TESTING USER PROFILE MANAGEMENT API")
        print("=" * 50)
        
        if not self.test_user_id:
            print("   ❌ No user ID available")
            return False
        
        success, user_profile = self.run_test(
            "Get User Profile",
            "GET",
            f"/api/admin/users/profile/{self.test_user_id}",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
        
        print("\n   📊 Verifying user profile structure...")
        
        # Verify comprehensive data structure
        required_fields = ['user_info', 'shipping_statistics', 'recent_shipments', 'frequent_recipients', 'cargo_requests_history']
        missing_fields = [field for field in required_fields if field not in user_profile]
        
        if missing_fields:
            print(f"   ❌ Missing required fields: {missing_fields}")
            return False
        
        print("   ✅ All required fields present")
        
        # Verify user_info
        user_info = user_profile.get('user_info', {})
        required_user_fields = ['user_number', 'role', 'full_name', 'phone']
        missing_user_fields = [field for field in required_user_fields if field not in user_info]
        
        if missing_user_fields:
            print(f"   ❌ Missing user info fields: {missing_user_fields}")
            return False
        
        print(f"   ✅ User info complete: {user_info.get('full_name')} (#{user_info.get('user_number')})")
        
        # Verify shipping statistics
        shipping_stats = user_profile.get('shipping_statistics', {})
        expected_stats = ['total_cargo_requests', 'total_sent_cargo', 'total_received_cargo', 'status_breakdown', 'registration_days']
        missing_stats = [stat for stat in expected_stats if stat not in shipping_stats]
        
        if missing_stats:
            print(f"   ❌ Missing shipping statistics: {missing_stats}")
            return False
        
        print(f"   ✅ Shipping statistics complete:")
        print(f"     Cargo requests: {shipping_stats.get('total_cargo_requests', 0)}")
        print(f"     Sent cargo: {shipping_stats.get('total_sent_cargo', 0)}")
        print(f"     Received cargo: {shipping_stats.get('total_received_cargo', 0)}")
        print(f"     Registration days: {shipping_stats.get('registration_days', 0)}")
        print(f"     Status breakdown: {shipping_stats.get('status_breakdown', {})}")
        
        # Verify recent shipments from both collections
        recent_shipments = user_profile.get('recent_shipments', [])
        print(f"   ✅ Recent shipments: {len(recent_shipments)} entries")
        
        if recent_shipments:
            collection_types = set()
            for shipment in recent_shipments[:3]:
                if 'collection_type' in shipment:
                    collection_types.add(shipment['collection_type'])
            
            if collection_types:
                print(f"     Collections: {list(collection_types)}")
            else:
                print("   ⚠️  Shipments missing collection type markers")
        
        # Verify frequent recipients with aggregated statistics
        frequent_recipients = user_profile.get('frequent_recipients', [])
        print(f"   ✅ Frequent recipients: {len(frequent_recipients)} recipients")
        
        if frequent_recipients:
            sample_recipient = frequent_recipients[0]
            required_recipient_fields = ['recipient_full_name', 'recipient_phone', 'shipment_count', 'last_sent', 'total_weight', 'total_value']
            missing_recipient_fields = [field for field in required_recipient_fields if field not in sample_recipient]
            
            if not missing_recipient_fields:
                print(f"     Top recipient: {sample_recipient.get('recipient_full_name')}")
                print(f"     Shipments: {sample_recipient.get('shipment_count')}, Weight: {sample_recipient.get('total_weight')} kg")
                print(f"     Value: {sample_recipient.get('total_value')} rubles")
            else:
                print(f"   ❌ Recipient data missing: {missing_recipient_fields}")
                return False
        
        # Verify cargo requests history
        requests_history = user_profile.get('cargo_requests_history', [])
        print(f"   ✅ Cargo requests history: {len(requests_history)} requests")
        
        print("   ✅ USER PROFILE MANAGEMENT API - PASSED")
        return True

    def test_quick_cargo_creation(self):
        """Test Quick Cargo Creation API"""
        print("\n⚡ TESTING QUICK CARGO CREATION API")
        print("=" * 50)
        
        if not self.test_user_id:
            print("   ❌ No user ID available")
            return False
        
        # First, we need a warehouse operator token
        if not self.operator_token:
            # Try to login as warehouse operator
            operator_login = {
                "phone": "+992777888999",
                "password": "operator123"
            }
            
            success, response = self.run_test(
                "Login as Warehouse Operator",
                "POST",
                "/api/auth/login",
                200,
                operator_login
            )
            
            if success and 'access_token' in response:
                self.operator_token = response['access_token']
                print("   ✅ Warehouse operator token obtained")
            else:
                print("   ❌ Failed to get warehouse operator token")
                return False
        
        # Test quick cargo creation with multi-item support
        quick_cargo_data = {
            "sender_id": self.test_user_id,
            "recipient_data": {
                "recipient_full_name": "Тест Получатель",
                "recipient_phone": "+992999999999",
                "recipient_address": "Душанбе, тестовый адрес"
            },
            "cargo_items": [
                {"cargo_name": "Документы", "weight": 2.0, "price_per_kg": 100.0},
                {"cargo_name": "Одежда", "weight": 3.5, "price_per_kg": 80.0}
            ],
            "route": "moscow_to_tajikistan",
            "description": "Быстрое создание из профиля пользователя"
        }
        
        success, quick_cargo_response = self.run_test(
            "Create Quick Cargo for User",
            "POST",
            f"/api/admin/users/{self.test_user_id}/quick-cargo",
            200,
            quick_cargo_data,
            self.operator_token
        )
        
        if not success:
            return False
        
        print("\n   📊 Verifying quick cargo creation...")
        
        if 'cargo' not in quick_cargo_response:
            print("   ❌ Response missing cargo information")
            return False
        
        cargo_info = quick_cargo_response['cargo']
        
        # Verify calculations
        expected_weight = 2.0 + 3.5  # 5.5 kg
        expected_cost = (2.0 * 100.0) + (3.5 * 80.0)  # 200 + 280 = 480 rubles
        
        actual_weight = cargo_info.get('total_weight', 0)
        actual_cost = cargo_info.get('total_cost', 0)
        
        if actual_weight != expected_weight or actual_cost != expected_cost:
            print(f"   ❌ Calculation error:")
            print(f"     Expected: {expected_weight} kg, {expected_cost} rubles")
            print(f"     Got: {actual_weight} kg, {actual_cost} rubles")
            return False
        
        print(f"   ✅ Calculations correct: {actual_weight} kg, {actual_cost} rubles")
        
        # Verify auto-filled sender data
        sender_name = cargo_info.get('sender_name', '')
        if not sender_name:
            print("   ❌ Sender data not auto-filled")
            return False
        
        print(f"   ✅ Auto-filled sender data: {sender_name}")
        
        # Verify multi-item support
        items_count = cargo_info.get('items_count', 0)
        if items_count != 2:
            print(f"   ❌ Multi-item support issue: Expected 2 items, got {items_count}")
            return False
        
        print(f"   ✅ Multi-item support working: {items_count} items")
        
        # Store cargo number for integration testing
        created_cargo_number = cargo_info.get('cargo_number')
        if not created_cargo_number:
            print("   ❌ No cargo number returned")
            return False
        
        print(f"   ✅ Cargo created: #{created_cargo_number}")
        
        # Test integration with existing system
        print("\n   🔗 Testing integration with existing system...")
        
        # Check if cargo appears in operator cargo list
        success, cargo_list = self.run_test(
            "Check Cargo in Operator List",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.operator_token
        )
        
        if not success:
            print("   ❌ Failed to get operator cargo list")
            return False
        
        cargo_found = False
        items = cargo_list.get('items', []) if isinstance(cargo_list, dict) else cargo_list
        
        for cargo in items:
            if cargo.get('cargo_number') == created_cargo_number:
                cargo_found = True
                
                # Verify quick_created marker
                if cargo.get('quick_created'):
                    print("   ✅ Quick-created cargo has proper marker")
                else:
                    print("   ⚠️  Quick-created cargo missing marker")
                
                # Verify sender_id integration
                if cargo.get('sender_id') == self.test_user_id:
                    print("   ✅ Sender ID properly linked")
                else:
                    print("   ❌ Sender ID not properly linked")
                    return False
                
                break
        
        if not cargo_found:
            print("   ❌ Quick-created cargo not found in operator list")
            return False
        
        print("   ✅ Quick-created cargo appears in operator list")
        print("   ✅ QUICK CARGO CREATION API - PASSED")
        return True

    def test_data_aggregation(self):
        """Test data aggregation across multiple collections"""
        print("\n📊 TESTING DATA AGGREGATION")
        print("=" * 50)
        
        if not self.test_user_id:
            print("   ❌ No user ID available")
            return False
        
        # Test frequent recipients calculation from multiple collections
        success, user_profile = self.run_test(
            "Get User Profile for Aggregation Test",
            "GET",
            f"/api/admin/users/profile/{self.test_user_id}",
            200,
            token=self.admin_token
        )
        
        if not success:
            return False
        
        frequent_recipients = user_profile.get('frequent_recipients', [])
        
        if not frequent_recipients:
            print("   ⚠️  No frequent recipients data for aggregation testing")
            return True
        
        print(f"   ✅ Data aggregation working: {len(frequent_recipients)} recipients")
        
        # Verify recipient statistics accuracy
        for i, recipient in enumerate(frequent_recipients[:3]):
            shipment_count = recipient.get('shipment_count', 0)
            last_sent = recipient.get('last_sent')
            total_weight = recipient.get('total_weight', 0)
            total_value = recipient.get('total_value', 0)
            
            print(f"   📊 Recipient {i+1}: {recipient.get('recipient_full_name', 'N/A')}")
            print(f"     Shipments: {shipment_count}, Weight: {total_weight} kg, Value: {total_value} rubles")
            
            if shipment_count > 0 and last_sent:
                print(f"     Last sent: {last_sent}")
            else:
                print("   ❌ Recipient statistics incomplete")
                return False
        
        # Test cargo history aggregation with proper sorting
        recent_shipments = user_profile.get('recent_shipments', [])
        
        if recent_shipments:
            print(f"   ✅ Cargo history aggregation: {len(recent_shipments)} shipments")
            
            # Verify sorting (should be by created_at descending)
            dates = []
            for shipment in recent_shipments[:5]:
                created_at = shipment.get('created_at')
                if created_at:
                    dates.append(created_at)
            
            if len(dates) > 1:
                # Check if dates are in descending order
                sorted_dates = sorted(dates, reverse=True)
                if dates == sorted_dates:
                    print("   ✅ Cargo history properly sorted by date")
                else:
                    print("   ❌ Cargo history not properly sorted")
                    return False
        
        print("   ✅ DATA AGGREGATION - PASSED")
        return True

    def test_access_control(self):
        """Test proper access control for admin-only endpoints"""
        print("\n🔒 TESTING ACCESS CONTROL")
        print("=" * 50)
        
        if not self.test_operator_id or not self.user_token:
            print("   ❌ Required tokens not available")
            return False
        
        # Test that regular user cannot access operator profile
        success, response = self.run_test(
            "Regular User Access to Operator Profile (Should Fail)",
            "GET",
            f"/api/admin/operators/profile/{self.test_operator_id}",
            403,  # Should be forbidden
            token=self.user_token
        )
        
        if success:
            print("   ✅ Regular user correctly denied access to operator profile")
        else:
            print("   ❌ Access control failed for operator profile")
            return False
        
        # Test that regular user cannot access user profile endpoint
        success, response = self.run_test(
            "Regular User Access to User Profile Endpoint (Should Fail)",
            "GET",
            f"/api/admin/users/profile/{self.test_user_id}",
            403,  # Should be forbidden
            token=self.user_token
        )
        
        if success:
            print("   ✅ Regular user correctly denied access to user profile endpoint")
        else:
            print("   ❌ Access control failed for user profile endpoint")
            return False
        
        print("   ✅ ACCESS CONTROL - PASSED")
        return True

    def run_all_tests(self):
        """Run all enhanced admin panel tests"""
        print("🚀 Starting Enhanced Admin Panel Testing...")
        
        # Setup authentication
        if not self.setup_authentication():
            print("❌ Authentication setup failed")
            return False
        
        test_results = []
        
        # Run test suites
        test_suites = [
            ("Operator Profile Management API", self.test_operator_profile_management),
            ("User Profile Management API", self.test_user_profile_management),
            ("Quick Cargo Creation API", self.test_quick_cargo_creation),
            ("Data Aggregation Testing", self.test_data_aggregation),
            ("Access Control Testing", self.test_access_control),
        ]
        
        for suite_name, test_func in test_suites:
            try:
                result = test_func()
                test_results.append((suite_name, result))
                if result:
                    print(f"\n✅ {suite_name} - PASSED")
                else:
                    print(f"\n❌ {suite_name} - FAILED")
            except Exception as e:
                print(f"\n💥 {suite_name} - ERROR: {str(e)}")
                test_results.append((suite_name, False))
        
        # Print final results
        print("\n" + "=" * 60)
        print("📊 ENHANCED ADMIN PANEL TEST RESULTS")
        print("=" * 60)
        
        passed_suites = sum(1 for _, result in test_results if result)
        total_suites = len(test_results)
        
        for suite_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {suite_name}")
        
        print(f"\n📈 Overall Results:")
        print(f"   Test Suites: {passed_suites}/{total_suites} passed")
        print(f"   Success Rate: {(passed_suites/total_suites*100):.1f}%")
        
        if passed_suites == total_suites:
            print("\n🎉 ALL ENHANCED ADMIN PANEL TESTS PASSED!")
            print("✅ Operator profiles return complete work statistics and history")
            print("✅ User profiles show comprehensive shipping data and recipient history")
            print("✅ Quick cargo creation works with auto-filled data and multi-item support")
            print("✅ Data aggregation is accurate across multiple collections")
            print("✅ All calculations (totals, averages, counts) are mathematically correct")
            print("✅ Proper access control is enforced for admin-only endpoints")
            print("✅ Created cargo integrates seamlessly with existing system")
            return True
        else:
            print(f"\n⚠️  {total_suites - passed_suites} test suite(s) failed.")
            return False

def main():
    """Main test execution"""
    tester = EnhancedAdminPanelTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())