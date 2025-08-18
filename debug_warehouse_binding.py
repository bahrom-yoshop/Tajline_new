#!/usr/bin/env python3
"""
Debug test to investigate the operator warehouse binding issue
"""

import requests
import json

def debug_operator_warehouse_binding():
    base_url = "https://cargo-system-debug.preview.emergentagent.com"
    
    # Login as admin
    admin_login = {
        "phone": "+79999888777",
        "password": "admin123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=admin_login)
    admin_token = response.json()['access_token']
    admin_user = response.json()['user']
    
    # Login as warehouse operator
    operator_login = {
        "phone": "+79777888999",
        "password": "warehouse123"
    }
    
    response = requests.post(f"{base_url}/api/auth/login", json=operator_login)
    operator_token = response.json()['access_token']
    operator_user = response.json()['user']
    
    print(f"🔍 DEBUG: Operator ID: {operator_user['id']}")
    print(f"🔍 DEBUG: Operator Name: {operator_user['full_name']}")
    
    # Get all operator-warehouse bindings
    headers = {'Authorization': f'Bearer {admin_token}'}
    response = requests.get(f"{base_url}/api/admin/operator-warehouse-bindings", headers=headers)
    bindings = response.json()
    
    print(f"\n🔍 DEBUG: All operator-warehouse bindings:")
    for binding in bindings:
        print(f"   Binding ID: {binding.get('id')}")
        print(f"   Operator ID: {binding.get('operator_id')}")
        print(f"   Operator Name: {binding.get('operator_name')}")
        print(f"   Warehouse ID: {binding.get('warehouse_id')}")
        print(f"   Warehouse Name: {binding.get('warehouse_name')}")
        print(f"   ---")
    
    # Get operator's assigned warehouses
    headers = {'Authorization': f'Bearer {operator_token}'}
    response = requests.get(f"{base_url}/api/operator/my-warehouses", headers=headers)
    my_warehouses = response.json()
    
    print(f"\n🔍 DEBUG: Operator's assigned warehouses:")
    if 'warehouses' in my_warehouses:
        for warehouse in my_warehouses['warehouses']:
            print(f"   Warehouse ID: {warehouse.get('id')}")
            print(f"   Warehouse Name: {warehouse.get('name')}")
            print(f"   ---")
    else:
        print(f"   Response: {json.dumps(my_warehouses, indent=2)}")
    
    # Get all active warehouses
    headers = {'Authorization': f'Bearer {admin_token}'}
    response = requests.get(f"{base_url}/api/warehouses", headers=headers)
    all_warehouses = response.json()
    
    print(f"\n🔍 DEBUG: All active warehouses:")
    for warehouse in all_warehouses:
        print(f"   Warehouse ID: {warehouse.get('id')}")
        print(f"   Warehouse Name: {warehouse.get('name')}")
        print(f"   Created By: {warehouse.get('created_by')}")
        print(f"   Is Active: {warehouse.get('is_active')}")
        print(f"   ---")

if __name__ == "__main__":
    debug_operator_warehouse_binding()