#!/usr/bin/env python3
"""
TAJLINE.TJ CARGO PLACEMENT SYSTEM DIAGNOSTIC AND RETESTING
Comprehensive diagnostic and retesting of the cargo placement system fixes
"""

import requests
import sys
import json
import random
from datetime import datetime
from typing import Dict, Any, Optional

class TajlinePlacementDiagnostic:
    def __init__(self, base_url="https://tajline-manager-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        
        print("🔍 TAJLINE.TJ CARGO PLACEMENT DIAGNOSTIC & RETESTING")
        print("🎯 Diagnosing and testing fixes for intelligent cargo placement")
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

    def test_authentication_and_roles(self):
        """Test authentication and diagnose user roles"""
        print("\n🔐 AUTHENTICATION AND ROLE DIAGNOSTIC")
        
        # Login with specified credentials
        login_data = [
            {"role": "admin", "phone": "+79999888777", "password": "admin123"},
            {"role": "warehouse_operator", "phone": "+79777888999", "password": "warehouse123"}
        ]
        
        all_success = True
        for login_info in login_data:
            success, response = self.run_test(
                f"Login {login_info['role']}", 
                "POST", 
                "/api/auth/login", 
                200,
                {"phone": login_info['phone'], "password": login_info['password']}
            )
            
            if success and 'access_token' in response:
                self.tokens[login_info['role']] = response['access_token']
                self.users[login_info['role']] = response['user']
                
                user_data = response['user']
                print(f"   🔑 Token stored for {login_info['role']}")
                print(f"   👤 User: {user_data.get('full_name')} ({user_data.get('phone')})")
                print(f"   👑 Role: {user_data.get('role')}")
                print(f"   🆔 User ID: {user_data.get('id')}")
                
                # Check if warehouse operator role is correct
                if login_info['role'] == 'warehouse_operator':
                    actual_role = user_data.get('role')
                    if actual_role != 'warehouse_operator':
                        print(f"   ⚠️  ROLE MISMATCH: Expected 'warehouse_operator', got '{actual_role}'")
                        all_success = False
                    else:
                        print(f"   ✅ Role correctly set as 'warehouse_operator'")
            else:
                all_success = False
                
        return all_success

    def test_field_name_fix(self):
        """Test the fixed field name issue (processing_status vs new_status)"""
        print("\n🔧 FIELD NAME FIX TESTING")
        print("   🎯 Testing fixed processing_status field name")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        # Create test cargo
        test_cargo_data = {
            "sender_full_name": "Field Fix Test",
            "sender_phone": "+79999111111",
            "recipient_full_name": "Получатель Field Fix",
            "recipient_phone": "+992900111111",
            "recipient_address": "Душанбе, ул. Field Fix, 1",
            "cargo_items": [
                {"cargo_name": "Документы", "weight": 10.0, "price_per_kg": 60.0},
                {"cargo_name": "Одежда", "weight": 25.0, "price_per_kg": 60.0},
                {"cargo_name": "Электроника", "weight": 100.0, "price_per_kg": 65.0}
            ],
            "description": "Field name fix test cargo",
            "route": "moscow_dushanbe"
        }
        
        success, cargo_response = self.run_test(
            "Create Test Cargo for Field Fix",
            "POST",
            "/api/operator/cargo/accept",
            200,
            test_cargo_data,
            self.tokens['admin']
        )
        
        if not success or 'id' not in cargo_response:
            print("   ❌ Failed to create test cargo")
            return False
            
        cargo_id = cargo_response['id']
        cargo_number = cargo_response.get('cargo_number', 'N/A')
        print(f"   ✅ Test cargo created: {cargo_number}")
        
        # Test the FIXED field name (processing_status)
        success, status_response = self.run_test(
            "Update Status with Fixed Field Name",
            "PUT",
            f"/api/cargo/{cargo_id}/processing-status",
            200,
            {"processing_status": "paid"},
            self.tokens['admin']
        )
        
        if success:
            print("   ✅ FIELD NAME FIX CONFIRMED - processing_status field works")
            return True
        else:
            print("   ❌ Field name fix not working")
            return False

    def test_warehouse_info_fix(self):
        """Test the fixed warehouse_info field"""
        print("\n🏗️ WAREHOUSE_INFO FIELD FIX TESTING")
        print("   🎯 Testing fixed missing warehouse_info field")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        # Get warehouses list
        success, warehouses = self.run_test(
            "Get Warehouses for Info Test",
            "GET",
            "/api/warehouses",
            200,
            token=self.tokens['admin']
        )
        
        if not success or not isinstance(warehouses, list) or len(warehouses) == 0:
            print("   ❌ No warehouses available for testing")
            return False
            
        warehouse_id = warehouses[0]['id']
        warehouse_name = warehouses[0].get('name', 'Unknown')
        print(f"   🏭 Testing warehouse: {warehouse_name}")
        
        # Test detailed structure with warehouse_info field
        success, structure = self.run_test(
            "Get Detailed Structure with warehouse_info",
            "GET",
            f"/api/warehouses/{warehouse_id}/detailed-structure",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            if 'warehouse_info' in structure:
                warehouse_info = structure['warehouse_info']
                print("   ✅ WAREHOUSE_INFO FIX CONFIRMED - field is present")
                print(f"   📋 Name: {warehouse_info.get('name', 'N/A')}")
                print(f"   📍 Address: {warehouse_info.get('address', 'N/A')}")
                print(f"   📝 Description: {warehouse_info.get('description', 'N/A')}")
                return True
            else:
                print("   ❌ warehouse_info field still missing")
                return False
        else:
            print("   ❌ Failed to get detailed structure")
            return False

    def diagnose_warehouse_operator_permissions(self):
        """Diagnose warehouse operator permissions issues"""
        print("\n🔍 WAREHOUSE OPERATOR PERMISSIONS DIAGNOSTIC")
        
        if 'warehouse_operator' not in self.tokens:
            print("   ❌ No warehouse operator token available")
            return False
            
        # Check user role first
        warehouse_operator_user = self.users.get('warehouse_operator', {})
        actual_role = warehouse_operator_user.get('role')
        user_id = warehouse_operator_user.get('id')
        
        print(f"   👤 Warehouse Operator User ID: {user_id}")
        print(f"   👑 Actual Role: {actual_role}")
        
        if actual_role != 'warehouse_operator':
            print(f"   ❌ CRITICAL ISSUE: User role is '{actual_role}', should be 'warehouse_operator'")
            return False
        
        # Test basic warehouse access
        print("\n   🏭 Testing basic warehouse access...")
        success, warehouses = self.run_test(
            "Warehouse Operator: Get Warehouses",
            "GET",
            "/api/warehouses",
            200,
            token=self.tokens['warehouse_operator']
        )
        
        if success:
            print(f"   ✅ Warehouse operator can access warehouses ({len(warehouses)} found)")
            
            if len(warehouses) > 0:
                # Test available-for-placement with proper warehouse access
                print("\n   📦 Testing available-for-placement access...")
                success, available_cargo = self.run_test(
                    "Warehouse Operator: Available for Placement",
                    "GET",
                    "/api/operator/cargo/available-for-placement",
                    200,
                    token=self.tokens['warehouse_operator']
                )
                
                if success:
                    print("   ✅ PERMISSIONS FIX CONFIRMED - warehouse operator can access available-for-placement")
                    return True
                else:
                    print("   ❌ Warehouse operator still cannot access available-for-placement")
                    return False
            else:
                print("   ⚠️  No warehouses available to operator")
                return False
        else:
            print("   ❌ Warehouse operator cannot access basic warehouses endpoint")
            return False

    def test_complete_placement_workflow(self):
        """Test the complete placement workflow with fixes"""
        print("\n🎯 COMPLETE PLACEMENT WORKFLOW TESTING")
        print("   🎯 Testing end-to-end workflow with all fixes")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        # Step 1: Create cargo with individual pricing (135kg, 8600руб)
        print("\n   📦 Step 1: Creating cargo with individual pricing...")
        
        workflow_cargo_data = {
            "sender_full_name": "Workflow Complete Test",
            "sender_phone": "+79999654321",
            "recipient_full_name": "Получатель Complete",
            "recipient_phone": "+992900654321",
            "recipient_address": "Душанбе, ул. Complete, 1",
            "cargo_items": [
                {"cargo_name": "Документы", "weight": 10.0, "price_per_kg": 60.0},
                {"cargo_name": "Одежда", "weight": 25.0, "price_per_kg": 60.0},
                {"cargo_name": "Электроника", "weight": 100.0, "price_per_kg": 65.0}
            ],
            "description": "Complete workflow test cargo",
            "route": "moscow_dushanbe"
        }
        
        success, cargo_response = self.run_test(
            "Create Complete Workflow Cargo",
            "POST",
            "/api/operator/cargo/accept",
            200,
            workflow_cargo_data,
            self.tokens['admin']
        )
        
        if not success or 'id' not in cargo_response:
            print("   ❌ Failed to create workflow cargo")
            return False
            
        cargo_id = cargo_response['id']
        cargo_number = cargo_response.get('cargo_number', 'N/A')
        total_weight = cargo_response.get('weight', 0)
        total_cost = cargo_response.get('declared_value', 0)
        
        print(f"   ✅ Workflow cargo created: {cargo_number}")
        print(f"   📊 Weight: {total_weight} kg, Cost: {total_cost} руб")
        
        # Verify calculations
        if abs(total_weight - 135.0) < 0.01 and abs(total_cost - 8600.0) < 0.01:
            print("   ✅ Cargo calculations correct (135kg, 8600руб)")
        else:
            print("   ❌ Cargo calculations incorrect")
            return False
        
        # Step 2: Mark as paid using fixed field name
        print("\n   💳 Step 2: Marking cargo as paid using fixed field...")
        
        success, _ = self.run_test(
            "Mark Workflow Cargo as Paid",
            "PUT",
            f"/api/cargo/{cargo_id}/processing-status",
            200,
            {"processing_status": "paid"},
            self.tokens['admin']
        )
        
        if not success:
            print("   ❌ Failed to mark cargo as paid")
            return False
            
        print("   ✅ Cargo marked as paid using fixed field name")
        
        # Step 3: Test warehouse structure with warehouse_info
        print("\n   🏗️ Step 3: Getting warehouse structure with warehouse_info...")
        
        success, warehouses = self.run_test(
            "Get Warehouses for Structure Test",
            "GET",
            "/api/warehouses",
            200,
            token=self.tokens['admin']
        )
        
        if not success or len(warehouses) == 0:
            print("   ❌ No warehouses available")
            return False
            
        warehouse_id = warehouses[0]['id']
        success, structure = self.run_test(
            "Get Warehouse Structure with Info",
            "GET",
            f"/api/warehouses/{warehouse_id}/detailed-structure",
            200,
            token=self.tokens['admin']
        )
        
        if not success:
            print("   ❌ Failed to get warehouse structure")
            return False
            
        if 'warehouse_info' not in structure:
            print("   ❌ warehouse_info field missing from structure")
            return False
            
        print("   ✅ Warehouse structure retrieved with warehouse_info field")
        
        # Step 4: Test cargo placement
        print("\n   📍 Step 4: Testing cargo placement...")
        
        # Get available cells
        success, available_cells = self.run_test(
            "Get Available Cells for Placement",
            "GET",
            f"/api/warehouses/{warehouse_id}/available-cells/1/1",
            200,
            token=self.tokens['admin']
        )
        
        if not success or not isinstance(available_cells, list) or len(available_cells) == 0:
            print("   ❌ No available cells found")
            return False
            
        selected_cell = available_cells[0]
        print(f"   🎯 Selected cell: B{selected_cell.get('block_number')}-S{selected_cell.get('shelf_number')}-C{selected_cell.get('cell_number')}")
        
        # Execute placement
        placement_data = {
            "cargo_id": cargo_id,
            "warehouse_id": warehouse_id,
            "block_number": selected_cell.get('block_number', 1),
            "shelf_number": selected_cell.get('shelf_number', 1),
            "cell_number": selected_cell.get('cell_number', 1)
        }
        
        success, placement_response = self.run_test(
            "Execute Cargo Placement",
            "POST",
            "/api/operator/cargo/place",
            200,
            placement_data,
            self.tokens['admin']
        )
        
        if success:
            print("   ✅ Cargo placement successful")
            print(f"   📍 Location: {placement_response.get('location', 'N/A')}")
            print("   ✅ COMPLETE WORKFLOW SUCCESSFUL")
            return True
        else:
            print("   ❌ Cargo placement failed")
            return False

    def run_comprehensive_diagnostic(self):
        """Run comprehensive diagnostic and retesting"""
        print("\n🚀 STARTING COMPREHENSIVE DIAGNOSTIC AND RETESTING")
        print("=" * 70)
        
        test_results = []
        
        # Test 1: Authentication and roles
        result = self.test_authentication_and_roles()
        test_results.append(("Authentication and Role Diagnostic", result))
        
        if not result:
            print("\n❌ Authentication failed - cannot continue")
            return False
        
        # Test 2: Field name fix
        result = self.test_field_name_fix()
        test_results.append(("Field Name Fix (processing_status)", result))
        
        # Test 3: Warehouse info fix
        result = self.test_warehouse_info_fix()
        test_results.append(("Warehouse Info Fix (warehouse_info field)", result))
        
        # Test 4: Warehouse operator permissions diagnostic
        result = self.diagnose_warehouse_operator_permissions()
        test_results.append(("Warehouse Operator Permissions", result))
        
        # Test 5: Complete workflow
        result = self.test_complete_placement_workflow()
        test_results.append(("Complete Placement Workflow", result))
        
        # Print summary
        print("\n" + "=" * 70)
        print("🏁 COMPREHENSIVE DIAGNOSTIC SUMMARY")
        print("=" * 70)
        
        passed_tests = 0
        critical_fixes = 0
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{status} - {test_name}")
            if result:
                passed_tests += 1
                if "Fix" in test_name or "Workflow" in test_name:
                    critical_fixes += 1
        
        success_rate = (passed_tests / len(test_results)) * 100
        print(f"\n📊 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{len(test_results)} tests passed)")
        print(f"🔧 Individual API Tests: {self.tests_passed}/{self.tests_run} passed")
        print(f"🎯 Critical Fixes Working: {critical_fixes}/3")
        
        # Detailed analysis
        print("\n📋 DETAILED ANALYSIS:")
        
        if critical_fixes >= 2:
            print("✅ MAJOR FIXES CONFIRMED:")
            print("   - Field name fix (processing_status) working")
            print("   - Warehouse info field (warehouse_info) working")
            
            if critical_fixes == 3:
                print("   - Complete workflow functional")
                print("\n🎉 RETESTING SUCCESSFUL - CRITICAL FIXES CONFIRMED!")
            else:
                print("\n⚠️  RETESTING PARTIALLY SUCCESSFUL - Some workflow issues remain")
        else:
            print("❌ CRITICAL FIXES NOT WORKING PROPERLY")
        
        return success_rate >= 80

def main():
    """Main function to run the diagnostic"""
    diagnostic = TajlinePlacementDiagnostic()
    
    try:
        success = diagnostic.run_comprehensive_diagnostic()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Diagnostic failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()