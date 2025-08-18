#!/usr/bin/env python3
"""
🎯 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ НАВИГАЦИИ ЧАТА: Проверить что исправление работает правильно

КОНТЕКСТ ПРОБЛЕМЫ:
Пользователь сообщил что при нажатии на кнопку "💬 ЧАТ" открываются 3 подкатегории:
1. Чаты по грузам  
2. Поддержка
3. Статистика чатов

НО при выборе любой из этих подкатегорий через личный кабинет оператора и админа кнопки НЕ реагируют и не переключают на соответствующую секцию чата.

ИСПРАВЛЕНИЕ ВЫПОЛНЕНО:
В файле /app/frontend/src/App.js исправлены обработчики кликов по подсекциям в двух местах:
1. Десктопное меню - добавлено setActiveSection(item.section) 
2. Мобильное меню - добавлено setActiveSection(item.section)

ЗАДАЧА ТЕСТИРОВАНИЯ:
1. Проверить что все backend API endpoints для чата работают корректно
2. Убедиться что endpoints доступны для ролей admin и warehouse_operator
3. Протестировать основные API endpoints системы чата:
   - GET /api/chat/list - получение списка чатов
   - GET /api/chat/unread-count - подсчет непрочитанных сообщений  
   - GET /api/chat/stats - статистика чатов (для админов)
   - GET /api/users/list-for-chat - список пользователей для создания чата

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:
- Все API endpoints чата работают корректно
- Нет ошибок авторизации или доступа 
- Backend готов поддерживать исправленную навигацию frontend

ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ:
- Система: TAJLINE.TJ cargo management system
- Роли для тестирования: admin, warehouse_operator  
- Backend: FastAPI + MongoDB
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

class ChatNavigationTester:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.test_results = []
        
    def log_result(self, test_name, success, details="", error_msg=""):
        """Log test result"""
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
            print(f"   📋 {details}")
        if error_msg:
            print(f"   ⚠️ {error_msg}")
        print()

    def authenticate_user(self, credentials, role_name):
        """Authenticate user and get JWT token"""
        try:
            print(f"🔐 Authenticating {role_name}...")
            
            response = requests.post(
                f"{BACKEND_URL}/auth/login",
                json=credentials,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                user_info = data.get("user", {})
                
                self.log_result(
                    f"Authentication - {role_name}",
                    True,
                    f"User: {user_info.get('full_name', 'Unknown')} (Role: {user_info.get('role', 'Unknown')})"
                )
                return token
            else:
                self.log_result(
                    f"Authentication - {role_name}",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
                return None
                
        except Exception as e:
            self.log_result(
                f"Authentication - {role_name}",
                False,
                "",
                str(e)
            )
            return None

    def test_endpoint(self, endpoint, token, role_name, expected_fields=None):
        """Test a specific endpoint"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                details = f"HTTP 200 - Data received"
                
                # Check expected fields if provided
                if expected_fields:
                    missing_fields = []
                    for field in expected_fields:
                        if field not in data:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        details += f" (Missing fields: {', '.join(missing_fields)})"
                    else:
                        details += f" (All expected fields present)"
                
                # Add data size info
                if isinstance(data, list):
                    details += f" - {len(data)} items"
                elif isinstance(data, dict):
                    details += f" - {len(data)} fields"
                
                self.log_result(
                    f"{endpoint} - {role_name}",
                    True,
                    details
                )
                return True, data
            else:
                self.log_result(
                    f"{endpoint} - {role_name}",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200] if response.text else "No response body"
                )
                return False, None
                
        except Exception as e:
            self.log_result(
                f"{endpoint} - {role_name}",
                False,
                "",
                str(e)
            )
            return False, None

    def test_chat_list_endpoint(self):
        """Test GET /api/chat/list endpoint"""
        print("📋 Testing Chat List Endpoint...")
        
        # Test with admin
        if self.admin_token:
            success, data = self.test_endpoint("/chat/list", self.admin_token, "Admin")
            if success and data:
                # Analyze chat list structure
                if isinstance(data, list):
                    print(f"   📊 Found {len(data)} chats")
                elif isinstance(data, dict) and 'chats' in data:
                    chats = data.get('chats', [])
                    print(f"   📊 Found {len(chats)} chats in response")
        
        # Test with operator
        if self.operator_token:
            success, data = self.test_endpoint("/chat/list", self.operator_token, "Operator")

    def test_chat_stats_endpoint(self):
        """Test GET /api/chat/stats endpoint (admin only)"""
        print("📊 Testing Chat Stats Endpoint...")
        
        # Test with admin
        if self.admin_token:
            expected_fields = ["total_chats", "active_chats", "total_messages"]
            success, data = self.test_endpoint("/chat/stats", self.admin_token, "Admin", expected_fields)
            
            if success and data:
                print(f"   📈 Chat Statistics:")
                for key, value in data.items():
                    print(f"      {key}: {value}")
        
        # Test with operator (should work or give appropriate error)
        if self.operator_token:
            success, data = self.test_endpoint("/chat/stats", self.operator_token, "Operator")

    def test_unread_count_endpoint(self):
        """Test GET /api/chat/unread-count endpoint"""
        print("🔔 Testing Unread Count Endpoint...")
        
        # This endpoint might not exist, so we'll test if it's available
        endpoints_to_try = [
            "/chat/unread-count",
            "/chat/unread",
            "/notifications/unread-count"
        ]
        
        for endpoint in endpoints_to_try:
            print(f"   Trying {endpoint}...")
            
            if self.admin_token:
                success, data = self.test_endpoint(endpoint, self.admin_token, "Admin")
                if success:
                    break
            
            if self.operator_token:
                success, data = self.test_endpoint(endpoint, self.operator_token, "Operator")
                if success:
                    break

    def test_users_for_chat_endpoint(self):
        """Test GET /api/users/list-for-chat endpoint"""
        print("👥 Testing Users for Chat Endpoint...")
        
        # This endpoint might not exist, so we'll test variations
        endpoints_to_try = [
            "/users/list-for-chat",
            "/users/chat-list", 
            "/admin/users",
            "/users"
        ]
        
        for endpoint in endpoints_to_try:
            print(f"   Trying {endpoint}...")
            
            if self.admin_token:
                success, data = self.test_endpoint(endpoint, self.admin_token, "Admin")
                if success and data:
                    if isinstance(data, list):
                        print(f"      📊 Found {len(data)} users")
                    elif isinstance(data, dict) and 'users' in data:
                        users = data.get('users', [])
                        print(f"      📊 Found {len(users)} users")
                    break

    def test_additional_chat_endpoints(self):
        """Test additional chat-related endpoints"""
        print("🔍 Testing Additional Chat Endpoints...")
        
        additional_endpoints = [
            "/chat/create",
            "/notifications",
            "/chat"
        ]
        
        for endpoint in additional_endpoints:
            if self.admin_token:
                # For POST endpoints, we'll just check if they exist (might get 400/422 but not 404)
                try:
                    headers = {"Authorization": f"Bearer {self.admin_token}"}
                    if endpoint == "/chat/create":
                        # Try POST for create endpoint
                        response = requests.post(f"{BACKEND_URL}{endpoint}", headers=headers, json={})
                    else:
                        response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers)
                    
                    if response.status_code != 404:
                        self.log_result(
                            f"{endpoint} - Endpoint exists",
                            True,
                            f"HTTP {response.status_code} (endpoint available)"
                        )
                    else:
                        self.log_result(
                            f"{endpoint} - Endpoint exists",
                            False,
                            f"HTTP 404 - Endpoint not found"
                        )
                except Exception as e:
                    self.log_result(
                        f"{endpoint} - Endpoint test",
                        False,
                        "",
                        str(e)
                    )

    def run_comprehensive_test(self):
        """Run comprehensive chat navigation backend test"""
        print("🎯 STARTING CHAT NAVIGATION BACKEND TESTING")
        print("=" * 60)
        print()
        
        # Step 1: Authenticate users
        print("🔐 AUTHENTICATION PHASE")
        print("-" * 30)
        self.admin_token = self.authenticate_user(ADMIN_CREDENTIALS, "Administrator")
        self.operator_token = self.authenticate_user(OPERATOR_CREDENTIALS, "Warehouse Operator")
        print()
        
        if not self.admin_token and not self.operator_token:
            print("❌ CRITICAL ERROR: No successful authentication. Cannot proceed with testing.")
            return
        
        # Step 2: Test core chat endpoints
        print("💬 CORE CHAT ENDPOINTS TESTING")
        print("-" * 35)
        self.test_chat_list_endpoint()
        self.test_chat_stats_endpoint()
        self.test_unread_count_endpoint()
        self.test_users_for_chat_endpoint()
        print()
        
        # Step 3: Test additional endpoints
        print("🔍 ADDITIONAL ENDPOINTS TESTING")
        print("-" * 35)
        self.test_additional_chat_endpoints()
        print()
        
        # Step 4: Generate summary
        self.generate_test_summary()

    def generate_test_summary(self):
        """Generate comprehensive test summary"""
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        # Group results by category
        auth_tests = [r for r in self.test_results if "Authentication" in r["test"]]
        endpoint_tests = [r for r in self.test_results if "Authentication" not in r["test"]]
        
        print("🔐 AUTHENTICATION RESULTS:")
        for result in auth_tests:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['test']}")
        print()
        
        print("🌐 ENDPOINT TESTING RESULTS:")
        for result in endpoint_tests:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['test']}")
            if result["details"]:
                print(f"      📋 {result['details']}")
        print()
        
        # Critical findings
        print("🎯 CRITICAL FINDINGS:")
        
        # Check if core chat endpoints work
        chat_list_works = any(r["success"] and "/chat/list" in r["test"] for r in self.test_results)
        chat_stats_works = any(r["success"] and "/chat/stats" in r["test"] for r in self.test_results)
        
        if chat_list_works:
            print("  ✅ Chat list endpoint is functional")
        else:
            print("  ❌ Chat list endpoint has issues")
            
        if chat_stats_works:
            print("  ✅ Chat stats endpoint is functional")
        else:
            print("  ❌ Chat stats endpoint has issues")
        
        # Check authentication
        auth_success = any(r["success"] and "Authentication" in r["test"] for r in self.test_results)
        if auth_success:
            print("  ✅ Authentication system is working")
        else:
            print("  ❌ Authentication system has critical issues")
        
        print()
        print("🎯 CONCLUSION:")
        if success_rate >= 80:
            print("  ✅ Backend chat system is ready to support frontend navigation fixes")
        elif success_rate >= 60:
            print("  ⚠️ Backend chat system has some issues but core functionality works")
        else:
            print("  ❌ Backend chat system has critical issues that need attention")
        
        print()
        print("📝 RECOMMENDATION:")
        if success_rate >= 80:
            print("  The backend API endpoints are working correctly and can support the")
            print("  frontend navigation fixes. The chat navigation should work properly.")
        else:
            print("  Some backend endpoints need attention before the frontend navigation")
            print("  fixes can work optimally. Focus on fixing failed endpoints.")

if __name__ == "__main__":
    print("🎯 CHAT NAVIGATION BACKEND TESTING")
    print("Testing backend API endpoints for chat navigation fix")
    print("=" * 60)
    print()
    
    tester = ChatNavigationTester()
    tester.run_comprehensive_test()
    
    print("\n" + "=" * 60)
    print("🎯 CHAT NAVIGATION BACKEND TESTING COMPLETED")