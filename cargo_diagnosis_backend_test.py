#!/usr/bin/env python3
"""
Backend Testing Script for TAJLINE.TJ Cargo Management System
Диагностика груза по номеру 250103 через новый endpoint
"""

import requests
import json
import os
from datetime import datetime

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://73ed2aa0-f922-4978-81e7-0ad7dcef385d.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_info = None
        
    def log(self, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def login_admin(self):
        """Login as admin"""
        try:
            self.log("🔐 Attempting admin login...")
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79999888777",
                "password": "admin123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_info = data.get("user")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                self.log(f"✅ Admin login successful: {self.user_info.get('full_name')} (role: {self.user_info.get('role')})")
                return True
            else:
                self.log(f"❌ Admin login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Admin login error: {str(e)}")
            return False
    
    def login_warehouse_operator(self):
        """Login as warehouse operator (Moscow-1)"""
        try:
            self.log("🔐 Attempting warehouse operator login...")
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79777888999",
                "password": "warehouse123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_info = data.get("user")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                self.log(f"✅ Warehouse operator login successful: {self.user_info.get('full_name')} (role: {self.user_info.get('role')})")
                return True
            else:
                self.log(f"❌ Warehouse operator login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Warehouse operator login error: {str(e)}")
            return False
    
    def debug_find_cargo_by_number(self, cargo_number):
        """Call the debug endpoint to find cargo by number"""
        try:
            self.log(f"🔍 Searching for cargo number: {cargo_number}")
            response = self.session.get(f"{API_BASE}/debug/find-cargo-by-number/{cargo_number}")
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Debug search successful")
                return data
            else:
                self.log(f"❌ Debug search failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.log(f"❌ Debug search error: {str(e)}")
            return None
    
    def analyze_results(self, results):
        """Analyze and format the search results"""
        if not results:
            return {
                "found_documents": 0,
                "documents": [],
                "summary": {"hidden_status_counts": {}},
                "next_steps": [
                    "Проверка по QR коду",
                    "Проверка по истории операций", 
                    "Проверка старых коллекций/переименований"
                ]
            }
        
        documents = results.get("data", [])
        summary = results.get("summary", {})
        
        analysis = {
            "found_documents": len(documents),
            "documents": [],
            "summary": summary,
            "next_steps": []
        }
        
        # Format document information
        for doc in documents:
            doc_info = {
                "collection": doc.get("collection"),
                "id": doc.get("id"),
                "cargo_number": doc.get("cargo_number"),
                "base_request_number": doc.get("base_request_number"),
                "warehouse_id": doc.get("warehouse_id"),
                "warehouse_name": doc.get("warehouse_name"),
                "destination_warehouse_id": doc.get("destination_warehouse_id"),
                "destination_warehouse_name": doc.get("destination_warehouse_name"),
                "status": doc.get("status"),
                "processing_status": doc.get("processing_status"),
                "warehouse_location": doc.get("warehouse_location"),
                "block_number": doc.get("block_number"),
                "shelf_number": doc.get("shelf_number"),
                "cell_number": doc.get("cell_number"),
                "hidden_reason": doc.get("hidden_reason"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at")
            }
            analysis["documents"].append(doc_info)
        
        # Add next steps if no documents found
        if len(documents) == 0:
            analysis["next_steps"] = [
                "Проверка по QR коду",
                "Проверка по истории операций",
                "Проверка старых коллекций/переименований"
            ]
        
        return analysis
    
    def run_cargo_diagnosis(self, cargo_number="250103"):
        """Run complete cargo diagnosis"""
        self.log("🎯 НАЧАЛО ДИАГНОСТИКИ ГРУЗА ПО НОМЕРУ 250103")
        self.log("=" * 60)
        
        # Try to login as admin first, then warehouse operator
        if not self.login_admin():
            if not self.login_warehouse_operator():
                self.log("❌ Failed to login as both admin and warehouse operator")
                return None
        
        # Call debug endpoint
        results = self.debug_find_cargo_by_number(cargo_number)
        
        # Analyze results
        analysis = self.analyze_results(results)
        
        # Log detailed results
        self.log("📊 РЕЗУЛЬТАТЫ ДИАГНОСТИКИ:")
        self.log(f"   Найдено документов: {analysis['found_documents']}")
        
        if analysis['found_documents'] > 0:
            self.log("📋 НАЙДЕННЫЕ ДОКУМЕНТЫ:")
            for i, doc in enumerate(analysis['documents'], 1):
                self.log(f"   Документ {i}:")
                self.log(f"     - Коллекция: {doc['collection']}")
                self.log(f"     - ID: {doc['id']}")
                self.log(f"     - Номер груза: {doc['cargo_number']}")
                self.log(f"     - Базовый номер заявки: {doc['base_request_number']}")
                self.log(f"     - Склад ID: {doc['warehouse_id']}")
                self.log(f"     - Склад название: {doc['warehouse_name']}")
                self.log(f"     - Склад назначения ID: {doc['destination_warehouse_id']}")
                self.log(f"     - Склад назначения название: {doc['destination_warehouse_name']}")
                self.log(f"     - Статус: {doc['status']}")
                self.log(f"     - Статус обработки: {doc['processing_status']}")
                self.log(f"     - Местоположение на складе: {doc['warehouse_location']}")
                self.log(f"     - Блок: {doc['block_number']}")
                self.log(f"     - Полка: {doc['shelf_number']}")
                self.log(f"     - Ячейка: {doc['cell_number']}")
                self.log(f"     - Причина скрытия: {doc['hidden_reason']}")
                self.log(f"     - Создан: {doc['created_at']}")
                self.log(f"     - Обновлен: {doc['updated_at']}")
                self.log("")
        
        # Log summary
        summary = analysis.get('summary', {})
        hidden_counts = summary.get('hidden_status_counts', {})
        
        self.log("📈 ИТОГОВАЯ СВОДКА:")
        self.log(f"   Запрос: {summary.get('query', cargo_number)}")
        self.log(f"   Всего найдено: {summary.get('total_found', 0)}")
        
        by_collection = summary.get('by_collection', {})
        self.log(f"   По коллекциям:")
        self.log(f"     - cargo: {by_collection.get('cargo', 0)}")
        self.log(f"     - operator_cargo: {by_collection.get('operator_cargo', 0)}")
        
        self.log(f"   Статусы скрытия:")
        for status, count in hidden_counts.items():
            self.log(f"     - {status}: {count}")
        
        # Log next steps if needed
        if analysis['next_steps']:
            self.log("🔄 СЛЕДУЮЩИЕ ШАГИ:")
            for step in analysis['next_steps']:
                self.log(f"   - {step}")
        
        self.log("=" * 60)
        self.log("🎯 ДИАГНОСТИКА ЗАВЕРШЕНА")
        
        return analysis

def main():
    """Main function"""
    tester = BackendTester()
    
    # Run cargo diagnosis for number 250103
    results = tester.run_cargo_diagnosis("250103")
    
    if results:
        print("\n" + "="*60)
        print("КРАТКОЕ РЕЗЮМЕ:")
        print(f"Найдено документов: {results['found_documents']}")
        
        if results['found_documents'] > 0:
            print("Ключевые поля найденных документов:")
            for doc in results['documents']:
                print(f"  - {doc['cargo_number']} (коллекция: {doc['collection']}, причина скрытия: {doc['hidden_reason']})")
        else:
            print("Документы не найдены. Рекомендуемые следующие шаги:")
            for step in results['next_steps']:
                print(f"  - {step}")
        
        summary = results.get('summary', {})
        hidden_counts = summary.get('hidden_status_counts', {})
        print(f"Сводка по статусам скрытия: {hidden_counts}")
        print("="*60)

if __name__ == "__main__":
    main()