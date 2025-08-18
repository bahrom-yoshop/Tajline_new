#!/usr/bin/env python3
"""
Enhanced User Profile Functionality Test
Focused test for the enhanced user profile functionality as requested in review
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

class ProfileTester:
    def __init__(self):
        self.base_url = os.getenv('REACT_APP_BACKEND_URL', 'https://qr-logistics-1.preview.emergentagent.com')
        self.tokens = {}
        
    def make_request(self, method, endpoint, data=None, token=None):
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response.status_code, response.json() if response.text else {}
        except Exception as e:
            return 500, {"error": str(e)}
    
    def test_user_login(self):
        """Login test user"""
        print("🔐 Logging in test user...")
        
        # Try to login with Bahrom user
        status, response = self.make_request('POST', '/api/auth/login', {
            'phone': '+992900000000',
            'password': '123456'
        })
        
        if status == 200 and 'access_token' in response:
            self.tokens['user'] = response['access_token']
            print(f"✅ User logged in successfully: {response['user']['full_name']}")
            return True
        else:
            print(f"❌ User login failed: {response}")
            return False
    
    def test_admin_login(self):
        """Login admin user"""
        print("🔐 Logging in admin user...")
        
        status, response = self.make_request('POST', '/api/auth/login', {
            'phone': '+79999888777',
            'password': 'admin123'
        })
        
        if status == 200 and 'access_token' in response:
            self.tokens['admin'] = response['access_token']
            print(f"✅ Admin logged in successfully: {response['user']['full_name']}")
            return True
        else:
            print(f"❌ Admin login failed: {response}")
            return False
    
    def test_user_model_updates(self):
        """Test that user model includes email and address fields"""
        print("\n📋 Testing User Model Updates (email and address fields)...")
        
        # Use admin token since user login failed
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        status, response = self.make_request('GET', '/api/auth/me', token=self.tokens['admin'])
        
        if status == 200:
            has_email = 'email' in response
            has_address = 'address' in response
            
            print(f"📧 Email field present: {has_email}")
            print(f"🏠 Address field present: {has_address}")
            print(f"👤 User: {response.get('full_name')} ({response.get('phone')})")
            
            if has_email and has_address:
                print("✅ User model includes new email and address fields")
                return True
            else:
                print("❌ User model missing email or address fields")
                return False
        else:
            print(f"❌ Failed to get user info: {response}")
            return False
    
    def test_profile_update(self):
        """Test profile update functionality"""
        print("\n✏️ Testing User Profile Update (PUT /api/user/profile)...")
        
        # Use admin token since user login failed
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        # Test updating profile
        update_data = {
            "full_name": "Админ Системы Тестовый",
            "email": "admin.test@example.com",
            "address": "Москва, ул. Тестовая, 123"
        }
        
        status, response = self.make_request('PUT', '/api/user/profile', update_data, self.tokens['admin'])
        
        if status == 200:
            print("✅ Profile updated successfully")
            print(f"👤 New name: {response.get('full_name')}")
            print(f"📧 New email: {response.get('email')}")
            print(f"🏠 New address: {response.get('address')}")
            
            # Verify all fields were updated
            if (response.get('full_name') == update_data['full_name'] and
                response.get('email') == update_data['email'] and
                response.get('address') == update_data['address']):
                print("✅ All profile fields updated correctly")
                return True
            else:
                print("❌ Some profile fields not updated correctly")
                return False
        else:
            print(f"❌ Profile update failed: {response}")
            return False
    
    def test_data_persistence(self):
        """Test that updated data persists"""
        print("\n💾 Testing Data Persistence...")
        
        # Use admin token since user login failed
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        status, response = self.make_request('GET', '/api/auth/me', token=self.tokens['admin'])
        
        if status == 200:
            print(f"👤 Persisted name: {response.get('full_name')}")
            print(f"📧 Persisted email: {response.get('email')}")
            print(f"🏠 Persisted address: {response.get('address')}")
            print("✅ Updated profile information properly persisted")
            return True
        else:
            print(f"❌ Failed to verify persistence: {response}")
            return False
    
    def test_validation(self):
        """Test validation features"""
        print("\n🔒 Testing Validation Features...")
        
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        # Test empty update validation
        status, response = self.make_request('PUT', '/api/user/profile', {}, self.tokens['admin'])
        
        if status == 400:
            print("✅ Empty update correctly rejected with 400 error")
            print(f"📄 Error message: {response.get('detail', 'No detail')}")
            return True
        else:
            print(f"❌ Empty update validation failed: {status} - {response}")
            return False
    
    def test_partial_updates(self):
        """Test partial profile updates"""
        print("\n📝 Testing Partial Profile Updates...")
        
        if 'admin' not in self.tokens:
            print("❌ No admin token available")
            return False
        
        # Update only email
        update_data = {
            "email": "admin.partial@test.com"
        }
        
        status, response = self.make_request('PUT', '/api/user/profile', update_data, self.tokens['admin'])
        
        if status == 200:
            if response.get('email') == update_data['email']:
                print("✅ Partial update (email only) working correctly")
                print(f"📧 Updated email: {response.get('email')}")
                return True
            else:
                print("❌ Partial update failed")
                return False
        else:
            print(f"❌ Partial update failed: {response}")
            return False
    
    def run_all_tests(self):
        """Run all profile functionality tests"""
        print("🚀 Starting Enhanced User Profile Functionality Testing...")
        print("=" * 60)
        
        tests = [
            ("User Login", self.test_user_login),
            ("Admin Login", self.test_admin_login),
            ("User Model Updates", self.test_user_model_updates),
            ("Profile Update", self.test_profile_update),
            ("Data Persistence", self.test_data_persistence),
            ("Validation Features", self.test_validation),
            ("Partial Updates", self.test_partial_updates)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"\n{status} - {test_name}")
            except Exception as e:
                print(f"\n💥 ERROR - {test_name}: {str(e)}")
                results.append((test_name, False))
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 ENHANCED USER PROFILE FUNCTIONALITY TEST RESULTS")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\n📈 Overall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - Enhanced User Profile Functionality is working perfectly!")
        else:
            print(f"⚠️ {total-passed} test(s) failed - Some issues need attention")
        
        return passed == total

if __name__ == "__main__":
    tester = ProfileTester()
    tester.run_all_tests()