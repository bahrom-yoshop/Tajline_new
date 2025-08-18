#!/usr/bin/env python3
"""
🎯 ДЕТАЛЬНАЯ ДИАГНОСТИКА: Анализ полей в API endpoint /api/operator/available-cargo-for-placement
Проверка конкретных полей согласно review request
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"

# Тестовые данные для авторизации
OPERATOR_CREDENTIALS = {
    "phone": "+79777888999", 
    "password": "warehouse123"
}

class DetailedFieldAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.operator_token = None
        
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
                self.session.headers.update({"Authorization": f"Bearer {self.operator_token}"})
                
                user_info = data.get("user", {})
                print(f"✅ Авторизация: {user_info.get('full_name', 'N/A')} (роль: {user_info.get('role', 'N/A')})")
                return True
            else:
                print(f"❌ Ошибка авторизации: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка авторизации: {str(e)}")
            return False

    def analyze_cargo_fields(self):
        """Детальный анализ полей в грузах"""
        try:
            response = self.session.get(
                f"{BACKEND_URL}/operator/cargo/available-for-placement?per_page=5",
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"❌ Ошибка получения данных: HTTP {response.status_code}")
                return
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                print("⚠️ Нет грузов для анализа")
                return
            
            print(f"\n🔍 АНАЛИЗ ПОЛЕЙ В {len(items)} ГРУЗАХ:")
            print("=" * 80)
            
            # Анализируем каждый груз
            for i, cargo in enumerate(items):
                print(f"\n📦 ГРУЗ {i+1}: {cargo.get('cargo_number', 'N/A')}")
                print("-" * 50)
                
                # Основные поля из review request
                required_fields = {
                    "payment_method": "Способ оплаты",
                    "payment_amount": "Сумма оплаты", 
                    "debt_due_date": "Дата погашения долга",
                    "cargo_number": "Номер груза",
                    "base_request_number": "Базовый номер заявки"
                }
                
                # Дополнительные важные поля
                additional_fields = {
                    "declared_value": "Стоимость груза",
                    "total_cost": "Общая стоимость",
                    "accepting_operator": "Принявший оператор",
                    "received_by_operator": "Получен оператором",
                    "accepting_operator_info": "Информация об операторе",
                    "creator_name": "Создатель",
                    "warehouse_name": "Склад",
                    "status": "Статус",
                    "created_at": "Дата создания"
                }
                
                # Проверяем обязательные поля
                print("🎯 ОБЯЗАТЕЛЬНЫЕ ПОЛЯ:")
                for field, description in required_fields.items():
                    value = cargo.get(field)
                    status = "✅" if value is not None else "❌"
                    print(f"  {status} {description} ({field}): {value}")
                
                # Проверяем дополнительные поля
                print("\n📋 ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ:")
                for field, description in additional_fields.items():
                    value = cargo.get(field)
                    status = "✅" if value is not None else "❌"
                    if isinstance(value, dict):
                        print(f"  {status} {description} ({field}): {json.dumps(value, ensure_ascii=False)[:100]}...")
                    else:
                        print(f"  {status} {description} ({field}): {value}")
                
                # Показываем все доступные поля для первого груза
                if i == 0:
                    print(f"\n🔧 ВСЕ ДОСТУПНЫЕ ПОЛЯ В ГРУЗЕ:")
                    all_fields = sorted(cargo.keys())
                    for field in all_fields:
                        value = cargo[field]
                        if isinstance(value, (dict, list)):
                            print(f"  • {field}: {type(value).__name__} ({len(value) if hasattr(value, '__len__') else 'N/A'})")
                        else:
                            print(f"  • {field}: {value}")
                
                if i >= 2:  # Показываем только первые 3 груза детально
                    break
            
            # Статистика по полям
            print(f"\n📊 СТАТИСТИКА ПО ПОЛЯМ (из {len(items)} грузов):")
            print("=" * 60)
            
            field_stats = {}
            for cargo in items:
                for field in cargo.keys():
                    if field not in field_stats:
                        field_stats[field] = {"present": 0, "null": 0, "total": 0}
                    
                    field_stats[field]["total"] += 1
                    if cargo[field] is not None and cargo[field] != "":
                        field_stats[field]["present"] += 1
                    else:
                        field_stats[field]["null"] += 1
            
            # Сортируем по важности (обязательные поля сначала)
            important_fields = list(required_fields.keys()) + list(additional_fields.keys())
            other_fields = [f for f in field_stats.keys() if f not in important_fields]
            
            for field in important_fields + other_fields:
                if field in field_stats:
                    stats = field_stats[field]
                    percentage = (stats["present"] / stats["total"]) * 100
                    status = "✅" if percentage >= 80 else "⚠️" if percentage >= 50 else "❌"
                    print(f"  {status} {field}: {stats['present']}/{stats['total']} ({percentage:.1f}%)")
            
            # Проверяем примеры данных для каждого способа оплаты
            print(f"\n💳 ПРИМЕРЫ ДАННЫХ ПО СПОСОБАМ ОПЛАТЫ:")
            print("=" * 60)
            
            payment_examples = {}
            for cargo in items:
                method = cargo.get("payment_method", "unknown")
                if method not in payment_examples:
                    payment_examples[method] = []
                if len(payment_examples[method]) < 2:  # Максимум 2 примера на метод
                    payment_examples[method].append({
                        "cargo_number": cargo.get("cargo_number"),
                        "payment_amount": cargo.get("payment_amount"),
                        "debt_due_date": cargo.get("debt_due_date"),
                        "declared_value": cargo.get("declared_value"),
                        "total_cost": cargo.get("total_cost")
                    })
            
            for method, examples in payment_examples.items():
                print(f"\n🔸 {method.upper()}:")
                for example in examples:
                    print(f"  • Груз {example['cargo_number']}: сумма={example['payment_amount']}, "
                          f"долг_до={example['debt_due_date']}, стоимость={example['declared_value'] or example['total_cost']}")
                          
        except Exception as e:
            print(f"❌ Ошибка анализа: {str(e)}")

def main():
    """Главная функция"""
    analyzer = DetailedFieldAnalyzer()
    
    print("🎯 ДЕТАЛЬНАЯ ДИАГНОСТИКА: Анализ полей API endpoint")
    print("=" * 80)
    
    if not analyzer.authenticate_operator():
        print("❌ Не удалось авторизоваться. Анализ прерван.")
        sys.exit(1)
    
    analyzer.analyze_cargo_fields()
    
    print("\n" + "=" * 80)
    print("✅ Анализ завершен!")

if __name__ == "__main__":
    main()