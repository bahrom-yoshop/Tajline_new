#!/usr/bin/env python3
"""
Debug script for Problem 1.4 to understand warehouse assignment logic
"""

import requests
import json

base_url = "https://tajline-manager-1.preview.emergentagent.com"

# Login as admin
admin_login = {
    "phone": "+79999888777",
    "password": "admin123"
}

response = requests.post(f"{base_url}/api/auth/login", json=admin_login)
admin_token = response.json()['access_token']

# Login as warehouse operator
operator_login = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

response = requests.post(f"{base_url}/api/auth/login", json=operator_login)
operator_token = response.json()['access_token']
operator_user = response.json()['user']

print(f"Operator ID: {operator_user['id']}")

# Check operator's warehouse bindings
headers = {'Authorization': f'Bearer {admin_token}'}
response = requests.get(f"{base_url}/api/admin/operator-warehouse-bindings", headers=headers)
bindings = response.json()

print(f"\nAll operator-warehouse bindings:")
for binding in bindings:
    print(f"  Operator: {binding['operator_name']} ({binding['operator_id']})")
    print(f"  Warehouse: {binding['warehouse_name']} ({binding['warehouse_id']})")
    print(f"  Created by: {binding['created_by']}")
    print("  ---")

# Check operator's assigned warehouses
headers = {'Authorization': f'Bearer {operator_token}'}
response = requests.get(f"{base_url}/api/operator/my-warehouses", headers=headers)
my_warehouses = response.json()

print(f"\nOperator's assigned warehouses:")
if 'warehouses' in my_warehouses:
    for warehouse in my_warehouses['warehouses']:
        print(f"  ID: {warehouse['id']}")
        print(f"  Name: {warehouse['name']}")
        print(f"  Location: {warehouse['location']}")
        print("  ---")
else:
    print(f"  Response: {my_warehouses}")

# Check all warehouses
headers = {'Authorization': f'Bearer {admin_token}'}
response = requests.get(f"{base_url}/api/warehouses", headers=headers)
all_warehouses = response.json()

print(f"\nAll warehouses:")
for warehouse in all_warehouses:
    print(f"  ID: {warehouse['id']}")
    print(f"  Name: {warehouse['name']}")
    print(f"  Location: {warehouse['location']}")
    print(f"  Created by: {warehouse['created_by']}")
    print("  ---")