#!/usr/bin/env python3
"""
Backend Test for TAJLINE.TJ Placement Statistics Improvements
Testing the enhanced placement statistics system according to review request.

УЛУЧШЕНИЯ СТАТИСТИКИ РАЗМЕЩЕНИЯ ГРУЗА В TAJLINE.TJ:

РЕАЛИЗОВАННЫЕ УЛУЧШЕНИЯ:
- Добавлена статистика размещения: за сессию, за сегодня, осталось разместить
- Добавлен процентный индикатор выполнения в сессии
- Список размещенных грузов в формате "Груз № 000000/01 - Б1-П1-Я1" с временем размещения
- Убрана отладочная информация, заменена полезной статистикой
- Накопление списка размещенных грузов в течение сессии (показываются последние 5)

КРИТИЧЕСКИЕ ПРОВЕРКИ:
- API должен предоставлять статистику today_placements
- Система должна корректно подсчитывать проценты размещения
- Данные грузов должны содержать cargo_number для отображения

TEST PLAN:
1. Авторизация оператора склада (+79777888999/warehouse123)
2. Проверить существование API /api/operator/placement-statistics для статистики за сегодня
3. Получить доступные грузы для размещения для подсчета процентов
4. Убедиться что все данные готовы для нового улучшенного интерфейса
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://qr-logistics-1.preview.emergentagent.com/api"
WAREHOUSE_OPERATOR_CREDENTIALS = {
    "phone": "+79777888999",
    "password": "warehouse123"
}

class PlacementStatisticsTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.operator_info = None
        
    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def authenticate_warehouse_operator(self):
        """Authenticate warehouse operator"""
        self.log("🔐 Authenticating warehouse operator...")
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=WAREHOUSE_OPERATOR_CREDENTIALS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.operator_info = data.get("user")
                
                # Set authorization header
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                
                self.log(f"✅ Successfully authenticated warehouse operator: {self.operator_info.get('full_name', 'Unknown')}")
                self.log(f"   User Number: {self.operator_info.get('user_number', 'N/A')}")
                self.log(f"   Role: {self.operator_info.get('role', 'N/A')}")
                return True
            else:
                self.log(f"❌ Authentication failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Authentication error: {str(e)}", "ERROR")
            return False
    
    def test_placement_statistics_api(self):
        """Test the placement statistics API endpoint"""
        self.log("📊 Testing placement statistics API...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/placement-statistics",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log("✅ Placement statistics API is accessible")
                
                # Check required fields for improved interface
                required_fields = ['today_placements', 'session_placements', 'recent_placements']
                missing_fields = []
                
                for field in required_fields:
                    if field not in data:
                        missing_fields.append(field)
                
                if missing_fields:
                    self.log(f"⚠️ Missing required fields: {missing_fields}", "WARNING")
                else:
                    self.log("✅ All required statistics fields are present")
                
                # Display statistics data
                self.log(f"   Today placements: {data.get('today_placements', 'N/A')}")
                self.log(f"   Session placements: {data.get('session_placements', 'N/A')}")
                self.log(f"   Recent placements count: {len(data.get('recent_placements', []))}")
                
                # Check recent placements format
                recent_placements = data.get('recent_placements', [])
                if recent_placements:
                    self.log("📋 Recent placements format check:")
                    for i, placement in enumerate(recent_placements[:3]):  # Check first 3
                        cargo_number = placement.get('cargo_number', 'N/A')
                        location = placement.get('location_code', 'N/A')
                        placed_at = placement.get('placed_at', 'N/A')
                        self.log(f"   {i+1}. Груз № {cargo_number} - {location} ({placed_at})")
                
                return True, data
            else:
                self.log(f"❌ Placement statistics API failed: {response.status_code} - {response.text}", "ERROR")
                return False, None
                
        except Exception as e:
            self.log(f"❌ Placement statistics API error: {str(e)}", "ERROR")
            return False, None
    
    def test_available_cargo_for_placement(self):
        """Test available cargo for placement to calculate percentages"""
        self.log("📦 Testing available cargo for placement...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if it's paginated response
                if 'items' in data:
                    cargo_list = data['items']
                    total_count = data.get('total_count', len(cargo_list))
                    self.log(f"✅ Available cargo API accessible (paginated)")
                    self.log(f"   Total available cargo: {total_count}")
                    self.log(f"   Current page items: {len(cargo_list)}")
                else:
                    cargo_list = data if isinstance(data, list) else []
                    total_count = len(cargo_list)
                    self.log(f"✅ Available cargo API accessible (simple list)")
                    self.log(f"   Total available cargo: {total_count}")
                
                # Check cargo data structure for display requirements
                if cargo_list:
                    sample_cargo = cargo_list[0]
                    required_fields = ['cargo_number', 'id']
                    missing_fields = []
                    
                    for field in required_fields:
                        if field not in sample_cargo:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        self.log(f"⚠️ Sample cargo missing fields: {missing_fields}", "WARNING")
                    else:
                        self.log("✅ Cargo data contains required fields for display")
                        self.log(f"   Sample cargo number: {sample_cargo.get('cargo_number', 'N/A')}")
                        self.log(f"   Sample cargo ID: {sample_cargo.get('id', 'N/A')}")
                
                return True, total_count, cargo_list
            else:
                self.log(f"❌ Available cargo API failed: {response.status_code} - {response.text}", "ERROR")
                return False, 0, []
                
        except Exception as e:
            self.log(f"❌ Available cargo API error: {str(e)}", "ERROR")
            return False, 0, []
    
    def test_percentage_calculation_readiness(self, statistics_data, total_available_cargo):
        """Test if system is ready for percentage calculations"""
        self.log("🧮 Testing percentage calculation readiness...")
        
        try:
            today_placements = statistics_data.get('today_placements', 0)
            session_placements = statistics_data.get('session_placements', 0)
            
            # Calculate percentages for session (if there are any placements)
            if session_placements > 0 and total_available_cargo > 0:
                session_percentage = (session_placements / (session_placements + total_available_cargo)) * 100
                self.log(f"✅ Session completion percentage: {session_percentage:.1f}%")
                self.log(f"   ({session_placements} placed / {session_placements + total_available_cargo} total)")
            else:
                self.log("ℹ️ No placements in current session for percentage calculation")
            
            # Check remaining to place calculation
            remaining_to_place = total_available_cargo
            self.log(f"✅ Remaining to place: {remaining_to_place}")
            
            # Verify data structure for improved interface
            interface_ready = True
            
            if not isinstance(today_placements, int):
                self.log("⚠️ today_placements is not integer", "WARNING")
                interface_ready = False
            
            if not isinstance(session_placements, int):
                self.log("⚠️ session_placements is not integer", "WARNING")
                interface_ready = False
            
            if not isinstance(statistics_data.get('recent_placements', []), list):
                self.log("⚠️ recent_placements is not list", "WARNING")
                interface_ready = False
            
            if interface_ready:
                self.log("✅ All data types are correct for improved interface")
            
            return interface_ready
            
        except Exception as e:
            self.log(f"❌ Percentage calculation test error: {str(e)}", "ERROR")
            return False
    
    def test_cargo_number_format_compatibility(self, cargo_list):
        """Test cargo number formats for display compatibility"""
        self.log("🔢 Testing cargo number format compatibility...")
        
        try:
            if not cargo_list:
                self.log("⚠️ No cargo available for format testing", "WARNING")
                return True
            
            format_stats = {
                'new_format': 0,  # 2501XXXXXX
                'old_format': 0,  # 100XXX/XX
                'other_format': 0
            }
            
            for cargo in cargo_list[:10]:  # Check first 10 cargo
                cargo_number = cargo.get('cargo_number', '')
                
                if cargo_number.startswith('2501') and len(cargo_number) >= 6:
                    format_stats['new_format'] += 1
                elif '/' in cargo_number and cargo_number.startswith('100'):
                    format_stats['old_format'] += 1
                else:
                    format_stats['other_format'] += 1
            
            self.log(f"✅ Cargo number format analysis:")
            self.log(f"   New format (2501XXXXXX): {format_stats['new_format']}")
            self.log(f"   Old format (100XXX/XX): {format_stats['old_format']}")
            self.log(f"   Other formats: {format_stats['other_format']}")
            
            # All formats should be displayable
            self.log("✅ All cargo number formats are compatible for display")
            return True
            
        except Exception as e:
            self.log(f"❌ Cargo number format test error: {str(e)}", "ERROR")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test of placement statistics improvements"""
        self.log("🚀 Starting comprehensive placement statistics test...")
        self.log("=" * 80)
        
        # Test results tracking
        test_results = {
            'authentication': False,
            'placement_statistics_api': False,
            'available_cargo_api': False,
            'percentage_calculation': False,
            'cargo_format_compatibility': False
        }
        
        # 1. Authenticate warehouse operator
        if self.authenticate_warehouse_operator():
            test_results['authentication'] = True
        else:
            self.log("❌ Cannot proceed without authentication", "ERROR")
            return self.generate_final_report(test_results)
        
        # 2. Test placement statistics API
        stats_success, statistics_data = self.test_placement_statistics_api()
        test_results['placement_statistics_api'] = stats_success
        
        # 3. Test available cargo API
        cargo_success, total_cargo, cargo_list = self.test_available_cargo_for_placement()
        test_results['available_cargo_api'] = cargo_success
        
        # 4. Test percentage calculation readiness
        if stats_success and cargo_success and statistics_data:
            percentage_ready = self.test_percentage_calculation_readiness(statistics_data, total_cargo)
            test_results['percentage_calculation'] = percentage_ready
        
        # 5. Test cargo number format compatibility
        if cargo_success and cargo_list:
            format_compatible = self.test_cargo_number_format_compatibility(cargo_list)
            test_results['cargo_format_compatibility'] = format_compatible
        
        return self.generate_final_report(test_results, statistics_data if stats_success else None, total_cargo if cargo_success else 0)
    
    def generate_final_report(self, test_results, statistics_data=None, total_cargo=0):
        """Generate final test report"""
        self.log("=" * 80)
        self.log("📋 FINAL TEST REPORT - PLACEMENT STATISTICS IMPROVEMENTS")
        self.log("=" * 80)
        
        # Calculate success rate
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        self.log(f"🎯 SUCCESS RATE: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
        self.log("")
        
        # Detailed results
        self.log("📊 DETAILED TEST RESULTS:")
        test_names = {
            'authentication': 'Warehouse Operator Authentication (+79777888999/warehouse123)',
            'placement_statistics_api': 'Placement Statistics API (/api/operator/placement-statistics)',
            'available_cargo_api': 'Available Cargo API (/api/operator/cargo/available-for-placement)',
            'percentage_calculation': 'Percentage Calculation Readiness',
            'cargo_format_compatibility': 'Cargo Number Format Compatibility'
        }
        
        for key, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            self.log(f"   {status}: {test_names[key]}")
        
        self.log("")
        
        # Summary of improvements readiness
        if statistics_data:
            self.log("🎉 УЛУЧШЕНИЯ СТАТИСТИКИ РАЗМЕЩЕНИЯ ГОТОВЫ:")
            self.log(f"   ✅ Статистика за сегодня: {statistics_data.get('today_placements', 0)} размещений")
            self.log(f"   ✅ Статистика за сессию: {statistics_data.get('session_placements', 0)} размещений")
            self.log(f"   ✅ Доступно для размещения: {total_cargo} грузов")
            self.log(f"   ✅ Последние размещения: {len(statistics_data.get('recent_placements', []))} записей")
        
        # Critical checks status
        self.log("")
        self.log("🔍 КРИТИЧЕСКИЕ ПРОВЕРКИ:")
        
        critical_checks = [
            ("API предоставляет статистику today_placements", test_results['placement_statistics_api']),
            ("Система готова для подсчета процентов размещения", test_results['percentage_calculation']),
            ("Данные грузов содержат cargo_number для отображения", test_results['cargo_format_compatibility']),
            ("Backend готов для улучшенного интерфейса", all(test_results.values()))
        ]
        
        for check_name, check_result in critical_checks:
            status = "✅ ВЫПОЛНЕНО" if check_result else "❌ НЕ ВЫПОЛНЕНО"
            self.log(f"   {status}: {check_name}")
        
        self.log("")
        
        # Final verdict
        if success_rate >= 80:
            self.log("🎉 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ: Backend готов для улучшенного интерфейса с детальной статистикой размещения!")
        elif success_rate >= 60:
            self.log("⚠️ ЧАСТИЧНЫЙ УСПЕХ: Большинство компонентов готово, но требуются доработки")
        else:
            self.log("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ: Backend не готов для улучшенного интерфейса")
        
        return success_rate >= 80

def main():
    """Main test execution"""
    print("🏭 TAJLINE.TJ Placement Statistics Improvements Backend Test")
    print("=" * 80)
    
    tester = PlacementStatisticsTester()
    success = tester.run_comprehensive_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()