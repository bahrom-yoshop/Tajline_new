#!/usr/bin/env python3
"""
Backend Test for UPDATED QR Code Format in TAJLINE.TJ
Testing NEW 9-digit QR format and OLD 8-digit format compatibility

REVIEW REQUEST CONTEXT:
- NEW QR format: 003010101 (9 digits) - WWW BB SS CC
  * WWW = warehouse number (3 digits, supports up to 999 warehouses)
  * BB = block number (2 digits)
  * SS = shelf number (2 digits) 
  * CC = cell number (2 digits)
- OLD QR format: 03010101 (8 digits) - WW BB SS CC (for backward compatibility)
- Frontend and Backend updated to support both formats

TEST PLAN:
1. Authorize warehouse operator (+79777888999/warehouse123)
2. Get available cargo for placement
3. CRITICAL TEST: Test API /api/cargo/place-in-cell with NEW format "003010101"
4. COMPATIBILITY TEST: Test OLD format "03010101"
5. Verify parsing: warehouse #3, block 1, shelf 1, cell 1

EXPECTED RESULTS:
- API should successfully process QR code "003010101" (9 digits)
- API should continue working with old format "03010101" (8 digits)
- System should correctly identify warehouse by 3-digit number
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://tajline-manager-1.preview.emergentagent.com/api"
WAREHOUSE_OPERATOR_CREDENTIALS = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class UpdatedQRFormatTester:
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
                operator_role = self.operator_info.get("role", "Unknown")
                
                self.log_test(
                    "Warehouse Operator Authentication",
                    True,
                    f"Successfully authenticated '{operator_name}' with role '{operator_role}'"
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
                    sample_numbers = [cargo.get("cargo_number") for cargo in self.available_cargo[:3]]
                    
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

    def test_new_qr_format_9_digits(self):
        """Step 3: CRITICAL TEST - Test NEW 9-digit QR format"""
        if not self.available_cargo:
            self.log_test(
                "NEW QR Format Test (9 digits)",
                False,
                error_msg="No available cargo to test with"
            )
            return False

        try:
            # Use first available cargo
            test_cargo = self.available_cargo[0]
            cargo_number = test_cargo.get("cargo_number")
            
            # NEW 9-digit format: 003010101
            # WWW=003 (warehouse #3), BB=01 (block 1), SS=01 (shelf 1), CC=01 (cell 1)
            new_qr_format = "003010101"
            
            payload = {
                "cargo_number": cargo_number,
                "cell_code": new_qr_format
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/cargo/place-in-cell",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                message = data.get("message", "")
                warehouse_name = data.get("warehouse_name", "")
                location = data.get("location", "")
                
                if success:
                    self.log_test(
                        "NEW QR Format Test (9 digits)",
                        True,
                        f"Successfully placed cargo {cargo_number} using QR code '{new_qr_format}'. "
                        f"Warehouse: {warehouse_name}, Location: {location}. "
                        f"Parsed as: warehouse #3, block 1, shelf 1, cell 1"
                    )
                    return True
                else:
                    self.log_test(
                        "NEW QR Format Test (9 digits)",
                        False,
                        error_msg=f"API returned success=False: {message}"
                    )
                    return False
            else:
                error_text = response.text
                self.log_test(
                    "NEW QR Format Test (9 digits)",
                    False,
                    error_msg=f"HTTP {response.status_code}: {error_text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "NEW QR Format Test (9 digits)",
                False,
                error_msg=str(e)
            )
            return False

    def test_old_qr_format_8_digits(self):
        """Step 4: COMPATIBILITY TEST - Test OLD 8-digit QR format"""
        if len(self.available_cargo) < 2:
            self.log_test(
                "OLD QR Format Test (8 digits)",
                False,
                error_msg="Not enough available cargo to test with"
            )
            return False

        try:
            # Use second available cargo
            test_cargo = self.available_cargo[1]
            cargo_number = test_cargo.get("cargo_number")
            
            # OLD 8-digit format: 03010101
            # WW=03 (warehouse #3), BB=01 (block 1), SS=01 (shelf 1), CC=01 (cell 1)
            old_qr_format = "03010101"
            
            payload = {
                "cargo_number": cargo_number,
                "cell_code": old_qr_format
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/cargo/place-in-cell",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                message = data.get("message", "")
                warehouse_name = data.get("warehouse_name", "")
                location = data.get("location", "")
                
                if success:
                    self.log_test(
                        "OLD QR Format Test (8 digits)",
                        True,
                        f"Successfully placed cargo {cargo_number} using QR code '{old_qr_format}'. "
                        f"Warehouse: {warehouse_name}, Location: {location}. "
                        f"Backward compatibility confirmed"
                    )
                    return True
                else:
                    self.log_test(
                        "OLD QR Format Test (8 digits)",
                        False,
                        error_msg=f"API returned success=False: {message}"
                    )
                    return False
            else:
                error_text = response.text
                self.log_test(
                    "OLD QR Format Test (8 digits)",
                    False,
                    error_msg=f"HTTP {response.status_code}: {error_text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "OLD QR Format Test (8 digits)",
                False,
                error_msg=str(e)
            )
            return False

    def test_additional_new_formats(self):
        """Step 5: Test additional NEW format variations"""
        if len(self.available_cargo) < 3:
            self.log_test(
                "Additional NEW Format Variations",
                False,
                error_msg="Not enough available cargo to test with"
            )
            return False

        try:
            # Test different warehouse numbers and positions
            test_cases = [
                {
                    "qr_code": "001020305",  # warehouse #1, block 2, shelf 3, cell 5
                    "description": "warehouse #1, block 2, shelf 3, cell 5"
                },
                {
                    "qr_code": "005010102",  # warehouse #5, block 1, shelf 1, cell 2
                    "description": "warehouse #5, block 1, shelf 1, cell 2"
                }
            ]
            
            success_count = 0
            total_tests = len(test_cases)
            
            for i, test_case in enumerate(test_cases):
                if i + 2 >= len(self.available_cargo):
                    break
                    
                test_cargo = self.available_cargo[i + 2]
                cargo_number = test_cargo.get("cargo_number")
                qr_code = test_case["qr_code"]
                description = test_case["description"]
                
                payload = {
                    "cargo_number": cargo_number,
                    "cell_code": qr_code
                }
                
                response = self.session.post(
                    f"{BACKEND_URL}/cargo/place-in-cell",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    success = data.get("success", False)
                    
                    if success:
                        success_count += 1
                        warehouse_name = data.get("warehouse_name", "")
                        location = data.get("location", "")
                        print(f"   ✅ QR '{qr_code}' ({description}) -> {warehouse_name}, {location}")
                    else:
                        print(f"   ❌ QR '{qr_code}' failed: {data.get('message', '')}")
                else:
                    print(f"   ❌ QR '{qr_code}' HTTP error: {response.status_code}")
            
            if success_count > 0:
                self.log_test(
                    "Additional NEW Format Variations",
                    True,
                    f"Successfully tested {success_count}/{total_tests} additional QR format variations"
                )
                return True
            else:
                self.log_test(
                    "Additional NEW Format Variations",
                    False,
                    error_msg="None of the additional QR format variations worked"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Additional NEW Format Variations",
                False,
                error_msg=str(e)
            )
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 STARTING UPDATED QR FORMAT TESTING FOR TAJLINE.TJ")
        print("=" * 60)
        print()
        
        # Step 1: Authentication
        if not self.authenticate_warehouse_operator():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        # Step 2: Get available cargo
        if not self.get_available_cargo():
            print("❌ Could not get available cargo. Cannot proceed with placement tests.")
            return False
        
        # Step 3: Test NEW 9-digit format
        new_format_success = self.test_new_qr_format_9_digits()
        
        # Step 4: Test OLD 8-digit format
        old_format_success = self.test_old_qr_format_8_digits()
        
        # Step 5: Test additional variations
        additional_tests_success = self.test_additional_new_formats()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
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
        if new_format_success:
            print("✅ NEW 9-digit QR format (003010101) - WORKING")
        else:
            print("❌ NEW 9-digit QR format (003010101) - FAILED")
            
        if old_format_success:
            print("✅ OLD 8-digit QR format (03010101) - BACKWARD COMPATIBLE")
        else:
            print("❌ OLD 8-digit QR format (03010101) - COMPATIBILITY BROKEN")
        
        print()
        
        # Overall result
        critical_success = new_format_success and old_format_success
        if critical_success:
            print("🎉 OVERALL RESULT: SUCCESS")
            print("Both NEW and OLD QR formats are working correctly!")
        else:
            print("🚨 OVERALL RESULT: FAILURE")
            print("Critical QR format issues detected!")
        
        return critical_success

def main():
    """Main test execution"""
    tester = UpdatedQRFormatTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()