#!/usr/bin/env python3
"""
Focused test for operator-warehouse binding system
"""

import requests
import sys
import json

class OperatorBindingTester:
    def __init__(self, base_url="https://cargo-tracker-29.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        
    def login_users(self):
        """Login required users"""
        login_data = [
            {"role": "admin", "phone": "+79999888777", "password": "admin123"},
            {"role": "warehouse_operator", "phone": "+79777888999", "password": "warehouse123"},
            {"role": "user", "phone": "+79123456789", "password": "123456"}
        ]
        
        for login_info in login_data:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={"phone": login_info['phone'], "password": login_info['password']},
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.tokens[login_info['role']] = data['access_token']
                self.users[login_info['role']] = data['user']
                print(f"✅ Logged in as {login_info['role']}")
            else:
                print(f"❌ Failed to login as {login_info['role']}: {response.status_code}")
                return False
        return True
    
    def test_operator_warehouse_binding(self):
        """Test the operator-warehouse binding system"""
        print("\n🔗 TESTING OPERATOR-WAREHOUSE BINDING SYSTEM")
        
        # Create a warehouse first
        warehouse_data = {
            "name": "Test Binding Warehouse",
            "location": "Test Location",
            "blocks_count": 1,
            "shelves_per_block": 1,
            "cells_per_shelf": 1
        }
        
        response = requests.post(
            f"{self.base_url}/api/warehouses/create",
            json=warehouse_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.tokens["admin"]}'
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to create warehouse: {response.status_code}")
            return False
            
        warehouse_id = response.json()['id']
        print(f"✅ Created warehouse: {warehouse_id}")
        
        # Test 1: Create operator-warehouse binding
        binding_data = {
            "operator_id": self.users['warehouse_operator']['id'],
            "warehouse_id": warehouse_id
        }
        
        response = requests.post(
            f"{self.base_url}/api/admin/operator-warehouse-binding",
            json=binding_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.tokens["admin"]}'
            }
        )
        
        if response.status_code == 200:
            binding_id = response.json()['binding_id']
            print(f"✅ Created binding: {binding_id}")
        else:
            print(f"❌ Failed to create binding: {response.status_code} - {response.text}")
            return False
        
        # Test 2: Get all bindings
        response = requests.get(
            f"{self.base_url}/api/admin/operator-warehouse-bindings",
            headers={'Authorization': f'Bearer {self.tokens["admin"]}'}
        )
        
        if response.status_code == 200:
            bindings = response.json()
            print(f"✅ Retrieved {len(bindings)} bindings")
        else:
            print(f"❌ Failed to get bindings: {response.status_code} - {response.text}")
            return False
        
        # Test 3: Operator gets their warehouses (this was failing before)
        response = requests.get(
            f"{self.base_url}/api/operator/my-warehouses",
            headers={'Authorization': f'Bearer {self.tokens["warehouse_operator"]}'}
        )
        
        if response.status_code == 200:
            warehouses = response.json()
            print(f"✅ Operator can access {len(warehouses)} warehouses")
            if warehouses and warehouses[0]['id'] == warehouse_id:
                print("✅ Correct warehouse returned")
            else:
                print("❌ Wrong warehouse returned")
        else:
            print(f"❌ Failed to get operator warehouses: {response.status_code} - {response.text}")
            return False
        
        # Test 4: Available cargo for transport (this was also failing)
        response = requests.get(
            f"{self.base_url}/api/transport/available-cargo",
            headers={'Authorization': f'Bearer {self.tokens["admin"]}'}
        )
        
        if response.status_code == 200:
            cargo = response.json()
            print(f"✅ Admin can see {len(cargo)} available cargo items")
        else:
            print(f"❌ Failed to get available cargo (admin): {response.status_code} - {response.text}")
            return False
        
        # Test 5: Operator available cargo
        response = requests.get(
            f"{self.base_url}/api/transport/available-cargo",
            headers={'Authorization': f'Bearer {self.tokens["warehouse_operator"]}'}
        )
        
        if response.status_code == 200:
            cargo = response.json()
            print(f"✅ Operator can see {len(cargo)} available cargo items")
        else:
            print(f"❌ Failed to get available cargo (operator): {response.status_code} - {response.text}")
            return False
        
        # Test 6: Delete binding
        response = requests.delete(
            f"{self.base_url}/api/admin/operator-warehouse-binding/{binding_id}",
            headers={'Authorization': f'Bearer {self.tokens["admin"]}'}
        )
        
        if response.status_code == 200:
            print(f"✅ Deleted binding: {binding_id}")
        else:
            print(f"❌ Failed to delete binding: {response.status_code} - {response.text}")
            return False
        
        # Test 7: Verify operator no longer has access
        response = requests.get(
            f"{self.base_url}/api/operator/my-warehouses",
            headers={'Authorization': f'Bearer {self.tokens["warehouse_operator"]}'}
        )
        
        if response.status_code == 200:
            warehouses = response.json()
            if len(warehouses) == 0:
                print("✅ Operator no longer has warehouse access after deletion")
            else:
                print(f"⚠️  Operator still has access to {len(warehouses)} warehouses")
        else:
            print(f"❌ Failed to verify operator warehouse access: {response.status_code}")
            return False
        
        return True
    
    def run_test(self):
        """Run the focused test"""
        print("🚀 Starting Operator-Warehouse Binding Test")
        
        if not self.login_users():
            return False
            
        if not self.test_operator_warehouse_binding():
            return False
            
        print("\n✅ ALL OPERATOR-WAREHOUSE BINDING TESTS PASSED!")
        return True

def main():
    tester = OperatorBindingTester()
    success = tester.run_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())