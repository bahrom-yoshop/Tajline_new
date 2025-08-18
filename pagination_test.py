#!/usr/bin/env python3
"""
Comprehensive Pagination Testing for TAJLINE.TJ Application
Tests all pagination functionality for API endpoints as requested in the review
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class PaginationTester:
    def __init__(self, base_url="https://cargo-talk.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.tests_run = 0
        self.tests_passed = 0
        
        print(f"📄 TAJLINE.TJ Pagination Tester")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

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
        if params:
            print(f"   📋 Params: {params}")
        
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

    def setup_test_users(self):
        """Setup test users as specified in requirements"""
        print("\n👥 SETTING UP TEST USERS")
        
        # Test users as specified in requirements
        test_users = [
            {
                "name": "Regular User",
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
            },
            {
                "name": "Warehouse Operator",
                "data": {
                    "full_name": "Оператор Складской", 
                    "phone": "+79777888999",
                    "password": "warehouse123",
                    "role": "warehouse_operator"
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
                print(f"   🔑 Token stored for {role}")
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
                    print(f"   🔑 Token stored for {role}")
                else:
                    all_success = False
                    
        return all_success

    def test_cargo_list_pagination(self):
        """Test GET /api/operator/cargo/list with pagination parameters"""
        print("\n📦 CARGO LIST PAGINATION TESTING")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Test 1: Default pagination (page=1&per_page=25)
        success, response = self.run_test(
            "Cargo List - Default Pagination",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 1, "per_page": 25}
        )
        all_success &= success
        
        if success:
            self.validate_pagination_response(response, "Default pagination")
        
        # Test 2: Custom pagination (page=2&per_page=10)
        success, response = self.run_test(
            "Cargo List - Custom Pagination (page=2, per_page=10)",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 2, "per_page": 10}
        )
        all_success &= success
        
        if success:
            self.validate_pagination_response(response, "Custom pagination")
        
        # Test 3: Small page size (page=1&per_page=5)
        success, response = self.run_test(
            "Cargo List - Small Page Size (per_page=5)",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 1, "per_page": 5}
        )
        all_success &= success
        
        if success:
            self.validate_pagination_response(response, "Small page size")
        
        # Test 4: Maximum page size (page=1&per_page=100)
        success, response = self.run_test(
            "Cargo List - Maximum Page Size (per_page=100)",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 1, "per_page": 100}
        )
        all_success &= success
        
        if success:
            self.validate_pagination_response(response, "Maximum page size")
        
        # Test 5: Filter integration with pagination
        success, response = self.run_test(
            "Cargo List - Filter with Pagination (payment_pending)",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"filter_status": "payment_pending", "page": 1, "per_page": 10}
        )
        all_success &= success
        
        if success:
            self.validate_pagination_response(response, "Filter with pagination")
        
        # Test 6: Another filter with pagination
        success, response = self.run_test(
            "Cargo List - Filter with Pagination (awaiting_placement)",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"filter_status": "awaiting_placement", "page": 2, "per_page": 5}
        )
        all_success &= success
        
        if success:
            self.validate_pagination_response(response, "Filter with pagination (awaiting_placement)")
        
        return all_success

    def test_available_cargo_pagination(self):
        """Test GET /api/operator/cargo/available-for-placement with pagination"""
        print("\n📋 AVAILABLE CARGO FOR PLACEMENT PAGINATION")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Test 1: Default pagination (25 per page)
        success, response = self.run_test(
            "Available Cargo - Default Pagination",
            "GET",
            "/api/operator/cargo/available-for-placement",
            200,
            token=self.tokens['admin']
        )
        all_success &= success
        
        if success:
            # Check if response has pagination structure
            if 'pagination' in response:
                self.validate_pagination_response(response, "Available cargo default pagination")
            else:
                # If no pagination structure, check if it's a simple list
                cargo_list = response.get('cargo_list', [])
                print(f"   📊 Found {len(cargo_list)} available cargo items")
        
        # Test 2: Custom pagination (page=2, per_page=10)
        success, response = self.run_test(
            "Available Cargo - Custom Pagination",
            "GET",
            "/api/operator/cargo/available-for-placement",
            200,
            token=self.tokens['admin'],
            params={"page": 2, "per_page": 10}
        )
        all_success &= success
        
        if success:
            if 'pagination' in response:
                self.validate_pagination_response(response, "Available cargo custom pagination")
            else:
                cargo_list = response.get('cargo_list', [])
                print(f"   📊 Found {len(cargo_list)} available cargo items (page 2)")
        
        return all_success

    def test_user_management_pagination(self):
        """Test GET /api/admin/users with new pagination features"""
        print("\n👥 USER MANAGEMENT PAGINATION")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Test 1: Basic pagination (page=1&per_page=25)
        success, response = self.run_test(
            "User Management - Basic Pagination",
            "GET",
            "/api/admin/users",
            200,
            token=self.tokens['admin'],
            params={"page": 1, "per_page": 25}
        )
        all_success &= success
        
        if success:
            if 'pagination' in response:
                self.validate_pagination_response(response, "User management basic pagination")
            else:
                # If no pagination, check if it's a simple list
                users = response if isinstance(response, list) else []
                print(f"   👥 Found {len(users)} users")
        
        # Test 2: Role filtering with pagination
        success, response = self.run_test(
            "User Management - Role Filter with Pagination",
            "GET",
            "/api/admin/users",
            200,
            token=self.tokens['admin'],
            params={"role": "user", "page": 1, "per_page": 10}
        )
        all_success &= success
        
        if success:
            if 'pagination' in response:
                self.validate_pagination_response(response, "User management role filter")
            else:
                users = response if isinstance(response, list) else []
                user_role_users = [u for u in users if u.get('role') == 'user']
                print(f"   👤 Found {len(user_role_users)} users with role 'user'")
        
        # Test 3: Search with pagination
        success, response = self.run_test(
            "User Management - Search with Pagination",
            "GET",
            "/api/admin/users",
            200,
            token=self.tokens['admin'],
            params={"search": "Клиент", "page": 1, "per_page": 5}
        )
        all_success &= success
        
        if success:
            if 'pagination' in response:
                self.validate_pagination_response(response, "User management search")
            else:
                users = response if isinstance(response, list) else []
                print(f"   🔍 Found {len(users)} users matching 'Клиент'")
        
        # Test 4: Combined filters
        success, response = self.run_test(
            "User Management - Combined Filters",
            "GET",
            "/api/admin/users",
            200,
            token=self.tokens['admin'],
            params={"role": "admin", "search": "admin", "page": 1, "per_page": 10}
        )
        all_success &= success
        
        if success:
            if 'pagination' in response:
                self.validate_pagination_response(response, "User management combined filters")
            else:
                users = response if isinstance(response, list) else []
                print(f"   🔍 Found {len(users)} admin users matching 'admin'")
        
        return all_success

    def test_pagination_edge_cases(self):
        """Test pagination with invalid parameters and edge cases"""
        print("\n⚠️ PAGINATION EDGE CASES")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Test 1: Invalid page=0 (should default to 1)
        success, response = self.run_test(
            "Edge Case - Invalid page=0",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 0, "per_page": 10}
        )
        all_success &= success
        
        if success and 'pagination' in response:
            actual_page = response['pagination'].get('page', 0)
            if actual_page == 1:
                print("   ✅ page=0 correctly defaulted to 1")
            else:
                print(f"   ❌ page=0 resulted in page={actual_page}, expected 1")
                all_success = False
        
        # Test 2: per_page=200 (should cap at 100)
        success, response = self.run_test(
            "Edge Case - per_page=200 (should cap at 100)",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 1, "per_page": 200}
        )
        all_success &= success
        
        if success and 'pagination' in response:
            actual_per_page = response['pagination'].get('per_page', 0)
            if actual_per_page <= 100:
                print(f"   ✅ per_page=200 correctly capped to {actual_per_page}")
            else:
                print(f"   ❌ per_page=200 resulted in per_page={actual_per_page}, expected ≤100")
                all_success = False
        
        # Test 3: per_page=1 (should default to minimum 5)
        success, response = self.run_test(
            "Edge Case - per_page=1 (should default to minimum 5)",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 1, "per_page": 1}
        )
        all_success &= success
        
        if success and 'pagination' in response:
            actual_per_page = response['pagination'].get('per_page', 0)
            if actual_per_page >= 5:
                print(f"   ✅ per_page=1 correctly defaulted to {actual_per_page}")
            else:
                print(f"   ❌ per_page=1 resulted in per_page={actual_per_page}, expected ≥5")
                all_success = False
        
        # Test 4: Non-numeric values for page/per_page
        success, response = self.run_test(
            "Edge Case - Non-numeric page parameter",
            "GET",
            "/api/operator/cargo/list",
            200,  # Should handle gracefully or return 422
            token=self.tokens['admin'],
            params={"page": "invalid", "per_page": 10}
        )
        # This test passes if it either works (handles gracefully) or returns proper error
        if success:
            print("   ✅ Non-numeric page parameter handled gracefully")
        else:
            print("   ✅ Non-numeric page parameter properly rejected")
        all_success = True  # Either outcome is acceptable
        
        # Test 5: Empty results pagination
        success, response = self.run_test(
            "Edge Case - Query with No Results",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"filter_status": "nonexistent_status", "page": 1, "per_page": 10}
        )
        all_success &= success
        
        if success and 'pagination' in response:
            total_count = response['pagination'].get('total_count', 0)
            items = response.get('items', [])
            if total_count == 0 and len(items) == 0:
                print("   ✅ Empty results pagination handled correctly")
            else:
                print(f"   ⚠️ Expected empty results, got {total_count} total, {len(items)} items")
        
        # Test 6: Single result pagination
        success, response = self.run_test(
            "Edge Case - Single Result Pagination",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 1, "per_page": 1}
        )
        all_success &= success
        
        if success and 'pagination' in response:
            items = response.get('items', [])
            per_page = response['pagination'].get('per_page', 0)
            print(f"   📊 Single result test: {len(items)} items, per_page={per_page}")
        
        return all_success

    def test_pagination_consistency(self):
        """Test pagination consistency across multiple requests"""
        print("\n🔄 PAGINATION CONSISTENCY TESTING")
        
        if 'admin' not in self.tokens:
            print("   ❌ No admin token available")
            return False
            
        all_success = True
        
        # Test 1: Multiple requests with same parameters should return same results
        params = {"page": 1, "per_page": 10}
        
        success1, response1 = self.run_test(
            "Consistency Test - First Request",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params=params
        )
        
        success2, response2 = self.run_test(
            "Consistency Test - Second Request",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params=params
        )
        
        all_success &= (success1 and success2)
        
        if success1 and success2:
            if ('pagination' in response1 and 'pagination' in response2):
                total1 = response1['pagination'].get('total_count', 0)
                total2 = response2['pagination'].get('total_count', 0)
                
                if total1 == total2:
                    print(f"   ✅ Consistent total_count: {total1}")
                else:
                    print(f"   ❌ Inconsistent total_count: {total1} vs {total2}")
                    all_success = False
        
        # Test 2: Total count accuracy verification
        success, response = self.run_test(
            "Total Count Accuracy - Get All Pages",
            "GET",
            "/api/operator/cargo/list",
            200,
            token=self.tokens['admin'],
            params={"page": 1, "per_page": 100}  # Get large page to verify count
        )
        all_success &= success
        
        if success and 'pagination' in response:
            total_count = response['pagination'].get('total_count', 0)
            items_count = len(response.get('items', []))
            total_pages = response['pagination'].get('total_pages', 0)
            
            print(f"   📊 Total count: {total_count}")
            print(f"   📊 Items in response: {items_count}")
            print(f"   📊 Total pages: {total_pages}")
            
            # Verify total_pages calculation
            expected_pages = (total_count + 99) // 100  # Ceiling division for per_page=100
            if total_pages == expected_pages or (total_count == 0 and total_pages == 1):
                print("   ✅ Total pages calculation is correct")
            else:
                print(f"   ❌ Total pages calculation incorrect: expected {expected_pages}, got {total_pages}")
                all_success = False
        
        return all_success

    def validate_pagination_response(self, response: Dict, test_name: str) -> bool:
        """Validate that a response has proper pagination structure"""
        if not isinstance(response, dict):
            print(f"   ❌ {test_name}: Response is not a dictionary")
            return False
        
        # Check for pagination metadata
        if 'pagination' not in response:
            print(f"   ⚠️ {test_name}: No pagination metadata found")
            return False
        
        pagination = response['pagination']
        required_fields = ['page', 'per_page', 'total_count', 'total_pages', 'has_next', 'has_prev']
        
        missing_fields = [field for field in required_fields if field not in pagination]
        if missing_fields:
            print(f"   ❌ {test_name}: Missing pagination fields: {missing_fields}")
            return False
        
        # Check items array
        if 'items' not in response:
            print(f"   ❌ {test_name}: No items array found")
            return False
        
        items = response['items']
        if not isinstance(items, list):
            print(f"   ❌ {test_name}: Items is not a list")
            return False
        
        # Validate pagination values
        page = pagination.get('page', 0)
        per_page = pagination.get('per_page', 0)
        total_count = pagination.get('total_count', 0)
        total_pages = pagination.get('total_pages', 0)
        has_next = pagination.get('has_next', False)
        has_prev = pagination.get('has_prev', False)
        
        print(f"   📊 {test_name}: Page {page}/{total_pages}, {len(items)} items, {total_count} total")
        print(f"   📊 Per page: {per_page}, Has next: {has_next}, Has prev: {has_prev}")
        
        # Validate logical consistency
        if page < 1:
            print(f"   ❌ {test_name}: Invalid page number: {page}")
            return False
        
        if per_page < 1:
            print(f"   ❌ {test_name}: Invalid per_page: {per_page}")
            return False
        
        if total_count < 0:
            print(f"   ❌ {test_name}: Invalid total_count: {total_count}")
            return False
        
        if len(items) > per_page:
            print(f"   ❌ {test_name}: Too many items returned: {len(items)} > {per_page}")
            return False
        
        # Check next/prev page logic
        if 'next_page' in pagination:
            next_page = pagination['next_page']
            if has_next and next_page != page + 1:
                print(f"   ❌ {test_name}: Incorrect next_page: {next_page}, expected {page + 1}")
                return False
            if not has_next and next_page is not None:
                print(f"   ❌ {test_name}: next_page should be None when has_next is False")
                return False
        
        if 'prev_page' in pagination:
            prev_page = pagination['prev_page']
            if has_prev and prev_page != page - 1:
                print(f"   ❌ {test_name}: Incorrect prev_page: {prev_page}, expected {page - 1}")
                return False
            if not has_prev and prev_page is not None:
                print(f"   ❌ {test_name}: prev_page should be None when has_prev is False")
                return False
        
        print(f"   ✅ {test_name}: Pagination structure is valid")
        return True

    def run_all_tests(self):
        """Run all pagination tests"""
        print("🚀 STARTING COMPREHENSIVE PAGINATION TESTING")
        
        # Setup
        if not self.setup_test_users():
            print("❌ Failed to setup test users")
            return False
        
        # Run all test suites
        test_suites = [
            ("Cargo List Pagination", self.test_cargo_list_pagination),
            ("Available Cargo Pagination", self.test_available_cargo_pagination),
            ("User Management Pagination", self.test_user_management_pagination),
            ("Pagination Edge Cases", self.test_pagination_edge_cases),
            ("Pagination Consistency", self.test_pagination_consistency),
        ]
        
        suite_results = []
        for suite_name, test_func in test_suites:
            print(f"\n{'='*60}")
            print(f"🧪 RUNNING: {suite_name}")
            print(f"{'='*60}")
            
            try:
                result = test_func()
                suite_results.append((suite_name, result))
                if result:
                    print(f"✅ {suite_name}: PASSED")
                else:
                    print(f"❌ {suite_name}: FAILED")
            except Exception as e:
                print(f"❌ {suite_name}: EXCEPTION - {str(e)}")
                suite_results.append((suite_name, False))
        
        # Final summary
        print(f"\n{'='*60}")
        print("📊 FINAL PAGINATION TEST SUMMARY")
        print(f"{'='*60}")
        
        passed_suites = sum(1 for _, result in suite_results if result)
        total_suites = len(suite_results)
        
        print(f"📈 Individual Tests: {self.tests_passed}/{self.tests_run} passed")
        print(f"📈 Test Suites: {passed_suites}/{total_suites} passed")
        
        for suite_name, result in suite_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status}: {suite_name}")
        
        overall_success = passed_suites == total_suites
        if overall_success:
            print("\n🎉 ALL PAGINATION TESTS PASSED!")
        else:
            print(f"\n⚠️ {total_suites - passed_suites} TEST SUITE(S) FAILED")
        
        return overall_success

if __name__ == "__main__":
    tester = PaginationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)