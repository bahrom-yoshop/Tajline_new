#!/usr/bin/env python3
"""
🎯 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ: Полный флоу системы чата с автоматическим созданием
Тестирование системы автоматического создания чатов при создании заявок в TAJLINE.TJ

Цель: подтвердить что система автоматического создания чатов работает при создании заявок.
"""

import requests
import json
import sys
from datetime import datetime
import time

# Конфигурация
BACKEND_URL = "https://c1fee57d-64d0-4902-b6b6-459531853840.preview.emergentagent.com/api"

class ChatSystemTester:
    def __init__(self):
        self.admin_token = None
        self.operator_token = None
        self.test_cargo_id = None
        self.test_chat_id = None
        self.warehouse_id = None
        self.warehouse_name = None
        
    def log(self, message, level="INFO"):
        """Логирование с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def make_request(self, method, endpoint, data=None, token=None, files=None):
        """Универсальная функция для HTTP запросов"""
        url = f"{BACKEND_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        if files:
            # Для загрузки файлов убираем Content-Type
            headers.pop("Content-Type", None)
            
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                if files:
                    response = requests.post(url, headers=headers, files=files, data=data)
                else:
                    response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except Exception as e:
            self.log(f"❌ Request failed: {e}", "ERROR")
            return None
            
    def authenticate_admin(self):
        """Авторизация администратора"""
        self.log("🔐 Авторизация администратора...")
        
        response = self.make_request("POST", "/auth/login", {
            "phone": "+79999888777",
            "password": "admin123"
        })
        
        if response and response.status_code == 200:
            data = response.json()
            self.admin_token = data.get("access_token")
            user_info = data.get("user", {})
            self.log(f"✅ Администратор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
            return True
        else:
            self.log(f"❌ Ошибка авторизации администратора: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def authenticate_operator(self):
        """Авторизация оператора склада"""
        self.log("🔐 Авторизация оператора склада...")
        
        response = self.make_request("POST", "/auth/login", {
            "phone": "+79777888999",
            "password": "warehouse123"
        })
        
        if response and response.status_code == 200:
            data = response.json()
            self.operator_token = data.get("access_token")
            user_info = data.get("user", {})
            self.log(f"✅ Оператор авторизован: {user_info.get('full_name')} (роль: {user_info.get('role')})")
            return True
        else:
            self.log(f"❌ Ошибка авторизации оператора: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def get_warehouse_info(self):
        """Получить информацию о складах"""
        self.log("🏢 Получение информации о складах...")
        
        response = self.make_request("GET", "/operator/warehouses", token=self.operator_token)
        
        if response and response.status_code == 200:
            warehouses = response.json()
            if warehouses:
                warehouse = warehouses[0]
                self.warehouse_id = warehouse.get("id")
                self.warehouse_name = warehouse.get("name")
                self.log(f"✅ Найден склад: {self.warehouse_name} (ID: {self.warehouse_id})")
                return True
            else:
                self.log("❌ Склады не найдены", "ERROR")
                return False
        else:
            self.log(f"❌ Ошибка получения складов: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def create_cargo_with_chat(self):
        """Создать новую заявку с автоматическим чатом"""
        self.log("📦 Создание новой заявки с автоматическим чатом...")
        
        cargo_data = {
            "sender_full_name": "Тест Чата Системы",
            "sender_phone": "+79994445566",
            "sender_address": "Москва, ул. Чатовая 1",
            "recipient_full_name": "Получатель Чата",
            "recipient_phone": "+992904445566",
            "recipient_address": "Душанбе, ул. Чатовая 2",
            "cargo_items": [
                {
                    "cargo_name": "Тест чата груз 1",
                    "weight": 2.0,
                    "price_per_kg": 150
                },
                {
                    "cargo_name": "Тест чата груз 2",
                    "weight": 3.0,
                    "price_per_kg": 200
                }
            ],
            "destination_warehouse_id": self.warehouse_id,
            "destination_warehouse_name": self.warehouse_name,
            "route": "moscow_to_tajikistan",
            "payment_method": "cash",
            "payment_amount": 900,
            "description": "Тестовая заявка для проверки автоматического создания чата"
        }
        
        response = self.make_request("POST", "/operator/cargo/direct-accept", cargo_data, token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            self.test_cargo_id = data.get("created_cargo", [{}])[0].get("id")
            cargo_number = data.get("created_cargo", [{}])[0].get("cargo_number")
            base_request_number = data.get("base_request_number")
            
            self.log(f"✅ Заявка создана успешно:")
            self.log(f"   📦 Cargo ID: {self.test_cargo_id}")
            self.log(f"   🔢 Номер груза: {cargo_number}")
            self.log(f"   📋 Базовый номер заявки: {base_request_number}")
            
            return True
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log(f"❌ Ошибка создания заявки: {error_msg}", "ERROR")
            return False
            
    def check_automatic_chat_creation(self):
        """Проверить автоматическое создание чата"""
        self.log("💬 Проверка автоматического создания чата...")
        
        # Небольшая задержка для обработки
        time.sleep(2)
        
        response = self.make_request("GET", "/chat/list", token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            chats = data.get("chats", [])
            
            # Ищем чат для нашего груза
            cargo_chat = None
            for chat in chats:
                if chat.get("cargo_id") == self.test_cargo_id:
                    cargo_chat = chat
                    self.test_chat_id = chat.get("id")
                    break
                    
            if cargo_chat:
                self.log("✅ Чат автоматически создан!")
                self.log(f"   💬 Chat ID: {cargo_chat.get('id')}")
                self.log(f"   📦 Cargo ID: {cargo_chat.get('cargo_id')}")
                self.log(f"   🔢 Cargo Number: {cargo_chat.get('cargo_number')}")
                self.log(f"   📝 Title: {cargo_chat.get('title')}")
                
                # Проверяем участников
                participants = cargo_chat.get("participants", [])
                self.log(f"   👥 Участники чата ({len(participants)}):")
                
                operator_found = False
                admin_found = False
                
                for participant in participants:
                    role = participant.get("user_role")
                    name = participant.get("user_name")
                    self.log(f"      - {name} ({role})")
                    
                    if role == "warehouse_operator":
                        operator_found = True
                    elif role == "admin":
                        admin_found = True
                        
                if operator_found:
                    self.log("   ✅ Оператор добавлен в чат")
                else:
                    self.log("   ❌ Оператор НЕ найден в чате", "ERROR")
                    
                if admin_found:
                    self.log("   ✅ Администратор добавлен в чат")
                else:
                    self.log("   ❌ Администратор НЕ найден в чате", "ERROR")
                    
                return operator_found and admin_found
            else:
                self.log("❌ Чат для груза НЕ найден", "ERROR")
                return False
        else:
            self.log(f"❌ Ошибка получения списка чатов: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def check_system_message(self):
        """Проверить создание системного сообщения"""
        self.log("📨 Проверка системного сообщения...")
        
        if not self.test_chat_id:
            self.log("❌ Chat ID не найден", "ERROR")
            return False
            
        response = self.make_request("GET", f"/chat/{self.test_chat_id}/messages", token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            
            # Ищем системное сообщение
            system_message = None
            for message in messages:
                if message.get("message_type") == "system":
                    system_message = message
                    break
                    
            if system_message:
                self.log("✅ Системное сообщение найдено!")
                self.log(f"   📨 Message ID: {system_message.get('id')}")
                self.log(f"   📝 Text: {system_message.get('message_text')}")
                self.log(f"   👤 Sender: {system_message.get('sender_name')}")
                self.log(f"   🕐 Sent at: {system_message.get('sent_at')}")
                return True
            else:
                self.log("❌ Системное сообщение НЕ найдено", "ERROR")
                return False
        else:
            self.log(f"❌ Ошибка получения сообщений: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def test_chat_list_api(self):
        """Протестировать API списка чатов"""
        self.log("📋 Тестирование API списка чатов...")
        
        response = self.make_request("GET", "/chat/list", token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            chats = data.get("chats", [])
            total_count = data.get("total_count", 0)
            unread_total = data.get("unread_total", 0)
            
            self.log(f"✅ API списка чатов работает:")
            self.log(f"   📊 Всего чатов: {total_count}")
            self.log(f"   📬 Непрочитанных: {unread_total}")
            self.log(f"   📋 Получено чатов: {len(chats)}")
            
            # Проверяем что наш чат в списке
            our_chat_found = False
            for chat in chats:
                if chat.get("id") == self.test_chat_id:
                    our_chat_found = True
                    self.log(f"   ✅ Наш чат найден в списке: {chat.get('title')}")
                    break
                    
            if not our_chat_found:
                self.log("   ❌ Наш чат НЕ найден в списке", "ERROR")
                
            return our_chat_found
        else:
            self.log(f"❌ Ошибка API списка чатов: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def send_test_message(self):
        """Отправить тестовое сообщение в автоматически созданный чат"""
        self.log("💬 Отправка тестового сообщения...")
        
        if not self.test_chat_id:
            self.log("❌ Chat ID не найден", "ERROR")
            return False
            
        message_data = {
            "message_type": "text",
            "message_text": "Тестовое сообщение в автоматически созданный чат для груза. Проверяем функциональность системы чатов TAJLINE.TJ"
        }
        
        response = self.make_request("POST", f"/chat/{self.test_chat_id}/messages", message_data, token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            message_id = data.get("id")
            
            self.log("✅ Сообщение отправлено успешно!")
            self.log(f"   📨 Message ID: {message_id}")
            self.log(f"   📝 Text: {data.get('message_text')}")
            self.log(f"   👤 Sender: {data.get('sender_name')}")
            
            return True
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log(f"❌ Ошибка отправки сообщения: {error_msg}", "ERROR")
            return False
            
    def verify_message_saving_and_timestamp(self):
        """Проверить сохранение сообщения и обновление времени last_message_at"""
        self.log("🕐 Проверка сохранения сообщения и обновления времени...")
        
        # Небольшая задержка
        time.sleep(1)
        
        # Проверяем сообщения в чате
        response = self.make_request("GET", f"/chat/{self.test_chat_id}/messages", token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            
            # Ищем наше тестовое сообщение
            test_message_found = False
            for message in messages:
                if "Тестовое сообщение в автоматически созданный чат" in message.get("message_text", ""):
                    test_message_found = True
                    self.log("✅ Тестовое сообщение найдено в чате!")
                    self.log(f"   📨 Message ID: {message.get('id')}")
                    self.log(f"   🕐 Sent at: {message.get('sent_at')}")
                    break
                    
            if not test_message_found:
                self.log("❌ Тестовое сообщение НЕ найдено в чате", "ERROR")
                return False
                
        else:
            self.log(f"❌ Ошибка получения сообщений: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
        # Проверяем обновление last_message_at в чате
        response = self.make_request("GET", "/chat/list", token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            chats = data.get("chats", [])
            
            for chat in chats:
                if chat.get("id") == self.test_chat_id:
                    last_message_at = chat.get("last_message_at")
                    if last_message_at:
                        self.log("✅ Время last_message_at обновлено!")
                        self.log(f"   🕐 Last message at: {last_message_at}")
                        return True
                    else:
                        self.log("❌ Время last_message_at НЕ обновлено", "ERROR")
                        return False
                        
            self.log("❌ Чат не найден при проверке last_message_at", "ERROR")
            return False
        else:
            self.log(f"❌ Ошибка получения чатов для проверки времени: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def show_complete_chat_structure(self):
        """Показать полную структуру созданного чата"""
        self.log("🏗️ Показ полной структуры созданного чата...")
        
        if not self.test_chat_id:
            self.log("❌ Chat ID не найден", "ERROR")
            return False
            
        # Получаем информацию о чате
        response = self.make_request("GET", "/chat/list", token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            chats = data.get("chats", [])
            
            chat_info = None
            for chat in chats:
                if chat.get("id") == self.test_chat_id:
                    chat_info = chat
                    break
                    
            if chat_info:
                self.log("📋 ПОЛНАЯ СТРУКТУРА ЧАТА:")
                self.log(f"   💬 ID: {chat_info.get('id')}")
                self.log(f"   📝 Title: {chat_info.get('title')}")
                self.log(f"   🏷️ Type: {chat_info.get('chat_type')}")
                self.log(f"   📦 Cargo ID: {chat_info.get('cargo_id')}")
                self.log(f"   🔢 Cargo Number: {chat_info.get('cargo_number')}")
                self.log(f"   👤 Created by: {chat_info.get('created_by')}")
                self.log(f"   🕐 Created at: {chat_info.get('created_at')}")
                self.log(f"   🕐 Updated at: {chat_info.get('updated_at')}")
                self.log(f"   🕐 Last message at: {chat_info.get('last_message_at')}")
                self.log(f"   📬 Unread count: {chat_info.get('unread_count', {})}")
                self.log(f"   📁 Is archived: {chat_info.get('is_archived', False)}")
                
                participants = chat_info.get("participants", [])
                self.log(f"   👥 Participants ({len(participants)}):")
                for i, participant in enumerate(participants, 1):
                    self.log(f"      {i}. {participant.get('user_name')} ({participant.get('user_role')})")
                    self.log(f"         - User ID: {participant.get('user_id')}")
                    self.log(f"         - Joined at: {participant.get('joined_at')}")
                    self.log(f"         - Is active: {participant.get('is_active')}")
                    
                return True
            else:
                self.log("❌ Информация о чате не найдена", "ERROR")
                return False
        else:
            self.log(f"❌ Ошибка получения информации о чате: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def show_system_message_details(self):
        """Показать детали системного сообщения"""
        self.log("📨 ДЕТАЛИ СИСТЕМНОГО СООБЩЕНИЯ:")
        
        if not self.test_chat_id:
            self.log("❌ Chat ID не найден", "ERROR")
            return False
            
        response = self.make_request("GET", f"/chat/{self.test_chat_id}/messages", token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            
            system_messages = [msg for msg in messages if msg.get("message_type") == "system"]
            
            if system_messages:
                for i, msg in enumerate(system_messages, 1):
                    self.log(f"   📨 Системное сообщение #{i}:")
                    self.log(f"      - ID: {msg.get('id')}")
                    self.log(f"      - Text: {msg.get('message_text')}")
                    self.log(f"      - Sender: {msg.get('sender_name')} ({msg.get('sender_role')})")
                    self.log(f"      - Sent at: {msg.get('sent_at')}")
                    self.log(f"      - Chat ID: {msg.get('chat_id')}")
                    
                return True
            else:
                self.log("❌ Системные сообщения не найдены", "ERROR")
                return False
        else:
            self.log(f"❌ Ошибка получения сообщений: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def verify_cargo_number_in_chat(self):
        """Убедиться что cargo_number заполнен правильно"""
        self.log("🔢 Проверка правильности заполнения cargo_number...")
        
        if not self.test_chat_id:
            self.log("❌ Chat ID не найден", "ERROR")
            return False
            
        response = self.make_request("GET", "/chat/list", token=self.operator_token)
        
        if response and response.status_code == 200:
            data = response.json()
            chats = data.get("chats", [])
            
            for chat in chats:
                if chat.get("id") == self.test_chat_id:
                    cargo_number = chat.get("cargo_number")
                    cargo_id = chat.get("cargo_id")
                    
                    if cargo_number:
                        self.log(f"✅ Cargo number заполнен: {cargo_number}")
                        
                        # Проверяем соответствие с грузом
                        if cargo_id == self.test_cargo_id:
                            self.log(f"✅ Cargo ID соответствует: {cargo_id}")
                            return True
                        else:
                            self.log(f"❌ Cargo ID НЕ соответствует: ожидался {self.test_cargo_id}, получен {cargo_id}", "ERROR")
                            return False
                    else:
                        self.log("❌ Cargo number НЕ заполнен", "ERROR")
                        return False
                        
            self.log("❌ Чат не найден при проверке cargo_number", "ERROR")
            return False
        else:
            self.log(f"❌ Ошибка получения чатов: {response.status_code if response else 'No response'}", "ERROR")
            return False
            
    def cleanup_test_data(self):
        """Очистка тестовых данных"""
        self.log("🧹 Очистка тестовых данных...")
        
        # Удаляем тестовый груз
        if self.test_cargo_id:
            response = self.make_request("DELETE", f"/admin/cargo/{self.test_cargo_id}", token=self.admin_token)
            if response and response.status_code == 200:
                self.log("✅ Тестовый груз удален")
            else:
                self.log("⚠️ Не удалось удалить тестовый груз")
                
        # Удаляем тестовый чат
        if self.test_chat_id:
            response = self.make_request("DELETE", f"/chat/{self.test_chat_id}", token=self.admin_token)
            if response and response.status_code == 200:
                self.log("✅ Тестовый чат удален")
            else:
                self.log("⚠️ Не удалось удалить тестовый чат")
                
    def run_complete_test(self):
        """Запуск полного тестирования"""
        self.log("🚀 НАЧАЛО КРИТИЧЕСКОГО ТЕСТИРОВАНИЯ СИСТЕМЫ ЧАТА С АВТОМАТИЧЕСКИМ СОЗДАНИЕМ")
        self.log("=" * 80)
        
        test_results = []
        
        # 1. Авторизация
        test_results.append(("Авторизация администратора", self.authenticate_admin()))
        test_results.append(("Авторизация оператора", self.authenticate_operator()))
        
        # 2. Получение информации о складах
        test_results.append(("Получение информации о складах", self.get_warehouse_info()))
        
        # 3. Создание заявки с автоматическим чатом
        test_results.append(("Создание заявки с автоматическим чатом", self.create_cargo_with_chat()))
        
        # 4. Проверка автоматического создания чата
        test_results.append(("Проверка автоматического создания чата", self.check_automatic_chat_creation()))
        
        # 5. Проверка системного сообщения
        test_results.append(("Проверка системного сообщения", self.check_system_message()))
        
        # 6. Тестирование API списка чатов
        test_results.append(("Тестирование API списка чатов", self.test_chat_list_api()))
        
        # 7. Отправка тестового сообщения
        test_results.append(("Отправка тестового сообщения", self.send_test_message()))
        
        # 8. Проверка сохранения сообщения и обновления времени
        test_results.append(("Проверка сохранения сообщения и времени", self.verify_message_saving_and_timestamp()))
        
        # 9. Проверка cargo_number
        test_results.append(("Проверка cargo_number", self.verify_cargo_number_in_chat()))
        
        # 10. Показ структуры чата
        test_results.append(("Показ структуры чата", self.show_complete_chat_structure()))
        
        # 11. Показ системного сообщения
        test_results.append(("Показ системного сообщения", self.show_system_message_details()))
        
        # Подсчет результатов
        self.log("=" * 80)
        self.log("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            self.log(f"   {status}: {test_name}")
            if result:
                passed += 1
            else:
                failed += 1
                
        success_rate = (passed / len(test_results)) * 100 if test_results else 0
        
        self.log("=" * 80)
        self.log(f"📈 ИТОГОВАЯ СТАТИСТИКА:")
        self.log(f"   ✅ Пройдено: {passed}")
        self.log(f"   ❌ Провалено: {failed}")
        self.log(f"   📊 Процент успеха: {success_rate:.1f}%")
        
        if success_rate >= 90:
            self.log("🎉 КРИТИЧЕСКОЕ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            self.log("💬 Система автоматического создания чатов работает корректно!")
        elif success_rate >= 70:
            self.log("⚠️ Тестирование завершено с предупреждениями")
            self.log("🔧 Требуются минорные исправления")
        else:
            self.log("❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ!")
            self.log("🚨 Система требует серьезных исправлений")
            
        # Очистка тестовых данных
        self.cleanup_test_data()
        
        return success_rate >= 90

def main():
    """Главная функция"""
    tester = ChatSystemTester()
    
    try:
        success = tester.run_complete_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        tester.log("⚠️ Тестирование прервано пользователем")
        tester.cleanup_test_data()
        sys.exit(1)
    except Exception as e:
        tester.log(f"💥 Критическая ошибка: {e}", "ERROR")
        tester.cleanup_test_data()
        sys.exit(1)

if __name__ == "__main__":
    main()