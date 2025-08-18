#!/usr/bin/env python3
"""
Backend Test for TAJLINE.TJ Digital QR Code Display and React Error Fixes
Testing final fixes for digital QR code display and React error in TAJLINE.TJ

REVIEW REQUEST CONTEXT:
Протестировать ОКОНЧАТЕЛЬНЫЕ исправления отображения цифрового QR кода и React ошибки в TAJLINE.TJ:

1. Авторизация оператора склада (+79777888999/warehouse123)
2. Получить доступные грузы для размещения
3. КРИТИЧЕСКИЙ ТЕСТ: API /api/operator/cargo/place с обновленной структурой ответа
4. Проверить что ответ содержит правильные поля: warehouse_name, location_code, cargo_number, placed_at

ИСПРАВЛЕНИЯ ЗАВЕРШЕНЫ:
- Frontend: Поле ввода ячейки показывает цифровой код QR (03010101) вместо читаемого формата
- Frontend: Исправлена React ошибка в handlePlaceCargo с proper обработкой объекта response
- Backend: Обновлен /api/operator/cargo/place для возврата правильной структуры:
  * warehouse_name (вместо warehouse)
  * location_code (вместо location)
  * cargo_number (добавлено)
  * placed_at (добавлено)
  * cargo_name (добавлено)

ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: 
- API теперь возвращает совместимую структуру для frontend
- React ошибка "Objects are not valid as a React child" должна быть исправлена
- Цифровой QR код отображается в поле ввода ячейки
- Сообщения о размещении груза корректно отображаются
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

class QRDisplayReactFixesTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.operator_info = None
        self.available_cargo = []
        self.warehouses = []
        
    def authenticate_warehouse_operator(self):
        """1. Авторизация оператора склада (+79777888999/warehouse123)"""
        print("🔐 ЭТАП 1: Авторизация оператора склада...")
        
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
                
                print(f"✅ Успешная авторизация оператора склада:")
                print(f"   - Имя: {self.operator_info.get('full_name')}")
                print(f"   - Номер пользователя: {self.operator_info.get('user_number')}")
                print(f"   - Роль: {self.operator_info.get('role')}")
                print(f"   - Телефон: {self.operator_info.get('phone')}")
                
                if self.operator_info.get('role') != 'warehouse_operator':
                    print(f"⚠️  ПРЕДУПРЕЖДЕНИЕ: Ожидалась роль 'warehouse_operator', получена '{self.operator_info.get('role')}'")
                
                return True
            else:
                print(f"❌ Ошибка авторизации: {response.status_code}")
                print(f"   Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при авторизации: {e}")
            return False
    
    def get_available_cargo_for_placement(self):
        """2. Получить доступные грузы для размещения"""
        print("\n📦 ЭТАП 2: Получение доступных грузов для размещения...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response has items structure
                if 'items' in data:
                    self.available_cargo = data['items']
                    pagination = data.get('pagination', {})
                    
                    print(f"✅ Успешно получены доступные грузы:")
                    print(f"   - Всего грузов: {len(self.available_cargo)}")
                    print(f"   - Общее количество: {pagination.get('total_count', 'N/A')}")
                    print(f"   - Страница: {pagination.get('page', 'N/A')}")
                    
                    # Show first few cargo for testing
                    if self.available_cargo:
                        print(f"   - Первые грузы для тестирования:")
                        for i, cargo in enumerate(self.available_cargo[:3]):
                            print(f"     {i+1}. {cargo.get('cargo_number')} - {cargo.get('sender_full_name')} -> {cargo.get('recipient_full_name')}")
                            print(f"        Статус: {cargo.get('processing_status')}, Вес: {cargo.get('weight')}кг")
                    
                    return True
                else:
                    # Legacy format without pagination
                    self.available_cargo = data if isinstance(data, list) else []
                    print(f"✅ Получены доступные грузы (legacy format): {len(self.available_cargo)} грузов")
                    return True
                    
            else:
                print(f"❌ Ошибка получения грузов: {response.status_code}")
                print(f"   Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при получении грузов: {e}")
            return False
    
    def get_operator_warehouses(self):
        """Получить склады оператора для тестирования"""
        print("\n🏭 ДОПОЛНИТЕЛЬНО: Получение складов оператора...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/warehouses",
                timeout=10
            )
            
            if response.status_code == 200:
                self.warehouses = response.json()
                print(f"✅ Получены склады оператора: {len(self.warehouses)} складов")
                
                if self.warehouses:
                    print("   Доступные склады:")
                    for warehouse in self.warehouses[:3]:
                        print(f"   - {warehouse.get('name')} (ID: {warehouse.get('id')})")
                        print(f"     Местоположение: {warehouse.get('location')}")
                        if 'warehouse_number' in warehouse:
                            print(f"     Номер склада: {warehouse.get('warehouse_number')}")
                        if 'warehouse_id_number' in warehouse:
                            print(f"     ID номер склада: {warehouse.get('warehouse_id_number')}")
                
                return True
            else:
                print(f"⚠️  Не удалось получить склады: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️  Исключение при получении складов: {e}")
            return False
    
    def test_cargo_place_api_structure(self):
        """3. КРИТИЧЕСКИЙ ТЕСТ: API /api/operator/cargo/place с обновленной структурой ответа"""
        print("\n🎯 ЭТАП 3: КРИТИЧЕСКИЙ ТЕСТ - API /api/operator/cargo/place структура ответа...")
        
        if not self.available_cargo:
            print("❌ Нет доступных грузов для тестирования")
            return False
        
        if not self.warehouses:
            print("❌ Нет доступных складов для тестирования")
            return False
        
        # Use first available cargo and warehouse
        test_cargo = self.available_cargo[0]
        test_warehouse = self.warehouses[0]
        
        cargo_id = test_cargo.get('id')
        warehouse_id = test_warehouse.get('id')
        
        print(f"   Тестовый груз: {test_cargo.get('cargo_number')}")
        print(f"   Тестовый склад: {test_warehouse.get('name')}")
        
        # Test data for cargo placement
        placement_data = {
            "cargo_id": cargo_id,
            "warehouse_id": warehouse_id,
            "block_number": 1,
            "shelf_number": 1,
            "cell_number": 1
        }
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/place",
                json=placement_data,
                timeout=10
            )
            
            print(f"   Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API /api/operator/cargo/place работает!")
                print(f"   Структура ответа: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                # Check for required fields according to review request
                required_fields = ['warehouse_name', 'location_code', 'cargo_number', 'placed_at']
                optional_fields = ['cargo_name']
                
                print(f"\n🔍 ПРОВЕРКА СТРУКТУРЫ ОТВЕТА:")
                all_required_present = True
                
                for field in required_fields:
                    if field in data:
                        print(f"   ✅ {field}: {data[field]}")
                    else:
                        print(f"   ❌ ОТСУТСТВУЕТ ОБЯЗАТЕЛЬНОЕ ПОЛЕ: {field}")
                        all_required_present = False
                
                for field in optional_fields:
                    if field in data:
                        print(f"   ✅ {field} (опционально): {data[field]}")
                    else:
                        print(f"   ⚠️  {field} (опционально): отсутствует")
                
                # Check for old fields that should be replaced
                old_fields = ['message', 'location', 'warehouse']
                old_fields_found = []
                for field in old_fields:
                    if field in data:
                        old_fields_found.append(field)
                        print(f"   ⚠️  СТАРОЕ ПОЛЕ (должно быть заменено): {field}: {data[field]}")
                
                if all_required_present:
                    print(f"\n🎉 КРИТИЧЕСКИЙ УСПЕХ: Все обязательные поля присутствуют!")
                    print(f"   - warehouse_name: ✅")
                    print(f"   - location_code: ✅") 
                    print(f"   - cargo_number: ✅")
                    print(f"   - placed_at: ✅")
                    
                    if old_fields_found:
                        print(f"   ⚠️  Найдены старые поля: {old_fields_found}")
                        print(f"   Это может указывать на неполное обновление API")
                    
                    return True
                else:
                    print(f"\n❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Отсутствуют обязательные поля!")
                    print(f"   Frontend ожидает: {required_fields}")
                    print(f"   Получено: {list(data.keys())}")
                    return False
                    
            elif response.status_code == 400:
                error_data = response.json()
                print(f"⚠️  Ошибка размещения (ожидаемо): {error_data.get('detail', 'Unknown error')}")
                
                # This might be expected if cargo is already placed or cell is occupied
                # Let's try with different coordinates
                print(f"   Пробуем другие координаты...")
                
                for cell_num in range(2, 6):  # Try cells 2-5
                    placement_data['cell_number'] = cell_num
                    retry_response = self.session.post(
                        f"{BACKEND_URL}/operator/cargo/place",
                        json=placement_data,
                        timeout=10
                    )
                    
                    if retry_response.status_code == 200:
                        print(f"   ✅ Успешно с ячейкой {cell_num}")
                        return self.analyze_response_structure(retry_response.json())
                    
                print(f"   ❌ Не удалось разместить груз ни в одну ячейку")
                return False
                
            else:
                print(f"❌ Неожиданная ошибка API: {response.status_code}")
                print(f"   Ответ: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при тестировании API: {e}")
            return False
    
    def analyze_response_structure(self, data):
        """Analyze the response structure for required fields"""
        required_fields = ['warehouse_name', 'location_code', 'cargo_number', 'placed_at']
        
        print(f"🔍 АНАЛИЗ СТРУКТУРЫ ОТВЕТА:")
        all_required_present = True
        
        for field in required_fields:
            if field in data:
                print(f"   ✅ {field}: {data[field]}")
            else:
                print(f"   ❌ ОТСУТСТВУЕТ: {field}")
                all_required_present = False
        
        return all_required_present
    
    def test_digital_qr_support(self):
        """4. Проверить поддержку цифрового QR формата (03010101)"""
        print("\n🔢 ЭТАП 4: Проверка поддержки цифрового QR формата...")
        
        if not self.warehouses:
            print("❌ Нет складов для проверки цифрового формата")
            return False
        
        digital_format_ready = True
        
        for warehouse in self.warehouses[:3]:  # Check first 3 warehouses
            warehouse_name = warehouse.get('name', 'Unknown')
            warehouse_number = warehouse.get('warehouse_number')
            warehouse_id_number = warehouse.get('warehouse_id_number')
            
            print(f"   Склад: {warehouse_name}")
            
            if warehouse_number is not None:
                print(f"   ✅ warehouse_number: {warehouse_number}")
            else:
                print(f"   ❌ warehouse_number: отсутствует")
                digital_format_ready = False
            
            if warehouse_id_number is not None:
                print(f"   ✅ warehouse_id_number: {warehouse_id_number}")
            else:
                print(f"   ⚠️  warehouse_id_number: отсутствует (может быть не критично)")
        
        if digital_format_ready:
            print(f"\n✅ ПОДДЕРЖКА ЦИФРОВОГО QR ФОРМАТА: Готова")
            print(f"   Склады имеют необходимые поля для формата 03010101")
        else:
            print(f"\n⚠️  ПОДДЕРЖКА ЦИФРОВОГО QR ФОРМАТА: Частично готова")
            print(f"   Некоторые склады не имеют warehouse_number")
        
        return digital_format_ready
    
    def run_comprehensive_test(self):
        """Запустить полное тестирование исправлений"""
        print("🚀 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Исправления отображения цифрового QR кода и React ошибки в TAJLINE.TJ")
        print("=" * 100)
        
        test_results = {
            "warehouse_operator_auth": False,
            "available_cargo_retrieval": False,
            "cargo_place_api_structure": False,
            "digital_qr_support": False
        }
        
        # Step 1: Authenticate warehouse operator
        test_results["warehouse_operator_auth"] = self.authenticate_warehouse_operator()
        
        if not test_results["warehouse_operator_auth"]:
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как оператор склада")
            return self.generate_final_report(test_results)
        
        # Step 2: Get available cargo for placement
        test_results["available_cargo_retrieval"] = self.get_available_cargo_for_placement()
        
        # Get warehouses for testing
        self.get_operator_warehouses()
        
        # Step 3: Test critical API structure
        test_results["cargo_place_api_structure"] = self.test_cargo_place_api_structure()
        
        # Step 4: Test digital QR support
        test_results["digital_qr_support"] = self.test_digital_qr_support()
        
        return self.generate_final_report(test_results)
    
    def generate_final_report(self, test_results):
        """Генерировать финальный отчет"""
        print("\n" + "=" * 100)
        print("📊 ФИНАЛЬНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
        print("=" * 100)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"📈 ОБЩИЙ РЕЗУЛЬТАТ: {passed_tests}/{total_tests} тестов пройдено ({success_rate:.1f}% успешности)")
        print()
        
        # Detailed results
        test_descriptions = {
            "warehouse_operator_auth": "1. Авторизация оператора склада (+79777888999/warehouse123)",
            "available_cargo_retrieval": "2. Получение доступных грузов для размещения", 
            "cargo_place_api_structure": "3. КРИТИЧЕСКИЙ ТЕСТ: API /api/operator/cargo/place структура ответа",
            "digital_qr_support": "4. Поддержка цифрового QR формата (03010101)"
        }
        
        for test_key, passed in test_results.items():
            status = "✅ ПРОЙДЕН" if passed else "❌ ПРОВАЛЕН"
            description = test_descriptions.get(test_key, test_key)
            print(f"{status}: {description}")
        
        print()
        
        # Critical analysis
        if test_results["cargo_place_api_structure"]:
            print("🎉 КРИТИЧЕСКИЙ УСПЕХ: API /api/operator/cargo/place возвращает правильную структуру!")
            print("   - warehouse_name: ✅")
            print("   - location_code: ✅")
            print("   - cargo_number: ✅") 
            print("   - placed_at: ✅")
            print("   React ошибка 'Objects are not valid as a React child' должна быть исправлена!")
        else:
            print("🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: API /api/operator/cargo/place НЕ возвращает ожидаемую структуру!")
            print("   Frontend ожидает: warehouse_name, location_code, cargo_number, placed_at")
            print("   Это блокирует исправление React ошибки!")
        
        if test_results["digital_qr_support"]:
            print("✅ ЦИФРОВОЙ QR ФОРМАТ: Поддержка готова")
            print("   Поле ввода ячейки может отображать цифровой код (03010101)")
        else:
            print("⚠️  ЦИФРОВОЙ QR ФОРМАТ: Частичная поддержка")
        
        print()
        
        # Final verdict
        if success_rate >= 75:
            print("🎯 ЗАКЛЮЧЕНИЕ: Исправления в основном завершены успешно!")
            if test_results["cargo_place_api_structure"]:
                print("   Основная проблема React ошибки решена через правильную структуру API")
        else:
            print("⚠️  ЗАКЛЮЧЕНИЕ: Исправления требуют дополнительной работы")
            print("   Критические проблемы блокируют полное исправление ошибок")
        
        return success_rate >= 75

def main():
    """Main test execution"""
    print("🔧 BACKEND STABILITY TESTING FOR QR DISPLAY AND REACT FIXES")
    print("Testing final fixes for digital QR code display and React error in TAJLINE.TJ")
    print()
    
    tester = QRDisplayReactFixesTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО")
        sys.exit(0)
    else:
        print("\n❌ ТЕСТИРОВАНИЕ ВЫЯВИЛО КРИТИЧЕСКИЕ ПРОБЛЕМЫ")
        sys.exit(1)

if __name__ == "__main__":
    main()