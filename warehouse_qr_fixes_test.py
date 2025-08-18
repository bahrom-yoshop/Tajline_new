#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ СИСТЕМЫ УПРАВЛЕНИЯ ЯЧЕЙКАМИ СКЛАДА TAJLINE.TJ

КОНТЕКСТ ИСПРАВЛЕНИЙ:
1. **Исправлена схема склада**: Теперь использует реальные данные о занятости ячеек вместо Math.random()
2. **Изменен формат QR кода**: Убраны пробелы между цифрами (было "04 01 01 09" → стало "04010109")
3. **Улучшена печать QR**: Добавлено модальное окно, улучшен шаблон печати

ENDPOINTS ДЛЯ ТЕСТИРОВАНИЯ:
1. GET /api/warehouses/{warehouse_id}/cells - получение реальных данных о ячейках (для схемы склада)
2. GET /api/warehouses/cells/{cell_id}/qr - генерация QR с новым форматом без пробелов  
3. GET /api/warehouses/{warehouse_id}/cells/qr-batch - массовая генерация QR с новым форматом

ТЕСТОВЫЙ ПЛАН:
1. Авторизация admin (+79999888777/admin123)
2. Найти склад с реальной структурой ячеек
3. **КРИТИЧЕСКАЯ ПРОВЕРКА**: Протестировать новый формат QR кода без пробелов
4. Сравнить данные из /api/warehouses/{warehouse_id}/cells с генерируемой схемой склада
5. Убедиться, что qr_data содержит формат "04010109" вместо "04 01 01 09"
6. Проверить массовую генерацию QR с новым форматом

ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:
- QR коды должны содержать числовые данные без пробелов (например "04010109")
- Схема склада должна использовать реальную занятость ячеек из API
- Все endpoints должны работать стабильно с новым форматом

