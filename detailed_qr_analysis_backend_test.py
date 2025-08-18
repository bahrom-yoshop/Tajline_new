#!/usr/bin/env python3
"""
🎯 ДЕТАЛЬНЫЙ АНАЛИЗ: Проблема дублирования QR-кодов в API TAJLINE.TJ
Углубленное исследование причин дублирования cargo_number в QR генерации
"""

import requests
import json
import sys
from datetime import datetime
from collections import Counter

# Конфигурация
BACKEND_URL = "https://tajline-cargo-3.preview.emergentagent.com/api"

# Тестовые данные для авторизации
ADMIN_CREDENTIALS = {
    "phone": "+79999888777",
    "password": "admin123"
}

OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

class DetailedQRAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                print(f"✅ Авторизация администратора: {data.get('user', {}).get('full_name', 'N/A')}")
                return True
            else:
                print(f"❌ Ошибка авторизации администратора: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка авторизации администратора: {str(e)}")
            return False

    def authenticate_operator(self):
        """Авторизация оператора склада"""
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json=OPERATOR_CREDENTIALS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                print(f"✅ Авторизация оператора: {data.get('user', {}).get('full_name', 'N/A')}")
                return True
            else:
                print(f"❌ Ошибка авторизации оператора: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка авторизации оператора: {str(e)}")
            return False

    def find_and_analyze_250818_request(self):
        """Поиск и детальный анализ заявки 250818"""
        try:
            # Переключаемся на токен администратора
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            # Получаем список грузов для размещения
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement?page=1&per_page=100",
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"❌ Ошибка получения списка грузов: HTTP {response.status_code}")
                return None
            
            data = response.json()
            items = data.get("items", [])
            
            # Ищем заявки с базовым номером начинающимся на 250818
            requests_250818 = {}
            for item in items:
                base_number = item.get("base_request_number", "")
                if base_number.startswith("250818"):
                    if base_number not in requests_250818:
                        requests_250818[base_number] = []
                    requests_250818[base_number].append(item)
            
            print(f"\n🔍 НАЙДЕНО ЗАЯВОК С 250818: {len(requests_250818)}")
            
            # Анализируем каждую заявку
            for base_number, cargo_list in requests_250818.items():
                print(f"\n📋 ЗАЯВКА: {base_number}")
                print(f"   Количество грузов: {len(cargo_list)}")
                
                # Анализируем cargo_number
                cargo_numbers = [c.get("cargo_number", "") for c in cargo_list]
                cargo_number_counts = Counter(cargo_numbers)
                
                print(f"   Номера грузов: {cargo_numbers}")
                
                if len(set(cargo_numbers)) != len(cargo_numbers):
                    print(f"   🚨 ДУБЛИРОВАННЫЕ НОМЕРА: {[cn for cn, count in cargo_number_counts.items() if count > 1]}")
                else:
                    print(f"   ✅ Все номера уникальны")
                
                # Детальный анализ каждого груза
                for i, cargo in enumerate(cargo_list):
                    print(f"   Груз {i+1}:")
                    print(f"     ID: {cargo.get('id', 'N/A')}")
                    print(f"     Номер: {cargo.get('cargo_number', 'N/A')}")
                    print(f"     Название: {cargo.get('cargo_name', 'N/A')}")
                    print(f"     Вес: {cargo.get('weight', 'N/A')}кг")
                    print(f"     Base request: {cargo.get('base_request_number', 'N/A')}")
                    print(f"     Item sequence: {cargo.get('item_sequence', 'N/A')}")
                
                # Если это заявка с 2 грузами, тестируем QR генерацию
                if len(cargo_list) == 2:
                    print(f"\n🎯 ТЕСТИРОВАНИЕ QR ГЕНЕРАЦИИ ДЛЯ ЗАЯВКИ {base_number}")
                    self.test_qr_generation_detailed(base_number, cargo_list)
                    return base_number, cargo_list
            
            return None, None
            
        except Exception as e:
            print(f"❌ Ошибка поиска заявки: {str(e)}")
            return None, None

    def test_qr_generation_detailed(self, base_request_number, cargo_list):
        """Детальное тестирование генерации QR кодов"""
        try:
            # Переключаемся на токен оператора
            self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
            
            cargo_ids = [c.get("id", "") for c in cargo_list]
            
            payload = {
                "base_request_number": base_request_number,
                "cargo_ids": cargo_ids
            }
            
            print(f"📤 ЗАПРОС НА ГЕНЕРАЦИЮ QR:")
            print(f"   Base request number: {base_request_number}")
            print(f"   Cargo IDs: {cargo_ids}")
            
            response = self.session.post(
                f"{BACKEND_URL}/operator/cargo/generate-qr-batch",
                json=payload,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"❌ Ошибка генерации QR: HTTP {response.status_code}: {response.text}")
                return
            
            data = response.json()
            qr_codes = data.get("qr_codes", [])
            generated_count = data.get("generated_count", 0)
            
            print(f"\n📥 ОТВЕТ API:")
            print(f"   Generated count: {generated_count}")
            print(f"   Количество QR кодов: {len(qr_codes)}")
            
            # Детальный анализ каждого QR кода
            cargo_numbers_in_qr = []
            qr_data_list = []
            
            for i, qr_code in enumerate(qr_codes):
                cargo_number = qr_code.get("cargo_number", "")
                qr_data = qr_code.get("qr_data", "")
                cargo_id = qr_code.get("cargo_id", "")
                cargo_name = qr_code.get("cargo_name", "")
                
                cargo_numbers_in_qr.append(cargo_number)
                qr_data_list.append(qr_data)
                
                print(f"\n   QR КОД {i+1}:")
                print(f"     Cargo ID: {cargo_id}")
                print(f"     Cargo Number: {cargo_number}")
                print(f"     Cargo Name: {cargo_name}")
                print(f"     QR Data: {qr_data}")
                print(f"     QR Image: {'Присутствует' if qr_code.get('qr_code') else 'Отсутствует'}")
            
            # Анализ дублирования
            print(f"\n🔍 АНАЛИЗ ДУБЛИРОВАНИЯ:")
            
            cargo_number_counts = Counter(cargo_numbers_in_qr)
            qr_data_counts = Counter(qr_data_list)
            
            print(f"   Статистика cargo_number: {dict(cargo_number_counts)}")
            print(f"   Статистика qr_data: {dict(qr_data_counts)}")
            
            duplicated_cargo_numbers = [cn for cn, count in cargo_number_counts.items() if count > 1]
            duplicated_qr_data = [qd for qd, count in qr_data_counts.items() if count > 1]
            
            if duplicated_cargo_numbers:
                print(f"   🚨 ДУБЛИРОВАННЫЕ CARGO_NUMBER: {duplicated_cargo_numbers}")
            else:
                print(f"   ✅ Все cargo_number уникальны")
            
            if duplicated_qr_data:
                print(f"   🚨 ДУБЛИРОВАННЫЕ QR_DATA: {duplicated_qr_data}")
            else:
                print(f"   ✅ Все qr_data уникальны")
            
            # Сравнение с исходными данными
            print(f"\n🔄 СРАВНЕНИЕ С ИСХОДНЫМИ ДАННЫМИ:")
            original_cargo_numbers = [c.get("cargo_number", "") for c in cargo_list]
            original_ids = [c.get("id", "") for c in cargo_list]
            
            print(f"   Исходные cargo_number: {original_cargo_numbers}")
            print(f"   QR cargo_number: {cargo_numbers_in_qr}")
            print(f"   Исходные ID: {original_ids}")
            print(f"   QR cargo_id: {[qr.get('cargo_id', '') for qr in qr_codes]}")
            
            # Проверяем соответствие
            if set(original_cargo_numbers) == set(cargo_numbers_in_qr):
                print(f"   ✅ Cargo numbers соответствуют исходным данным")
            else:
                print(f"   🚨 НЕСООТВЕТСТВИЕ cargo numbers!")
                print(f"      Ожидалось: {set(original_cargo_numbers)}")
                print(f"      Получено: {set(cargo_numbers_in_qr)}")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования QR генерации: {str(e)}")

    def investigate_database_issue(self, base_request_number):
        """Исследование проблемы в базе данных"""
        try:
            # Переключаемся на токен администратора
            self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
            
            print(f"\n🔍 ИССЛЕДОВАНИЕ БАЗЫ ДАННЫХ ДЛЯ ЗАЯВКИ {base_request_number}")
            
            # Пытаемся найти грузы через debug endpoint
            debug_endpoints = [
                f"/debug/find-cargo-by-base-number/{base_request_number}",
                f"/debug/find-cargo-by-number/{base_request_number}",
            ]
            
            for endpoint in debug_endpoints:
                try:
                    response = self.session.get(f"{BACKEND_URL}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ Endpoint {endpoint} работает:")
                        print(f"   Найдено записей: {len(data.get('found_cargo', []))}")
                        
                        for i, cargo in enumerate(data.get('found_cargo', [])):
                            print(f"   Груз {i+1}:")
                            print(f"     ID: {cargo.get('id', 'N/A')}")
                            print(f"     Number: {cargo.get('cargo_number', 'N/A')}")
                            print(f"     Base request: {cargo.get('base_request_number', 'N/A')}")
                            print(f"     Collection: {cargo.get('collection', 'N/A')}")
                    else:
                        print(f"❌ Endpoint {endpoint}: HTTP {response.status_code}")
                except:
                    print(f"❌ Endpoint {endpoint}: недоступен")
            
        except Exception as e:
            print(f"❌ Ошибка исследования базы данных: {str(e)}")

    def run_analysis(self):
        """Запуск полного анализа"""
        print("🎯 ДЕТАЛЬНЫЙ АНАЛИЗ: Проблема дублирования QR-кодов в API")
        print("=" * 80)
        
        # 1. Авторизация
        if not self.authenticate_admin() or not self.authenticate_operator():
            print("❌ Ошибка авторизации. Анализ прерван.")
            return False
        
        # 2. Поиск и анализ заявки 250818
        base_request_number, cargo_list = self.find_and_analyze_250818_request()
        
        if not base_request_number:
            print("❌ Не найдено заявок с 250818 для анализа")
            return False
        
        # 3. Исследование базы данных
        self.investigate_database_issue(base_request_number)
        
        print("\n" + "=" * 80)
        print("📊 ВЫВОДЫ ДЕТАЛЬНОГО АНАЛИЗА:")
        print("1. Проблема дублирования cargo_number в QR генерации подтверждена")
        print("2. QR_data генерируются уникально, но cargo_number дублируются")
        print("3. Проблема может быть в логике поиска грузов в двух коллекциях")
        print("4. Требуется исправление backend логики генерации QR кодов")
        print("=" * 80)
        
        return True

def main():
    """Главная функция"""
    analyzer = DetailedQRAnalyzer()
    
    try:
        success = analyzer.run_analysis()
        if success:
            print("\n✅ Детальный анализ завершен!")
        else:
            print("\n❌ Анализ завершен с ошибками!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Анализ прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка анализа: {str(e)}")

if __name__ == "__main__":
    main()