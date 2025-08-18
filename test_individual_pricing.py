#!/usr/bin/env python3
"""
Test script specifically for Individual Pricing Multi-Cargo Form functionality
"""

import requests
import json

class IndividualPricingTester:
    def __init__(self):
        self.base_url = "https://tajline-cargo-3.preview.emergentagent.com"
        self.admin_token = None
        
    def login_admin(self):
        """Login as admin to get token"""
        login_data = {
            "phone": "+79999888777",
            "password": "admin123"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/login", json=login_data)
        if response.status_code == 200:
            self.admin_token = response.json()['access_token']
            print("✅ Admin login successful")
            return True
        else:
            print(f"❌ Admin login failed: {response.status_code}")
            return False
    
    def test_individual_pricing_multi_cargo(self):
        """Test the enhanced multi-cargo form with individual pricing"""
        print("\n🎯 TESTING INDIVIDUAL PRICING MULTI-CARGO FORM")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return False
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        # Test 1: Multi-cargo with individual prices (PRIMARY TEST SCENARIO)
        print("\n   🧮 Testing Multi-Cargo with Individual Prices...")
        
        multi_cargo_data = {
            "sender_full_name": "Тест Отправитель",
            "sender_phone": "+79999999999",
            "recipient_full_name": "Тест Получатель",
            "recipient_phone": "+992999999999",
            "recipient_address": "Душанбе",
            "cargo_items": [
                {"cargo_name": "Документы", "weight": 10.0, "price_per_kg": 60.0},
                {"cargo_name": "Одежда", "weight": 25.0, "price_per_kg": 60.0},
                {"cargo_name": "Электроника", "weight": 100.0, "price_per_kg": 65.0}
            ],
            "description": "Разные виды груза с индивидуальными ценами",
            "route": "moscow_to_tajikistan"
        }
        
        response = requests.post(
            f"{self.base_url}/api/operator/cargo/accept",
            json=multi_cargo_data,
            headers=headers
        )
        
        print(f"   📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            cargo_number = result.get('cargo_number', 'N/A')
            total_weight = result.get('weight', 0)
            total_cost = result.get('declared_value', 0)
            cargo_name = result.get('cargo_name', 'N/A')
            description = result.get('description', '')
            
            print(f"   ✅ Multi-cargo with individual prices created: {cargo_number}")
            print(f"   📊 Total weight: {total_weight} kg")
            print(f"   💰 Total cost: {total_cost} руб")
            print(f"   🏷️  Combined cargo name: {cargo_name}")
            
            # Expected calculations:
            # Груз 1: 10 кг × 60 руб/кг = 600 руб
            # Груз 2: 25 кг × 60 руб/кг = 1500 руб  
            # Груз 3: 100 кг × 65 руб/кг = 6500 руб
            # Общий вес: 135 кг
            # Общая стоимость: 8600 руб
            expected_weight = 10.0 + 25.0 + 100.0  # 135 kg
            expected_cost = (10.0 * 60.0) + (25.0 * 60.0) + (100.0 * 65.0)  # 600 + 1500 + 6500 = 8600 rubles
            expected_name = "Документы, Одежда, Электроника"
            
            print(f"   🧮 Expected: {expected_weight}kg, {expected_cost}руб")
            print(f"   🧮 Actual: {total_weight}kg, {total_cost}руб")
            
            # Verify calculations
            if (abs(total_weight - expected_weight) < 0.01 and 
                abs(total_cost - expected_cost) < 0.01 and 
                cargo_name == expected_name):
                print("   ✅ Individual pricing calculations verified correctly")
                
                # Verify detailed description includes individual cost breakdown
                expected_breakdown_items = [
                    "1. Документы - 10.0 кг × 60.0 руб/кг = 600.0 руб",
                    "2. Одежда - 25.0 кг × 60.0 руб/кг = 1500.0 руб", 
                    "3. Электроника - 100.0 кг × 65.0 руб/кг = 6500.0 руб",
                    "Общий вес: 135.0 кг",
                    "Общая стоимость: 8600.0 руб"
                ]
                
                breakdown_verified = all(item in description for item in expected_breakdown_items)
                if breakdown_verified:
                    print("   ✅ Individual cost breakdown verified in description")
                    return True
                else:
                    print("   ❌ Individual cost breakdown missing or incorrect")
                    print(f"   📄 Description: {description[:300]}...")
                    return False
            else:
                print(f"   ❌ Individual pricing calculation error")
                return False
        else:
            print(f"   ❌ Request failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   📄 Error: {error_detail}")
            except:
                print(f"   📄 Raw response: {response.text[:200]}")
            return False
    
    def test_backward_compatibility(self):
        """Test single cargo mode for backward compatibility"""
        print("\n   📦 Testing Single Cargo Mode (Backward Compatibility)...")
        
        if not self.admin_token:
            print("❌ No admin token available")
            return False
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        single_cargo_data = {
            "sender_full_name": "Тест Отправитель",
            "sender_phone": "+79999999999",
            "recipient_full_name": "Тест Получатель",
            "recipient_phone": "+992999999999",
            "recipient_address": "Душанбе",
            "cargo_name": "Документы",
            "weight": 5.0,
            "declared_value": 300.0,
            "description": "Одиночный груз",
            "route": "moscow_to_tajikistan"
        }
        
        response = requests.post(
            f"{self.base_url}/api/operator/cargo/accept",
            json=single_cargo_data,
            headers=headers
        )
        
        print(f"   📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            cargo_number = result.get('cargo_number', 'N/A')
            weight = result.get('weight', 0)
            declared_value = result.get('declared_value', 0)
            cargo_name = result.get('cargo_name', 'N/A')
            
            print(f"   ✅ Single cargo created: {cargo_number}")
            print(f"   📊 Weight: {weight} kg, Value: {declared_value} руб")
            print(f"   🏷️  Cargo name: {cargo_name}")
            
            # Verify backward compatibility fields
            if weight == 5.0 and declared_value == 300.0 and cargo_name == "Документы":
                print("   ✅ Backward compatibility verified")
                return True
            else:
                print("   ❌ Backward compatibility failed")
                return False
        else:
            print(f"   ❌ Request failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   📄 Error: {error_detail}")
            except:
                print(f"   📄 Raw response: {response.text[:200]}")
            return False
    
    def run_tests(self):
        """Run all individual pricing tests"""
        print("🚀 Starting Individual Pricing Multi-Cargo Form Tests...")
        
        if not self.login_admin():
            return False
        
        test1_result = self.test_individual_pricing_multi_cargo()
        test2_result = self.test_backward_compatibility()
        
        print("\n" + "="*60)
        print("📊 INDIVIDUAL PRICING TEST RESULTS")
        print("="*60)
        print(f"✅ Individual Pricing Multi-Cargo: {'PASSED' if test1_result else 'FAILED'}")
        print(f"✅ Backward Compatibility: {'PASSED' if test2_result else 'FAILED'}")
        print(f"📈 Overall Success: {'PASSED' if test1_result and test2_result else 'FAILED'}")
        
        return test1_result and test2_result

if __name__ == "__main__":
    tester = IndividualPricingTester()
    success = tester.run_tests()
    exit(0 if success else 1)