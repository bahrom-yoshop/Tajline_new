#!/usr/bin/env python3
import requests

BACKEND_URL = 'https://tajline-cargo-3.preview.emergentagent.com/api'

# Authorize as admin
admin_response = requests.post(f'{BACKEND_URL}/auth/login', json={'phone': '+79999888777', 'password': 'admin123'})

if admin_response.status_code == 200:
    admin_token = admin_response.json().get('access_token')
    headers = {'Authorization': f'Bearer {admin_token}'}
    
    print('🔍 Checking warehouse notifications with admin token...')
    notifications_response = requests.get(f'{BACKEND_URL}/operator/warehouse-notifications', headers=headers)
    print(f'Status: {notifications_response.status_code}')
    if notifications_response.status_code == 200:
        notifications = notifications_response.json()
        print(f'Found {len(notifications)} warehouse notifications')
        if notifications and len(notifications) > 0:
            sample = notifications[0]
            print('Sample notification fields:')
            for key in sorted(sample.keys()):
                value = sample[key]
                if isinstance(value, str) and len(value) > 30:
                    value = value[:30] + '...'
                print(f'  {key}: {value}')
    else:
        print(f'Error: {notifications_response.text}')
        
    print('\n🔍 Checking operator pickup requests with admin token...')
    pickup_response = requests.get(f'{BACKEND_URL}/operator/pickup-requests', headers=headers)
    print(f'Status: {pickup_response.status_code}')
    if pickup_response.status_code == 200:
        pickup_data = pickup_response.json()
        print(f'Pickup requests: {pickup_data.get("total_count", 0)}')
        if pickup_data.get('pickup_requests') and len(pickup_data.get('pickup_requests', [])) > 0:
            print('Sample pickup request fields:')
            sample = pickup_data['pickup_requests'][0]
            for key in sorted(sample.keys()):
                value = sample[key]
                if isinstance(value, str) and len(value) > 30:
                    value = value[:30] + '...'
                print(f'  {key}: {value}')
    else:
        print(f'Error: {pickup_response.text}')
else:
    print('Failed to authorize as admin')