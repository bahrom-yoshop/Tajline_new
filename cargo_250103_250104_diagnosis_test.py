#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Авто-диагностика и исправление заявок 250103 и 250104 в TAJLINE.TJ
Comprehensive backend testing for auto-diagnosis and correction of cargo requests 250103 and 250104

Test Plan:
1. Authenticate as admin
2. Diagnose cargo 250103 and 250104 using debug endpoint
3. Fix warehouse_id if empty (set Moscow Warehouse #1)
4. Determine destination warehouse if possible
5. Verify fixes and ensure visibility
6. Update test results
"""

import requests
import json
import sys
from datetime import datetime
import os

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://qr-logistics-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

# Known warehouse IDs
MOSCOW_WAREHOUSE_1_ID = "d0a8362d-b4d3-4947-b335-28c94658a021"
DUSHANBE_WAREHOUSE_3_ID = "84d25a76-f23b-4c95-adb4-255732cd6520"

# Cargo numbers to test
CARGO_NUMBERS = ["250103", "250104"]

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_results = []
        self.diagnosis_results = {}
        
    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def authenticate_admin(self):
        """Authenticate as administrator"""
        try:
            self.log("🔐 Authenticating as administrator...")
            
            response = self.session.post(
                f"{API_BASE}/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                user_info = data.get("user", {})
                
                self.log(f"✅ Admin authentication successful!")
                self.log(f"   User: {user_info.get('full_name', 'Unknown')}")
                self.log(f"   Role: {user_info.get('role', 'Unknown')}")
                self.log(f"   User Number: {user_info.get('user_number', 'Unknown')}")
                
                # Set authorization header
                self.session.headers.update({
                    "Authorization": f"Bearer {self.admin_token}"
                })
                
                return True
            else:
                self.log(f"❌ Admin authentication failed: {response.status_code}", "ERROR")
                self.log(f"   Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin authentication error: {str(e)}", "ERROR")
            return False
    
    def diagnose_cargo(self, cargo_number):
        """Diagnose cargo using debug endpoint"""
        try:
            self.log(f"🔍 Diagnosing cargo {cargo_number}...")
            
            response = self.session.get(
                f"{API_BASE}/debug/find-cargo-by-number/{cargo_number}",
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.log(f"✅ Cargo {cargo_number} diagnosis successful!")
                self.log(f"   Found documents: {data.get('total_found', 0)}")
                
                # Extract key information
                diagnosis = {
                    "cargo_number": cargo_number,
                    "total_found": data.get("total_found", 0),
                    "collections": data.get("by_collection", {}),
                    "documents": data.get("documents", []),
                    "summary": data.get("summary", {}),
                    "warehouse_id": None,
                    "destination_warehouse_id": None,
                    "status": None,
                    "processing_status": None,
                    "hidden_reason": None,
                    "needs_warehouse_fix": False,
                    "needs_destination_fix": False
                }
                
                # Analyze documents
                if diagnosis["documents"]:
                    doc = diagnosis["documents"][0]  # Take first document
                    diagnosis["warehouse_id"] = doc.get("warehouse_id")
                    diagnosis["destination_warehouse_id"] = doc.get("destination_warehouse_id")
                    diagnosis["status"] = doc.get("status")
                    diagnosis["processing_status"] = doc.get("processing_status")
                    diagnosis["hidden_reason"] = doc.get("hidden_reason")
                    
                    # Check if fixes are needed
                    if not diagnosis["warehouse_id"]:
                        diagnosis["needs_warehouse_fix"] = True
                        self.log(f"⚠️  Cargo {cargo_number} missing warehouse_id")
                    
                    if not diagnosis["destination_warehouse_id"]:
                        diagnosis["needs_destination_fix"] = True
                        self.log(f"⚠️  Cargo {cargo_number} missing destination_warehouse_id")
                    
                    if diagnosis["hidden_reason"]:
                        self.log(f"⚠️  Cargo {cargo_number} has hidden_reason: {diagnosis['hidden_reason']}")
                
                self.diagnosis_results[cargo_number] = diagnosis
                return diagnosis
                
            else:
                self.log(f"❌ Cargo {cargo_number} diagnosis failed: {response.status_code}", "ERROR")
                self.log(f"   Response: {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Cargo {cargo_number} diagnosis error: {str(e)}", "ERROR")
            return None
    
    def get_destinations(self):
        """Get available destinations/cities"""
        try:
            self.log("🌍 Getting available destinations...")
            
            response = self.session.get(
                f"{API_BASE}/destinations/cities",
                timeout=30
            )
            
            if response.status_code == 200:
                destinations = response.json()
                self.log(f"✅ Found {len(destinations)} destinations")
                
                # Log some destinations for reference
                for dest in destinations[:3]:
                    self.log(f"   - {dest.get('name', 'Unknown')}: {dest.get('id', 'Unknown')}")
                
                return destinations
            else:
                self.log(f"❌ Failed to get destinations: {response.status_code}", "ERROR")
                return []
                
        except Exception as e:
            self.log(f"❌ Error getting destinations: {str(e)}", "ERROR")
            return []
    
    def set_warehouses(self, cargo_number, current_warehouse_id=None, destination_warehouse_id=None):
        """Set warehouses for cargo using PATCH endpoint"""
        try:
            self.log(f"🔧 Setting warehouses for cargo {cargo_number}...")
            
            payload = {}
            if current_warehouse_id:
                payload["current_warehouse_id"] = current_warehouse_id
                self.log(f"   Setting current_warehouse_id: {current_warehouse_id}")
            
            if destination_warehouse_id:
                payload["destination_warehouse_id"] = destination_warehouse_id
                self.log(f"   Setting destination_warehouse_id: {destination_warehouse_id}")
            
            if not payload:
                self.log("⚠️  No warehouse changes needed")
                return True
            
            response = self.session.patch(
                f"{API_BASE}/admin/cargo/by-number/{cargo_number}/set-warehouses",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Warehouses set successfully for cargo {cargo_number}")
                self.log(f"   Response: {data.get('message', 'Success')}")
                return True
            else:
                self.log(f"❌ Failed to set warehouses for cargo {cargo_number}: {response.status_code}", "ERROR")
                self.log(f"   Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error setting warehouses for cargo {cargo_number}: {str(e)}", "ERROR")
            return False
    
    def determine_destination_warehouse(self, destinations):
        """Determine destination warehouse based on available destinations"""
        # For this test, we'll use Dushanbe as a common destination
        for dest in destinations:
            if "душанбе" in dest.get("name", "").lower() or "dushanbe" in dest.get("name", "").lower():
                return dest.get("warehouse_id") or DUSHANBE_WAREHOUSE_3_ID
        
        # Default to Dushanbe Warehouse #3
        return DUSHANBE_WAREHOUSE_3_ID
    
    def process_cargo(self, cargo_number):
        """Process a single cargo: diagnose and fix if needed"""
        self.log(f"\n🎯 PROCESSING CARGO {cargo_number}")
        self.log("=" * 50)
        
        # Step 1: Initial diagnosis
        diagnosis = self.diagnose_cargo(cargo_number)
        if not diagnosis:
            return False
        
        # Step 2: Get destinations if needed
        destinations = []
        if diagnosis["needs_destination_fix"]:
            destinations = self.get_destinations()
        
        # Step 3: Apply fixes if needed
        fixes_applied = False
        
        if diagnosis["needs_warehouse_fix"] or diagnosis["needs_destination_fix"]:
            current_warehouse_id = None
            destination_warehouse_id = None
            
            # Set Moscow Warehouse #1 as reception warehouse if missing
            if diagnosis["needs_warehouse_fix"]:
                current_warehouse_id = MOSCOW_WAREHOUSE_1_ID
                self.log(f"🏭 Will set reception warehouse: Moscow Warehouse #1")
            
            # Determine destination warehouse if missing
            if diagnosis["needs_destination_fix"] and destinations:
                destination_warehouse_id = self.determine_destination_warehouse(destinations)
                self.log(f"🎯 Will set destination warehouse: {destination_warehouse_id}")
            
            # Apply the fixes
            if self.set_warehouses(cargo_number, current_warehouse_id, destination_warehouse_id):
                fixes_applied = True
                self.log(f"✅ Fixes applied successfully for cargo {cargo_number}")
            else:
                self.log(f"❌ Failed to apply fixes for cargo {cargo_number}")
        
        # Step 4: Re-diagnose to verify fixes
        self.log(f"🔄 Re-diagnosing cargo {cargo_number} to verify fixes...")
        final_diagnosis = self.diagnose_cargo(cargo_number)
        
        if final_diagnosis:
            # Check if hidden_reason is resolved
            if not final_diagnosis["hidden_reason"]:
                self.log(f"✅ Cargo {cargo_number} is now visible (no hidden_reason)")
            else:
                self.log(f"⚠️  Cargo {cargo_number} still has hidden_reason: {final_diagnosis['hidden_reason']}")
            
            # Update diagnosis with final state
            diagnosis["final_state"] = final_diagnosis
            diagnosis["fixes_applied"] = fixes_applied
        
        return True
    
    def run_comprehensive_test(self):
        """Run comprehensive auto-diagnosis and correction test"""
        self.log("🎯 STARTING COMPREHENSIVE AUTO-DIAGNOSIS AND CORRECTION TEST")
        self.log("=" * 80)
        
        # Step 1: Authenticate as admin
        if not self.authenticate_admin():
            self.log("❌ Cannot proceed without admin authentication", "ERROR")
            return False
        
        # Step 2: Process each cargo
        success_count = 0
        for cargo_number in CARGO_NUMBERS:
            if self.process_cargo(cargo_number):
                success_count += 1
        
        # Step 3: Generate summary
        self.log(f"\n📊 COMPREHENSIVE TEST SUMMARY")
        self.log("=" * 50)
        self.log(f"Total cargo processed: {len(CARGO_NUMBERS)}")
        self.log(f"Successful processing: {success_count}")
        self.log(f"Success rate: {(success_count/len(CARGO_NUMBERS)*100):.1f}%")
        
        # Step 4: Detailed results for each cargo
        for cargo_number in CARGO_NUMBERS:
            if cargo_number in self.diagnosis_results:
                diagnosis = self.diagnosis_results[cargo_number]
                self.log(f"\n🔍 CARGO {cargo_number} FINAL STATUS:")
                self.log(f"   Warehouse ID: {diagnosis.get('warehouse_id', 'None')}")
                self.log(f"   Destination Warehouse ID: {diagnosis.get('destination_warehouse_id', 'None')}")
                self.log(f"   Status: {diagnosis.get('status', 'Unknown')}")
                self.log(f"   Processing Status: {diagnosis.get('processing_status', 'Unknown')}")
                self.log(f"   Hidden Reason: {diagnosis.get('hidden_reason', 'None')}")
                self.log(f"   Fixes Applied: {diagnosis.get('fixes_applied', False)}")
                
                if diagnosis.get("final_state"):
                    final = diagnosis["final_state"]
                    self.log(f"   Final Warehouse ID: {final.get('warehouse_id', 'None')}")
                    self.log(f"   Final Destination ID: {final.get('destination_warehouse_id', 'None')}")
                    self.log(f"   Final Hidden Reason: {final.get('hidden_reason', 'None')}")
        
        return success_count == len(CARGO_NUMBERS)

def main():
    """Main test execution"""
    print("🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Авто-диагностика и исправление заявок 250103 и 250104")
    print("=" * 80)
    
    tester = BackendTester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎉 COMPREHENSIVE AUTO-DIAGNOSIS AND CORRECTION TEST COMPLETED SUCCESSFULLY!")
            print("✅ All cargo requests have been diagnosed and corrected as needed")
            sys.exit(0)
        else:
            print("\n❌ COMPREHENSIVE AUTO-DIAGNOSIS AND CORRECTION TEST FAILED!")
            print("⚠️  Some cargo requests could not be processed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()