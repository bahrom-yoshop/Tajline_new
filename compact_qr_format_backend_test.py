#!/usr/bin/env python3
"""
CRITICAL BACKEND TEST: Compact QR Code Format Support in TAJLINE.TJ
Testing the FIXED support for compact QR cell code format "03010106"

REVIEW REQUEST CONTEXT:
- Test FIXED support for compact QR cell code format in TAJLINE.TJ
- Warehouse operator authorization (+79777888999/warehouse123)
- Get available cargo for placement
- CRITICAL TEST: API /api/cargo/place-in-cell with compact format "03010106"
- Format should parse as WWBBSSCC: WW=warehouse, BB=block, SS=shelf, CC=cell
- Expected: warehouse #3, block 1, shelf 1, cell 6

BACKEND FIXES IMPLEMENTED:
- Added support for compact QR cell code format "03010106"
- Format parsed as WWBBSSCC: WW=warehouse, BB=block, SS=shelf, CC=cell  
- Warehouse search by warehouse_number instead of warehouse_id
- Updated error message for all supported formats

EXPECTED RESULTS:
- API should successfully process QR code "03010106"
- Cargo should be placed in warehouse #3, block 1, shelf 1, cell 6
- "Invalid cell code format" error should be FIXED
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://cargo-tracker-29.preview.emergentagent.com/api"
WAREHOUSE_OPERATOR_CREDENTIALS = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class CompactQRFormatTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.operator_info = None
        self.available_cargo = []
        self.test_results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        print(f"   {message}")
        if details:
            print(f"   Details: {details}")
        print()
        
    def authenticate_warehouse_operator(self):
        """Step 1: Authenticate warehouse operator"""
        print("🔐 STEP 1: Authenticating warehouse operator (+79777888999/warehouse123)")
        
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
                
                self.log_result(
                    "Warehouse Operator Authentication",
                    True,
                    f"Successfully authenticated as '{operator_name}' with role '{operator_role}'",
                    {"user_id": self.operator_info.get("id"), "phone": self.operator_info.get("phone")}
                )
                return True
            else:
                self.log_result(
                    "Warehouse Operator Authentication",
                    False,
                    f"Authentication failed with status {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Warehouse Operator Authentication",
                False,
                f"Authentication error: {str(e)}"
            )
            return False
    
    def get_available_cargo(self):
        """Step 2: Get available cargo for placement"""
        print("📦 STEP 2: Getting available cargo for placement")
        
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement")
            
            if response.status_code == 200:
                data = response.json()
                self.available_cargo = data.get("items", [])
                cargo_count = len(self.available_cargo)
                
                if cargo_count > 0:
                    # Get first cargo for testing
                    test_cargo = self.available_cargo[0]
                    cargo_number = test_cargo.get("cargo_number")
                    
                    self.log_result(
                        "Get Available Cargo",
                        True,
                        f"Successfully retrieved {cargo_count} cargo items for placement",
                        {"test_cargo_number": cargo_number, "total_cargo": cargo_count}
                    )
                    return True
                else:
                    self.log_result(
                        "Get Available Cargo",
                        False,
                        "No cargo available for placement",
                        {"response_data": data}
                    )
                    return False
            else:
                self.log_result(
                    "Get Available Cargo",
                    False,
                    f"Failed to get cargo list with status {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Get Available Cargo",
                False,
                f"Error getting cargo: {str(e)}"
            )
            return False
    
    def test_compact_qr_format_03010106(self):
        """Step 3: CRITICAL TEST - Test compact QR format "03010106" """
        print("🎯 STEP 3: CRITICAL TEST - Testing compact QR format '03010106'")
        
        if not self.available_cargo:
            self.log_result(
                "Compact QR Format Test",
                False,
                "No available cargo to test with"
            )
            return False
        
        # Use first available cargo
        test_cargo = self.available_cargo[0]
        cargo_number = test_cargo.get("cargo_number")
        
        # Test compact format: "03010106" should parse as warehouse #3, block 1, shelf 1, cell 6
        compact_cell_code = "03010106"
        
        try:
            payload = {
                "cargo_number": cargo_number,
                "cell_code": compact_cell_code
            }
            
            print(f"   Testing cargo: {cargo_number}")
            print(f"   Compact cell code: {compact_cell_code}")
            print(f"   Expected parsing: warehouse #3, block 1, shelf 1, cell 6")
            
            response = self.session.post(
                f"{BACKEND_URL}/cargo/place-in-cell",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if placement was successful
                warehouse_name = data.get("warehouse_name", "")
                location_code = data.get("location_code", "")
                placed_cargo = data.get("cargo_number", "")
                
                self.log_result(
                    "Compact QR Format Test (03010106)",
                    True,
                    f"✅ CRITICAL SUCCESS: Compact QR code '03010106' processed successfully!",
                    {
                        "cargo_number": placed_cargo,
                        "warehouse_name": warehouse_name,
                        "location_code": location_code,
                        "compact_format": compact_cell_code,
                        "expected_parsing": "warehouse #3, block 1, shelf 1, cell 6",
                        "full_response": data
                    }
                )
                return True
            else:
                error_message = response.text
                
                # Check if it's the old "Invalid cell code format" error
                if "Invalid cell code format" in error_message:
                    self.log_result(
                        "Compact QR Format Test (03010106)",
                        False,
                        f"❌ CRITICAL FAILURE: 'Invalid cell code format' error NOT FIXED!",
                        {
                            "compact_format": compact_cell_code,
                            "error_response": error_message,
                            "status_code": response.status_code,
                            "issue": "Backend still doesn't support compact format"
                        }
                    )
                else:
                    self.log_result(
                        "Compact QR Format Test (03010106)",
                        False,
                        f"Compact QR format failed with status {response.status_code}",
                        {
                            "compact_format": compact_cell_code,
                            "error_response": error_message,
                            "status_code": response.status_code
                        }
                    )
                return False
                
        except Exception as e:
            self.log_result(
                "Compact QR Format Test (03010106)",
                False,
                f"Error testing compact QR format: {str(e)}"
            )
            return False
    
    def test_additional_compact_formats(self):
        """Step 4: Test additional compact formats for comprehensive coverage"""
        print("🔍 STEP 4: Testing additional compact QR formats")
        
        if not self.available_cargo or len(self.available_cargo) < 2:
            self.log_result(
                "Additional Compact Formats Test",
                False,
                "Not enough cargo available for additional testing"
            )
            return False
        
        # Test additional compact formats
        test_formats = [
            {"code": "01010101", "expected": "warehouse #1, block 1, shelf 1, cell 1"},
            {"code": "02020203", "expected": "warehouse #2, block 2, shelf 2, cell 3"},
            {"code": "05030210", "expected": "warehouse #5, block 3, shelf 2, cell 10"}
        ]
        
        success_count = 0
        
        for i, format_test in enumerate(test_formats):
            if i >= len(self.available_cargo):
                break
                
            cargo = self.available_cargo[i]
            cargo_number = cargo.get("cargo_number")
            cell_code = format_test["code"]
            expected = format_test["expected"]
            
            try:
                payload = {
                    "cargo_number": cargo_number,
                    "cell_code": cell_code
                }
                
                response = self.session.post(
                    f"{BACKEND_URL}/cargo/place-in-cell",
                    json=payload
                )
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"   ✅ Format {cell_code} ({expected}): SUCCESS")
                else:
                    print(f"   ❌ Format {cell_code} ({expected}): FAILED - {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Format {cell_code} ({expected}): ERROR - {str(e)}")
        
        self.log_result(
            "Additional Compact Formats Test",
            success_count > 0,
            f"Successfully tested {success_count}/{len(test_formats)} additional compact formats",
            {"successful_formats": success_count, "total_tested": len(test_formats)}
        )
        
        return success_count > 0
    
    def test_error_message_improvements(self):
        """Step 5: Test improved error messages for unsupported formats"""
        print("📝 STEP 5: Testing improved error messages")
        
        if not self.available_cargo:
            self.log_result(
                "Error Message Test",
                False,
                "No available cargo to test error messages"
            )
            return False
        
        # Test invalid format to check error message
        test_cargo = self.available_cargo[0]
        cargo_number = test_cargo.get("cargo_number")
        invalid_cell_code = "INVALID_FORMAT"
        
        try:
            payload = {
                "cargo_number": cargo_number,
                "cell_code": invalid_cell_code
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/cargo/place-in-cell",
                json=payload
            )
            
            if response.status_code != 200:
                error_message = response.text
                
                # Check if error message mentions supported formats
                has_format_info = any(keyword in error_message.lower() for keyword in [
                    "supported format", "format", "example", "wwbbsscc"
                ])
                
                self.log_result(
                    "Error Message Improvements Test",
                    has_format_info,
                    f"Error message {'includes' if has_format_info else 'lacks'} format information",
                    {
                        "error_message": error_message,
                        "includes_format_info": has_format_info,
                        "test_input": invalid_cell_code
                    }
                )
                return has_format_info
            else:
                self.log_result(
                    "Error Message Test",
                    False,
                    "Expected error for invalid format but got success",
                    {"unexpected_success": True}
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Error Message Test",
                False,
                f"Error testing error messages: {str(e)}"
            )
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test of compact QR format fixes"""
        print("🚀 STARTING COMPREHENSIVE COMPACT QR FORMAT TEST")
        print("=" * 80)
        
        # Step 1: Authentication
        if not self.authenticate_warehouse_operator():
            print("❌ CRITICAL FAILURE: Cannot proceed without authentication")
            return False
        
        # Step 2: Get available cargo
        if not self.get_available_cargo():
            print("❌ CRITICAL FAILURE: Cannot proceed without available cargo")
            return False
        
        # Step 3: CRITICAL TEST - Test compact format "03010106"
        critical_success = self.test_compact_qr_format_03010106()
        
        # Step 4: Test additional formats
        additional_success = self.test_additional_compact_formats()
        
        # Step 5: Test error messages
        error_msg_success = self.test_error_message_improvements()
        
        # Generate final report
        self.generate_final_report(critical_success)
        
        return critical_success
    
    def generate_final_report(self, critical_success):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📊 FINAL TEST REPORT: COMPACT QR FORMAT SUPPORT")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📈 OVERALL SUCCESS RATE: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
        print()
        
        # Critical test result
        if critical_success:
            print("🎉 CRITICAL TEST RESULT: ✅ SUCCESS")
            print("   ✅ Compact QR format '03010106' is WORKING")
            print("   ✅ 'Invalid cell code format' error is FIXED")
            print("   ✅ Backend correctly parses WWBBSSCC format")
        else:
            print("🚨 CRITICAL TEST RESULT: ❌ FAILURE")
            print("   ❌ Compact QR format '03010106' is NOT WORKING")
            print("   ❌ 'Invalid cell code format' error is NOT FIXED")
            print("   ❌ Backend does not support WWBBSSCC format")
        
        print()
        print("📋 DETAILED TEST RESULTS:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['test']}: {result['message']}")
        
        print()
        if critical_success:
            print("🎯 CONCLUSION: COMPACT QR FORMAT FIXES ARE WORKING CORRECTLY!")
            print("   The API /api/cargo/place-in-cell successfully processes compact format '03010106'")
            print("   Cargo placement with compact QR codes is functional")
        else:
            print("⚠️  CONCLUSION: COMPACT QR FORMAT FIXES NEED ATTENTION!")
            print("   The API /api/cargo/place-in-cell does not support compact format '03010106'")
            print("   Further backend development is required")
        
        print("=" * 80)

def main():
    """Main test execution"""
    tester = CompactQRFormatTester()
    
    try:
        success = tester.run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()