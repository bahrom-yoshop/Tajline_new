#!/usr/bin/env python3
"""
Focused test for the critical transport cargo list fix
Tests that cargo from both 'cargo' and 'operator_cargo' collections appear in transport cargo list
"""

import requests
import sys
import json
from datetime import datetime

class TransportCargoFixTester:
    def __init__(self, base_url="https://tajline-cargo-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        
        print(f"🚛 TRANSPORT CARGO LIST FIX TESTER")
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

    def login_users(self):
        """Login existing users"""
        print("\n🔐 LOGGING IN EXISTING USERS")
        
        login_data = [
            {"role": "user", "phone": "+79123456789", "password": "123456"},
            {"role": "admin", "phone": "+79999888777", "password": "admin123"},
            {"role": "warehouse_operator", "phone": "+79777888999", "password": "warehouse123"}
        ]
        
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
                print(f"   🔑 Token stored for {login_info['role']}")
            else:
                print(f"   ❌ Failed to login {login_info['role']}")
                return False
                
        return True

    def test_transport_cargo_list_fix(self):
        """Test the critical fix for transport cargo list display"""
        print("\n🚛 CRITICAL FIX TEST: TRANSPORT CARGO LIST DISPLAY")
        print("Testing that cargo from both 'cargo' and 'operator_cargo' collections appear in transport cargo list")
        
        if not self.login_users():
            return False
            
        # Step 1: Create a transport
        print("\n   🚛 Step 1: Creating transport...")
        transport_data = {
            "driver_name": "Тестовый Водитель",
            "driver_phone": "+79123456789",
            "transport_number": f"TEST{datetime.now().strftime('%H%M%S')}",
            "capacity_kg": 10000.0,
            "direction": "Москва - Душанбе (Тест)"
        }
        
        success, transport_response = self.run_test(
            "Create Transport",
            "POST",
            "/api/transport/create",
            200,
            transport_data,
            self.tokens['admin']
        )
        
        if not success or 'transport_id' not in transport_response:
            print("   ❌ Failed to create transport")
            return False
            
        transport_id = transport_response['transport_id']
        print(f"   ✅ Created transport: {transport_id}")
        
        # Step 2: Create cargo in 'cargo' collection (user cargo)
        print("\n   📦 Step 2: Creating user cargo (cargo collection)...")
        user_cargo_data = {
            "recipient_name": "Получатель Пользователя",
            "recipient_phone": "+992444555666",
            "route": "moscow_to_tajikistan",
            "weight": 50.0,
            "cargo_name": "Груз пользователя",
            "description": "Груз из коллекции cargo",
            "declared_value": 8000.0,
            "sender_address": "Москва, ул. Пользователя, 1",
            "recipient_address": "Душанбе, ул. Получателя, 1"
        }
        
        success, user_cargo_response = self.run_test(
            "Create User Cargo",
            "POST",
            "/api/cargo/create",
            200,
            user_cargo_data,
            self.tokens['user']
        )
        
        if not success or 'id' not in user_cargo_response:
            print("   ❌ Failed to create user cargo")
            return False
            
        user_cargo_id = user_cargo_response['id']
        user_cargo_number = user_cargo_response.get('cargo_number')
        print(f"   ✅ Created user cargo: {user_cargo_id} (№{user_cargo_number})")
        
        # Update cargo status to accepted with warehouse location
        success, _ = self.run_test(
            "Update User Cargo Status",
            "PUT",
            f"/api/cargo/{user_cargo_id}/status",
            200,
            token=self.tokens['admin'],
            params={"status": "accepted", "warehouse_location": "Склад А, Стеллаж 1"}
        )
        
        if not success:
            print("   ❌ Failed to update user cargo status")
            return False
        
        # Step 3: Create cargo in 'operator_cargo' collection
        print("\n   🏭 Step 3: Creating operator cargo (operator_cargo collection)...")
        operator_cargo_data = {
            "sender_full_name": "Отправитель Оператора",
            "sender_phone": "+79111222333",
            "recipient_full_name": "Получатель Оператора",
            "recipient_phone": "+992777888999",
            "recipient_address": "Душанбе, ул. Операторская, 25",
            "weight": 75.0,
            "cargo_name": "Груз оператора",
            "declared_value": 12000.0,
            "description": "Груз из коллекции operator_cargo",
            "route": "moscow_to_tajikistan"
        }
        
        success, operator_cargo_response = self.run_test(
            "Create Operator Cargo",
            "POST",
            "/api/operator/cargo/accept",
            200,
            operator_cargo_data,
            self.tokens['admin']
        )
        
        if not success or 'id' not in operator_cargo_response:
            print("   ❌ Failed to create operator cargo")
            return False
            
        operator_cargo_id = operator_cargo_response['id']
        operator_cargo_number = operator_cargo_response.get('cargo_number')
        print(f"   ✅ Created operator cargo: {operator_cargo_id} (№{operator_cargo_number})")
        
        # Update operator cargo to have warehouse location
        success, _ = self.run_test(
            "Update Operator Cargo Status",
            "PUT",
            f"/api/cargo/{operator_cargo_id}/status",
            200,
            token=self.tokens['admin'],
            params={"status": "accepted", "warehouse_location": "Склад Б, Стеллаж 2"}
        )
        
        # Step 4: Place both cargo items on transport using cargo numbers
        print("\n   🚛 Step 4: Placing both cargo items on transport...")
        placement_data = {
            "transport_id": transport_id,
            "cargo_numbers": [user_cargo_number, operator_cargo_number]
        }
        
        success, placement_response = self.run_test(
            "Place Both Cargo Types on Transport",
            "POST",
            f"/api/transport/{transport_id}/place-cargo",
            200,
            placement_data,
            self.tokens['admin']
        )
        
        if not success:
            print("   ❌ Failed to place cargo on transport")
            # Let's try placing them individually
            print("   🔄 Trying to place cargo individually...")
            
            # Place user cargo
            user_placement_data = {
                "transport_id": transport_id,
                "cargo_numbers": [user_cargo_number]
            }
            
            success1, _ = self.run_test(
                "Place User Cargo on Transport",
                "POST",
                f"/api/transport/{transport_id}/place-cargo",
                200,
                user_placement_data,
                self.tokens['admin']
            )
            
            # Place operator cargo
            operator_placement_data = {
                "transport_id": transport_id,
                "cargo_numbers": [operator_cargo_number]
            }
            
            success2, _ = self.run_test(
                "Place Operator Cargo on Transport",
                "POST",
                f"/api/transport/{transport_id}/place-cargo",
                200,
                operator_placement_data,
                self.tokens['admin']
            )
            
            if not (success1 or success2):
                print("   ❌ Failed to place any cargo on transport")
                return False
        else:
            placed_count = placement_response.get('placed_count', 0)
            print(f"   ✅ Successfully placed {placed_count} cargo items on transport")
        
        # Step 5: CRITICAL TEST - Get transport cargo list
        print("\n   🔍 Step 5: CRITICAL TEST - Getting transport cargo list...")
        success, cargo_list_response = self.run_test(
            "Get Transport Cargo List (CRITICAL FIX TEST)",
            "GET",
            f"/api/transport/{transport_id}/cargo-list",
            200,
            token=self.tokens['admin']
        )
        
        if not success:
            print("   ❌ Failed to get transport cargo list")
            return False
        
        cargo_list = cargo_list_response.get('cargo_list', [])
        cargo_count = len(cargo_list)
        total_weight = cargo_list_response.get('total_weight', 0)
        
        print(f"   📊 Transport cargo list contains {cargo_count} items, total weight: {total_weight}kg")
        
        # Verify cargo items are present
        user_cargo_found = False
        operator_cargo_found = False
        
        for cargo in cargo_list:
            cargo_num = cargo.get('cargo_number')
            cargo_name = cargo.get('cargo_name', 'Unknown')
            sender = cargo.get('sender_full_name', 'Unknown')
            recipient = cargo.get('recipient_name', 'Unknown')
            weight = cargo.get('weight', 0)
            status = cargo.get('status', 'Unknown')
            
            print(f"   📦 Found cargo: №{cargo_num} - {cargo_name} ({weight}kg, {status})")
            print(f"       Sender: {sender}, Recipient: {recipient}")
            
            if cargo_num == user_cargo_number:
                user_cargo_found = True
                print(f"   ✅ User cargo (cargo collection) found: №{cargo_num}")
            elif cargo_num == operator_cargo_number:
                operator_cargo_found = True
                print(f"   ✅ Operator cargo (operator_cargo collection) found: №{cargo_num}")
        
        # CRITICAL VERIFICATION
        print(f"\n   📋 CRITICAL FIX VERIFICATION:")
        if user_cargo_found and operator_cargo_found:
            print(f"   🎉 SUCCESS: Both cargo types appear in transport cargo list!")
            print(f"   ✅ User cargo (cargo collection): №{user_cargo_number} ✓")
            print(f"   ✅ Operator cargo (operator_cargo collection): №{operator_cargo_number} ✓")
            print(f"   ✅ Total cargo displayed: {cargo_count}")
            print(f"   ✅ Total weight calculated: {total_weight}kg")
            return True
        elif user_cargo_found and not operator_cargo_found:
            print(f"   ❌ PARTIAL SUCCESS: Only user cargo found, operator cargo missing!")
            print(f"   ✅ User cargo (cargo collection): №{user_cargo_number} ✓")
            print(f"   ❌ Operator cargo (operator_cargo collection): №{operator_cargo_number} ✗")
            return False
        elif operator_cargo_found and not user_cargo_found:
            print(f"   ❌ PARTIAL SUCCESS: Only operator cargo found, user cargo missing!")
            print(f"   ❌ User cargo (cargo collection): №{user_cargo_number} ✗")
            print(f"   ✅ Operator cargo (operator_cargo collection): №{operator_cargo_number} ✓")
            return False
        else:
            print(f"   ❌ CRITICAL FAILURE: Neither cargo type found in transport cargo list!")
            print(f"   ❌ User cargo (cargo collection): №{user_cargo_number} ✗")
            print(f"   ❌ Operator cargo (operator_cargo collection): №{operator_cargo_number} ✗")
            return False

def main():
    tester = TransportCargoFixTester()
    
    print("🚀 Starting critical transport cargo list fix test...")
    
    success = tester.test_transport_cargo_list_fix()
    
    print("\n" + "=" * 60)
    print("📊 CRITICAL FIX TEST RESULTS")
    print("=" * 60)
    
    if success:
        print("🎉 CRITICAL FIX VERIFIED: Transport cargo list correctly displays cargo from both collections!")
        print("✅ The fix for GET /api/transport/{transport_id}/cargo-list is working correctly")
        print("✅ Cargo from 'cargo' collection: VISIBLE")
        print("✅ Cargo from 'operator_cargo' collection: VISIBLE")
        sys.exit(0)
    else:
        print("❌ CRITICAL FIX FAILED: Transport cargo list has issues displaying cargo from both collections")
        print("❌ The fix for GET /api/transport/{transport_id}/cargo-list needs attention")
        sys.exit(1)

if __name__ == "__main__":
    main()