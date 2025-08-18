#!/usr/bin/env python3
import requests
import json

# Configuration
BACKEND_URL = "https://tajline-cargo-3.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

def check_courier_lists():
    session = requests.Session()
    
    # Authenticate
    auth_response = session.post(f"{BACKEND_URL}/auth/login", json=ADMIN_CREDENTIALS)
    if auth_response.status_code != 200:
        print(f"Authentication failed: {auth_response.text}")
        return
    
    # Set authorization header
    auth_data = auth_response.json()
    token = auth_data["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    print("✅ Authenticated successfully")
    
    # Check active couriers
    active_response = session.get(f"{BACKEND_URL}/admin/couriers/list")
    if active_response.status_code == 200:
        active_data = active_response.json()
        active_count = len(active_data.get('items', []))
        print(f"📊 Active couriers: {active_count}")
        
        # Show first few active couriers
        if active_data.get('items'):
            print("Active couriers sample:")
            for courier in active_data['items'][:3]:
                print(f"  - {courier.get('full_name', 'N/A')} (ID: {courier.get('id', 'N/A')[:8]}..., active: {courier.get('is_active', 'N/A')}, deleted: {courier.get('deleted', 'N/A')})")
    else:
        print(f"❌ Failed to get active couriers: {active_response.text}")
    
    # Check inactive couriers
    inactive_response = session.get(f"{BACKEND_URL}/admin/couriers/inactive")
    if inactive_response.status_code == 200:
        inactive_data = inactive_response.json()
        inactive_couriers = inactive_data.get('inactive_couriers', [])
        inactive_count = len(inactive_couriers)
        print(f"📊 Inactive couriers: {inactive_count}")
        
        # Show first few inactive couriers
        if inactive_couriers:
            print("Inactive couriers sample:")
            for courier in inactive_couriers[:3]:
                print(f"  - {courier.get('full_name', 'N/A')} (ID: {courier.get('id', 'N/A')[:8]}..., active: {courier.get('is_active', 'N/A')}, deleted: {courier.get('deleted', 'N/A')})")
    else:
        print(f"❌ Failed to get inactive couriers: {inactive_response.text}")
    
    # Check all couriers with show_inactive=true
    all_response = session.get(f"{BACKEND_URL}/admin/couriers/list?show_inactive=true")
    if all_response.status_code == 200:
        all_data = all_response.json()
        all_count = len(all_data.get('items', []))
        print(f"📊 All couriers (including inactive): {all_count}")
        
        # Count by status
        active_in_all = sum(1 for c in all_data.get('items', []) if c.get('is_active', True) and not c.get('deleted', False))
        inactive_in_all = sum(1 for c in all_data.get('items', []) if not c.get('is_active', True) and not c.get('deleted', False))
        deleted_in_all = sum(1 for c in all_data.get('items', []) if c.get('deleted', False))
        
        print(f"  - Active: {active_in_all}")
        print(f"  - Inactive (not deleted): {inactive_in_all}")
        print(f"  - Deleted: {deleted_in_all}")
    else:
        print(f"❌ Failed to get all couriers: {all_response.text}")

if __name__ == "__main__":
    check_courier_lists()