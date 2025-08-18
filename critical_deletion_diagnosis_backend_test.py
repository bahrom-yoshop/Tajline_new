#!/usr/bin/env python3
"""
КРИТИЧЕСКАЯ ДИАГНОСТИКА: Проблемы с удалением в системе TAJLINE.TJ
Диагностирует две критические проблемы:
1) НЕ УДАЛЯЮТСЯ ЗАЯВКИ НА ЗАБОР ПРИ МАССОВОМ УДАЛЕНИИ
2) ГРУЗЫ В РАЗМЕЩЕНИИ ТОЛЬКО МЕНЯЮТСЯ МЕСТАМИ (100008/01 ↔ 100008/02)
"""

import requests
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "https://cargo-talk.preview.emergentagent.com/api"
ADMIN_PHONE = "+79999888777"
ADMIN_PASSWORD = "admin123"

class TajlineDeletionDiagnostic:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.admin_user_info = None
        
    def authenticate_admin(self):
        """Авторизация администратора"""
        print("🔐 АВТОРИЗАЦИЯ АДМИНИСТРАТОРА...")
        
        login_data = {
            "phone": ADMIN_PHONE,
            "password": ADMIN_PASSWORD
        }
        
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.admin_user_info = data.get("user")
                
                # Устанавливаем заголовок авторизации
                self.session.headers.update({
                    "Authorization": f"Bearer {self.admin_token}",
                    "Content-Type": "application/json"
                })
                
                print(f"   ✅ Успешная авторизация: {self.admin_user_info.get('full_name')} ({self.admin_user_info.get('user_number')})")
                print(f"   📋 Роль: {self.admin_user_info.get('role')}")
                return True
            else:
                print(f"   ❌ Ошибка авторизации: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Исключение при авторизации: {e}")
            return False
    
    def analyze_pickup_requests_state(self):
        """Анализ текущего состояния заявок на забор"""
        print("\n📊 АНАЛИЗ СОСТОЯНИЯ ЗАЯВОК НА ЗАБОР...")
        
        # Проверяем заявки на забор через operator endpoint
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/pickup-requests")
            print(f"   GET /api/operator/pickup-requests - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                pickup_requests = data.get("pickup_requests", [])
                total_count = data.get("total_count", 0)
                
                print(f"   📋 Всего заявок на забор: {total_count}")
                print(f"   📋 Активных заявок: {len(pickup_requests)}")
                
                if pickup_requests:
                    print("   📋 Первые 3 заявки:")
                    for i, req in enumerate(pickup_requests[:3]):
                        print(f"      {i+1}. ID: {req.get('id')}, Номер: {req.get('request_number')}, Статус: {req.get('status')}")
                
                return pickup_requests, total_count
            else:
                print(f"   ❌ Ошибка получения заявок на забор: {response.text}")
                return [], 0
                
        except Exception as e:
            print(f"   ❌ Исключение при получении заявок на забор: {e}")
            return [], 0
    
    def analyze_cargo_requests_state(self):
        """Анализ состояния заявок на груз"""
        print("\n📊 АНАЛИЗ СОСТОЯНИЯ ЗАЯВОК НА ГРУЗ...")
        
        try:
            response = self.session.get(f"{BACKEND_URL}/admin/cargo-requests")
            print(f"   GET /api/admin/cargo-requests - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    cargo_requests = data
                else:
                    cargo_requests = data.get("items", data.get("cargo_requests", []))
                
                print(f"   📋 Всего заявок на груз: {len(cargo_requests)}")
                
                if cargo_requests:
                    print("   📋 Первые 3 заявки:")
                    for i, req in enumerate(cargo_requests[:3]):
                        print(f"      {i+1}. ID: {req.get('id')}, Номер: {req.get('request_number')}, Отправитель: {req.get('sender_full_name')}")
                
                return cargo_requests
            else:
                print(f"   ❌ Ошибка получения заявок на груз: {response.text}")
                return []
                
        except Exception as e:
            print(f"   ❌ Исключение при получении заявок на груз: {e}")
            return []
    
    def search_specific_cargo(self, cargo_numbers):
        """Поиск конкретных грузов 100008/01 и 100008/02"""
        print(f"\n🔍 ПОИСК КОНКРЕТНЫХ ГРУЗОВ: {cargo_numbers}")
        
        found_cargo = {}
        
        # Поиск в размещении
        try:
            response = self.session.get(f"{BACKEND_URL}/operator/cargo/available-for-placement")
            print(f"   GET /api/operator/cargo/available-for-placement - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                print(f"   📋 Всего грузов в размещении: {len(items)}")
                
                for cargo_number in cargo_numbers:
                    for item in items:
                        if item.get("cargo_number") == cargo_number:
                            found_cargo[cargo_number] = {
                                "location": "placement",
                                "data": item,
                                "id": item.get("id"),
                                "status": item.get("processing_status"),
                                "payment_status": item.get("payment_status")
                            }
                            print(f"   ✅ Найден груз {cargo_number} в размещении:")
                            print(f"      ID: {item.get('id')}")
                            print(f"      Отправитель: {item.get('sender_full_name')}")
                            print(f"      Статус: {item.get('processing_status')}")
                            print(f"      Оплата: {item.get('payment_status')}")
                            break
                
        except Exception as e:
            print(f"   ❌ Исключение при поиске в размещении: {e}")
        
        # Поиск в общих грузах
        try:
            response = self.session.get(f"{BACKEND_URL}/admin/cargo")
            print(f"   GET /api/admin/cargo - Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                for cargo_number in cargo_numbers:
                    if cargo_number not in found_cargo:
                        for item in items:
                            if item.get("cargo_number") == cargo_number:
                                found_cargo[cargo_number] = {
                                    "location": "general",
                                    "data": item,
                                    "id": item.get("id"),
                                    "status": item.get("status"),
                                    "payment_status": item.get("payment_status", "unknown")
                                }
                                print(f"   ✅ Найден груз {cargo_number} в общих грузах:")
                                print(f"      ID: {item.get('id')}")
                                print(f"      Статус: {item.get('status')}")
                                break
                
        except Exception as e:
            print(f"   ❌ Исключение при поиске в общих грузах: {e}")
        
        # Отчет о поиске
        for cargo_number in cargo_numbers:
            if cargo_number not in found_cargo:
                print(f"   ❌ Груз {cargo_number} НЕ НАЙДЕН в системе")
        
        return found_cargo
    
    def test_bulk_pickup_deletion(self, pickup_requests):
        """Тестирование массового удаления заявок на забор"""
        print(f"\n🗑️ ТЕСТИРОВАНИЕ МАССОВОГО УДАЛЕНИЯ ЗАЯВОК НА ЗАБОР...")
        
        if not pickup_requests:
            print("   ⚠️ Нет заявок на забор для тестирования удаления")
            return False
        
        # Берем первые 2-3 заявки для тестирования
        test_requests = pickup_requests[:3]
        print(f"   📋 Выбрано {len(test_requests)} заявок для тестирования удаления")
        
        deletion_results = []
        
        for i, request in enumerate(test_requests):
            request_id = request.get("id")
            request_number = request.get("request_number", "unknown")
            
            print(f"\n   🗑️ Удаление заявки {i+1}: {request_number} (ID: {request_id})")
            
            try:
                # Пробуем разные endpoints для удаления
                endpoints_to_try = [
                    f"/admin/cargo-applications/{request_id}",
                    f"/operator/pickup-requests/{request_id}",
                    f"/admin/pickup-requests/{request_id}"
                ]
                
                deleted = False
                for endpoint in endpoints_to_try:
                    try:
                        response = self.session.delete(f"{BACKEND_URL}{endpoint}")
                        print(f"      DELETE {endpoint} - Status: {response.status_code}")
                        
                        if response.status_code in [200, 204]:
                            print(f"      ✅ Успешное удаление через {endpoint}")
                            deletion_results.append({
                                "request_id": request_id,
                                "request_number": request_number,
                                "deleted": True,
                                "endpoint": endpoint,
                                "response": response.text
                            })
                            deleted = True
                            break
                        else:
                            print(f"      ❌ Ошибка удаления: {response.text}")
                            
                    except Exception as e:
                        print(f"      ❌ Исключение при удалении через {endpoint}: {e}")
                
                if not deleted:
                    deletion_results.append({
                        "request_id": request_id,
                        "request_number": request_number,
                        "deleted": False,
                        "endpoint": None,
                        "error": "Все endpoints вернули ошибку"
                    })
                
            except Exception as e:
                print(f"      ❌ Общее исключение при удалении заявки: {e}")
                deletion_results.append({
                    "request_id": request_id,
                    "request_number": request_number,
                    "deleted": False,
                    "endpoint": None,
                    "error": str(e)
                })
        
        # Проверяем результаты удаления
        print(f"\n   📊 РЕЗУЛЬТАТЫ МАССОВОГО УДАЛЕНИЯ:")
        successful_deletions = sum(1 for r in deletion_results if r["deleted"])
        print(f"   ✅ Успешно удалено: {successful_deletions}/{len(deletion_results)}")
        
        if successful_deletions > 0:
            # Проверяем, действительно ли заявки удалились
            print(f"\n   🔍 ПРОВЕРКА ФАКТИЧЕСКОГО УДАЛЕНИЯ...")
            pickup_requests_after, total_after = self.analyze_pickup_requests_state()
            
            print(f"   📊 Заявок было: {len(pickup_requests)}")
            print(f"   📊 Заявок стало: {total_after}")
            print(f"   📊 Разница: {len(pickup_requests) - total_after}")
            
            if len(pickup_requests) - total_after == successful_deletions:
                print(f"   ✅ МАССОВОЕ УДАЛЕНИЕ РАБОТАЕТ КОРРЕКТНО!")
                return True
            else:
                print(f"   ❌ ПРОБЛЕМА: Количество удаленных заявок не соответствует ожидаемому")
                return False
        else:
            print(f"   ❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: НИ ОДНА ЗАЯВКА НЕ БЫЛА УДАЛЕНА!")
            return False
    
    def test_cargo_deletion_swapping(self, found_cargo):
        """Тестирование проблемы смены мест грузов при удалении"""
        print(f"\n🔄 ТЕСТИРОВАНИЕ ПРОБЛЕМЫ СМЕНЫ МЕСТ ГРУЗОВ...")
        
        if not found_cargo:
            print("   ⚠️ Не найдены грузы 100008/01 и 100008/02 для тестирования")
            return False
        
        # Записываем начальное состояние
        initial_state = {}
        for cargo_number, cargo_info in found_cargo.items():
            initial_state[cargo_number] = {
                "id": cargo_info["id"],
                "location": cargo_info["location"],
                "status": cargo_info["status"]
            }
            print(f"   📋 Начальное состояние {cargo_number}:")
            print(f"      ID: {cargo_info['id']}")
            print(f"      Местоположение: {cargo_info['location']}")
            print(f"      Статус: {cargo_info['status']}")
        
        # Пробуем удалить первый груз
        test_cargo_numbers = list(found_cargo.keys())
        if len(test_cargo_numbers) >= 1:
            first_cargo = test_cargo_numbers[0]
            first_cargo_info = found_cargo[first_cargo]
            
            print(f"\n   🗑️ ПОПЫТКА УДАЛЕНИЯ ГРУЗА: {first_cargo}")
            print(f"      ID для удаления: {first_cargo_info['id']}")
            
            # Пробуем разные endpoints для удаления груза
            deletion_endpoints = [
                f"/operator/cargo/{first_cargo_info['id']}/remove-from-placement",
                f"/admin/cargo/{first_cargo_info['id']}",
                f"/operator/cargo/bulk-remove-from-placement"
            ]
            
            deletion_attempted = False
            
            for endpoint in deletion_endpoints:
                try:
                    if "bulk-remove" in endpoint:
                        # Для bulk удаления используем POST с JSON
                        payload = {"cargo_ids": [first_cargo_info['id']]}
                        response = self.session.delete(f"{BACKEND_URL}{endpoint}", json=payload)
                    else:
                        response = self.session.delete(f"{BACKEND_URL}{endpoint}")
                    
                    print(f"      DELETE {endpoint} - Status: {response.status_code}")
                    
                    if response.status_code in [200, 204]:
                        print(f"      ✅ Удаление выполнено через {endpoint}")
                        print(f"      📄 Ответ: {response.text}")
                        deletion_attempted = True
                        break
                    else:
                        print(f"      ❌ Ошибка удаления: {response.text}")
                        
                except Exception as e:
                    print(f"      ❌ Исключение при удалении через {endpoint}: {e}")
            
            if deletion_attempted:
                # Проверяем состояние после удаления
                print(f"\n   🔍 ПРОВЕРКА СОСТОЯНИЯ ПОСЛЕ УДАЛЕНИЯ...")
                updated_cargo = self.search_specific_cargo(test_cargo_numbers)
                
                # Анализируем изменения
                print(f"\n   📊 АНАЛИЗ ИЗМЕНЕНИЙ:")
                
                for cargo_number in test_cargo_numbers:
                    print(f"\n   📋 Груз {cargo_number}:")
                    
                    if cargo_number in initial_state and cargo_number in updated_cargo:
                        initial_id = initial_state[cargo_number]["id"]
                        updated_id = updated_cargo[cargo_number]["id"]
                        
                        print(f"      Было ID: {initial_id}")
                        print(f"      Стало ID: {updated_id}")
                        
                        if initial_id != updated_id:
                            print(f"      ⚠️ ID ИЗМЕНИЛСЯ! Возможна смена мест")
                        else:
                            print(f"      ✅ ID не изменился")
                    
                    elif cargo_number in initial_state and cargo_number not in updated_cargo:
                        print(f"      ✅ Груз УДАЛЕН из системы (ожидаемое поведение)")
                    
                    elif cargo_number not in initial_state and cargo_number in updated_cargo:
                        print(f"      ⚠️ Груз ПОЯВИЛСЯ в системе (неожиданно)")
                    
                    else:
                        print(f"      ❓ Состояние не изменилось")
                
                # Проверяем, произошла ли смена номеров
                if len(test_cargo_numbers) >= 2:
                    cargo1, cargo2 = test_cargo_numbers[0], test_cargo_numbers[1]
                    
                    if (cargo1 in initial_state and cargo2 in updated_cargo and 
                        cargo2 in initial_state and cargo1 in updated_cargo):
                        
                        if (initial_state[cargo1]["id"] == updated_cargo[cargo2]["id"] and
                            initial_state[cargo2]["id"] == updated_cargo[cargo1]["id"]):
                            
                            print(f"\n   🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА ПОДТВЕРЖДЕНА!")
                            print(f"   🔄 Грузы {cargo1} и {cargo2} ПОМЕНЯЛИСЬ МЕСТАМИ!")
                            print(f"   ❌ Фактического удаления НЕ ПРОИЗОШЛО!")
                            return False
                
                return True
            else:
                print(f"   ❌ Не удалось выполнить удаление ни через один endpoint")
                return False
        
        return False
    
    def check_backend_logs(self):
        """Проверка логов backend на предмет ошибок при удалении"""
        print(f"\n📋 ПРОВЕРКА ЛОГОВ BACKEND...")
        
        # Пытаемся получить логи через различные endpoints
        log_endpoints = [
            "/admin/system/logs",
            "/admin/logs",
            "/system/logs"
        ]
        
        for endpoint in log_endpoints:
            try:
                response = self.session.get(f"{BACKEND_URL}{endpoint}")
                print(f"   GET {endpoint} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    logs = response.json()
                    print(f"   ✅ Получены логи через {endpoint}")
                    
                    # Ищем ошибки связанные с удалением
                    deletion_errors = []
                    if isinstance(logs, list):
                        for log_entry in logs:
                            if isinstance(log_entry, dict):
                                message = log_entry.get("message", "").lower()
                                if any(keyword in message for keyword in ["delete", "remove", "error", "exception"]):
                                    deletion_errors.append(log_entry)
                    
                    if deletion_errors:
                        print(f"   ⚠️ Найдено {len(deletion_errors)} записей с ошибками удаления:")
                        for i, error in enumerate(deletion_errors[:5]):  # Показываем первые 5
                            print(f"      {i+1}. {error.get('timestamp', 'unknown')}: {error.get('message', 'no message')}")
                    else:
                        print(f"   ✅ Ошибок удаления в логах не найдено")
                    
                    return True
                    
            except Exception as e:
                print(f"   ❌ Исключение при получении логов через {endpoint}: {e}")
        
        print(f"   ⚠️ Не удалось получить логи backend через доступные endpoints")
        return False
    
    def run_comprehensive_diagnosis(self):
        """Запуск полной диагностики проблем с удалением"""
        print("=" * 80)
        print("🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА ПРОБЛЕМ С УДАЛЕНИЕМ В TAJLINE.TJ")
        print("=" * 80)
        
        # 1. Авторизация администратора
        if not self.authenticate_admin():
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось авторизоваться как администратор")
            return False
        
        # 2. Анализ текущего состояния заявок на забор
        pickup_requests, pickup_total = self.analyze_pickup_requests_state()
        
        # 3. Анализ заявок на груз
        cargo_requests = self.analyze_cargo_requests_state()
        
        # 4. Поиск конкретных грузов 100008/01 и 100008/02
        target_cargo = ["100008/01", "100008/02"]
        found_cargo = self.search_specific_cargo(target_cargo)
        
        # 5. Тестирование массового удаления заявок на забор
        print("\n" + "=" * 60)
        print("🧪 ТЕСТИРОВАНИЕ ПРОБЛЕМЫ 1: МАССОВОЕ УДАЛЕНИЕ ЗАЯВОК НА ЗАБОР")
        print("=" * 60)
        
        bulk_deletion_works = self.test_bulk_pickup_deletion(pickup_requests)
        
        # 6. Тестирование проблемы смены мест грузов
        print("\n" + "=" * 60)
        print("🧪 ТЕСТИРОВАНИЕ ПРОБЛЕМЫ 2: СМЕНА МЕСТ ГРУЗОВ ПРИ УДАЛЕНИИ")
        print("=" * 60)
        
        cargo_swapping_issue = not self.test_cargo_deletion_swapping(found_cargo)
        
        # 7. Проверка логов backend
        self.check_backend_logs()
        
        # 8. Итоговый отчет
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ДИАГНОСТИКИ")
        print("=" * 80)
        
        print(f"🔐 Авторизация администратора: ✅ Успешно")
        print(f"📊 Всего заявок на забор: {pickup_total}")
        print(f"📊 Всего заявок на груз: {len(cargo_requests)}")
        print(f"🔍 Найдено целевых грузов: {len(found_cargo)}/{len(target_cargo)}")
        
        print(f"\n🚨 ПРОБЛЕМА 1 - Массовое удаление заявок на забор:")
        if bulk_deletion_works:
            print(f"   ✅ РАБОТАЕТ КОРРЕКТНО")
        else:
            print(f"   ❌ ПОДТВЕРЖДЕНА ПРОБЛЕМА - заявки не удаляются при массовом удалении")
        
        print(f"\n🚨 ПРОБЛЕМА 2 - Смена мест грузов при удалении:")
        if cargo_swapping_issue:
            print(f"   ❌ ПОДТВЕРЖДЕНА ПРОБЛЕМА - грузы меняются местами вместо удаления")
        else:
            print(f"   ✅ Проблема не воспроизведена или исправлена")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        if not bulk_deletion_works:
            print(f"   1. Проверить endpoint /api/admin/cargo-applications/{{id}} для удаления заявок")
            print(f"   2. Убедиться что frontend правильно вызывает API удаления")
            print(f"   3. Проверить права доступа администратора к удалению заявок")
        
        if cargo_swapping_issue:
            print(f"   4. Исследовать логику удаления грузов из размещения")
            print(f"   5. Проверить целостность данных в коллекциях MongoDB")
            print(f"   6. Убедиться что ID грузов не переиспользуются")
        
        return True

def main():
    """Главная функция для запуска диагностики"""
    diagnostic = TajlineDeletionDiagnostic()
    
    try:
        success = diagnostic.run_comprehensive_diagnosis()
        
        if success:
            print(f"\n✅ Диагностика завершена успешно")
            sys.exit(0)
        else:
            print(f"\n❌ Диагностика завершена с ошибками")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Диагностика прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка диагностики: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()