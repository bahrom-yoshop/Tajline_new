#!/usr/bin/env python3
"""
🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА: Дублирование заявок при обработке груза в TAJLINE.TJ

ПРОБЛЕМА: При нажатии кнопки "Принять груз":
1. Заявка дублируется вместо удаления из списка уведомлений
2. Создается несколько одинаковых грузов с номером 100012/01 
3. В списке размещения груза появляется множество копий одной заявки
4. Номер создаваемого груза не соответствует номеру принятой заявки

ЦЕЛЬ: Диагностировать функцию complete_cargo_processing на предмет дублирования
"""

import requests
import json
import os
from datetime import datetime
import time

# Получаем URL backend из переменных окружения
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://qr-logistics-1.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class CargoDuplicationTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.user_info = None
        
    def log(self, message, level="INFO"):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        try:
            self.log("🔐 Авторизация администратора...")
            
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "phone": "+79999888777",
                "password": "admin123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                
                # Получаем информацию о пользователе
                user_response = self.session.get(f"{API_BASE}/auth/me")
                if user_response.status_code == 200:
                    self.user_info = user_response.json()
                    self.log(f"✅ Успешная авторизация: {self.user_info.get('full_name')} (роль: {self.user_info.get('role')})")
                    return True
                    
            self.log(f"❌ Ошибка авторизации: {response.status_code}", "ERROR")
            return False
                
        except Exception as e:
            self.log(f"❌ Исключение при авторизации: {str(e)}", "ERROR")
            return False
    
    def get_notifications(self):
        """Получение списка уведомлений"""
        try:
            self.log("📋 Получение списка уведомлений...")
            
            response = self.session.get(f"{API_BASE}/operator/warehouse-notifications")
            
            if response.status_code == 200:
                data = response.json()
                notifications = data.get('notifications', [])
                self.log(f"✅ Получено {len(notifications)} уведомлений")
                
                # Анализируем дублирование ID
                id_counts = {}
                for notif in notifications:
                    notif_id = notif.get('id')
                    if notif_id in id_counts:
                        id_counts[notif_id] += 1
                    else:
                        id_counts[notif_id] = 1
                
                duplicated_ids = {k: v for k, v in id_counts.items() if v > 1}
                if duplicated_ids:
                    self.log(f"🚨 НАЙДЕНО ДУБЛИРОВАНИЕ ID УВЕДОМЛЕНИЙ:")
                    for notif_id, count in duplicated_ids.items():
                        self.log(f"   - ID {notif_id}: {count} копий")
                
                # Показываем структуру первого уведомления
                if notifications and len(notifications) > 0:
                    first_notif = notifications[0]
                    self.log(f"📊 Структура уведомления: {list(first_notif.keys())}")
                    self.log(f"🎯 Пример уведомления: ID={first_notif.get('id')}, статус={first_notif.get('status')}, номер={first_notif.get('request_number')}")
                
                return notifications
            else:
                self.log(f"❌ Ошибка получения уведомлений: {response.status_code} - {response.text}", "ERROR")
                return []
                
        except Exception as e:
            self.log(f"❌ Исключение при получении уведомлений: {str(e)}", "ERROR")
            return []
    
    def test_complete_endpoint_duplication(self, notification_id):
        """КРИТИЧЕСКИЙ ТЕСТ: Проверка дублирования в /complete endpoint"""
        try:
            self.log(f"🎯 КРИТИЧЕСКИЙ ТЕСТ: Тестирование endpoint /complete для уведомления {notification_id}")
            
            # Получаем количество грузов ДО вызова complete
            before_count = self.get_total_cargo_count()
            self.log(f"📊 Количество грузов ДО /complete: {before_count}")
            
            # Подготавливаем данные для complete
            complete_data = {
                "cargo_items": [
                    {
                        "cargo_name": "Тестовый груз дублирования",
                        "weight": 10.0,
                        "price_per_kg": 100.0
                    }
                ],
                "description": "Тест дублирования грузов",
                "payment_method": "cash",
                "payment_amount": 1000.0
            }
            
            self.log(f"📦 Отправляем данные на /complete...")
            
            # Вызываем complete endpoint
            response = self.session.post(
                f"{API_BASE}/operator/warehouse-notifications/{notification_id}/complete",
                json=complete_data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log(f"✅ Complete endpoint выполнен успешно")
                
                # Получаем количество грузов ПОСЛЕ вызова complete
                time.sleep(1)  # Небольшая задержка
                after_count = self.get_total_cargo_count()
                self.log(f"📊 Количество грузов ПОСЛЕ /complete: {after_count}")
                
                created_count = after_count - before_count
                self.log(f"🎯 КРИТИЧЕСКИЙ РЕЗУЛЬТАТ: Создано грузов за один вызов /complete: {created_count}")
                
                if created_count > 1:
                    self.log(f"🚨 ДУБЛИРОВАНИЕ НАЙДЕНО! Создано {created_count} грузов вместо 1!", "ERROR")
                    return False, created_count
                elif created_count == 1:
                    self.log("✅ Корректно: создан 1 груз")
                    return True, created_count
                else:
                    self.log("⚠️ Грузы не созданы", "WARNING")
                    return True, created_count
                    
            else:
                self.log(f"❌ Ошибка complete endpoint: {response.status_code} - {response.text}", "ERROR")
                return False, 0
                
        except Exception as e:
            self.log(f"❌ Исключение в тесте complete: {str(e)}", "ERROR")
            return False, 0
    
    def get_total_cargo_count(self):
        """Получение общего количества грузов в системе"""
        try:
            # Проверяем operator_cargo коллекцию
            response = self.session.get(f"{API_BASE}/operator/cargo/list?per_page=1")
            if response.status_code == 200:
                data = response.json()
                return data.get('pagination', {}).get('total_count', 0)
            return 0
        except:
            return 0
    
    def check_placement_list_duplicates(self):
        """Проверка дубликатов в списке размещения"""
        try:
            self.log("🔍 Проверка дубликатов в списке размещения...")
            
            response = self.session.get(f"{API_BASE}/operator/cargo/available-for-placement")
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                self.log(f"📦 Найдено {len(items)} грузов для размещения")
                
                # Группируем по номерам грузов
                cargo_numbers = {}
                for item in items:
                    cargo_number = item.get('cargo_number', 'N/A')
                    if cargo_number in cargo_numbers:
                        cargo_numbers[cargo_number] += 1
                    else:
                        cargo_numbers[cargo_number] = 1
                
                # Ищем дубликаты
                duplicates = {k: v for k, v in cargo_numbers.items() if v > 1}
                
                if duplicates:
                    self.log(f"🚨 НАЙДЕНЫ ДУБЛИКАТЫ В СПИСКЕ РАЗМЕЩЕНИЯ:")
                    for number, count in duplicates.items():
                        self.log(f"   - Номер {number}: {count} копий")
                    return False, duplicates
                else:
                    self.log("✅ Дубликатов в списке размещения не найдено")
                    return True, {}
                    
            else:
                self.log(f"❌ Ошибка получения списка размещения: {response.status_code}", "ERROR")
                return False, {}
                
        except Exception as e:
            self.log(f"❌ Исключение при проверке размещения: {str(e)}", "ERROR")
            return False, {}
    
    def analyze_cargo_numbers(self):
        """Анализ номеров грузов на предмет дублирования"""
        try:
            self.log("🔍 Анализ номеров грузов...")
            
            response = self.session.get(f"{API_BASE}/operator/cargo/list?per_page=20&sort_by=created_at&sort_order=desc")
            if response.status_code == 200:
                data = response.json()
                recent_cargos = data.get('items', [])
                
                self.log(f"📦 Анализируем последние {len(recent_cargos)} грузов:")
                
                cargo_numbers = []
                for cargo in recent_cargos:
                    cargo_number = cargo.get('cargo_number', 'N/A')
                    created_at = cargo.get('created_at', 'N/A')
                    cargo_numbers.append(cargo_number)
                    self.log(f"   - {cargo_number} (создан: {created_at})")
                
                # Проверяем на дубликаты
                duplicates = {}
                for number in cargo_numbers:
                    if number in duplicates:
                        duplicates[number] += 1
                    else:
                        duplicates[number] = 1
                
                duplicate_numbers = {k: v for k, v in duplicates.items() if v > 1}
                if duplicate_numbers:
                    self.log(f"🚨 НАЙДЕНЫ ДУБЛИРОВАННЫЕ НОМЕРА ГРУЗОВ:")
                    for number, count in duplicate_numbers.items():
                        self.log(f"   - {number}: {count} копий")
                    return False, duplicate_numbers
                else:
                    self.log("✅ Дублированных номеров грузов не найдено")
                    return True, {}
                    
            else:
                self.log(f"❌ Ошибка получения списка грузов: {response.status_code}", "ERROR")
                return False, {}
                
        except Exception as e:
            self.log(f"❌ Исключение при анализе номеров: {str(e)}", "ERROR")
            return False, {}
    
    def run_full_duplication_test(self):
        """Полный тест дублирования"""
        try:
            self.log("🚀 НАЧАЛО ПОЛНОГО ТЕСТА ДУБЛИРОВАНИЯ")
            self.log("=" * 80)
            
            # 1. Авторизация
            if not self.authenticate_admin():
                return False
            
            # 2. Получение уведомлений
            notifications = self.get_notifications()
            if not notifications:
                self.log("❌ Нет уведомлений для тестирования", "ERROR")
                return False
            
            # 3. Анализ существующих дубликатов
            self.log("\n📊 АНАЛИЗ СУЩЕСТВУЮЩИХ ДУБЛИКАТОВ:")
            placement_ok, placement_dups = self.check_placement_list_duplicates()
            cargo_ok, cargo_dups = self.analyze_cargo_numbers()
            
            # 4. Поиск подходящего уведомления для тестирования
            test_notification = None
            for notif in notifications:
                if isinstance(notif, dict) and notif.get('status') == 'pending_acceptance':
                    test_notification = notif
                    break
            
            if not test_notification:
                # Ищем уведомления в других статусах
                for notif in notifications:
                    if isinstance(notif, dict):
                        test_notification = notif
                        break
            
            if not test_notification:
                self.log("❌ Не найдено подходящих уведомлений для тестирования", "ERROR")
                return False
            
            notification_id = test_notification.get('id')
            notification_status = test_notification.get('status')
            request_number = test_notification.get('request_number', 'N/A')
            
            self.log(f"\n🎯 ТЕСТИРУЕМ УВЕДОМЛЕНИЕ:")
            self.log(f"   - ID: {notification_id}")
            self.log(f"   - Статус: {notification_status}")
            self.log(f"   - Номер заявки: {request_number}")
            
            # 5. Тестирование complete endpoint (если уведомление в подходящем статусе)
            if notification_status in ['in_processing', 'pending_acceptance']:
                # Если статус pending_acceptance, сначала принимаем
                if notification_status == 'pending_acceptance':
                    self.log(f"\n✋ Принимаем уведомление...")
                    accept_response = self.session.post(f"{API_BASE}/operator/warehouse-notifications/{notification_id}/accept")
                    if accept_response.status_code == 200:
                        self.log("✅ Уведомление принято")
                        time.sleep(1)
                    else:
                        self.log(f"❌ Ошибка принятия: {accept_response.status_code}", "ERROR")
                
                # Тестируем complete
                self.log(f"\n🎯 КРИТИЧЕСКИЙ ТЕСТ COMPLETE:")
                complete_ok, created_count = self.test_complete_endpoint_duplication(notification_id)
                
                if not complete_ok:
                    self.log(f"🚨 ПРОБЛЕМА ДУБЛИРОВАНИЯ ПОДТВЕРЖДЕНА! Создано {created_count} грузов", "ERROR")
                
            else:
                self.log(f"⚠️ Уведомление в статусе {notification_status}, пропускаем тест complete", "WARNING")
            
            # 6. Финальная проверка дубликатов
            self.log(f"\n📊 ФИНАЛЬНАЯ ПРОВЕРКА ДУБЛИКАТОВ:")
            final_placement_ok, final_placement_dups = self.check_placement_list_duplicates()
            final_cargo_ok, final_cargo_dups = self.analyze_cargo_numbers()
            
            self.log("=" * 80)
            self.log("🎯 ИТОГОВЫЙ РЕЗУЛЬТАТ ДИАГНОСТИКИ ДУБЛИРОВАНИЯ")
            
            if not placement_ok or not cargo_ok or not final_placement_ok or not final_cargo_ok:
                self.log("🚨 ДУБЛИРОВАНИЕ ОБНАРУЖЕНО!", "ERROR")
                return False
            else:
                self.log("✅ Дублирование не обнаружено")
                return True
                
        except Exception as e:
            self.log(f"❌ Критическое исключение в тесте: {str(e)}", "ERROR")
            return False

def main():
    """Главная функция"""
    print("🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА ДУБЛИРОВАНИЯ ЗАЯВОК В TAJLINE.TJ")
    print("=" * 80)
    print("ПРОБЛЕМА: При нажатии кнопки 'Принять груз' создаются дубликаты")
    print("ЦЕЛЬ: Найти корневую причину дублирования в функции complete_cargo_processing")
    print("=" * 80)
    
    tester = CargoDuplicationTester()
    
    try:
        success = tester.run_full_duplication_test()
        
        print("\n" + "=" * 80)
        print("🎯 ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("=" * 80)
        
        if success:
            print("✅ Дублирование не обнаружено или исправлено")
        else:
            print("🚨 ДУБЛИРОВАНИЕ ПОДТВЕРЖДЕНО - требуется исправление!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Тест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {str(e)}")

if __name__ == "__main__":
    main()