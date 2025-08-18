#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Анализ данных API для карточек грузов в размещении
Проверка полей стоимости и способов оплаты в endpoint /api/operator/cargo/available-for-placement

Цель: понять почему стоимость не показывается и способ оплаты отображается неправильно
"""

import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Any

# Конфигурация
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://cargo-talk.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class CargoPlacementAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.operator_token = None
        
    def authenticate_admin(self) -> bool:
        """Авторизация администратора"""
        try:
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79999888777",
                "password": "admin123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                print(f"✅ Авторизация администратора успешна")
                return True
            else:
                print(f"❌ Ошибка авторизации администратора: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при авторизации администратора: {e}")
            return False
    
    def authenticate_operator(self) -> bool:
        """Авторизация оператора склада"""
        try:
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79777888999",
                "password": "warehouse123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.operator_token = data.get("access_token")
                print(f"✅ Авторизация оператора склада успешна")
                return True
            else:
                print(f"❌ Ошибка авторизации оператора: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Исключение при авторизации оператора: {e}")
            return False
    
    def get_available_for_placement(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Получить грузы доступные для размещения"""
        try:
            headers = {"Authorization": f"Bearer {self.operator_token}"}
            params = {"page": page, "per_page": per_page}
            
            response = self.session.get(
                f"{API_BASE}/operator/cargo/available-for-placement",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка получения грузов для размещения: {response.status_code}")
                print(f"Response: {response.text}")
                return {}
                
        except Exception as e:
            print(f"❌ Исключение при получении грузов: {e}")
            return {}
    
    def analyze_cargo_fields(self, cargo: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ полей одного груза"""
        analysis = {
            "cargo_number": cargo.get("cargo_number", "НЕТ"),
            "cargo_name": cargo.get("cargo_name", "НЕТ"),
            
            # Анализ полей стоимости
            "declared_value": {
                "exists": "declared_value" in cargo,
                "value": cargo.get("declared_value"),
                "type": type(cargo.get("declared_value")).__name__,
                "is_null": cargo.get("declared_value") is None,
                "is_zero": cargo.get("declared_value") == 0
            },
            
            "total_cost": {
                "exists": "total_cost" in cargo,
                "value": cargo.get("total_cost"),
                "type": type(cargo.get("total_cost")).__name__,
                "is_null": cargo.get("total_cost") is None,
                "is_zero": cargo.get("total_cost") == 0
            },
            
            # Анализ полей оплаты
            "payment_method": {
                "exists": "payment_method" in cargo,
                "value": cargo.get("payment_method"),
                "type": type(cargo.get("payment_method")).__name__,
                "is_expected_value": cargo.get("payment_method") in ["cash", "card_transfer", "cash_on_delivery", "credit", "not_paid"],
                "is_old_value": cargo.get("payment_method") in ["card", "transfer", "prepaid"]
            },
            
            "payment_amount": {
                "exists": "payment_amount" in cargo,
                "value": cargo.get("payment_amount"),
                "type": type(cargo.get("payment_amount")).__name__,
                "is_null": cargo.get("payment_amount") is None
            },
            
            "debt_due_date": {
                "exists": "debt_due_date" in cargo,
                "value": cargo.get("debt_due_date"),
                "type": type(cargo.get("debt_due_date")).__name__,
                "is_null": cargo.get("debt_due_date") is None
            },
            
            # Дополнительные поля для контекста
            "weight": cargo.get("weight"),
            "sender_full_name": cargo.get("sender_full_name", "НЕТ"),
            "recipient_full_name": cargo.get("recipient_full_name", "НЕТ"),
            "status": cargo.get("status", "НЕТ"),
            "created_at": cargo.get("created_at", "НЕТ")
        }
        
        return analysis
    
    def print_cargo_analysis(self, analysis: Dict[str, Any], index: int):
        """Красивый вывод анализа груза"""
        print(f"\n{'='*60}")
        print(f"📦 ГРУЗ #{index + 1}: {analysis['cargo_number']}")
        print(f"{'='*60}")
        print(f"Название груза: {analysis['cargo_name']}")
        print(f"Отправитель: {analysis['sender_full_name']}")
        print(f"Получатель: {analysis['recipient_full_name']}")
        print(f"Вес: {analysis['weight']} кг")
        print(f"Статус: {analysis['status']}")
        
        print(f"\n💰 АНАЛИЗ ПОЛЕЙ СТОИМОСТИ:")
        print(f"┌─ declared_value:")
        print(f"│  ├─ Существует: {analysis['declared_value']['exists']}")
        print(f"│  ├─ Значение: {analysis['declared_value']['value']}")
        print(f"│  ├─ Тип: {analysis['declared_value']['type']}")
        print(f"│  ├─ Null: {analysis['declared_value']['is_null']}")
        print(f"│  └─ Ноль: {analysis['declared_value']['is_zero']}")
        
        print(f"└─ total_cost:")
        print(f"   ├─ Существует: {analysis['total_cost']['exists']}")
        print(f"   ├─ Значение: {analysis['total_cost']['value']}")
        print(f"   ├─ Тип: {analysis['total_cost']['type']}")
        print(f"   ├─ Null: {analysis['total_cost']['is_null']}")
        print(f"   └─ Ноль: {analysis['total_cost']['is_zero']}")
        
        print(f"\n💳 АНАЛИЗ ПОЛЕЙ ОПЛАТЫ:")
        print(f"┌─ payment_method:")
        print(f"│  ├─ Существует: {analysis['payment_method']['exists']}")
        print(f"│  ├─ Значение: '{analysis['payment_method']['value']}'")
        print(f"│  ├─ Тип: {analysis['payment_method']['type']}")
        print(f"│  ├─ Ожидаемое значение: {analysis['payment_method']['is_expected_value']}")
        print(f"│  └─ Старое значение: {analysis['payment_method']['is_old_value']}")
        
        print(f"├─ payment_amount:")
        print(f"│  ├─ Существует: {analysis['payment_amount']['exists']}")
        print(f"│  ├─ Значение: {analysis['payment_amount']['value']}")
        print(f"│  ├─ Тип: {analysis['payment_amount']['type']}")
        print(f"│  └─ Null: {analysis['payment_amount']['is_null']}")
        
        print(f"└─ debt_due_date:")
        print(f"   ├─ Существует: {analysis['debt_due_date']['exists']}")
        print(f"   ├─ Значение: {analysis['debt_due_date']['value']}")
        print(f"   ├─ Тип: {analysis['debt_due_date']['type']}")
        print(f"   └─ Null: {analysis['debt_due_date']['is_null']}")
    
    def print_summary_statistics(self, analyses: List[Dict[str, Any]]):
        """Сводная статистика по всем грузам"""
        total_count = len(analyses)
        
        # Статистика по declared_value
        declared_value_exists = sum(1 for a in analyses if a['declared_value']['exists'])
        declared_value_null = sum(1 for a in analyses if a['declared_value']['is_null'])
        declared_value_zero = sum(1 for a in analyses if a['declared_value']['is_zero'])
        declared_value_has_value = sum(1 for a in analyses if a['declared_value']['value'] and a['declared_value']['value'] != 0)
        
        # Статистика по total_cost
        total_cost_exists = sum(1 for a in analyses if a['total_cost']['exists'])
        total_cost_null = sum(1 for a in analyses if a['total_cost']['is_null'])
        total_cost_zero = sum(1 for a in analyses if a['total_cost']['is_zero'])
        total_cost_has_value = sum(1 for a in analyses if a['total_cost']['value'] and a['total_cost']['value'] != 0)
        
        # Статистика по payment_method
        payment_method_exists = sum(1 for a in analyses if a['payment_method']['exists'])
        payment_method_expected = sum(1 for a in analyses if a['payment_method']['is_expected_value'])
        payment_method_old = sum(1 for a in analyses if a['payment_method']['is_old_value'])
        
        # Подсчет уникальных значений payment_method
        payment_methods = {}
        for a in analyses:
            method = a['payment_method']['value']
            if method:
                payment_methods[method] = payment_methods.get(method, 0) + 1
        
        print(f"\n{'='*80}")
        print(f"📊 СВОДНАЯ СТАТИСТИКА ПО {total_count} ГРУЗАМ")
        print(f"{'='*80}")
        
        print(f"\n💰 ПОЛЯ СТОИМОСТИ:")
        print(f"┌─ declared_value:")
        print(f"│  ├─ Существует: {declared_value_exists}/{total_count} ({declared_value_exists/total_count*100:.1f}%)")
        print(f"│  ├─ Null значения: {declared_value_null}/{total_count} ({declared_value_null/total_count*100:.1f}%)")
        print(f"│  ├─ Нулевые значения: {declared_value_zero}/{total_count} ({declared_value_zero/total_count*100:.1f}%)")
        print(f"│  └─ Имеют значение: {declared_value_has_value}/{total_count} ({declared_value_has_value/total_count*100:.1f}%)")
        
        print(f"└─ total_cost:")
        print(f"   ├─ Существует: {total_cost_exists}/{total_count} ({total_cost_exists/total_count*100:.1f}%)")
        print(f"   ├─ Null значения: {total_cost_null}/{total_count} ({total_cost_null/total_count*100:.1f}%)")
        print(f"   ├─ Нулевые значения: {total_cost_zero}/{total_count} ({total_cost_zero/total_count*100:.1f}%)")
        print(f"   └─ Имеют значение: {total_cost_has_value}/{total_count} ({total_cost_has_value/total_count*100:.1f}%)")
        
        print(f"\n💳 ПОЛЯ ОПЛАТЫ:")
        print(f"┌─ payment_method:")
        print(f"│  ├─ Существует: {payment_method_exists}/{total_count} ({payment_method_exists/total_count*100:.1f}%)")
        print(f"│  ├─ Ожидаемые значения: {payment_method_expected}/{total_count} ({payment_method_expected/total_count*100:.1f}%)")
        print(f"│  ├─ Старые значения: {payment_method_old}/{total_count} ({payment_method_old/total_count*100:.1f}%)")
        print(f"│  └─ Распределение значений:")
        
        for method, count in sorted(payment_methods.items()):
            percentage = count/total_count*100
            print(f"│     ├─ '{method}': {count} ({percentage:.1f}%)")
        
        print(f"\n🔍 ПРОБЛЕМНЫЕ ОБЛАСТИ:")
        problems = []
        
        if declared_value_has_value < total_count * 0.8:
            problems.append(f"❌ Низкий процент заполнения declared_value: {declared_value_has_value/total_count*100:.1f}%")
        
        if total_cost_has_value < total_count * 0.8:
            problems.append(f"❌ Низкий процент заполнения total_cost: {total_cost_has_value/total_count*100:.1f}%")
        
        if payment_method_expected < total_count * 0.8:
            problems.append(f"❌ Много неожиданных значений payment_method: {(total_count-payment_method_expected)/total_count*100:.1f}%")
        
        if payment_method_old > 0:
            problems.append(f"⚠️ Найдены старые значения payment_method: {payment_method_old} грузов")
        
        if problems:
            for problem in problems:
                print(f"   {problem}")
        else:
            print(f"   ✅ Критических проблем не обнаружено")
    
    def print_raw_examples(self, cargos: List[Dict[str, Any]], count: int = 3):
        """Вывод сырых данных для примеров"""
        print(f"\n{'='*80}")
        print(f"📋 ПРИМЕРЫ СЫРЫХ ДАННЫХ ({count} ГРУЗОВ)")
        print(f"{'='*80}")
        
        for i, cargo in enumerate(cargos[:count]):
            print(f"\n--- ГРУЗ #{i+1}: {cargo.get('cargo_number', 'НЕТ НОМЕРА')} ---")
            
            # Ключевые поля для анализа
            key_fields = [
                'cargo_number', 'cargo_name', 'declared_value', 'total_cost',
                'payment_method', 'payment_amount', 'debt_due_date',
                'weight', 'sender_full_name', 'recipient_full_name', 'status'
            ]
            
            for field in key_fields:
                value = cargo.get(field)
                print(f"{field}: {value} ({type(value).__name__})")
    
    def run_analysis(self):
        """Запуск полного анализа"""
        print("🚀 ЗАПУСК КРИТИЧЕСКОГО АНАЛИЗА API ДАННЫХ ДЛЯ РАЗМЕЩЕНИЯ ГРУЗОВ")
        print("="*80)
        
        # Авторизация
        if not self.authenticate_admin():
            return False
        
        if not self.authenticate_operator():
            return False
        
        # Получение данных
        print(f"\n📡 Получение данных из /api/operator/cargo/available-for-placement...")
        data = self.get_available_for_placement(page=1, per_page=20)
        
        if not data:
            print("❌ Не удалось получить данные")
            return False
        
        items = data.get("items", [])
        pagination = data.get("pagination", {})
        
        print(f"✅ Получено {len(items)} грузов")
        print(f"📊 Пагинация: страница {pagination.get('page', 'НЕТ')}, всего {pagination.get('total_count', 'НЕТ')}")
        
        if not items:
            print("⚠️ Нет грузов для анализа")
            return True
        
        # Анализ первых 5 грузов детально
        analyses = []
        for i, cargo in enumerate(items[:5]):
            analysis = self.analyze_cargo_fields(cargo)
            analyses.append(analysis)
            self.print_cargo_analysis(analysis, i)
        
        # Сводная статистика
        if len(items) > 5:
            # Анализируем все грузы для статистики
            all_analyses = []
            for cargo in items:
                analysis = self.analyze_cargo_fields(cargo)
                all_analyses.append(analysis)
            self.print_summary_statistics(all_analyses)
        else:
            self.print_summary_statistics(analyses)
        
        # Примеры сырых данных
        self.print_raw_examples(items, min(3, len(items)))
        
        print(f"\n{'='*80}")
        print("✅ АНАЛИЗ ЗАВЕРШЕН")
        print(f"{'='*80}")
        
        return True

def main():
    """Главная функция"""
    analyzer = CargoPlacementAnalyzer()
    
    try:
        success = analyzer.run_analysis()
        if success:
            print("\n🎉 Анализ API данных для размещения грузов завершен успешно!")
        else:
            print("\n❌ Анализ завершен с ошибками")
            
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()