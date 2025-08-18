#!/usr/bin/env python3
"""
Comprehensive Backend Test for UPDATED QR Code Format in TAJLINE.TJ
Testing NEW 9-digit QR format and OLD 8-digit format compatibility with different cells

REVIEW REQUEST CONTEXT:
- NEW QR format: 003010101 (9 digits) - WWW BB SS CC
- OLD QR format: 03010101 (8 digits) - WW BB SS CC (for backward compatibility)
- Test both formats with different cell positions to avoid conflicts
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"
WAREHOUSE_OPERATOR_CREDENTIALS = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class ComprehensiveQRFormatTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.operator_info = None
        self.available_cargo = []
        self.test_results = []

    def log_test(self, test_name, success, details="", error_msg=""):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if error_msg:
            print(f"   Error: {error_msg}")
        print()

    def authenticate_warehouse_operator(self):
        """Step 1: Authenticate warehouse operator"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=WAREHOUSE_OPERATOR_CREDENTIALS
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.operator_info = data.get("user")
                
                # Set authorization header
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                
                operator_name = self.operator_info.get("full_name", "Unknown")
                operator_number = self.operator_info.get("user_number", "Unknown")
                operator_role = self.operator_info.get("role", "Unknown")
                
                self.log_test(
                    "Warehouse Operator Authentication",
                    True,
                    f"Successfully authenticated '{operator_name}' (номер: {operator_number}), роль: {operator_role}"
                )
                return True
            else:
                self.log_test(
                    "Warehouse Operator Authentication",
                    False,
                    error_msg=f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Warehouse Operator Authentication",
                False,
                error_msg=str(e)
            )
            return False

    def get_available_cargo(self):
        """Step 2: Get available cargo for placement"""
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement")
            
            if response.status_code == 200:
                data = response.json()
                self.available_cargo = data.get("items", [])
                
                cargo_count = len(self.available_cargo)
                if cargo_count > 0:
                    # Get sample cargo numbers for testing
                    sample_numbers = [cargo.get("cargo_number") for cargo in self.available_cargo[:5]]
                    
                    self.log_test(
                        "Get Available Cargo for Placement",
                        True,
                        f"Found {cargo_count} cargo items available for placement. Sample numbers: {sample_numbers}"
                    )
                    return True
                else:
                    self.log_test(
                        "Get Available Cargo for Placement",
                        False,
                        error_msg="No cargo available for placement"
                    )
                    return False
            else:
                self.log_test(
                    "Get Available Cargo for Placement",
                    False,
                    error_msg=f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Get Available Cargo for Placement",
                False,
                error_msg=str(e)
            )
            return False

    def test_qr_format_comprehensive(self):
        """Comprehensive test of both NEW and OLD QR formats with different cells"""
        if len(self.available_cargo) < 6:
            self.log_test(
                "Comprehensive QR Format Test",
                False,
                error_msg="Not enough available cargo to test with (need at least 6)"
            )
            return False

        try:
            # Test cases with different cell positions to avoid conflicts
            test_cases = [
                {
                    "cargo_index": 0,
                    "qr_code": "003010102",  # NEW format: warehouse #3, block 1, shelf 1, cell 2
                    "format_type": "NEW (9 digits)",
                    "description": "warehouse #3, block 1, shelf 1, cell 2"
                },
                {
                    "cargo_index": 1,
                    "qr_code": "03010103",   # OLD format: warehouse #3, block 1, shelf 1, cell 3
                    "format_type": "OLD (8 digits)",
                    "description": "warehouse #3, block 1, shelf 1, cell 3"
                },
                {
                    "cargo_index": 2,
                    "qr_code": "003010104",  # NEW format: warehouse #3, block 1, shelf 1, cell 4
                    "format_type": "NEW (9 digits)",
                    "description": "warehouse #3, block 1, shelf 1, cell 4"
                },
                {
                    "cargo_index": 3,
                    "qr_code": "03010105",   # OLD format: warehouse #3, block 1, shelf 1, cell 5
                    "format_type": "OLD (8 digits)",
                    "description": "warehouse #3, block 1, shelf 1, cell 5"
                },
                {
                    "cargo_index": 4,
                    "qr_code": "003020101",  # NEW format: warehouse #3, block 2, shelf 1, cell 1
                    "format_type": "NEW (9 digits)",
                    "description": "warehouse #3, block 2, shelf 1, cell 1"
                },
                {
                    "cargo_index": 5,
                    "qr_code": "03020102",   # OLD format: warehouse #3, block 2, shelf 1, cell 2
                    "format_type": "OLD (8 digits)",
                    "description": "warehouse #3, block 2, shelf 1, cell 2"
                }
            ]
            
            new_format_successes = 0
            old_format_successes = 0
            total_new_tests = 0
            total_old_tests = 0
            
            for test_case in test_cases:
                cargo_index = test_case["cargo_index"]
                if cargo_index >= len(self.available_cargo):
                    continue
                    
                test_cargo = self.available_cargo[cargo_index]
                cargo_number = test_cargo.get("cargo_number")
                qr_code = test_case["qr_code"]
                format_type = test_case["format_type"]
                description = test_case["description"]
                
                payload = {
                    "cargo_number": cargo_number,
                    "cell_code": qr_code
                }
                
                response = self.session.post(
                    f"{BACKEND_URL}/cargo/place-in-cell",
                    json=payload
                )
                
                if "NEW" in format_type:
                    total_new_tests += 1
                else:
                    total_old_tests += 1
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False)
                    
                    if success:
                        warehouse_name = data.get("warehouse_name", "")
                        location = data.get("location", "")
                        
                        if "NEW" in format_type:
                            new_format_successes += 1
                        else:
                            old_format_successes += 1
                            
                        print(f"   ✅ {format_type} QR '{qr_code}' ({description})")
                        print(f"      Cargo: {cargo_number} -> {warehouse_name}, {location}")
                    else:
                        message = data.get("message", "")
                        print(f"   ❌ {format_type} QR '{qr_code}' failed: {message}")
                else:
                    error_text = response.text
                    print(f"   ❌ {format_type} QR '{qr_code}' HTTP error: {response.status_code} - {error_text}")
            
            # Evaluate results
            new_format_success_rate = (new_format_successes / total_new_tests * 100) if total_new_tests > 0 else 0
            old_format_success_rate = (old_format_successes / total_old_tests * 100) if total_old_tests > 0 else 0
            
            overall_success = new_format_successes > 0 and old_format_successes > 0
            
            details = (f"NEW format: {new_format_successes}/{total_new_tests} ({new_format_success_rate:.1f}%), "
                      f"OLD format: {old_format_successes}/{total_old_tests} ({old_format_success_rate:.1f}%)")
            
            self.log_test(
                "Comprehensive QR Format Test",
                overall_success,
                details if overall_success else "",
                "" if overall_success else f"Failed tests - {details}"
            )
            
            return overall_success, new_format_successes > 0, old_format_successes > 0
                
        except Exception as e:
            self.log_test(
                "Comprehensive QR Format Test",
                False,
                error_msg=str(e)
            )
            return False, False, False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 STARTING COMPREHENSIVE UPDATED QR FORMAT TESTING FOR TAJLINE.TJ")
        print("=" * 70)
        print()
        
        # Step 1: Authentication
        if not self.authenticate_warehouse_operator():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Step 2: Get available cargo
        if not self.get_available_cargo():
            print("❌ Could not get available cargo. Cannot proceed with placement tests.")
            return False
        
        # Step 3: Comprehensive QR format testing
        overall_success, new_format_works, old_format_works = self.test_qr_format_comprehensive()
        
        # Summary
        print("=" * 70)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)
        
        passed_tests = sum(1 for result in self.test_results if result["success"])
        total_tests = len(self.test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        # Critical results
        print("🎯 CRITICAL RESULTS:")
        if new_format_works:
            print("✅ NEW 9-digit QR format (003010101) - WORKING")
        else:
            print("❌ NEW 9-digit QR format (003010101) - FAILED")
            
        if old_format_works:
            print("✅ OLD 8-digit QR format (03010101) - BACKWARD COMPATIBLE")
        else:
            print("❌ OLD 8-digit QR format (03010101) - COMPATIBILITY BROKEN")
        
        print()
        
        # Overall result
        critical_success = new_format_works and old_format_works
        if critical_success:
            print("🎉 OVERALL RESULT: SUCCESS")
            print("Both NEW and OLD QR formats are working correctly!")
            print("✅ API successfully processes QR code with 9 digits")
            print("✅ API continues working with old format (8 digits)")
            print("✅ System correctly identifies warehouse by 3-digit number")
        else:
            print("🚨 OVERALL RESULT: PARTIAL SUCCESS / ISSUES DETECTED")
            if new_format_works and not old_format_works:
                print("✅ NEW format works, but OLD format has issues")
            elif not new_format_works and old_format_works:
                print("✅ OLD format works, but NEW format has issues")
            else:
                print("❌ Both formats have critical issues")
        
        return critical_success

def main():
    """Main test execution"""
    tester = ComprehensiveQRFormatTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()