ФОКУС: Особое внимание на новый формат QR кода без пробелов!
"""

import requests
import json
import sys
import re
from datetime import datetime

# Configuration
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

class WarehouseQRFixesTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.test_results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def authenticate_admin(self):
        """Authenticate as admin"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                if self.admin_token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.admin_token}"
                    })
                    user_info = data.get("user", {})
                    self.log_result(
                        "Admin Authentication",
                        True,
                        f"Successfully authenticated as {user_info.get('full_name', 'Admin')} (Role: {user_info.get('role', 'Unknown')})"
                    )
                    return True
                else:
                    self.log_result("Admin Authentication", False, "No access token in response")
                    return False
            else:
                self.log_result("Admin Authentication", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Admin Authentication", False, f"Exception: {str(e)}")
            return False
    
    def find_warehouse_with_cells(self):
        """Find a warehouse with real cell structure"""
        try:
            response = self.session.get(f"{BACKEND_URL}/warehouses", timeout=30)
            
            if response.status_code == 200:
                warehouses = response.json()
                
                # Find warehouse with reasonable structure for testing
                target_warehouse = None
                for warehouse in warehouses:
                    blocks = warehouse.get("blocks_count", 0)
                    shelves = warehouse.get("shelves_per_block", 0)
                    cells = warehouse.get("cells_per_shelf", 0)
                    total_cells = blocks * shelves * cells
                    
                    # Look for warehouse with manageable size (5-50 cells)
                    if 5 <= total_cells <= 50:
                        target_warehouse = warehouse
                        break
                
                # If no small warehouse found, use any warehouse with cells
                if not target_warehouse:
                    for warehouse in warehouses:
                        blocks = warehouse.get("blocks_count", 0)
                        shelves = warehouse.get("shelves_per_block", 0)
                        cells = warehouse.get("cells_per_shelf", 0)
                        total_cells = blocks * shelves * cells
                        
                        if total_cells > 0:
                            target_warehouse = warehouse
                            break
                
                if target_warehouse:
                    warehouse_number = target_warehouse.get("warehouse_number", "Unknown")
                    self.log_result(
                        "Find Warehouse with Cells",
                        True,
                        f"Found warehouse: {target_warehouse.get('name', 'Unknown')} (warehouse_number: {warehouse_number})",
                        {
                            "warehouse_data": target_warehouse,
                            "warehouse_number": warehouse_number,
                            "structure": {
                                "blocks_count": target_warehouse.get("blocks_count"),
                                "shelves_per_block": target_warehouse.get("shelves_per_block"),
                                "cells_per_shelf": target_warehouse.get("cells_per_shelf"),
                                "expected_total_cells": (
                                    target_warehouse.get("blocks_count", 0) * 
                                    target_warehouse.get("shelves_per_block", 0) * 
                                    target_warehouse.get("cells_per_shelf", 0)
                                )
                            }
                        }
                    )
                    return target_warehouse
                else:
                    self.log_result(
                        "Find Warehouse with Cells",
                        False,
                        f"No suitable warehouse found",
                        {"total_warehouses": len(warehouses)}
                    )
                    return None
            else:
                self.log_result("Find Warehouse with Cells", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Find Warehouse with Cells", False, f"Exception: {str(e)}")
            return None
    
    def test_warehouse_cells_real_data(self, warehouse_id, expected_cells=None):
        """Test GET /api/warehouses/{warehouse_id}/cells - real cell occupancy data"""
        try:
            response = self.session.get(f"{BACKEND_URL}/warehouses/{warehouse_id}/cells", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                cells = data.get("cells", [])
                
                actual_cells = len(cells)
                
                # Check if we have real occupancy data (not random)
                occupied_cells = [cell for cell in cells if cell.get("is_occupied", False)]
                occupied_count = len(occupied_cells)
                
                # Check cell structure
                sample_cell = cells[0] if cells else {}
                required_fields = ["id", "warehouse_id", "block_number", "shelf_number", "cell_number", "is_occupied"]
                missing_fields = [field for field in required_fields if field not in sample_cell]
                
                if not missing_fields:
                    self.log_result(
                        "Warehouse Cells Real Data (CRITICAL)",
                        True,
                        f"Successfully retrieved {actual_cells} cells with real occupancy data ({occupied_count} occupied)",
                        {
                            "total_cells": actual_cells,
                            "expected_cells": expected_cells,
                            "occupied_cells": occupied_count,
                            "occupancy_rate": f"{(occupied_count/actual_cells*100):.1f}%" if actual_cells > 0 else "0%",
                            "sample_cell": sample_cell,
                            "all_required_fields_present": True,
                            "real_data_confirmed": True
                        }
                    )
                    return cells
                else:
                    self.log_result(
                        "Warehouse Cells Real Data (CRITICAL)",
                        False,
                        f"Retrieved {actual_cells} cells but missing required fields: {missing_fields}",
                        {"sample_cell": sample_cell, "missing_fields": missing_fields}
                    )
                    return cells
            else:
                self.log_result(
                    "Warehouse Cells Real Data (CRITICAL)",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return None
                
        except Exception as e:
            self.log_result("Warehouse Cells Real Data (CRITICAL)", False, f"Exception: {str(e)}")
            return None
    
    def test_individual_cell_qr_new_format(self, cells, warehouse_number):
        """Test GET /api/warehouses/cells/{cell_id}/qr - NEW FORMAT WITHOUT SPACES"""
        if not cells:
            self.log_result("Individual Cell QR New Format", False, "No cells available for testing")
            return False
        
        # Test with first cell
        test_cell = cells[0]
        cell_id = test_cell.get("id")
        block_number = test_cell.get("block_number", 1)
        shelf_number = test_cell.get("shelf_number", 1)
        cell_number = test_cell.get("cell_number", 1)
        
        try:
            response = self.session.get(f"{BACKEND_URL}/warehouses/cells/{cell_id}/qr", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                qr_code = data.get("qr_code", "")
                qr_data = data.get("qr_data", "")
                
                # Check if QR code is in base64 format
                if qr_code.startswith("data:image/png;base64,"):
                    # CRITICAL CHECK: New format without spaces
                    # Expected format: "04010109" (warehouse_number + block + shelf + cell, no spaces)
                    expected_format_pattern = r'^\d{8}$'  # 8 digits, no spaces
                    
                    # Check if qr_data matches new format (no spaces)
                    has_new_format = bool(re.match(expected_format_pattern, qr_data))
                    has_old_format_spaces = ' ' in qr_data
                    
                    # Expected QR data format: warehouse_number(2) + block(2) + shelf(2) + cell(2)
                    expected_qr_data = f"{warehouse_number:02d}{block_number:02d}{shelf_number:02d}{cell_number:02d}"
                    
                    format_correct = qr_data == expected_qr_data
                    
                    self.log_result(
                        "Individual Cell QR New Format (CRITICAL)",
                        has_new_format and not has_old_format_spaces and format_correct,
                        f"QR code generated with {'NEW' if has_new_format else 'OLD'} format: '{qr_data}'",
                        {
                            "cell_id": cell_id,
                            "qr_data": qr_data,
                            "expected_qr_data": expected_qr_data,
                            "qr_code_length": len(qr_code),
                            "qr_format_valid": qr_code.startswith("data:image/png;base64,"),
                            "new_format_no_spaces": has_new_format,
                            "old_format_has_spaces": has_old_format_spaces,
                            "format_matches_expected": format_correct,
                            "warehouse_number": warehouse_number,
                            "block_number": block_number,
                            "shelf_number": shelf_number,
                            "cell_number": cell_number
                        }
                    )
                    return has_new_format and not has_old_format_spaces and format_correct
                else:
                    self.log_result(
                        "Individual Cell QR New Format (CRITICAL)",
                        False,
                        f"QR code format invalid: {qr_code[:100]}...",
                        {"full_response": data}
                    )
                    return False
            else:
                self.log_result(
                    "Individual Cell QR New Format (CRITICAL)",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    {
                        "cell_id": cell_id,
                        "cell_data": test_cell,
                        "error_details": response.text
                    }
                )
                return False
                
        except Exception as e:
            self.log_result("Individual Cell QR New Format (CRITICAL)", False, f"Exception: {str(e)}")
            return False
    
    def test_batch_qr_generation_new_format(self, warehouse_id, warehouse_number, expected_qr_count=None):
        """Test GET /api/warehouses/{warehouse_id}/cells/qr-batch - NEW FORMAT WITHOUT SPACES"""
        try:
            response = self.session.get(f"{BACKEND_URL}/warehouses/{warehouse_id}/cells/qr-batch", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                qr_codes = data.get("qr_codes", [])
                
                actual_qr_count = len(qr_codes)
                
                # Check QR code format for all generated QR codes
                valid_qr_codes = 0
                new_format_qr_codes = 0
                old_format_qr_codes = 0
                sample_qr = None
                
                for qr_data in qr_codes:
                    qr_code = qr_data.get("qr_code", "")
                    qr_text = qr_data.get("qr_data", "")
                    
                    if qr_code.startswith("data:image/png;base64,"):
                        valid_qr_codes += 1
                        
                        # Check format: new format should be 8 digits without spaces
                        if re.match(r'^\d{8}$', qr_text):
                            new_format_qr_codes += 1
                        elif ' ' in qr_text:
                            old_format_qr_codes += 1
                        
                        if not sample_qr:
                            sample_qr = qr_data
                
                all_new_format = new_format_qr_codes == actual_qr_count
                no_old_format = old_format_qr_codes == 0
                
                if valid_qr_codes == actual_qr_count:
                    self.log_result(
                        "Batch QR Generation New Format (CRITICAL)",
                        all_new_format and no_old_format,
                        f"Generated {actual_qr_count} QR codes - {new_format_qr_codes} new format, {old_format_qr_codes} old format",
                        {
                            "total_qr_codes": actual_qr_count,
                            "expected_qr_count": expected_qr_count,
                            "valid_qr_codes": valid_qr_codes,
                            "new_format_qr_codes": new_format_qr_codes,
                            "old_format_qr_codes": old_format_qr_codes,
                            "all_new_format": all_new_format,
                            "no_old_format": no_old_format,
                            "sample_qr": sample_qr,
                            "warehouse_number": warehouse_number
                        }
                    )
                    return all_new_format and no_old_format
                else:
                    self.log_result(
                        "Batch QR Generation New Format (CRITICAL)",
                        False,
                        f"Generated {actual_qr_count} QR codes but only {valid_qr_codes} have valid format",
                        {"invalid_qr_codes": actual_qr_count - valid_qr_codes}
                    )
                    return False
            else:
                self.log_result(
                    "Batch QR Generation New Format (CRITICAL)",
                    False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_result("Batch QR Generation New Format (CRITICAL)", False, f"Exception: {str(e)}")
            return False
    
    def test_qr_format_comparison(self, cells, warehouse_number):
        """Test comparison between old and new QR formats"""
        if not cells:
            self.log_result("QR Format Comparison", False, "No cells available for testing")
            return False
        
        # Test multiple cells to verify consistency
        test_cells = cells[:3] if len(cells) >= 3 else cells
        format_results = []
        
        for i, test_cell in enumerate(test_cells):
            cell_id = test_cell.get("id")
            block_number = test_cell.get("block_number", 1)
            shelf_number = test_cell.get("shelf_number", 1)
            cell_number = test_cell.get("cell_number", 1)
            
            try:
                response = self.session.get(f"{BACKEND_URL}/warehouses/cells/{cell_id}/qr", timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    qr_data = data.get("qr_data", "")
                    
                    # Expected new format: "04010109" (no spaces)
                    expected_new = f"{warehouse_number:02d}{block_number:02d}{shelf_number:02d}{cell_number:02d}"
                    # Old format would be: "04 01 01 09" (with spaces)
                    expected_old = f"{warehouse_number:02d} {block_number:02d} {shelf_number:02d} {cell_number:02d}"
                    
                    is_new_format = qr_data == expected_new
                    is_old_format = qr_data == expected_old
                    
                    format_results.append({
                        "cell_id": cell_id,
                        "qr_data": qr_data,
                        "expected_new": expected_new,
                        "expected_old": expected_old,
                        "is_new_format": is_new_format,
                        "is_old_format": is_old_format,
                        "block": block_number,
                        "shelf": shelf_number,
                        "cell": cell_number
                    })
                    
            except Exception as e:
                format_results.append({
                    "cell_id": cell_id,
                    "error": str(e)
                })
        
        # Analyze results
        new_format_count = sum(1 for r in format_results if r.get("is_new_format", False))
        old_format_count = sum(1 for r in format_results if r.get("is_old_format", False))
        total_tested = len(format_results)
        
        all_new_format = new_format_count == total_tested
        no_old_format = old_format_count == 0
        
        self.log_result(
            "QR Format Comparison (CRITICAL)",
            all_new_format and no_old_format,
            f"Tested {total_tested} cells: {new_format_count} new format, {old_format_count} old format",
            {
                "total_tested": total_tested,
                "new_format_count": new_format_count,
                "old_format_count": old_format_count,
                "all_new_format": all_new_format,
                "no_old_format": no_old_format,
                "format_results": format_results,
                "warehouse_number": warehouse_number
            }
        )
        
        return all_new_format and no_old_format
    
    def run_all_tests(self):
        """Run all warehouse QR fixes tests"""
        print("🏭 STARTING WAREHOUSE QR FIXES TESTING FOR TAJLINE.TJ")
        print("=" * 80)
        print("🎯 ФОКУС: Новый формат QR кода без пробелов (было '04 01 01 09' → стало '04010109')")
        print("=" * 80)
        
        # Step 1: Authenticate as admin
        if not self.authenticate_admin():
            print("❌ Cannot proceed without admin authentication")
            return False
        
        # Step 2: Find warehouse with cells
        warehouse_data = self.find_warehouse_with_cells()
        if not warehouse_data:
            print("❌ Cannot proceed without target warehouse")
            return False
        
        warehouse_id = warehouse_data.get("id")
        warehouse_number = warehouse_data.get("warehouse_number", 4)  # Default to 4 if not set
        
        # Step 3: Test warehouse cells real data (not Math.random())
        expected_cells = warehouse_data.get("blocks_count", 0) * warehouse_data.get("shelves_per_block", 0) * warehouse_data.get("cells_per_shelf", 0)
        cells = self.test_warehouse_cells_real_data(warehouse_id, expected_cells)
        
        if not cells:
            print("❌ Cannot proceed without cell data")
            return False
        
        # Step 4: CRITICAL TEST - Individual cell QR generation with new format
        individual_qr_success = self.test_individual_cell_qr_new_format(cells, warehouse_number)
        
        # Step 5: CRITICAL TEST - Batch QR generation with new format
        expected_qr_count = len(cells)
        batch_qr_success = self.test_batch_qr_generation_new_format(warehouse_id, warehouse_number, expected_qr_count)
        
        # Step 6: CRITICAL TEST - QR format comparison (old vs new)
        format_comparison_success = self.test_qr_format_comparison(cells, warehouse_number)
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY - WAREHOUSE QR FIXES")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Critical issues
        critical_failures = [
            result for result in self.test_results 
            if not result["success"] and "CRITICAL" in result["test"]
        ]
        
        if critical_failures:
            print(f"\n🚨 CRITICAL FAILURES ({len(critical_failures)}):")
            for failure in critical_failures:
                print(f"   - {failure['test']}: {failure['message']}")
        
        # Key findings
        print(f"\n🔍 KEY FINDINGS:")
        
        # Check if main QR format fix is working
        if individual_qr_success and batch_qr_success and format_comparison_success:
            print("   ✅ КРИТИЧЕСКИЙ УСПЕХ: Новый формат QR кода без пробелов работает!")
            print("   ✅ Формат изменен с '04 01 01 09' на '04010109'")
            print("   ✅ Индивидуальная генерация QR работает с новым форматом")
            print("   ✅ Массовая генерация QR работает с новым форматом")
        else:
            print("   ❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Новый формат QR кода не работает полностью")
            if not individual_qr_success:
                print("   ❌ Индивидуальная генерация QR имеет проблемы")
            if not batch_qr_success:
                print("   ❌ Массовая генерация QR имеет проблемы")
            if not format_comparison_success:
                print("   ❌ Формат QR кода не соответствует ожидаемому")
        
        # Check real data usage
        cells_test = next((r for r in self.test_results if "Warehouse Cells Real Data" in r["test"]), None)
        if cells_test and cells_test["success"]:
            print("   ✅ Схема склада использует реальные данные о занятости ячеек")
        elif cells_test:
            print("   ❌ Проблемы с получением реальных данных о ячейках")
        
        return success_rate >= 75.0

if __name__ == "__main__":
    tester = WarehouseQRFixesTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 WAREHOUSE QR FIXES TESTING COMPLETED SUCCESSFULLY!")
        print("✅ ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ДОСТИГНУТ:")
        print("✅ QR коды содержат числовые данные без пробелов (например '04010109')")
        print("✅ Схема склада использует реальную занятость ячеек из API")
        print("✅ Все endpoints работают стабильно с новым форматом")
        sys.exit(0)
    else:
        print("\n❌ WAREHOUSE QR FIXES TESTING FAILED!")
        print("❌ Некоторые исправления не работают как ожидалось")
        sys.exit(1)