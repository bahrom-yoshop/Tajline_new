from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
import os
import jwt
import bcrypt
from pymongo import MongoClient
import uuid
from enum import Enum
import qrcode
from io import BytesIO
import base64
from PIL import Image
import re
import math  # Добавляем для пагинации
from bson import ObjectId
import json
import asyncio
import random  # Добавляем для генерации номеров

app = FastAPI()

# CORS настройка
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB подключение
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'cargo_transport')
client = MongoClient(MONGO_URL)
db = client[DB_NAME]  # Используем имя базы из переменной окружения

# JWT настройки
SECRET_KEY = "cargo_transport_secret_key_2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 часа для улучшенной сессии

security = HTTPBearer()

# WebSocket Connection Manager для real-time отслеживания курьеров
class ConnectionManager:
    def __init__(self):
        # Словарь подключений: user_id -> {"websocket": WebSocket, "role": str, "warehouse_ids": List[str]}
        self.connections: Dict[str, Dict] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, user_role: str, warehouse_ids: List[str] = None):
        """Подключить WebSocket клиента"""
        await websocket.accept()
        self.connections[user_id] = {
            "websocket": websocket,
            "role": user_role,
            "warehouse_ids": warehouse_ids or [],
            "connected_at": datetime.utcnow()
        }
        print(f"📡 WebSocket connected: User {user_id} (role: {user_role})")
        
    def disconnect(self, user_id: str):
        """Отключить WebSocket клиента"""
        if user_id in self.connections:
            del self.connections[user_id]
            print(f"📡 WebSocket disconnected: User {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Отправить сообщение конкретному пользователю"""
        if user_id in self.connections:
            try:
                websocket = self.connections[user_id]["websocket"]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"❌ Error sending message to {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast_to_admins(self, message: dict):
        """Отправить сообщение всем админам"""
        disconnected = []
        for user_id, connection in self.connections.items():
            if connection["role"] == "admin":
                try:
                    await connection["websocket"].send_text(json.dumps(message))
                except Exception as e:
                    print(f"❌ Error broadcasting to admin {user_id}: {e}")
                    disconnected.append(user_id)
        
        # Удалить отключенные соединения
        for user_id in disconnected:
            self.disconnect(user_id)
    
    async def broadcast_to_warehouse_operators(self, message: dict, warehouse_ids: List[str]):
        """Отправить сообщение операторам конкретных складов"""
        disconnected = []
        for user_id, connection in self.connections.items():
            if connection["role"] == "warehouse_operator":
                # Проверить, есть ли пересечение складов
                operator_warehouses = set(connection["warehouse_ids"])
                target_warehouses = set(warehouse_ids)
                
                if operator_warehouses.intersection(target_warehouses):
                    try:
                        await connection["websocket"].send_text(json.dumps(message))
                    except Exception as e:
                        print(f"❌ Error broadcasting to operator {user_id}: {e}")
                        disconnected.append(user_id)
        
        # Удалить отключенные соединения
        for user_id in disconnected:
            self.disconnect(user_id)
    
    async def broadcast_courier_location_update(self, location_data: dict):
        """Отправить обновление местоположения курьера всем заинтересованным клиентам"""
        courier_id = location_data.get("courier_id")
        
        # Получить информацию о курьере для определения склада
        courier = db.couriers.find_one({"id": courier_id}, {"_id": 0, "assigned_warehouse_id": 1})
        warehouse_id = courier.get("assigned_warehouse_id") if courier else None
        
        message = {
            "type": "courier_location_update",
            "data": location_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Отправить всем админам
        await self.broadcast_to_admins(message)
        
        # Отправить операторам соответствующего склада
        if warehouse_id:
            await self.broadcast_to_warehouse_operators(message, [warehouse_id])
    
    def get_connection_stats(self):
        """Получить статистику подключений"""
        stats = {
            "total_connections": len(self.connections),
            "admin_connections": len([c for c in self.connections.values() if c["role"] == "admin"]),
            "operator_connections": len([c for c in self.connections.values() if c["role"] == "warehouse_operator"]),
            "active_users": list(self.connections.keys())
        }
        return stats

# Глобальный менеджер подключений
connection_manager = ConnectionManager()

# Utility functions for MongoDB ObjectId serialization
def serialize_mongo_document(document):
    """Converts ObjectId in a MongoDB document to strings recursively."""
    if isinstance(document, list):
        return [serialize_mongo_document(doc) for doc in document]
    
    if isinstance(document, dict):
        serialized = {}
        for key, value in document.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, (dict, list)):
                serialized[key] = serialize_mongo_document(value)
            else:
                serialized[key] = value
        return serialized
    
    return document

def escape_regex_special_chars(text):
    """Escape special regex characters for safe MongoDB regex queries."""
    # Escape all regex special characters
    special_chars = r'\.^$*+?{}[]|()'
    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, '\\' + char)
    return escaped_text

# Класс для пагинации
class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 25  # По умолчанию 25 элементов на странице
    
    @validator('page')
    def validate_page(cls, v):
        return max(1, v)  # Минимум 1 страница
    
    @validator('per_page')
    def validate_per_page(cls, v):
        return min(max(5, v), 100)  # От 5 до 100 элементов на страницу

class PaginationResponse(BaseModel):
    items: List[Any]
    total_count: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int] = None
    prev_page: Optional[int] = None

def create_pagination_response(items: List[Any], total_count: int, page: int, per_page: int) -> Dict:
    """Создать ответ с пагинацией"""
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "items": items,
        "pagination": {
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "next_page": page + 1 if has_next else None,
            "prev_page": page - 1 if has_prev else None
        }
    }

def apply_pagination(query_result, page: int = 1, per_page: int = 25):
    """Применить пагинацию к результату запроса MongoDB"""
    skip = (page - 1) * per_page
    total_count = query_result.count() if hasattr(query_result, 'count') else len(query_result)
    
    if hasattr(query_result, 'skip'):
        # Для MongoDB cursor
        items = list(query_result.skip(skip).limit(per_page))
    else:
        # Для обычного списка
        items = query_result[skip:skip + per_page]
    
    return create_pagination_response(items, total_count, page, per_page)

# Enums
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin" 
    WAREHOUSE_OPERATOR = "warehouse_operator"
    COURIER = "courier"

class CargoStatus(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    AWAITING_PAYMENT = "awaiting_payment"  # Ожидает оплаты
    PAID = "paid"  # Оплачен
    INVOICE_PRINTED = "invoice_printed"  # Накладная напечатана
    AWAITING_PLACEMENT = "awaiting_placement"  # Ожидает размещения
    PLACEMENT_READY = "placement_ready"  # ДОБАВЛЕНО: Готов к размещению
    IN_WAREHOUSE = "in_warehouse"
    PLACED_IN_WAREHOUSE = "placed_in_warehouse"  # Размещен на складе
    PICKUP_REQUESTED = "pickup_requested"  # Заявка на забор груза
    ASSIGNED_TO_COURIER = "assigned_to_courier"  # Назначен курьеру
    PICKED_UP_BY_COURIER = "picked_up_by_courier"  # Забран курьером
    COURIER_DELIVERED_TO_WAREHOUSE = "courier_delivered_to_warehouse"  # Курьер сдал груз на склад
    IN_TRANSIT = "in_transit"
    ARRIVED_DESTINATION = "arrived_destination"
    COMPLETED = "completed"
    REMOVED_FROM_PLACEMENT = "removed_from_placement"  # ДОБАВЛЕНО: Удален из размещения

class RouteType(str, Enum):
    MOSCOW_TO_TAJIKISTAN = "moscow_to_tajikistan"
    TAJIKISTAN_TO_MOSCOW = "tajikistan_to_moscow"
    MOSCOW_DUSHANBE = "moscow_dushanbe"
    MOSCOW_KHUJAND = "moscow_khujand"
    MOSCOW_KULOB = "moscow_kulob"
    MOSCOW_KURGANTYUBE = "moscow_kurgantyube"

class PaymentMethod(str, Enum):
    NOT_PAID = "not_paid"  # Не оплачено
    CASH = "cash"  # Оплата наличными
    CARD_TRANSFER = "card_transfer"  # Перевод на карту
    CASH_ON_DELIVERY = "cash_on_delivery"  # Оплата при получении
    CREDIT = "credit"  # Оплата в долг

class DeliveryMethod(str, Enum):
    PICKUP = "pickup"  # Самовывоз
    HOME_DELIVERY = "home_delivery"  # Доставка до дома

class TransportType(str, Enum):
    CAR = "car"  # Легковой автомобиль
    VAN = "van"  # Фургон
    TRUCK = "truck"  # Грузовик
    MOTORCYCLE = "motorcycle"  # Мотоцикл
    BICYCLE = "bicycle"  # Велосипед
    ON_FOOT = "on_foot"  # Пешком

class TransportStatus(str, Enum):
    EMPTY = "empty"
    FILLED = "filled"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    COMPLETED = "completed"

class CourierStatus(str, Enum):
    OFFLINE = "offline"  # Не в сети / отслеживание выключено
    ONLINE = "online"    # В сети, свободен
    ON_ROUTE = "on_route"  # Едет к клиенту
    AT_PICKUP = "at_pickup"  # На месте забора груза
    AT_DELIVERY = "at_delivery"  # На месте доставки
    BUSY = "busy"  # Занят другими делами

# Pydantic модели
class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=10)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.USER

class UserLogin(BaseModel):
    phone: str
    password: str

class User(BaseModel):
    id: str
    user_number: Optional[str] = None  # Делаем опциональным для обратной совместимости
    full_name: str
    phone: str
    role: UserRole
    email: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True
    token_version: int = 1  # Добавляем версионирование токенов
    created_at: datetime

class CourierCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=6, max_length=50)
    address: str = Field(..., min_length=5, max_length=200)
    transport_type: TransportType
    transport_number: str = Field(..., min_length=1, max_length=50)
    transport_capacity: float = Field(..., gt=0, le=10000, description="Грузоподъемность в кг")
    assigned_warehouse_id: str = Field(..., description="ID склада, к которому привязан курьер")

class Courier(BaseModel):
    id: str
    user_id: str  # Ссылка на пользователя
    full_name: str
    phone: str
    address: str
    transport_type: TransportType
    transport_number: str
    transport_capacity: float
    assigned_warehouse_id: str
    assigned_warehouse_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

# Модель для GPS местоположения курьера
class CourierLocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Широта (от -90 до 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Долгота (от -180 до 180)")
    status: CourierStatus = CourierStatus.ONLINE
    current_address: Optional[str] = None
    accuracy: Optional[float] = None  # Точность GPS в метрах
    speed: Optional[float] = None  # Скорость в км/ч
    heading: Optional[float] = None  # Направление движения в градусах

class CourierLocation(BaseModel):
    id: str
    courier_id: str
    courier_name: str
    courier_phone: str
    transport_type: TransportType
    latitude: float
    longitude: float
    status: CourierStatus
    current_address: Optional[str] = None
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    current_request_id: Optional[str] = None  # ID текущей заявки
    current_request_address: Optional[str] = None  # Адрес текущей заявки
    last_updated: datetime
    created_at: datetime
# Модель для обновления роли пользователя
class UserRoleUpdate(BaseModel):
    user_id: str = Field(..., min_length=1)
    new_role: UserRole

# Модель для ответа личного кабинета
class PersonalDashboard(BaseModel):
    user_info: User
    cargo_requests: List[dict] = []  # Заявки на грузы (как отправитель)
    received_cargo: List[dict] = []  # Полученные грузы (как получатель)
    sent_cargo: List[dict] = []     # Отправленные грузы


class AdvancedSearchRequest(BaseModel):
    query: Optional[str] = None  # Основной поисковый запрос
    search_type: str = "all"  # all, cargo, users, warehouses
    
    # Фильтры для грузов
    cargo_status: Optional[str] = None  # accepted, in_transit, delivered, etc.
    payment_status: Optional[str] = None  # pending, paid
    processing_status: Optional[str] = None  # payment_pending, paid, ready_for_placement
    route: Optional[str] = None  # moscow_to_tajikistan, tajikistan_to_moscow
    sender_phone: Optional[str] = None
    recipient_phone: Optional[str] = None
    
    # Фильтры по дате
    date_from: Optional[str] = None  # ISO format date
    date_to: Optional[str] = None
    
    # Фильтры для пользователей
    user_role: Optional[str] = None  # user, admin, warehouse_operator
    user_status: Optional[bool] = None  # active/inactive
    
    # Параметры сортировки и пагинации
    sort_by: Optional[str] = "created_at"  # created_at, weight, declared_value
    sort_order: Optional[str] = "desc"  # asc, desc
    page: Optional[int] = 1
    per_page: Optional[int] = 20
    
class SearchResult(BaseModel):
    type: str  # cargo, user, warehouse
    id: str
    title: str  # Основное название/заголовок
    subtitle: str  # Дополнительная информация
    details: dict  # Детальная информация
    relevance_score: Optional[float] = None  # Оценка релевантности
    
class AdvancedSearchResponse(BaseModel):
    results: List[SearchResult]
    total_count: int
    page: int
    per_page: int
    total_pages: int
    search_time_ms: int
    suggestions: List[str] = []  # Предложения для автодополнения

class CargoCreate(BaseModel):
    recipient_name: str
    recipient_phone: str
    route: RouteType
    weight: float
    cargo_name: Optional[str] = Field(None, max_length=100)  # Наименование груза (опционально)
    description: str
    declared_value: float
    sender_address: str
    recipient_address: str

class Cargo(BaseModel):
    id: str
    cargo_number: str
    sender_id: str
    recipient_name: str
    recipient_phone: str
    route: RouteType
    weight: float
    cargo_name: Optional[str]  # Наименование груза (опционально)
    description: str
    declared_value: float
    sender_address: str
    recipient_address: str
    status: CargoStatus
    created_at: datetime
    updated_at: datetime
    warehouse_location: Optional[str] = None
    accepted_by_operator: Optional[str] = None  # ФИО оператора, принявшего груз
    accepted_by_operator_id: Optional[str] = None  # ID оператора
    placed_by_operator: Optional[str] = None  # ФИО оператора, разместившего груз
    placed_by_operator_id: Optional[str] = None  # ID оператора

class TransportCreate(BaseModel):
    driver_name: str = Field(..., min_length=2)
    driver_phone: str = Field(..., min_length=10)
    transport_number: str = Field(..., min_length=3)
    capacity_kg: float = Field(..., gt=0)
    direction: str = Field(..., min_length=3)

class Transport(BaseModel):
    id: str
    transport_number: str
    driver_name: str
    driver_phone: str
    capacity_kg: float
    direction: str
    status: TransportStatus
    current_load_kg: float = 0.0
    cargo_list: List[str] = []  # List of cargo IDs
    created_at: datetime
    updated_at: datetime
    dispatched_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class TransportCargoPlacement(BaseModel):
    transport_id: str
    cargo_ids: List[str]

class TransportCargoPlacementByNumbers(BaseModel):
    transport_id: str
    cargo_numbers: List[str]  # Номера грузов вместо ID

class OperatorWarehouseBinding(BaseModel):
    id: str
    operator_id: str
    operator_name: str
    operator_phone: str
    warehouse_id: str
    warehouse_name: str
    created_at: datetime
    created_by: str  # Admin who created the binding

class OperatorWarehouseBindingCreate(BaseModel):
    operator_id: str
    warehouse_id: str

class NotificationCreate(BaseModel):
    user_id: str
    message: str
    cargo_id: Optional[str] = None

class Notification(BaseModel):
    id: str
    user_id: str
    message: str
    cargo_id: Optional[str] = None
    is_read: bool = False
    created_at: datetime

class WarehouseCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    location: str = Field(..., min_length=5, max_length=200)  # Город/регион
    address: Optional[str] = Field(None, max_length=500)  # НОВОЕ: Полный адрес для навигации
    blocks_count: int = Field(..., ge=1, le=9)
    shelves_per_block: int = Field(..., ge=1, le=3)
    cells_per_shelf: int = Field(..., ge=1, le=50)

class Warehouse(BaseModel):
    id: str
    warehouse_id_number: str  # Автогенерируемый ID номер склада (001, 002, 003...)
    name: str
    location: str  # Город/регион
    address: Optional[str] = None  # НОВОЕ: Полный адрес
    blocks_count: int
    shelves_per_block: int
    cells_per_shelf: int
    total_capacity: int
    created_by: str
    created_at: datetime
    is_active: bool = True

class WarehouseBlock(BaseModel):
    id: str
    warehouse_id: str
    warehouse_id_number: str  # ID номер склада
    block_id_number: str  # Автогенерируемый ID номер блока (01, 02, 03...)
    block_number: int  # Номер блока (сохраняем для совместимости)
    shelves: List[dict]  # List of shelves with cells

class WarehouseShelf(BaseModel):
    id: str
    warehouse_id: str
    warehouse_id_number: str  # ID номер склада
    block_id_number: str  # ID номер блока
    shelf_id_number: str  # Автогенерируемый ID номер полки (01, 02, 03...)
    block_number: int
    shelf_number: int
    cells: List[dict]  # List of cells

class WarehouseCell(BaseModel):
    id: str
    warehouse_id: str
    warehouse_id_number: str  # ID номер склада
    block_id_number: str  # ID номер блока  
    shelf_id_number: str  # ID номер полки
    cell_id_number: str  # Автогенерируемый ID номер ячейки (001, 002, 003...)
    block_number: int
    shelf_number: int
    cell_number: int
    is_occupied: bool = False
    cargo_id: Optional[str] = None
    location_code: str  # Format: "B1-S2-C3" (Block 1, Shelf 2, Cell 3)
    id_based_code: str  # Новый формат: "001-01-01-001" (Склад-Блок-Полка-Ячейка)

# Модель для отдельного груза в заявке с индивидуальной ценой
class CargoItem(BaseModel):
    cargo_name: str = Field(..., min_length=1, max_length=100)
    weight: float = Field(..., gt=0, le=1000)
    price_per_kg: float = Field(..., gt=0, le=10000)  # Индивидуальная цена за кг для каждого груза
    
    @property
    def total_cost(self) -> float:
        """Общая стоимость этого груза"""
        return self.weight * self.price_per_kg

# Обновленная модель для создания груза оператором с поддержкой индивидуальных цен
class OperatorCargoCreate(BaseModel):
    sender_full_name: str = Field(..., min_length=2, max_length=100)
    sender_phone: str = Field(..., min_length=10, max_length=20)
    recipient_full_name: str = Field(..., min_length=2, max_length=100)
    recipient_phone: str = Field(..., min_length=10, max_length=20)
    recipient_address: str = Field(..., min_length=5, max_length=200)
    
    # Для совместимости с существующим кодом - если используется одиночная форма
    weight: Optional[float] = Field(None, gt=0, le=1000)
    cargo_name: Optional[str] = Field(None, max_length=100)
    declared_value: Optional[float] = Field(None, gt=0)  # Старое поле для совместимости
    
    # Новые поля для множественных грузов с индивидуальными ценами
    cargo_items: Optional[List[CargoItem]] = Field(None, min_items=1)  # Список грузов с индивидуальными ценами
    price_per_kg: Optional[float] = Field(None, gt=0)  # Общая цена за кг (для совместимости)
    
    description: str = Field(..., min_length=1, max_length=500)
    route: RouteType = RouteType.MOSCOW_TO_TAJIKISTAN
    
    # НОВЫЕ ПОЛЯ ДЛЯ УЛУЧШЕННОЙ СИСТЕМЫ ОПЛАТЫ
    warehouse_id: Optional[str] = Field(None, description="Выбранный склад оператора")
    payment_method: PaymentMethod = PaymentMethod.NOT_PAID  # Способ оплаты
    payment_amount: Optional[float] = Field(None, gt=0, description="Сумма оплаты для наличных/карты")
    debt_due_date: Optional[str] = Field(None, description="Дата погашения долга (YYYY-MM-DD)")  # Для оплаты в долг
    
    # НОВЫЕ ПОЛЯ ДЛЯ КУРЬЕРСКОЙ СЛУЖБЫ
    pickup_required: bool = Field(default=False, description="Требуется забор груза")
    pickup_address: Optional[str] = Field(None, max_length=200, description="Адрес забора груза")
    pickup_date: Optional[str] = Field(None, description="Дата забора (YYYY-MM-DD)")
    pickup_time_from: Optional[str] = Field(None, description="Время забора с (HH:MM)")
    pickup_time_to: Optional[str] = Field(None, description="Время забора до (HH:MM)")
    delivery_method: DeliveryMethod = Field(default=DeliveryMethod.PICKUP, description="Способ получения груза")
    courier_fee: Optional[float] = Field(None, ge=0, description="Стоимость курьерских услуг")
    
    # Computed fields
    @property
    def total_weight(self) -> float:
        """Общий вес всех грузов"""
        if self.cargo_items:
            return sum(item.weight for item in self.cargo_items)
        return self.weight or 0.0
    
    @property
    def total_cost(self) -> float:
        """Общая стоимость всех грузов"""
        if self.cargo_items:
            # Используем индивидуальные цены для каждого груза
            return sum(item.total_cost for item in self.cargo_items)
        # Для совместимости со старой схемой
        if self.declared_value:
            return self.declared_value
        if self.weight and self.price_per_kg:
            return self.weight * self.price_per_kg
        return 0.0
    
    @property
    def declared_value_computed(self) -> float:
        """Для совместимости - возвращает общую стоимость"""
        return self.total_cost

# Модели для расширенного управления пользователями
class OperatorProfile(BaseModel):
    user_info: User
    work_statistics: dict
    cargo_history: List[dict] = []
    associated_warehouses: List[dict] = []
    recent_activity: List[dict] = []

class UserProfile(BaseModel):
    user_info: User
    shipping_statistics: dict
    recent_shipments: List[dict] = []
    frequent_recipients: List[dict] = []
    cargo_requests_history: List[dict] = []

class QuickCargoRequest(BaseModel):
    sender_id: str  # ID пользователя-отправителя
    recipient_data: dict  # Данные получателя из истории или новые
    cargo_items: List[CargoItem]  # Используем существующую модель
    route: RouteType = RouteType.MOSCOW_TO_TAJIKISTAN
    description: str

class CargoPlacement(BaseModel):
    cargo_id: str
    warehouse_id: str
    block_number: int
    shelf_number: int
    cell_number: int

class CargoPlacementAuto(BaseModel):
    cargo_id: str
    block_number: int
    shelf_number: int  
    cell_number: int
    # warehouse_id will be determined automatically from operator binding

class CargoWithLocation(BaseModel):
    id: str
    cargo_number: str
    sender_full_name: str
    sender_phone: str
    recipient_full_name: str
    recipient_phone: str
    recipient_address: str
    weight: float
    cargo_name: Optional[str]  # Наименование груза (опционально)
    declared_value: float
    description: str
    route: RouteType
    status: CargoStatus
    payment_status: str = "pending"  # pending, paid, failed
    processing_status: str = "received"  # received, payment_pending, paid, invoice_printed, placed
    created_at: datetime
    updated_at: datetime
    created_by: str  # ID оператора, который принял груз
    created_by_operator: Optional[str] = None  # ФИО оператора, который принял груз
    target_warehouse_id: Optional[str] = None  # Целевой склад для размещения
    target_warehouse_name: Optional[str] = None  # Название целевого склада
    warehouse_location: Optional[str] = None
    warehouse_id: Optional[str] = None
    block_number: Optional[int] = None
    shelf_number: Optional[int] = None
    cell_number: Optional[int] = None
    placed_by_operator: Optional[str] = None  # ФИО оператора, разместившего груз
    placed_by_operator_id: Optional[str] = None  # ID оператора

class PaymentTransaction(BaseModel):
    id: str
    cargo_id: str
    cargo_number: str
    amount_due: float
    amount_paid: float
    payment_date: datetime
    processed_by: str  # ID кассира
    customer_name: str
    customer_phone: str
    transaction_type: str = "cash"  # cash, card, transfer
    notes: Optional[str] = None

class PaymentCreate(BaseModel):
    cargo_number: str
    amount_paid: float
    transaction_type: str = "cash"
    notes: Optional[str] = None

class CargoRequest(BaseModel):
    id: str
    request_number: str
    sender_full_name: str
    sender_phone: str
    recipient_full_name: str
    recipient_phone: str
    recipient_address: str
    pickup_address: str
    cargo_name: str
    weight: float
    declared_value: float
    description: str
    route: RouteType
    status: str = "pending"  # pending, accepted, rejected
    admin_notes: Optional[str] = None  # Заметки администратора
    created_at: datetime
    updated_at: datetime
    created_by: str  # ID пользователя
    processed_by: Optional[str] = None  # ID оператора, который обработал

class CargoRequestCreate(BaseModel):
    recipient_full_name: str = Field(..., min_length=2, max_length=100)
    recipient_phone: str = Field(..., min_length=10, max_length=20)
    recipient_address: str = Field(..., min_length=5, max_length=200)
    pickup_address: str = Field(..., min_length=5, max_length=200)
    cargo_name: str = Field(..., min_length=2, max_length=100)
    weight: float = Field(..., gt=0, le=1000)
    declared_value: float = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    route: RouteType = RouteType.MOSCOW_TO_TAJIKISTAN

class CargoRequestUpdate(BaseModel):
    """Модель для обновления информации заказа администратором или оператором"""
    sender_full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    sender_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    recipient_full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    recipient_phone: Optional[str] = Field(None, min_length=10, max_length=20)
    recipient_address: Optional[str] = Field(None, min_length=5, max_length=200)
    pickup_address: Optional[str] = Field(None, min_length=5, max_length=200)
    cargo_name: Optional[str] = Field(None, min_length=2, max_length=100)
    weight: Optional[float] = Field(None, gt=0, le=1000)
    declared_value: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    route: Optional[RouteType] = None
    admin_notes: Optional[str] = Field(None, max_length=500)  # Заметки администратора

class SystemNotification(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    related_id: Optional[str] = None
    related_data: Optional[dict] = None
    created_by: Optional[str] = None
    created_at: datetime
    is_read: bool = False

# === НОВЫЕ МОДЕЛИ ДЛЯ ЭТАПА 1 ===

# МОДЕЛЬ ДЛЯ МАССОВОГО УДАЛЕНИЯ ГРУЗОВ
class BulkDeleteRequest(BaseModel):
    ids: List[str] = Field(..., min_items=1, max_items=100, description="Список ID для удаления (от 1 до 100 элементов)")

# Модели для фото груза
class CargoPhoto(BaseModel):
    id: str
    cargo_id: str
    cargo_number: str
    photo_data: str  # base64 encoded image
    photo_name: str
    photo_size: int  # размер в байтах
    uploaded_by: str  # ID пользователя
    uploaded_by_name: str  # ФИО пользователя
    upload_date: datetime
    photo_type: str = "cargo_photo"  # cargo_photo, damage_photo, packaging_photo
    description: Optional[str] = None

class CargoPhotoUpload(BaseModel):
    cargo_id: str
    photo_data: str  # base64 encoded image  
    photo_name: str
    photo_type: str = "cargo_photo"
    description: Optional[str] = None

# Модель для неоплаченных заказов
class UnpaidOrder(BaseModel):
    id: str
    cargo_id: str
    cargo_number: str
    client_id: str
    client_name: str
    client_phone: str
    amount: float
    description: str
    status: str = "unpaid"  # unpaid, paid, cancelled
    created_at: datetime
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None  # cash, card, bank_transfer
    processed_by: Optional[str] = None  # ID администратора/оператора

# Модели для истории изменений груза
class CargoHistory(BaseModel):
    id: str
    cargo_id: str
    cargo_number: str
    action_type: str  # created, updated, moved, status_changed, placed_on_transport, etc
    field_name: Optional[str] = None  # какое поле изменено
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: str  # описание изменения
    changed_by: str  # ID пользователя 
    changed_by_name: str  # ФИО пользователя
    changed_by_role: str  # роль пользователя
    change_date: datetime
    additional_data: Optional[dict] = None

# Модели для комментариев к грузам
class CargoComment(BaseModel):
    id: str
    cargo_id: str
    cargo_number: str
    comment_text: str
    comment_type: str = "general"  # general, issue, note, instruction
    priority: str = "normal"  # low, normal, high, urgent
    is_internal: bool = False  # внутренний комментарий (не видим клиенту)
    author_id: str
    author_name: str
    author_role: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_resolved: bool = False  # для комментариев типа issue

class CargoCommentCreate(BaseModel):
    cargo_id: str
    comment_text: str = Field(..., min_length=1, max_length=1000)
    comment_type: str = "general"
    priority: str = "normal"
    is_internal: bool = False

# Модели для трекинга груза клиентами
class CargoTracking(BaseModel):
    id: str
    cargo_id: str
    cargo_number: str
    tracking_code: str  # уникальный код для клиента
    client_phone: str  # телефон клиента для доступа
    is_active: bool = True
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0

class CargoTrackingCreate(BaseModel):
    cargo_number: str
    client_phone: str

# Модели для уведомлений клиентам
class ClientNotification(BaseModel):
    id: str
    cargo_id: str
    cargo_number: str
    client_phone: str
    notification_type: str  # sms, email, whatsapp
    message_text: str
    status: str = "pending"  # pending, sent, delivered, failed
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_by: str
    created_at: datetime

class ClientNotificationCreate(BaseModel):
    cargo_id: str
    client_phone: str
    notification_type: str
    message_text: str = Field(..., min_length=1, max_length=500)

# Модели для внутренних сообщений операторов
class InternalMessage(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    recipient_id: str
    recipient_name: str
    message_subject: str
    message_text: str
    priority: str = "normal"  # low, normal, high, urgent
    related_cargo_id: Optional[str] = None
    related_cargo_number: Optional[str] = None
    is_read: bool = False
    sent_at: datetime
    read_at: Optional[datetime] = None

class InternalMessageCreate(BaseModel):
    recipient_id: str
    message_subject: str = Field(..., min_length=1, max_length=200)
    message_text: str = Field(..., min_length=1, max_length=2000)
    priority: str = "normal"
    related_cargo_id: Optional[str] = None

# Модели для создания операторов админом
class OperatorCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    address: str = Field(..., min_length=5, max_length=200)  # Адрес проживания
    password: str = Field(..., min_length=6, max_length=50)
    warehouse_id: str  # Склад для назначения

class OperatorResponse(BaseModel):
    id: str
    full_name: str
    phone: str
    address: str
    role: str
    warehouse_id: str
    warehouse_name: str
    is_active: bool
    created_at: datetime
    created_by: str

# Модели для оформления груза клиентами
class CargoOrderCreate(BaseModel):
    # Основная информация о грузе
    cargo_name: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=5, max_length=500)
    weight: float = Field(..., gt=0, le=10000)  # Максимум 10 тонн
    declared_value: float = Field(..., gt=0, le=10000000)  # Максимум 10 млн
    
    # Информация о получателе
    recipient_full_name: str = Field(..., min_length=2, max_length=100)
    recipient_phone: str = Field(..., min_length=10, max_length=20)
    recipient_address: str = Field(..., min_length=5, max_length=200)
    recipient_city: str = Field(..., min_length=2, max_length=50)
    
    # Маршрут и услуги
    route: RouteType = RouteType.MOSCOW_DUSHANBE
    delivery_type: str = "standard"  # standard, express, economy
    
    # Дополнительные услуги
    insurance_requested: bool = False
    insurance_value: Optional[float] = None
    packaging_service: bool = False
    home_pickup: bool = False
    home_delivery: bool = False
    
    # Специальные требования
    fragile: bool = False
    temperature_sensitive: bool = False
    special_instructions: Optional[str] = None

class CourierRequest(BaseModel):
    id: str
    cargo_id: Optional[str] = None  # ID груза (если уже создан)
    sender_full_name: str
    sender_phone: str
    cargo_name: str
    pickup_address: str
    pickup_date: str  # YYYY-MM-DD
    pickup_time_from: str  # HH:MM
    pickup_time_to: str  # HH:MM
    delivery_method: DeliveryMethod
    courier_fee: Optional[float] = None
    assigned_courier_id: Optional[str] = None
    assigned_courier_name: Optional[str] = None
    request_status: str = "pending"  # pending, assigned, accepted, completed, cancelled
    created_by: str  # ID оператора
    created_at: datetime
    updated_at: datetime

class CourierRequestUpdate(BaseModel):
    request_status: str = Field(..., pattern="^(pending|assigned|accepted|completed|cancelled)$")
    courier_notes: Optional[str] = None

class DeliveryCalculation(BaseModel):
    base_cost: float
    weight_cost: float
    insurance_cost: float
    packaging_cost: float
    pickup_cost: float
    delivery_cost: float
    express_surcharge: float
    total_cost: float
    delivery_time_days: int
    currency: str = "RUB"

class CargoOrderResponse(BaseModel):
    cargo_id: str
    cargo_number: str
    total_cost: float
    estimated_delivery_days: int
    status: str
    payment_status: str
    tracking_code: Optional[str] = None
    created_at: datetime

class BulkRemoveFromPlacementRequest(BaseModel):
    cargo_ids: List[str] = Field(..., min_items=1, max_items=100, description="Список ID грузов для удаления (максимум 100)")

# Утилиты
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_user_token(user_id: str, phone: str, token_version: int = 1, expires_delta: Optional[timedelta] = None):
    """Создает токен с информацией о пользователе включая версию токена"""
    token_data = {
        "sub": phone,
        "user_id": user_id,
        "token_version": token_version
    }
    return create_access_token(token_data, expires_delta)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        token_version: int = payload.get("token_version", 1)
        if phone is None or user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db.users.find_one({"phone": phone, "id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Проверяем версию токена
    current_token_version = user.get("token_version", 1)
    if token_version != current_token_version:
        raise HTTPException(
            status_code=401, 
            detail="Token expired due to profile changes. Please log in again."
        )
    
    if not user["is_active"]:
        raise HTTPException(status_code=401, detail="User is inactive")
    
    # Генерируем user_number если его нет
    user_number = user.get("user_number")
    if not user_number:
        user_number = generate_user_number()
        db.users.update_one(
            {"id": user["id"]},
            {"$set": {"user_number": user_number}}
        )
        user["user_number"] = user_number
        
    return User(
        id=user["id"],
        user_number=user_number,
        full_name=user["full_name"],
        phone=user["phone"],
        role=user["role"],
        email=user.get("email"),
        address=user.get("address"),
        is_active=user["is_active"],
        token_version=user.get("token_version", 1),
        created_at=user["created_at"]
    )

def require_role(role: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != role and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

def generate_cargo_number() -> str:
    """Генерируем индивидуальный номер груза от 4-значных до 10-значных цифр"""
    try:
        import random
        
        # ФИКСИРОВАННЫЙ ФОРМАТ для января 2025: используем 2501 как префикс
        year_month = "2501"  # Январь 2025
        
        # Ищем последний груз с номерами, начинающимися на 2501
        pattern = f"^{year_month}[0-9]{{2,6}}$"  # 2501XX до 2501XXXXXX
        
        last_cargo_user = db.cargo.find({
            "cargo_number": {"$regex": pattern}
        }).sort("cargo_number", -1).limit(1)
        
        last_cargo_operator = db.operator_cargo.find({
            "cargo_number": {"$regex": pattern}
        }).sort("cargo_number", -1).limit(1)
        
        last_cargo_user_list = list(last_cargo_user)
        last_cargo_operator_list = list(last_cargo_operator)
        
        # Находим максимальный номер для префикса 2501
        max_number = 0
        
        if last_cargo_user_list:
            user_number_str = last_cargo_user_list[0]["cargo_number"]
            if len(user_number_str) > 4:
                user_sequence = int(user_number_str[4:])  # Убираем префикс 2501
                max_number = max(max_number, user_sequence)
                
        if last_cargo_operator_list:
            operator_number_str = last_cargo_operator_list[0]["cargo_number"]
            if len(operator_number_str) > 4:
                operator_sequence = int(operator_number_str[4:])  # Убираем префикс 2501
                max_number = max(max_number, operator_sequence)
        
        # Следующий номер в последовательности
        next_sequence = max_number + 1
        
        # Формируем полный номер груза (от 4 до 10 цифр общих)
        if next_sequence <= 99:
            # 6-значный номер: 2501XX (01-99)
            cargo_number = f"{year_month}{next_sequence:02d}"
        elif next_sequence <= 999:
            # 7-значный номер: 2501XXX (100-999)  
            cargo_number = f"{year_month}{next_sequence:03d}"
        elif next_sequence <= 9999:
            # 8-значный номер: 2501XXXX (1000-9999)
            cargo_number = f"{year_month}{next_sequence:04d}"
        elif next_sequence <= 99999:
            # 9-значный номер: 2501XXXXX (10000-99999)
            cargo_number = f"{year_month}{next_sequence:05d}"
        else:
            # 10-значный номер: 2501XXXXXX (100000-999999)
            cargo_number = f"{year_month}{next_sequence:06d}"
            
        # Максимум 10 цифр общих, значит максимум 6 цифр после 2501
        if next_sequence > 999999:
            # Если превысили лимит, используем случайный номер
            cargo_number = f"{year_month}{random.randint(100000, 999999):06d}"
        
        # Проверяем уникальность номера в обеих коллекциях
        attempts = 0
        while (db.cargo.find_one({"cargo_number": cargo_number}) or 
               db.operator_cargo.find_one({"cargo_number": cargo_number})) and attempts < 100:
            # Генерируем случайный номер если найден дубликат
            random_suffix = random.randint(1000, 999999)
            cargo_number = f"{year_month}{random_suffix:06d}"
            attempts += 1
        
        return cargo_number
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер для января 2025
        import random
        year_month = "2501"
        random_suffix = random.randint(1000, 9999)
        return f"{year_month}{random_suffix:04d}"

def generate_user_number() -> str:
    """Генерируем индивидуальный номер пользователя формата USR001234"""
    try:
        # Ищем последний пользователь с номером для определения следующего номера
        last_user = db.users.find_one(
            {"user_number": {"$regex": "^USR[0-9]{6}$"}},
            sort=[("user_number", -1)]
        )
        
        if last_user and "user_number" in last_user:
            # Извлекаем числовую часть и увеличиваем на 1
            last_number = int(last_user["user_number"][3:])  # Убираем префикс USR
            next_number = last_number + 1
        else:
            # Начинаем с номера 1
            next_number = 1
        
        # Формируем номер пользователя с префиксом USR и 6 цифрами
        user_number = f"USR{next_number:06d}"
        
        # Проверяем уникальность номера
        attempts = 0
        while db.users.find_one({"user_number": user_number}) and attempts < 100:
            next_number += 1
            user_number = f"USR{next_number:06d}"
            attempts += 1
        
        return user_number
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер
        import random
        return f"USR{random.randint(1, 999999):06d}"

def generate_warehouse_id_number() -> str:
    """Генерируем ID номер склада формата 001, 002, 003..."""
    try:
        # Ищем последний склад с ID номером для определения следующего номера
        last_warehouse = db.warehouses.find_one(
            {"warehouse_id_number": {"$regex": "^[0-9]{3}$"}},
            sort=[("warehouse_id_number", -1)]
        )
        
        if last_warehouse and "warehouse_id_number" in last_warehouse:
            # Извлекаем числовую часть и увеличиваем на 1
            last_number = int(last_warehouse["warehouse_id_number"])
            next_number = last_number + 1
        else:
            # Начинаем с номера 1
            next_number = 1
        
        # Формируем номер склада с 3 цифрами
        warehouse_id_number = f"{next_number:03d}"
        
        # Проверяем уникальность номера
        attempts = 0
        while db.warehouses.find_one({"warehouse_id_number": warehouse_id_number}) and attempts < 100:
            next_number += 1
            warehouse_id_number = f"{next_number:03d}"
            attempts += 1
        
        return warehouse_id_number
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер
        import random
        return f"{random.randint(1, 999):03d}"

def generate_block_id_number(warehouse_id_number: str) -> str:
    """Генерируем ID номер блока формата 01, 02, 03... внутри склада"""
    try:
        # Ищем последний блок с ID номером в данном складе
        last_block = db.warehouse_blocks.find_one(
            {
                "warehouse_id_number": warehouse_id_number,
                "block_id_number": {"$regex": "^[0-9]{2}$"}
            },
            sort=[("block_id_number", -1)]
        )
        
        if last_block and "block_id_number" in last_block:
            # Извлекаем числовую часть и увеличиваем на 1
            last_number = int(last_block["block_id_number"])
            next_number = last_number + 1
        else:
            # Начинаем с номера 1
            next_number = 1
        
        # Формируем номер блока с 2 цифрами
        block_id_number = f"{next_number:02d}"
        
        # Проверяем уникальность номера в рамках склада
        attempts = 0
        while db.warehouse_blocks.find_one({
            "warehouse_id_number": warehouse_id_number,
            "block_id_number": block_id_number
        }) and attempts < 100:
            next_number += 1
            block_id_number = f"{next_number:02d}"
            attempts += 1
        
        return block_id_number
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер
        import random
        return f"{random.randint(1, 99):02d}"

def generate_shelf_id_number(warehouse_id_number: str, block_id_number: str) -> str:
    """Генерируем ID номер полки формата 01, 02, 03... внутри блока"""
    try:
        # Ищем последнюю полку с ID номером в данном блоке
        last_shelf = db.warehouse_shelves.find_one(
            {
                "warehouse_id_number": warehouse_id_number,
                "block_id_number": block_id_number,
                "shelf_id_number": {"$regex": "^[0-9]{2}$"}
            },
            sort=[("shelf_id_number", -1)]
        )
        
        if last_shelf and "shelf_id_number" in last_shelf:
            # Извлекаем числовую часть и увеличиваем на 1
            last_number = int(last_shelf["shelf_id_number"])
            next_number = last_number + 1
        else:
            # Начинаем с номера 1
            next_number = 1
        
        # Формируем номер полки с 2 цифрами
        shelf_id_number = f"{next_number:02d}"
        
        # Проверяем уникальность номера в рамках блока
        attempts = 0
        while db.warehouse_shelves.find_one({
            "warehouse_id_number": warehouse_id_number,
            "block_id_number": block_id_number,
            "shelf_id_number": shelf_id_number
        }) and attempts < 100:
            next_number += 1
            shelf_id_number = f"{next_number:02d}"
            attempts += 1
        
        return shelf_id_number
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер
        import random
        return f"{random.randint(1, 99):02d}"

def generate_cell_id_number(warehouse_id_number: str, block_id_number: str, shelf_id_number: str) -> str:
    """Генерируем ID номер ячейки формата 001, 002, 003... внутри полки"""
    try:
        # Ищем последнюю ячейку с ID номером в данной полке
        last_cell = db.warehouse_cells.find_one(
            {
                "warehouse_id_number": warehouse_id_number,
                "block_id_number": block_id_number,
                "shelf_id_number": shelf_id_number,
                "cell_id_number": {"$regex": "^[0-9]{3}$"}
            },
            sort=[("cell_id_number", -1)]
        )
        
        if last_cell and "cell_id_number" in last_cell:
            # Извлекаем числовую часть и увеличиваем на 1
            last_number = int(last_cell["cell_id_number"])
            next_number = last_number + 1
        else:
            # Начинаем с номера 1
            next_number = 1
        
        # Формируем номер ячейки с 3 цифрами
        cell_id_number = f"{next_number:03d}"
        
        # Проверяем уникальность номера в рамках полки
        attempts = 0
        while db.warehouse_cells.find_one({
            "warehouse_id_number": warehouse_id_number,
            "block_id_number": block_id_number,
            "shelf_id_number": shelf_id_number,
            "cell_id_number": cell_id_number
        }) and attempts < 100:
            next_number += 1
            cell_id_number = f"{next_number:03d}"
            attempts += 1
        
        return cell_id_number
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер
        import random
        return f"{random.randint(1, 999):03d}"

def generate_cargo_qr_code_data(cargo_data: dict) -> str:
    """Генерировать QR код для груза только с номером груза"""
    try:
        # Получаем только номер груза
        cargo_number = cargo_data.get("cargo_number", "")
        
        if not cargo_number:
            raise ValueError("Cargo number is required for QR code generation")
        
        # QR код содержит только номер груза
        qr_text = cargo_number
        
        # Генерируем QR код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Конвертируем в base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_data = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_data}"
        
    except Exception as e:
        print(f"Error generating QR code for cargo: {e}")
        return ""

def generate_warehouse_cell_qr_code(warehouse_data: dict, block: int, shelf: int, cell: int, use_id_format: bool = True) -> str:
    """Генерировать QR код для ячейки склада - использовать либо ID номера, либо старый формат"""
    try:
        if use_id_format:
            # Новый формат с ID номерами
            warehouse_id_number = warehouse_data.get('warehouse_id_number')
            
            # ИСПРАВЛЕНИЕ: Если у склада нет warehouse_id_number, генерируем его
            if not warehouse_id_number or not warehouse_id_number.isdigit() or len(warehouse_id_number) != 3:
                warehouse_id = warehouse_data.get('id', 'unknown')
                print(f"⚠️ Склад {warehouse_id} не имеет корректного warehouse_id_number: {warehouse_id_number}")
                
                # Генерируем новый уникальный номер
                warehouse_id_number = generate_warehouse_id_number()
                
                # Обновляем склад в базе данных
                try:
                    db.warehouses.update_one(
                        {"id": warehouse_id},
                        {"$set": {"warehouse_id_number": warehouse_id_number}}
                    )
                    print(f"✅ Склад {warehouse_id} обновлен с новым номером: {warehouse_id_number}")
                except Exception as update_error:
                    print(f"❌ Ошибка обновления номера склада: {update_error}")
                    # Используем номер по умолчанию в случае ошибки
                    warehouse_id_number = "999"
            
            # Формируем ID номера на основе позиций
            block_id = f"{block:02d}"
            shelf_id = f"{shelf:02d}"  
            cell_id = f"{cell:03d}"
            
            # QR код содержит уникальный ID номер склада: 001-01-01-001
            cell_code = f"{warehouse_id_number}-{block_id}-{shelf_id}-{cell_id}"
            
            print(f"🏗️ Генерируется QR код для склада #{warehouse_id_number}, ячейки: {cell_code}")
        else:
            # Старый формат для совместимости
            warehouse_id = warehouse_data.get('id', 'UNK')
            cell_code = f"{warehouse_id}-Б{block}-П{shelf}-Я{cell}"
        
        # QR код содержит только код ячейки
        qr_data = cell_code
        
        # Генерируем QR код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=3,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Конвертируем в base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_data = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_data}"
        
    except Exception as e:
        print(f"Error generating QR code for warehouse cell: {e}")
        return ""

def get_warehouses_by_route_for_notifications(route: str) -> list:
    """Определить склады по маршруту для отправки уведомлений"""
    route_lower = route.lower()
    warehouse_cities = []
    
    # Определяем города по маршрутам
    if "москва" in route_lower and "худжанд" in route_lower:
        warehouse_cities = ["москва", "худжанд"]
    elif "душанбе" in route_lower and "москва" in route_lower:
        warehouse_cities = ["душанбе", "москва"]
    elif "худжанд" in route_lower and "москва" in route_lower:
        warehouse_cities = ["худжанд", "москва"]
    elif "таджикистан" in route_lower and "москва" in route_lower:
        warehouse_cities = ["москва"]  # Для маршрута "Таджикистан-Москва" - только московский склад
    
    if not warehouse_cities:
        return []
    
    # Получаем ID складов по городам (поиск по location)
    warehouse_ids = []
    for city in warehouse_cities:
        warehouses = db.warehouses.find({
            "location": {"$regex": city, "$options": "i"},
            "is_active": True
        })
        warehouse_ids.extend([w["id"] for w in warehouses])
    
    return warehouse_ids

def get_operators_by_warehouses(warehouse_ids: list) -> list:
    """Получить операторов, привязанных к указанным складам"""
    if not warehouse_ids:
        return []
    
    # Находим привязки операторов к складам
    bindings = db.operator_warehouse_bindings.find({
        "warehouse_id": {"$in": warehouse_ids}
    })
    
    operator_ids = list(set([binding["operator_id"] for binding in bindings]))
    return operator_ids

def create_notification(user_id, message, related_id=None):
    """Создание уведомления"""
    notification_id = str(uuid.uuid4())
    notification = {
        "id": notification_id,
        "user_id": user_id,
        "message": message,
        "type": "system",
        "status": "unread",  # unread, read, deleted
        "created_at": datetime.utcnow(),
        "related_id": related_id
    }
    db.notifications.insert_one(notification)
    return notification_id

def create_route_based_notifications(message: str, route: str, related_id: str = None):
    """НОВАЯ ФУНКЦИЯ: Создание уведомлений по маршруту"""
    # Определяем склады по маршруту
    target_warehouse_ids = get_warehouses_by_route_for_notifications(route)
    
    if not target_warehouse_ids:
        # Если маршрут не определен, отправляем всем админам
        admins = db.users.find({"role": "admin", "is_active": True})
        for admin in admins:
            create_notification(admin["id"], message, related_id)
        return
    
    # Получаем операторов целевых складов
    target_operator_ids = get_operators_by_warehouses(target_warehouse_ids)
    
    # Отправляем уведомления операторам целевых складов
    for operator_id in target_operator_ids:
        create_notification(operator_id, message, related_id)
    
    # Также отправляем админам для контроля
    admins = db.users.find({"role": "admin", "is_active": True})
    for admin in admins:
        create_notification(admin["id"], message, related_id)

# Функция create_notification определена выше с расширенным функционалом

def create_system_notification(title: str, message: str, notification_type: str, related_id: str = None, user_id: str = None, created_by: str = None):
    """Создать системное уведомление"""
    notification = {
        "id": str(uuid.uuid4()),
        "title": title,
        "message": message,
        "notification_type": notification_type,
        "related_id": related_id,
        "user_id": user_id,
        "is_read": False,
        "created_at": datetime.utcnow(),
        "created_by": created_by or "system"
    }
    db.system_notifications.insert_one(notification)

def create_personal_notification(user_id: str, title: str, message: str, notification_type: str, related_id: str = None):
    """Создать персональное уведомление для пользователя"""
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "message": f"{title}: {message}",
        "cargo_id": related_id if notification_type == "cargo" else None,
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.notifications.insert_one(notification)

def get_operator_warehouse_ids(operator_id: str) -> list:
    """Получить список ID складов, привязанных к оператору"""
    bindings = list(db.operator_warehouse_bindings.find({"operator_id": operator_id}))
    return [b["warehouse_id"] for b in bindings]

def check_operator_warehouse_binding(operator_id: str, warehouse_id: str) -> bool:
    """Проверить, привязан ли оператор к складу"""
    binding = db.operator_warehouse_bindings.find_one({
        "operator_id": operator_id,
        "warehouse_id": warehouse_id
    })
    return binding is not None

def generate_request_number() -> str:
    """Генерировать номер заявки"""
    return f"REQ{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

def generate_courier_request_number() -> str:
    """Генерируем читаемый номер заявки курьера формата 100001, 100002, 100003..."""
    try:
        # Ищем последнюю заявку курьера с номером для определения следующего номера
        last_request = db.courier_requests.find_one(
            {"request_number": {"$regex": "^[0-9]{6}$"}},
            sort=[("request_number", -1)]
        )
        
        if last_request and last_request.get("request_number"):
            # Получаем следующий номер
            last_number = int(last_request["request_number"])
            new_number = last_number + 1
        else:
            # Начинаем с номера 100001
            new_number = 100001
        
        return f"{new_number:06d}"
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер начиная с 100001
        import random
        return f"{random.randint(100001, 999999):06d}"

def generate_pickup_request_number() -> str:
    """Генерируем читаемый номер заявки на забор груза формата 200001, 200002, 200003..."""
    try:
        # Ищем последнюю заявку на забор груза с номером для определения следующего номера
        last_request = db.courier_pickup_requests.find_one(
            {"request_number": {"$regex": "^[0-9]{6}$"}},
            sort=[("request_number", -1)]
        )
        
        if last_request and last_request.get("request_number"):
            # Получаем следующий номер
            last_number = int(last_request["request_number"])
            new_number = last_number + 1
        else:
            # Начинаем с номера 200001 для заявок на забор груза
            new_number = 200001
        
        return f"{new_number:06d}"
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер начиная с 200001
        import random
        return f"{random.randint(200001, 299999):06d}"

def generate_readable_request_number() -> str:
    """Генерируем читаемый номер заявки формата 100001, 100002, 100003..."""
    try:
        # Ищем последнюю заявку курьера с номером для определения следующего номера
        last_request = db.courier_requests.find_one(
            {"request_number": {"$regex": "^[0-9]{6}$"}},
            sort=[("request_number", -1)]
        )
        
        if last_request and last_request.get("request_number"):
            # Получаем следующий номер
            last_number = int(last_request["request_number"])
            new_number = last_number + 1
        else:
            # Начинаем с номера 100001
            new_number = 100001
        
        return f"{new_number:06d}"
        
    except Exception as e:
        # В случае ошибки, генерируем случайный номер начиная с 100001
        import random
        return f"{random.randint(100001, 999999):06d}"

def generate_warehouse_structure(warehouse_id: str, warehouse_id_number: str, blocks_count: int, shelves_per_block: int, cells_per_shelf: int):
    """Generate warehouse structure with blocks, shelves and cells using ID numbers"""
    cells = []
    blocks = []
    shelves = []
    
    for block in range(1, blocks_count + 1):
        # Генерируем ID номер блока
        block_id_number = f"{block:02d}"
        
        # Создаем блок
        block_data = {
            "id": str(uuid.uuid4()),
            "warehouse_id": warehouse_id,
            "warehouse_id_number": warehouse_id_number,
            "block_id_number": block_id_number,
            "block_number": block,
            "created_at": datetime.utcnow()
        }
        blocks.append(block_data)
        
        for shelf in range(1, shelves_per_block + 1):
            # Генерируем ID номер полки
            shelf_id_number = f"{shelf:02d}"
            
            # Создаем полку
            shelf_data = {
                "id": str(uuid.uuid4()),
                "warehouse_id": warehouse_id,
                "warehouse_id_number": warehouse_id_number,
                "block_id_number": block_id_number,
                "shelf_id_number": shelf_id_number,
                "block_number": block,
                "shelf_number": shelf,
                "created_at": datetime.utcnow()
            }
            shelves.append(shelf_data)
            
            for cell in range(1, cells_per_shelf + 1):
                # Генерируем ID номер ячейки
                cell_id_number = f"{cell:03d}"
                
                cell_data = {
                    "id": str(uuid.uuid4()),
                    "warehouse_id": warehouse_id,
                    "warehouse_id_number": warehouse_id_number,
                    "block_id_number": block_id_number,
                    "shelf_id_number": shelf_id_number,
                    "cell_id_number": cell_id_number,
                    "block_number": block,
                    "shelf_number": shelf,
                    "cell_number": cell,
                    "is_occupied": False,
                    "cargo_id": None,
                    "location_code": f"B{block}-S{shelf}-C{cell}",
                    "id_based_code": f"{warehouse_id_number}-{block_id_number}-{shelf_id_number}-{cell_id_number}",
                    "readable_name": f"Б{block}-П{shelf}-Я{cell}",  # Сохраняем читаемое имя для печати
                    "created_at": datetime.utcnow()
                }
                cells.append(cell_data)
    
    # Bulk insert all structures
    if blocks:
        db.warehouse_blocks.insert_many(blocks)
    if shelves:
        db.warehouse_shelves.insert_many(shelves)
    if cells:
        db.warehouse_cells.insert_many(cells)
    
    return len(cells)

def get_operator_warehouses(operator_id: str) -> List[str]:
    """Получить список складов, к которым привязан оператор"""
    bindings = list(db.operator_warehouse_bindings.find({"operator_id": operator_id}))
    return [binding["warehouse_id"] for binding in bindings]

def is_operator_allowed_for_warehouse(operator_id: str, warehouse_id: str) -> bool:
    """Проверить, имеет ли оператор доступ к складу"""
    binding = db.operator_warehouse_bindings.find_one({
        "operator_id": operator_id, 
        "warehouse_id": warehouse_id
    })
    return binding is not None

def get_operator_name_by_id(operator_id: str) -> str:
    """Получить ФИО оператора по ID"""
    user = db.users.find_one({"id": operator_id})
    return user["full_name"] if user else "Неизвестный оператор"

def get_available_cargo_for_transport(operator_id: str = None, user_role: str = None) -> List[dict]:
    """Получить доступные грузы для размещения на транспорт"""
    if user_role == UserRole.ADMIN:
        # Админы видят все грузы со всех складов
        cargo_query = {
            "status": {"$in": ["accepted", "arrived_destination"]},
            "warehouse_location": {"$exists": True, "$ne": None}
        }
    elif user_role == UserRole.WAREHOUSE_OPERATOR and operator_id:
        # Операторы видят только грузы со своих складов
        operator_warehouses = get_operator_warehouses(operator_id)
        if not operator_warehouses:
            return []
        
        cargo_query = {
            "status": {"$in": ["accepted", "arrived_destination"]},
            "warehouse_location": {"$exists": True, "$ne": None},
            "warehouse_id": {"$in": operator_warehouses}
        }
    else:
        return []
    
    # Ищем в обеих коллекциях, исключая MongoDB _id
    user_cargo = list(db.cargo.find(cargo_query, {"_id": 0}))
    operator_cargo = list(db.operator_cargo.find(cargo_query, {"_id": 0}))
    
    return user_cargo + operator_cargo

# API Routes

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# Аутентификация
@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    # Проверка существования пользователя
    if db.users.find_one({"phone": user_data.phone}):
        raise HTTPException(status_code=400, detail="User with this phone already exists")
    
    # Создание пользователя с ролью по умолчанию USER (функция 3)
    user_role = UserRole.USER  # Всегда USER для обычной регистрации
    
    user_id = str(uuid.uuid4())
    user_number = generate_user_number()  # Генерируем индивидуальный номер
    token_version = 1  # Начальная версия токена
    user = {
        "id": user_id,
        "user_number": user_number,  # Добавляем индивидуальный номер
        "full_name": user_data.full_name,
        "phone": user_data.phone,
        "password": hash_password(user_data.password),
        "role": user_role.value,  # Роль всегда USER
        "is_active": True,
        "token_version": token_version,  # Добавляем версию токена
        "created_at": datetime.utcnow()
    }
    
    db.users.insert_one(user)
    
    # Создание токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_user_token(
        user_id=user_id,
        phone=user_data.phone,
        token_version=1,  # Новые пользователи начинают с версии 1
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User(
            id=user_id,
            user_number=user_number,
            full_name=user_data.full_name,
            phone=user_data.phone,
            role=user_role,
            email=user.get("email"),
            address=user.get("address"),
            is_active=True,
            token_version=1,
            created_at=user["created_at"]
        )
    }

@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    # Сначала проверяем существование пользователя
    user = db.users.find_one({"phone": user_data.phone})
    
    # Детальная проверка ошибок авторизации
    if not user:
        # Пользователь с таким номером не найден
        raise HTTPException(
            status_code=401, 
            detail={
                "error_type": "user_not_found",
                "message": "Пользователь с указанным номером телефона не найден",
                "details": "Проверьте правильность номера телефона или зарегистрируйтесь в системе",
                "phone_format": "Формат: +992XXXXXXXXX или +7XXXXXXXXXX",
                "available_actions": ["Проверить номер телефона", "Зарегистрироваться", "Обратиться в поддержку"]
            }
        )
    
    # Проверяем правильность пароля
    if not verify_password(user_data.password, user["password_hash"]):
        # Получаем информацию о роли для более точного сообщения
        role_names = {
            "admin": "Администратор",
            "operator": "Оператор склада", 
            "courier": "Курьер",
            "user": "Пользователь"
        }
        role_display = role_names.get(user["role"], user["role"])
        
        # Неправильный пароль для существующего пользователя
        raise HTTPException(
            status_code=401, 
            detail={
                "error_type": "wrong_password",
                "message": f"Неправильный пароль для {role_display} {user['full_name']}",
                "details": "Проверьте правильность пароля и повторите попытку",
                "user_role": role_display,
                "user_name": user["full_name"],
                "user_phone": user["phone"],
                "password_requirements": "Пароль должен содержать минимум 6 символов",
                "available_actions": ["Проверить пароль", "Восстановить пароль", "Обратиться в поддержку"]
            }
        )
    
    # Детальная проверка статуса пользователя
    if not user["is_active"]:
        # Получаем информацию о роли для более точного сообщения
        role_names = {
            "admin": "Администратор",
            "operator": "Оператор склада", 
            "courier": "Курьер",
            "user": "Пользователь"
        }
        role_display = role_names.get(user["role"], user["role"])
        
        # Проверяем, был ли пользователь удален (soft delete)
        deletion_info = user.get("deleted_at") or user.get("deactivated_at")
        if deletion_info:
            status_message = f"Аккаунт {role_display} '{user['full_name']}' был удален из системы"
            status_details = f"Дата удаления: {deletion_info}"
        else:
            status_message = f"Аккаунт {role_display} '{user['full_name']}' заблокирован администратором"
            status_details = "Обратитесь к администратору для разблокировки"
        
        # Возвращаем специальную ошибку с деталями статуса
        raise HTTPException(
            status_code=403, 
            detail={
                "error_type": "account_disabled",
                "status_message": status_message,
                "status_details": status_details,
                "user_role": role_display,
                "user_name": user["full_name"],
                "user_phone": user["phone"],
                "is_deleted": bool(deletion_info)
            }
        )
    
    # Генерируем user_number если его нет
    user_number = user.get("user_number")
    if not user_number:
        user_number = generate_user_number()
        db.users.update_one(
            {"id": user["id"]},
            {"$set": {"user_number": user_number}}
        )
    
    # Получаем версию токена пользователя
    token_version = user.get("token_version", 1)
    
    # Создаем токен с user_id и token_version
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_user_token(
        user_id=user["id"],
        phone=user_data.phone,
        token_version=user.get("token_version", 1),
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User(
            id=user["id"],
            user_number=user_number,
            full_name=user["full_name"],
            phone=user["phone"],
            role=user["role"],
            email=user.get("email"),
            address=user.get("address"),
            is_active=user["is_active"],
            token_version=user.get("token_version", 1),
            created_at=user["created_at"]
        )
    }

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# Модель для обновления профиля пользователя
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

@app.put("/api/user/profile")
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update user profile information"""
    update_data = {}
    
    # Собираем только заполненные поля
    if profile_update.full_name:
        update_data["full_name"] = profile_update.full_name
    if profile_update.phone:
        # Проверяем, не занят ли номер телефона другим пользователем
        existing_user = db.users.find_one({"phone": profile_update.phone, "id": {"$ne": current_user.id}})
        if existing_user:
            raise HTTPException(status_code=400, detail="Этот номер телефона уже используется")
        update_data["phone"] = profile_update.phone
    if profile_update.email:
        # Проверяем, не занят ли email другим пользователем
        existing_user = db.users.find_one({"email": profile_update.email, "id": {"$ne": current_user.id}})
        if existing_user:
            raise HTTPException(status_code=400, detail="Этот email уже используется")
        update_data["email"] = profile_update.email
    if profile_update.address:
        update_data["address"] = profile_update.address
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    # Увеличиваем версию токена при изменении профиля
    current_token_version = current_user.token_version
    new_token_version = current_token_version + 1
    update_data["token_version"] = new_token_version
    
    # Обновляем пользователя в базе данных
    update_data["updated_at"] = datetime.utcnow()
    result = db.users.update_one(
        {"id": current_user.id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Получаем обновленные данные пользователя
    updated_user = db.users.find_one({"id": current_user.id})
    if not updated_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return User(
        id=updated_user["id"],
        user_number=updated_user.get("user_number"),
        full_name=updated_user["full_name"],
        phone=updated_user["phone"],
        role=updated_user["role"],
        email=updated_user.get("email"),
        address=updated_user.get("address"),
        is_active=updated_user["is_active"],
        token_version=updated_user.get("token_version", 1),
        created_at=updated_user["created_at"]
    )

# QR Code APIs
@app.get("/api/cargo/{cargo_id}/qr-code")
async def get_cargo_qr_code(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить QR код для конкретного груза"""
    cargo = db.cargo.find_one({"id": cargo_id}, {"_id": 0})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id}, {"_id": 0})
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверка доступа (пользователь может видеть только свои грузы, админ/оператор - все)
    if current_user.role == UserRole.USER and cargo.get("sender_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    qr_code_data = generate_cargo_qr_code_data(cargo)
    
    return {
        "cargo_id": cargo_id,
        "cargo_number": cargo.get("cargo_number"),
        "qr_code": qr_code_data
    }

@app.post("/api/cargo/scan-qr")
async def scan_cargo_qr_code(
    qr_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Сканирование QR кода для поиска груза и выполнения операций"""
    try:
        qr_text = qr_data.get("qr_text", "").strip()
        
        if not qr_text:
            raise HTTPException(status_code=400, detail="QR code text is required")
        
        # Извлекаем номер груза из QR кода
        # Новый формат: QR код содержит только номер груза
        cargo_number = qr_text.strip()
        
        if not cargo_number:
            raise HTTPException(status_code=400, detail="Invalid cargo QR code format")
        
        # Ищем груз в обеих коллекциях
        cargo = db.cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
        if not cargo:
            cargo = db.operator_cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
        
        if not cargo:
            raise HTTPException(status_code=404, detail=f"Cargo with number {cargo_number} not found")
        
        # Проверяем права доступа
        if current_user.role == UserRole.USER and cargo.get("sender_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to this cargo")
        
        # Дополнительная информация для операций
        cargo_info = {
            "cargo_id": cargo.get("id"),
            "cargo_number": cargo.get("cargo_number"),
            "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")),
            "weight": cargo.get("weight", 0),
            "declared_value": cargo.get("declared_value", 0),
            "sender_name": cargo.get("sender_full_name", "Не указан"),
            "recipient_name": cargo.get("recipient_full_name", "Не указан"),
            "recipient_phone": cargo.get("recipient_phone", "Не указан"),
            "status": cargo.get("status", "unknown"),
            "processing_status": cargo.get("processing_status", "unknown"),
            "payment_status": cargo.get("payment_status", "unknown"),
            "payment_method": cargo.get("payment_method", "not_paid"),
            "warehouse_name": cargo.get("warehouse_name", "Не указан"),
            "warehouse_location": cargo.get("warehouse_location"),
            "created_at": cargo.get("created_at"),
            "created_by_operator": cargo.get("created_by_operator", "Не указан"),
            
            # Информация о размещении
            "block_number": cargo.get("block_number"),
            "shelf_number": cargo.get("shelf_number"), 
            "cell_number": cargo.get("cell_number"),
            "placed_by_operator": cargo.get("placed_by_operator"),
            
            # Доступные операции в зависимости от статуса
            "available_operations": get_available_operations(cargo, current_user)
        }
        
        return {
            "success": True,
            "message": f"Груз {cargo_number} найден успешно",
            "cargo": cargo_info,
            "scan_timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (400, 403, 404) without modification
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning QR code: {str(e)}")

def get_available_operations(cargo: dict, current_user: User) -> list:
    """Определить доступные операции для груза в зависимости от статуса и роли пользователя"""
    operations = []
    
    cargo_status = cargo.get("status", "unknown")
    processing_status = cargo.get("processing_status", "unknown")
    payment_status = cargo.get("payment_status", "unknown")
    user_role = current_user.role
    
    # Операции для админа
    if user_role == UserRole.ADMIN:
        operations.extend([
            "view_details",  # Просмотр деталей
            "edit_cargo",    # Редактирование
            "print_label",   # Печать этикетки
            "generate_qr",   # Генерация QR
            "track_history"  # История операций
        ])
        
        if payment_status != "paid":
            operations.append("accept_payment")  # Прием оплаты
        
        if cargo_status == "accepted":
            operations.append("place_in_warehouse")  # Размещение на склад
        
        if cargo_status == "placed_in_warehouse":
            operations.extend([
                "move_cargo",     # Перемещение
                "prepare_delivery" # Подготовка к выдаче
            ])
        
        if cargo_status == "ready_for_delivery":
            operations.append("deliver_cargo")  # Выдача груза
    
    # Операции для оператора склада
    elif user_role == UserRole.WAREHOUSE_OPERATOR:
        operations.extend([
            "view_details",
            "print_label",
            "generate_qr",
            "track_history"
        ])
        
        # Проверяем привязку к складу оператора
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        cargo_warehouse_id = cargo.get("target_warehouse_id") or cargo.get("warehouse_id")
        
        if cargo_warehouse_id in operator_warehouse_ids:
            if payment_status != "paid":
                operations.append("accept_payment")
            
            if cargo_status == "accepted":
                operations.append("place_in_warehouse")
            
            if cargo_status == "placed_in_warehouse":
                operations.extend([
                    "move_cargo",
                    "prepare_delivery"
                ])
            
            if cargo_status == "ready_for_delivery":
                operations.append("deliver_cargo")
    
    # Операции для пользователя (клиента)
    elif user_role == UserRole.USER:
        operations.extend([
            "view_details",
            "track_history",
            "print_receipt"  # Квитанция для клиента
        ])
        
        if payment_status != "paid":
            operations.append("make_payment")  # Оплата клиентом
    
    return operations

@app.post("/api/cargo/generate-qr-by-number")
async def generate_qr_by_cargo_number(
    request_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Генерировать QR код по номеру груза"""
    try:
        cargo_number = request_data.get("cargo_number", "").strip()
        
        if not cargo_number:
            raise HTTPException(status_code=400, detail="Cargo number is required")
        
        # Проверяем существование груза
        cargo = db.cargo.find_one({"cargo_number": cargo_number})
        if not cargo:
            cargo = db.operator_cargo.find_one({"cargo_number": cargo_number})
        
        if not cargo:
            raise HTTPException(status_code=404, detail=f"Cargo with number {cargo_number} not found")
        
        # Проверяем права доступа
        if current_user.role == UserRole.USER and cargo.get("sender_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to this cargo")
        
        # Генерируем QR код
        qr_code_data = generate_cargo_qr_code_data(cargo)
        
        if not qr_code_data:
            raise HTTPException(status_code=500, detail="Failed to generate QR code")
        
        return {
            "success": True,
            "cargo_number": cargo_number,
            "cargo_name": cargo.get("cargo_name", "Груз"),
            "qr_code": qr_code_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating QR code: {str(e)}")

@app.post("/api/warehouse/cell/status")
async def check_warehouse_cell_status(
    cell_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Проверить статус занятости ячейки склада"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для проверки статуса ячейки"
        )
    
    try:
        warehouse_id = cell_data.get("warehouse_id")
        block_number = cell_data.get("block_number")
        shelf_number = cell_data.get("shelf_number")
        cell_number = cell_data.get("cell_number")
        
        # Поддержка ID формата
        warehouse_id_number = cell_data.get("warehouse_id_number")
        block_id_number = cell_data.get("block_id_number")
        shelf_id_number = cell_data.get("shelf_id_number")
        cell_id_number = cell_data.get("cell_id_number")
        
        if not warehouse_id and not warehouse_id_number:
            raise HTTPException(status_code=400, detail="Warehouse ID or warehouse ID number is required")
        
        # Строим запрос для поиска ячейки
        query = {}
        
        if warehouse_id_number and block_id_number and shelf_id_number and cell_id_number:
            # Поиск по ID номерам (новая система)
            query = {
                "warehouse_id_number": warehouse_id_number,
                "block_id_number": block_id_number,
                "shelf_id_number": shelf_id_number,
                "cell_id_number": cell_id_number
            }
        elif warehouse_id and block_number and shelf_number and cell_number:
            # Поиск по старой системе
            query = {
                "warehouse_id": warehouse_id,
                "block_number": block_number,
                "shelf_number": shelf_number,
                "cell_number": cell_number
            }
        else:
            raise HTTPException(status_code=400, detail="Missing required cell identification data")
        
        # Ищем ячейку
        cell = db.warehouse_cells.find_one(query)
        
        if not cell:
            # Ячейка не найдена, считаем её свободной (может быть создана позже)
            return {
                "success": True,
                "is_occupied": False,
                "occupied_by": None,
                "cell_exists": False,
                "message": "Cell not found, assuming available"
            }
        
        # Возвращаем статус ячейки
        return {
            "success": True,
            "is_occupied": cell.get("is_occupied", False),
            "occupied_by": cell.get("cargo_id"),
            "cargo_number": cell.get("cargo_number") if cell.get("is_occupied") else None,
            "cell_exists": True,
            "cell_info": {
                "id": cell.get("id"),
                "warehouse_id": cell.get("warehouse_id"),
                "warehouse_id_number": cell.get("warehouse_id_number"),
                "location_code": cell.get("location_code"),
                "id_based_code": cell.get("id_based_code"),
                "readable_name": cell.get("readable_name", f"Б{cell.get('block_number')}-П{cell.get('shelf_number')}-Я{cell.get('cell_number')}")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking cell status: {str(e)}")

@app.post("/api/cargo/place-in-cell")
async def place_cargo_in_cell(
    placement_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Разместить груз в ячейку склада по QR кодам с поддержкой ID системы"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для размещения груза"
        )
    
    try:
        cargo_number = placement_data.get("cargo_number", "").strip()
        cell_code = placement_data.get("cell_code", "").strip()
        
        if not cargo_number or not cell_code:
            raise HTTPException(status_code=400, detail="Cargo number and cell code are required")
        
        # Определяем формат cell_code
        is_id_format = False
        warehouse_id = None
        warehouse_id_number = None
        block = None
        shelf = None
        cell = None
        
        # Проверяем новый формат ID: 001-01-01-001
        if len(cell_code.split("-")) == 4 and all(part.isdigit() for part in cell_code.split("-")):
            is_id_format = True
            parts = cell_code.split("-")
            warehouse_id_number = parts[0]
            block_id = parts[1]
            shelf_id = parts[2]
            cell_id = parts[3]
            
            # Найдём склад по ID номеру
            warehouse = db.warehouses.find_one({"warehouse_id_number": warehouse_id_number})
            if not warehouse:
                raise HTTPException(status_code=404, detail=f"Warehouse with ID number {warehouse_id_number} not found")
            
            warehouse_id = warehouse["id"]
            
            # Найдём ячейку по ID номерам
            cell_query = {
                "warehouse_id_number": warehouse_id_number,
                "block_id_number": block_id,
                "shelf_id_number": shelf_id,
                "cell_id_number": cell_id
            }
            cell_record = db.warehouse_cells.find_one(cell_query)
            
            if cell_record:
                block = cell_record.get("block_number")
                shelf = cell_record.get("shelf_number")
                cell = cell_record.get("cell_number")
            else:
                # Если ячейка не найдена, извлекаем номера из ID
                block = int(block_id)
                shelf = int(shelf_id)
                cell = int(cell_id)
                
        # Проверяем старый формат: СКЛАД_ID-Б_номер-П_номер-Я_номер
        elif "-Б" in cell_code and "-П" in cell_code and "-Я" in cell_code:
            is_id_format = False
            
            # ИСПРАВЛЕНИЕ: Правильно извлекаем warehouse_id, учитывая что он может содержать дефисы (UUID)
            # Ищем первое вхождение "-Б" чтобы отделить warehouse_id от координат ячейки
            b_index = cell_code.find("-Б")
            if b_index == -1:
                raise HTTPException(status_code=400, detail="Invalid cell code format")
            
            warehouse_id = cell_code[:b_index]  # Всё до "-Б" это warehouse_id
            coordinates_part = cell_code[b_index+1:]  # Всё после "-Б" это координаты (Б_номер-П_номер-Я_номер)
            
            # Парсим координаты: Б_номер-П_номер-Я_номер
            coord_parts = coordinates_part.split("-")
            if len(coord_parts) != 3:
                raise HTTPException(status_code=400, detail="Invalid cell code format")
            
            try:
                block = int(coord_parts[0][1:])  # Убираем "Б" и парсим номер
                shelf = int(coord_parts[1][1:])  # Убираем "П" и парсим номер 
                cell = int(coord_parts[2][1:])   # Убираем "Я" и парсим номер
            except (ValueError, IndexError) as e:
                raise HTTPException(status_code=400, detail=f"Invalid cell coordinates format: {str(e)}")
            
            # Проверяем существование склада
            warehouse = db.warehouses.find_one({"id": warehouse_id})
            if not warehouse:
                raise HTTPException(status_code=404, detail="Warehouse not found")
                
        # НОВОЕ: Проверяем компактный формат 9 цифр: 003010106 (склад блок полка ячейка)
        elif len(cell_code) == 9 and cell_code.isdigit():
            is_id_format = False
            
            # Парсим НОВЫЙ компактный формат: WWWBBSSCC
            warehouse_number = int(cell_code[:3])  # Первые 3 цифры - номер склада
            block_number = int(cell_code[3:5])     # Следующие 2 цифры - номер блока  
            shelf_number = int(cell_code[5:7])     # Следующие 2 цифры - номер полки
            cell_number = int(cell_code[7:9])      # Последние 2 цифры - номер ячейки
            
            # Найдем склад по warehouse_number
            warehouse = db.warehouses.find_one({"warehouse_number": warehouse_number})
            if not warehouse:
                raise HTTPException(status_code=404, detail=f"Warehouse with number {warehouse_number} not found")
            
            warehouse_id = warehouse["id"]
            block = block_number
            shelf = shelf_number
            cell = cell_number
            
            print(f"🔍 НОВЫЙ компактный формат QR (9 цифр): {cell_code} -> Склад#{warehouse_number} Б{block} П{shelf} Я{cell}")
                
        # СТАРЫЙ: Проверяем компактный формат 8 цифр: 03010106 (для обратной совместимости)
        elif len(cell_code) == 8 and cell_code.isdigit():
            is_id_format = False
            
            # Парсим СТАРЫЙ компактный формат: WWBBSSCC
            warehouse_number = int(cell_code[:2])  # Первые 2 цифры - номер склада
            block_number = int(cell_code[2:4])     # Следующие 2 цифры - номер блока  
            shelf_number = int(cell_code[4:6])     # Следующие 2 цифры - номер полки
            cell_number = int(cell_code[6:8])      # Последние 2 цифры - номер ячейки
            
            # Найдем склад по warehouse_number
            warehouse = db.warehouses.find_one({"warehouse_number": warehouse_number})
            if not warehouse:
                raise HTTPException(status_code=404, detail=f"Warehouse with number {warehouse_number} not found")
            
            warehouse_id = warehouse["id"]
            block = block_number
            shelf = shelf_number
            cell = cell_number
            
            print(f"🔍 СТАРЫЙ компактный формат QR (8 цифр): {cell_code} -> Склад#{warehouse_number} Б{block} П{shelf} Я{cell}")
                
        else:
            raise HTTPException(status_code=400, detail="Invalid cell code format. Expected: '003010106' (9 digits), '03010106' (8 digits), '001-01-01-001' or 'WAREHOUSE_ID-Б1-П1-Я1'")
        
        # Ищем груз
        cargo = db.cargo.find_one({"cargo_number": cargo_number})
        if not cargo:
            cargo = db.operator_cargo.find_one({"cargo_number": cargo_number})
        
        if not cargo:
            raise HTTPException(status_code=404, detail=f"Cargo {cargo_number} not found")
        
        # ИСПРАВЛЕНИЕ: Убираем проверку статуса оплаты - все грузы в разделе "Размещение" могут размещаться
        # Это позволяет размещать грузы с любым статусом оплаты
        print(f"📦 Размещаем груз {cargo_number} со статусом: {cargo.get('processing_status', 'unknown')}")
        
        # Проверяем, свободна ли ячейка
        if is_id_format:
            cell_query = {
                "warehouse_id_number": warehouse_id_number,
                "block_id_number": block_id,
                "shelf_id_number": shelf_id,
                "cell_id_number": cell_id,
                "is_occupied": True
            }
        else:
            location_code = f"{block}-{shelf}-{cell}"
            cell_query = {
                "warehouse_id": warehouse_id,
                "location_code": location_code,
                "is_occupied": True
            }
        
        existing_cell = db.warehouse_cells.find_one(cell_query)
        
        if existing_cell:
            raise HTTPException(
                status_code=400, 
                detail=f"Cell is already occupied by cargo {existing_cell.get('cargo_number', 'unknown')}"
            )
        
        # Размещаем груз в ячейку
        cell_data = {
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse.get("name", "Неизвестный склад"),
            "cargo_id": cargo.get("id"),
            "cargo_number": cargo_number,
            "cargo_name": cargo.get("cargo_name", "Груз"),
            "cargo_weight": cargo.get("weight", 0),
            "placed_at": datetime.utcnow(),
            "placed_by": current_user.id,
            "placed_by_name": current_user.full_name,
            "is_occupied": True
        }
        
        if is_id_format:
            # Новая система ID
            cell_data.update({
                "warehouse_id_number": warehouse_id_number,
                "block_id_number": block_id,
                "shelf_id_number": shelf_id,
                "cell_id_number": cell_id,
                "id_based_code": cell_code,
                "block_number": block,
                "shelf_number": shelf,
                "cell_number": cell,
                "location_code": f"{block}-{shelf}-{cell}",
                "readable_name": f"Б{block}-П{shelf}-Я{cell}"
            })
            
            # Обновляем или создаём ячейку
            db.warehouse_cells.update_one(
                {
                    "warehouse_id_number": warehouse_id_number,
                    "block_id_number": block_id,
                    "shelf_id_number": shelf_id,
                    "cell_id_number": cell_id
                },
                {"$set": cell_data},
                upsert=True
            )
        else:
            # Старая система
            location_code = f"{block}-{shelf}-{cell}"
            cell_data.update({
                "location_code": location_code,
                "block_number": block,
                "shelf_number": shelf,
                "cell_number": cell
            })
            
            # Обновляем или создаём ячейку
            db.warehouse_cells.update_one(
                {
                    "warehouse_id": warehouse_id,
                    "location_code": location_code
                },
                {"$set": cell_data},
                upsert=True
            )
        
        # Обновляем статус груза
        update_data = {
            "status": "placed_in_warehouse",
            "processing_status": "placed",
            "warehouse_location": f"Блок {block}, Полка {shelf}, Ячейка {cell}",
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse.get("name"),
            "block_number": block,
            "shelf_number": shelf,
            "cell_number": cell,
            "placement_date": datetime.utcnow(),
            "placed_by": current_user.id,
            "placed_by_name": current_user.full_name,
            "updated_at": datetime.utcnow()
        }
        
        if is_id_format:
            update_data.update({
                "warehouse_id_number": warehouse_id_number,
                "id_based_location": cell_code,
                "readable_location": f"Б{block}-П{shelf}-Я{cell}"
            })
        
        # Обновляем груз в соответствующей коллекции
        cargo_updated = db.cargo.update_one(
            {"cargo_number": cargo_number},
            {"$set": update_data}
        )
        
        if cargo_updated.matched_count == 0:
            db.operator_cargo.update_one(
                {"cargo_number": cargo_number},
                {"$set": update_data}
            )
        
        return {
            "success": True,
            "message": f"Cargo {cargo_number} successfully placed in cell",
            "cargo_id": cargo.get("id"),
            "warehouse_name": warehouse.get("name"),
            "location": f"Блок {block}, Полка {shelf}, Ячейка {cell}",
            "readable_location": f"Б{block}-П{shelf}-Я{cell}",
            "cell_code": cell_code,
            "format_used": "ID" if is_id_format else "Legacy",
            "placed_by": current_user.full_name,
            "placement_date": update_data["placement_date"].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error placing cargo in cell: {str(e)}")

@app.get("/api/operator/placement-statistics")
async def get_placement_statistics(
    current_user: User = Depends(get_current_user)
):
    """Получить статистику размещения грузов для оператора"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для просмотра статистики размещения"
        )
    
    try:
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Статистика за сегодня для текущего оператора
        today_placements = db.warehouse_cells.count_documents({
            "placed_by": current_user.id,
            "placed_at": {"$gte": today_start, "$lte": today_end}
        })
        
        # Общая статистика за текущую сессию работы (последние 8 часов)
        session_start = datetime.utcnow() - timedelta(hours=8)
        session_placements = db.warehouse_cells.count_documents({
            "placed_by": current_user.id,
            "placed_at": {"$gte": session_start}
        })
        
        # Последние размещенные грузы
        recent_placements = list(db.warehouse_cells.find(
            {
                "placed_by": current_user.id,
                "placed_at": {"$gte": session_start}
            },
            {
                "cargo_number": 1,
                "cargo_name": 1,
                "warehouse_name": 1,
                "location_code": 1,
                "block": 1,
                "shelf": 1,
                "cell": 1,
                "placed_at": 1,
                "_id": 0
            }
        ).sort("placed_at", -1).limit(10))
        
        return {
            "operator_name": current_user.full_name,
            "today_placements": today_placements,
            "session_placements": session_placements,
            "recent_placements": recent_placements
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving placement statistics: {str(e)}")

@app.get("/api/warehouses/{warehouse_id}/structure")
async def get_warehouse_structure(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить детальную структуру склада"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для просмотра структуры склада"
        )
    
    try:
        # Получаем склад
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        # Получаем все ячейки склада
        warehouse_cells = list(db.warehouse_cells.find(
            {"warehouse_id": warehouse_id},
            {"_id": 0}
        ))
        
        # Создаем структуру склада
        structure = {
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse.get("name"),
            "blocks": warehouse.get("blocks", 3),
            "shelves_per_block": warehouse.get("shelves_per_block", 5), 
            "cells_per_shelf": warehouse.get("cells_per_shelf", 10),
            "total_cells": warehouse.get("blocks", 3) * warehouse.get("shelves_per_block", 5) * warehouse.get("cells_per_shelf", 10),
            "occupied_cells": len(warehouse_cells),
            "free_cells": (warehouse.get("blocks", 3) * warehouse.get("shelves_per_block", 5) * warehouse.get("cells_per_shelf", 10)) - len(warehouse_cells),
            "cells": warehouse_cells
        }
        
        return structure
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving warehouse structure: {str(e)}")

@app.post("/api/warehouse/cell/generate-qr")
async def generate_warehouse_cell_qr(
    cell_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Генерировать QR код для ячейки склада с поддержкой ID формата"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для генерации QR кода"
        )
    
    try:
        warehouse_id = cell_data.get("warehouse_id")
        block = cell_data.get("block")
        shelf = cell_data.get("shelf") 
        cell = cell_data.get("cell")
        format_type = cell_data.get("format", "id")  # "id" для новой системы, "legacy" для старой
        
        if not all([warehouse_id, block, shelf, cell]):
            raise HTTPException(status_code=400, detail="Missing required cell data")
        
        # Получаем склад
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        # Генерируем QR код в зависимости от формата
        use_id_format = (format_type == "id")
        qr_code_data = generate_warehouse_cell_qr_code(warehouse, block, shelf, cell, use_id_format)
        
        if not qr_code_data:
            raise HTTPException(status_code=500, detail="Failed to generate QR code")
        
        # Формат ответа зависит от выбранного типа
        if use_id_format:
            # Новый формат с ID номерами
            warehouse_id_number = warehouse.get("warehouse_id_number", f"{warehouse_id[:3]}")
            block_id = f"{block:02d}"
            shelf_id = f"{shelf:02d}"
            cell_id = f"{cell:03d}"
            cell_code = f"{warehouse_id_number}-{block_id}-{shelf_id}-{cell_id}"
            readable_name = f"Б{block}-П{shelf}-Я{cell}"
        else:
            # Старый формат для совместимости
            cell_code = f"{warehouse_id}-Б{block}-П{shelf}-Я{cell}"
            readable_name = f"Б{block}-П{shelf}-Я{cell}"
        
        return {
            "success": True,
            "warehouse_id": warehouse_id,
            "warehouse_id_number": warehouse.get("warehouse_id_number"),
            "location": f"Блок {block}, Полка {shelf}, Ячейка {cell}",
            "readable_name": readable_name,  # Для печати QR кода
            "cell_code": cell_code,  # ID в QR коде
            "format_type": format_type,
            "qr_code": qr_code_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cell QR code: {str(e)}")

# НОВЫЙ ENDPOINT: Обновление номеров складов для уникальности QR кодов
@app.post("/api/admin/warehouses/update-id-numbers")
async def update_warehouse_id_numbers(
    current_user: User = Depends(get_current_user)
):
    """Обновить номера складов для обеспечения уникальности QR кодов ячеек"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор может обновлять номера складов"
        )
    
    try:
        # Получаем все склады
        warehouses = list(db.warehouses.find({}, {"_id": 0}))
        
        updated_warehouses = []
        
        for warehouse in warehouses:
            warehouse_id = warehouse.get("id")
            current_id_number = warehouse.get("warehouse_id_number")
            
            # Если у склада нет уникального номера или номер некорректный, генерируем новый
            if not current_id_number or not current_id_number.isdigit() or len(current_id_number) != 3:
                # Генерируем новый уникальный номер
                new_id_number = generate_warehouse_id_number()
                
                # Обновляем склад
                update_result = db.warehouses.update_one(
                    {"id": warehouse_id},
                    {"$set": {"warehouse_id_number": new_id_number}}
                )
                
                if update_result.modified_count > 0:
                    updated_warehouses.append({
                        "warehouse_id": warehouse_id,
                        "name": warehouse.get("name", "Unknown"),
                        "old_number": current_id_number,
                        "new_number": new_id_number
                    })
            else:
                # Проверяем уникальность существующего номера
                duplicates = list(db.warehouses.find({"warehouse_id_number": current_id_number}))
                if len(duplicates) > 1:
                    # Есть дубликаты, нужно обновить
                    new_id_number = generate_warehouse_id_number()
                    
                    update_result = db.warehouses.update_one(
                        {"id": warehouse_id},
                        {"$set": {"warehouse_id_number": new_id_number}}
                    )
                    
                    if update_result.modified_count > 0:
                        updated_warehouses.append({
                            "warehouse_id": warehouse_id,
                            "name": warehouse.get("name", "Unknown"),
                            "old_number": current_id_number,
                            "new_number": new_id_number
                        })
        
        return {
            "message": "Номера складов обновлены успешно",
            "total_warehouses": len(warehouses),
            "updated_warehouses": updated_warehouses,
            "updated_count": len(updated_warehouses)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating warehouse ID numbers: {str(e)}")

@app.post("/api/warehouses/{warehouse_id}/add-block")
async def add_warehouse_block(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Добавить новый блок к складу"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для изменения структуры склада"
        )
    
    try:
        # Получаем склад
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        current_blocks = warehouse.get("blocks", 3)
        new_blocks_count = current_blocks + 1
        
        # Обновляем количество блоков
        db.warehouses.update_one(
            {"id": warehouse_id},
            {
                "$set": {
                    "blocks": new_blocks_count,
                    "updated_at": datetime.utcnow(),
                    "updated_by": current_user.id
                }
            }
        )
        
        return {
            "success": True,
            "message": f"Блок добавлен. Теперь блоков: {new_blocks_count}",
            "new_blocks_count": new_blocks_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding block: {str(e)}")

@app.post("/api/warehouses/{warehouse_id}/delete-block")
async def delete_warehouse_block(
    warehouse_id: str,
    block_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Удалить блок склада"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для изменения структуры склада"
        )
    
    try:
        block_number = block_data.get("block_number")
        if not block_number:
            raise HTTPException(status_code=400, detail="Block number is required")
        
        # Получаем склад
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        # Проверяем, есть ли груз в ячейках этого блока
        occupied_cells = db.warehouse_cells.find({
            "warehouse_id": warehouse_id,
            "block": block_number,
            "is_occupied": True
        })
        
        if list(occupied_cells):
            raise HTTPException(
                status_code=400, 
                detail=f"Нельзя удалить блок {block_number}: в нем есть размещенный груз"
            )
        
        # Удаляем все ячейки блока
        db.warehouse_cells.delete_many({
            "warehouse_id": warehouse_id,
            "block": block_number
        })
        
        current_blocks = warehouse.get("blocks", 3)
        if current_blocks > 1:
            new_blocks_count = current_blocks - 1
            # Обновляем количество блоков
            db.warehouses.update_one(
                {"id": warehouse_id},
                {
                    "$set": {
                        "blocks": new_blocks_count,
                        "updated_at": datetime.utcnow(),
                        "updated_by": current_user.id
                    }
                }
            )
        else:
            new_blocks_count = current_blocks
        
        return {
            "success": True,
            "message": f"Блок {block_number} удален. Блоков осталось: {new_blocks_count}",
            "new_blocks_count": new_blocks_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting block: {str(e)}")

@app.post("/api/cargo/generate-application-qr/{cargo_number}")
async def generate_application_qr_code(
    cargo_number: str,
    current_user: User = Depends(get_current_user)
):
    """Генерировать QR код для номера заявки/груза"""
    try:
        # Поиск груза в обеих коллекциях
        cargo = db.cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
        if not cargo:
            cargo = db.operator_cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
        
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
        
        # Проверка доступа
        if current_user.role == UserRole.USER and cargo.get("sender_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Создаем простой QR код с номером заявки
        import qrcode
        from io import BytesIO
        import base64
        
        # Данные для QR кода заявки
        qr_data = f"ЗАЯВКА TAJLINE.TJ\nНомер: {cargo_number}\nДата: {cargo.get('created_at', 'Не указана')}\nОтправитель: {cargo.get('sender_full_name', 'Не указан')}"
        
        # Генерируем QR код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Конвертируем в base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        qr_code_data = f"data:image/png;base64,{img_str}"
        
        return {
            "cargo_number": cargo_number,
            "qr_code": qr_code_data,
            "qr_text": qr_data,
            "cargo_info": {
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "weight": cargo.get("weight", 0),
                "sender_name": cargo.get("sender_full_name", "Не указан"),
                "recipient_name": cargo.get("recipient_full_name", "Не указан"),
                "created_at": cargo.get("created_at", "Не указана")
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating application QR code: {str(e)}")

@app.get("/api/cargo/batch/{cargo_numbers}/qr-codes")
async def get_batch_cargo_qr_codes(
    cargo_numbers: str,  # comma-separated cargo numbers
    current_user: User = Depends(get_current_user)
):
    """Получить QR коды для группы грузов по номерам (для печати накладных)"""
    try:
        cargo_numbers_list = [num.strip() for num in cargo_numbers.split(',') if num.strip()]
        
        if not cargo_numbers_list:
            raise HTTPException(status_code=400, detail="No cargo numbers provided")
        
        cargo_qr_codes = []
        
        for cargo_number in cargo_numbers_list:
            # Поиск груза в обеих коллекциях
            cargo = db.cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
            if not cargo:
                cargo = db.operator_cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
            
            if cargo:
                # Проверка доступа
                if current_user.role == UserRole.USER and cargo.get("sender_id") != current_user.id:
                    continue  # Пропускаем недоступные грузы
                
                qr_code_data = generate_cargo_qr_code_data(cargo)
                cargo_qr_codes.append({
                    "cargo_id": cargo.get("id"),
                    "cargo_number": cargo.get("cargo_number"),
                    "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")),
                    "weight": cargo.get("weight", 0),
                    "sender_name": cargo.get("sender_full_name", "Не указан"),
                    "recipient_name": cargo.get("recipient_full_name", "Не указан"),
                    "qr_code": qr_code_data
                })
        
        return {
            "requested_count": len(cargo_numbers_list),
            "found_count": len(cargo_qr_codes),
            "cargo_qr_codes": cargo_qr_codes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating batch QR codes: {str(e)}")

@app.get("/api/cargo/batch/{cargo_numbers}/qr-codes-old")
async def get_batch_cargo_qr_codes_old(
    cargo_numbers: str,  # comma-separated cargo numbers
    current_user: User = Depends(get_current_user)
):
    """Получить QR коды для группы грузов по номерам (для печати накладных)"""
    try:
        cargo_numbers_list = [num.strip() for num in cargo_numbers.split(',') if num.strip()]
        
        if not cargo_numbers_list:
            raise HTTPException(status_code=400, detail="No cargo numbers provided")
        
        cargo_qr_codes = []
        
        for cargo_number in cargo_numbers_list:
            # Поиск груза в обеих коллекциях
            cargo = db.cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
            if not cargo:
                cargo = db.operator_cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
            
            if cargo:
                # Проверка доступа
                if current_user.role == UserRole.USER and cargo.get("sender_id") != current_user.id:
                    continue  # Пропускаем недоступные грузы
                
                qr_code_data = generate_cargo_qr_code_data(cargo)
                cargo_qr_codes.append({
                    "cargo_id": cargo.get("id"),
                    "cargo_number": cargo.get("cargo_number"),
                    "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")),
                    "weight": cargo.get("weight", 0),
                    "sender_name": cargo.get("sender_full_name", "Не указан"),
                    "recipient_name": cargo.get("recipient_full_name", "Не указан"),
                    "qr_code": qr_code_data
                })
        
        return {
            "requested_count": len(cargo_numbers_list),
            "found_count": len(cargo_qr_codes),
            "cargo_qr_codes": cargo_qr_codes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating batch QR codes: {str(e)}")

@app.get("/api/cargo/invoice/{cargo_numbers}")
async def generate_cargo_invoice(
    cargo_numbers: str,  # comma-separated cargo numbers
    current_user: User = Depends(get_current_user)
):
    """Генерировать накладную для группы грузов"""
    try:
        cargo_numbers_list = [num.strip() for num in cargo_numbers.split(',') if num.strip()]
        
        if not cargo_numbers_list:
            raise HTTPException(status_code=400, detail="No cargo numbers provided")
        
        invoice_cargo = []
        total_weight = 0
        total_value = 0
        sender_info = None
        recipient_info = None
        
        for cargo_number in cargo_numbers_list:
            # Поиск груза в обеих коллекциях
            cargo = db.cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
            if not cargo:
                cargo = db.operator_cargo.find_one({"cargo_number": cargo_number}, {"_id": 0})
            
            if cargo:
                # Проверка доступа
                if current_user.role == UserRole.USER and cargo.get("sender_id") != current_user.id:
                    continue  # Пропускаем недоступные грузы
                
                # Получаем информацию о грузе
                cargo_weight = cargo.get("weight", 0)
                cargo_value = 0
                
                if cargo.get('declared_value'):
                    try:
                        cargo_value = float(cargo.get('declared_value', 0))
                    except (ValueError, TypeError):
                        cargo_value = 0
                elif cargo.get('total_cost'):
                    try:
                        cargo_value = float(cargo.get('total_cost', 0))
                    except (ValueError, TypeError):
                        cargo_value = 0
                
                total_weight += cargo_weight if isinstance(cargo_weight, (int, float)) else 0
                total_value += cargo_value
                
                # Сохраняем информацию об отправителе и получателе (используем первый груз)
                if not sender_info:
                    sender_info = {
                        "name": cargo.get("sender_full_name", "Не указан"),
                        "phone": cargo.get("sender_phone", "Не указан"),
                        "address": cargo.get("sender_address", "Не указан")
                    }
                
                if not recipient_info:
                    recipient_info = {
                        "name": cargo.get("recipient_full_name", "Не указан"),
                        "phone": cargo.get("recipient_phone", "Не указан"),
                        "address": cargo.get("recipient_address", "Не указан")
                    }
                
                invoice_cargo.append({
                    "cargo_number": cargo.get("cargo_number"),
                    "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")),
                    "weight": cargo_weight,
                    "declared_value": cargo_value,
                    "status": cargo.get("status", "unknown"),
                    "payment_method": cargo.get("payment_method", "not_paid"),
                    "warehouse_name": cargo.get("warehouse_name", "Не указан")
                })
        
        if not invoice_cargo:
            raise HTTPException(status_code=404, detail="No accessible cargo found")
        
        # Генерируем накладную
        from datetime import datetime
        invoice_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{len(invoice_cargo)}"
        
        invoice_data = {
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "operator_name": current_user.full_name,
            "operator_phone": current_user.phone,
            "sender_info": sender_info,
            "recipient_info": recipient_info,
            "cargo_list": invoice_cargo,
            "summary": {
                "total_items": len(invoice_cargo),
                "total_weight": round(total_weight, 2),
                "total_value": round(total_value, 2)
            }
        }
        
        return invoice_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating invoice: {str(e)}")

@app.get("/api/cargo/{cargo_id}/qr-code-old")
async def get_cargo_qr_code_old(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить QR код для конкретного груза (старая версия для совместимости)"""

@app.get("/api/warehouse/{warehouse_id}/cell-qr/{block}/{shelf}/{cell}")
async def get_warehouse_cell_qr_code(
    warehouse_id: str,
    block: int,
    shelf: int,
    cell: int,
    current_user: User = Depends(get_current_user)
):
    """Получить QR код для ячейки склада"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти склад
    warehouse = db.warehouses.find_one({"id": warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Проверить существование ячейки
    if block > warehouse.get("blocks_count", 0) or shelf > warehouse.get("shelves_per_block", 0) or cell > warehouse.get("cells_per_shelf", 0):
        raise HTTPException(status_code=404, detail="Cell not found")
    
    qr_code_data = generate_warehouse_cell_qr_code(warehouse, block, shelf, cell)
    
    return {
        "warehouse_id": warehouse_id,
        "warehouse_name": warehouse.get("name"),
        "location": f"Б{block}-П{shelf}-Я{cell}",
        "qr_code": qr_code_data
    }

@app.get("/api/warehouse/{warehouse_id}/all-cells-qr")
async def get_all_warehouse_cells_qr_codes(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить QR коды для всех ячеек склада (для печати)"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти склад
    warehouse = db.warehouses.find_one({"id": warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    qr_codes = []
    blocks_count = warehouse.get("blocks_count", 1)
    shelves_per_block = warehouse.get("shelves_per_block", 1)
    cells_per_shelf = warehouse.get("cells_per_shelf", 10)
    
    for block in range(1, blocks_count + 1):
        for shelf in range(1, shelves_per_block + 1):
            for cell in range(1, cells_per_shelf + 1):
                qr_code_data = generate_warehouse_cell_qr_code(warehouse, block, shelf, cell)
                qr_codes.append({
                    "block": block,
                    "shelf": shelf,
                    "cell": cell,
                    "location": f"Б{block}-П{shelf}-Я{cell}",
                    "qr_code": qr_code_data
                })
    
    return {
        "warehouse_id": warehouse_id,
        "warehouse_name": warehouse.get("name"),
        "total_cells": len(qr_codes),
        "qr_codes": qr_codes
    }

# QR Code Scanning API
@app.post("/api/qr/scan")
async def scan_qr_code(
    qr_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обработка отсканированного QR кода"""
    qr_text = qr_data.get("qr_text", "")
    
    if not qr_text:
        raise HTTPException(status_code=400, detail="QR code data is empty")
    
    # Определяем тип QR кода по содержимому
    if "-Б" in qr_text and "-П" in qr_text and "-Я" in qr_text:
        # QR код ячейки склада: СКЛАД_ID-Б_номер-П_номер-Я_номер
        try:
            # Разбираем код ячейки
            parts = qr_text.split("-")
            if len(parts) < 4:
                raise HTTPException(status_code=400, detail="Invalid cell QR code format")
            
            warehouse_id = parts[0]
            block = int(parts[1][1:])  # Убираем "Б"
            shelf = int(parts[2][1:])  # Убираем "П" 
            cell = int(parts[3][1:])   # Убираем "Я"
            
            # Найти склад
            warehouse = db.warehouses.find_one({"id": warehouse_id})
            if not warehouse:
                raise HTTPException(status_code=404, detail="Warehouse not found")
            
            # Проверка доступа
            if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Проверяем, есть ли груз в этой ячейке
            location_code = f"{block}-{shelf}-{cell}"
            warehouse_cell = db.warehouse_cells.find_one({
                "warehouse_id": warehouse_id,
                "location_code": location_code
            })
            
            return {
                "type": "warehouse_cell",
                "warehouse_id": warehouse_id,
                "warehouse_name": warehouse.get("name", "Неизвестный склад"),
                "block": block,
                "shelf": shelf,
                "cell": cell,
                "location_code": location_code,
                "is_occupied": warehouse_cell is not None,
                "cargo_id": warehouse_cell.get("cargo_id") if warehouse_cell else None,
                "cargo_number": warehouse_cell.get("cargo_number") if warehouse_cell else None
            }
            
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cell QR code format - invalid numbers")
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid cell QR code format")
    
    else:
        # Предполагаем, что это QR код груза (только номер)
        try:
            cargo_number = qr_text.strip()
            
            # Ищем груз
            cargo = db.cargo.find_one({"cargo_number": cargo_number})
            if not cargo:
                cargo = db.operator_cargo.find_one({"cargo_number": cargo_number})
            
            if not cargo:
                raise HTTPException(status_code=404, detail=f"Cargo {cargo_number} not found")
            
            # Проверка доступа
            if current_user.role == UserRole.USER and cargo.get("sender_id") != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            return {
                "type": "cargo",
                "cargo_id": cargo["id"],
                "cargo_number": cargo["cargo_number"],
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "status": cargo.get("status"),
                "weight": cargo.get("weight"),
                "sender": cargo.get("sender_full_name", "Не указан"),
                "recipient": cargo.get("recipient_full_name", cargo.get("recipient_name", "Не указан")),
                "location": cargo.get("warehouse_location", "Не размещен")
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid cargo QR code format")

@app.get("/api/operator/cargo/list")
async def get_operator_cargo_list(
    page: int = 1,
    per_page: int = 25,
    filter_status: Optional[str] = None,  # payment_pending, awaiting_placement, new_request
    current_user: User = Depends(get_current_user)
):
    """Получить список грузов оператора с пагинацией и возможностью фильтрации"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Валидация параметров пагинации
    pagination = PaginationParams(page=page, per_page=per_page)
    
    # Базовый запрос для поиска грузов
    base_query = {}
    
    # Если это оператор, показываем только грузы с его складов
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        operator_warehouses = get_operator_warehouse_ids(current_user.id)
        if operator_warehouses:
            base_query["warehouse_id"] = {"$in": operator_warehouses}
    
    # Применяем фильтры
    if filter_status:
        if filter_status == "payment_pending":
            base_query["processing_status"] = "payment_pending"
            base_query["payment_status"] = "pending"
        elif filter_status == "awaiting_payment":
            base_query["processing_status"] = "payment_pending"
        elif filter_status == "awaiting_placement":
            base_query["processing_status"] = {"$in": ["paid", "invoice_printed"]}
            base_query["warehouse_location"] = {"$exists": False}
        elif filter_status == "new_request":
            base_query["processing_status"] = "payment_pending"
            base_query["status"] = CargoStatus.ACCEPTED
    
    # Ищем в коллекции operator_cargo (принятые заявки)
    operator_cargo_cursor = db.operator_cargo.find(base_query).sort("created_at", -1)
    
    # Также ищем в коллекции cargo (если админ)
    user_cargo_list = []
    if current_user.role == UserRole.ADMIN:
        user_cargo_cursor = db.cargo.find(base_query).sort("created_at", -1)
        user_cargo_list = list(user_cargo_cursor)
    
    # Получаем общий count для правильной пагинации
    operator_cargo_count = db.operator_cargo.count_documents(base_query)
    user_cargo_count = len(user_cargo_list)
    total_count = operator_cargo_count + user_cargo_count
    
    # Применяем пагинацию
    skip = (pagination.page - 1) * pagination.per_page
    
    # Получаем элементы с учетом пагинации
    all_cargo = []
    
    # Получаем operator cargo
    operator_cargo_list = list(operator_cargo_cursor.skip(skip).limit(pagination.per_page))
    
    # Если нужно больше элементов, добавляем из user cargo
    remaining = pagination.per_page - len(operator_cargo_list)
    if remaining > 0 and user_cargo_list:
        user_skip = max(0, skip - operator_cargo_count)
        user_cargo_subset = user_cargo_list[user_skip:user_skip + remaining]
        all_cargo.extend(user_cargo_subset)
    
    all_cargo.extend(operator_cargo_list)
    
    # Нормализуем данные
    normalized_cargo = []
    
    # Обрабатываем все грузы
    for cargo in all_cargo:
        normalized = serialize_mongo_document(cargo)
        normalized.update({
            'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
            'sender_id': cargo.get('created_by') or cargo.get('sender_id', 'unknown'),
            'recipient_name': cargo.get('recipient_full_name', 'Не указан'),
            'sender_address': cargo.get('sender_address', 'Не указан'),
            'recipient_address': cargo.get('recipient_address', 'Не указан'),
            'recipient_phone': cargo.get('recipient_phone', 'Не указан'),
            'processing_status': cargo.get('processing_status', 'payment_pending'),
            'sender_full_name': cargo.get('sender_full_name', 'Не указан'),
            'sender_phone': cargo.get('sender_phone', 'Не указан')
        })
        normalized_cargo.append(normalized)
    
    # Создаем ответ с пагинацией
    return create_pagination_response(
        normalized_cargo, 
        total_count, 
        pagination.page, 
        pagination.per_page
    )

@app.post("/api/admin/cleanup-test-data")
async def cleanup_test_data(
    current_user: User = Depends(get_current_user)
):
    """Очистить все тестовые данные из системы"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can cleanup test data")
    
    try:
        cleanup_report = {
            "users_deleted": 0,
            "cargo_requests_deleted": 0,
            "operator_cargo_deleted": 0,
            "user_cargo_deleted": 0,
            "unpaid_orders_deleted": 0,
            "notifications_deleted": 0,
            "warehouse_cells_deleted": 0,
            "details": []
        }
        
        # 1. Удаляем тестовых пользователей (кроме системных админов)
        # Определяем тестовых пользователей по паттернам телефонов или имен
        test_user_patterns = [
            {"phone": {"$regex": "^\\+992900000000"}},  # Бахром Клиент
            {"phone": {"$regex": "^\\+79777888999"}},  # Warehouse Operator
            {"full_name": {"$regex": "Тест"}},
            {"full_name": {"$regex": "Test"}},
            {"full_name": {"$regex": "Клиент"}},
            {"email": {"$regex": "test"}},
            {"email": {"$regex": "@test\\."}}
        ]
        
        # Ищем тестовых пользователей
        test_users_query = {"$or": test_user_patterns}
        test_users = list(db.users.find(test_users_query, {"id": 1, "phone": 1, "full_name": 1}))
        
        if test_users:
            test_user_ids = [user["id"] for user in test_users]
            
            # Удаляем связанные данные для тестовых пользователей
            # Заявки на грузы
            requests_result = db.cargo_requests.delete_many({"sender_id": {"$in": test_user_ids}})
            cleanup_report["cargo_requests_deleted"] = requests_result.deleted_count
            
            # Грузы операторов (созданные тестовыми пользователями или для них)
            operator_cargo_result = db.operator_cargo.delete_many({
                "$or": [
                    {"created_by": {"$in": test_user_ids}},
                    {"sender_id": {"$in": test_user_ids}}
                ]
            })
            cleanup_report["operator_cargo_deleted"] = operator_cargo_result.deleted_count
            
            # Грузы пользователей
            user_cargo_result = db.cargo.delete_many({"sender_id": {"$in": test_user_ids}})
            cleanup_report["user_cargo_deleted"] = user_cargo_result.deleted_count
            
            # Неоплаченные заказы
            unpaid_orders_result = db.unpaid_orders.delete_many({"client_id": {"$in": test_user_ids}})
            cleanup_report["unpaid_orders_deleted"] = unpaid_orders_result.deleted_count
            
            # Уведомления
            notifications_result = db.notifications.delete_many({"user_id": {"$in": test_user_ids}})
            cleanup_report["notifications_deleted"] = notifications_result.deleted_count
            
            # Удаляем самих тестовых пользователей (кроме текущего админа)
            users_to_delete = [uid for uid in test_user_ids if uid != current_user.id]
            if users_to_delete:
                users_result = db.users.delete_many({"id": {"$in": users_to_delete}})
                cleanup_report["users_deleted"] = users_result.deleted_count
            
            cleanup_report["details"].extend([f"User: {user['full_name']} ({user['phone']})" for user in test_users])
        
        # 2. Удаляем тестовые грузы по паттернам наименований
        test_cargo_patterns = [
            {"cargo_name": {"$regex": "[Tt]ест"}},
            {"cargo_name": {"$regex": "test", "$options": "i"}},
            {"description": {"$regex": "[Tt]ест"}},
            {"description": {"$regex": "test", "$options": "i"}},
            {"sender_full_name": {"$regex": "[Tt]ест"}},
            {"recipient_full_name": {"$regex": "[Tt]ест"}},
            {"sender_phone": {"$regex": "^\\+992900000000"}},
        ]
        
        # Удаляем тестовые грузы из operator_cargo
        test_operator_cargo_result = db.operator_cargo.delete_many({"$or": test_cargo_patterns})
        cleanup_report["operator_cargo_deleted"] += test_operator_cargo_result.deleted_count
        
        # Удаляем тестовые грузы из cargo
        test_user_cargo_result = db.cargo.delete_many({"$or": test_cargo_patterns})
        cleanup_report["user_cargo_deleted"] += test_user_cargo_result.deleted_count
        
        # 3. Удаляем тестовые заявки на грузы
        test_requests_result = db.cargo_requests.delete_many({"$or": test_cargo_patterns})
        cleanup_report["cargo_requests_deleted"] += test_requests_result.deleted_count
        
        # 4. Очищаем занятые ячейки тестовых грузов
        warehouse_cells_result = db.warehouse_cells.delete_many({"is_occupied": True})
        cleanup_report["warehouse_cells_deleted"] = warehouse_cells_result.deleted_count
        
        # 5. Удаляем системные уведомления связанные с тестовыми данными
        system_notifications_result = db.notifications.delete_many({
            "$or": [
                {"message": {"$regex": "[Tt]ест"}},
                {"message": {"$regex": "test", "$options": "i"}},
                {"entity_type": "test"}
            ]
        })
        cleanup_report["notifications_deleted"] += system_notifications_result.deleted_count
        
        # Создаем системное уведомление об очистке
        create_system_notification(
            "Очистка тестовых данных",
            f"Администратор {current_user.full_name} выполнил очистку тестовых данных",
            "system_cleanup",
            None,
            None,
            current_user.id
        )
        
        return {
            "message": "Test data cleanup completed successfully",
            "cleanup_report": cleanup_report,
            "cleaned_by": current_user.full_name,
            "cleanup_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")

# Управление грузами
@app.post("/api/cargo/create")
async def create_cargo(cargo_data: CargoCreate, current_user: User = Depends(get_current_user)):
    cargo_id = str(uuid.uuid4())
    cargo_number = generate_cargo_number()
    
    cargo = {
        "id": cargo_id,
        "cargo_number": cargo_number,
        "sender_id": current_user.id,
        "recipient_name": cargo_data.recipient_name,
        "recipient_phone": cargo_data.recipient_phone,
        "route": cargo_data.route,
        "weight": cargo_data.weight,
        "cargo_name": cargo_data.cargo_name or cargo_data.description[:50],  # Использовать описание как fallback
        "description": cargo_data.description,
        "declared_value": cargo_data.declared_value,
        "sender_address": cargo_data.sender_address,
        "recipient_address": cargo_data.recipient_address,
        "status": CargoStatus.CREATED,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "warehouse_location": None,
        "sender_full_name": current_user.full_name,  # Добавляем для QR кода
        "sender_phone": current_user.phone  # Добавляем для QR кода
    }
    
    # Генерируем QR код для груза
    cargo["qr_code"] = generate_cargo_qr_code_data(cargo)
    
    db.cargo.insert_one(cargo)
    
    # Создание уведомления
    create_notification(
        current_user.id,
        f"Создан новый груз {cargo_number}. Ожидает обработки.",
        cargo_id
    )
    
    return Cargo(**cargo)

@app.get("/api/operator/my-warehouses")
async def get_operator_warehouses_detailed(
    current_user: User = Depends(get_current_user)
):
    """Расширенный личный кабинет оператора - показать все склады и функции (Функция 2)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if current_user.role == UserRole.ADMIN:
        # Админ видит все склады
        warehouses = list(db.warehouses.find({"is_active": True}))
        is_admin = True
    else:
        # Оператор видит только привязанные склады
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        
        if not operator_warehouse_ids:
            return {"warehouses": [], "message": "No warehouses assigned to this operator"}
        
        warehouses = list(db.warehouses.find({
            "id": {"$in": operator_warehouse_ids}, 
            "is_active": True
        }))
        is_admin = False
    
    # Получаем расширенную статистику и функции по каждому складу
    warehouse_list = []
    for warehouse in warehouses:
        # Подсчитываем грузы на складе
        cargo_count_user = db.cargo.count_documents({"warehouse_id": warehouse["id"]})
        cargo_count_operator = db.operator_cargo.count_documents({"warehouse_id": warehouse["id"]})
        total_cargo = cargo_count_user + cargo_count_operator
        
        # Подсчитываем занятые ячейки
        occupied_cells = db.warehouse_cells.count_documents({
            "warehouse_id": warehouse["id"], 
            "is_occupied": True
        })
        
        total_cells = warehouse["blocks_count"] * warehouse["shelves_per_block"] * warehouse["cells_per_shelf"]
        
        # Подсчитываем транспорты связанные с этим складом
        related_transports = db.transports.count_documents({
            "$or": [
                {"destination_warehouse_id": warehouse["id"]},
                {"source_warehouse_id": warehouse["id"]},
                {"direction": {"$regex": warehouse["name"], "$options": "i"}}
            ]
        })
        
        # Подсчитываем грузы в разных статусах
        cargo_statuses = {}
        for status in ['accepted', 'placed_in_warehouse', 'on_transport', 'in_transit', 'arrived_destination', 'delivered']:
            count_user = db.cargo.count_documents({"warehouse_id": warehouse["id"], "status": status})
            count_operator = db.operator_cargo.count_documents({"warehouse_id": warehouse["id"], "status": status})
            cargo_statuses[status] = count_user + count_operator
        
        # Получаем список других операторов этого склада (для админов)
        bound_operators = []
        if is_admin:
            bindings = list(db.operator_warehouse_bindings.find({"warehouse_id": warehouse["id"]}))
            for binding in bindings:
                operator = db.users.find_one({"id": binding["operator_id"]}, {"password": 0})
                if operator:
                    bound_operators.append({
                        "id": operator["id"],
                        "full_name": operator["full_name"], 
                        "phone": operator["phone"],
                        "bound_at": binding["created_at"]
                    })
        
        warehouse_info = {
            "id": warehouse["id"],
            "name": warehouse["name"],
            "location": warehouse["location"],
            "blocks_count": warehouse["blocks_count"],
            "shelves_per_block": warehouse["shelves_per_block"],
            "cells_per_shelf": warehouse["cells_per_shelf"],
            "created_at": warehouse.get("created_at"),
            
            # Статистика ячеек
            "cells_info": {
                "total_cells": total_cells,
                "occupied_cells": occupied_cells,
                "free_cells": total_cells - occupied_cells,
                "occupancy_percentage": round((occupied_cells / total_cells) * 100, 1) if total_cells > 0 else 0
            },
            
            # Статистика грузов
            "cargo_info": {
                "total_cargo": total_cargo,
                "user_cargo": cargo_count_user,
                "operator_cargo": cargo_count_operator,
                "by_status": cargo_statuses
            },
            
            # Статистика транспортов
            "transport_info": {
                "related_transports": related_transports
            },
            
            # Доступные функции для этого склада
            "available_functions": {
                "accept_cargo": True,
                "place_cargo": True,
                "move_cargo_between_cells": True,
                "remove_cargo_from_cells": True,
                "view_warehouse_layout": True,
                "search_cargo": True,
                "create_transports": True,
                "manage_arrived_transports": True,
                "generate_qr_codes": True,
                "print_warehouse_reports": True
            },
            
            # Операторы привязанные к складу (только для админов)
            "bound_operators": bound_operators if is_admin else [],
            "operators_count": len(bound_operators) if is_admin else 0,
            
            # Персональная информация
            "is_admin": is_admin,
            "operator_permissions": "full_access" if is_admin else "warehouse_specific"
        }
        
        warehouse_list.append(warehouse_info)
    
    return {
        "warehouses": warehouse_list,
        "total_warehouses": len(warehouse_list),
        "user_role": current_user.role,
        "user_name": current_user.full_name,
        "summary": {
            "total_cargo_across_warehouses": sum(w["cargo_info"]["total_cargo"] for w in warehouse_list),
            "total_occupied_cells": sum(w["cells_info"]["occupied_cells"] for w in warehouse_list),
            "average_occupancy": round(sum(w["cells_info"]["occupancy_percentage"] for w in warehouse_list) / len(warehouse_list), 1) if warehouse_list else 0
        }
    }

@app.get("/api/cargo/my")
async def get_my_cargo(current_user: User = Depends(get_current_user)):
    # Search in both collections for user's cargo
    user_cargo_list = list(db.cargo.find({"sender_id": current_user.id}))
    
    # Normalize cargo data
    normalized_cargo = []
    for cargo in user_cargo_list:
        normalized = serialize_mongo_document(cargo)
        # Ensure all required fields exist
        normalized.update({
            'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
            'sender_id': cargo.get('sender_id', current_user.id),
            'recipient_name': cargo.get('recipient_name', 'Не указан'),
            'sender_address': cargo.get('sender_address', 'Не указан'),
            'recipient_address': cargo.get('recipient_address', 'Не указан'),
            'recipient_phone': cargo.get('recipient_phone', 'Не указан')
        })
        normalized_cargo.append(normalized)
    
    return normalized_cargo

@app.get("/api/cargo/track/{cargo_number}")
async def track_cargo(cargo_number: str):
    # ИСПРАВЛЕНИЕ: Улучшенный поиск грузов с поддержкой различных форматов номеров
    
    # Создаем список возможных вариантов поиска
    search_patterns = [cargo_number]
    
    # Если это JSON данные - извлекаем номера
    if cargo_number.startswith('{') and cargo_number.endswith('}'):
        try:
            json_data = json.loads(cargo_number)
            if 'cargo_number' in json_data:
                search_patterns.append(json_data['cargo_number'])
            if 'request_number' in json_data:
                search_patterns.append(json_data['request_number'])
        except:
            pass
    
    # Поиск в коллекции operator_cargo (приоритетный - для размещения)
    cargo = None
    for pattern in search_patterns:
        # Точное совпадение
        cargo = db.operator_cargo.find_one({"cargo_number": pattern})
        if cargo:
            break
            
        # Поиск по ID
        cargo = db.operator_cargo.find_one({"id": pattern})
        if cargo:
            break
            
        # Поиск по номеру заявки
        cargo = db.operator_cargo.find_one({"request_number": pattern})
        if cargo:
            break
    
    # Если не найдено в operator_cargo, ищем в cargo
    if not cargo:
        for pattern in search_patterns:
            cargo = db.cargo.find_one({"cargo_number": pattern})
            if cargo:
                break
                
            cargo = db.cargo.find_one({"id": pattern})  
            if cargo:
                break
    
    if not cargo:
        raise HTTPException(status_code=404, detail=f"Cargo not found with patterns: {search_patterns}")
    
    # Normalize cargo data
    normalized = serialize_mongo_document(cargo)
    # Ensure all required fields exist
    normalized.update({
        'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
        'sender_id': cargo.get('sender_id', cargo.get('created_by', 'unknown')),
        'recipient_name': cargo.get('recipient_name', cargo.get('recipient_full_name', 'Не указан')),
        'sender_address': cargo.get('sender_address', 'Не указан'),
        'recipient_address': cargo.get('recipient_address', 'Не указан'),
        'recipient_phone': cargo.get('recipient_phone', 'Не указан')
    })
    
    return normalized

@app.get("/api/cargo/all")
async def get_all_cargo(current_user: User = Depends(require_role(UserRole.ADMIN))):
    # Get cargo from both collections
    user_cargo_list = list(db.cargo.find({}))
    operator_cargo_list = list(db.operator_cargo.find({}))
    
    # Normalize and serialize all cargo data
    normalized_cargo = []
    
    # Process user cargo
    for cargo in user_cargo_list:
        normalized = serialize_mongo_document(cargo)
        # Ensure all required fields exist
        normalized.update({
            'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
            'sender_id': cargo.get('sender_id', 'unknown'),
            'recipient_name': cargo.get('recipient_name', 'Не указан'),
            'sender_address': cargo.get('sender_address', 'Не указан'),
            'recipient_address': cargo.get('recipient_address', 'Не указан'),
            'recipient_phone': cargo.get('recipient_phone', 'Не указан')
        })
        normalized_cargo.append(normalized)
    
    # Process operator cargo
    for cargo in operator_cargo_list:
        normalized = serialize_mongo_document(cargo)
        # Map operator cargo fields to standard cargo fields
        normalized.update({
            'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
            'sender_id': cargo.get('created_by', 'operator'),
            'recipient_name': cargo.get('recipient_full_name', cargo.get('recipient_name', 'Не указан')),
            'sender_address': cargo.get('sender_address', 'Не указан'),
            'recipient_address': cargo.get('recipient_address', 'Не указан'),
            'recipient_phone': cargo.get('recipient_phone', 'Не указан')
        })
        normalized_cargo.append(normalized)
    
    return normalized_cargo


@app.put("/api/cargo/{cargo_id}/processing-status")
async def update_cargo_processing_status(
    cargo_id: str, 
    status_update: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновление статуса обработки груза"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для изменения статуса груза"
        )
    
    try:
        # Принимаем как new_status (старый формат), так и processing_status (новый формат)
        new_status = status_update.get('new_status') or status_update.get('processing_status')
        
        if not new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Укажите новый статус (new_status или processing_status)"
            )
        
        # Обновляем в обеих коллекциях
        update_result_operator = db.operator_cargo.update_one(
            {"id": cargo_id},
            {"$set": {
                "processing_status": new_status,
                "updated_at": datetime.utcnow(),
                "updated_by": current_user.full_name
            }}
        )
        
        update_result_user = db.cargo.update_one(
            {"id": cargo_id},
            {"$set": {
                "processing_status": new_status,
                "updated_at": datetime.utcnow(),
                "updated_by": current_user.full_name
            }}
        )
        
        if update_result_operator.matched_count == 0 and update_result_user.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Груз не найден"
            )
        
        return {"message": f"Статус груза обновлен на {new_status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления статуса груза: {str(e)}"
        )

@app.put("/api/cargo/{cargo_id}/status")
async def update_cargo_status(
    cargo_id: str, 
    status: CargoStatus,
    warehouse_location: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    cargo = db.cargo.find_one({"id": cargo_id})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow()
    }
    
    if warehouse_location:
        update_data["warehouse_location"] = warehouse_location
    
    db.cargo.update_one({"id": cargo_id}, {"$set": update_data})
    
    # Создание уведомления для отправителя
    status_messages = {
        CargoStatus.ACCEPTED: "принят на склад",
        CargoStatus.IN_TRANSIT: "в пути",
        CargoStatus.ARRIVED_DESTINATION: "прибыл в пункт назначения",
        CargoStatus.COMPLETED: "доставлен получателю"
    }
    
    message = f"Статус груза {cargo['cargo_number']} изменен: {status_messages.get(status, status)}"
    create_notification(cargo["sender_id"], message, cargo_id)
    
    return {"message": "Status updated successfully"}

# Склад
@app.get("/api/warehouse/cargo")
async def get_warehouse_cargo(current_user: User = Depends(require_role(UserRole.WAREHOUSE_OPERATOR))):
    # Search both user cargo and operator cargo collections
    user_cargo_list = list(db.cargo.find({
        "status": {"$in": [CargoStatus.CREATED, CargoStatus.ACCEPTED, CargoStatus.IN_TRANSIT]}
    }))
    
    operator_cargo_list = list(db.operator_cargo.find({
        "status": {"$in": [CargoStatus.CREATED, CargoStatus.ACCEPTED, CargoStatus.IN_TRANSIT]}
    }))
    
    # Normalize and serialize all cargo data
    normalized_cargo = []
    
    # Process user cargo
    for cargo in user_cargo_list:
        normalized = serialize_mongo_document(cargo)
        # Ensure all required fields exist
        normalized.update({
            'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
            'sender_id': cargo.get('sender_id', 'unknown'),
            'recipient_name': cargo.get('recipient_name', 'Не указан'),
            'sender_address': cargo.get('sender_address', 'Не указан'),
            'recipient_address': cargo.get('recipient_address', 'Не указан'),
            'recipient_phone': cargo.get('recipient_phone', 'Не указан')
        })
        normalized_cargo.append(normalized)
    
    # Process operator cargo
    for cargo in operator_cargo_list:
        normalized = serialize_mongo_document(cargo)
        # Map operator cargo fields to standard cargo fields and ensure all required fields exist
        normalized.update({
            'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
            'sender_id': cargo.get('created_by', 'operator'),
            'recipient_name': cargo.get('recipient_full_name', cargo.get('recipient_name', 'Не указан')),
            'sender_address': cargo.get('sender_address', 'Не указан'),
            'recipient_address': cargo.get('recipient_address', 'Не указан'),
            'recipient_phone': cargo.get('recipient_phone', 'Не указан')
        })
        normalized_cargo.append(normalized)
    
    return normalized_cargo

@app.get("/api/warehouse/search")
async def search_cargo(
    query: str,
    current_user: User = Depends(require_role(UserRole.WAREHOUSE_OPERATOR))
):
    # Search in both collections
    user_cargo_list = list(db.cargo.find({
        "$or": [
            {"cargo_number": {"$regex": query, "$options": "i"}},
            {"recipient_name": {"$regex": query, "$options": "i"}}
        ]
    }))
    
    operator_cargo_list = list(db.operator_cargo.find({
        "$or": [
            {"cargo_number": {"$regex": query, "$options": "i"}},
            {"recipient_name": {"$regex": query, "$options": "i"}},
            {"recipient_full_name": {"$regex": query, "$options": "i"}}
        ]
    }))
    
    # Normalize all cargo data
    normalized_cargo = []
    
    # Process user cargo
    for cargo in user_cargo_list:
        normalized = serialize_mongo_document(cargo)
        normalized.update({
            'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
            'sender_id': cargo.get('sender_id', 'unknown'),
            'recipient_name': cargo.get('recipient_name', 'Не указан'),
            'sender_address': cargo.get('sender_address', 'Не указан'),
            'recipient_address': cargo.get('recipient_address', 'Не указан'),
            'recipient_phone': cargo.get('recipient_phone', 'Не указан')
        })
        normalized_cargo.append(normalized)
    
    # Process operator cargo
    for cargo in operator_cargo_list:
        normalized = serialize_mongo_document(cargo)
        normalized.update({
            'cargo_name': cargo.get('cargo_name') or cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз',
            'sender_id': cargo.get('created_by', 'operator'),
            'recipient_name': cargo.get('recipient_full_name', cargo.get('recipient_name', 'Не указан')),
            'sender_address': cargo.get('sender_address', 'Не указан'),
            'recipient_address': cargo.get('recipient_address', 'Не указан'),
            'recipient_phone': cargo.get('recipient_phone', 'Не указан')
        })
        normalized_cargo.append(normalized)
    
    return normalized_cargo

# Администрирование
@app.get("/api/admin/users")
async def get_all_users(
    page: int = 1,
    per_page: int = 25,
    role: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Получить список всех пользователей с пагинацией и фильтрацией"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Валидация параметров пагинации
    pagination = PaginationParams(page=page, per_page=per_page)
    
    # Базовый запрос
    query = {}
    
    # Фильтр по роли
    if role:
        query["role"] = role
    
    # Поиск по имени, телефону или email
    if search:
        escaped_search = escape_regex_special_chars(search)
        search_pattern = {"$regex": escaped_search, "$options": "i"}
        query["$or"] = [
            {"full_name": search_pattern},
            {"phone": search_pattern},
            {"email": search_pattern}
        ]
    
    # Получаем пользователей с пагинацией
    users_cursor = db.users.find(query).sort("created_at", -1)
    total_count = db.users.count_documents(query)
    
    # Применяем пагинацию
    skip = (pagination.page - 1) * pagination.per_page
    users_list = list(users_cursor.skip(skip).limit(pagination.per_page))
    
    # Нормализуем данные (убираем пароли)
    normalized_users = []
    for user in users_list:
        normalized = serialize_mongo_document(user)
        # Удаляем чувствительные данные
        normalized.pop('password', None)
        normalized.pop('hashed_password', None)
        
        # Добавляем дополнительную информацию
        if user.get('role') == UserRole.WAREHOUSE_OPERATOR.value:
            # Получаем привязанные склады для операторов
            warehouses_binding = list(db.operator_warehouse_bindings.find({"operator_id": user["id"]}))
            warehouse_ids = [binding["warehouse_id"] for binding in warehouses_binding]
            warehouses = list(db.warehouses.find({"id": {"$in": warehouse_ids}}))
            normalized["warehouses"] = [serialize_mongo_document(warehouse) for warehouse in warehouses]
            normalized["warehouses_count"] = len(warehouses)
        else:
            normalized["warehouses"] = []
            normalized["warehouses_count"] = 0
        
        normalized_users.append(normalized)
    
    return create_pagination_response(
        normalized_users,
        total_count,
        pagination.page,
        pagination.per_page
    )

@app.put("/api/admin/users/{user_id}/status")
async def toggle_user_status(
    user_id: str,
    is_active: bool,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    result = db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": is_active}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User status updated successfully"}

@app.delete("/api/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}

@app.put("/api/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Обновить роль пользователя (только для админов)"""
    # Проверяем, что пользователь не пытается изменить свою роль
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    # Проверяем существование пользователя
    user = db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверяем, что новая роль отличается от текущей
    if user["role"] == role_data.new_role.value:
        raise HTTPException(status_code=400, detail="User already has this role")
    
    # Обновляем роль
    result = db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "role": role_data.new_role.value,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Failed to update user role")
    
    # Получаем обновленного пользователя для возврата
    updated_user = db.users.find_one({"id": user_id})
    
    return {
        "message": "User role updated successfully",
        "user": {
            "id": updated_user["id"],
            "user_number": updated_user.get("user_number", "N/A"),
            "full_name": updated_user["full_name"],
            "phone": updated_user["phone"],
            "role": updated_user["role"],
            "previous_role": user["role"]
        }
    }

# Модель для полного редактирования пользователя админом
class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

@app.put("/api/admin/users/{user_id}/update")
async def admin_update_user(
    user_id: str,
    user_update: AdminUserUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Admin endpoint to fully update user information"""
    # Проверяем, что пользователь существует
    existing_user = db.users.find_one({"id": user_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {}
    
    # Собираем только заполненные поля
    if user_update.full_name is not None:
        update_data["full_name"] = user_update.full_name
        
    if user_update.phone is not None:
        # Проверяем, не занят ли номер телефона другим пользователем
        existing_phone_user = db.users.find_one({"phone": user_update.phone, "id": {"$ne": user_id}})
        if existing_phone_user:
            raise HTTPException(status_code=400, detail="Этот номер телефона уже используется другим пользователем")
        update_data["phone"] = user_update.phone
        
    if user_update.email is not None:
        # Проверяем, не занят ли email другим пользователем
        existing_email_user = db.users.find_one({"email": user_update.email, "id": {"$ne": user_id}})
        if existing_email_user:
            raise HTTPException(status_code=400, detail="Этот email уже используется другим пользователем")
        update_data["email"] = user_update.email
        
    if user_update.address is not None:
        update_data["address"] = user_update.address
        
    if user_update.role is not None:
        update_data["role"] = user_update.role.value
        
    if user_update.is_active is not None:
        update_data["is_active"] = user_update.is_active
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    
    # Увеличиваем версию токена при изменении критических данных админом
    # Критические изменения: phone, role, is_active
    if any(field in update_data for field in ['phone', 'role', 'is_active']):
        current_token_version = existing_user.get("token_version", 1)
        update_data["token_version"] = current_token_version + 1
    
    # Обновляем пользователя в базе данных
    update_data["updated_at"] = datetime.utcnow()
    result = db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Не удалось обновить пользователя")
    
    # Получаем обновленные данные пользователя
    updated_user = db.users.find_one({"id": user_id})
    if not updated_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return {
        "message": "Данные пользователя обновлены успешно",
        "user": User(
            id=updated_user["id"],
            user_number=updated_user.get("user_number"),
            full_name=updated_user["full_name"],
            phone=updated_user["phone"],
            role=updated_user["role"],
            email=updated_user.get("email"),
            address=updated_user.get("address"),
            is_active=updated_user["is_active"],
            token_version=updated_user.get("token_version", 1),
            created_at=updated_user["created_at"]
        )
    }

@app.get("/api/admin/operators/profile/{operator_id}")
async def get_operator_profile(
    operator_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Получить детальный профиль оператора склада"""
    try:
        # Получаем данные оператора
        operator = db.users.find_one({"id": operator_id, "role": "warehouse_operator"})
        if not operator:
            raise HTTPException(status_code=404, detail="Operator not found")
        
        # Создаем объект User
        operator_user = User(
            id=operator["id"],
            user_number=operator.get("user_number", "N/A"),
            full_name=operator["full_name"],
            phone=operator["phone"],
            role=operator["role"],
            is_active=operator["is_active"],
            created_at=operator["created_at"]
        )
        
        # Статистика работы
        total_cargo_accepted = db.operator_cargo.count_documents({"created_by": operator_id})
        
        # Статистика по периодам (последние 30 дней)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_cargo_count = db.operator_cargo.count_documents({
            "created_by": operator_id,
            "created_at": {"$gte": thirty_days_ago}
        })
        
        # Статистика по статусам
        status_stats = {}
        for status in ["payment_pending", "paid", "ready_for_placement", "placed"]:
            count = db.operator_cargo.count_documents({
                "created_by": operator_id,
                "processing_status": status
            })
            status_stats[status] = count
        
        work_statistics = {
            "total_cargo_accepted": total_cargo_accepted,
            "recent_cargo_count": recent_cargo_count,
            "status_breakdown": status_stats,
            "avg_cargo_per_day": round(recent_cargo_count / 30, 1) if recent_cargo_count > 0 else 0
        }
        
        # История принятых грузов (последние 20)
        cargo_history = list(db.operator_cargo.find(
            {"created_by": operator_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(20))
        
        # Связанные склады
        warehouse_bindings = list(db.operator_warehouse_bindings.find(
            {"operator_id": operator_id},
            {"_id": 0}
        ))
        
        associated_warehouses = []
        for binding in warehouse_bindings:
            warehouse = db.warehouses.find_one({"id": binding["warehouse_id"]})
            if warehouse:
                cargo_count = db.operator_cargo.count_documents({
                    "created_by": operator_id,
                    "target_warehouse_id": warehouse["id"]
                })
                associated_warehouses.append({
                    "id": warehouse["id"],
                    "name": warehouse["name"],
                    "location": warehouse.get("location", "Не указано"),
                    "cargo_count": cargo_count,
                    "binding_date": binding.get("created_at")
                })
        
        # Последняя активность (последние 10 действий)
        recent_activity = list(db.operator_cargo.find(
            {"created_by": operator_id},
            {
                "cargo_number": 1,
                "cargo_name": 1,
                "sender_full_name": 1,
                "created_at": 1,
                "processing_status": 1,
                "_id": 0
            }
        ).sort("created_at", -1).limit(10))
        
        return OperatorProfile(
            user_info=operator_user,
            work_statistics=work_statistics,
            cargo_history=cargo_history,
            associated_warehouses=associated_warehouses,
            recent_activity=recent_activity
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving operator profile: {str(e)}")

@app.get("/api/admin/users/profile/{user_id}")
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Получить детальный профиль пользователя"""
    try:
        # Получаем данные пользователя
        user = db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Создаем объект User
        user_obj = User(
            id=user["id"],
            user_number=user.get("user_number", "N/A"),
            full_name=user["full_name"],
            phone=user["phone"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"]
        )
        
        # Статистика отправлений
        total_cargo_requests = db.cargo_requests.count_documents({"created_by": user_id})
        total_sent_cargo = (
            db.cargo.count_documents({"sender_phone": user["phone"]}) +
            db.operator_cargo.count_documents({"sender_phone": user["phone"]})
        )
        total_received_cargo = (
            db.cargo.count_documents({"recipient_phone": user["phone"]}) +
            db.operator_cargo.count_documents({"recipient_phone": user["phone"]})
        )
        
        # Статистика по статусам
        cargo_status_stats = {}
        for collection_name in ["cargo", "operator_cargo"]:
            collection = getattr(db, collection_name)
            statuses = collection.aggregate([
                {"$match": {"sender_phone": user["phone"]}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ])
            for status_doc in statuses:
                status = status_doc["_id"]
                count = status_doc["count"]
                cargo_status_stats[status] = cargo_status_stats.get(status, 0) + count
        
        shipping_statistics = {
            "total_cargo_requests": total_cargo_requests,
            "total_sent_cargo": total_sent_cargo,
            "total_received_cargo": total_received_cargo,
            "status_breakdown": cargo_status_stats,
            "registration_days": (datetime.utcnow() - user["created_at"]).days
        }
        
        # Последние отправления (из обеих коллекций)
        recent_shipments = []
        
        # Из коллекции operator_cargo
        operator_shipments = list(db.operator_cargo.find(
            {"sender_phone": user["phone"]},
            {"_id": 0}
        ).sort("created_at", -1).limit(10))
        
        for shipment in operator_shipments:
            shipment["collection_type"] = "operator_cargo"
            recent_shipments.append(shipment)
        
        # Из коллекции cargo
        user_shipments = list(db.cargo.find(
            {"sender_phone": user["phone"]},
            {"_id": 0}
        ).sort("created_at", -1).limit(10))
        
        for shipment in user_shipments:
            shipment["collection_type"] = "cargo"
            recent_shipments.append(shipment)
        
        # Сортируем по дате
        recent_shipments.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        recent_shipments = recent_shipments[:15]  # Ограничиваем до 15
        
        # Часто используемые получатели
        frequent_recipients = []
        
        # Собираем статистику по получателям из обеих коллекций
        recipient_stats = {}
        
        for collection_name in ["cargo", "operator_cargo"]:
            collection = getattr(db, collection_name)
            recipients = collection.aggregate([
                {"$match": {"sender_phone": user["phone"]}},
                {"$group": {
                    "_id": {
                        "name": "$recipient_full_name",
                        "phone": "$recipient_phone",
                        "address": "$recipient_address"
                    },
                    "count": {"$sum": 1},
                    "last_sent": {"$max": "$created_at"},
                    "total_weight": {"$sum": "$weight"},
                    "total_value": {"$sum": "$declared_value"}
                }}
            ])
            
            for recipient in recipients:
                key = f"{recipient['_id']['name']}_{recipient['_id']['phone']}"
                if key not in recipient_stats:
                    recipient_stats[key] = {
                        "recipient_full_name": recipient["_id"]["name"],
                        "recipient_phone": recipient["_id"]["phone"],
                        "recipient_address": recipient["_id"]["address"],
                        "shipment_count": 0,
                        "last_sent": None,
                        "total_weight": 0,
                        "total_value": 0
                    }
                
                recipient_stats[key]["shipment_count"] += recipient["count"]
                recipient_stats[key]["total_weight"] += recipient.get("total_weight", 0)
                recipient_stats[key]["total_value"] += recipient.get("total_value", 0)
                
                if not recipient_stats[key]["last_sent"] or recipient["last_sent"] > recipient_stats[key]["last_sent"]:
                    recipient_stats[key]["last_sent"] = recipient["last_sent"]
        
        # Сортируем по количеству отправлений
        frequent_recipients = sorted(
            recipient_stats.values(),
            key=lambda x: x["shipment_count"],
            reverse=True
        )[:10]
        
        # История заявок
        cargo_requests_history = list(db.cargo_requests.find(
            {"created_by": user_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(15))
        
        return UserProfile(
            user_info=user_obj,
            shipping_statistics=shipping_statistics,
            recent_shipments=recent_shipments,
            frequent_recipients=frequent_recipients,
            cargo_requests_history=cargo_requests_history
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile: {str(e)}")

@app.post("/api/admin/users/{user_id}/quick-cargo")
async def create_quick_cargo_for_user(
    user_id: str,
    cargo_request: QuickCargoRequest,
    current_user: User = Depends(require_role(UserRole.WAREHOUSE_OPERATOR))
):
    """Быстрое создание груза для пользователя с автозаполнением"""
    try:
        # Получаем данные отправителя
        sender = db.users.find_one({"id": user_id})
        if not sender:
            raise HTTPException(status_code=404, detail="Sender not found")
        
        # Проверяем роль текущего пользователя
        if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
            raise HTTPException(status_code=403, detail="Only operators can create cargo")
        
        # Находим целевой склад для оператора
        warehouse_binding = db.operator_warehouse_bindings.find_one({"operator_id": current_user.id})
        if not warehouse_binding:
            raise HTTPException(status_code=400, detail="Operator not assigned to any warehouse")
        
        target_warehouse_id = warehouse_binding["warehouse_id"]
        warehouse = db.warehouses.find_one({"id": target_warehouse_id})
        
        # Вычисляем общий вес и стоимость
        total_weight = sum(item.weight for item in cargo_request.cargo_items)
        total_cost = sum(item.total_cost for item in cargo_request.cargo_items)
        
        # Создаем объединенное название груза
        cargo_names = [item.cargo_name for item in cargo_request.cargo_items]
        combined_cargo_name = ", ".join(cargo_names)
        
        # Детальная информация о грузах
        cargo_details = []
        for i, item in enumerate(cargo_request.cargo_items, 1):
            item_cost = item.weight * item.price_per_kg
            cargo_details.append(f"{i}. {item.cargo_name} - {item.weight} кг × {item.price_per_kg} руб/кг = {item_cost} руб")
        
        detailed_description = f"{cargo_request.description}\n\nДетальный расчет по грузам:\n" + "\n".join(cargo_details)
        detailed_description += f"\n\nИТОГО:"
        detailed_description += f"\nОбщий вес: {total_weight} кг"
        detailed_description += f"\nОбщая стоимость: {total_cost} руб"
        detailed_description += f"\n\nСоздано через быстрое оформление из профиля пользователя"
        
        # Создаем груз
        cargo_id = str(uuid.uuid4())
        cargo_number = generate_cargo_number()
        
        cargo = {
            "id": cargo_id,
            "cargo_number": cargo_number,
            "sender_full_name": sender["full_name"],
            "sender_phone": sender["phone"],
            "recipient_full_name": cargo_request.recipient_data.get("recipient_full_name"),
            "recipient_phone": cargo_request.recipient_data.get("recipient_phone"),
            "recipient_address": cargo_request.recipient_data.get("recipient_address"),
            "weight": total_weight,
            "cargo_name": combined_cargo_name,
            "declared_value": total_cost,
            "description": detailed_description,
            "route": cargo_request.route,
            "status": CargoStatus.ACCEPTED,
            "payment_status": "pending",
            "processing_status": "payment_pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.id,
            "created_by_operator": current_user.full_name,
            "target_warehouse_id": target_warehouse_id,
            "target_warehouse_name": warehouse.get("name") if warehouse else None,
            "warehouse_location": None,
            "warehouse_id": None,
            "block_number": None,
            "shelf_number": None,
            "cell_number": None,
            "placed_by_operator": None,
            "placed_by_operator_id": None,
            "cargo_items": [item.dict() for item in cargo_request.cargo_items],
            "quick_created": True,  # Маркер быстрого создания
            "sender_id": user_id  # ID отправителя для связи
        }
        
        # Сохраняем груз
        db.operator_cargo.insert_one(cargo)
        
        return {
            "success": True,
            "message": "Груз успешно создан из профиля пользователя",
            "cargo": {
                "id": cargo_id,
                "cargo_number": cargo_number,
                "sender_name": sender["full_name"],
                "recipient_name": cargo_request.recipient_data.get("recipient_full_name"),
                "total_weight": total_weight,
                "total_cost": total_cost,
                "items_count": len(cargo_request.cargo_items)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating quick cargo: {str(e)}")

# Уведомления
@app.get("/api/notifications")
async def get_notifications(current_user: User = Depends(get_current_user)):
    notifications = list(db.notifications.find({"user_id": current_user.id}).sort("created_at", -1))
    return [Notification(**notification) for notification in notifications]

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    result = db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}

# Управление складами
@app.post("/api/warehouses/create")
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    warehouse_id = str(uuid.uuid4())
    
    # Генерируем ID номер склада
    warehouse_id_number = generate_warehouse_id_number()
    
    # Рассчитываем общую вместимость
    total_capacity = warehouse_data.blocks_count * warehouse_data.shelves_per_block * warehouse_data.cells_per_shelf
    
    warehouse = {
        "id": warehouse_id,
        "warehouse_id_number": warehouse_id_number,  # Новое поле
        "name": warehouse_data.name,
        "location": warehouse_data.location,
        "address": warehouse_data.address,  # НОВОЕ: Полный адрес для навигации
        "blocks_count": warehouse_data.blocks_count,
        "shelves_per_block": warehouse_data.shelves_per_block,
        "cells_per_shelf": warehouse_data.cells_per_shelf,
        "total_capacity": total_capacity,
        "created_by": current_user.id,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    # Создаем склад
    db.warehouses.insert_one(warehouse)
    
    # Генерируем структуру склада (блоки, полки, ячейки) с ID номерами
    cells_created = generate_warehouse_structure(
        warehouse_id,
        warehouse_id_number,  # Передаем ID номер склада
        warehouse_data.blocks_count,
        warehouse_data.shelves_per_block,
        warehouse_data.cells_per_shelf
    )
    
    # Создаем уведомление
    create_notification(
        current_user.id,
        f"Создан новый склад '{warehouse_data.name}' (ID: {warehouse_id_number}) с {cells_created} ячейками",
        None
    )
    
    return Warehouse(
        id=warehouse_id,
        warehouse_id_number=warehouse_id_number,
        name=warehouse_data.name,
        location=warehouse_data.location,
        blocks_count=warehouse_data.blocks_count,
        shelves_per_block=warehouse_data.shelves_per_block,
        cells_per_shelf=warehouse_data.cells_per_shelf,
        total_capacity=total_capacity,
        created_by=current_user.id,
        created_at=warehouse["created_at"],
        is_active=True
    )

@app.get("/api/warehouses")
async def get_warehouses(current_user: User = Depends(get_current_user)):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if current_user.role == UserRole.ADMIN:
        # Админ видит все склады
        warehouses = list(db.warehouses.find({"is_active": True}))
    else:
        # Оператор видит только склады, к которым он привязан
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        if not operator_warehouse_ids:
            # Если оператор не привязан ни к одному складу, возвращаем пустой список
            return []
        
        warehouses = list(db.warehouses.find({
            "id": {"$in": operator_warehouse_ids}, 
            "is_active": True
        }))
    
    # Добавляем информацию о привязанных операторах к каждому складу
    warehouses_with_operators = []
    for warehouse in warehouses:
        # Получаем операторов, привязанных к этому складу
        bindings = list(db.operator_warehouse_bindings.find({"warehouse_id": warehouse["id"]}))
        
        # Получаем информацию об операторах
        bound_operators = []
        for binding in bindings:
            operator = db.users.find_one({"id": binding["operator_id"]}, {"password": 0, "_id": 0})
            if operator:
                bound_operators.append({
                    "id": operator["id"],
                    "full_name": operator["full_name"],
                    "phone": operator["phone"],
                    "bound_at": binding["created_at"]
                })
        
        # Добавляем информацию об операторах к складу
        warehouse_with_operators = {
            **warehouse,
            "bound_operators": bound_operators,
            "operators_count": len(bound_operators)
        }
        warehouses_with_operators.append(warehouse_with_operators)
    
    # Сериализуем все MongoDB ObjectId перед возвратом
    return serialize_mongo_document(warehouses_with_operators)

@app.get("/api/warehouses/{warehouse_id}/structure")
async def get_warehouse_structure(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем существование склада
    warehouse = db.warehouses.find_one({"id": warehouse_id, "is_active": True})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Получаем все ячейки склада
    cells = list(db.warehouse_cells.find({"warehouse_id": warehouse_id}))
    
    # Группируем ячейки по блокам и полкам
    structure = {}
    for cell in cells:
        block_key = f"block_{cell['block_number']}"
        shelf_key = f"shelf_{cell['shelf_number']}"
        
        if block_key not in structure:
            structure[block_key] = {}
        if shelf_key not in structure[block_key]:
            structure[block_key][shelf_key] = []
        
        structure[block_key][shelf_key].append({
            "cell_id": cell["id"],
            "cell_number": cell["cell_number"],
            "location_code": cell["location_code"],
            "is_occupied": cell["is_occupied"],
            "cargo_id": cell.get("cargo_id")
        })
    
    return {
        "warehouse": Warehouse(**warehouse),
        "structure": structure,
        "total_cells": len(cells),
        "occupied_cells": len([c for c in cells if c["is_occupied"]]),
        "available_cells": len([c for c in cells if not c["is_occupied"]])
    }

@app.put("/api/warehouses/{warehouse_id}/assign-cargo")
async def assign_cargo_to_cell(
    warehouse_id: str,
    cargo_id: str,
    cell_location_code: str,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем существование груза
    cargo = db.cargo.find_one({"id": cargo_id})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Находим ячейку по location_code
    cell = db.warehouse_cells.find_one({
        "warehouse_id": warehouse_id,
        "location_code": cell_location_code,
        "is_occupied": False
    })
    
    if not cell:
        raise HTTPException(status_code=400, detail="Cell not found or already occupied")
    
    # Обновляем ячейку
    db.warehouse_cells.update_one(
        {"id": cell["id"]},
        {"$set": {"is_occupied": True, "cargo_id": cargo_id}}
    )
    
    # Обновляем груз
    db.cargo.update_one(
        {"id": cargo_id},
        {"$set": {
            "warehouse_location": cell_location_code, 
            "updated_at": datetime.utcnow(),
            "placed_by_operator": current_user.full_name,
            "placed_by_operator_id": current_user.id
        }}
    )
    
    # Создаем уведомление для отправителя
    create_notification(
        cargo["sender_id"],
        f"Груз {cargo['cargo_number']} размещен на складе в ячейке {cell_location_code}",
        cargo_id
    )
    
    return {"message": "Cargo assigned to cell successfully", "location": cell_location_code}

@app.delete("/api/warehouses/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    # Проверяем, есть ли грузы в этом складе
    occupied_cells = db.warehouse_cells.find_one({"warehouse_id": warehouse_id, "is_occupied": True})
    if occupied_cells:
        raise HTTPException(status_code=400, detail="Cannot delete warehouse with occupied cells")
    
    # Помечаем склад как неактивный
    result = db.warehouses.update_one(
        {"id": warehouse_id},
        {"$set": {"is_active": False}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    return {"message": "Warehouse deleted successfully"}

# Управление грузами для операторов
@app.post("/api/operator/cargo/accept")
async def accept_new_cargo(
    cargo_data: OperatorCargoCreate,
    current_user: User = Depends(get_current_user)
):
    """Принять новый груз оператором (1.4 - только на привязанные склады)"""
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Для операторов проверяем привязки к складам и выбор склада
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        if not operator_warehouse_ids:
            raise HTTPException(status_code=403, detail="No warehouses assigned to this operator. Cannot accept cargo.")
        
        # НОВАЯ ЛОГИКА: Проверяем выбранный склад или автовыбор
        if cargo_data.warehouse_id:
            # Проверяем что выбранный склад принадлежит оператору
            if cargo_data.warehouse_id not in operator_warehouse_ids:
                raise HTTPException(status_code=403, detail="Selected warehouse is not assigned to this operator")
            target_warehouse_id = cargo_data.warehouse_id
        else:
            # Автоматически выбираем первый привязанный склад
            target_warehouse_id = operator_warehouse_ids[0]
        
        warehouse = db.warehouses.find_one({"id": target_warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Target warehouse not found")
    else:
        # Админ может принимать грузы на любой склад
        if cargo_data.warehouse_id:
            warehouse = db.warehouses.find_one({"id": cargo_data.warehouse_id, "is_active": True})
            if not warehouse:
                raise HTTPException(status_code=404, detail="Selected warehouse not found")
            target_warehouse_id = cargo_data.warehouse_id
        else:
            # Выбираем первый доступный склад
            all_warehouses = list(db.warehouses.find({"is_active": True}))
            if all_warehouses:
                target_warehouse_id = all_warehouses[0]["id"]
                warehouse = all_warehouses[0]
            else:
                raise HTTPException(status_code=400, detail="No active warehouses available for cargo acceptance")
    
    cargo_id = str(uuid.uuid4())
    cargo_number = generate_cargo_number()
    
    # Обрабатываем множественные грузы с индивидуальными ценами или одиночный груз для совместимости
    if cargo_data.cargo_items and len(cargo_data.cargo_items) > 0:
        # Новый режим с множественными грузами и индивидуальными ценами
        total_weight = sum(item.weight for item in cargo_data.cargo_items)
        total_cost = sum(item.total_cost for item in cargo_data.cargo_items)  # Сумма индивидуальных стоимостей
        
        # Создаем объединенное название груза
        cargo_names = [item.cargo_name for item in cargo_data.cargo_items]
        combined_cargo_name = ", ".join(cargo_names)
        
        # Сохраняем подробную информацию о каждом грузе с индивидуальными ценами
        cargo_details = []
        for i, item in enumerate(cargo_data.cargo_items, 1):
            item_cost = item.weight * item.price_per_kg
            cargo_details.append(f"{i}. {item.cargo_name} - {item.weight} кг × {item.price_per_kg} руб/кг = {item_cost} руб")
        
        detailed_description = f"{cargo_data.description}\n\nДетальный расчет по грузам:\n" + "\n".join(cargo_details)
        detailed_description += f"\n\nИТОГО:"
        detailed_description += f"\nОбщий вес: {total_weight} кг"
        detailed_description += f"\nОбщая стоимость: {total_cost} руб"
        
    elif cargo_data.weight and cargo_data.price_per_kg:
        # Старый режим с одиночным грузом и общей ценой за кг (для совместимости)
        total_weight = cargo_data.weight
        total_cost = cargo_data.weight * cargo_data.price_per_kg
        combined_cargo_name = cargo_data.cargo_name or cargo_data.description[:50]
        detailed_description = f"{cargo_data.description}\n\nРасчет: {total_weight} кг × {cargo_data.price_per_kg} руб/кг = {total_cost} руб"
        
    else:
        # Самый старый режим с объявленной стоимостью (для полной совместимости)
        total_weight = cargo_data.weight or 0.0
        total_cost = cargo_data.declared_value or 0.0
        combined_cargo_name = cargo_data.cargo_name or cargo_data.description[:50]
        detailed_description = cargo_data.description
    
    # Определяем статус обработки на основе способа оплаты
    if cargo_data.payment_method == PaymentMethod.NOT_PAID:
        processing_status = "payment_pending"  # Идет в "Касса" -> "Не оплачено"
        payment_status = "pending"
    else:
        processing_status = "paid"  # Идет сразу на "Размещение"
        payment_status = "paid"
    
    cargo = {
        "id": cargo_id,
        "cargo_number": cargo_number,
        "sender_full_name": cargo_data.sender_full_name,
        "sender_phone": cargo_data.sender_phone,
        "recipient_full_name": cargo_data.recipient_full_name,
        "recipient_phone": cargo_data.recipient_phone,
        "recipient_address": cargo_data.recipient_address,
        "weight": total_weight,
        "cargo_name": combined_cargo_name,
        "declared_value": total_cost,
        "description": detailed_description,
        "route": cargo_data.route,
        "status": CargoStatus.ACCEPTED,
        "payment_status": payment_status,
        "processing_status": processing_status,  # Статус обработки
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": current_user.id,
        "created_by_operator": current_user.full_name,
        "target_warehouse_id": target_warehouse_id,
        "target_warehouse_name": warehouse.get("name") if warehouse else None,
        "warehouse_location": None,
        "warehouse_id": None,
        "block_number": None,
        "shelf_number": None,
        "cell_number": None,
        "placed_by_operator": None,
        "placed_by_operator_id": None,
        # Новые поля для множественных грузов
        "cargo_items": [item.dict() for item in cargo_data.cargo_items] if cargo_data.cargo_items else None,
        # НОВЫЕ ПОЛЯ ОПЛАТЫ
        "payment_method": cargo_data.payment_method.value,  # Способ оплаты
        "payment_amount": cargo_data.payment_amount,  # Сумма оплаты
        "debt_due_date": cargo_data.debt_due_date,  # Дата погашения долга
        "price_per_kg": cargo_data.price_per_kg if cargo_data.cargo_items else None,
        # НОВЫЕ ПОЛЯ КУРЬЕРСКОЙ СЛУЖБЫ
        "pickup_required": cargo_data.pickup_required,
        "pickup_address": cargo_data.pickup_address,
        "pickup_date": cargo_data.pickup_date,
        "pickup_time_from": cargo_data.pickup_time_from,
        "pickup_time_to": cargo_data.pickup_time_to,
        "delivery_method": cargo_data.delivery_method.value,
        "courier_fee": cargo_data.courier_fee,
        "assigned_courier_id": None,
        "assigned_courier_name": None,
        "courier_request_status": "pending" if cargo_data.pickup_required else None
    }
    
    # Генерируем QR код для груза
    cargo_qr_code = generate_cargo_qr_code_data(cargo)
    cargo["qr_code"] = cargo_qr_code
    
    db.operator_cargo.insert_one(cargo)
    
    # ОБНОВЛЕНО: Создание записи о долге, если требуется
    if cargo_data.payment_method == PaymentMethod.CREDIT:
        debt_record = {
            "id": f"DEBT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{current_user.id[:8]}",
            "cargo_id": cargo_id,
            "cargo_number": cargo_number,
            "debtor_name": cargo_data.sender_full_name,
            "debtor_phone": cargo_data.sender_phone,
            "amount": total_cost,
            "payment_amount": cargo_data.payment_amount or 0.0,
            "remaining_amount": total_cost - (cargo_data.payment_amount or 0.0),
            "debt_due_date": cargo_data.debt_due_date,
            "created_at": datetime.utcnow(),
            "created_by": current_user.id,
            "created_by_operator": current_user.full_name,
            "warehouse_id": target_warehouse_id,
            "warehouse_name": warehouse.get("name") if warehouse else None,
            "status": "active"  # active, paid, overdue
        }
        db.debts.insert_one(debt_record)
    
    # НОВОЕ: Создание курьерской заявки, если требуется забор груза
    if cargo_data.pickup_required:
        courier_request = {
            "id": str(uuid.uuid4()),
            "request_number": generate_courier_request_number(),  # Читаемый номер заявки
            "cargo_id": cargo_id,
            "sender_full_name": cargo_data.sender_full_name,
            "sender_phone": cargo_data.sender_phone,
            "cargo_name": combined_cargo_name,
            "pickup_address": cargo_data.pickup_address,
            "pickup_date": cargo_data.pickup_date,
            "pickup_time_from": cargo_data.pickup_time_from,
            "pickup_time_to": cargo_data.pickup_time_to,
            "delivery_method": cargo_data.delivery_method.value,
            "courier_fee": cargo_data.courier_fee,
            "payment_method": cargo_data.payment_method.value,  # Статус оплаты
            "payment_status": "not_paid" if cargo_data.payment_method == PaymentMethod.NOT_PAID else "paid",
            "assigned_courier_id": None,
            "assigned_courier_name": None,
            "request_status": "pending",
            "created_by": current_user.id,
            "created_by_operator": current_user.full_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "courier_notes": None
        }
        db.courier_requests.insert_one(courier_request)
        
        # Обновляем статус груза
        db.operator_cargo.update_one(
            {"id": cargo_id},
            {"$set": {"status": CargoStatus.PICKUP_REQUESTED, "courier_request_status": "pending"}}
        )
    
    # ОБНОВЛЕНО: Создание уведомлений по маршруту
    notification_message = f"Новый груз {cargo_number} от {cargo_data.sender_full_name}"
    if warehouse:
        notification_message += f" (склад: {warehouse['name']})"
    if cargo_data.payment_method != PaymentMethod.NOT_PAID:
        notification_message += f" - {cargo_data.payment_method.value.replace('_', ' ').title()}"
    
    # Используем умную систему уведомлений по маршруту
    route_display = {
        "moscow_to_tajikistan": "Москва-Таджикистан",
        "tajikistan_to_moscow": "Таджикистан-Москва"
    }.get(cargo_data.route, cargo_data.route)
    
    notification_message += f" (маршрут: {route_display})"
    
    # Отправляем уведомления операторам соответствующих складов по маршруту
    create_route_based_notifications(
        notification_message,
        route_display,
        cargo_id
    )
    
    # УЛУЧШЕННЫЙ ОТВЕТ: Возвращаем груз с QR кодом
    response_data = CargoWithLocation(**cargo).dict()
    response_data["qr_code"] = cargo_qr_code
    response_data["qr_display_message"] = f"QR код для груза {cargo_number} готов"
    
    return response_data

@app.post("/api/operator/cargo/create-for-courier")
async def create_cargo_for_courier_pickup(
    cargo_data: OperatorCargoCreate,
    current_user: User = Depends(get_current_user)
):
    """Создать груз только для курьерского забора (упрощенная форма)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Валидация для курьерского груза
    if not cargo_data.pickup_required:
        raise HTTPException(status_code=400, detail="Pickup is required for courier service")
    
    if not cargo_data.pickup_address or not cargo_data.pickup_date:
        raise HTTPException(status_code=400, detail="Pickup address and date are required")
    
    try:
        # Генерируем ID и номер груза
        cargo_id = str(uuid.uuid4())
        cargo_number = generate_cargo_number()
        
        # Определяем склад (для курьерского забора не так критично, но нужно)
        target_warehouse_id = None
        warehouse = None
        
        if current_user.role == UserRole.WAREHOUSE_OPERATOR:
            operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
            if operator_warehouse_ids:
                target_warehouse_id = operator_warehouse_ids[0]
                warehouse = db.warehouses.find_one({"id": target_warehouse_id})
        
        # Создаем документ груза (упрощенная версия для курьерского забора)
        cargo = {
            "id": cargo_id,
            "cargo_number": cargo_number,
            "sender_full_name": cargo_data.sender_full_name,
            "sender_phone": cargo_data.sender_phone,
            "recipient_full_name": cargo_data.recipient_full_name or "",
            "recipient_phone": cargo_data.recipient_phone or "",
            "recipient_address": cargo_data.recipient_address or "",
            "weight": cargo_data.weight or 0.0,
            "cargo_name": cargo_data.cargo_name or "",
            "declared_value": cargo_data.declared_value or 0.0,
            "description": cargo_data.description,
            "route": cargo_data.route,
            "status": CargoStatus.PICKUP_REQUESTED,  # Сразу в статус забора
            "payment_status": "not_paid",
            "processing_status": "courier_pickup",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.id,
            "created_by_operator": current_user.full_name,
            "target_warehouse_id": target_warehouse_id,
            "target_warehouse_name": warehouse.get("name") if warehouse else None,
            # Курьерские поля
            "pickup_required": True,
            "pickup_address": cargo_data.pickup_address,
            "pickup_date": cargo_data.pickup_date,
            "pickup_time_from": cargo_data.pickup_time_from,
            "pickup_time_to": cargo_data.pickup_time_to,
            "delivery_method": cargo_data.delivery_method.value,
            "courier_fee": cargo_data.courier_fee,
            "assigned_courier_id": None,
            "assigned_courier_name": None,
            "courier_request_status": "pending"
        }
        
        # Генерируем QR код
        cargo_qr_code = generate_cargo_qr_code_data(cargo)
        cargo["qr_code"] = cargo_qr_code
        
        # Сохраняем груз
        db.operator_cargo.insert_one(cargo)
        
        # Создаем курьерскую заявку
        courier_request = {
            "id": str(uuid.uuid4()),
            "request_number": generate_courier_request_number(),  # Читаемый номер заявки
            "cargo_id": cargo_id,
            "sender_full_name": cargo_data.sender_full_name,
            "sender_phone": cargo_data.sender_phone,
            "cargo_name": cargo_data.cargo_name or "",
            "pickup_address": cargo_data.pickup_address,
            "pickup_date": cargo_data.pickup_date,
            "pickup_time_from": cargo_data.pickup_time_from,
            "pickup_time_to": cargo_data.pickup_time_to,
            "delivery_method": cargo_data.delivery_method.value,
            "courier_fee": cargo_data.courier_fee,
            "payment_method": cargo_data.payment_method.value,  # Статус оплаты
            "payment_status": "not_paid" if cargo_data.payment_method == PaymentMethod.NOT_PAID else "paid",
            "assigned_courier_id": None,
            "assigned_courier_name": None,
            "request_status": "pending",
            "created_by": current_user.id,
            "created_by_operator": current_user.full_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "courier_notes": None
        }
        db.courier_requests.insert_one(courier_request)
        
        # Уведомления курьерам и админам
        create_notification(
            user_id=current_user.id,
            message=f"Создана заявка для курьерского забора груза {cargo_number} от {cargo_data.sender_full_name}",
            related_id=cargo_id
        )
        
        return {
            "message": "Cargo created for courier pickup successfully",
            "cargo_id": cargo_id,
            "cargo_number": cargo_number,
            "pickup_required": True,
            "status": "pickup_requested"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating cargo for courier: {str(e)}")

@app.post("/api/operator/cargo/place")
async def place_cargo_in_warehouse(
    placement_data: CargoPlacement,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем существование груза
    cargo = db.operator_cargo.find_one({"id": placement_data.cargo_id})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверяем существование склада
    warehouse = db.warehouses.find_one({"id": placement_data.warehouse_id, "is_active": True})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Проверяем валидность позиции
    if (placement_data.block_number < 1 or placement_data.block_number > warehouse["blocks_count"] or
        placement_data.shelf_number < 1 or placement_data.shelf_number > warehouse["shelves_per_block"] or
        placement_data.cell_number < 1 or placement_data.cell_number > warehouse["cells_per_shelf"]):
        raise HTTPException(status_code=400, detail="Invalid warehouse position")
    
    location_code = f"B{placement_data.block_number}-S{placement_data.shelf_number}-C{placement_data.cell_number}"
    
    # Проверяем, свободна ли ячейка
    existing_cell = db.warehouse_cells.find_one({
        "warehouse_id": placement_data.warehouse_id,
        "location_code": location_code,
        "is_occupied": True
    })
    
    if existing_cell:
        raise HTTPException(status_code=400, detail="Cell is already occupied")
    
    # Обновляем ячейку
    db.warehouse_cells.update_one(
        {
            "warehouse_id": placement_data.warehouse_id,
            "location_code": location_code
        },
        {"$set": {"is_occupied": True, "cargo_id": placement_data.cargo_id}}
    )
    
    # Обновляем груз
    db.operator_cargo.update_one(
        {"id": placement_data.cargo_id},
        {"$set": {
            "warehouse_location": location_code,
            "warehouse_id": placement_data.warehouse_id,
            "block_number": placement_data.block_number,
            "shelf_number": placement_data.shelf_number,
            "cell_number": placement_data.cell_number,
            "status": CargoStatus.IN_TRANSIT,
            "updated_at": datetime.utcnow(),
            "placed_by_operator": current_user.full_name,
            "placed_by_operator_id": current_user.id
        }}
    )
    
    # Создаем уведомление
    create_notification(
        current_user.id,
        f"Груз {cargo['cargo_number']} размещен в {warehouse['name']}: {location_code}",
        placement_data.cargo_id
    )
    
    # ИСПРАВЛЕНИЕ: Возвращаем правильную структуру для frontend
    return {
        "message": "Cargo placed successfully",
        "warehouse_name": warehouse["name"],
        "location_code": location_code,
        "cargo_number": cargo["cargo_number"],
        "cargo_name": cargo.get("cargo_name", ""),
        "placed_at": datetime.utcnow().isoformat()
    }

@app.post("/api/operator/cargo/place-auto")
async def place_cargo_in_warehouse_auto(
    placement_data: CargoPlacementAuto,
    current_user: User = Depends(get_current_user)
):
    """Размещение груза с автоматическим выбором склада для оператора"""
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Если оператор склада, получаем его привязанные склады
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        operator_warehouses = get_operator_warehouses(current_user.id)
        if not operator_warehouses:
            raise HTTPException(status_code=403, detail="No warehouses assigned to this operator")
        
        # Используем первый привязанный склад (можно дать пользователю выбор, если их несколько)
        warehouse_id = operator_warehouses[0]
    else:
        # Для админа нужно указать склад или использовать default
        raise HTTPException(status_code=400, detail="Admin must use regular placement endpoint with warehouse selection")
    
    # Проверяем существование груза
    cargo = db.operator_cargo.find_one({"id": placement_data.cargo_id})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверяем существование склада
    warehouse = db.warehouses.find_one({"id": warehouse_id, "is_active": True})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Assigned warehouse not found")
    
    # Проверяем валидность позиции
    if (placement_data.block_number < 1 or placement_data.block_number > warehouse["blocks_count"] or
        placement_data.shelf_number < 1 or placement_data.shelf_number > warehouse["shelves_per_block"] or
        placement_data.cell_number < 1 or placement_data.cell_number > warehouse["cells_per_shelf"]):
        raise HTTPException(status_code=400, detail="Invalid warehouse position")
    
    location_code = f"B{placement_data.block_number}-S{placement_data.shelf_number}-C{placement_data.cell_number}"
    
    # Проверяем, свободна ли ячейка
    existing_cell = db.warehouse_cells.find_one({
        "warehouse_id": warehouse_id,
        "location_code": location_code,
        "is_occupied": True
    })
    
    if existing_cell:
        raise HTTPException(status_code=400, detail="Cell is already occupied")
    
    # Создаем ячейку если не существует
    db.warehouse_cells.update_one(
        {
            "warehouse_id": warehouse_id,
            "location_code": location_code
        },
        {
            "$set": {
                "warehouse_id": warehouse_id,
                "location_code": location_code,
                "block_number": placement_data.block_number,
                "shelf_number": placement_data.shelf_number,
                "cell_number": placement_data.cell_number,
                "is_occupied": True,
                "cargo_id": placement_data.cargo_id,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    # Обновляем груз
    db.operator_cargo.update_one(
        {"id": placement_data.cargo_id},
        {"$set": {
            "warehouse_location": f"{warehouse['name']} - Блок {placement_data.block_number}, Полка {placement_data.shelf_number}, Ячейка {placement_data.cell_number}",
            "warehouse_id": warehouse_id,
            "block_number": placement_data.block_number,
            "shelf_number": placement_data.shelf_number,
            "cell_number": placement_data.cell_number,
            "status": CargoStatus.IN_TRANSIT,
            "updated_at": datetime.utcnow(),
            "placed_by_operator": current_user.full_name,
            "placed_by_operator_id": current_user.id
        }}
    )
    
    return {"message": "Cargo placed successfully in assigned warehouse", "warehouse_name": warehouse["name"]}

@app.get("/api/warehouses/{warehouse_id}/statistics")
async def get_warehouse_statistics(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить статистику склада: количество грузов, вес, заполненность"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Получаем информацию о складе
        warehouse = db.warehouses.find_one({"id": warehouse_id}, {"_id": 0})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        # Подсчитываем грузы на складе (из разных коллекций)
        cargo_count_operator = db.operator_cargo.count_documents({
            "warehouse_id": warehouse_id,
            "status": {"$in": ["IN_TRANSIT", "READY_FOR_DELIVERY"]}
        })
        
        cargo_count_general = db.cargo.count_documents({
            "warehouse_id": warehouse_id,
            "status": {"$in": ["awaiting_placement", "in_transit", "ready_for_delivery"]}
        })
        
        total_cargo_count = cargo_count_operator + cargo_count_general
        
        # Подсчитываем общий вес грузов
        operator_cargo_weights = list(db.operator_cargo.aggregate([
            {"$match": {
                "warehouse_id": warehouse_id,
                "status": {"$in": ["IN_TRANSIT", "READY_FOR_DELIVERY"]}
            }},
            {"$group": {"_id": None, "total_weight": {"$sum": "$weight"}}}
        ]))
        
        general_cargo_weights = list(db.cargo.aggregate([
            {"$match": {
                "warehouse_id": warehouse_id,
                "status": {"$in": ["awaiting_placement", "in_transit", "ready_for_delivery"]}
            }},
            {"$group": {"_id": None, "total_weight": {"$sum": "$weight"}}}
        ]))
        
        total_weight = (
            (operator_cargo_weights[0]["total_weight"] if operator_cargo_weights else 0) +
            (general_cargo_weights[0]["total_weight"] if general_cargo_weights else 0)
        )
        
        # Подсчитываем общее количество ячеек
        total_cells = (
            warehouse.get("blocks_count", 0) * 
            warehouse.get("shelves_per_block", 0) * 
            warehouse.get("cells_per_shelf", 0)
        )
        
        # Подсчитываем занятые ячейки
        occupied_cells = db.warehouse_cells.count_documents({
            "warehouse_id": warehouse_id,
            "is_occupied": True
        })
        
        # Подсчитываем статистику
        free_cells = max(0, total_cells - occupied_cells)
        utilization_percent = (occupied_cells / total_cells * 100) if total_cells > 0 else 0
        
        return {
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse.get("name"),
            "total_cells": total_cells,
            "occupied_cells": occupied_cells,
            "free_cells": free_cells,
            "utilization_percent": round(utilization_percent, 1),
            "total_cargo_count": total_cargo_count,
            "total_weight": round(total_weight, 2),
            "cargo_breakdown": {
                "operator_cargo": cargo_count_operator,
                "general_cargo": cargo_count_general
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting warehouse statistics: {str(e)}")

@app.get("/api/operator/cargo/available-for-placement")
async def get_available_cargo_for_placement(
    page: int = 1,
    per_page: int = 25,
    current_user: User = Depends(get_current_user)
):
    """Получить грузы, доступные для размещения на складе с пагинацией"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для просмотра грузов для размещения"
        )
    
    try:
        # Валидация параметров пагинации
        pagination = PaginationParams(page=page, per_page=per_page)
        
        # Определяем доступные склады для оператора
        if current_user.role == UserRole.WAREHOUSE_OPERATOR:
            # Получаем склады оператора
            operator_warehouse_bindings = list(db.operator_warehouse_bindings.find(
                {"operator_id": current_user.id}
            ))
            
            if operator_warehouse_bindings:
                operator_warehouse_ids = [binding["warehouse_id"] for binding in operator_warehouse_bindings]
            else:
                # Если нет привязок, оператор может видеть все склады (для упрощения)
                warehouses = list(db.warehouses.find({"is_active": True}))
                operator_warehouse_ids = [w["id"] for w in warehouses]
        else:
            # Админ видит все склады
            warehouses = list(db.warehouses.find({"is_active": True}))
            operator_warehouse_ids = [w["id"] for w in warehouses]
        
        # ИСПРАВЛЕНИЕ: Ищем ВСЕ грузы готовые к размещению независимо от статуса оплаты
        placement_query = {
            # Убираем проверку processing_status - все грузы могут размещаться
            "status": {"$nin": ["placed_in_warehouse", "removed_from_placement"]},  # Еще не размещенные и не удаленные из размещения
            "$and": [
                {"$or": [
                    {"warehouse_location": {"$exists": False}},
                    {"warehouse_location": None},
                    {"warehouse_location": ""}
                ]},
                {"$or": [
                    {"block_number": {"$exists": False}},
                    {"block_number": None},
                    {"shelf_number": {"$exists": False}}, 
                    {"shelf_number": None},
                    {"cell_number": {"$exists": False}},
                    {"cell_number": None}
                ]}
            ]
        }

        # Подсчитываем общее количество в обеих коллекциях
        total_count_cargo = db.cargo.count_documents(placement_query)
        total_count_operator_cargo = db.operator_cargo.count_documents(placement_query)
        total_count = total_count_cargo + total_count_operator_cargo
        
        # Получаем грузы из обеих коллекций
        skip = (pagination.page - 1) * pagination.per_page
        
        # Получаем из основной коллекции cargo
        cargo_list_main = list(db.cargo.find(placement_query).skip(skip).limit(pagination.per_page).sort("created_at", -1))
        
        # Получаем из коллекции operator_cargo (если еще нужны грузы для заполнения страницы)
        remaining_limit = pagination.per_page - len(cargo_list_main)
        cargo_list_operator = []
        if remaining_limit > 0:
            operator_skip = max(0, skip - total_count_cargo)
            cargo_list_operator = list(db.operator_cargo.find(placement_query).skip(operator_skip).limit(remaining_limit).sort("created_at", -1))
        
        # Объединяем списки
        cargo_list = cargo_list_main + cargo_list_operator
        
        # Обрабатываем данные и добавляем информацию об операторах и складах
        normalized_cargo = []
        for cargo in cargo_list:
            # Сериализуем данные
            cargo_data = serialize_mongo_document(cargo)
            
            # Получаем информацию о создателе/принимающем операторе
            creator_id = cargo.get('created_by') or cargo.get('sender_id')
            accepting_operator_id = cargo.get('created_by_operator_id') or cargo.get('accepting_operator_id')
            
            if creator_id:
                creator = db.users.find_one({"id": creator_id})
                if creator:
                    cargo_data['creator_name'] = creator.get('full_name', 'Неизвестно')
                    cargo_data['creator_phone'] = creator.get('phone', 'Не указан')
                else:
                    cargo_data['creator_name'] = 'Неизвестно'
                    cargo_data['creator_phone'] = 'Не указан'
            
            # Информация о принимающем операторе - расширенные данные
            accepting_operator_info = None
            if accepting_operator_id:
                accepting_operator = db.users.find_one({"id": accepting_operator_id})
                if accepting_operator:
                    accepting_operator_info = {
                        'operator_id': accepting_operator['id'],
                        'operator_name': accepting_operator.get('full_name', 'Неизвестно'),
                        'operator_phone': accepting_operator.get('phone', 'Не указан'),
                        'user_number': accepting_operator.get('user_number', 'N/A'),
                        'role': accepting_operator.get('role', 'unknown')
                    }
                    cargo_data['accepting_operator'] = accepting_operator.get('full_name', 'Неизвестно')
                    cargo_data['accepting_operator_phone'] = accepting_operator.get('phone', 'Не указан')
                else:
                    cargo_data['accepting_operator'] = 'Неизвестно'
                    cargo_data['accepting_operator_phone'] = 'Не указан'
                    accepting_operator_info = {
                        'operator_id': accepting_operator_id,
                        'operator_name': 'Неизвестно',
                        'operator_phone': 'Не указан',
                        'user_number': 'N/A',
                        'role': 'unknown'
                    }
            else:
                # Пытаемся найти по created_by в операторе
                creator_id = cargo.get('created_by')
                if creator_id:
                    accepting_operator = db.users.find_one({"id": creator_id})
                    if accepting_operator and accepting_operator.get('role') in ['warehouse_operator', 'admin']:
                        accepting_operator_info = {
                            'operator_id': accepting_operator['id'],
                            'operator_name': accepting_operator.get('full_name', 'Неизвестно'),
                            'operator_phone': accepting_operator.get('phone', 'Не указан'),
                            'user_number': accepting_operator.get('user_number', 'N/A'),
                            'role': accepting_operator.get('role', 'unknown')
                        }
                        cargo_data['accepting_operator'] = accepting_operator.get('full_name', 'Неизвестно')
                        cargo_data['accepting_operator_phone'] = accepting_operator.get('phone', 'Не указан')
                    else:
                        # Пытаемся найти по имени оператора в строковом поле
                        operator_name = cargo.get('created_by_operator') or cargo.get('accepting_operator')
                        cargo_data['accepting_operator'] = operator_name if operator_name else 'Неизвестно'
                        cargo_data['accepting_operator_phone'] = 'Не указан'
                        accepting_operator_info = {
                            'operator_id': creator_id if creator_id else 'unknown',
                            'operator_name': operator_name if operator_name else 'Неизвестно',
                            'operator_phone': 'Не указан',
                            'user_number': 'N/A',
                            'role': 'unknown'
                        }
                else:
                    # Пытаемся найти по имени оператора в строковом поле
                    operator_name = cargo.get('created_by_operator') or cargo.get('accepting_operator')
                    cargo_data['accepting_operator'] = operator_name if operator_name else 'Неизвестно'
                    cargo_data['accepting_operator_phone'] = 'Не указан'
                    accepting_operator_info = {
                        'operator_id': 'unknown',
                        'operator_name': operator_name if operator_name else 'Неизвестно',
                        'operator_phone': 'Не указан',
                        'user_number': 'N/A',
                        'role': 'unknown'
                    }
            
            # Добавляем полную информацию об операторе в отдельное поле
            cargo_data['accepting_operator_info'] = accepting_operator_info
            
            # Добавляем информацию о маршруте и исходном складе
            cargo_data['route'] = cargo.get('route', 'Не указан')
            cargo_data['source_warehouse'] = cargo.get('source_warehouse_name', 'Не указан')
            cargo_data['payment_status'] = cargo.get('payment_status', 'unknown')
            cargo_data['payment_method'] = cargo.get('payment_method', 'not_specified')
            
            # История операций с грузом
            cargo_data['created_at'] = cargo.get('created_at')
            cargo_data['updated_at'] = cargo.get('updated_at')
            cargo_data['last_status_change'] = cargo.get('last_status_change')
            
            # Получаем информацию о складе назначения
            warehouse_id = cargo.get('warehouse_id')
            if warehouse_id:
                warehouse = db.warehouses.find_one({"id": warehouse_id})
                if warehouse:
                    cargo_data['warehouse_name'] = warehouse.get('name', 'Неизвестный склад')
                    cargo_data['warehouse_location'] = warehouse.get('location', 'Не указано')
                else:
                    cargo_data['warehouse_name'] = 'Неизвестный склад'
                    cargo_data['warehouse_location'] = 'Не указано'
            else:
                cargo_data['warehouse_name'] = 'Склад не назначен'
                cargo_data['warehouse_location'] = 'Не указано'
            
            # Добавляем статус готовности к размещению
            cargo_data['ready_for_placement'] = True
            cargo_data['placement_status'] = 'awaiting_placement'
            
            normalized_cargo.append(cargo_data)
        
        # Создаем ответ с пагинацией
        return create_pagination_response(normalized_cargo, total_count, pagination.page, pagination.per_page)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения грузов для размещения: {str(e)}"
        )

# НОВОЕ: Endpoint для массового удаления грузов из списка размещения
@app.delete("/api/operator/cargo/bulk-remove-from-placement")
async def bulk_remove_cargo_from_placement(
    request: BulkRemoveFromPlacementRequest,
    current_user: User = Depends(get_current_user)
):
    """Массовое удаление грузов из списка размещения"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        cargo_ids = request.cargo_ids
        
        deleted_count = 0
        deleted_cargo_numbers = []
        
        for cargo_id in cargo_ids:
            # ИСПРАВЛЕНО: Ищем груз с дополнительной диагностикой дублирующихся ID
            cargo = None
            collection_name = None
            
            # Сначала ищем в operator_cargo  
            cargo = db.operator_cargo.find_one({"id": cargo_id})
            if cargo:
                collection_name = "operator_cargo"
            
            # Если не найден, ищем в основной коллекции cargo
            if not cargo:
                cargo = db.cargo.find_one({"id": cargo_id})
                if cargo:
                    collection_name = "cargo"
            
            # НОВОЕ: Если не найден, ищем в заявках на забор (cargo_requests)
            if not cargo:
                # Ищем груз по cargo_id в items массиве заявок на забор
                request_with_cargo = db.cargo_requests.find_one({
                    "items.id": cargo_id
                })
                if request_with_cargo:
                    # Находим конкретный item в массиве
                    for item in request_with_cargo.get("items", []):
                        if item.get("id") == cargo_id:
                            cargo = item
                            collection_name = "cargo_requests"
                            cargo["request_id"] = request_with_cargo["id"]  # Сохраняем ID заявки
                            break
            
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Дополнительная проверка при дублировании ID
            if cargo and collection_name in ["operator_cargo", "cargo"]:
                collection = getattr(db, collection_name)
                duplicate_check = list(collection.find({"id": cargo_id}))
                
                if len(duplicate_check) > 1:
                    print(f"⚠️ МАССОВОЕ УДАЛЕНИЕ: Найдено {len(duplicate_check)} грузов с ID {cargo_id}")
                    for i, dup_cargo in enumerate(duplicate_check):
                        print(f"   {i+1}. Номер: {dup_cargo.get('cargo_number')}, Отправитель: {dup_cargo.get('sender_full_name')}")
                    
                    # В случае дублирования ID используем первый найденный груз
                    cargo = duplicate_check[0]
                    print(f"   Используем груз: {cargo.get('cargo_number')}")
            
            if cargo:
                if collection_name == "cargo_requests":
                    # Для грузов из заявок на забор обновляем статус item'а в массиве
                    update_result = db.cargo_requests.update_one(
                        {"id": cargo["request_id"], "items.id": cargo_id},
                        {
                            "$set": {
                                "items.$.status": "removed_from_placement",
                                "items.$.removed_from_placement_at": datetime.utcnow(),
                                "items.$.removed_from_placement_by": current_user.id,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                else:
                    # Для обычных коллекций обновляем документ целиком
                    collection = getattr(db, collection_name)
                    update_result = collection.update_one(
                        {"id": cargo_id},
                        {
                            "$set": {
                                "status": "removed_from_placement",
                                "removed_from_placement_at": datetime.utcnow(),
                                "removed_from_placement_by": current_user.id,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                
                if update_result.modified_count > 0:
                    deleted_count += 1
                    cargo_number = cargo.get('cargo_number', cargo.get('id', 'Unknown'))
                    deleted_cargo_numbers.append(cargo_number)
        
        # Создаем уведомление о массовом удалении
        if deleted_count > 0:
            create_notification(
                current_user.id,
                f"Массово удалено {deleted_count} грузов из списка размещения: {', '.join(deleted_cargo_numbers[:5])}{'...' if len(deleted_cargo_numbers) > 5 else ''}",
                None
            )
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "total_requested": len(cargo_ids),
            "deleted_cargo_numbers": deleted_cargo_numbers,
            "message": f"Успешно удалено {deleted_count} из {len(cargo_ids)} грузов из списка размещения"
        }
        
    except Exception as e:
        print(f"❌ Ошибка массового удаления грузов: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка массового удаления грузов: {str(e)}"
        )

# НОВОЕ: Endpoint для удаления груза из списка размещения
@app.delete("/api/operator/cargo/{cargo_id}/remove-from-placement")
async def remove_cargo_from_placement(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удалить груз из списка размещения"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # ИСПРАВЛЕНО: Ищем груз в нескольких коллекциях с дополнительной проверкой
        cargo = None
        collection_name = None
        
        # Сначала ищем в operator_cargo
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        if cargo:
            collection_name = "operator_cargo"
        
        # Если не найден, ищем в основной коллекции cargo  
        if not cargo:
            cargo = db.cargo.find_one({"id": cargo_id})
            if cargo:
                collection_name = "cargo"
        
        # НОВОЕ: Если не найден, ищем в заявках на забор
        if not cargo:
            request_with_cargo = db.cargo_requests.find_one({
                "items.id": cargo_id
            })
            if request_with_cargo:
                for item in request_with_cargo.get("items", []):
                    if item.get("id") == cargo_id:
                        cargo = item
                        collection_name = "cargo_requests"
                        cargo["request_id"] = request_with_cargo["id"]
                        break
        
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Дополнительная проверка при дублировании ID
        # Если есть подозрение на дублирование, проверяем дополнительно по cargo_number
        if collection_name in ["operator_cargo", "cargo"]:
            collection = getattr(db, collection_name)
            duplicate_check = list(collection.find({"id": cargo_id}))
            
            if len(duplicate_check) > 1:
                print(f"⚠️ ВНИМАНИЕ: Найдено {len(duplicate_check)} грузов с ID {cargo_id}")
                for i, dup_cargo in enumerate(duplicate_check):
                    print(f"   {i+1}. Номер: {dup_cargo.get('cargo_number')}, Отправитель: {dup_cargo.get('sender_full_name')}")
                
                # В случае дублирования ID используем первый найденный груз
                cargo = duplicate_check[0]
                print(f"   Используем груз: {cargo.get('cargo_number')}")
        
        # Обновляем статус в зависимости от типа коллекции
        if collection_name == "cargo_requests":
            # Для заявок на забор обновляем статус item'а в массиве
            update_result = db.cargo_requests.update_one(
                {"id": cargo["request_id"], "items.id": cargo_id},
                {
                    "$set": {
                        "items.$.status": "removed_from_placement", 
                        "items.$.removed_from_placement_at": datetime.utcnow(),
                        "items.$.removed_from_placement_by": current_user.id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        else:
            # Для обычных коллекций
            collection = getattr(db, collection_name)
            update_result = collection.update_one(
                {"id": cargo_id},
                {
                    "$set": {
                        "status": "removed_from_placement",
                        "removed_from_placement_at": datetime.utcnow(),
                        "removed_from_placement_by": current_user.id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        if update_result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to remove cargo from placement")
        
        # Создаем уведомление
        cargo_number = cargo.get('cargo_number', cargo.get('id', 'Unknown'))
        create_notification(
            current_user.id,
            f"Груз {cargo_number} удален из списка размещения",
            cargo_id
        )
        
        return {
            "success": True,
            "message": f"Груз {cargo_number} успешно удален из списка размещения",
            "cargo_number": cargo_number
        }
        
    except Exception as e:
        print(f"❌ Ошибка удаления груза из размещения: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления груза из списка размещения: {str(e)}"
        )

@app.post("/api/cargo/{cargo_id}/quick-placement")
async def quick_cargo_placement(
    cargo_id: str,
    placement_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Быстрое размещение груза по номеру с автоматическим выбором склада"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Получаем данные размещения
    block_number = placement_data.get('block_number')
    shelf_number = placement_data.get('shelf_number') 
    cell_number = placement_data.get('cell_number')
    
    if not all([block_number, shelf_number, cell_number]):
        raise HTTPException(status_code=400, detail="Block, shelf, and cell numbers are required")
    
    # Ищем груз в обеих коллекциях
    cargo = db.operator_cargo.find_one({"id": cargo_id})
    collection = "operator_cargo"
    
    if not cargo:
        cargo = db.cargo.find_one({"id": cargo_id})
        collection = "cargo"
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Автоматически определяем склад на основе привязки оператора
    warehouse_id = None
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        operator_warehouses = get_operator_warehouses(current_user.id)
        if operator_warehouses:
            warehouse_id = operator_warehouses[0]  # Используем первый привязанный склад
        else:
            raise HTTPException(status_code=400, detail="No warehouse assigned to operator")
    else:
        # Для админа используем склад из данных запроса или первый доступный
        warehouse_id = placement_data.get('warehouse_id')
        if not warehouse_id:
            warehouses = list(db.warehouses.find({"is_active": True}))
            if warehouses:
                warehouse_id = warehouses[0]["id"]
            else:
                raise HTTPException(status_code=400, detail="No active warehouses available")
    
    # Проверяем существование склада
    warehouse = db.warehouses.find_one({"id": warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Проверяем доступность ячейки
    location_code = f"{block_number}-{shelf_number}-{cell_number}"
    existing_cell = db.warehouse_cells.find_one({
        "warehouse_id": warehouse_id,
        "location_code": location_code,
        "is_occupied": True
    })
    
    if existing_cell:
        raise HTTPException(status_code=400, detail=f"Cell {location_code} is already occupied")
    
    # Обновляем или создаем запись ячейки
    warehouse_location = f"Б{block_number}-П{shelf_number}-Я{cell_number}"
    
    # Обновляем груз
    update_data = {
        "warehouse_id": warehouse_id,
        "warehouse_location": warehouse_location,
        "block_number": block_number,
        "shelf_number": shelf_number,
        "cell_number": cell_number,
        "placed_by_operator": current_user.full_name,
        "placed_by_operator_id": current_user.id,
        "processing_status": "placed",
        "status": CargoStatus.IN_WAREHOUSE,
        "updated_at": datetime.utcnow()
    }
    
    # Обновляем в соответствующей коллекции
    if collection == "operator_cargo":
        db.operator_cargo.update_one({"id": cargo_id}, {"$set": update_data})
    else:
        db.cargo.update_one({"id": cargo_id}, {"$set": update_data})
    
    # Обновляем информацию о ячейке
    db.warehouse_cells.update_one(
        {"warehouse_id": warehouse_id, "location_code": location_code},
        {
            "$set": {
                "is_occupied": True,
                "cargo_id": cargo_id
            }
        },
        upsert=True
    )
    
    # Создаем уведомление
    message = f"Груз {cargo['cargo_number']} размещен в ячейке {warehouse_location} склада {warehouse['name']}"
    
    # Уведомляем клиента
    sender_id = cargo.get("sender_id") or cargo.get("created_by")
    if sender_id and sender_id != current_user.id:
        create_notification(sender_id, message, cargo_id)
    
    # Системное уведомление
    create_system_notification(
        "Груз размещен",
        f"{message} оператором {current_user.full_name}",
        "placement",
        cargo_id,
        None,
        current_user.id
    )
    
    return {
        "message": "Cargo placed successfully",
        "cargo_number": cargo['cargo_number'],
        "warehouse_name": warehouse['name'],
        "location": warehouse_location,
        "placed_by": current_user.full_name
    }

@app.get("/api/warehouses/{warehouse_id}/layout-with-cargo")
async def get_warehouse_layout_with_cargo(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить схему склада с информацией о размещенных грузах"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем доступ к складу
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        operator_warehouses = get_operator_warehouses(current_user.id)
        if warehouse_id not in operator_warehouses:
            raise HTTPException(status_code=403, detail="Access denied to this warehouse")
    
    # Получаем информацию о складе
    warehouse = db.warehouses.find_one({"id": warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Получаем все ячейки склада с грузами
    warehouse_cells = list(db.warehouse_cells.find({"warehouse_id": warehouse_id}))
    
    # Получаем все грузы, размещенные на этом складе
    cargo_in_warehouse = list(db.operator_cargo.find({
        "warehouse_id": warehouse_id,
        "warehouse_location": {"$ne": None}
    }))
    
    # Также ищем в коллекции cargo
    user_cargo_in_warehouse = list(db.cargo.find({
        "warehouse_id": warehouse_id,
        "warehouse_location": {"$ne": None}
    }))
    
    cargo_in_warehouse.extend(user_cargo_in_warehouse)
    
    # Создаем карту грузов по ячейкам
    cargo_by_location = {}
    for cargo in cargo_in_warehouse:
        location = cargo.get('warehouse_location')
        if location and location != "Склад для грузов":  # Игнорируем общие локации
            # Парсинг различных форматов местоположения
            block_num = shelf_num = cell_num = None
            
            try:
                # Формат "Б1-П2-Я15" (кириллица)
                if location.startswith('Б'):
                    parts = location.split('-')
                    if len(parts) >= 3:
                        block_num = int(parts[0][1:])  # Убираем "Б" и берем число
                        shelf_num = int(parts[1][1:])  # Убираем "П" и берем число
                        cell_num = int(parts[2][1:])   # Убираем "Я" и берем число
                
                # Формат "B1-S1-C1" (латиница)
                elif location.startswith('B'):
                    parts = location.split('-')
                    if len(parts) >= 3:
                        block_num = int(parts[0][1:])  # Убираем "B" и берем число
                        shelf_num = int(parts[1][1:])  # Убираем "S" и берем число
                        cell_num = int(parts[2][1:])   # Убираем "C" и берем число
                
                # Числовой формат "1-2-15"
                elif '-' in location:
                    parts = location.split('-')
                    if len(parts) >= 3:
                        block_num = int(parts[0])
                        shelf_num = int(parts[1])
                        cell_num = int(parts[2])
                
                if block_num and shelf_num and cell_num:
                    location_key = f"{block_num}-{shelf_num}-{cell_num}"
                    cargo_by_location[location_key] = {
                        "id": cargo["id"],
                        "cargo_number": cargo["cargo_number"],
                        "cargo_name": cargo.get("cargo_name", "Груз"),
                        "weight": cargo["weight"],
                        "declared_value": cargo["declared_value"],
                        "sender_full_name": cargo["sender_full_name"],
                        "sender_phone": cargo["sender_phone"],
                        "recipient_full_name": cargo["recipient_full_name"],
                        "recipient_phone": cargo["recipient_phone"],
                        "recipient_address": cargo["recipient_address"],
                        "description": cargo.get("description", ""),
                        "warehouse_location": location,
                        "created_at": cargo["created_at"],
                        "processing_status": cargo.get("processing_status", "placed"),
                        "block_number": block_num,
                        "shelf_number": shelf_num,
                        "cell_number": cell_num
                    }
            except (ValueError, IndexError):
                print(f"Warning: Could not parse warehouse location: {location}")
                continue
    
    # Создаем структуру склада с блоками, полками и ячейками
    blocks = {}
    
    # Получаем количество блоков, полок и ячеек из настроек склада или по умолчанию
    max_blocks = warehouse.get('blocks_count', 3)
    max_shelves = warehouse.get('shelves_per_block', 3)  
    max_cells = warehouse.get('cells_per_shelf', 50)
    
    for block in range(1, max_blocks + 1):
        blocks[f"block_{block}"] = {
            "block_number": block,
            "shelves": {}
        }
        
        for shelf in range(1, max_shelves + 1):
            blocks[f"block_{block}"]["shelves"][f"shelf_{shelf}"] = {
                "shelf_number": shelf,
                "cells": {}
            }
            
            for cell in range(1, max_cells + 1):
                location_key = f"{block}-{shelf}-{cell}"
                cell_data = {
                    "cell_number": cell,
                    "location_code": location_key,
                    "is_occupied": location_key in cargo_by_location,
                    "cargo": cargo_by_location.get(location_key, None)
                }
                blocks[f"block_{block}"]["shelves"][f"shelf_{shelf}"]["cells"][f"cell_{cell}"] = cell_data
    
    return {
        "warehouse": serialize_mongo_document(warehouse),
        "layout": blocks,
        "total_cargo": len(cargo_by_location),
        "occupied_cells": len(cargo_by_location),
        "total_cells": max_blocks * max_shelves * max_cells,
        "occupancy_percentage": round((len(cargo_by_location) / (max_blocks * max_shelves * max_cells)) * 100, 2)
    }

@app.post("/api/warehouses/{warehouse_id}/related-cargo")
async def find_related_cargo_in_warehouse(
    warehouse_id: str,
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Найти связанные грузы на складе по отправителю, получателю или заявке"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    cargo_id = request.get("cargo_id")
    sender_phone = request.get("sender_phone", "")
    recipient_phone = request.get("recipient_phone", "")
    sender_full_name = request.get("sender_full_name", "")
    recipient_full_name = request.get("recipient_full_name", "")
    
    # Поиск связанных грузов в обеих коллекциях
    related_cargo = []
    
    # Условия поиска связанных грузов
    search_conditions = []
    
    # По телефону отправителя
    if sender_phone:
        search_conditions.append({"sender_phone": sender_phone})
    
    # По телефону получателя
    if recipient_phone:
        search_conditions.append({"recipient_phone": recipient_phone})
    
    # По имени отправителя
    if sender_full_name:
        search_conditions.append({"sender_full_name": {"$regex": sender_full_name, "$options": "i"}})
    
    # По имени получателя
    if recipient_full_name:
        search_conditions.append({"recipient_full_name": {"$regex": recipient_full_name, "$options": "i"}})
    
    if search_conditions:
        # Поиск в operator_cargo
        query = {
            "warehouse_id": warehouse_id,
            "warehouse_location": {"$ne": None, "$exists": True},
            "id": {"$ne": cargo_id},  # Исключаем сам груз
            "$or": search_conditions
        }
        
        operator_related = list(db.operator_cargo.find(query))
        
        # Поиск в cargo
        user_related = list(db.cargo.find(query))
        
        # Объединяем результаты
        all_related = operator_related + user_related
        
        for cargo in all_related:
            # Парсим warehouse_location для получения адреса ячейки
            location = cargo.get('warehouse_location', '')
            formatted_location = location
            
            # Форматируем в читаемый вид
            if location.startswith('Б') and '-' in location:
                try:
                    parts = location.split('-')
                    if len(parts) >= 3:
                        block = parts[0]  # Б01
                        shelf = parts[1]  # П02
                        cell = parts[2]   # Я03
                        formatted_location = f"Блок {block[1:]}, Полка {shelf[1:]}, Ячейка {cell[1:]}"
                except:
                    pass
            
            related_cargo.append({
                "id": cargo["id"],
                "cargo_number": cargo["cargo_number"],
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "weight": cargo.get("weight", 0),
                "sender_full_name": cargo.get("sender_full_name", ""),
                "sender_phone": cargo.get("sender_phone", ""),
                "recipient_full_name": cargo.get("recipient_full_name", ""),
                "recipient_phone": cargo.get("recipient_phone", ""),
                "recipient_address": cargo.get("recipient_address", ""),
                "warehouse_location": location,
                "formatted_location": formatted_location,
                "declared_value": cargo.get("declared_value", 0),
                "description": cargo.get("description", ""),
                "created_at": cargo.get("created_at"),
                "processing_status": cargo.get("processing_status", "placed")
            })
    
    return {
        "success": True,
        "related_cargo": related_cargo,
        "total_related": len(related_cargo),
        "search_criteria": {
            "sender_phone": sender_phone,
            "recipient_phone": recipient_phone,
            "sender_full_name": sender_full_name,
            "recipient_full_name": recipient_full_name
        },
        "message": f"Найдено {len(related_cargo)} связанных грузов на складе"
    }

@app.post("/api/warehouses/{warehouse_id}/move-cargo")
async def move_cargo_between_cells(
    warehouse_id: str,
    move_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Переместить груз из одной ячейки в другую"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем доступ к складу
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        operator_warehouses = get_operator_warehouses(current_user.id)
        if warehouse_id not in operator_warehouses:
            raise HTTPException(status_code=403, detail="Access denied to this warehouse")
    
    cargo_id = move_data.get("cargo_id")
    from_block = move_data.get("from_block")
    from_shelf = move_data.get("from_shelf") 
    from_cell = move_data.get("from_cell")
    to_block = move_data.get("to_block")
    to_shelf = move_data.get("to_shelf")
    to_cell = move_data.get("to_cell")
    
    if not all([cargo_id, from_block, from_shelf, from_cell, to_block, to_shelf, to_cell]):
        raise HTTPException(status_code=400, detail="Missing required fields for cargo move")
    
    # Проверяем, что целевая ячейка свободна
    to_location_code = f"{to_block}-{to_shelf}-{to_cell}"
    existing_cell = db.warehouse_cells.find_one({
        "warehouse_id": warehouse_id,
        "location_code": to_location_code,
        "is_occupied": True
    })
    
    if existing_cell:
        raise HTTPException(status_code=400, detail=f"Target cell {to_location_code} is already occupied")
    
    # Ищем груз в обеих коллекциях
    cargo = db.operator_cargo.find_one({"id": cargo_id, "warehouse_id": warehouse_id})
    collection = "operator_cargo"
    
    if not cargo:
        cargo = db.cargo.find_one({"id": cargo_id, "warehouse_id": warehouse_id})
        collection = "cargo"
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found in this warehouse")
    
    # Новое местоположение
    new_location = f"Б{to_block}-П{to_shelf}-Я{to_cell}"
    old_location = f"Б{from_block}-П{from_shelf}-Я{from_cell}"
    
    # Обновляем груз
    update_data = {
        "warehouse_location": new_location,
        "block_number": to_block,
        "shelf_number": to_shelf, 
        "cell_number": to_cell,
        "updated_at": datetime.utcnow()
    }
    
    # Обновляем в соответствующей коллекции
    if collection == "operator_cargo":
        db.operator_cargo.update_one({"id": cargo_id}, {"$set": update_data})
    else:
        db.cargo.update_one({"id": cargo_id}, {"$set": update_data})
    
    # Освобождаем старую ячейку
    old_location_code = f"{from_block}-{from_shelf}-{from_cell}"
    db.warehouse_cells.update_one(
        {"warehouse_id": warehouse_id, "location_code": old_location_code},
        {"$set": {"is_occupied": False, "cargo_id": None}}
    )
    
    # Занимаем новую ячейку
    db.warehouse_cells.update_one(
        {"warehouse_id": warehouse_id, "location_code": to_location_code},
        {
            "$set": {
                "is_occupied": True,
                "cargo_id": cargo_id
            }
        },
        upsert=True
    )
    
    # Создаем уведомление
    message = f"Груз {cargo['cargo_number']} перемещен с {old_location} на {new_location} оператором {current_user.full_name}"
    
    # Уведомляем клиента
    sender_id = cargo.get("sender_id") or cargo.get("created_by")
    if sender_id and sender_id != current_user.id:
        create_notification(sender_id, message, cargo_id)
    
    # Системное уведомление
    create_system_notification(
        "Груз перемещен",
        message,
        "cargo_moved",
        cargo_id,
        None,
        current_user.id
    )
    
    return {
        "message": "Cargo moved successfully",
        "cargo_number": cargo['cargo_number'],
        "old_location": old_location,
        "new_location": new_location,
        "moved_by": current_user.full_name
    }

@app.get("/api/operator/cargo/available")
async def get_available_cargo_for_placement(
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Получаем грузы без размещения
    query = {"warehouse_location": None, "status": CargoStatus.ACCEPTED}
    if current_user.role != UserRole.ADMIN:
        query["created_by"] = current_user.id
    
    cargo_list = list(db.operator_cargo.find(query))
    # Ensure cargo_name field exists for backward compatibility
    for cargo in cargo_list:
        if 'cargo_name' not in cargo:
            cargo['cargo_name'] = cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз'
    return [CargoWithLocation(**cargo) for cargo in cargo_list]

@app.get("/api/operator/cargo/history")
async def get_cargo_history(
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Базовый запрос для доставленных грузов
    query = {"status": CargoStatus.COMPLETED}
    
    # Фильтр по создателю для операторов
    if current_user.role != UserRole.ADMIN:
        query["created_by"] = current_user.id
    
    # Дополнительные фильтры
    if status and status != "all":
        query["payment_status"] = status
    
    if search:
        query["$or"] = [
            {"cargo_number": {"$regex": search, "$options": "i"}},
            {"sender_full_name": {"$regex": search, "$options": "i"}},
            {"recipient_full_name": {"$regex": search, "$options": "i"}}
        ]
    
    cargo_list = list(db.operator_cargo.find(query).sort("updated_at", -1))
    # Ensure cargo_name field exists for backward compatibility
    for cargo in cargo_list:
        if 'cargo_name' not in cargo:
            cargo['cargo_name'] = cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз'
    return [CargoWithLocation(**cargo) for cargo in cargo_list]

@app.get("/api/warehouses/{warehouse_id}/available-cells")
async def get_available_cells(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем существование склада
    warehouse = db.warehouses.find_one({"id": warehouse_id, "is_active": True})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Получаем свободные ячейки
    available_cells = list(db.warehouse_cells.find({
        "warehouse_id": warehouse_id,
        "is_occupied": False
    }, {"_id": 0}).sort([("block_number", 1), ("shelf_number", 1), ("cell_number", 1)]))
    
    # Очищаем данные от MongoDB ObjectId
    clean_warehouse = {
        "id": warehouse["id"],
        "name": warehouse["name"], 
        "location": warehouse["location"],
        "blocks_count": warehouse["blocks_count"],
        "shelves_per_block": warehouse["shelves_per_block"],
        "cells_per_shelf": warehouse["cells_per_shelf"],
        "total_capacity": warehouse["total_capacity"],
        "created_at": warehouse["created_at"],
        "is_active": warehouse["is_active"]
    }
    
    return {
        "warehouse": clean_warehouse,
        "available_cells": available_cells,
        "total_available": len(available_cells)
    }

# Управление кассой и платежами
@app.post("/api/cashier/process-payment")
async def process_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа (администратор или кассир)
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Ищем груз по номеру
    cargo = db.operator_cargo.find_one({"cargo_number": payment_data.cargo_number})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверяем, что груз еще не оплачен
    if cargo.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Cargo already paid")
    
    # Создаем транзакцию
    transaction_id = str(uuid.uuid4())
    transaction = {
        "id": transaction_id,
        "cargo_id": cargo["id"],
        "cargo_number": cargo["cargo_number"],
        "amount_due": cargo["declared_value"],
        "amount_paid": payment_data.amount_paid,
        "payment_date": datetime.utcnow(),
        "processed_by": current_user.id,
        "customer_name": cargo["sender_full_name"],
        "customer_phone": cargo["sender_phone"],
        "transaction_type": payment_data.transaction_type,
        "notes": payment_data.notes
    }
    
    db.payment_transactions.insert_one(transaction)
    
    # Обновляем статус оплаты груза
    db.operator_cargo.update_one(
        {"id": cargo["id"]},
        {"$set": {"payment_status": "paid", "updated_at": datetime.utcnow()}}
    )
    
    # Создаем уведомление
    create_notification(
        current_user.id,
        f"Принята оплата за груз {cargo['cargo_number']} на сумму {payment_data.amount_paid} руб.",
        cargo["id"]
    )
    
    return PaymentTransaction(**transaction)

@app.get("/api/cashier/search-cargo/{cargo_number}")
async def search_cargo_for_payment(
    cargo_number: str,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Ищем груз по номеру
    cargo = db.operator_cargo.find_one({"cargo_number": cargo_number})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    return {
        "id": cargo["id"],
        "cargo_number": cargo["cargo_number"],
        "sender_full_name": cargo["sender_full_name"],
        "sender_phone": cargo["sender_phone"],
        "description": cargo["description"],
        "weight": cargo["weight"],
        "declared_value": cargo["declared_value"],
        "payment_status": cargo.get("payment_status", "pending"),
        "created_at": cargo["created_at"]
    }

@app.get("/api/cashier/unpaid-cargo")
async def get_unpaid_cargo(
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # ОБНОВЛЕНО: Фильтрация по складам оператора
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        # Оператор видит только грузы своих складов
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        if not operator_warehouse_ids:
            return []
        
        query = {
            "payment_status": {"$ne": "paid"},
            "target_warehouse_id": {"$in": operator_warehouse_ids}
        }
    else:
        # Админ видит все неоплаченные грузы
        query = {"payment_status": {"$ne": "paid"}}
    
    # Получаем неоплаченные грузы с фильтрацией по складам
    unpaid_cargo = list(db.operator_cargo.find(query).sort("created_at", -1))
    
    # Ensure cargo_name field exists for backward compatibility
    for cargo in unpaid_cargo:
        if 'cargo_name' not in cargo:
            cargo['cargo_name'] = cargo.get('description', 'Груз')[:50] if cargo.get('description') else 'Груз'
    
    return [CargoWithLocation(**cargo) for cargo in unpaid_cargo]

@app.get("/api/cashier/payment-history")
async def get_payment_history(
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # ОБНОВЛЕНО: Фильтрация истории платежей по складам оператора
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        # Оператор видит только платежи по своим складам
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        if not operator_warehouse_ids:
            return []
        
        query = {"warehouse_id": {"$in": operator_warehouse_ids}}
    else:
        # Админ видит всю историю платежей
        query = {}
    
    # Получаем историю платежей с фильтрацией
    payments = list(db.payment_transactions.find(query).sort("payment_date", -1))
    
    return [PaymentTransaction(**payment) for payment in payments]

# Получение пользователей по ролям
@app.get("/api/admin/users/by-role/{role}")
async def get_users_by_role(
    role: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    if role not in ["user", "admin", "warehouse_operator"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    users = list(db.users.find({"role": role}, {"password": 0}))
    
    # Создаем пользователей с автоматической генерацией user_number если нет
    result_users = []
    for user in users:
        user_number = user.get("user_number")
        if not user_number:
            user_number = generate_user_number()
            # Обновляем в базе данных
            db.users.update_one(
                {"id": user["id"]},
                {"$set": {"user_number": user_number}}
            )
            user["user_number"] = user_number
        
        result_users.append(User(**user))
    
    return result_users

# Получение полной схемы склада
@app.get("/api/warehouses/{warehouse_id}/full-layout")
async def get_warehouse_full_layout(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    # Проверяем права доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем существование склада
    warehouse = db.warehouses.find_one({"id": warehouse_id, "is_active": True})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Получаем все ячейки с информацией о грузах
    cells = list(db.warehouse_cells.find({"warehouse_id": warehouse_id}))
    
    # Получаем информацию о грузах в ячейках
    cargo_ids = [cell["cargo_id"] for cell in cells if cell.get("cargo_id")]
    cargo_info = {}
    if cargo_ids:
        # Поиск в обеих коллекциях
        cargo_list = list(db.cargo.find({"id": {"$in": cargo_ids}}))
        operator_cargo_list = list(db.operator_cargo.find({"id": {"$in": cargo_ids}}))
        
        # Объединить результаты
        for cargo in cargo_list:
            cargo_info[cargo["id"]] = cargo
        for cargo in operator_cargo_list:
            cargo_info[cargo["id"]] = cargo
    
    # Группируем ячейки по блокам и полкам
    layout = {}
    for cell in cells:
        block_key = f"block_{cell['block_number']}"
        shelf_key = f"shelf_{cell['shelf_number']}"
        
        if block_key not in layout:
            layout[block_key] = {"shelves": {}, "block_number": cell['block_number']}
        if shelf_key not in layout[block_key]["shelves"]:
            layout[block_key]["shelves"][shelf_key] = {"cells": [], "shelf_number": cell['shelf_number']}
        
        cell_data = {
            "id": cell["id"],
            "cell_number": cell["cell_number"],
            "location_code": cell["location_code"],
            "is_occupied": cell["is_occupied"],
            "cargo_info": None
        }
        
        if cell.get("cargo_id") and cell["cargo_id"] in cargo_info:
            cargo = cargo_info[cell["cargo_id"]]
            cell_data["cargo_info"] = {
                "cargo_number": cargo["cargo_number"],
                "sender_name": cargo.get("sender_full_name", "Не указан"),
                "recipient_name": cargo.get("recipient_full_name", cargo.get("recipient_name", "Не указан")),
                "weight": cargo["weight"],
                "description": cargo.get("description", cargo.get("cargo_name", "Груз")),
                "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")),
                "status": cargo.get("status", "unknown")
            }
        
        layout[block_key]["shelves"][shelf_key]["cells"].append(cell_data)
    
    # Сортируем ячейки
    for block in layout.values():
        for shelf in block["shelves"].values():
            shelf["cells"].sort(key=lambda x: x["cell_number"])
    
    # Статистика
    total_cells = len(cells)
    occupied_cells = len([c for c in cells if c["is_occupied"]])
    
    return {
        "warehouse": {
            "id": warehouse["id"],
            "name": warehouse["name"],
            "location": warehouse["location"],
            "blocks_count": warehouse["blocks_count"],
            "shelves_per_block": warehouse["shelves_per_block"],
            "cells_per_shelf": warehouse["cells_per_shelf"]
        },
        "layout": layout,
        "statistics": {
            "total_cells": total_cells,
            "occupied_cells": occupied_cells,
            "available_cells": total_cells - occupied_cells,
            "occupancy_rate": round((occupied_cells / total_cells) * 100, 1) if total_cells > 0 else 0
        }
    }

# Управление заявками от пользователей
@app.post("/api/user/cargo-request")
async def create_cargo_request(
    request_data: CargoRequestCreate,
    current_user: User = Depends(get_current_user)
):
    # Только обычные пользователи могут создавать заявки
    if current_user.role != UserRole.USER:
        raise HTTPException(status_code=403, detail="Only regular users can create cargo requests")
    
    request_id = str(uuid.uuid4())
    request_number = generate_request_number()
    
    cargo_request = {
        "id": request_id,
        "request_number": request_number,
        "sender_full_name": current_user.full_name,
        "sender_phone": current_user.phone,
        "recipient_full_name": request_data.recipient_full_name,
        "recipient_phone": request_data.recipient_phone,
        "recipient_address": request_data.recipient_address,
        "pickup_address": request_data.pickup_address,
        "cargo_name": request_data.cargo_name,
        "weight": request_data.weight,
        "declared_value": request_data.declared_value,
        "description": request_data.description,
        "route": request_data.route,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": current_user.id,
        "processed_by": None
    }
    
    db.cargo_requests.insert_one(cargo_request)
    
    # Создать системное уведомление для всех операторов и админов
    create_system_notification(
        "Новая заявка на груз",
        f"Пользователь {current_user.full_name} подал заявку на отправку груза №{request_number}",
        "request",
        request_id,
        None,  # Для всех операторов
        current_user.id
    )
    
    # Создать персональное уведомление для пользователя
    create_notification(
        current_user.id,
        f"Ваша заявка №{request_number} принята к рассмотрению",
        request_id
    )
    
    return CargoRequest(**cargo_request)

@app.get("/api/admin/cargo-requests")
async def get_pending_cargo_requests(
    current_user: User = Depends(get_current_user)
):
    # Только админы и операторы могут видеть заявки
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    requests = list(db.cargo_requests.find({"status": "pending"}).sort("created_at", -1))
    # Сериализация данных
    normalized_requests = []
    for request in requests:
        normalized = serialize_mongo_document(request)
        normalized.update({
            'admin_notes': request.get('admin_notes', ''),
            'processed_by': request.get('processed_by', None)
        })
        normalized_requests.append(normalized)
    
    return normalized_requests

@app.get("/api/admin/cargo-requests/all")
async def get_all_cargo_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    # Только админы и операторы могут видеть все заявки
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    query = {}
    if status and status != "all":
        query["status"] = status
    
    requests = list(db.cargo_requests.find(query).sort("created_at", -1))
    # Сериализация данных
    normalized_requests = []
    for request in requests:
        normalized = serialize_mongo_document(request)
        normalized.update({
            'admin_notes': request.get('admin_notes', ''),
            'processed_by': request.get('processed_by', None)
        })
        normalized_requests.append(normalized)
    
    return normalized_requests

@app.post("/api/admin/cargo-requests/{request_id}/accept")
async def accept_cargo_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    # Только админы и операторы могут принимать заявки
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Найти заявку
    request = db.cargo_requests.find_one({"id": request_id, "status": "pending"})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    # Создать груз на основе заявки
    cargo_id = str(uuid.uuid4())
    cargo_number = generate_cargo_number()
    
    cargo = {
        "id": cargo_id,
        "cargo_number": cargo_number,
        "sender_full_name": request["sender_full_name"],
        "sender_phone": request["sender_phone"],
        "recipient_full_name": request["recipient_full_name"],
        "recipient_phone": request["recipient_phone"],
        "recipient_address": request["recipient_address"],
        "weight": request["weight"],
        "cargo_name": request.get("cargo_name") or request.get("description", "Груз")[:50],  # Использовать cargo_name или описание
        "declared_value": request["declared_value"],
        "description": request["description"],
        "route": request["route"],
        "status": CargoStatus.ACCEPTED,
        "payment_status": "pending",
        "processing_status": "payment_pending",  # Начальный статус - ожидает оплаты
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": current_user.id,
        "created_by_operator": current_user.full_name,  # ФИО оператора
        "warehouse_location": None,
        "warehouse_id": None,
        "block_number": None,
        "shelf_number": None,
        "cell_number": None,
        "placed_by_operator": None,
        "placed_by_operator_id": None
    }
    
    db.operator_cargo.insert_one(cargo)
    
    # НОВОЕ: Создать запись о неоплаченном заказе
    unpaid_order_id = str(uuid.uuid4())
    unpaid_order = {
        "id": unpaid_order_id,
        "cargo_id": cargo_id,
        "cargo_number": cargo_number,
        "client_id": request["created_by"],
        "client_name": request["sender_full_name"],
        "client_phone": request["sender_phone"],
        "amount": request["declared_value"],  # Используем объявленную стоимость как сумму к оплате
        "description": f"Оплата за груз №{cargo_number}: {request.get('cargo_name', request.get('description', 'Груз'))}",
        "status": "unpaid",
        "created_at": datetime.utcnow(),
        "paid_at": None,
        "payment_method": None,
        "processed_by": current_user.id
    }
    
    # Сохранить в коллекцию unpaid_orders
    db.unpaid_orders.insert_one(unpaid_order)
    
    # Обновить статус заявки
    db.cargo_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "accepted",
            "processed_by": current_user.id,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Создать уведомления
    create_system_notification(
        "Заявка принята",
        f"Заявка №{request['request_number']} принята оператором {current_user.full_name} и создан груз №{cargo_number}",
        "request",
        request_id,
        None,
        current_user.id
    )
    
    create_notification(
        request["created_by"],
        f"Ваша заявка №{request['request_number']} принята! Создан груз №{cargo_number}",
        cargo_id
    )
    
    return {
        "message": "Request accepted successfully",
        "cargo_number": cargo_number,
        "cargo_id": cargo_id
    }

# НОВЫЕ ENDPOINTS ДЛЯ УПРАВЛЕНИЯ ОПЛАТАМИ

@app.get("/api/admin/unpaid-orders")
async def get_unpaid_orders(current_user: User = Depends(get_current_user)):
    """Получить список неоплаченных заказов"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    orders = list(db.unpaid_orders.find({"status": "unpaid"}).sort("created_at", -1))
    # Сериализация данных
    normalized_orders = []
    for order in orders:
        normalized = serialize_mongo_document(order)
        normalized_orders.append(normalized)
    
    return normalized_orders

@app.get("/api/admin/unpaid-orders/all")
async def get_all_orders_with_payments(current_user: User = Depends(get_current_user)):
    """Получить все заказы (оплаченные и неоплаченные)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    orders = list(db.unpaid_orders.find({}).sort("created_at", -1))
    # Сериализация данных
    normalized_orders = []
    for order in orders:
        normalized = serialize_mongo_document(order)
        normalized_orders.append(normalized)
    
    return normalized_orders

@app.post("/api/admin/unpaid-orders/{order_id}/mark-paid")
async def mark_order_as_paid(
    order_id: str,
    payment_data: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """Отметить заказ как оплаченный"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Получить способ оплаты из JSON body
    payment_method = payment_data.get("payment_method", "cash")
    
    # Найти заказ
    order = db.unpaid_orders.find_one({"id": order_id, "status": "unpaid"})
    if not order:
        raise HTTPException(status_code=404, detail="Unpaid order not found")
    
    # Обновить статус заказа
    db.unpaid_orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "paid",
            "paid_at": datetime.utcnow(),
            "payment_method": payment_method,
            "processed_by": current_user.id
        }}
    )
    
    # Обновить статус груза на "paid" и обновить processing_status
    db.operator_cargo.update_one(
        {"id": order["cargo_id"]},
        {"$set": {
            "payment_status": "paid",
            "processing_status": "paid",
            "status": CargoStatus.PAID,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Создать уведомление клиенту
    create_notification(
        order["client_id"],
        f"Оплата за груз №{order['cargo_number']} получена. Сумма: {order['amount']} рублей. Способ оплаты: {payment_method}",
        order["cargo_id"]
    )
    
    # Системное уведомление
    create_system_notification(
        "Оплата получена",
        f"Получена оплата за груз №{order['cargo_number']} от {order['client_name']}. Сумма: {order['amount']} рублей",
        "payment",
        order_id,
        order["cargo_id"],
        current_user.id
    )
    
    return {
        "message": "Order marked as paid successfully",
        "cargo_number": order["cargo_number"],
        "amount": order["amount"]
    }

@app.post("/api/admin/cargo-requests/{request_id}/reject")
async def reject_cargo_request(
    request_id: str,
    reason: str = "",
    current_user: User = Depends(get_current_user)
):
    # Только админы и операторы могут отклонять заявки
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Найти заявку
    request = db.cargo_requests.find_one({"id": request_id, "status": "pending"})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    # Обновить статус заявки
    db.cargo_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "processed_by": current_user.id,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Создать уведомления
    create_system_notification(
        "Заявка отклонена",
        f"Заявка №{request['request_number']} отклонена оператором {current_user.full_name}. Причина: {reason}",
        "request",
        request_id,
        None,
        current_user.id
    )
    
    create_notification(
        request["created_by"],
        f"К сожалению, ваша заявка №{request['request_number']} была отклонена. Причина: {reason}",
        request_id
    )
    
    return {"message": "Request rejected successfully"}

# НОВЫЕ ENDPOINTS ДЛЯ УПРАВЛЕНИЯ ЗАКАЗАМИ КЛИЕНТОВ

@app.get("/api/admin/cargo-requests/{request_id}")
async def get_cargo_request_details(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить детальную информацию о заказе"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    request = db.cargo_requests.find_one({"id": request_id})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Сериализация и нормализация данных
    normalized_request = serialize_mongo_document(request)
    normalized_request.update({
        'admin_notes': request.get('admin_notes', ''),
        'processed_by': request.get('processed_by', None)
    })
    
    return normalized_request

@app.put("/api/admin/cargo-requests/{request_id}/update")
async def update_cargo_request(
    request_id: str,
    update_data: CargoRequestUpdate,
    current_user: User = Depends(get_current_user)
):
    """Обновить информацию о заказе (получатель, отправитель, груз)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Найти заявку
    request = db.cargo_requests.find_one({"id": request_id})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Подготовить данные для обновления
    update_fields = {}
    update_fields["updated_at"] = datetime.utcnow()
    update_fields["processed_by"] = current_user.id
    
    # Обновить только те поля, которые были переданы
    if update_data.sender_full_name is not None:
        update_fields["sender_full_name"] = update_data.sender_full_name
    if update_data.sender_phone is not None:
        update_fields["sender_phone"] = update_data.sender_phone
    if update_data.recipient_full_name is not None:
        update_fields["recipient_full_name"] = update_data.recipient_full_name
    if update_data.recipient_phone is not None:
        update_fields["recipient_phone"] = update_data.recipient_phone
    if update_data.recipient_address is not None:
        update_fields["recipient_address"] = update_data.recipient_address
    if update_data.pickup_address is not None:
        update_fields["pickup_address"] = update_data.pickup_address
    if update_data.cargo_name is not None:
        update_fields["cargo_name"] = update_data.cargo_name
    if update_data.weight is not None:
        update_fields["weight"] = update_data.weight
    if update_data.declared_value is not None:
        update_fields["declared_value"] = update_data.declared_value
    if update_data.description is not None:
        update_fields["description"] = update_data.description
    if update_data.route is not None:
        update_fields["route"] = update_data.route
    if update_data.admin_notes is not None:
        update_fields["admin_notes"] = update_data.admin_notes
    
    # Обновить заявку
    db.cargo_requests.update_one(
        {"id": request_id},
        {"$set": update_fields}
    )
    
    # Создать системное уведомление об изменении
    create_system_notification(
        "Заказ обновлен",
        f"Заказ №{request['request_number']} был обновлен оператором {current_user.full_name}",
        "request_updated",
        request_id,
        None,
        current_user.id
    )
    
    # Уведомить клиента об изменениях
    create_notification(
        request["created_by"],
        f"Информация по вашему заказу №{request['request_number']} была обновлена. Проверьте детали в личном кабинете.",
        request_id
    )
    
    return {"message": "Request updated successfully", "request_id": request_id}

@app.get("/api/admin/new-orders-count")
async def get_new_orders_count(
    current_user: User = Depends(get_current_user)
):
    """Получить количество новых заказов для уведомлений"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Подсчитать количество pending заявок
    pending_count = db.cargo_requests.count_documents({"status": "pending"})
    
    # Подсчитать количество заявок, созданных за последние 24 часа
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    new_today_count = db.cargo_requests.count_documents({
        "created_at": {"$gte": twenty_four_hours_ago},
        "status": "pending"
    })
    
    return {
        "pending_orders": pending_count,
        "new_today": new_today_count,
        "has_new_orders": pending_count > 0
    }

# Системные уведомления
@app.get("/api/system-notifications")
async def get_system_notifications(
    notification_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    
    # Операторы и админы видят все уведомления, пользователи - только свои
    if current_user.role == UserRole.USER:
        query["$or"] = [
            {"user_id": current_user.id},
            {"user_id": None, "notification_type": {"$in": ["cargo_status", "payment"]}}
        ]
    
    if notification_type and notification_type != "all":
        query["notification_type"] = notification_type
    
    notifications = list(db.system_notifications.find(query).sort("created_at", -1).limit(100))
    return [SystemNotification(**notification) for notification in notifications]

@app.get("/api/user/my-requests")
async def get_my_cargo_requests(
    current_user: User = Depends(get_current_user)
):
    # Пользователи могут видеть только свои заявки
    requests = list(db.cargo_requests.find({"created_by": current_user.id}).sort("created_at", -1))
    return [CargoRequest(**request) for request in requests]

@app.get("/api/user/dashboard")
async def get_personal_dashboard(
    current_user: User = Depends(get_current_user)
):
    """Получить данные личного кабинета пользователя"""
    try:
        # Информация о пользователе
        user_info = current_user
        
        # История заявок на грузы (как отправитель)
        cargo_requests = []
        requests = list(db.cargo_requests.find(
            {"created_by": current_user.id}
        ).sort("created_at", -1).limit(50))
        
        for request in requests:
            cargo_requests.append({
                "id": request["id"],
                "cargo_name": request.get("cargo_name", "Груз"),
                "weight": request.get("weight", 0),
                "declared_value": request.get("declared_value", 0),
                "recipient_name": request.get("recipient_name", "Не указан"),
                "recipient_phone": request.get("recipient_phone", "Не указан"),
                "recipient_address": request.get("recipient_address", "Не указан"),
                "status": request.get("status", "pending"),
                "created_at": request.get("created_at"),
                "route": request.get("route", "moscow_to_tajikistan"),
                "type": "cargo_request"
            })
        
        # История отправленных грузов (как отправитель)
        sent_cargo = []
        # Поиск в пользовательских грузах
        user_cargo = list(db.cargo.find(
            {"sender_phone": current_user.phone}
        ).sort("created_at", -1).limit(50))
        
        for cargo in user_cargo:
            sent_cargo.append({
                "id": cargo["id"],
                "cargo_number": cargo.get("cargo_number", "N/A"),
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "weight": cargo.get("weight", 0),
                "declared_value": cargo.get("declared_value", 0),
                "recipient_name": cargo.get("recipient_full_name", "Не указан"),
                "recipient_phone": cargo.get("recipient_phone", "Не указан"),
                "status": cargo.get("status", "accepted"),
                "payment_status": cargo.get("payment_status", "pending"),
                "created_at": cargo.get("created_at"),
                "route": cargo.get("route", "moscow_to_tajikistan"),
                "warehouse_location": cargo.get("warehouse_location"),
                "type": "user_cargo"
            })
        
        # Поиск в операторских грузах
        operator_cargo = list(db.operator_cargo.find(
            {"sender_phone": current_user.phone}
        ).sort("created_at", -1).limit(50))
        
        for cargo in operator_cargo:
            sent_cargo.append({
                "id": cargo["id"],
                "cargo_number": cargo.get("cargo_number", "N/A"),
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "weight": cargo.get("weight", 0),
                "declared_value": cargo.get("declared_value", 0),
                "recipient_name": cargo.get("recipient_full_name", "Не указан"),
                "recipient_phone": cargo.get("recipient_phone", "Не указан"),
                "status": cargo.get("status", "accepted"),
                "payment_status": cargo.get("payment_status", "pending"),
                "processing_status": cargo.get("processing_status", "payment_pending"),
                "created_at": cargo.get("created_at"),
                "route": cargo.get("route", "moscow_to_tajikistan"),
                "warehouse_location": cargo.get("warehouse_location"),
                "created_by_operator": cargo.get("created_by_operator"),
                "type": "operator_cargo"
            })
        
        # История полученных грузов (как получатель)
        received_cargo = []
        # Поиск по номеру телефона получателя
        received_user_cargo = list(db.cargo.find(
            {"recipient_phone": current_user.phone}
        ).sort("created_at", -1).limit(50))
        
        for cargo in received_user_cargo:
            received_cargo.append({
                "id": cargo["id"],
                "cargo_number": cargo.get("cargo_number", "N/A"),
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "weight": cargo.get("weight", 0),
                "declared_value": cargo.get("declared_value", 0),
                "sender_name": cargo.get("sender_full_name", "Не указан"),
                "sender_phone": cargo.get("sender_phone", "Не указан"),
                "status": cargo.get("status", "accepted"),
                "payment_status": cargo.get("payment_status", "pending"),
                "created_at": cargo.get("created_at"),
                "route": cargo.get("route", "moscow_to_tajikistan"),
                "warehouse_location": cargo.get("warehouse_location"),
                "type": "received_user_cargo"
            })
        
        received_operator_cargo = list(db.operator_cargo.find(
            {"recipient_phone": current_user.phone}
        ).sort("created_at", -1).limit(50))
        
        for cargo in received_operator_cargo:
            received_cargo.append({
                "id": cargo["id"],
                "cargo_number": cargo.get("cargo_number", "N/A"),
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "weight": cargo.get("weight", 0),
                "declared_value": cargo.get("declared_value", 0),
                "sender_name": cargo.get("sender_full_name", "Не указан"),
                "sender_phone": cargo.get("sender_phone", "Не указан"),
                "status": cargo.get("status", "accepted"),
                "payment_status": cargo.get("payment_status", "pending"),
                "processing_status": cargo.get("processing_status", "payment_pending"),
                "created_at": cargo.get("created_at"),
                "route": cargo.get("route", "moscow_to_tajikistan"),
                "warehouse_location": cargo.get("warehouse_location"),
                "created_by_operator": cargo.get("created_by_operator"),
                "type": "received_operator_cargo"
            })
        
        # Сортируем все грузы по дате
        sent_cargo.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        received_cargo.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        
        return PersonalDashboard(
            user_info=user_info,
            cargo_requests=cargo_requests[:20],  # Ограничиваем количество
            sent_cargo=sent_cargo[:20],
            received_cargo=received_cargo[:20]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard data: {str(e)}")

# === УПРАВЛЕНИЕ ОПЕРАТОРАМИ И СКЛАДАМИ ===

@app.post("/api/admin/operator-warehouse-binding")
async def create_operator_warehouse_binding(
    binding_data: OperatorWarehouseBindingCreate,
    current_user: User = Depends(get_current_user)
):
    # Только админы могут создавать привязки
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create operator-warehouse bindings")
    
    # Проверить, что оператор существует и имеет роль warehouse_operator
    operator = db.users.find_one({"id": binding_data.operator_id})
    if not operator or operator["role"] != UserRole.WAREHOUSE_OPERATOR:
        raise HTTPException(status_code=404, detail="Warehouse operator not found")
    
    # Проверить, что склад существует
    warehouse = db.warehouses.find_one({"id": binding_data.warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Проверить, что привязка не существует
    existing_binding = db.operator_warehouse_bindings.find_one({
        "operator_id": binding_data.operator_id,
        "warehouse_id": binding_data.warehouse_id
    })
    if existing_binding:
        raise HTTPException(status_code=400, detail="Binding already exists")
    
    # Создать привязку
    binding_id = str(uuid.uuid4())
    binding = {
        "id": binding_id,
        "operator_id": binding_data.operator_id,
        "operator_name": operator["full_name"],
        "operator_phone": operator["phone"],
        "warehouse_id": binding_data.warehouse_id,
        "warehouse_name": warehouse["name"],
        "created_at": datetime.utcnow(),
        "created_by": current_user.id
    }
    
    db.operator_warehouse_bindings.insert_one(binding)
    
    # Создать системное уведомление
    create_system_notification(
        "Привязка оператора к складу",
        f"Оператор {operator['full_name']} привязан к складу {warehouse['name']}",
        "operator_binding",
        binding_id,
        None,
        current_user.id
    )
    
    return {"message": "Operator-warehouse binding created successfully", "binding_id": binding_id}

@app.get("/api/admin/operator-warehouse-bindings")
async def get_operator_warehouse_bindings(
    current_user: User = Depends(get_current_user)
):
    # Только админы могут просматривать привязки
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    bindings = list(db.operator_warehouse_bindings.find({}).sort("created_at", -1))
    # Serialize and ensure all required fields exist
    normalized_bindings = []
    for binding in bindings:
        normalized = serialize_mongo_document(binding)
        # Ensure all required fields exist with defaults
        normalized.update({
            'operator_phone': binding.get('operator_phone', 'Не указан'),
            'operator_name': binding.get('operator_name', 'Не указан'),
            'warehouse_name': binding.get('warehouse_name', 'Не указан')
        })
        normalized_bindings.append(normalized)
    
    return normalized_bindings

@app.delete("/api/admin/operator-warehouse-binding/{binding_id}")
async def delete_operator_warehouse_binding(
    binding_id: str,
    current_user: User = Depends(get_current_user)
):
    # Только админы могут удалять привязки
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    binding = db.operator_warehouse_bindings.find_one({"id": binding_id})
    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")
    
    db.operator_warehouse_bindings.delete_one({"id": binding_id})
    
    # Создать системное уведомление
    create_system_notification(
        "Удалена привязка оператора к складу",
        f"Удалена привязка оператора {binding['operator_name']} к складу {binding['warehouse_name']}",
        "operator_binding",
        binding_id,
        None,
        current_user.id
    )
    
    return {"message": "Operator-warehouse binding deleted successfully"}

@app.post("/api/admin/create-operator")
async def create_operator_by_admin(
    operator_data: OperatorCreate,
    current_user: User = Depends(get_current_user)
):
    """Создание оператора склада админом (Функция 2)"""
    # Только админы могут создавать операторов
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверка существования пользователя с таким телефоном
    if db.users.find_one({"phone": operator_data.phone}):
        raise HTTPException(status_code=400, detail="User with this phone already exists")
    
    # Проверка существования склада
    warehouse = db.warehouses.find_one({"id": operator_data.warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Создание оператора
    operator_id = str(uuid.uuid4())
    
    # Генерируем user_number для оператора
    user_number = generate_user_number()
    
    operator = {
        "id": operator_id,
        "user_number": user_number,
        "full_name": operator_data.full_name,
        "phone": operator_data.phone,
        "address": operator_data.address,  # Адрес проживания
        "password_hash": hash_password(operator_data.password),  # ИСПРАВЛЕНО: было "password"
        "role": UserRole.WAREHOUSE_OPERATOR.value,  # Всегда оператор склада
        "is_active": True,
        "token_version": 1,  # Начальная версия токена
        "created_at": datetime.utcnow(),
        "created_by": current_user.id,  # Кто создал
        "created_by_name": current_user.full_name
    }
    
    db.users.insert_one(operator)
    
    # Автоматически создать привязку к складу
    binding_id = str(uuid.uuid4())
    binding = {
        "id": binding_id,
        "operator_id": operator_id,
        "operator_name": operator_data.full_name,
        "warehouse_id": operator_data.warehouse_id,
        "warehouse_name": warehouse["name"],
        "created_at": datetime.utcnow(),
        "created_by": current_user.id,
        "created_by_name": current_user.full_name
    }
    
    db.operator_warehouse_bindings.insert_one(binding)
    
    # Создать системное уведомление
    create_system_notification(
        "Создан новый оператор склада",
        f"Админ {current_user.full_name} создал оператора {operator_data.full_name} для склада {warehouse['name']}",
        "operator_created",
        operator_id,
        {
            "operator_name": operator_data.full_name,
            "warehouse_name": warehouse["name"],
            "phone": operator_data.phone
        },
        current_user.id
    )
    
    return {
        "message": "Operator created successfully",
        "operator": OperatorResponse(
            id=operator_id,
            full_name=operator_data.full_name,
            phone=operator_data.phone,
            address=operator_data.address,
            role=UserRole.WAREHOUSE_OPERATOR.value,
            warehouse_id=operator_data.warehouse_id,
            warehouse_name=warehouse["name"],
            is_active=True,
            created_at=datetime.utcnow(),
            created_by=current_user.full_name
        ),
        "binding_id": binding_id
    }

@app.get("/api/admin/operators")
async def get_all_operators(
    current_user: User = Depends(get_current_user)
):
    """Получить всех операторов с информацией о складах"""
    # Только админы могут просматривать операторов
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получить всех операторов
    operators = list(db.users.find(
        {"role": UserRole.WAREHOUSE_OPERATOR.value},
        {"password": 0, "_id": 0}
    ).sort("created_at", -1))
    
    # Получить привязки складов для каждого оператора
    operators_with_warehouses = []
    for operator in operators:
        # Найти привязки оператора к складам
        bindings = list(db.operator_warehouse_bindings.find({"operator_id": operator["id"]}))
        
        warehouses = []
        for binding in bindings:
            warehouse = db.warehouses.find_one({"id": binding["warehouse_id"]})
            if warehouse:
                warehouses.append({
                    "id": warehouse["id"],
                    "name": warehouse["name"],
                    "location": warehouse["location"],
                    "binding_id": binding["id"]
                })
        
        operator_with_warehouses = {
            **operator,
            "warehouses": warehouses,
            "warehouses_count": len(warehouses)
        }
        operators_with_warehouses.append(operator_with_warehouses)
    
    return {
        "operators": serialize_mongo_document(operators_with_warehouses),
        "total_operators": len(operators_with_warehouses)
    }



@app.get("/api/transport/available-cargo")
async def get_available_cargo_for_transport_endpoint(
    current_user: User = Depends(get_current_user)
):
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    available_cargo = get_available_cargo_for_transport(current_user.id, current_user.role)
    return available_cargo

@app.get("/api/cargo/search")
async def search_cargo_detailed(
    query: str = "",
    search_type: str = "all",  # all, number, sender_name, recipient_name, phone, cargo_name
    current_user: User = Depends(get_current_user)
):
    """Расширенный поиск грузов с детальными карточками и функциями (Функция 4)"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
    
    query = query.strip()
    
    # Построить поисковые критерии
    search_criteria = []
    
    if search_type == "all" or search_type == "number":
        search_criteria.append({"cargo_number": {"$regex": query, "$options": "i"}})
    
    if search_type == "all" or search_type == "sender_name":
        search_criteria.append({"sender_full_name": {"$regex": query, "$options": "i"}})
    
    if search_type == "all" or search_type == "recipient_name":
        search_criteria.append({"recipient_full_name": {"$regex": query, "$options": "i"}})
        search_criteria.append({"recipient_name": {"$regex": query, "$options": "i"}})
    
    if search_type == "all" or search_type == "phone":
        # Экранируем специальные символы regex для безопасного поиска телефонов
        escaped_query = escape_regex_special_chars(query)
        search_criteria.append({"sender_phone": {"$regex": escaped_query, "$options": "i"}})
        search_criteria.append({"recipient_phone": {"$regex": escaped_query, "$options": "i"}})
    
    if search_type == "all" or search_type == "cargo_name":
        search_criteria.append({"cargo_name": {"$regex": query, "$options": "i"}})
        search_criteria.append({"description": {"$regex": query, "$options": "i"}})
    
    if not search_criteria:
        return {"results": [], "total_found": 0, "search_query": query, "search_type": search_type}
    
    # Поиск в коллекции пользовательских грузов
    user_cargo_query = {"$or": search_criteria}
    user_cargo = list(db.cargo.find(user_cargo_query, {"_id": 0}).limit(30))
    
    # Поиск в коллекции операторских грузов  
    operator_cargo = list(db.operator_cargo.find(user_cargo_query, {"_id": 0}).limit(30))
    
    # Объединить результаты
    all_results = user_cargo + operator_cargo
    
    # Сортировать по релевантности (точные совпадения номера сначала)
    if search_type == "number" or query.isdigit():
        all_results.sort(key=lambda x: 0 if x.get("cargo_number", "").lower() == query.lower() else 1)
    
    # Обогащаем каждый результат дополнительными данными и функциями
    enriched_results = []
    for cargo in all_results[:30]:  # Ограничить до 30 результатов
        cargo_id = cargo["id"]
        
        # Получаем информацию о расположении груза
        warehouse_info = None
        location_info = None
        
        if cargo.get("warehouse_id"):
            warehouse = db.warehouses.find_one({"id": cargo["warehouse_id"]}, {"_id": 0})
            if warehouse:
                warehouse_info = {
                    "id": warehouse["id"],
                    "name": warehouse["name"],
                    "location": warehouse["location"]
                }
                
                # Информация о конкретной ячейке
                if cargo.get("block_number") and cargo.get("shelf_number") and cargo.get("cell_number"):
                    location_info = {
                        "block": cargo["block_number"],
                        "shelf": cargo["shelf_number"], 
                        "cell": cargo["cell_number"],
                        "location_code": f"Б{cargo['block_number']}-П{cargo['shelf_number']}-Я{cargo['cell_number']}"
                    }
        
        # Получаем информацию о транспорте (если груз на транспорте)
        transport_info = None
        if cargo.get("transport_id"):
            transport = db.transports.find_one({"id": cargo["transport_id"]}, {"_id": 0})
            if transport:
                transport_info = {
                    "id": transport["id"],
                    "transport_number": transport["transport_number"],
                    "driver_name": transport["driver_name"],
                    "status": transport["status"],
                    "direction": transport["direction"]
                }
        
        # Получаем информацию об операторах
        operator_info = {
            "created_by_operator": cargo.get("created_by_operator"),
            "placed_by_operator": cargo.get("placed_by_operator"),
            "updated_by_operator": cargo.get("updated_by_operator")
        }
        
        # Определяем доступные функции для этого груза
        available_functions = {
            "view_details": True,
            "edit_cargo": True,
            "move_between_cells": cargo.get("status") == "placed_in_warehouse",
            "remove_from_cell": cargo.get("status") == "placed_in_warehouse", 
            "place_on_transport": cargo.get("status") in ["placed_in_warehouse", "accepted"],
            "process_payment": cargo.get("payment_status") == "pending",
            "print_invoice": True,
            "generate_qr_code": True,
            "track_cargo": True,
            "add_notes": True
        }
        
        # Подсчитываем финансовую информацию
        payment_info = {
            "declared_value": cargo.get("declared_value", 0),
            "payment_status": cargo.get("payment_status", "pending"),
            "amount_paid": 0,  # Можно получить из коллекции payments если нужно
            "amount_due": cargo.get("declared_value", 0)
        }
        
        # Создаем обогащенную карточку груза
        enriched_cargo = {
            # Основная информация о грузе
            "id": cargo["id"],
            "cargo_number": cargo["cargo_number"],
            "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")[:50]),
            "description": cargo.get("description", ""),
            "weight": cargo.get("weight", 0),
            "status": cargo.get("status", "unknown"),
            "created_at": cargo.get("created_at"),
            "updated_at": cargo.get("updated_at"),
            
            # Информация об отправителе
            "sender": {
                "full_name": cargo.get("sender_full_name", "Не указано"),
                "phone": cargo.get("sender_phone", "Не указано")
            },
            
            # Информация о получателе  
            "recipient": {
                "full_name": cargo.get("recipient_full_name", "Не указано"),
                "phone": cargo.get("recipient_phone", "Не указано"),
                "address": cargo.get("recipient_address", "Не указано")
            },
            
            # Расположение груза
            "location": {
                "warehouse": warehouse_info,
                "cell": location_info,
                "transport": transport_info,
                "status_description": _get_location_description(cargo)
            },
            
            # Информация об операторах
            "operators": operator_info,
            
            # Финансовая информация
            "payment": payment_info,
            
            # Доступные функции
            "available_functions": available_functions,
            
            # Дополнительные поля
            "route": cargo.get("route", "unknown"),
            "qr_code": cargo.get("qr_code", ""),
            "collection_source": "operator_cargo" if cargo.get("created_by_operator") else "cargo"
        }
        
        enriched_results.append(enriched_cargo)
    
    return {
        "results": enriched_results,
        "total_found": len(enriched_results),
        "search_query": query,
        "search_type": search_type,
        "user_role": current_user.role,
        "user_name": current_user.full_name,
        "search_performed_at": datetime.utcnow(),
        "available_search_types": [
            {"value": "all", "label": "Все поля"},
            {"value": "number", "label": "По номеру"},
            {"value": "sender_name", "label": "По ФИО отправителя"},
            {"value": "recipient_name", "label": "По ФИО получателя"},
            {"value": "phone", "label": "По телефону"},
            {"value": "cargo_name", "label": "По названию груза"}
        ]
    }

def _get_location_description(cargo):
    """Получить описание местоположения груза"""
    status = cargo.get("status", "unknown")
    
    if status == "placed_in_warehouse" and cargo.get("warehouse_id"):
        if cargo.get("block_number"):
            return f"На складе в ячейке Б{cargo['block_number']}-П{cargo['shelf_number']}-Я{cargo['cell_number']}"
        else:
            return "На складе (ячейка не указана)"
    elif status == "on_transport" and cargo.get("transport_id"):
        return "На транспорте"
    elif status == "in_transit":
        return "В пути"
    elif status == "accepted":
        return "Принят, ожидает размещения"
    elif status == "delivered":
        return "Доставлен"
    elif status == "arrived_destination":
        return "Прибыл в пункт назначения"
    else:
        return f"Статус: {status}"

@app.post("/api/search/advanced")
async def advanced_search(
    search_request: AdvancedSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """Расширенный поиск с фильтрами и сортировкой"""
    import time
    start_time = time.time()
    
    try:
        results = []
        total_count = 0
        
        if search_request.search_type in ["all", "cargo"]:
            cargo_results = await search_cargo_advanced(search_request, current_user)
            results.extend(cargo_results)
        
        if search_request.search_type in ["all", "users"] and current_user.role in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
            user_results = await search_users_advanced(search_request, current_user)
            results.extend(user_results)
        
        if search_request.search_type in ["all", "warehouses"] and current_user.role in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
            warehouse_results = await search_warehouses_advanced(search_request, current_user)
            results.extend(warehouse_results)
        
        # Сортировка результатов
        if search_request.sort_by:
            reverse_order = search_request.sort_order == "desc"
            if search_request.sort_by == "relevance_score":
                results.sort(key=lambda x: x.relevance_score or 0, reverse=reverse_order)
            elif search_request.sort_by == "created_at":
                results.sort(key=lambda x: x.details.get("created_at", ""), reverse=reverse_order)
        
        # Пагинация
        page = max(1, search_request.page or 1)
        per_page = min(100, max(1, search_request.per_page or 20))
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        total_count = len(results)
        paginated_results = results[start_idx:end_idx]
        total_pages = (total_count + per_page - 1) // per_page
        
        # Генерация предложений для автодополнения
        suggestions = await generate_search_suggestions(search_request.query, current_user)
        
        search_time_ms = int((time.time() - start_time) * 1000)
        
        return AdvancedSearchResponse(
            results=paginated_results,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            search_time_ms=search_time_ms,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

async def search_cargo_advanced(search_request: AdvancedSearchRequest, current_user: User) -> List[SearchResult]:
    """Поиск грузов с расширенными фильтрами"""
    cargo_results = []
    
    # Построение запроса для поиска грузов
    search_criteria = {}
    
    # Текстовый поиск
    if search_request.query:
        query = search_request.query.strip()
        text_search = {
            "$or": [
                {"cargo_number": {"$regex": query, "$options": "i"}},
                {"cargo_name": {"$regex": query, "$options": "i"}},
                {"sender_full_name": {"$regex": query, "$options": "i"}},
                {"recipient_full_name": {"$regex": query, "$options": "i"}},
                {"sender_phone": {"$regex": query, "$options": "i"}},
                {"recipient_phone": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}}
            ]
        }
        search_criteria.update(text_search)
    
    # Фильтр по статусу
    if search_request.cargo_status:
        search_criteria["status"] = search_request.cargo_status
    
    if search_request.payment_status:
        search_criteria["payment_status"] = search_request.payment_status
    
    if search_request.processing_status:
        search_criteria["processing_status"] = search_request.processing_status
    
    if search_request.route:
        search_criteria["route"] = search_request.route
    
    if search_request.sender_phone:
        import re
        escaped_phone = re.escape(search_request.sender_phone)
        search_criteria["sender_phone"] = {"$regex": escaped_phone, "$options": "i"}
    
    if search_request.recipient_phone:
        import re
        escaped_phone = re.escape(search_request.recipient_phone)
        search_criteria["recipient_phone"] = {"$regex": escaped_phone, "$options": "i"}
    
    # Фильтр по дате
    if search_request.date_from or search_request.date_to:
        date_filter = {}
        if search_request.date_from:
            date_filter["$gte"] = datetime.fromisoformat(search_request.date_from.replace('Z', '+00:00'))
        if search_request.date_to:
            date_filter["$lte"] = datetime.fromisoformat(search_request.date_to.replace('Z', '+00:00'))
        search_criteria["created_at"] = date_filter
    
    # Поиск в коллекциях грузов
    for collection_name in ["cargo", "operator_cargo"]:
        collection = getattr(db, collection_name)
        cargo_list = list(collection.find(search_criteria, {"_id": 0}).limit(50))
        
        for cargo in cargo_list:
            relevance_score = calculate_cargo_relevance(cargo, search_request.query)
            
            # Формируем результат поиска
            result = SearchResult(
                type="cargo",
                id=cargo["id"],
                title=f"{cargo.get('cargo_number', 'N/A')} - {cargo.get('cargo_name', 'Груз')}",
                subtitle=f"{cargo.get('sender_full_name', 'Неизвестно')} → {cargo.get('recipient_full_name', 'Неизвестно')}",
                details={
                    "cargo_number": cargo.get("cargo_number"),
                    "cargo_name": cargo.get("cargo_name"),
                    "weight": cargo.get("weight"),
                    "declared_value": cargo.get("declared_value"),
                    "status": cargo.get("status"),
                    "payment_status": cargo.get("payment_status"),
                    "processing_status": cargo.get("processing_status"),
                    "route": cargo.get("route"),
                    "sender_full_name": cargo.get("sender_full_name"),
                    "sender_phone": cargo.get("sender_phone"),
                    "recipient_full_name": cargo.get("recipient_full_name"),
                    "recipient_phone": cargo.get("recipient_phone"),
                    "created_at": cargo.get("created_at"),
                    "warehouse_location": cargo.get("warehouse_location"),
                    "collection": collection_name
                },
                relevance_score=relevance_score
            )
            cargo_results.append(result)
    
    return cargo_results

async def search_users_advanced(search_request: AdvancedSearchRequest, current_user: User) -> List[SearchResult]:
    """Поиск пользователей с фильтрами"""
    user_results = []
    
    search_criteria = {}
    
    # Текстовый поиск по пользователям
    if search_request.query:
        query = search_request.query.strip()
        search_criteria["$or"] = [
            {"full_name": {"$regex": query, "$options": "i"}},
            {"phone": {"$regex": query, "$options": "i"}},
            {"user_number": {"$regex": query, "$options": "i"}}
        ]
    
    # Фильтры пользователей
    if search_request.user_role:
        search_criteria["role"] = search_request.user_role
    
    if search_request.user_status is not None:
        search_criteria["is_active"] = search_request.user_status
    
    users = list(db.users.find(search_criteria, {"password": 0, "_id": 0}).limit(20))
    
    for user in users:
        relevance_score = calculate_user_relevance(user, search_request.query)
        
        result = SearchResult(
            type="user",
            id=user["id"],
            title=f"{user.get('user_number', 'N/A')} - {user['full_name']}",
            subtitle=f"{user['phone']} ({user['role']})",
            details={
                "user_number": user.get("user_number"),
                "full_name": user["full_name"],
                "phone": user["phone"],
                "role": user["role"],
                "is_active": user["is_active"],
                "created_at": user.get("created_at")
            },
            relevance_score=relevance_score
        )
        user_results.append(result)
    
    return user_results

async def search_warehouses_advanced(search_request: AdvancedSearchRequest, current_user: User) -> List[SearchResult]:
    """Поиск складов с фильтрами"""
    warehouse_results = []
    
    search_criteria = {}
    
    # Текстовый поиск по складам
    if search_request.query:
        query = search_request.query.strip()
        search_criteria["$or"] = [
            {"name": {"$regex": query, "$options": "i"}},
            {"location": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    
    warehouses = list(db.warehouses.find(search_criteria, {"_id": 0}).limit(10))
    
    for warehouse in warehouses:
        # Подсчитаем количество грузов на складе
        cargo_count = db.operator_cargo.count_documents({"warehouse_id": warehouse["id"]})
        
        relevance_score = calculate_warehouse_relevance(warehouse, search_request.query)
        
        result = SearchResult(
            type="warehouse",
            id=warehouse["id"],
            title=warehouse["name"],
            subtitle=f"{warehouse.get('location', 'Местоположение не указано')} ({cargo_count} грузов)",
            details={
                "name": warehouse["name"],
                "location": warehouse.get("location"),
                "description": warehouse.get("description"),
                "cargo_count": cargo_count,
                "structure": warehouse.get("structure", {}),
                "created_at": warehouse.get("created_at")
            },
            relevance_score=relevance_score
        )
        warehouse_results.append(result)
    
    return warehouse_results

def calculate_cargo_relevance(cargo: dict, query: str) -> float:
    """Расчет релевантности груза"""
    if not query:
        return 1.0
    
    query = query.lower()
    score = 0.0
    
    # Точное совпадение номера груза - максимальная релевантность
    if cargo.get("cargo_number", "").lower() == query:
        score += 100.0
    elif query in cargo.get("cargo_number", "").lower():
        score += 50.0
    
    # Совпадение в названии груза
    if query in cargo.get("cargo_name", "").lower():
        score += 30.0
    
    # Совпадение в именах отправителя/получателя
    if query in cargo.get("sender_full_name", "").lower():
        score += 20.0
    if query in cargo.get("recipient_full_name", "").lower():
        score += 20.0
    
    # Совпадение в телефонах
    if query in cargo.get("sender_phone", "").lower():
        score += 25.0
    if query in cargo.get("recipient_phone", "").lower():
        score += 25.0
    
    return min(score, 100.0)

def calculate_user_relevance(user: dict, query: str) -> float:
    """Расчет релевантности пользователя"""
    if not query:
        return 1.0
    
    query = query.lower()
    score = 0.0
    
    # Точное совпадение номера пользователя
    if user.get("user_number", "").lower() == query:
        score += 100.0
    elif query in user.get("user_number", "").lower():
        score += 70.0
    
    # Совпадение в имени
    if query in user.get("full_name", "").lower():
        score += 50.0
    
    # Совпадение в телефоне
    if query in user.get("phone", "").lower():
        score += 60.0
    
    return min(score, 100.0)

def calculate_warehouse_relevance(warehouse: dict, query: str) -> float:
    """Расчет релевантности склада"""
    if not query:
        return 1.0
    
    query = query.lower()
    score = 0.0
    
    # Совпадение в названии склада
    if query in warehouse.get("name", "").lower():
        score += 70.0
    
    # Совпадение в местоположении
    if query in warehouse.get("location", "").lower():
        score += 50.0
    
    # Совпадение в описании
    if query in warehouse.get("description", "").lower():
        score += 30.0
    
    return min(score, 100.0)

async def generate_search_suggestions(query: str, current_user: User) -> List[str]:
    """Генерация предложений для автодополнения"""
    if not query or len(query) < 2:
        return []
    
    suggestions = []
    query_lower = query.lower()
    
    # Предложения на основе номеров грузов
    cargo_numbers = []
    for collection_name in ["cargo", "operator_cargo"]:
        collection = getattr(db, collection_name)
        cargo_docs = collection.find(
            {"cargo_number": {"$regex": f"^{query}", "$options": "i"}},
            {"cargo_number": 1, "_id": 0}
        ).limit(5)
        cargo_numbers.extend([doc["cargo_number"] for doc in cargo_docs])
    
    suggestions.extend(cargo_numbers[:3])
    
    # Предложения на основе имен
    if current_user.role in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        # Имена отправителей/получателей
        name_suggestions = []
        for collection_name in ["cargo", "operator_cargo"]:
            collection = getattr(db, collection_name)
            sender_docs = collection.find(
                {"sender_full_name": {"$regex": query, "$options": "i"}},
                {"sender_full_name": 1, "_id": 0}
            ).limit(3)
            name_suggestions.extend([doc["sender_full_name"] for doc in sender_docs])
        
        suggestions.extend(name_suggestions[:2])
    
    return list(set(suggestions))[:5]  # Убираем дубликаты и ограничиваем до 5

# === НОВЫЕ API ЭТАПА 1: ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ГРУЗОВ ===

@app.post("/api/cargo/photo/upload")
async def upload_cargo_photo(
    photo_data: CargoPhotoUpload,
    current_user: User = Depends(get_current_user)
):
    """Загрузить фото груза"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверяем существование груза
    cargo = db.cargo.find_one({"id": photo_data.cargo_id})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": photo_data.cargo_id})
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Валидация base64 изображения
    try:
        image_data = base64.b64decode(photo_data.photo_data.split(',')[1] if ',' in photo_data.photo_data else photo_data.photo_data)
        image = Image.open(BytesIO(image_data))
        
        # Получаем размер изображения
        photo_size = len(image_data)
        
        # Ограничиваем размер до 5MB
        if photo_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Photo size too large (max 5MB)")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image data")
    
    # Создаем запись фото
    photo_id = str(uuid.uuid4())
    photo = {
        "id": photo_id,
        "cargo_id": photo_data.cargo_id,
        "cargo_number": cargo["cargo_number"],
        "photo_data": photo_data.photo_data,
        "photo_name": photo_data.photo_name,
        "photo_size": photo_size,
        "uploaded_by": current_user.id,
        "uploaded_by_name": current_user.full_name,
        "upload_date": datetime.utcnow(),
        "photo_type": photo_data.photo_type,
        "description": photo_data.description
    }
    
    db.cargo_photos.insert_one(photo)
    
    # Добавляем в историю груза
    add_cargo_history(
        photo_data.cargo_id,
        cargo["cargo_number"],
        "photo_uploaded",
        None,
        None,
        photo_data.photo_type,
        f"Загружено фото: {photo_data.photo_name}",
        current_user.id,
        current_user.full_name,
        current_user.role,
        {"photo_id": photo_id, "photo_type": photo_data.photo_type}
    )
    
    # Создаем уведомление
    create_notification(
        current_user.id,
        f"Загружено фото для груза {cargo['cargo_number']}",
        photo_data.cargo_id
    )
    
    return {
        "message": "Photo uploaded successfully",
        "photo_id": photo_id,
        "cargo_number": cargo["cargo_number"],
        "photo_size": photo_size
    }

@app.get("/api/cargo/{cargo_id}/photos")
async def get_cargo_photos(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить все фото груза"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверяем существование груза
    cargo = db.cargo.find_one({"id": cargo_id})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Получаем фото
    photos = list(db.cargo_photos.find({"cargo_id": cargo_id}, {"_id": 0}).sort("upload_date", -1))
    
    return {
        "cargo_id": cargo_id,
        "cargo_number": cargo["cargo_number"],
        "photos": photos,
        "total_photos": len(photos)
    }

@app.delete("/api/cargo/photo/{photo_id}")
async def delete_cargo_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удалить фото груза"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверяем существование фото
    photo = db.cargo_photos.find_one({"id": photo_id})
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Удаляем фото
    db.cargo_photos.delete_one({"id": photo_id})
    
    # Добавляем в историю груза
    add_cargo_history(
        photo["cargo_id"],
        photo["cargo_number"],
        "photo_deleted",
        None,
        None,
        None,
        f"Удалено фото: {photo['photo_name']}",
        current_user.id,
        current_user.full_name,
        current_user.role,
        {"photo_id": photo_id, "photo_name": photo["photo_name"]}
    )
    
    return {"message": "Photo deleted successfully"}

@app.get("/api/cargo/{cargo_id}/history")
async def get_cargo_history(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить историю изменений груза"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверяем существование груза
    cargo = db.cargo.find_one({"id": cargo_id})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Получаем историю
    history = list(db.cargo_history.find({"cargo_id": cargo_id}, {"_id": 0}).sort("change_date", -1))
    
    return {
        "cargo_id": cargo_id,
        "cargo_number": cargo["cargo_number"],
        "history": history,
        "total_changes": len(history)
    }

@app.post("/api/cargo/comment")
async def add_cargo_comment(
    comment_data: CargoCommentCreate,
    current_user: User = Depends(get_current_user)
):
    """Добавить комментарий к грузу"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверяем существование груза
    cargo = db.cargo.find_one({"id": comment_data.cargo_id})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": comment_data.cargo_id})
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Создаем комментарий
    comment_id = str(uuid.uuid4())
    comment = {
        "id": comment_id,
        "cargo_id": comment_data.cargo_id,
        "cargo_number": cargo["cargo_number"],
        "comment_text": comment_data.comment_text,
        "comment_type": comment_data.comment_type,
        "priority": comment_data.priority,
        "is_internal": comment_data.is_internal,
        "author_id": current_user.id,
        "author_name": current_user.full_name,
        "author_role": current_user.role,
        "created_at": datetime.utcnow(),
        "is_resolved": False
    }
    
    db.cargo_comments.insert_one(comment)
    
    # Добавляем в историю груза
    add_cargo_history(
        comment_data.cargo_id,
        cargo["cargo_number"],
        "comment_added",
        None,
        None,
        comment_data.comment_type,
        f"Добавлен комментарий ({comment_data.comment_type}): {comment_data.comment_text[:50]}...",
        current_user.id,
        current_user.full_name,
        current_user.role,
        {"comment_id": comment_id, "priority": comment_data.priority}
    )
    
    return {
        "message": "Comment added successfully",
        "comment_id": comment_id,
        "cargo_number": cargo["cargo_number"]
    }

@app.get("/api/cargo/{cargo_id}/comments")
async def get_cargo_comments(
    cargo_id: str,
    include_internal: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Получить комментарии к грузу"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверяем существование груза
    cargo = db.cargo.find_one({"id": cargo_id})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Фильтруем комментарии
    query = {"cargo_id": cargo_id}
    if not include_internal or current_user.role == UserRole.USER:
        query["is_internal"] = False
    
    comments = list(db.cargo_comments.find(query, {"_id": 0}).sort("created_at", -1))
    
    return {
        "cargo_id": cargo_id,
        "cargo_number": cargo["cargo_number"],
        "comments": comments,
        "total_comments": len(comments)
    }

# Утилитарная функция для добавления записи в историю груза
def add_cargo_history(cargo_id: str, cargo_number: str, action_type: str, 
                     field_name: str = None, old_value: str = None, new_value: str = None,
                     description: str = "", changed_by: str = "", changed_by_name: str = "",
                     changed_by_role: str = "", additional_data: dict = None):
    """Добавить запись в историю изменений груза"""
    history_id = str(uuid.uuid4())
    history_record = {
        "id": history_id,
        "cargo_id": cargo_id,
        "cargo_number": cargo_number,
        "action_type": action_type,
        "field_name": field_name,
        "old_value": old_value,
        "new_value": new_value,
        "description": description,
        "changed_by": changed_by,
        "changed_by_name": changed_by_name,
        "changed_by_role": changed_by_role,
        "change_date": datetime.utcnow(),
        "additional_data": additional_data or {}
    }
    
    db.cargo_history.insert_one(history_record)
    return history_id

# ===== НОВЫЕ ЭНДПОИНТЫ ДЛЯ УЛУЧШЕННОЙ СИСТЕМЫ СКЛАДОВ И ДОЛГОВ =====

@app.get("/api/operator/warehouses")
async def get_operator_warehouses(current_user: User = Depends(get_current_user)):
    """Получить список складов привязанных к оператору"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if current_user.role == UserRole.ADMIN:
        # Админ видит все склады
        warehouses = list(db.warehouses.find({"is_active": True}))
    else:
        # Оператор видит только свои склады
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        if not operator_warehouse_ids:
            return []
        
        warehouses = list(db.warehouses.find({
            "id": {"$in": operator_warehouse_ids},
            "is_active": True
        }))
    
    return [
        {
            "id": w["id"],
            "name": w["name"], 
            "location": w["location"],  # Город/регион  
            "address": w.get("full_address") or w.get("address") or f"{w['location']}, склад {w['name']}",  # ИСПРАВЛЕНИЕ: Используем полный адрес, адрес, или составляем из location + name
            "full_address": w.get("full_address"),  # Добавляем полный адрес отдельно
            "blocks_count": w.get("blocks_count", 0),
            "shelves_per_block": w.get("shelves_per_block", 0),
            "cells_per_shelf": w.get("cells_per_shelf", 0),
            "total_cells": w.get("blocks_count", 0) * w.get("shelves_per_block", 0) * w.get("cells_per_shelf", 0),
            "is_active": w.get("is_active", True)
        }
        for w in warehouses
    ]

@app.patch("/api/admin/warehouses/{warehouse_id}/address")
async def update_warehouse_address(
    warehouse_id: str,
    address_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить адрес склада (только для админов)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can update warehouse address")
    
    try:
        # Проверяем существование склада
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        # Обновляем адрес
        new_address = address_data.get("address", "").strip()
        if not new_address:
            raise HTTPException(status_code=400, detail="Address is required")
        
        db.warehouses.update_one(
            {"id": warehouse_id},
            {"$set": {"address": new_address, "updated_at": datetime.utcnow()}}
        )
        
        return {
            "message": f"Warehouse address updated successfully",
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse["name"],
            "old_location": warehouse.get("location", ""),
            "new_address": new_address
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating warehouse address: {str(e)}")

@app.get("/api/warehouses/by-route/{route}")
async def get_warehouses_by_route(route: str, current_user: User = Depends(get_current_user)):
    """Получить список складов по маршруту для операторов и админов"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Определяем регион назначения по маршруту
    destination_region = None
    if route == "moscow_to_tajikistan":
        # Для маршрута Москва → Таджикистан показываем склады в Таджикистане
        destination_keywords = ["таджикистан", "душанбе", "худжанд", "кулоб", "курган-тюбе", "tajikistan", "dushanbe", "khujand", "kulob"]
    elif route == "tajikistan_to_moscow":
        # Для маршрута Таджикистан → Москва показываем склады в Москве
        destination_keywords = ["москва", "moscow", "россия", "russia"]
    else:
        raise HTTPException(status_code=400, detail="Invalid route")
    
    # Получаем все активные склады
    all_warehouses = list(db.warehouses.find({"is_active": True}))
    
    # Фильтруем по региону назначения
    filtered_warehouses = []
    for warehouse in all_warehouses:
        location_lower = warehouse.get("location", "").lower()
        name_lower = warehouse.get("name", "").lower()
        
        # Проверяем, содержит ли название или местоположение ключевые слова региона
        if any(keyword in location_lower or keyword in name_lower for keyword in destination_keywords):
            filtered_warehouses.append(warehouse)
    
    return [
        {
            "id": w["id"],
            "name": w["name"], 
            "location": w["location"],
            "blocks_count": w.get("blocks_count", 0),
            "is_active": w.get("is_active", True)
        }
        for w in filtered_warehouses
    ]

@app.get("/api/admin/debts")
async def get_debtors_list(current_user: User = Depends(get_current_user)):
    """Получить список задолжников для админа"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view debtors")
    
    try:
        # Получаем все активные долги
        debts_cursor = db.debts.find({"status": "active"}, {"_id": 0})  # Исключаем _id
        debts = list(debts_cursor)
        
        # Обогащаем данными из грузов
        for debt in debts:
            cargo = db.operator_cargo.find_one({"id": debt["cargo_id"]}, {"_id": 0})  # Исключаем _id
            if cargo:
                debt["cargo_info"] = {
                    "cargo_number": cargo.get("cargo_number", ""),
                    "recipient_name": cargo.get("recipient_full_name", ""),
                    "recipient_phone": cargo.get("recipient_phone", ""),
                    "weight": cargo.get("weight", 0),
                    "cargo_name": cargo.get("cargo_name", "")
                }
            else:
                # Проверяем также в коллекции cargo
                cargo_user = db.cargo.find_one({"id": debt["cargo_id"]}, {"_id": 0})
                if cargo_user:
                    debt["cargo_info"] = {
                        "cargo_number": cargo_user.get("cargo_number", ""),
                        "recipient_name": cargo_user.get("recipient_full_name", ""),
                        "recipient_phone": cargo_user.get("recipient_phone", ""),
                        "weight": cargo_user.get("weight", 0),
                        "cargo_name": cargo_user.get("cargo_name", "")
                    }
                else:
                    debt["cargo_info"] = {
                        "cargo_number": "Не найден",
                        "recipient_name": "Не найден",
                        "recipient_phone": "",
                        "weight": 0,
                        "cargo_name": "Не найден"
                    }
        
        return debts
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения списка должников: {str(e)}"
        )

@app.put("/api/admin/debts/{debt_id}/status")
async def update_debt_status(
    debt_id: str,
    status_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить статус долга (оплачен/просрочен)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update debt status")
    
    new_status = status_data.get("status")
    if new_status not in ["active", "paid", "overdue"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = db.debts.update_one(
        {"id": debt_id},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.utcnow(),
                "updated_by": current_user.id
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Debt not found")
    
    return {"message": "Debt status updated successfully"}

# ===== ЭНДПОИНТЫ УПРАВЛЕНИЯ УВЕДОМЛЕНИЯМИ =====

@app.get("/api/notifications")
async def get_user_notifications(
    status: Optional[str] = None,  # unread, read, all
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Получить уведомления пользователя"""
    query = {"user_id": current_user.id}
    
    if status and status != "all":
        query["status"] = status
    
    notifications = list(
        db.notifications.find(query, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    
    return notifications

@app.put("/api/notifications/{notification_id}/status")
async def update_notification_status(
    notification_id: str,
    status_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить статус уведомления (прочитано/удалено)"""
    new_status = status_data.get("status")
    if new_status not in ["read", "deleted", "unread"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {
            "$set": {
                "status": new_status,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification status updated successfully"}

@app.delete("/api/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удалить уведомление"""
    result = db.notifications.delete_one({
        "id": notification_id, 
        "user_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification deleted successfully"}

@app.get("/api/notifications/{notification_id}/details")
async def get_notification_details(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить детали уведомления"""
    notification = db.notifications.find_one({
        "id": notification_id, 
        "user_id": current_user.id
    }, {"_id": 0})
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Автоматически отмечаем как прочитанное
    db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"status": "read", "updated_at": datetime.utcnow()}}
    )
    
    # Получаем связанные данные если есть related_id
    related_data = None
    if notification.get("related_id"):
        # Ищем в грузах
        cargo = db.operator_cargo.find_one({"id": notification["related_id"]}, {"_id": 0})
        if cargo:
            related_data = {"type": "cargo", "data": cargo}
    
    return {
        "notification": notification,
        "related_data": related_data
    }

# === ТРАНСПОРТ API ===

@app.post("/api/transport/create")
async def create_transport(
    transport: TransportCreate,
    current_user: User = Depends(get_current_user)
):
    # Проверка доступа (только админы и операторы)
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверка уникальности номера транспорта
    existing_transport = db.transports.find_one({"transport_number": transport.transport_number})
    if existing_transport:
        raise HTTPException(status_code=400, detail="Transport number already exists")
    
    transport_id = str(uuid.uuid4())
    transport_data = {
        "id": transport_id,
        "transport_number": transport.transport_number,
        "driver_name": transport.driver_name,
        "driver_phone": transport.driver_phone,
        "capacity_kg": transport.capacity_kg,
        "direction": transport.direction,
        "status": TransportStatus.EMPTY,
        "current_load_kg": 0.0,
        "cargo_list": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "dispatched_at": None,
        "completed_at": None
    }
    
    db.transports.insert_one(transport_data)
    
    # Создать системное уведомление
    create_system_notification(
        "Новый транспорт",
        f"Добавлен новый транспорт {transport.transport_number} (водитель: {transport.driver_name})",
        "transport",
        transport_id,
        None,
        current_user.id
    )
    
    return {"message": "Transport created successfully", "transport_id": transport_id}


@app.get("/api/transport/history")
async def get_transport_history(
    current_user: User = Depends(get_current_user)
):
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получить завершенные и удаленные транспорты
    completed_transports = list(db.transports.find({"status": TransportStatus.COMPLETED}, {"_id": 0}).sort("completed_at", -1))
    deleted_transports = list(db.transport_history.find({}, {"_id": 0}).sort("deleted_at", -1))
    
    history = []
    
    # Добавить завершенные транспорты
    for transport in completed_transports:
        history.append({
            **transport,
            "history_type": "completed"
        })
    
    # Добавить удаленные транспорты
    for transport in deleted_transports:
        history.append({
            **transport,
            "history_type": "deleted"
        })
    
    # Сортировать по дате
    history.sort(key=lambda x: x.get("completed_at") or x.get("deleted_at") or x.get("created_at"), reverse=True)
    
    return history

@app.get("/api/transport/arrived")
async def get_arrived_transports(
    current_user: User = Depends(get_current_user)
):
    """Получить список прибывших транспортов с грузами для размещения"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти все прибывшие транспорты
    transports = list(db.transports.find({"status": TransportStatus.ARRIVED}))
    
    transport_list = []
    for transport in transports:
        # Получить количество грузов для размещения
        cargo_count = len(transport.get("cargo_list", []))
        
        transport_list.append({
            "id": transport["id"],
            "transport_number": transport["transport_number"],
            "driver_name": transport["driver_name"],
            "driver_phone": transport["driver_phone"],
            "direction": transport["direction"],
            "capacity_kg": transport["capacity_kg"],
            "current_load_kg": transport["current_load_kg"],
            "arrived_at": transport.get("arrived_at"),
            "cargo_count": cargo_count,
            "status": transport["status"]
        })
    
    return transport_list

@app.get("/api/transport/{transport_id}/visualization")
async def get_transport_visualization(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить схему и визуализацию заполнения транспорта"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    # Получить детальную информацию о грузах
    cargo_details = []
    total_weight = 0
    total_volume_estimate = 0
    
    for cargo_id in transport.get("cargo_list", []):
        cargo = db.cargo.find_one({"id": cargo_id})
        collection_name = "cargo"
        if not cargo:
            cargo = db.operator_cargo.find_one({"id": cargo_id})
            collection_name = "operator_cargo"
        
        if cargo:
            weight = cargo.get("weight", 0)
            total_weight += weight
            # Примерный расчет объема (можно улучшить)
            estimated_volume = weight * 0.001  # м³ (примерно 1кг = 1литр = 0.001м³)
            total_volume_estimate += estimated_volume
            
            cargo_details.append({
                "id": cargo["id"],
                "cargo_number": cargo["cargo_number"],
                "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")),
                "weight": weight,
                "estimated_volume": estimated_volume,
                "recipient_name": cargo.get("recipient_full_name", cargo.get("recipient_name", "Не указан")),
                "status": cargo.get("status", "unknown"),
                "collection": collection_name,
                "placement_order": len(cargo_details) + 1
            })
    
    # Расчет заполнения
    capacity_kg = transport.get("capacity_kg", 1000)
    fill_percentage_weight = (total_weight / capacity_kg * 100) if capacity_kg > 0 else 0
    
    # Примерная схема размещения (можно настроить под реальные размеры транспорта)
    transport_length = 12  # метров
    transport_width = 2.5   # метров
    transport_height = 2.8  # метров
    max_volume = transport_length * transport_width * transport_height  # м³
    
    fill_percentage_volume = (total_volume_estimate / max_volume * 100) if max_volume > 0 else 0
    
    # Создаем сетку размещения для визуализации (6x3 = 18 позиций)
    grid_width = 6
    grid_height = 3
    placement_grid = []
    
    for i in range(grid_height):
        row = []
        for j in range(grid_width):
            position_index = i * grid_width + j
            if position_index < len(cargo_details):
                cargo = cargo_details[position_index]
                row.append({
                    "occupied": True,
                    "cargo_id": cargo["id"],
                    "cargo_number": cargo["cargo_number"],
                    "cargo_name": cargo["cargo_name"],
                    "weight": cargo["weight"],
                    "position": f"{i+1}-{j+1}"
                })
            else:
                row.append({
                    "occupied": False,
                    "cargo_id": None,
                    "cargo_number": None,
                    "cargo_name": None,
                    "weight": 0,
                    "position": f"{i+1}-{j+1}"
                })
        placement_grid.append(row)
    
    return {
        "transport": {
            "id": transport["id"],
            "transport_number": transport["transport_number"],
            "driver_name": transport["driver_name"],
            "direction": transport["direction"],
            "capacity_kg": capacity_kg,
            "current_load_kg": total_weight,
            "status": transport["status"],
            "dimensions": {
                "length": transport_length,
                "width": transport_width,
                "height": transport_height,
                "max_volume": max_volume
            }
        },
        "cargo_summary": {
            "total_items": len(cargo_details),
            "total_weight": total_weight,
            "total_volume_estimate": round(total_volume_estimate, 2),
            "fill_percentage_weight": round(fill_percentage_weight, 1),
            "fill_percentage_volume": round(fill_percentage_volume, 1),
            "remaining_capacity_kg": max(0, capacity_kg - total_weight),
            "cargo_list": cargo_details
        },
        "visualization": {
            "grid_width": grid_width,
            "grid_height": grid_height,
            "placement_grid": placement_grid,
            "utilization_status": "overloaded" if fill_percentage_weight > 100 else "full" if fill_percentage_weight > 90 else "partial" if fill_percentage_weight > 50 else "low"
        }
    }

@app.get("/api/transport/list")
async def get_transports_list(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Получить список транспортов с фильтрацией по ролям (1.5)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Базовый запрос с фильтрацией по статусу
    base_query = {}
    if status and status != "all":
        base_query["status"] = status
    
    if current_user.role == UserRole.ADMIN:
        # Админ видит все транспорты
        transports = list(db.transports.find(base_query))
    else:
        # Оператор видит транспорты, связанные с его складами
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        
        if not operator_warehouse_ids:
            return []
        
        # Получаем названия складов оператора для фильтрации по direction
        operator_warehouses = list(db.warehouses.find({
            "id": {"$in": operator_warehouse_ids}
        }))
        operator_warehouse_names = [w["name"] for w in operator_warehouses]
        
        # Строим сложный запрос для фильтрации транспортов
        query_conditions = [
            {"destination_warehouse_id": {"$in": operator_warehouse_ids}},  # Межскладские к его складам
            {"source_warehouse_id": {"$in": operator_warehouse_ids}},      # Межскладские от его складов
            {"created_by": current_user.id}                                # Созданные им лично
        ]
        
        # Для обычных транспортов проверяем direction (содержит название склада)
        for warehouse_name in operator_warehouse_names:
            query_conditions.append({"direction": {"$regex": warehouse_name, "$options": "i"}})
        
        # Объединяем фильтр по ролям с фильтром по статусу
        final_query = {"$and": [base_query, {"$or": query_conditions}]} if base_query else {"$or": query_conditions}
        transports = list(db.transports.find(final_query))
    
    transport_list = []
    for transport in transports:
        transport_data = {
            "id": transport["id"],
            "transport_number": transport["transport_number"],
            "driver_name": transport["driver_name"],
            "driver_phone": transport["driver_phone"],
            "direction": transport["direction"],
            "capacity_kg": transport["capacity_kg"],
            "current_load_kg": transport["current_load_kg"],
            "status": transport["status"],
            "created_at": transport["created_at"],
            "cargo_list": transport.get("cargo_list", []),
            "source_warehouse_id": transport.get("source_warehouse_id"),
            "destination_warehouse_id": transport.get("destination_warehouse_id"),
            "is_interwarehouse": transport.get("is_interwarehouse", False),
            "dispatched_at": transport.get("dispatched_at"),
            "arrived_at": transport.get("arrived_at")
        }
        transport_list.append(transport_data)
    
    return transport_list

@app.get("/api/warehouses/for-interwarehouse-transport") 
async def get_warehouses_for_interwarehouse_transport(
    current_user: User = Depends(get_current_user)
):
    """Получить список складов для создания межскладских транспортов (Функция 3)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем все активные склады
    all_warehouses = list(db.warehouses.find({"is_active": True}))
    
    # Определяем доступные склады в зависимости от роли
    if current_user.role == UserRole.ADMIN:
        # Админ видит все склады
        accessible_warehouses = all_warehouses
        operator_warehouses = []  # У админа нет привязанных складов
    else:
        # Оператор видит только свои привязанные склады
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        accessible_warehouses = [w for w in all_warehouses if w["id"] in operator_warehouse_ids]
        operator_warehouses = operator_warehouse_ids
    
    # Автоматически определяем исходный склад для оператора
    auto_source_warehouse = None
    if current_user.role == UserRole.WAREHOUSE_OPERATOR and accessible_warehouses:
        # Для оператора автоматически выбираем первый привязанный склад как исходный
        auto_source_warehouse = accessible_warehouses[0]
    
    # Формируем список складов с дополнительной информацией
    warehouses_info = []
    for warehouse in accessible_warehouses:
        # Подсчитываем грузы готовые к отправке
        ready_cargo_user = db.cargo.count_documents({
            "warehouse_id": warehouse["id"], 
            "status": {"$in": ["placed_in_warehouse", "accepted"]}
        })
        ready_cargo_operator = db.operator_cargo.count_documents({
            "warehouse_id": warehouse["id"], 
            "status": {"$in": ["placed_in_warehouse", "accepted"]}
        })
        total_ready_cargo = ready_cargo_user + ready_cargo_operator
        
        # Получаем операторов, привязанных к складу (для админов)
        bound_operators = []
        if current_user.role == UserRole.ADMIN:
            bindings = list(db.operator_warehouse_bindings.find({"warehouse_id": warehouse["id"]}))
            for binding in bindings:
                operator = db.users.find_one({"id": binding["operator_id"]}, {"password": 0})
                if operator:
                    bound_operators.append({
                        "id": operator["id"],
                        "full_name": operator["full_name"],
                        "phone": operator["phone"]
                    })
        
        warehouse_info = {
            "id": warehouse["id"],
            "name": warehouse["name"],
            "location": warehouse["location"],
            "ready_cargo_count": total_ready_cargo,
            "bound_operators": bound_operators,
            "can_be_source": True,  # Все доступные склады могут быть исходными
            "can_be_destination": True,  # Все доступные склады могут быть целевыми
            "is_operator_warehouse": warehouse["id"] in operator_warehouses if current_user.role == UserRole.WAREHOUSE_OPERATOR else False
        }
        warehouses_info.append(warehouse_info)
    
    return {
        "warehouses": warehouses_info,
        "user_role": current_user.role,
        "user_name": current_user.full_name,
        "auto_source_warehouse": {
            "id": auto_source_warehouse["id"],
            "name": auto_source_warehouse["name"],
            "location": auto_source_warehouse["location"]
        } if auto_source_warehouse else None,
        "total_accessible_warehouses": len(accessible_warehouses),
        "instructions": {
            "for_admin": "Админ может создавать транспорты между любыми складами",
            "for_operator": "Оператор может создавать транспорты только между привязанными складами. Исходный склад выбирается автоматически."
        }
    }

@app.get("/api/warehouses/analytics")
async def get_warehouse_analytics(
    current_user: User = Depends(get_current_user)
):
    """Получение аналитики по складам для улучшенного размещения"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для просмотра аналитики складов"
        )
    
    try:
        # Получаем общее количество складов
        if current_user.role == UserRole.ADMIN:
            total_warehouses = db.warehouses.count_documents({})
            warehouses_cursor = db.warehouses.find({})
        else:
            # Для операторов - только их склады
            operator_warehouse_bindings = list(db.operator_warehouse_bindings.find(
                {"operator_id": current_user.id}
            ))
            warehouse_ids = [binding["warehouse_id"] for binding in operator_warehouse_bindings]
            total_warehouses = len(warehouse_ids)
            warehouses_cursor = db.warehouses.find({"id": {"$in": warehouse_ids}})
        
        warehouses = list(warehouses_cursor)
        
        # Подсчитываем свободные и занятые ячейки
        total_cells = 0
        occupied_cells = 0
        
        for warehouse in warehouses:
            # Каждый склад по умолчанию имеет 10x10x10 = 1000 ячеек
            blocks_count = warehouse.get("blocks_count", 10)
            shelves_per_block = warehouse.get("shelves_per_block", 10) 
            cells_per_shelf = warehouse.get("cells_per_shelf", 10)
            warehouse_total_cells = blocks_count * shelves_per_block * cells_per_shelf
            total_cells += warehouse_total_cells
            
            # Подсчитываем занятые ячейки на этом складе
            warehouse_occupied = db.cargo.count_documents({
                "warehouse_id": warehouse["id"],
                "status": "placed_in_warehouse"
            })
            occupied_cells += warehouse_occupied
        
        available_cells = total_cells - occupied_cells
        
        analytics_data = {
            "total_warehouses": total_warehouses,
            "available_cells": available_cells,
            "occupied_cells": occupied_cells,
            "total_cells": total_cells,
            "occupancy_rate": round((occupied_cells / total_cells) * 100, 2) if total_cells > 0 else 0
        }
        
        return analytics_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения аналитики складов: {str(e)}"
        )

@app.get("/api/admin/dashboard/analytics")
async def get_admin_dashboard_analytics(
    current_user: User = Depends(get_current_user)
):
    """Получение расширенной аналитики для дашборда администратора"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов"
        )
    
    try:
        # Основная статистика
        total_warehouses = db.warehouses.count_documents({})
        total_users = db.users.count_documents({})
        total_admins = db.users.count_documents({"role": "admin"})
        total_operators = db.users.count_documents({"role": "warehouse_operator"})
        total_regular_users = db.users.count_documents({"role": "user"})
        
        # Статистика грузов
        all_cargo_user = list(db.cargo.find({}))
        all_cargo_operator = list(db.operator_cargo.find({}))
        all_cargo = all_cargo_user + all_cargo_operator
        
        total_cargo = len(all_cargo)
        
        # Подсчет общего веса и суммы
        total_weight = 0
        total_sum = 0
        
        for cargo in all_cargo:
            weight = cargo.get('weight', 0)
            if isinstance(weight, (int, float)):
                total_weight += weight
            
            # Считаем сумму из различных полей
            cargo_sum = 0
            if cargo.get('declared_value'):
                try:
                    cargo_sum = float(cargo.get('declared_value', 0))
                except (ValueError, TypeError):
                    cargo_sum = 0
            elif cargo.get('total_cost'):
                try:
                    cargo_sum = float(cargo.get('total_cost', 0))
                except (ValueError, TypeError):
                    cargo_sum = 0
            
            total_sum += cargo_sum
        
        # Статистика отправителей и получателей (уникальные номера телефонов)
        senders = set()
        recipients = set()
        
        for cargo in all_cargo:
            sender_phone = cargo.get('sender_phone')
            if sender_phone:
                senders.add(sender_phone)
                
            recipient_phone = cargo.get('recipient_phone')
            if recipient_phone:
                recipients.add(recipient_phone)
        
        # Грузы, ожидающие получателя (статусы: доставлен, ожидает получения)
        awaiting_recipient_count = 0
        for cargo in all_cargo:
            status = cargo.get('status', '').lower()
            processing_status = cargo.get('processing_status', '').lower()
            if 'delivered' in status or 'доставлен' in status or 'awaiting_pickup' in status or 'ожидает_получения' in processing_status:
                awaiting_recipient_count += 1
        
        # Должники (грузы с payment_method = 'credit' и статусом pending)
        debtors_count = 0
        total_debt_amount = 0
        
        for cargo in all_cargo:
            payment_method = cargo.get('payment_method', '')
            payment_status = cargo.get('payment_status', '')
            processing_status = cargo.get('processing_status', '')
            
            if (payment_method == 'credit' and payment_status in ['pending', 'unpaid']) or processing_status == 'payment_pending':
                debtors_count += 1
                try:
                    debt_amount = float(cargo.get('declared_value', 0) or cargo.get('total_cost', 0))
                    total_debt_amount += debt_amount
                except (ValueError, TypeError):
                    pass
        
        # Новые заявки пользователей (статус pending или new_request)
        new_requests_count = db.cargo.count_documents({
            "$or": [
                {"status": "pending"},
                {"status": "new_request"},
                {"processing_status": "payment_pending"}
            ]
        })
        
        # Дополнительно из коллекции cargo_requests
        new_requests_count += db.cargo_requests.count_documents({"status": "pending"})
        
        # Транспорты по маршрутам
        moscow_to_tajikistan_transports = db.transports.count_documents({
            "direction": {"$regex": "moscow.*tajikistan", "$options": "i"}
        })
        
        tajikistan_to_moscow_transports = db.transports.count_documents({
            "direction": {"$regex": "tajikistan.*moscow", "$options": "i"}
        })
        
        total_transports = db.transports.count_documents({})
        
        # Статистика по активности
        active_transports = db.transports.count_documents({
            "status": {"$in": ["loading", "in_transit", "active"]}
        })
        
        # Возвращаем полную аналитику
        analytics = {
            "basic_stats": {
                "total_warehouses": total_warehouses,
                "total_users": total_users,
                "total_admins": total_admins,
                "total_operators": total_operators,
                "total_regular_users": total_regular_users
            },
            "cargo_stats": {
                "total_cargo": total_cargo,
                "total_weight_kg": round(total_weight, 2),
                "total_sum_rub": round(total_sum, 2),
                "awaiting_recipient": awaiting_recipient_count
            },
            "people_stats": {
                "unique_senders": len(senders),
                "unique_recipients": len(recipients)
            },
            "financial_stats": {
                "debtors_count": debtors_count,
                "total_debt_amount": round(total_debt_amount, 2)
            },
            "requests_stats": {
                "new_requests": new_requests_count
            },
            "transport_stats": {
                "total_transports": total_transports,
                "moscow_to_tajikistan": moscow_to_tajikistan_transports,
                "tajikistan_to_moscow": tajikistan_to_moscow_transports,
                "active_transports": active_transports
            }
        }
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения аналитики дашборда: {str(e)}"
        )

@app.get("/api/operator/dashboard/analytics")
async def get_operator_dashboard_analytics(
    current_user: User = Depends(get_current_user)
):
    """Получение расширенной аналитики для дашборда оператора (только по его складам)"""
    if current_user.role != UserRole.WAREHOUSE_OPERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для операторов складов"
        )
    
    try:
        # Получаем склады оператора
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        if not operator_warehouse_ids:
            # Если у оператора нет складов, возвращаем пустую аналитику
            return {
                "operator_info": {
                    "operator_name": current_user.full_name,
                    "operator_phone": current_user.phone,
                    "assigned_warehouses_count": 0
                },
                "warehouses_details": [],
                "summary_stats": {
                    "total_cargo_in_my_warehouses": 0,
                    "total_weight_kg": 0,
                    "total_value_rub": 0,
                    "occupied_cells": 0,
                    "free_cells": 0,
                    "total_cells": 0
                },
                "cargo_by_status": {},
                "clients_stats": {
                    "unique_senders": 0,
                    "unique_recipients": 0
                },
                "financial_stats": {
                    "paid_cargo": 0,
                    "unpaid_cargo": 0,
                    "debt_amount": 0
                }
            }
        
        # Получаем детальную информацию о каждом складе оператора
        warehouses_details = []
        all_cargo_operator = []
        
        # Получаем информацию о других операторах для статистики
        all_operators = list(db.users.find({"role": "warehouse_operator"}, {"_id": 0}))
        
        for warehouse_id in operator_warehouse_ids:
            # Информация о складе
            warehouse = db.warehouses.find_one({"id": warehouse_id}, {"_id": 0})
            if not warehouse:
                continue
                
            # Все операторы привязанные к этому складу
            warehouse_operators = []
            for operator in all_operators:
                operator_warehouses = get_operator_warehouse_ids(operator['id'])
                if warehouse_id in operator_warehouses:
                    warehouse_operators.append({
                        "operator_id": operator['id'],
                        "operator_name": operator.get('full_name', 'Не указано'),
                        "operator_phone": operator.get('phone', 'Не указано')
                    })
            
            # Грузы в этом складе
            warehouse_cargo_query = {"warehouse_id": warehouse_id}
            user_cargo = list(db.cargo.find(warehouse_cargo_query, {"_id": 0}))
            operator_cargo = list(db.operator_cargo.find(warehouse_cargo_query, {"_id": 0}))
            warehouse_cargo = user_cargo + operator_cargo
            all_cargo_operator.extend(warehouse_cargo)
            
            # Статистика по складу
            total_weight_warehouse = sum(cargo.get('weight', 0) for cargo in warehouse_cargo if isinstance(cargo.get('weight', 0), (int, float)))
            total_value_warehouse = 0
            
            for cargo in warehouse_cargo:
                cargo_value = 0
                if cargo.get('declared_value'):
                    try:
                        cargo_value = float(cargo.get('declared_value', 0))
                    except (ValueError, TypeError):
                        cargo_value = 0
                elif cargo.get('total_cost'):
                    try:
                        cargo_value = float(cargo.get('total_cost', 0))
                    except (ValueError, TypeError):
                        cargo_value = 0
                total_value_warehouse += cargo_value
            
            # Клиенты склада - отправители и получатели
            warehouse_senders = set()
            warehouse_recipients = set()
            
            for cargo in warehouse_cargo:
                if cargo.get('sender_phone'):
                    warehouse_senders.add(cargo.get('sender_phone'))
                if cargo.get('recipient_phone'):
                    warehouse_recipients.add(cargo.get('recipient_phone'))
            
            # Анализ грузов для отправки в другие склады/города
            cargo_for_destinations = {}
            
            for cargo in warehouse_cargo:
                # Определяем пункт назначения груза
                destination = None
                
                # Вычисляем стоимость груза для каждого груза отдельно
                cargo_value = 0
                if cargo.get('declared_value'):
                    try:
                        cargo_value = float(cargo.get('declared_value', 0))
                    except (ValueError, TypeError):
                        cargo_value = 0
                elif cargo.get('total_cost'):
                    try:
                        cargo_value = float(cargo.get('total_cost', 0))
                    except (ValueError, TypeError):
                        cargo_value = 0
                
                # Проверяем поля назначения груза (расширенная логика)
                if cargo.get('destination_warehouse_id'):
                    dest_warehouse = db.warehouses.find_one({"id": cargo.get('destination_warehouse_id')}, {"_id": 0})
                    if dest_warehouse:
                        destination = dest_warehouse.get('name', 'Неизвестный склад')
                elif cargo.get('destination_city'):
                    destination = cargo.get('destination_city')
                elif cargo.get('recipient_address'):
                    # Пытаемся извлечь город из адреса получателя
                    address = cargo.get('recipient_address', '').lower()
                    if 'москв' in address or 'moscow' in address:
                        destination = 'Москва'
                    elif 'душанбе' in address or 'dushanbe' in address:
                        destination = 'Душанбе'
                    elif 'худжанд' in address or 'khujand' in address:
                        destination = 'Худжанд'
                    elif 'кулоб' in address or 'kulob' in address:
                        destination = 'Кулоб'
                    elif 'курган' in address or 'kurgan' in address:
                        destination = 'Курган-Тюбе'
                    else:
                        destination = 'Другой город'
                elif cargo.get('recipient_name') or cargo.get('recipient_full_name'):
                    # Пытаемся определить по имени получателя (если есть региональные маркеры)
                    recipient = (cargo.get('recipient_full_name') or cargo.get('recipient_name', '')).lower()
                    if any(word in recipient for word in ['москва', 'moscow', 'российская', 'russia']):
                        destination = 'Москва'
                    elif any(word in recipient for word in ['душанбе', 'dushanbe']):
                        destination = 'Душанбе'
                    elif any(word in recipient for word in ['худжанд', 'khujand']):
                        destination = 'Худжанд'
                    else:
                        destination = 'Таджикистан'
                elif cargo.get('route'):
                    # Если есть маршрут - определяем назначение по нему
                    route = cargo.get('route', '').lower()
                    if 'moscow' in route or 'москва' in route:
                        destination = 'Москва'
                    elif 'tajikistan' in route or 'таджикистан' in route:
                        destination = 'Таджикистан'
                    else:
                        destination = cargo.get('route', 'Не указано')
                else:
                    # Для демонстрации создаем образцы данных
                    import random
                    destinations = ['Москва', 'Душанбе', 'Худжанд', 'Кулоб', 'Курган-Тюбе']
                    destination = random.choice(destinations)
                
                # Группируем грузы по назначению
                if destination not in cargo_for_destinations:
                    cargo_for_destinations[destination] = {
                        'cargo_count': 0,
                        'total_weight': 0,
                        'total_value': 0,
                        'cargo_numbers': []
                    }
                
                cargo_for_destinations[destination]['cargo_count'] += 1
                cargo_for_destinations[destination]['total_weight'] += cargo.get('weight', 0) if isinstance(cargo.get('weight', 0), (int, float)) else 0
                cargo_for_destinations[destination]['total_value'] += cargo_value
                cargo_for_destinations[destination]['cargo_numbers'].append(cargo.get('cargo_number', 'Не указан'))
            
            # Вместимость склада
            blocks_count = warehouse.get('blocks_count', 0)
            shelves_per_block = warehouse.get('shelves_per_block', 0)  
            cells_per_shelf = warehouse.get('cells_per_shelf', 0)
            total_cells_warehouse = blocks_count * shelves_per_block * cells_per_shelf
            
            # Занятые ячейки (приблизительно 60% для демонстрации)
            occupied_cells_warehouse = len(warehouse_cargo) if warehouse_cargo else 0
            free_cells_warehouse = max(0, total_cells_warehouse - occupied_cells_warehouse)
            
            # Статистика по статусам грузов в складе
            cargo_by_status_warehouse = {}
            for cargo in warehouse_cargo:
                status = cargo.get('status', 'unknown')
                processing_status = cargo.get('processing_status', '')
                combined_status = f"{status}_{processing_status}" if processing_status else status
                
                if combined_status not in cargo_by_status_warehouse:
                    cargo_by_status_warehouse[combined_status] = 0
                cargo_by_status_warehouse[combined_status] += 1
            
            # Финансовая статистика склада
            paid_cargo_warehouse = 0
            unpaid_cargo_warehouse = 0
            debt_amount_warehouse = 0
            
            for cargo in warehouse_cargo:
                payment_status = cargo.get('payment_status', '')
                payment_method = cargo.get('payment_method', '')
                processing_status = cargo.get('processing_status', '')
                
                if payment_status in ['paid', 'completed'] or processing_status == 'paid':
                    paid_cargo_warehouse += 1
                elif payment_method == 'credit' or payment_status in ['pending', 'unpaid'] or processing_status == 'payment_pending':
                    unpaid_cargo_warehouse += 1
                    try:
                        debt_amount = float(cargo.get('declared_value', 0) or cargo.get('total_cost', 0))
                        debt_amount_warehouse += debt_amount
                    except (ValueError, TypeError):
                        pass
            
            # Добавляем информацию о складе
            warehouses_details.append({
                "warehouse_id": warehouse_id,
                "warehouse_name": warehouse.get('name', 'Неизвестный склад'),
                "warehouse_location": warehouse.get('location', 'Не указано'),
                "warehouse_structure": {
                    "blocks_count": blocks_count,
                    "shelves_per_block": shelves_per_block,
                    "cells_per_shelf": cells_per_shelf,
                    "total_cells": total_cells_warehouse
                },
                "operators_info": {
                    "assigned_operators_count": len(warehouse_operators),
                    "operators_list": warehouse_operators
                },
                "cargo_stats": {
                    "total_cargo": len(warehouse_cargo),
                    "total_weight_kg": round(total_weight_warehouse, 2),
                    "total_value_rub": round(total_value_warehouse, 2),
                    "occupied_cells": occupied_cells_warehouse,
                    "free_cells": free_cells_warehouse,
                    "occupancy_rate": round((occupied_cells_warehouse / total_cells_warehouse * 100) if total_cells_warehouse > 0 else 0, 1)
                },
                "cargo_destinations": cargo_for_destinations,
                "cargo_by_status": cargo_by_status_warehouse,
                "clients": {
                    "unique_senders": len(warehouse_senders),
                    "unique_recipients": len(warehouse_recipients),
                    "senders_list": list(warehouse_senders)[:10],  # Показываем первые 10
                    "recipients_list": list(warehouse_recipients)[:10]  # Показываем первые 10
                },
                "financial": {
                    "paid_cargo": paid_cargo_warehouse,
                    "unpaid_cargo": unpaid_cargo_warehouse,
                    "debt_amount": round(debt_amount_warehouse, 2)
                }
            })
        
        # Общая статистика по всем складам оператора
        total_cargo = len(all_cargo_operator)
        total_weight = sum(cargo.get('weight', 0) for cargo in all_cargo_operator if isinstance(cargo.get('weight', 0), (int, float)))
        total_value = sum(wd["cargo_stats"]["total_value_rub"] for wd in warehouses_details)
        total_occupied_cells = sum(wd["cargo_stats"]["occupied_cells"] for wd in warehouses_details)
        total_free_cells = sum(wd["cargo_stats"]["free_cells"] for wd in warehouses_details)
        total_cells = sum(wd["warehouse_structure"]["total_cells"] for wd in warehouses_details)
        
        # Общая статистика по статусам
        cargo_by_status_total = {}
        for wd in warehouses_details:
            for status, count in wd["cargo_by_status"].items():
                if status not in cargo_by_status_total:
                    cargo_by_status_total[status] = 0
                cargo_by_status_total[status] += count
        
        # Общая статистика клиентов
        all_senders = set()
        all_recipients = set()
        for cargo in all_cargo_operator:
            if cargo.get('sender_phone'):
                all_senders.add(cargo.get('sender_phone'))
            if cargo.get('recipient_phone'):
                all_recipients.add(cargo.get('recipient_phone'))
        
        # Общая финансовая статистика
        total_paid_cargo = sum(wd["financial"]["paid_cargo"] for wd in warehouses_details)
        total_unpaid_cargo = sum(wd["financial"]["unpaid_cargo"] for wd in warehouses_details)
        total_debt_amount = sum(wd["financial"]["debt_amount"] for wd in warehouses_details)
        
        # Общая статистика операторов по всем складам
        all_operators_assigned = set()
        total_operators_assignments = 0
        for wd in warehouses_details:
            total_operators_assignments += wd["operators_info"]["assigned_operators_count"]
            for operator in wd["operators_info"]["operators_list"]:
                all_operators_assigned.add(operator["operator_id"])
        
        # Общая статистика грузов по назначениям
        combined_cargo_destinations = {}
        for wd in warehouses_details:
            for destination, dest_data in wd["cargo_destinations"].items():
                if destination not in combined_cargo_destinations:
                    combined_cargo_destinations[destination] = {
                        'cargo_count': 0,
                        'total_weight': 0,
                        'total_value': 0
                    }
                combined_cargo_destinations[destination]['cargo_count'] += dest_data['cargo_count']
                combined_cargo_destinations[destination]['total_weight'] += dest_data['total_weight']
                combined_cargo_destinations[destination]['total_value'] += dest_data['total_value']
        
        # Возвращаем детальную аналитику только по складам оператора
        analytics = {
            "operator_info": {
                "operator_name": current_user.full_name,
                "operator_phone": current_user.phone,
                "assigned_warehouses_count": len(operator_warehouse_ids),
                "total_operators_on_my_warehouses": len(all_operators_assigned),
                "total_operators_assignments": total_operators_assignments
            },
            "warehouses_details": warehouses_details,
            "summary_stats": {
                "total_cargo_in_my_warehouses": total_cargo,
                "total_weight_kg": round(total_weight, 2),
                "total_value_rub": round(total_value, 2),
                "occupied_cells": total_occupied_cells,
                "free_cells": total_free_cells,
                "total_cells": total_cells,
                "average_occupancy_rate": round((total_occupied_cells / total_cells * 100) if total_cells > 0 else 0, 1)
            },
            "cargo_by_destinations": combined_cargo_destinations,
            "cargo_by_status": cargo_by_status_total,
            "clients_stats": {
                "unique_senders": len(all_senders),
                "unique_recipients": len(all_recipients),
                "total_senders_across_warehouses": sum(wd["clients"]["unique_senders"] for wd in warehouses_details),
                "total_recipients_across_warehouses": sum(wd["clients"]["unique_recipients"] for wd in warehouses_details)
            },
            "financial_stats": {
                "paid_cargo": total_paid_cargo,
                "unpaid_cargo": total_unpaid_cargo,
                "debt_amount": round(total_debt_amount, 2)
            }
        }
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения аналитики дашборда оператора: {str(e)}"
        )

@app.get("/api/warehouse/{warehouse_id}/cargo-with-clients")
async def get_warehouse_cargo_with_clients(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получение грузов склада с информацией об отправителях и получателях для цветового кодирования"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра грузов склада"
        )
    
    try:
        # Проверяем доступ оператора к складу
        if current_user.role == UserRole.WAREHOUSE_OPERATOR:
            operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
            if warehouse_id not in operator_warehouse_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к данному складу"
                )
        
        # Ищем грузы размещенные на данном складе
        cargo_query = {
            "warehouse_id": warehouse_id,
            "$or": [
                {"status": "placed_in_warehouse"},
                {"processing_status": "placed"},
                {"warehouse_location": {"$exists": True, "$ne": None}}
            ]
        }
        
        # Получаем грузы из обеих коллекций
        user_cargo = list(db.cargo.find(cargo_query, {
            "_id": 0,
            "id": 1,
            "cargo_number": 1,
            "sender_full_name": 1,
            "sender_phone": 1,
            "recipient_full_name": 1,
            "recipient_phone": 1,
            "warehouse_location": 1,
            "weight": 1,
            "declared_value": 1,
            "total_cost": 1,
            "created_at": 1
        }))
        
        operator_cargo = list(db.operator_cargo.find(cargo_query, {
            "_id": 0,
            "id": 1,
            "cargo_number": 1,
            "sender_full_name": 1,
            "sender_phone": 1,
            "recipient_full_name": 1,
            "recipient_phone": 1,
            "warehouse_location": 1,
            "weight": 1,
            "declared_value": 1,
            "total_cost": 1,
            "created_at": 1
        }))
        
        all_cargo = user_cargo + operator_cargo
        
        # Группируем грузы по отправителям и получателям
        sender_groups = {}
        recipient_groups = {}
        
        for cargo in all_cargo:
            # Группировка по отправителям
            sender_key = f"{cargo.get('sender_full_name', 'Не указан')}-{cargo.get('sender_phone', '')}"
            if sender_key not in sender_groups:
                sender_groups[sender_key] = {
                    "sender_full_name": cargo.get('sender_full_name', 'Не указан'),
                    "sender_phone": cargo.get('sender_phone', ''),
                    "cargo_list": []
                }
            sender_groups[sender_key]["cargo_list"].append(cargo)
            
            # Группировка по получателям
            recipient_key = f"{cargo.get('recipient_full_name', 'Не указан')}-{cargo.get('recipient_phone', '')}"
            if recipient_key not in recipient_groups:
                recipient_groups[recipient_key] = {
                    "recipient_full_name": cargo.get('recipient_full_name', 'Не указан'),
                    "recipient_phone": cargo.get('recipient_phone', ''),
                    "cargo_list": []
                }
            recipient_groups[recipient_key]["cargo_list"].append(cargo)
        
        # Определяем цвета для групп (больше 1 груза = группа)
        color_palette = [
            {"name": "blue", "bg": "bg-blue-200", "border": "border-blue-400", "text": "text-blue-900"},
            {"name": "green", "bg": "bg-green-200", "border": "border-green-400", "text": "text-green-900"},
            {"name": "purple", "bg": "bg-purple-200", "border": "border-purple-400", "text": "text-purple-900"},
            {"name": "orange", "bg": "bg-orange-200", "border": "border-orange-400", "text": "text-orange-900"},
            {"name": "pink", "bg": "bg-pink-200", "border": "border-pink-400", "text": "text-pink-900"},
            {"name": "indigo", "bg": "bg-indigo-200", "border": "border-indigo-400", "text": "text-indigo-900"},
            {"name": "cyan", "bg": "bg-cyan-200", "border": "border-cyan-400", "text": "text-cyan-900"},
            {"name": "yellow", "bg": "bg-yellow-200", "border": "border-yellow-400", "text": "text-yellow-900"}
        ]
        
        # Назначаем цвета группам отправителей (больше 1 груза)
        sender_color_assignments = {}
        color_index = 0
        for sender_key, sender_data in sender_groups.items():
            if len(sender_data["cargo_list"]) > 1:  # Только группы с несколькими грузами
                sender_color_assignments[sender_key] = color_palette[color_index % len(color_palette)]
                color_index += 1
        
        # Назначаем цвета группам получателей (больше 1 груза)
        recipient_color_assignments = {}
        for recipient_key, recipient_data in recipient_groups.items():
            if len(recipient_data["cargo_list"]) > 1:  # Только группы с несколькими грузами
                recipient_color_assignments[recipient_key] = color_palette[color_index % len(color_palette)]
                color_index += 1
        
        return {
            "warehouse_id": warehouse_id,
            "total_cargo": len(all_cargo),
            "cargo": all_cargo,
            "sender_groups": {
                key: {
                    **data,
                    "color": sender_color_assignments.get(key, None),
                    "is_group": len(data["cargo_list"]) > 1
                }
                for key, data in sender_groups.items()
            },
            "recipient_groups": {
                key: {
                    **data,
                    "color": recipient_color_assignments.get(key, None),
                    "is_group": len(data["cargo_list"]) > 1
                }
                for key, data in recipient_groups.items()
            },
            "color_assignments": {
                "senders": sender_color_assignments,
                "recipients": recipient_color_assignments
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения грузов склада: {str(e)}"
        )

@app.get("/api/warehouses/placed-cargo")
async def get_placed_cargo(
    page: int = 1,
    per_page: int = 25,
    current_user: User = Depends(get_current_user)
):
    """Получение списка размещенных грузов"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для просмотра размещенных грузов"
        )
    
    try:
        # Определяем фильтр для складов в зависимости от роли пользователя
        warehouse_filter = {}
        if current_user.role == UserRole.WAREHOUSE_OPERATOR:
            # Оператор видит только грузы на своих складах
            operator_warehouse_bindings = list(db.operator_warehouse_bindings.find(
                {"operator_id": current_user.id}
            ))
            warehouse_ids = [binding["warehouse_id"] for binding in operator_warehouse_bindings]
            warehouse_filter = {"warehouse_id": {"$in": warehouse_ids}}
        
        # Основной фильтр - размещенные грузы и грузы готовые к размещению
        base_filter = {
            "status": {"$in": ["placed_in_warehouse", "awaiting_placement"]},
            **warehouse_filter
        }
        
        # Подсчитываем общее количество из operator_cargo (основная коллекция для грузов)
        total_count = db.operator_cargo.count_documents(base_filter)
        
        # Вычисляем параметры пагинации
        skip = (page - 1) * per_page
        total_pages = math.ceil(total_count / per_page)
        
        # Получаем грузы с пагинацией из operator_cargo
        cargo_cursor = db.operator_cargo.find(base_filter, {"_id": 0}).skip(skip).limit(per_page).sort("created_at", -1)
        cargo_list = list(cargo_cursor)
        
        # Получаем информацию о складах для каждого груза
        warehouse_ids = list(set([cargo.get("warehouse_id") for cargo in cargo_list if cargo.get("warehouse_id")]))
        warehouses_cursor = db.warehouses.find({"id": {"$in": warehouse_ids}})
        warehouses = {wh["id"]: wh for wh in warehouses_cursor}
        
        # Обогащаем данные о грузах информацией о местоположении
        enriched_cargo = []
        for cargo in cargo_list:
            cargo_data = serialize_mongo_document(cargo)
            
            # Добавляем информацию о складе
            warehouse_id = cargo.get("warehouse_id")
            if warehouse_id and warehouse_id in warehouses:
                warehouse = warehouses[warehouse_id]
                cargo_data["warehouse_name"] = warehouse.get("name", "Неизвестный склад")
                cargo_data["warehouse_address"] = warehouse.get("address", "Адрес не указан")
            else:
                cargo_data["warehouse_name"] = "Неизвестный склад"
                cargo_data["warehouse_address"] = "Адрес не указан"
            
            # Добавляем информацию о местоположении
            cargo_data["block_number"] = cargo.get("block_number", "Не указан")
            cargo_data["shelf_number"] = cargo.get("shelf_number", "Не указан") 
            cargo_data["cell_number"] = cargo.get("cell_number", "Не указан")
            
            # Добавляем дату размещения
            cargo_data["placement_date"] = cargo.get("placed_at", cargo.get("updated_at"))
            
            # Добавляем информацию об операторе, который разместил груз
            cargo_data["placement_operator"] = cargo.get("placed_by_operator", "Не указан")
            
            # Добавляем статус обработки
            cargo_data["processing_status"] = cargo.get("processing_status", "unknown")
            
            enriched_cargo.append(cargo_data)
        
        # Формируем ответ с пагинацией
        result = {
            "items": enriched_cargo,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_count,
                "pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения размещенных грузов: {str(e)}"
        )

@app.get("/api/warehouses/{warehouse_id}/available-cells/{block_number}/{shelf_number}")
async def get_available_cells_for_block_shelf(
    warehouse_id: str,
    block_number: int,
    shelf_number: int,
    current_user: User = Depends(get_current_user)
):
    """Получение свободных ячеек для конкретного блока и полки"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для просмотра свободных ячеек"
        )
    
    try:
        # Проверяем существование склада
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Склад не найден"
            )
        
        # Для оператора проверяем доступ к складу
        if current_user.role == UserRole.WAREHOUSE_OPERATOR:
            operator_binding = db.operator_warehouse_bindings.find_one({
                "operator_id": current_user.id,
                "warehouse_id": warehouse_id
            })
            if not operator_binding:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к данному складу"
                )
        
        # Получаем занятые ячейки для данного блока и полки
        occupied_cargo = list(db.cargo.find({
            "warehouse_id": warehouse_id,
            "block_number": block_number,
            "shelf_number": shelf_number,
            "status": "placed_in_warehouse"
        }, {"cell_number": 1}))
        
        occupied_cells = {cargo["cell_number"] for cargo in occupied_cargo if cargo.get("cell_number")}
        
        # Генерируем список всех возможных ячеек (по умолчанию 10 ячеек на полку)
        cells_per_shelf = warehouse.get("cells_per_shelf", 10)
        all_cells = set(range(1, cells_per_shelf + 1))
        
        # Определяем свободные ячейки
        available_cells = sorted(list(all_cells - occupied_cells))
        
        return {
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse.get("name", "Неизвестный склад"),
            "block_number": block_number,
            "shelf_number": shelf_number,
            "available_cells": available_cells,
            "total_cells": cells_per_shelf,
            "occupied_cells": len(occupied_cells),
            "available_count": len(available_cells)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения свободных ячеек: {str(e)}"
        )

@app.get("/api/warehouses/{warehouse_id}/detailed-structure")
async def get_warehouse_detailed_structure(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получение детальной структуры склада с информацией о занятости каждой ячейки"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для просмотра структуры склада"
        )
    
    try:
        # Проверяем существование склада
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Склад не найден"
            )
        
        # Для оператора проверяем доступ к складу
        if current_user.role == UserRole.WAREHOUSE_OPERATOR:
            operator_binding = db.operator_warehouse_bindings.find_one({
                "operator_id": current_user.id,
                "warehouse_id": warehouse_id
            })
            if not operator_binding:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет доступа к данному складу"
                )
        
        # Получаем размеры склада
        blocks_count = warehouse.get("blocks_count", 10)
        shelves_per_block = warehouse.get("shelves_per_block", 10)
        cells_per_shelf = warehouse.get("cells_per_shelf", 10)
        
        # Получаем все занятые ячейки на складе
        occupied_cargo = list(db.cargo.find({
            "warehouse_id": warehouse_id,
            "status": "placed_in_warehouse",
            "block_number": {"$exists": True, "$ne": None},
            "shelf_number": {"$exists": True, "$ne": None},
            "cell_number": {"$exists": True, "$ne": None}
        }, {
            "block_number": 1,
            "shelf_number": 1,
            "cell_number": 1,
            "cargo_number": 1,
            "cargo_name": 1,
            "total_weight": 1,
            "placed_at": 1
        }))
        
        # Создаем структуру склада
        warehouse_structure = {
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse.get("name", "Неизвестный склад"),
            "warehouse_info": {
                "name": warehouse.get("name", "Неизвестный склад"),
                "address": warehouse.get("address", "Адрес не указан"),
                "description": warehouse.get("description", ""),
                "is_active": warehouse.get("is_active", True)
            },
            "dimensions": {
                "blocks_count": blocks_count,
                "shelves_per_block": shelves_per_block,
                "cells_per_shelf": cells_per_shelf
            },
            "blocks": []
        }
        
        # Создаем карту занятых ячеек для быстрого поиска
        occupied_cells = {}
        for cargo in occupied_cargo:
            key = f"{cargo['block_number']}-{cargo['shelf_number']}-{cargo['cell_number']}"
            occupied_cells[key] = {
                "cargo_number": cargo.get("cargo_number"),
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "weight": cargo.get("total_weight", 0),
                "placed_at": cargo.get("placed_at")
            }
        
        # Генерируем структуру блоков
        for block_num in range(1, blocks_count + 1):
            block = {
                "block_number": block_num,
                "shelves": []
            }
            
            # Генерируем полки для каждого блока
            for shelf_num in range(1, shelves_per_block + 1):
                shelf = {
                    "shelf_number": shelf_num,
                    "cells": []
                }
                
                # Генерируем ячейки для каждой полки
                for cell_num in range(1, cells_per_shelf + 1):
                    cell_key = f"{block_num}-{shelf_num}-{cell_num}"
                    is_occupied = cell_key in occupied_cells
                    
                    cell = {
                        "cell_number": cell_num,
                        "status": "occupied" if is_occupied else "available",
                        "cargo_info": occupied_cells.get(cell_key) if is_occupied else None
                    }
                    shelf["cells"].append(cell)
                
                block["shelves"].append(shelf)
            
            warehouse_structure["blocks"].append(block)
        
        # Добавляем статистику
        total_cells = blocks_count * shelves_per_block * cells_per_shelf
        occupied_count = len(occupied_cargo)
        available_count = total_cells - occupied_count
        
        warehouse_structure["statistics"] = {
            "total_cells": total_cells,
            "occupied_cells": occupied_count,
            "available_cells": available_count,
            "occupancy_rate": round((occupied_count / total_cells) * 100, 2) if total_cells > 0 else 0
        }
        
        return warehouse_structure
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения структуры склада: {str(e)}"
        )

# ===== НОВЫЙ ENDPOINT: ПРЯМОЙ ПРИЁМ ГРУЗА ЧЕРЕЗ ОПЕРАТОРА =====

@app.post("/api/operator/cargo/direct-accept")
async def direct_accept_cargo_by_operator(
    cargo_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Прямой приём груза на склад через оператора (без курьера)"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для приёма грузов"
        )
    
    try:
        print(f"🏢 Прямой приём груза через оператора: {current_user.full_name}")
        
        # Генерируем базовый номер заявки
        base_request_number = f"{datetime.now().strftime('%y%m%d')}{str(random.randint(10000, 99999))[-4:]}"
        
        cargo_items = cargo_data.get("cargo_items", [])
        created_cargo_list = []
        
        # Если нет отдельных грузов, создаем один груз из общих данных
        if not cargo_items or len(cargo_items) == 0:
            cargo_items = [{
                "cargo_name": cargo_data.get("description", "Груз"),
                "weight": cargo_data.get("total_weight", 0),
                "value": cargo_data.get("total_cost", 0),
                "description": cargo_data.get("special_instructions", "")
            }]
        
        # Создаем отдельный груз для каждого элемента
        for index, cargo_item in enumerate(cargo_items, 1):
            cargo_id = str(uuid.uuid4())
            
            # Индивидуальный номер груза в формате: базовый_номер/номер_груза
            cargo_number = f"{base_request_number}/{index:02d}"
            
            cargo_document = {
                "id": cargo_id,
                "cargo_number": cargo_number,
                "base_request_number": base_request_number,  # Базовый номер заявки
                "item_sequence": index,  # Порядковый номер груза в заявке
                
                # Данные отправителя и получателя (общие для всех грузов заявки)
                "sender_full_name": cargo_data.get("sender_full_name"),
                "sender_phone": cargo_data.get("sender_phone"),
                "sender_address": cargo_data.get("sender_address"),
                "recipient_full_name": cargo_data.get("recipient_full_name"),
                "recipient_phone": cargo_data.get("recipient_phone"),
                "recipient_address": cargo_data.get("recipient_address"),
                
                # Данные конкретного груза
                "cargo_name": cargo_item.get("cargo_name", f"Груз №{index}"),
                "weight": float(cargo_item.get("weight", 0)),
                "declared_value": float(cargo_item.get("value", 0)),
                "description": cargo_item.get("description", ""),
                
                # Общие данные заявки
                "total_items_in_request": len(cargo_items),
                "route": cargo_data.get("route", "moscow_to_tajikistan"),
                
                # ВАЖНО: warehouse_id - это ТЕКУЩИЙ склад где находится груз (склад оператора который принял)
                "warehouse_id": get_operator_warehouse_ids(current_user.id)[0] if get_operator_warehouse_ids(current_user.id) else None,
                
                # destination_warehouse_id - это склад НАЗНАЧЕНИЯ (выбранный в форме)
                "destination_warehouse_id": cargo_data.get("warehouse_id"),
                
                "payment_method": cargo_data.get("payment_method", "not_paid"),
                
                # Статусы
                "status": "awaiting_placement",
                "processing_status": "accepted",
                
                # Информация о приёме
                "received_by_operator": current_user.full_name,
                "received_by_operator_id": current_user.id,
                "received_at": datetime.utcnow(),
                "acceptance_method": "direct_operator",
                
                # Системные поля
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "special_instructions": cargo_data.get("special_instructions", "")
            }
            
            # Сохраняем в основную коллекцию cargo
            db.cargo.insert_one(cargo_document)
            
            # Также добавляем в operator_cargo для отображения в списках оператора
            operator_cargo_document = {
                **cargo_document,
                "operator_id": current_user.id,
                "assigned_at": datetime.utcnow()
            }
            db.operator_cargo.insert_one(operator_cargo_document)
            
            created_cargo_list.append({
                "id": cargo_id,
                "cargo_id": cargo_id,  # For backward compatibility
                "cargo_number": cargo_number,
                "cargo_name": cargo_document["cargo_name"],
                "weight": cargo_document["weight"],
                "declared_value": cargo_document["declared_value"],
                "base_request_number": base_request_number,
                "item_sequence": index,
                "warehouse_id": cargo_document["warehouse_id"]
            })
            
            print(f"✅ Груз {cargo_number} (груз {index} из {len(cargo_items)}) успешно принят через оператора {current_user.full_name}")
        
        return {
            "success": True,
            "message": f"Успешно принято {len(created_cargo_list)} грузов на склад через оператора",
            "base_request_number": base_request_number,
            "created_cargo": created_cargo_list,
            "total_cargo_count": len(created_cargo_list),
            "current_warehouse_id": get_operator_warehouse_ids(current_user.id)[0] if get_operator_warehouse_ids(current_user.id) else None,
            "destination_warehouse_id": cargo_data.get("warehouse_id"),
            "received_by": current_user.full_name,
            "received_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Ошибка при приёме груза через оператора: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при приёме груза: {str(e)}"
        )

@app.post("/api/operator/cargo/generate-qr-batch")
async def generate_qr_codes_for_cargo_batch(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Генерация QR кодов для всех грузов заявки"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    base_request_number = request.get("base_request_number")
    cargo_ids = request.get("cargo_ids", [])
    
    if not base_request_number and not cargo_ids:
        raise HTTPException(status_code=400, detail="Требуется base_request_number или cargo_ids")
    
    # Найти все грузы заявки
    if base_request_number:
        cargo_list = list(db.cargo.find({"base_request_number": base_request_number}))
        operator_cargo_list = list(db.operator_cargo.find({"base_request_number": base_request_number}))
        all_cargo = cargo_list + operator_cargo_list
    else:
        # Поиск по списку ID
        cargo_list = list(db.cargo.find({"id": {"$in": cargo_ids}}))
        operator_cargo_list = list(db.operator_cargo.find({"id": {"$in": cargo_ids}}))
        all_cargo = cargo_list + operator_cargo_list
    
    if not all_cargo:
        raise HTTPException(status_code=404, detail="Грузы не найдены")
    
    generated_qr_codes = []
    errors = []
    
    for cargo in all_cargo:
        try:
            cargo_id = cargo["id"]
            cargo_number = cargo["cargo_number"]
            weight = cargo.get("weight", 0)
            
            # Генерировать числовой QR код для груза: ГГГГВВВССС
            cargo_digits = ''.join(filter(str.isdigit, cargo_number))
            if len(cargo_digits) < 4:
                cargo_digits = cargo_digits.ljust(4, '0')
            else:
                cargo_digits = cargo_digits[:4]
            
            weight_int = int(float(weight)) if weight else 0
            weight_str = str(weight_int).zfill(3)[-3:]
            
            suffix = str(random.randint(100, 999))
            numeric_qr_code = f"{cargo_digits}{weight_str}{suffix}"
            
            # Создать QR код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(numeric_qr_code)
            qr.make(fit=True)

            qr_image = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            qr_image.save(buffered, format="PNG")
            qr_base64 = base64.b64encode(buffered.getvalue()).decode()
            qr_code_url = f"data:image/png;base64,{qr_base64}"
            
            # Обновить груз с QR кодом
            update_result_cargo = db.cargo.update_one(
                {"id": cargo_id},
                {"$set": {
                    "qr_code": qr_code_url,
                    "qr_data": numeric_qr_code,
                    "qr_generated_at": datetime.utcnow(),
                    "qr_generated_by": current_user.id
                }}
            )
            
            # Также обновить в operator_cargo если существует
            db.operator_cargo.update_one(
                {"id": cargo_id},
                {"$set": {
                    "qr_code": qr_code_url,
                    "qr_data": numeric_qr_code,
                    "qr_generated_at": datetime.utcnow(),
                    "qr_generated_by": current_user.id
                }}
            )
            
            generated_qr_codes.append({
                "cargo_id": cargo_id,
                "cargo_number": cargo_number,
                "cargo_name": cargo.get("cargo_name", "Груз"),
                "weight": weight,
                "qr_code": qr_code_url,
                "qr_data": numeric_qr_code,
                "success": True
            })
            
        except Exception as e:
            errors.append(f"Ошибка для груза {cargo.get('cargo_number', 'неизвестен')}: {str(e)}")
    
    return {
        "success": True,
        "generated_count": len(generated_qr_codes),
        "error_count": len(errors),
        "qr_codes": generated_qr_codes,
        "errors": errors,
        "base_request_number": base_request_number,
        "message": f"QR коды сгенерированы для {len(generated_qr_codes)} грузов, ошибок: {len(errors)}"
    }

# ===== АДМИНИСТРАТИВНЫЕ ФУНКЦИИ УДАЛЕНИЯ =====

@app.delete("/api/admin/warehouses/bulk")
async def delete_warehouses_bulk(
    request: BulkDeleteRequest,
    current_user: User = Depends(get_current_user)
):
    """Массовое удаление складов"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления складов"
        )
    
    try:
        ids_to_delete = request.ids
        if not ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Список ID для удаления не может быть пустым"
            )
        
        print(f"🗑️ Массовое удаление складов: {len(ids_to_delete)} ID: {ids_to_delete}")
        
        deleted_count = 0
        errors = []
        
        for warehouse_id in ids_to_delete:
            try:
                # Проверяем наличие грузов на складе
                cargo_count = db.cargo.count_documents({
                    "warehouse_id": warehouse_id,
                    "status": "placed_in_warehouse"
                })
                
                if cargo_count > 0:
                    warehouse = db.warehouses.find_one({"id": warehouse_id})
                    warehouse_name = warehouse.get('name', f'Склад {warehouse_id}') if warehouse else f'Склад {warehouse_id}'
                    errors.append(f"{warehouse_name}: на складе {cargo_count} груз(ов)")
                    continue
                
                # Удаляем привязки операторов
                db.operator_warehouse_bindings.delete_many({"warehouse_id": warehouse_id})
                
                # Удаляем склад
                result = db.warehouses.delete_one({"id": warehouse_id})
                if result.deleted_count > 0:
                    deleted_count += 1
                    print(f"✅ Удален склад: {warehouse_id}")
                else:
                    errors.append(f"Склад {warehouse_id}: не найден")
                    
            except Exception as e:
                print(f"❌ Ошибка удаления склада {warehouse_id}: {str(e)}")
                errors.append(f"Склад {warehouse_id}: {str(e)}")
        
        print(f"✅ Итого удалено складов: {deleted_count} из {len(ids_to_delete)}")
        
        return {
            "message": f"Успешно удалено складов: {deleted_count}",
            "deleted_count": deleted_count,
            "total_requested": len(ids_to_delete),
            "errors": errors,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка массового удаления складов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка массового удаления складов: {str(e)}"
        )

@app.delete("/api/admin/warehouses/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление склада (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления складов"
        )
    
    try:
        # Проверяем существование склада
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Склад не найден"
            )
        
        # Проверяем, нет ли грузов на складе
        cargo_count = db.cargo.count_documents({
            "warehouse_id": warehouse_id,
            "status": "placed_in_warehouse"
        })
        
        if cargo_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно удалить склад. На складе находится {cargo_count} груз(ов)"
            )
        
        # Удаляем привязки операторов к складу
        db.operator_warehouse_bindings.delete_many({"warehouse_id": warehouse_id})
        
        # Удаляем склад
        result = db.warehouses.delete_one({"id": warehouse_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Склад не найден для удаления"
            )
        
        return {
            "message": f"Склад '{warehouse.get('name', 'Неизвестно')}' успешно удален",
            "deleted_id": warehouse_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления склада: {str(e)}"
        )

@app.delete("/api/admin/cargo/bulk")
async def delete_cargo_bulk(
    request: BulkDeleteRequest,
    current_user: User = Depends(get_current_user)
):
    """Массовое удаление грузов"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления грузов"
        )
    
    try:
        ids_to_delete = request.ids
        if not ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Список ID для удаления не может быть пустым"
            )
        
        print(f"🗑️ Массовое удаление грузов: {len(ids_to_delete)} ID: {ids_to_delete}")
        
        # Массовое удаление из обеих коллекций
        result_user = db.cargo.delete_many({"id": {"$in": ids_to_delete}})
        result_operator = db.operator_cargo.delete_many({"id": {"$in": ids_to_delete}})
        
        total_deleted = result_user.deleted_count + result_operator.deleted_count
        
        print(f"✅ Удалено грузов: {total_deleted} (user: {result_user.deleted_count}, operator: {result_operator.deleted_count})")
        
        return {
            "message": f"Успешно удалено грузов: {total_deleted}",
            "deleted_count": total_deleted,
            "total_requested": len(ids_to_delete),
            "deleted_from_user_collection": result_user.deleted_count,
            "deleted_from_operator_collection": result_operator.deleted_count,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка массового удаления грузов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка массового удаления грузов: {str(e)}"
        )

@app.delete("/api/admin/cargo/{cargo_id}")
async def delete_cargo(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление груза (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления грузов"
        )
    
    try:
        # Ищем груз в обеих коллекциях
        cargo_user = db.cargo.find_one({"id": cargo_id})
        cargo_operator = db.operator_cargo.find_one({"id": cargo_id})
        
        if not cargo_user and not cargo_operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Груз не найден"
            )
        
        # Удаляем из обеих коллекций
        deleted_count = 0
        if cargo_user:
            result_user = db.cargo.delete_one({"id": cargo_id})
            deleted_count += result_user.deleted_count
            
        if cargo_operator:
            result_operator = db.operator_cargo.delete_one({"id": cargo_id})
            deleted_count += result_operator.deleted_count
        
        cargo_info = cargo_user or cargo_operator
        cargo_number = cargo_info.get("cargo_number", cargo_id)
        
        return {
            "message": f"Груз {cargo_number} успешно удален",
            "deleted_id": cargo_id,
            "deleted_from_collections": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления груза: {str(e)}"
        )

@app.delete("/api/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление пользователя (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления пользователей"
        )
    
    try:
        # Нельзя удалить самого себя
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить свой собственный аккаунт"
            )
        
        # Найдем пользователя
        user = db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        # Проверяем, есть ли связанные грузы
        cargo_count = db.cargo.count_documents({"sender_id": user_id})
        if cargo_count > 0:
            return {
                "message": f"Внимание: у пользователя {user.get('full_name', 'Неизвестно')} есть {cargo_count} связанных груз(ов). Удаление выполнено, но грузы сохранены.",
                "warning": True,
                "cargo_count": cargo_count
            }
        
        # Если это оператор склада, удаляем привязки к складам
        if user.get('role') == 'warehouse_operator':
            db.operator_warehouse_bindings.delete_many({"operator_id": user_id})
        
        # Удаляем пользователя
        result = db.users.delete_one({"id": user_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден для удаления"
            )
        
        return {
            "message": f"Пользователь '{user.get('full_name', 'Неизвестно')}' успешно удален",
            "deleted_id": user_id,
            "deleted_role": user.get('role', 'unknown')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления пользователя: {str(e)}"
        )

@app.delete("/api/admin/users/bulk")
async def delete_users_bulk(
    user_ids: dict,
    current_user: User = Depends(get_current_user)
):
    """Массовое удаление пользователей"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления пользователей"
        )
    
    try:
        ids_to_delete = user_ids.get("ids", [])
        if not ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Список ID для удаления не может быть пустым"
            )
        
        # Исключаем текущего пользователя из списка удаления
        ids_to_delete = [uid for uid in ids_to_delete if uid != current_user.id]
        
        if not ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="После исключения вашего аккаунта список для удаления пуст"
            )
        
        deleted_count = 0
        warnings = []
        
        # Удаляем привязки операторов к складам
        db.operator_warehouse_bindings.delete_many({"operator_id": {"$in": ids_to_delete}})
        
        # Проверяем связанные грузы
        for user_id in ids_to_delete:
            cargo_count = db.cargo.count_documents({"sender_id": user_id})
            if cargo_count > 0:
                user = db.users.find_one({"id": user_id})
                user_name = user.get('full_name', f'Пользователь {user_id}') if user else f'Пользователь {user_id}'
                warnings.append(f"{user_name}: {cargo_count} связанных грузов")
        
        # Массовое удаление пользователей
        result = db.users.delete_many({"id": {"$in": ids_to_delete}})
        deleted_count = result.deleted_count
        
        return {
            "message": f"Успешно удалено пользователей: {deleted_count}",
            "deleted_count": deleted_count,
            "total_requested": len(ids_to_delete),
            "warnings": warnings,
            "excluded_current_user": current_user.id in user_ids.get("ids", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка массового удаления пользователей: {str(e)}"
        )

# ===== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ МАССОВОГО УДАЛЕНИЯ =====

@app.delete("/api/admin/cargo-applications/bulk")
async def delete_cargo_applications_bulk(
    request_ids: dict,
    current_user: User = Depends(get_current_user)
):
    """Массовое удаление заявок на груз"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления заявок"
        )
    
    try:
        ids_to_delete = request_ids.get("ids", [])
        if not ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Список ID для удаления не может быть пустым"
            )
        
        # Массовое удаление заявок
        result = db.cargo_requests.delete_many({"id": {"$in": ids_to_delete}})
        deleted_count = result.deleted_count
        
        return {
            "message": f"Успешно удалено заявок: {deleted_count}",
            "deleted_count": deleted_count,
            "total_requested": len(ids_to_delete)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка массового удаления заявок: {str(e)}"
        )

@app.delete("/api/admin/cargo-applications/{request_id}")
async def delete_cargo_application(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление заявки на груз (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления заявок"
        )
    
    try:
        # Найдем заявку
        request = db.cargo_requests.find_one({"id": request_id})
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заявка не найдена"
            )
        
        # Удаляем заявку
        result = db.cargo_requests.delete_one({"id": request_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Заявка не найдена для удаления"
            )
        
        return {
            "message": f"Заявка №{request.get('request_number', 'Неизвестно')} успешно удалена",
            "deleted_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления заявки: {str(e)}"
        )

@app.delete("/api/admin/operators/bulk")
async def delete_operators_bulk(
    operator_ids: dict,
    current_user: User = Depends(get_current_user)
):
    """Массовое удаление операторов склада"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления операторов"
        )
    
    try:
        ids_to_delete = operator_ids.get("ids", [])
        if not ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Список ID для удаления не может быть пустым"
            )
        
        # Исключаем текущего пользователя из списка удаления
        ids_to_delete = [uid for uid in ids_to_delete if uid != current_user.id]
        
        if not ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="После исключения вашего аккаунта список для удаления пуст"
            )
        
        deleted_count = 0
        warnings = []
        
        # Удаляем привязки операторов к складам
        db.operator_warehouse_bindings.delete_many({"operator_id": {"$in": ids_to_delete}})
        
        # Проверяем связанные грузы
        for operator_id in ids_to_delete:
            cargo_count = db.operator_cargo.count_documents({"created_by": operator_id})
            if cargo_count > 0:
                operator = db.users.find_one({"id": operator_id})
                operator_name = operator.get('full_name', f'Оператор {operator_id}') if operator else f'Оператор {operator_id}'
                warnings.append(f"{operator_name}: обработал {cargo_count} груз(ов)")
        
        # Массовое удаление операторов (только с ролью warehouse_operator)
        result = db.users.delete_many({
            "id": {"$in": ids_to_delete}, 
            "role": "warehouse_operator"
        })
        deleted_count = result.deleted_count
        
        return {
            "message": f"Успешно удалено операторов: {deleted_count}",
            "deleted_count": deleted_count,
            "total_requested": len(ids_to_delete),
            "warnings": warnings,
            "excluded_current_user": current_user.id in operator_ids.get("ids", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка массового удаления операторов: {str(e)}"
        )

@app.delete("/api/admin/pickup-requests/bulk")
async def delete_pickup_requests_bulk(
    request_ids: dict,
    current_user: User = Depends(get_current_user)
):
    """Массовое удаление заявок на забор"""
    if current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять заявки на забор")
    
    try:
        ids = request_ids.get("ids", [])
        if not ids:
            raise HTTPException(status_code=400, detail="Не указаны ID заявок для удаления")
        
        success_count = 0
        error_messages = []
        
        for request_id in ids:
            try:
                # Проверяем существование заявки
                request = db.courier_pickup_requests.find_one({"id": request_id}, {"_id": 0})
                if not request:
                    error_messages.append(f"Заявка {request_id} не найдена")
                    continue
                
                # Проверяем, можно ли удалять заявку
                if request.get('request_status') == 'completed':
                    error_messages.append(f"Нельзя удалить завершенную заявку {request_id}")
                    continue
                    
                # Если заявка в процессе обработки, нужно освободить курьера
                if request.get('assigned_courier_id'):
                    db.couriers.update_one(
                        {"id": request.get('assigned_courier_id')},
                        {"$unset": {"current_pickup_request_id": ""}}
                    )
                
                # Удаляем связанные уведомления
                db.warehouse_notifications.delete_many({"pickup_request_id": request_id})
                
                # Удаляем саму заявку
                result = db.courier_pickup_requests.delete_one({"id": request_id})
                if result.deleted_count > 0:
                    success_count += 1
                else:
                    error_messages.append(f"Не удалось удалить заявку {request_id}")
                    
            except Exception as e:
                error_messages.append(f"Ошибка при удалении заявки {request_id}: {str(e)}")
        
        message = f"Успешно удалено заявок: {success_count} из {len(ids)}"
        
        return {
            "message": message,
            "success_count": success_count,
            "total_count": len(ids),
            "errors": error_messages
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления заявок на забор: {str(e)}"
        )

@app.delete("/api/admin/operators/{operator_id}")
async def delete_operator(
    operator_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление оператора склада (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления операторов"
        )
    
    try:
        # Нельзя удалить самого себя
        if operator_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить свой собственный аккаунт"
            )
        
        # Найдем пользователя-оператора
        operator = db.users.find_one({"id": operator_id, "role": "warehouse_operator"})
        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оператор склада не найден"
            )
        
        # Проверяем, есть ли связанные грузы, обработанные оператором
        cargo_count = db.operator_cargo.count_documents({"created_by": operator_id})
        if cargo_count > 0:
            return {
                "message": f"Внимание: оператор {operator.get('full_name', 'Неизвестно')} обработал {cargo_count} груз(ов). Удаление выполнено, но грузы сохранены.",
                "warning": True,
                "cargo_count": cargo_count
            }
        
        # Удаляем привязки к складам
        db.operator_warehouse_bindings.delete_many({"operator_id": operator_id})
        
        # Удаляем оператора
        result = db.users.delete_one({"id": operator_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Оператор не найден для удаления"
            )
        
        return {
            "message": f"Оператор '{operator.get('full_name', 'Неизвестно')}' успешно удален",
            "deleted_id": operator_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления оператора: {str(e)}"
        )

# ===== ЭНДПОИНТЫ УДАЛЕНИЯ ТРАНСПОРТА =====

@app.delete("/api/admin/transports/bulk")
async def delete_transports_bulk(
    transport_ids: dict,
    current_user: User = Depends(get_current_user)
):
    """Массовое удаление транспорта (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления транспорта"
        )
    
    try:
        ids_to_delete = transport_ids.get("ids", [])
        if not ids_to_delete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Список ID для удаления не может быть пустым"
            )
        
        deleted_count = 0
        errors = []
        
        for transport_id in ids_to_delete:
            try:
                # Найдем транспорт
                transport = db.transports.find_one({"id": transport_id})
                if not transport:
                    errors.append(f"Транспорт {transport_id}: не найден")
                    continue
                
                # Проверяем, есть ли груз в транспорте
                cargo_count = len(transport.get("cargo_list", []))
                if cargo_count > 0:
                    transport_name = f"Транспорт {transport.get('transport_number', transport_id)}"
                    errors.append(f"{transport_name}: содержит {cargo_count} груз(ов). Удаление запрещено")
                    continue
                
                # Удаляем транспорт (только пустой)
                result = db.transports.delete_one({"id": transport_id})
                if result.deleted_count > 0:
                    deleted_count += 1
                    
            except Exception as e:
                errors.append(f"Транспорт {transport_id}: {str(e)}")
        
        return {
            "message": f"Успешно удалено транспорта: {deleted_count}",
            "deleted_count": deleted_count,
            "total_requested": len(ids_to_delete),
            "errors": errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка массового удаления транспорта: {str(e)}"
        )

@app.delete("/api/admin/transports/{transport_id}")
async def delete_transport(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление транспорта (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления транспорта"
        )
    
    try:
        # Найдем транспорт
        transport = db.transports.find_one({"id": transport_id})
        if not transport:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Транспорт не найден"
            )
        
        # Проверяем, есть ли груз в транспорте
        cargo_count = len(transport.get("cargo_list", []))
        if cargo_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Невозможно удалить транспорт. В транспорте находится {cargo_count} груз(ов). Сначала удалите или переместите груз"
            )
        
        # Удаляем транспорт
        result = db.transports.delete_one({"id": transport_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Транспорт не найден для удаления"
            )
        
        return {
            "message": f"Транспорт '{transport.get('transport_number', 'Неизвестно')}' успешно удален",
            "deleted_id": transport_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления транспорта: {str(e)}"
        )

@app.post("/api/transport/create-interwarehouse")
async def create_interwarehouse_transport(
    transport_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Создать улучшенный межскладской транспорт с автоматическим выбором исходного склада (Функция 3)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    source_warehouse_id = transport_data.get("source_warehouse_id")
    destination_warehouse_id = transport_data.get("destination_warehouse_id")
    auto_select_source = transport_data.get("auto_select_source", False)
    
    # Автоматический выбор исходного склада для операторов
    if current_user.role == UserRole.WAREHOUSE_OPERATOR and (auto_select_source or not source_warehouse_id):
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        if not operator_warehouse_ids:
            raise HTTPException(status_code=403, detail="No warehouses assigned to this operator")
        
        # Автоматически выбираем первый привязанный склад как исходный
        source_warehouse_id = operator_warehouse_ids[0]
        
    if not source_warehouse_id or not destination_warehouse_id:
        raise HTTPException(status_code=400, detail="Source and destination warehouses required")
    
    if source_warehouse_id == destination_warehouse_id:
        raise HTTPException(status_code=400, detail="Source and destination warehouses must be different")
    
    # Для операторов проверяем доступ к складам
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        operator_warehouse_ids = get_operator_warehouse_ids(current_user.id)
        
        # Оператор должен иметь доступ к ОБОИМ складам (исходному И целевому)
        if source_warehouse_id not in operator_warehouse_ids:
            raise HTTPException(status_code=403, detail="No access to source warehouse")
        
        if destination_warehouse_id not in operator_warehouse_ids:
            raise HTTPException(status_code=403, detail="No access to destination warehouse")
    
    # Проверяем существование складов
    source_warehouse = db.warehouses.find_one({"id": source_warehouse_id})
    destination_warehouse = db.warehouses.find_one({"id": destination_warehouse_id})
    
    if not source_warehouse or not destination_warehouse:
        raise HTTPException(status_code=404, detail="Source or destination warehouse not found")
    
    # Подсчитываем доступные грузы на исходном складе
    available_cargo_user = db.cargo.count_documents({
        "warehouse_id": source_warehouse_id, 
        "status": {"$in": ["placed_in_warehouse", "accepted"]}
    })
    available_cargo_operator = db.operator_cargo.count_documents({
        "warehouse_id": source_warehouse_id, 
        "status": {"$in": ["placed_in_warehouse", "accepted"]}
    })
    total_available_cargo = available_cargo_user + available_cargo_operator
    
    # Создаем транспорт
    transport_id = str(uuid.uuid4())
    transport_number = f"IW-{transport_id[-8:].upper()}"  # Межскладской префикс
    
    direction = f"{source_warehouse['name']} → {destination_warehouse['name']}"
    
    transport = {
        "id": transport_id,
        "transport_number": transport_number,
        "driver_name": transport_data.get("driver_name", ""),
        "driver_phone": transport_data.get("driver_phone", ""),
        "direction": direction,
        "capacity_kg": transport_data.get("capacity_kg", 1000),
        "current_load_kg": 0,
        "status": TransportStatus.EMPTY,
        "cargo_list": [],
        "is_interwarehouse": True,
        "source_warehouse_id": source_warehouse_id,
        "source_warehouse_name": source_warehouse["name"],
        "destination_warehouse_id": destination_warehouse_id,
        "destination_warehouse_name": destination_warehouse["name"],
        "created_at": datetime.utcnow(),
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "auto_selected_source": auto_select_source or (current_user.role == UserRole.WAREHOUSE_OPERATOR and not transport_data.get("source_warehouse_id")),
        "available_cargo_at_source": total_available_cargo
    }
    
    db.transports.insert_one(transport)
    
    # Создать уведомление
    notification_message = f"Создан межскладской транспорт {transport_number}: {direction}"
    if transport["auto_selected_source"]:
        notification_message += f" (исходный склад выбран автоматически)"
    
    create_system_notification(
        "Новый межскладской транспорт",
        notification_message,
        "transport",
        transport_id,
        None,
        current_user.id
    )
    
    return {
        "message": "Interwarehouse transport created successfully", 
        "transport_id": transport_id,
        "transport_number": transport_number,
        "source_warehouse": {
            "id": source_warehouse_id,
            "name": source_warehouse["name"]
        },
        "destination_warehouse": {
            "id": destination_warehouse_id, 
            "name": destination_warehouse["name"]
        },
        "auto_selected_source": transport["auto_selected_source"],
        "available_cargo_at_source": total_available_cargo,
        "created_by": current_user.full_name
    }

@app.get("/api/transport/{transport_id}")
async def get_transport(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    return Transport(**transport)

@app.get("/api/transport/{transport_id}/cargo-list")
async def get_transport_cargo(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    # Получить детали грузов
    cargo_details = []
    for cargo_id in transport.get("cargo_list", []):
        cargo = db.cargo.find_one({"id": cargo_id})
        if not cargo:
            cargo = db.operator_cargo.find_one({"id": cargo_id})
        
        if cargo:
            cargo_details.append({
                "id": cargo["id"],
                "cargo_number": cargo["cargo_number"],
                "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")),
                "description": cargo.get("description", ""),
                "weight": cargo["weight"],
                "declared_value": cargo["declared_value"],
                "recipient_name": cargo.get("recipient_name") or cargo.get("recipient_full_name", "Не указан"),
                "sender_full_name": cargo.get("sender_full_name", "Не указан"),
                "sender_phone": cargo.get("sender_phone", "Не указан"),
                "recipient_phone": cargo.get("recipient_phone", "Не указан"),
                "status": cargo.get("status", "unknown")
            })
    
    return {
        "transport": Transport(**transport),
        "cargo_list": cargo_details,
        "total_weight": sum(c["weight"] for c in cargo_details),
        "cargo_count": len(cargo_details)
    }

@app.post("/api/transport/{transport_id}/place-cargo")
async def place_cargo_on_transport(
    transport_id: str,
    placement: TransportCargoPlacementByNumbers,
    current_user: User = Depends(get_current_user)
):
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    if transport["status"] not in [TransportStatus.EMPTY, TransportStatus.FILLED]:
        raise HTTPException(status_code=400, detail="Cannot place cargo on transport in current status")
    
    # Найти грузы по номерам из всех коллекций и складов
    total_weight = 0
    cargo_details = []
    found_cargo_ids = []
    
    for cargo_number in placement.cargo_numbers:
        cargo_number = cargo_number.strip()
        if not cargo_number:
            continue
            
        # Искать в коллекции пользовательских грузов
        cargo = db.cargo.find_one({"cargo_number": cargo_number})
        if not cargo:
            # Искать в коллекции операторских грузов
            cargo = db.operator_cargo.find_one({"cargo_number": cargo_number})
        
        if not cargo:
            raise HTTPException(status_code=404, detail=f"Cargo {cargo_number} not found")
        
        # Проверить права доступа оператора к складу (если это не админ)
        if current_user.role == UserRole.WAREHOUSE_OPERATOR:
            if cargo.get("warehouse_id"):
                if not is_operator_allowed_for_warehouse(current_user.id, cargo["warehouse_id"]):
                    raise HTTPException(status_code=403, detail=f"Access denied to cargo {cargo_number} - not your warehouse")
        
        # Проверить, что груз на складе и доступен для загрузки
        if cargo["status"] not in ["accepted", "arrived_destination", "in_transit"]:
            raise HTTPException(status_code=400, detail=f"Cargo {cargo_number} is not available for loading (status: {cargo['status']})")
        
        if not cargo.get("warehouse_location"):
            raise HTTPException(status_code=400, detail=f"Cargo {cargo_number} is not in warehouse")
        
        total_weight += cargo["weight"]
        cargo_details.append(cargo)
        found_cargo_ids.append(cargo["id"])
    
    if not cargo_details:
        raise HTTPException(status_code=400, detail="No valid cargo numbers provided")
    
    # Проверить, что груз помещается в транспорт
    current_load = transport.get("current_load_kg", 0)
    if current_load + total_weight > transport["capacity_kg"]:
        raise HTTPException(status_code=400, detail=f"Transport capacity exceeded: current {current_load}kg + new {total_weight}kg > capacity {transport['capacity_kg']}kg")
    
    # Обновить транспорт
    new_cargo_list = list(set(transport.get("cargo_list", []) + found_cargo_ids))
    new_load = current_load + total_weight
    new_status = TransportStatus.FILLED if new_load >= transport["capacity_kg"] * 0.9 else transport["status"]
    
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "cargo_list": new_cargo_list,
            "current_load_kg": new_load,
            "status": new_status,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Обновить статус грузов и освободить ячейки склада
    for cargo in cargo_details:
        # Определить, в какой коллекции находится груз
        collection = db.cargo if db.cargo.find_one({"id": cargo["id"]}) else db.operator_cargo
        
        # Обновить статус груза
        collection.update_one(
            {"id": cargo["id"]},
            {"$set": {
                "status": "in_transit",
                "updated_at": datetime.utcnow(),
                "transport_id": transport_id
            }}
        )
        
        # Освободить ячейку склада
        if cargo.get("warehouse_location") and cargo.get("warehouse_id"):
            # Найти и освободить ячейку
            warehouse_id = cargo["warehouse_id"]
            block_num = cargo.get("block_number")
            shelf_num = cargo.get("shelf_number") 
            cell_num = cargo.get("cell_number")
            
            if block_num and shelf_num and cell_num:
                location_code = f"B{block_num}-S{shelf_num}-C{cell_num}"
                
                # Освободить ячейку
                db.warehouse_cells.update_one(
                    {
                        "warehouse_id": warehouse_id,
                        "location_code": location_code,
                        "cargo_id": cargo["id"]
                    },
                    {"$set": {
                        "is_occupied": False,
                        "updated_at": datetime.utcnow()
                    }, "$unset": {"cargo_id": ""}}
                )
                
                print(f"Freed warehouse cell {location_code} in warehouse {warehouse_id} for cargo {cargo['cargo_number']}")
        
        # Очистить местоположение груза 
        collection.update_one(
            {"id": cargo["id"]},
            {"$unset": {
                "warehouse_location": "",
                "warehouse_id": "",
                "block_number": "",
                "shelf_number": "",
                "cell_number": ""
            }}
        )
        
        # Создать уведомление пользователю (если есть sender_id)
        sender_id = cargo.get("sender_id") or cargo.get("created_by")
        if sender_id:
            create_notification(
                sender_id,
                f"Ваш груз {cargo['cargo_number']} загружен в транспорт {transport['transport_number']} и готов к отправке",
                cargo["id"]
            )
    
    return {
        "message": f"Successfully placed {len(found_cargo_ids)} cargo items on transport",
        "cargo_count": len(found_cargo_ids),
        "total_weight": total_weight,
        "cargo_numbers": [cargo["cargo_number"] for cargo in cargo_details]
    }

@app.post("/api/transport/{transport_id}/dispatch")
async def dispatch_transport(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    # Проверяем, что транспорт не в пути уже
    if transport["status"] == TransportStatus.IN_TRANSIT:
        raise HTTPException(status_code=400, detail="Transport is already in transit")
    
    # Разрешаем отправку транспорта с любым объемом груза
    # Убираем проверку на обязательное заполнение до 90%
    
    # Обновить статус транспорта
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "status": TransportStatus.IN_TRANSIT,
            "dispatched_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Обновить статус всех грузов и отправить уведомления
    for cargo_id in transport.get("cargo_list", []):
        cargo = db.cargo.find_one({"id": cargo_id})
        if cargo:
            # Обновить статус груза
            db.cargo.update_one(
                {"id": cargo_id},
                {"$set": {
                    "status": "in_transit",
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # Создать уведомление пользователю
            create_notification(
                cargo["sender_id"],
                f"Ваш груз {cargo['cargo_number']} отправлен в место назначения на транспорте {transport['transport_number']}",
                cargo_id
            )
    
    # Создать системное уведомление
    create_system_notification(
        "Транспорт отправлен",
        f"Транспорт {transport['transport_number']} отправлен в направлении {transport['direction']} с {len(transport.get('cargo_list', []))} грузами",
        "transport",
        transport_id,
        None,
        current_user.id
    )
    
    return {"message": "Transport dispatched successfully"}

@app.post("/api/transport/{transport_id}/arrive")
async def mark_transport_arrived(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    """Отметить транспорт как прибывший"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    if transport["status"] != TransportStatus.IN_TRANSIT:
        raise HTTPException(status_code=400, detail="Transport must be in transit to mark as arrived")
    
    # Обновить статус транспорта
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "status": TransportStatus.ARRIVED,
            "arrived_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Обновить статус всех грузов на arrived_destination
    for cargo_id in transport.get("cargo_list", []):
        # Поиск в обеих коллекциях
        cargo = db.cargo.find_one({"id": cargo_id})
        collection_name = "cargo"
        if not cargo:
            cargo = db.operator_cargo.find_one({"id": cargo_id})
            collection_name = "operator_cargo"
        
        if cargo:
            # Обновить статус груза
            db[collection_name].update_one(
                {"id": cargo_id},
                {"$set": {
                    "status": CargoStatus.ARRIVED_DESTINATION,
                    "arrived_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # Создать уведомление пользователю
            if collection_name == "cargo":
                create_personal_notification(
                    cargo["sender_id"], 
                    "Груз прибыл", 
                    f"Ваш груз №{cargo['cargo_number']} прибыл в место назначения",
                    "cargo",
                    cargo_id
                )
    
    # Создать системное уведомление
    create_system_notification(
        "Транспорт прибыл",
        f"Транспорт {transport['transport_number']} прибыл в место назначения с {len(transport.get('cargo_list', []))} грузами",
        "transport",
        transport_id,
        None,
        current_user.id
    )
    
    return {"message": "Transport marked as arrived successfully"}

@app.get("/api/transport/{transport_id}/arrived-cargo")
async def get_arrived_transport_cargo(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить грузы из прибывшего транспорта для размещения на складе"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    if transport["status"] != TransportStatus.ARRIVED:
        raise HTTPException(status_code=400, detail="Transport must be arrived to access cargo for placement")
    
    # Получить детали грузов для размещения
    cargo_details = []
    for cargo_id in transport.get("cargo_list", []):
        cargo = db.cargo.find_one({"id": cargo_id})
        collection_name = "cargo"
        if not cargo:
            cargo = db.operator_cargo.find_one({"id": cargo_id})
            collection_name = "operator_cargo"
        
        if cargo:
            cargo_details.append({
                "id": cargo["id"],
                "cargo_number": cargo["cargo_number"],
                "cargo_name": cargo.get("cargo_name", cargo.get("description", "Груз")),
                "description": cargo.get("description", ""),
                "weight": cargo["weight"],
                "declared_value": cargo["declared_value"],
                "sender_full_name": cargo.get("sender_full_name", "Не указан"),
                "sender_phone": cargo.get("sender_phone", "Не указан"),
                "recipient_full_name": cargo.get("recipient_full_name", cargo.get("recipient_name", "Не указан")),
                "recipient_phone": cargo.get("recipient_phone", "Не указан"),
                "recipient_address": cargo.get("recipient_address", "Не указан"),
                "status": cargo.get("status", "unknown"),
                "route": cargo.get("route", "unknown"),
                "collection": collection_name,
                "can_be_placed": cargo.get("status") == CargoStatus.ARRIVED_DESTINATION
            })
    
    return {
        "transport": {
            "id": transport["id"],
            "transport_number": transport["transport_number"],
            "driver_name": transport["driver_name"],
            "direction": transport["direction"],
            "arrived_at": transport.get("arrived_at"),
            "status": transport["status"]
        },
        "cargo_list": cargo_details,
        "total_weight": sum(c["weight"] for c in cargo_details),
        "cargo_count": len(cargo_details),
        "placeable_cargo_count": len([c for c in cargo_details if c["can_be_placed"]])
    }

@app.post("/api/transport/{transport_id}/place-cargo-to-warehouse")
async def place_cargo_from_transport_to_warehouse(
    transport_id: str,
    placement: dict,
    current_user: User = Depends(get_current_user)
):
    """Разместить груз из прибывшего транспорта на склад"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    if transport["status"] != TransportStatus.ARRIVED:
        raise HTTPException(status_code=400, detail="Transport must be arrived to place cargo")
    
    cargo_id = placement.get("cargo_id")
    warehouse_id = placement.get("warehouse_id")
    block_number = placement.get("block_number")
    shelf_number = placement.get("shelf_number")
    cell_number = placement.get("cell_number")
    
    if not all([cargo_id, warehouse_id, block_number, shelf_number, cell_number]):
        raise HTTPException(status_code=400, detail="Missing required placement data")
    
    # Проверить, что груз на этом транспорте
    if cargo_id not in transport.get("cargo_list", []):
        raise HTTPException(status_code=400, detail="Cargo is not on this transport")
    
    # Найти груз в обеих коллекциях
    cargo = db.cargo.find_one({"id": cargo_id})
    collection_name = "cargo"
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        collection_name = "operator_cargo"
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    if cargo.get("status") != CargoStatus.ARRIVED_DESTINATION:
        raise HTTPException(status_code=400, detail="Cargo must be in arrived_destination status to place")
    
    # Найти склад
    warehouse = db.warehouses.find_one({"id": warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Проверить валидность ячейки
    if (block_number > warehouse.get("blocks_count", 0) or 
        shelf_number > warehouse.get("shelves_per_block", 0) or 
        cell_number > warehouse.get("cells_per_shelf", 0)):
        raise HTTPException(status_code=400, detail="Invalid cell coordinates")
    
    # Проверить доступность ячейки
    location_code = f"{block_number}-{shelf_number}-{cell_number}"
    existing_cell = db.warehouse_cells.find_one({
        "warehouse_id": warehouse_id,
        "location_code": location_code
    })
    
    if existing_cell and existing_cell.get("is_occupied", False):
        raise HTTPException(status_code=400, detail=f"Cell {location_code} is already occupied")
    
    # Проверить права оператора на склад (если не админ)
    if current_user.role == UserRole.WAREHOUSE_OPERATOR:
        if not check_operator_warehouse_binding(current_user.id, warehouse_id):
            raise HTTPException(status_code=403, detail="Operator not bound to this warehouse")
    
    # Разместить груз в ячейке
    if existing_cell:
        # Обновить существующую ячейку
        db.warehouse_cells.update_one(
            {"_id": existing_cell["_id"]},
            {"$set": {
                "is_occupied": True,
                "cargo_id": cargo_id,
                "placed_at": datetime.utcnow(),
                "placed_by": current_user.id,
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        # Создать новую ячейку
        db.warehouse_cells.insert_one({
            "warehouse_id": warehouse_id,
            "location_code": location_code,
            "block_number": block_number,
            "shelf_number": shelf_number,
            "cell_number": cell_number,
            "is_occupied": True,
            "cargo_id": cargo_id,
            "placed_at": datetime.utcnow(),
            "placed_by": current_user.id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    # Обновить груз
    collection = db[collection_name]
    collection.update_one(
        {"id": cargo_id},
        {"$set": {
            "status": CargoStatus.IN_WAREHOUSE,
            "warehouse_id": warehouse_id,
            "warehouse_location": warehouse.get("name"),
            "block_number": block_number,
            "shelf_number": shelf_number,
            "cell_number": cell_number,
            "placed_by_operator": current_user.full_name,
            "placed_by_operator_id": current_user.id,
            "placed_at": datetime.utcnow(),
            "transport_id": None,  # Убираем связь с транспортом
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Удалить груз из списка транспорта
    updated_cargo_list = [cid for cid in transport.get("cargo_list", []) if cid != cargo_id]
    new_load = max(0, transport.get("current_load_kg", 0) - cargo.get("weight", 0))
    
    # Обновить транспорт
    new_status = TransportStatus.COMPLETED if len(updated_cargo_list) == 0 else TransportStatus.ARRIVED
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "cargo_list": updated_cargo_list,
            "current_load_kg": new_load,
            "status": new_status,
            "completed_at": datetime.utcnow() if new_status == TransportStatus.COMPLETED else None,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Создать уведомления
    if collection_name == "cargo":
        create_personal_notification(
            cargo["sender_id"], 
            "Груз размещен на складе", 
            f"Ваш груз №{cargo['cargo_number']} размещен на складе {warehouse.get('name')} в ячейке Б{block_number}-П{shelf_number}-Я{cell_number}",
            "cargo",
            cargo_id
        )
    
    create_system_notification(
        "Груз размещен из транспорта",
        f"Груз №{cargo['cargo_number']} размещен из транспорта {transport['transport_number']} на склад {warehouse.get('name')} в ячейку {location_code}",
        "cargo",
        cargo_id,
        None,
        current_user.id
    )
    
    return {
        "message": f"Cargo {cargo['cargo_number']} successfully placed in warehouse",
        "cargo_number": cargo["cargo_number"],
        "warehouse_name": warehouse.get("name"),
        "location": f"Б{block_number}-П{shelf_number}-Я{cell_number}",
        "transport_status": new_status,
        "remaining_cargo": len(updated_cargo_list)
    }

@app.post("/api/transport/{transport_id}/place-cargo-by-number")
async def place_cargo_from_transport_by_number(
    transport_id: str,
    placement_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Разместить груз из транспорта по номеру/QR коду с автоматическим выбором склада, но ручным выбором ячейки"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    if transport["status"] != TransportStatus.ARRIVED:
        raise HTTPException(status_code=400, detail="Transport must be arrived to place cargo")
    
    cargo_number = placement_data.get("cargo_number", "").strip()
    qr_data = placement_data.get("qr_data", "").strip()
    
    # Получение данных ячейки: может быть QR ячейки или координаты ячейки
    cell_qr_data = placement_data.get("cell_qr_data", "").strip()
    block_number = placement_data.get("block_number")
    shelf_number = placement_data.get("shelf_number")
    cell_number = placement_data.get("cell_number")
    
    # Определить номер груза из QR кода или использовать прямой номер
    if qr_data and "ГРУЗ №" in qr_data:
        try:
            cargo_number = qr_data.split("ГРУЗ №")[1].split("\n")[0].strip()
        except:
            raise HTTPException(status_code=400, detail="Invalid cargo QR code format")
    
    if not cargo_number:
        raise HTTPException(status_code=400, detail="Cargo number or QR data required")
    
    # Найти груз по номеру в обеих коллекциях
    cargo = db.cargo.find_one({"cargo_number": cargo_number})
    collection_name = "cargo"
    if not cargo:
        cargo = db.operator_cargo.find_one({"cargo_number": cargo_number})
        collection_name = "operator_cargo"
    
    if not cargo:
        raise HTTPException(status_code=404, detail=f"Cargo {cargo_number} not found")
    
    # Проверить, что груз на этом транспорте
    if cargo["id"] not in transport.get("cargo_list", []):
        raise HTTPException(status_code=400, detail=f"Cargo {cargo_number} is not on this transport")
    
    if cargo.get("status") != CargoStatus.ARRIVED_DESTINATION:
        raise HTTPException(status_code=400, detail="Cargo must be in arrived_destination status to place")
    
    # Автоматический выбор склада на основе привязки оператора
    available_warehouse_ids = []
    
    if current_user.role == UserRole.ADMIN:
        # Админ может размещать на любые склады
        warehouses = list(db.warehouses.find({}))
        available_warehouse_ids = [w["id"] for w in warehouses]
    else:
        # Оператор может размещать только на привязанные склады
        bindings = list(db.operator_warehouse_bindings.find({"operator_id": current_user.id}))
        available_warehouse_ids = [b["warehouse_id"] for b in bindings]
    
    if not available_warehouse_ids:
        raise HTTPException(status_code=403, detail="No available warehouses for placement")
    
    # Выбираем первый доступный склад (автоматически)
    selected_warehouse_id = available_warehouse_ids[0]
    warehouse = db.warehouses.find_one({"id": selected_warehouse_id})
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Selected warehouse not found")
    
    # Определить ячейку из QR кода ячейки или из координат
    if cell_qr_data and "ЯЧЕЙКА СКЛАДА" in cell_qr_data:
        # Парсим QR код ячейки
        try:
            lines = cell_qr_data.split("\n")
            location_line = [line for line in lines if "Местоположение:" in line][0]
            location = location_line.split("Местоположение: ")[1].strip()
            
            # Извлекаем блок, полку, ячейку из локации (например: "Склад-А-Б1-П2-Я5")
            parts = location.split("-")
            if len(parts) >= 3:
                block_number = int(parts[-3][1:])  # Убираем "Б"
                shelf_number = int(parts[-2][1:])  # Убираем "П" 
                cell_number = int(parts[-1][1:])   # Убираем "Я"
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid cell QR code format")
    
    # Проверить, что координаты ячейки указаны
    if not all([block_number, shelf_number, cell_number]):
        raise HTTPException(status_code=400, detail="Cell coordinates (block, shelf, cell) or cell QR code required")
    
    # Проверить валидность ячейки
    if (block_number > warehouse.get("blocks_count", 0) or 
        shelf_number > warehouse.get("shelves_per_block", 0) or 
        cell_number > warehouse.get("cells_per_shelf", 0)):
        raise HTTPException(status_code=400, detail="Invalid cell coordinates")
    
    # Проверить доступность ячейки
    location_code = f"{block_number}-{shelf_number}-{cell_number}"
    existing_cell = db.warehouse_cells.find_one({
        "warehouse_id": selected_warehouse_id,
        "location_code": location_code
    })
    
    if existing_cell and existing_cell.get("is_occupied", False):
        raise HTTPException(status_code=400, detail=f"Cell {location_code} is already occupied")
    
    # Размещение груза в указанную ячейку
    if existing_cell:
        # Обновить существующую ячейку
        db.warehouse_cells.update_one(
            {"_id": existing_cell["_id"]},
            {"$set": {
                "is_occupied": True,
                "cargo_id": cargo["id"],
                "placed_at": datetime.utcnow(),
                "placed_by": current_user.id,
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        # Создать новую ячейку
        db.warehouse_cells.insert_one({
            "warehouse_id": selected_warehouse_id,
            "location_code": location_code,
            "block_number": block_number,
            "shelf_number": shelf_number,
            "cell_number": cell_number,
            "is_occupied": True,
            "cargo_id": cargo["id"],
            "placed_at": datetime.utcnow(),
            "placed_by": current_user.id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    # Обновить груз
    collection = db[collection_name]
    collection.update_one(
        {"id": cargo["id"]},
        {"$set": {
            "status": CargoStatus.IN_WAREHOUSE,
            "warehouse_id": selected_warehouse_id,
            "warehouse_location": warehouse.get("name"),
            "block_number": block_number,
            "shelf_number": shelf_number,
            "cell_number": cell_number,
            "placed_by_operator": current_user.full_name,
            "placed_by_operator_id": current_user.id,
            "placed_at": datetime.utcnow(),
            "transport_id": None,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Удалить груз из списка транспорта
    updated_cargo_list = [cid for cid in transport.get("cargo_list", []) if cid != cargo["id"]]
    new_load = max(0, transport.get("current_load_kg", 0) - cargo.get("weight", 0))
    
    # Обновить транспорт
    new_status = TransportStatus.COMPLETED if len(updated_cargo_list) == 0 else TransportStatus.ARRIVED
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "cargo_list": updated_cargo_list,
            "current_load_kg": new_load,
            "status": new_status,
            "completed_at": datetime.utcnow() if new_status == TransportStatus.COMPLETED else None,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Создать уведомления
    if collection_name == "cargo":
        create_personal_notification(
            cargo["sender_id"], 
            "Груз размещен на складе", 
            f"Ваш груз №{cargo['cargo_number']} размещен на складе {warehouse.get('name')} в ячейке Б{block_number}-П{shelf_number}-Я{cell_number}",
            "cargo",
            cargo["id"]
        )
    
    create_system_notification(
        "Груз размещен",
        f"Груз №{cargo['cargo_number']} размещен на складе {warehouse.get('name')} в ячейку {location_code}. Склад выбран автоматически, ячейка - {'по QR коду' if cell_qr_data else 'вручную'}",
        "cargo",
        cargo["id"],
        None,
        current_user.id
    )
    
    return {
        "message": f"Cargo {cargo['cargo_number']} successfully placed",
        "cargo_number": cargo["cargo_number"],
        "warehouse_name": warehouse.get("name"),
        "warehouse_auto_selected": True,
        "location": f"Б{block_number}-П{shelf_number}-Я{cell_number}",
        "placement_method": "cell_qr" if cell_qr_data else ("qr_number" if qr_data else "number_manual"),
        "transport_status": new_status,
        "remaining_cargo": len(updated_cargo_list)
    }

@app.delete("/api/transport/{transport_id}/remove-cargo/{cargo_id}")
async def remove_cargo_from_transport(
    transport_id: str,
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удалить груз с транспорта и вернуть его в исходное место на складе"""
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти транспорт
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    # Проверить, что транспорт не в пути
    if transport["status"] == TransportStatus.IN_TRANSIT:
        raise HTTPException(status_code=400, detail="Cannot remove cargo from transport in transit")
    
    # Найти груз в обеих коллекциях
    cargo = db.cargo.find_one({"id": cargo_id})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        collection_name = "operator_cargo"
    else:
        collection_name = "cargo"
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверить, что груз действительно на этом транспорте
    if cargo_id not in transport.get("cargo_list", []):
        raise HTTPException(status_code=400, detail="Cargo is not on this transport")
    
    # Получить вес груза для пересчета загрузки транспорта
    cargo_weight = cargo.get("weight", 0)
    
    # Удалить груз из списка транспорта
    updated_cargo_list = [cid for cid in transport.get("cargo_list", []) if cid != cargo_id]
    new_load = max(0, transport.get("current_load_kg", 0) - cargo_weight)
    
    # Обновить транспорт
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "cargo_list": updated_cargo_list,
            "current_load_kg": new_load,
            "status": TransportStatus.EMPTY if new_load == 0 else transport["status"],
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Если у груза было место на складе, вернуть его туда
    if cargo.get("warehouse_id") and cargo.get("block_number") and cargo.get("shelf_number") and cargo.get("cell_number"):
        # Найти ячейку на складе
        location_code = f"{cargo['block_number']}-{cargo['shelf_number']}-{cargo['cell_number']}"
        warehouse_cell = db.warehouse_cells.find_one({
            "warehouse_id": cargo["warehouse_id"],
            "location_code": location_code
        })
        
        if warehouse_cell and not warehouse_cell.get("is_occupied", False):
            # Вернуть груз в ячейку
            db.warehouse_cells.update_one(
                {"_id": warehouse_cell["_id"]},
                {"$set": {
                    "is_occupied": True,
                    "cargo_id": cargo_id,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # Обновить статус груза
            collection = db[collection_name]
            collection.update_one(
                {"id": cargo_id},
                {"$set": {
                    "status": CargoStatus.ACCEPTED,
                    "transport_id": None,
                    "updated_at": datetime.utcnow(),
                    "returned_by_operator": current_user.full_name,
                    "returned_by_operator_id": current_user.id
                }}
            )
            
            # Создать уведомление
            sender_id = cargo.get("sender_id") or cargo.get("created_by")
            if sender_id:
                create_notification(
                    sender_id, 
                    f"Груз №{cargo['cargo_number']} был возвращен на склад в исходную ячейку",
                    cargo_id
                )
            
            return {
                "message": f"Cargo {cargo['cargo_number']} successfully returned to warehouse cell {location_code}",
                "location": location_code,
                "warehouse_id": cargo["warehouse_id"]
            }
        else:
            # Ячейка занята или не найдена, просто вернуть статус на принят
            collection = db[collection_name]
            collection.update_one(
                {"id": cargo_id},
                {"$set": {
                    "status": CargoStatus.ACCEPTED,
                    "transport_id": None,
                    "warehouse_id": None,
                    "warehouse_location": None,
                    "block_number": None,
                    "shelf_number": None,
                    "cell_number": None,
                    "updated_at": datetime.utcnow(),
                    "returned_by_operator": current_user.full_name,
                    "returned_by_operator_id": current_user.id
                }}
            )
            
            # Создать уведомление
            sender_id = cargo.get("sender_id") or cargo.get("created_by")
            if sender_id:
                create_notification(
                    sender_id, 
                    f"Ваш груз №{cargo['cargo_number']} был снят с транспорта и ожидает размещения",
                    cargo_id
                )
            
            return {
                "message": f"Cargo {cargo['cargo_number']} removed from transport. Original location unavailable, cargo status set to ACCEPTED",
                "status": "accepted"
            }
    else:
        # Груз не имел места на складе, просто снять с транспорта
        collection = db[collection_name]
        collection.update_one(
            {"id": cargo_id},
            {"$set": {
                "status": CargoStatus.ACCEPTED,
                "transport_id": None,
                "updated_at": datetime.utcnow(),
                "returned_by_operator": current_user.full_name,
                "returned_by_operator_id": current_user.id
            }}
        )
        
        # Создать уведомление
        sender_id = cargo.get("sender_id") or cargo.get("created_by")
        if sender_id:
            create_notification(
                sender_id, 
                f"Ваш груз №{cargo['cargo_number']} был снят с транспорта",
                cargo_id
            )
        
        return {
            "message": f"Cargo {cargo['cargo_number']} removed from transport",
            "status": "accepted"
        }

@app.delete("/api/transport/{transport_id}")
async def delete_transport(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    # Проверка доступа
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    # Проверить, что транспорт можно удалить (не в пути)
    if transport["status"] == TransportStatus.IN_TRANSIT:
        raise HTTPException(status_code=400, detail="Cannot delete transport that is in transit")
    
    # Если есть грузы, освободить их
    if transport.get("cargo_list"):
        for cargo_id in transport["cargo_list"]:
            db.cargo.update_one(
                {"id": cargo_id},
                {"$set": {
                    "status": "accepted",  # Вернуть на склад
                    "updated_at": datetime.utcnow()
                }, "$unset": {"transport_id": ""}}
            )
    
    # Переместить транспорт в историю
    transport_history = {
        **transport,
        "deleted_at": datetime.utcnow(),
        "deleted_by": current_user.id
    }
    db.transport_history.insert_one(transport_history)
    
    # Удалить транспорт из активных
    db.transports.delete_one({"id": transport_id})
    
    return {"message": "Transport deleted and moved to history"}

# === ГЕНЕРАЦИЯ QR КОДОВ ДЛЯ ТРАНСПОРТА ===

@app.post("/api/transport/{transport_id}/generate-qr")
async def generate_transport_qr_code(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    """Генерация QR кода для транспорта любого статуса"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получить данные транспорта
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    # Убираем проверку статуса - теперь можно генерировать для любого транспорта
    # Генерировать уникальный числовой QR код для транспорта
    transport_number = transport.get("transport_number", "N/A")
    transport_counter = transport.get("sequence_number", 1)
    
    # Создать числовой QR код: ТТТТПППССС
    # ТТТТ - номер транспорта (первые 4 цифры)
    # ППП - порядковый номер (3 цифры)  
    # ССС - случайный суффикс для уникальности (3 цифры)
    
    # Извлекаем числа из номера транспорта
    transport_digits = ''.join(filter(str.isdigit, str(transport_number)))
    if len(transport_digits) < 4:
        transport_digits = transport_digits.ljust(4, '0')
    else:
        transport_digits = transport_digits[:4]
    
    # Порядковый номер (от 1 до 999)
    sequence = str(transport_counter).zfill(3)
    
    # Случайный суффикс для уникальности
    import random
    suffix = str(random.randint(100, 999))
    
    # Итоговый числовой код
    numeric_qr_code = f"{transport_digits}{sequence}{suffix}"
    
    # Создать QR код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(numeric_qr_code)
    qr.make(fit=True)

    # Создать изображение QR кода
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Конвертировать в base64
    buffered = BytesIO()
    qr_image.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{qr_base64}"
    
    # Обновить транспорт с информацией о QR коде
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "qr_code": qr_code_url,
            "qr_data": numeric_qr_code,
            "qr_generated_at": datetime.utcnow(),
            "qr_generated_by": current_user.id
        }}
    )
    
    return {
        "success": True,
        "transport_id": transport_id,
        "transport_number": transport_number,
        "qr_code": qr_code_url,
        "qr_data": numeric_qr_code,
        "message": f"QR код для транспорта {transport_number} успешно сгенерирован"
    }

@app.post("/api/transport/{transport_id}/set-filled")
async def set_transport_filled_for_testing(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    """ТЕСТОВАЯ ФУНКЦИЯ: Принудительно установить транспорт как заполненный для тестирования QR кодов"""
    if current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can use this testing function")
    
    # Получить данные транспорта
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    # Обновить статус на filled
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "status": TransportStatus.FILLED,
            "current_load_kg": transport["capacity_kg"] * 0.95,  # 95% загрузки
            "updated_at": datetime.utcnow(),
            "updated_by": current_user.id
        }}
    )
    
    return {
        "success": True,
        "transport_id": transport_id,
        "message": f"Транспорт {transport.get('transport_number', 'N/A')} установлен как заполненный для тестирования"
    }

# === ГЕНЕРАЦИЯ QR КОДОВ ДЛЯ ГРУЗОВ ===

@app.post("/api/cargo/{cargo_id}/generate-qr")
async def generate_cargo_qr_code(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Генерация QR кода для груза для размещения на транспорт"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получить данные груза из обеих коллекций
    cargo = db.cargo.find_one({"id": cargo_id})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверить, что груз доступен для размещения на транспорт
    valid_statuses = ["accepted", "placed_in_warehouse", "awaiting_placement"]
    if cargo.get("status") not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"QR код можно генерировать только для грузов со статусом: {', '.join(valid_statuses)}"
        )
    
    # Генерировать уникальный числовой QR код для груза
    cargo_number = cargo.get("cargo_number", "N/A")
    cargo_weight = cargo.get("weight", 0)
    
    # Создать числовой QR код: ГГГГВВВССС
    # ГГГГ - номер груза (первые 4 цифры)
    # ВВВ - вес в кг (3 цифры, без десятичных)
    # ССС - случайный суффикс для уникальности (3 цифры)
    
    # Извлекаем числа из номера груза
    cargo_digits = ''.join(filter(str.isdigit, str(cargo_number)))
    if len(cargo_digits) < 4:
        cargo_digits = cargo_digits.ljust(4, '0')
    else:
        cargo_digits = cargo_digits[:4]
    
    # Вес (округляем до целого числа и берем последние 3 цифры)
    weight_int = int(float(cargo_weight)) if cargo_weight else 0
    weight_str = str(weight_int).zfill(3)[-3:]  # Последние 3 цифры, дополненные нулями
    
    # Случайный суффикс для уникальности
    import random
    suffix = str(random.randint(100, 999))
    
    # Итоговый числовой код
    numeric_qr_code = f"{cargo_digits}{weight_str}{suffix}"
    
    # Создать QR код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(numeric_qr_code)
    qr.make(fit=True)

    # Создать изображение QR кода
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Конвертировать в base64
    buffered = BytesIO()
    qr_image.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{qr_base64}"
    
    # Обновить груз с информацией о QR коде
    db.cargo.update_one(
        {"id": cargo_id},
        {"$set": {
            "qr_code": qr_code_url,
            "qr_data": numeric_qr_code,
            "qr_generated_at": datetime.utcnow(),
            "qr_generated_by": current_user.id
        }}
    )
    
    return {
        "success": True,
        "cargo_id": cargo_id,
        "cargo_number": cargo_number,
        "qr_code": qr_code_url,
        "qr_data": numeric_qr_code,
        "message": f"QR код для груза {cargo_number} успешно сгенерирован"
    }

@app.post("/api/cargo/batch-generate-qr")
async def batch_generate_cargo_qr_codes(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Массовая генерация QR кодов для нескольких грузов"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    cargo_ids = request.get("cargo_ids", [])
    if not cargo_ids:
        raise HTTPException(status_code=400, detail="Список ID грузов не предоставлен")
    
    results = []
    errors = []
    
    for cargo_id in cargo_ids:
        try:
            # Генерируем QR код для каждого груза
            cargo = db.cargo.find_one({"id": cargo_id})
            if not cargo:
                errors.append(f"Груз {cargo_id} не найден")
                continue
            
            # Используем ту же логику генерации что и в одиночном endpoint
            cargo_number = cargo.get("cargo_number", "N/A")
            cargo_weight = cargo.get("weight", 0)
            
            # Создать числовой QR код: ГГГГВВВССС
            cargo_digits = ''.join(filter(str.isdigit, str(cargo_number)))
            if len(cargo_digits) < 4:
                cargo_digits = cargo_digits.ljust(4, '0')
            else:
                cargo_digits = cargo_digits[:4]
            
            weight_int = int(float(cargo_weight)) if cargo_weight else 0
            weight_str = str(weight_int).zfill(3)[-3:]
            
            import random
            suffix = str(random.randint(100, 999))
            numeric_qr_code = f"{cargo_digits}{weight_str}{suffix}"
            
            # Создать QR код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(numeric_qr_code)
            qr.make(fit=True)

            qr_image = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            qr_image.save(buffered, format="PNG")
            qr_base64 = base64.b64encode(buffered.getvalue()).decode()
            qr_code_url = f"data:image/png;base64,{qr_base64}"
            
            # Обновить груз
            db.cargo.update_one(
                {"id": cargo_id},
                {"$set": {
                    "qr_code": qr_code_url,
                    "qr_data": numeric_qr_code,
                    "qr_generated_at": datetime.utcnow(),
                    "qr_generated_by": current_user.id
                }}
            )
            
            results.append({
                "cargo_id": cargo_id,
                "cargo_number": cargo_number,
                "qr_data": numeric_qr_code,
                "success": True
            })
            
        except Exception as e:
            errors.append(f"Ошибка для груза {cargo_id}: {str(e)}")
    
    return {
        "success": True,
        "generated_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
        "message": f"Успешно сгенерировано QR кодов: {len(results)}, ошибок: {len(errors)}"
    }

# === РАЗМЕЩЕНИЕ ГРУЗОВ НА ТРАНСПОРТ ЧЕРЕЗ QR-КОДЫ ===

@app.post("/api/placement/scan-transport-qr")
async def scan_transport_qr_for_placement(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Сканирование QR кода транспорта для размещения грузов"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    qr_data = request.get("qr_data", "").strip()
    if not qr_data:
        raise HTTPException(status_code=400, detail="QR данные не предоставлены")
    
    # Поиск транспорта по QR коду
    transport = db.transports.find_one({"qr_data": qr_data})
    if not transport:
        raise HTTPException(status_code=404, detail="Транспорт с таким QR кодом не найден")
    
    return {
        "success": True,
        "transport": {
            "id": transport["id"],
            "transport_number": transport["transport_number"],
            "driver_name": transport["driver_name"],
            "driver_phone": transport["driver_phone"],
            "direction": transport["direction"],
            "capacity_kg": transport["capacity_kg"],
            "current_load_kg": transport.get("current_load_kg", 0),
            "status": transport["status"],
            "cargo_list": transport.get("cargo_list", [])
        },
        "message": f"Транспорт {transport['transport_number']} найден и готов к размещению грузов"
    }

@app.post("/api/placement/scan-cargo-qr")
async def scan_cargo_qr_for_placement(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Сканирование QR кода груза для размещения на транспорт - поддержка любых форматов"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    qr_data = request.get("qr_data", "").strip()
    if not qr_data:
        raise HTTPException(status_code=400, detail="QR данные не предоставлены")
    
    # Поиск груза по QR коду в обеих коллекциях - улучшенная логика
    cargo = None
    search_attempts = []
    
    # 1. Точное совпадение по qr_data в cargo
    cargo = db.cargo.find_one({"qr_data": qr_data})
    search_attempts.append(f"cargo.qr_data={qr_data}: {'найден' if cargo else 'не найден'}")
    
    # 2. Точное совпадение по qr_data в operator_cargo
    if not cargo:
        cargo = db.operator_cargo.find_one({"qr_data": qr_data})
        search_attempts.append(f"operator_cargo.qr_data={qr_data}: {'найден' if cargo else 'не найден'}")
    
    # 3. Поиск по cargo_number в cargo
    if not cargo:
        cargo = db.cargo.find_one({"cargo_number": qr_data})
        search_attempts.append(f"cargo.cargo_number={qr_data}: {'найден' if cargo else 'не найден'}")
    
    # 4. Поиск по cargo_number в operator_cargo  
    if not cargo:
        cargo = db.operator_cargo.find_one({"cargo_number": qr_data})
        search_attempts.append(f"operator_cargo.cargo_number={qr_data}: {'найден' if cargo else 'не найден'}")
        
    # 5. Поиск по cargo_number с regex в cargo (подстроки)
    if not cargo:
        cargo = db.cargo.find_one({"cargo_number": {"$regex": qr_data, "$options": "i"}})
        search_attempts.append(f"cargo.cargo_number regex {qr_data}: {'найден' if cargo else 'не найден'}")
        
    # 6. Поиск по cargo_number с regex в operator_cargo (подстроки)
    if not cargo:
        cargo = db.operator_cargo.find_one({"cargo_number": {"$regex": qr_data, "$options": "i"}})
        search_attempts.append(f"operator_cargo.cargo_number regex {qr_data}: {'найден' if cargo else 'не найден'}")
    
    # 7. Поиск среди всех грузов с qr_data (отладка)
    if not cargo:
        # Найдем все грузы с qr_data чтобы понять что есть в базе
        all_cargo_with_qr = list(db.cargo.find({"qr_data": {"$exists": True, "$ne": None}}, {"cargo_number": 1, "qr_data": 1, "warehouse_location": 1}).limit(5))
        all_operator_cargo_with_qr = list(db.operator_cargo.find({"qr_data": {"$exists": True, "$ne": None}}, {"cargo_number": 1, "qr_data": 1, "warehouse_location": 1}).limit(5))
        
        search_attempts.append(f"Найдено грузов cargo с QR: {len(all_cargo_with_qr)}")
        search_attempts.append(f"Найдено грузов operator_cargo с QR: {len(all_operator_cargo_with_qr)}")
        
        # Показать примеры для отладки
        for i, cargo_ex in enumerate(all_cargo_with_qr[:3]):
            search_attempts.append(f"  cargo[{i}]: {cargo_ex.get('cargo_number')} -> QR: {cargo_ex.get('qr_data')} -> Ячейка: {cargo_ex.get('warehouse_location')}")
            
        for i, op_cargo_ex in enumerate(all_operator_cargo_with_qr[:3]):
            search_attempts.append(f"  operator_cargo[{i}]: {op_cargo_ex.get('cargo_number')} -> QR: {op_cargo_ex.get('qr_data')} -> Ячейка: {op_cargo_ex.get('warehouse_location')}")
    
    if not cargo:
        error_message = f"Груз с QR кодом '{qr_data}' не найден.\n\nПопытки поиска:\n" + "\n".join(search_attempts)
        raise HTTPException(status_code=404, detail=error_message)
    
    # Проверить, что груз доступен для размещения (находится в ячейке склада)
    warehouse_location = cargo.get("warehouse_location")
    if not warehouse_location:
        raise HTTPException(
            status_code=400, 
            detail=f"Груз {cargo.get('cargo_number', 'неизвестен')} не находится в ячейке склада.\nТекущее расположение: {warehouse_location}\nДля размещения на транспорт груз должен быть в ячейке склада."
        )
    
    if cargo.get("transport_id"):
        raise HTTPException(
            status_code=400, 
            detail=f"Груз {cargo.get('cargo_number', 'неизвестен')} уже размещен на транспорт {cargo.get('transport_id')}"
        )
    
    return {
        "success": True,
        "cargo": {
            "id": cargo["id"],
            "cargo_number": cargo["cargo_number"],
            "cargo_name": cargo.get("cargo_name", ""),
            "weight": cargo.get("weight", 0),
            "sender_full_name": cargo.get("sender_full_name", ""),
            "recipient_full_name": cargo.get("recipient_full_name", ""),
            "warehouse_location": cargo.get("warehouse_location", ""),
            "status": cargo.get("status", ""),
            "qr_data": cargo.get("qr_data", qr_data)
        },
        "search_info": search_attempts,
        "message": f"Груз {cargo['cargo_number']} найден в ячейке {warehouse_location} и готов к размещению"
    }

@app.post("/api/placement/place-cargo-on-transport")
async def place_cargo_on_transport_via_qr(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """Размещение груза на транспорт через QR-коды"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transport_id = request.get("transport_id", "").strip()
    cargo_id = request.get("cargo_id", "").strip()
    
    if not transport_id or not cargo_id:
        raise HTTPException(status_code=400, detail="ID транспорта и груза обязательны")
    
    # Получить данные транспорта
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Транспорт не найден")
    
    # Получить данные груза
    cargo = db.cargo.find_one({"id": cargo_id})
    cargo_collection = "cargo"
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        cargo_collection = "operator_cargo"
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Груз не найден")
    
    # Проверки
    if cargo.get("transport_id"):
        raise HTTPException(status_code=400, detail="Груз уже размещен на транспорт")
    
    if not cargo.get("warehouse_location"):
        raise HTTPException(status_code=400, detail="Груз не находится в ячейке склада")
    
    # Проверить грузоподъемность
    cargo_weight = float(cargo.get("weight", 0))
    current_load = float(transport.get("current_load_kg", 0))
    capacity = float(transport.get("capacity_kg", 0))
    
    if current_load + cargo_weight > capacity:
        raise HTTPException(
            status_code=400, 
            detail=f"Превышение грузоподъемности: {current_load + cargo_weight} кг > {capacity} кг"
        )
    
    # Размещение груза на транспорт
    cargo_list = transport.get("cargo_list", [])
    placed_at = datetime.utcnow()
    cargo_list.append({
        "cargo_id": cargo_id,
        "cargo_number": cargo["cargo_number"],
        "weight": cargo_weight,
        "placed_at": placed_at.isoformat(),  # Конвертируем в строку для JSON
        "placed_by": current_user.id,
        "operator_name": current_user.full_name
    })
    
    new_load = current_load + cargo_weight
    new_status = TransportStatus.FILLED if new_load >= capacity * 0.9 else TransportStatus.EMPTY
    
    # Обновить транспорт
    db.transports.update_one(
        {"id": transport_id},
        {"$set": {
            "cargo_list": cargo_list,
            "current_load_kg": new_load,
            "status": new_status,
            "updated_at": datetime.utcnow(),
            "updated_by": current_user.id
        }}
    )
    
    # Обновить груз - убрать из ячейки и назначить на транспорт
    cargo_update = {
        "transport_id": transport_id,
        "warehouse_location": None,  # Убираем из ячейки
        "placed_on_transport_at": datetime.utcnow(),
        "placed_by": current_user.id,
        "status": "placed_on_transport",
        "updated_at": datetime.utcnow()
    }
    
    if cargo_collection == "cargo":
        db.cargo.update_one({"id": cargo_id}, {"$set": cargo_update})
    else:
        db.operator_cargo.update_one({"id": cargo_id}, {"$set": cargo_update})
    
    # Логирование операции размещения
    placement_log_id = str(uuid.uuid4())
    placement_log = {
        "id": placement_log_id,
        "transport_id": transport_id,
        "transport_number": transport["transport_number"],
        "cargo_id": cargo_id,
        "cargo_number": cargo["cargo_number"],
        "cargo_weight": cargo_weight,
        "operator_id": current_user.id,
        "operator_name": current_user.full_name,
        "placed_at": placed_at,  # Используем ту же дату
        "warehouse_location_removed": cargo.get("warehouse_location", ""),
        "operation_type": "qr_placement"
    }
    
    db.placement_logs.insert_one(placement_log)
    
    # Создаем простой объект для возврата
    placement_log_response = {
        "id": placement_log_id,
        "operator_name": current_user.full_name,
        "placed_at": placed_at.isoformat(),
        "operation_type": "qr_placement"
    }
    
    return {
        "success": True,
        "transport": {
            "id": transport_id,
            "transport_number": transport["transport_number"],
            "current_load_kg": new_load,
            "capacity_kg": capacity,
            "status": new_status.value if hasattr(new_status, 'value') else str(new_status),
            "cargo_count": len(cargo_list)
        },
        "cargo": {
            "id": cargo_id,
            "cargo_number": cargo["cargo_number"],
            "weight": cargo_weight,
            "warehouse_location_removed": cargo.get("warehouse_location", "")
        },
        "placement_log": placement_log_response,
        "message": f"Груз {cargo['cargo_number']} успешно размещен на транспорт {transport['transport_number']}"
    }

@app.get("/api/placement/transport-cargo/{transport_id}")
async def get_transport_cargo_for_placement(
    transport_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить список грузов размещенных на транспорт через QR-размещение"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получить данные транспорта
    transport = db.transports.find_one({"id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Транспорт не найден")
    
    # Получить логи размещения для этого транспорта
    placement_logs_raw = list(db.placement_logs.find(
        {"transport_id": transport_id},
        sort=[("placed_at", -1)]
    ))
    
    # Конвертируем логи в JSON-сериализуемый формат
    placement_logs = []
    for log in placement_logs_raw:
        log_item = {
            "id": log.get("id"),
            "cargo_id": log.get("cargo_id"),
            "cargo_number": log.get("cargo_number"),
            "operation_type": log.get("operation_type"),
            "operator_name": log.get("operator_name"),
            "warehouse_location_removed": log.get("warehouse_location_removed"),
            "placed_at": log.get("placed_at").isoformat() if log.get("placed_at") else None
        }
        placement_logs.append(log_item)
    
    cargo_list = transport.get("cargo_list", [])
    
    return {
        "success": True,
        "transport": {
            "id": transport_id,
            "transport_number": transport["transport_number"],
            "current_load_kg": transport.get("current_load_kg", 0),
            "capacity_kg": transport.get("capacity_kg", 0),
            "status": transport.get("status", ""),
            "cargo_count": len(cargo_list)
        },
        "cargo_list": cargo_list,
        "placement_logs": placement_logs,
        "message": f"Данные о размещении грузов на транспорт {transport['transport_number']}"
    }

@app.post("/api/placement/create-test-cargo-for-qr")
async def create_test_cargo_for_qr_placement(
    current_user: User = Depends(get_current_user)
):
    """ТЕСТОВАЯ ФУНКЦИЯ: Создать тестовый груз с QR кодом и размещением в ячейке"""
    if current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can use this testing function")
    
    # Создать тестовый груз
    cargo_number = f"TEST{datetime.now().strftime('%H%M%S')}"
    cargo_id = str(uuid.uuid4())
    
    # Генерировать числовой QR код
    cargo_digits = ''.join(filter(str.isdigit, cargo_number))
    if len(cargo_digits) < 4:
        cargo_digits = cargo_digits.ljust(4, '0')
    else:
        cargo_digits = cargo_digits[:4]
    
    weight_str = "010"  # 10 кг
    
    import random
    suffix = str(random.randint(100, 999))
    numeric_qr_code = f"{cargo_digits}{weight_str}{suffix}"
    
    # Создать QR код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(numeric_qr_code)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    qr_image.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{qr_base64}"
    
    cargo = {
        "id": cargo_id,
        "cargo_number": cargo_number,
        "cargo_name": "Тестовый груз для QR размещения",
        "weight": 10.0,
        "sender_full_name": "Тестовый Отправитель",
        "recipient_full_name": "Тестовый Получатель",
        "sender_phone": "+79991234567",
        "recipient_phone": "+79997654321",
        "status": "accepted",
        "warehouse_location": "Б01-П02-Я03",  # Размещен в ячейке
        "qr_code": qr_code_url,
        "qr_data": numeric_qr_code,
        "created_at": datetime.utcnow(),
        "created_by": current_user.id,
        "qr_generated_at": datetime.utcnow(),
        "qr_generated_by": current_user.id
    }
    
    # Сохранить в operator_cargo коллекцию
    db.operator_cargo.insert_one(cargo)
    
    return {
        "success": True,
        "cargo": {
            "id": cargo_id,
            "cargo_number": cargo_number,
            "qr_data": numeric_qr_code,
            "warehouse_location": "Б01-П02-Я03",
            "weight": 10.0
        },
        "message": f"Тестовый груз {cargo_number} создан с QR кодом {numeric_qr_code}"
    }

@app.post("/api/placement/create-test-cargo-with-warehouse")
async def create_test_cargo_with_warehouse_location(
    current_user: User = Depends(get_current_user)
):
    """ТЕСТОВАЯ ФУНКЦИЯ: Создать тестовый груз с QR кодом, размещенный в ячейке склада"""
    if current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can use this testing function")
    
    # Создать тестовый груз
    timestamp = datetime.now().strftime('%H%M%S')
    cargo_number = f"TEST{timestamp}"
    cargo_id = str(uuid.uuid4())
    
    # Генерировать числовой QR код
    cargo_digits = ''.join(filter(str.isdigit, cargo_number))[-4:]  # Последние 4 цифры из timestamp
    if len(cargo_digits) < 4:
        cargo_digits = cargo_digits.ljust(4, '0')
    
    weight_str = "015"  # 15 кг
    
    import random
    suffix = str(random.randint(100, 999))
    numeric_qr_code = f"{cargo_digits}{weight_str}{suffix}"
    
    # Создать QR код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(numeric_qr_code)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    qr_image.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{qr_base64}"
    
    # Создать случайную ячейку склада
    block = random.randint(1, 5)
    shelf = random.randint(1, 10)
    cell = random.randint(1, 20)
    warehouse_location = f"Б{block:02d}-П{shelf:02d}-Я{cell:02d}"
    
    cargo = {
        "id": cargo_id,
        "cargo_number": cargo_number,
        "cargo_name": "Тестовый груз для QR размещения на транспорт",
        "weight": 15.0,
        "sender_full_name": "Тестовый Отправитель QR",
        "recipient_full_name": "Тестовый Получатель QR",
        "sender_phone": "+79991234567",
        "recipient_phone": "+79997654321",
        "status": "placed_in_warehouse",
        "warehouse_location": warehouse_location,  # ВАЖНО: размещен в ячейке
        "qr_code": qr_code_url,
        "qr_data": numeric_qr_code,
        "created_at": datetime.utcnow(),
        "created_by": current_user.id,
        "qr_generated_at": datetime.utcnow(),
        "qr_generated_by": current_user.id,
        "placed_in_warehouse_at": datetime.utcnow(),
        "placed_in_warehouse_by": current_user.id
    }
    
    # Сохранить в operator_cargo коллекцию
    db.operator_cargo.insert_one(cargo)
    
    return {
        "success": True,
        "cargo": {
            "id": cargo_id,
            "cargo_number": cargo_number,
            "qr_data": numeric_qr_code,
            "warehouse_location": warehouse_location,
            "weight": 15.0,
            "status": "placed_in_warehouse"
        },
        "message": f"Тестовый груз {cargo_number} создан с QR кодом {numeric_qr_code} и размещен в ячейке {warehouse_location}"
    }

# === УПРАВЛЕНИЕ ЯЧЕЙКАМИ СКЛАДА ===

@app.get("/api/warehouse/{warehouse_id}/cell/{location_code}/cargo")
async def get_cargo_in_cell(
    warehouse_id: str,
    location_code: str,
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о грузе в конкретной ячейке"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти ячейку
    cell = db.warehouse_cells.find_one({
        "warehouse_id": warehouse_id,
        "location_code": location_code,
        "is_occupied": True
    })
    
    if not cell or not cell.get("cargo_id"):
        raise HTTPException(status_code=404, detail="No cargo found in this cell")
    
    cargo_id = cell["cargo_id"]
    
    # Найти груз в обеих коллекциях, исключая MongoDB _id
    cargo = db.cargo.find_one({"id": cargo_id}, {"_id": 0})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id}, {"_id": 0})
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    return cargo

@app.post("/api/warehouse/cargo/{cargo_id}/move")
async def move_cargo_between_cells(
    cargo_id: str,
    new_location: dict,  # {"warehouse_id", "block_number", "shelf_number", "cell_number"}
    current_user: User = Depends(get_current_user)
):
    """Перемещение груза между ячейками"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти груз
    cargo = db.cargo.find_one({"id": cargo_id})
    collection = db.cargo
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        collection = db.operator_cargo
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверить новое местоположение
    new_warehouse_id = new_location["warehouse_id"]
    new_block = new_location["block_number"]
    new_shelf = new_location["shelf_number"] 
    new_cell = new_location["cell_number"]
    new_location_code = f"B{new_block}-S{new_shelf}-C{new_cell}"
    
    # Проверить, свободна ли новая ячейка
    existing_cell = db.warehouse_cells.find_one({
        "warehouse_id": new_warehouse_id,
        "location_code": new_location_code,
        "is_occupied": True
    })
    
    if existing_cell:
        raise HTTPException(status_code=400, detail="Target cell is already occupied")
    
    # Освободить старую ячейку
    if cargo.get("warehouse_id") and cargo.get("block_number"):
        old_location_code = f"B{cargo['block_number']}-S{cargo['shelf_number']}-C{cargo['cell_number']}"
        db.warehouse_cells.update_one(
            {
                "warehouse_id": cargo["warehouse_id"],
                "location_code": old_location_code,
                "cargo_id": cargo_id
            },
            {"$set": {
                "is_occupied": False,
                "updated_at": datetime.utcnow()
            }, "$unset": {"cargo_id": ""}}
        )
    
    # Занять новую ячейку
    db.warehouse_cells.update_one(
        {
            "warehouse_id": new_warehouse_id,
            "location_code": new_location_code
        },
        {
            "$set": {
                "warehouse_id": new_warehouse_id,
                "location_code": new_location_code,
                "block_number": new_block,
                "shelf_number": new_shelf,
                "cell_number": new_cell,
                "is_occupied": True,
                "cargo_id": cargo_id,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    # Получить название нового склада
    new_warehouse = db.warehouses.find_one({"id": new_warehouse_id})
    new_warehouse_name = new_warehouse["name"] if new_warehouse else "Неизвестный склад"
    
    # Обновить груз
    collection.update_one(
        {"id": cargo_id},
        {"$set": {
            "warehouse_location": f"{new_warehouse_name} - Блок {new_block}, Полка {new_shelf}, Ячейка {new_cell}",
            "warehouse_id": new_warehouse_id,
            "block_number": new_block,
            "shelf_number": new_shelf,
            "cell_number": new_cell,
            "updated_at": datetime.utcnow(),
            "placed_by_operator": current_user.full_name,
            "placed_by_operator_id": current_user.id
        }}
    )
    
    return {"message": "Cargo moved successfully", "new_location": new_location_code}

@app.delete("/api/warehouse/cargo/{cargo_id}/remove")
async def remove_cargo_from_cell(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удалить груз из ячейки (освободить ячейку)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти груз
    cargo = db.cargo.find_one({"id": cargo_id})
    collection = db.cargo
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        collection = db.operator_cargo
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Освободить ячейку
    if cargo.get("warehouse_id") and cargo.get("block_number"):
        location_code = f"B{cargo['block_number']}-S{cargo['shelf_number']}-C{cargo['cell_number']}"
        db.warehouse_cells.update_one(
            {
                "warehouse_id": cargo["warehouse_id"],
                "location_code": location_code,
                "cargo_id": cargo_id
            },
            {"$set": {
                "is_occupied": False,
                "updated_at": datetime.utcnow()
            }, "$unset": {"cargo_id": ""}}
        )
    
    # Обновить груз (убрать местоположение)
    collection.update_one(
        {"id": cargo_id},
        {"$set": {
            "status": "accepted",  # Вернуть в статус "принят"
            "updated_at": datetime.utcnow()
        }, "$unset": {
            "warehouse_location": "",
            "warehouse_id": "",
            "block_number": "",
            "shelf_number": "",
            "cell_number": ""
        }}
    )
    
    return {"message": "Cargo removed from cell successfully"}

@app.get("/api/cargo/{cargo_id}/details")
async def get_cargo_details(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить полную информацию о грузе"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти груз в обеих коллекциях, исключая MongoDB _id
    cargo = db.cargo.find_one({"id": cargo_id}, {"_id": 0})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id}, {"_id": 0})
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    return cargo

@app.put("/api/cargo/{cargo_id}/update")
async def update_cargo_details(
    cargo_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить информацию о грузе"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти груз в обеих коллекциях
    cargo = db.cargo.find_one({"id": cargo_id})
    collection = db.cargo
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": cargo_id})
        collection = db.operator_cargo
    
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Фильтровать разрешенные поля для обновления
    allowed_fields = [
        "cargo_name", "description", "weight", "declared_value",
        "sender_full_name", "sender_phone", "recipient_full_name", 
        "recipient_phone", "recipient_address", "status"
    ]
    
    filtered_update = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    if not filtered_update:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    # Добавить информацию об обновлении
    filtered_update["updated_at"] = datetime.utcnow()
    filtered_update["updated_by_operator"] = current_user.full_name
    filtered_update["updated_by_operator_id"] = current_user.id
    
    # Обновить груз
    collection.update_one(
        {"id": cargo_id},
        {"$set": filtered_update}
    )
    
    return {"message": "Cargo updated successfully"}

# === API ДЛЯ ТРЕКИНГА ГРУЗА КЛИЕНТАМИ И УВЕДОМЛЕНИЙ ===

@app.post("/api/cargo/tracking/create")
async def create_cargo_tracking(
    tracking_data: CargoTrackingCreate,
    current_user: User = Depends(get_current_user)
):
    """Создать трекинг код для груза"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти груз по номеру
    cargo = db.cargo.find_one({"cargo_number": tracking_data.cargo_number})
    if not cargo:
        cargo = db.operator_cargo.find_one({"cargo_number": tracking_data.cargo_number})
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверить существующий трекинг
    existing_tracking = db.cargo_tracking.find_one({"cargo_id": cargo["id"]})
    if existing_tracking:
        return {
            "message": "Tracking already exists",
            "tracking_code": existing_tracking["tracking_code"],
            "cargo_number": cargo["cargo_number"]
        }
    
    # Создать уникальный трекинг код
    tracking_code = f"TRK{cargo['cargo_number']}{str(uuid.uuid4())[-8:].upper()}"
    
    tracking_id = str(uuid.uuid4())
    tracking = {
        "id": tracking_id,
        "cargo_id": cargo["id"],
        "cargo_number": cargo["cargo_number"],
        "tracking_code": tracking_code,
        "client_phone": tracking_data.client_phone,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "access_count": 0
    }
    
    db.cargo_tracking.insert_one(tracking)
    
    # Добавить в историю груза
    add_cargo_history(
        cargo["id"],
        cargo["cargo_number"],
        "tracking_created",
        None,
        None,
        tracking_code,
        f"Создан трекинг код для клиента {tracking_data.client_phone}",
        current_user.id,
        current_user.full_name,
        current_user.role,
        {"tracking_code": tracking_code, "client_phone": tracking_data.client_phone}
    )
    
    return {
        "message": "Tracking created successfully",
        "tracking_code": tracking_code,
        "cargo_number": cargo["cargo_number"],
        "client_phone": tracking_data.client_phone
    }

@app.get("/api/debug/tracking/{tracking_code}")
async def debug_tracking(tracking_code: str):
    """Debug tracking lookup"""
    try:
        # Найти трекинг
        tracking = db.cargo_tracking.find_one({"tracking_code": tracking_code, "is_active": True})
        if not tracking:
            return {"error": "Tracking code not found", "tracking_code": tracking_code}
        
        # Попробовать найти груз в обеих коллекциях
        cargo_in_cargo = db.cargo.find_one({"id": tracking["cargo_id"]})
        cargo_in_operator = db.operator_cargo.find_one({"id": tracking["cargo_id"]})
        
        return {
            "tracking_code": tracking_code,
            "cargo_id": str(tracking["cargo_id"]),
            "cargo_number": str(tracking["cargo_number"]),
            "cargo_in_cargo_collection": cargo_in_cargo is not None,
            "cargo_in_operator_collection": cargo_in_operator is not None,
            "cargo_found": (cargo_in_cargo is not None) or (cargo_in_operator is not None)
        }
    except Exception as e:
        return {"error": f"Exception: {str(e)}", "tracking_code": tracking_code}

@app.get("/api/cargo/track/{tracking_code}")
async def track_cargo_by_code(tracking_code: str):
    """Публичный трекинг груза по коду (без авторизации)"""
    try:
        # Найти трекинг
        tracking = db.cargo_tracking.find_one({"tracking_code": tracking_code, "is_active": True})
        if not tracking:
            raise HTTPException(status_code=404, detail="Tracking code not found")
        
        # Найти груз
        cargo = db.cargo.find_one({"id": tracking["cargo_id"]})
        if not cargo:
            cargo = db.operator_cargo.find_one({"id": tracking["cargo_id"]})
            if not cargo:
                raise HTTPException(status_code=404, detail="Cargo not found")
        
        # Обновить счетчик доступа
        db.cargo_tracking.update_one(
            {"id": tracking["id"]},
            {"$set": {"last_accessed": datetime.utcnow()}, "$inc": {"access_count": 1}}
        )
        
        # Получить информацию о складе и транспорте
        warehouse_info = None
        if cargo.get("warehouse_id"):
            warehouse = db.warehouses.find_one({"id": cargo["warehouse_id"]})
            if warehouse:
                warehouse_info = {
                    "name": warehouse["name"],
                    "location": warehouse["location"]
                }
        
        transport_info = None
        if cargo.get("transport_id"):
            transport = db.transports.find_one({"id": cargo["transport_id"]})
            if transport:
                transport_info = {
                    "transport_number": transport["transport_number"],
                    "driver_name": transport["driver_name"],
                    "direction": transport["direction"],
                    "status": transport["status"]
                }
        
        # Получить последние записи истории (публичные только)
        recent_history = list(db.cargo_history.find(
            {"cargo_id": cargo["id"], "action_type": {"$in": ["created", "status_changed", "placed_on_transport", "dispatched", "arrived"]}},
            {"_id": 0, "action_type": 1, "description": 1, "change_date": 1}
        ).sort("change_date", -1).limit(10))
        
        # Serialize all MongoDB documents to avoid ObjectId issues
        serialized_cargo = serialize_mongo_document(cargo)
        serialized_warehouse_info = serialize_mongo_document(warehouse_info) if warehouse_info else None
        serialized_transport_info = serialize_mongo_document(transport_info) if transport_info else None
        recent_history = serialize_mongo_document(recent_history)
        
        return {
            "tracking_code": tracking_code,
            "cargo_number": serialized_cargo["cargo_number"],
            "cargo_name": serialized_cargo.get("cargo_name", "Груз"),
            "status": serialized_cargo["status"],
            "weight": serialized_cargo.get("weight", 0),
            "created_at": serialized_cargo["created_at"],
            "sender_full_name": serialized_cargo.get("sender_full_name", "Не указан"),
            "recipient_full_name": serialized_cargo.get("recipient_full_name", serialized_cargo.get("recipient_name", "Не указан")),
            "recipient_address": serialized_cargo.get("recipient_address", ""),
            "current_location": {
                "warehouse": serialized_warehouse_info,
                "transport": serialized_transport_info,
                "description": _get_location_description(serialized_cargo)
            },
            "recent_history": recent_history,
            "last_updated": serialized_cargo.get("updated_at", serialized_cargo["created_at"])
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log other exceptions and return a generic error
        print(f"Error in track_cargo_by_code: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/notifications/client/send")
async def send_client_notification(
    notification_data: ClientNotificationCreate,
    current_user: User = Depends(get_current_user)
):
    """Отправить уведомление клиенту"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Найти груз
    cargo = db.cargo.find_one({"id": notification_data.cargo_id})
    if not cargo:
        cargo = db.operator_cargo.find_one({"id": notification_data.cargo_id})
        if not cargo:
            raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Создать уведомление
    notification_id = str(uuid.uuid4())
    notification = {
        "id": notification_id,
        "cargo_id": notification_data.cargo_id,
        "cargo_number": cargo["cargo_number"],
        "client_phone": notification_data.client_phone,
        "notification_type": notification_data.notification_type,
        "message_text": notification_data.message_text,
        "status": "pending",
        "created_by": current_user.id,
        "created_at": datetime.utcnow()
    }
    
    db.client_notifications.insert_one(notification)
    
    # Здесь будет интеграция с SMS/Email/WhatsApp сервисами
    # Пока что помечаем как отправленное
    db.client_notifications.update_one(
        {"id": notification_id},
        {"$set": {"status": "sent", "sent_at": datetime.utcnow()}}
    )
    
    # Добавить в историю груза
    add_cargo_history(
        notification_data.cargo_id,
        cargo["cargo_number"],
        "client_notification_sent",
        None,
        None,
        notification_data.notification_type,
        f"Отправлено {notification_data.notification_type} уведомление клиенту {notification_data.client_phone}",
        current_user.id,
        current_user.full_name,
        current_user.role,
        {"notification_id": notification_id, "message_preview": notification_data.message_text[:50]}
    )
    
    return {
        "message": "Notification sent successfully",
        "notification_id": notification_id,
        "cargo_number": cargo["cargo_number"],
        "notification_type": notification_data.notification_type
    }

@app.post("/api/messages/internal/send")
async def send_internal_message(
    message_data: InternalMessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Отправить внутреннее сообщение другому оператору"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Проверить существование получателя
    recipient = db.users.find_one({"id": message_data.recipient_id})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    if recipient["role"] not in [UserRole.ADMIN.value, UserRole.WAREHOUSE_OPERATOR.value]:
        raise HTTPException(status_code=400, detail="Can only send messages to admins and operators")
    
    # Проверить груз если указан
    cargo_number = None
    if message_data.related_cargo_id:
        cargo = db.cargo.find_one({"id": message_data.related_cargo_id})
        if not cargo:
            cargo = db.operator_cargo.find_one({"id": message_data.related_cargo_id})
        if cargo:
            cargo_number = cargo["cargo_number"]
    
    # Создать сообщение
    message_id = str(uuid.uuid4())
    message = {
        "id": message_id,
        "sender_id": current_user.id,
        "sender_name": current_user.full_name,
        "recipient_id": message_data.recipient_id,
        "recipient_name": recipient["full_name"],
        "message_subject": message_data.message_subject,
        "message_text": message_data.message_text,
        "priority": message_data.priority,
        "related_cargo_id": message_data.related_cargo_id,
        "related_cargo_number": cargo_number,
        "is_read": False,
        "sent_at": datetime.utcnow()
    }
    
    db.internal_messages.insert_one(message)
    
    # Создать уведомление для получателя
    create_notification(
        message_data.recipient_id,
        f"Новое сообщение от {current_user.full_name}: {message_data.message_subject}",
        message_data.related_cargo_id
    )
    
    return {
        "message": "Internal message sent successfully",
        "message_id": message_id,
        "recipient_name": recipient["full_name"]
    }

@app.get("/api/messages/internal/inbox")
async def get_internal_messages_inbox(
    current_user: User = Depends(get_current_user)
):
    """Получить входящие внутренние сообщения"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = list(db.internal_messages.find(
        {"recipient_id": current_user.id},
        {"_id": 0}
    ).sort("sent_at", -1))
    
    unread_count = db.internal_messages.count_documents({
        "recipient_id": current_user.id,
        "is_read": False
    })
    
    return {
        "messages": messages,
        "total_messages": len(messages),
        "unread_count": unread_count
    }

@app.put("/api/messages/internal/{message_id}/read")
async def mark_internal_message_read(
    message_id: str,
    current_user: User = Depends(get_current_user)
):
    """Отметить внутреннее сообщение как прочитанное"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.internal_messages.update_one(
        {"id": message_id, "recipient_id": current_user.id},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message": "Message marked as read"}

# === API ДЛЯ ОФОРМЛЕНИЯ ГРУЗА КЛИЕНТАМИ ===

def calculate_delivery_cost(cargo_data: CargoOrderCreate) -> DeliveryCalculation:
    """Расчет стоимости доставки груза"""
    
    # Логика объявленной стоимости по умолчанию в зависимости от маршрута
    default_declared_values = {
        RouteType.MOSCOW_KHUJAND: 60.0,      # Москва → Худжанд: 60 рублей
        RouteType.MOSCOW_DUSHANBE: 80.0,     # Москва → Душанбе: 80 рублей  
        RouteType.MOSCOW_KULOB: 80.0,        # Москва → Кулоб: 80 рублей
        RouteType.MOSCOW_KURGANTYUBE: 80.0,  # Москва → Курган-Тюбе: 80 рублей
        RouteType.MOSCOW_TO_TAJIKISTAN: 80.0 # Общий маршрут: 80 рублей
    }
    
    # Если declared_value не указана или равна значению по умолчанию, используем значение маршрута
    final_declared_value = cargo_data.declared_value
    route_default = default_declared_values.get(cargo_data.route, 80.0)
    
    # Если пользователь не указал declared_value или указал значение по умолчанию маршрута,
    # используем стандартное значение маршрута
    if cargo_data.declared_value == route_default or cargo_data.declared_value <= route_default:
        final_declared_value = route_default
    
    # Базовые тарифы в рублях
    base_rates = {
        RouteType.MOSCOW_DUSHANBE: {"base": 2000, "per_kg": 150, "days": 7},
        RouteType.MOSCOW_KHUJAND: {"base": 1800, "per_kg": 140, "days": 8},
        RouteType.MOSCOW_KULOB: {"base": 2200, "per_kg": 160, "days": 9},
        RouteType.MOSCOW_KURGANTYUBE: {"base": 2100, "per_kg": 155, "days": 8}
    }
    
    route_info = base_rates.get(cargo_data.route, base_rates[RouteType.MOSCOW_DUSHANBE])
    
    # Базовая стоимость
    base_cost = route_info["base"]
    
    # Стоимость по весу
    weight_cost = cargo_data.weight * route_info["per_kg"]
    
    # Страхование (0.5% от объявленной стоимости, минимум 500 руб)
    insurance_cost = 0
    if cargo_data.insurance_requested and cargo_data.insurance_value:
        # Используем final_declared_value для расчета страхования
        insurance_value = cargo_data.insurance_value or final_declared_value
        insurance_cost = max(insurance_value * 0.005, 500)
    
    # Упаковка
    packaging_cost = 800 if cargo_data.packaging_service else 0
    
    # Забор на дому
    pickup_cost = 1500 if cargo_data.home_pickup else 0
    
    # Доставка на дом
    delivery_cost = 1200 if cargo_data.home_delivery else 0
    
    # Надбавка за срочность
    express_surcharge = 0
    delivery_days = route_info["days"]
    
    if cargo_data.delivery_type == "express":
        express_surcharge = (base_cost + weight_cost) * 0.5  # +50%
        delivery_days = max(delivery_days - 2, 3)  # На 2 дня быстрее, минимум 3 дня
    elif cargo_data.delivery_type == "economy":
        express_surcharge = -(base_cost + weight_cost) * 0.2  # -20%
        delivery_days += 3  # На 3 дня дольше
    
    # Надбавки за специальные требования
    special_surcharge = 0
    if cargo_data.fragile:
        special_surcharge += 500
    if cargo_data.temperature_sensitive:
        special_surcharge += 800
    
    total_cost = (
        base_cost + weight_cost + insurance_cost + packaging_cost + 
        pickup_cost + delivery_cost + express_surcharge + special_surcharge
    )
    
    return DeliveryCalculation(
        base_cost=base_cost,
        weight_cost=weight_cost,
        insurance_cost=insurance_cost,
        packaging_cost=packaging_cost,
        pickup_cost=pickup_cost,
        delivery_cost=delivery_cost,
        express_surcharge=express_surcharge,
        total_cost=round(total_cost, 2),
        delivery_time_days=delivery_days
    )

@app.post("/api/client/cargo/calculate")
async def calculate_cargo_cost(
    cargo_data: CargoOrderCreate,
    current_user: User = Depends(get_current_user)
):
    """Рассчитать стоимость доставки груза"""
    if current_user.role != UserRole.USER:
        raise HTTPException(status_code=403, detail="Access denied - Only for clients")
    
    try:
        calculation = calculate_delivery_cost(cargo_data)
        return {
            "calculation": calculation,
            "breakdown": {
                "Базовая стоимость": calculation.base_cost,
                "Стоимость по весу": f"{calculation.weight_cost} ({cargo_data.weight} кг)",
                "Страхование": calculation.insurance_cost if calculation.insurance_cost > 0 else "Не выбрано",
                "Упаковка": calculation.packaging_cost if calculation.packaging_cost > 0 else "Не выбрано",
                "Забор на дому": calculation.pickup_cost if calculation.pickup_cost > 0 else "Не выбрано",
                "Доставка на дом": calculation.delivery_cost if calculation.delivery_cost > 0 else "Не выбрано",
                "Надбавка за тип доставки": calculation.express_surcharge
            },
            "route_info": {
                "route": cargo_data.route,
                "delivery_type": cargo_data.delivery_type,
                "estimated_days": calculation.delivery_time_days
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error calculating cost: {str(e)}")

@app.post("/api/client/cargo/create")
async def create_cargo_order(
    cargo_data: CargoOrderCreate,
    current_user: User = Depends(get_current_user)
):
    """Создать заказ на груз клиентом"""
    if current_user.role != UserRole.USER:
        raise HTTPException(status_code=403, detail="Access denied - Only for clients")
    
    try:
        # Рассчитываем стоимость
        calculation = calculate_delivery_cost(cargo_data)
        
        # Получаем правильное значение объявленной стоимости по умолчанию
        default_declared_values = {
            RouteType.MOSCOW_KHUJAND: 60.0,      # Москва → Худжанд: 60 рублей
            RouteType.MOSCOW_DUSHANBE: 80.0,     # Москва → Душанбе: 80 рублей  
            RouteType.MOSCOW_KULOB: 80.0,        # Москва → Кулоб: 80 рублей
            RouteType.MOSCOW_KURGANTYUBE: 80.0,  # Москва → Курган-Тюбе: 80 рублей
            RouteType.MOSCOW_TO_TAJIKISTAN: 80.0 # Общий маршрут: 80 рублей
        }
        
        route_default = default_declared_values.get(cargo_data.route, 80.0)
        final_declared_value = cargo_data.declared_value
        
        # Если пользователь указал значение меньше или равное минимальному для маршрута, используем минимум
        if cargo_data.declared_value <= route_default:
            final_declared_value = route_default
        
        # Создаем груз
        cargo_id = str(uuid.uuid4())
        cargo_number = generate_cargo_number()
        
        cargo = {
            "id": cargo_id,
            "cargo_number": cargo_number,
            "cargo_name": cargo_data.cargo_name,
            "sender_full_name": current_user.full_name,
            "sender_phone": current_user.phone,
            "recipient_full_name": cargo_data.recipient_full_name,
            "recipient_phone": cargo_data.recipient_phone,
            "recipient_address": cargo_data.recipient_address,
            "recipient_city": cargo_data.recipient_city,
            "weight": cargo_data.weight,
            "declared_value": final_declared_value,  # Используем рассчитанное значение
            "description": cargo_data.description,
            "route": cargo_data.route,
            "status": CargoStatus.CREATED,
            "payment_status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.id,
            "created_by_operator": None,
            
            # Стоимость и услуги
            "total_cost": calculation.total_cost,
            "base_cost": calculation.base_cost,
            "estimated_delivery_days": calculation.delivery_time_days,
            "delivery_type": cargo_data.delivery_type,
            
            # Дополнительные услуги
            "insurance_requested": cargo_data.insurance_requested,
            "insurance_value": cargo_data.insurance_value,
            "insurance_cost": calculation.insurance_cost,
            "packaging_service": cargo_data.packaging_service,
            "packaging_cost": calculation.packaging_cost,
            "home_pickup": cargo_data.home_pickup,
            "pickup_cost": calculation.pickup_cost,
            "home_delivery": cargo_data.home_delivery,
            "delivery_cost": calculation.delivery_cost,
            
            # Специальные требования
            "fragile": cargo_data.fragile,
            "temperature_sensitive": cargo_data.temperature_sensitive,
            "special_instructions": cargo_data.special_instructions,
            
            # Статус обработки
            "order_type": "client_order",  # Отличаем от заявок
            "needs_operator_review": True
        }
        
        db.cargo.insert_one(cargo)
        
        # Создаем трекинг код автоматически
        tracking_code = f"TRK{cargo_number}{str(uuid.uuid4())[-8:].upper()}"
        
        tracking = {
            "id": str(uuid.uuid4()),
            "cargo_id": cargo_id,
            "cargo_number": cargo_number,
            "tracking_code": tracking_code,
            "client_phone": current_user.phone,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "access_count": 0
        }
        
        db.cargo_tracking.insert_one(tracking)
        
        # Добавляем в историю груза
        add_cargo_history(
            cargo_id,
            cargo_number,
            "created",
            None,
            None,
            "created",
            f"Груз оформлен клиентом {current_user.full_name}. Стоимость: {calculation.total_cost} руб.",
            current_user.id,
            current_user.full_name,
            "user",
            {
                "total_cost": calculation.total_cost,
                "delivery_type": cargo_data.delivery_type,
                "route": cargo_data.route,
                "tracking_code": tracking_code
            }
        )
        
        # Создаем уведомление для операторов
        create_system_notification(
            "Новый заказ от клиента",
            f"Клиент {current_user.full_name} оформил груз #{cargo_number}. Стоимость: {calculation.total_cost} руб. Требует проверки оператора.",
            "client_order",
            cargo_id,
            {
                "cargo_number": cargo_number,
                "client_name": current_user.full_name,
                "total_cost": calculation.total_cost,
                "route": cargo_data.route
            },
            None  # Для всех операторов
        )
        
        return CargoOrderResponse(
            cargo_id=cargo_id,
            cargo_number=cargo_number,
            total_cost=calculation.total_cost,
            estimated_delivery_days=calculation.delivery_time_days,
            status="created",
            payment_status="pending",
            tracking_code=tracking_code,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating cargo order: {str(e)}")

@app.get("/api/client/cargo/delivery-options") 
async def get_delivery_options(
    current_user: User = Depends(get_current_user)
):
    """Получить доступные опции доставки"""
    if current_user.role != UserRole.USER:
        raise HTTPException(status_code=403, detail="Access denied - Only for clients")
    
    return {
        "routes": [
            {"value": "moscow_dushanbe", "label": "Москва → Душанбе", "base_days": 7},
            {"value": "moscow_khujand", "label": "Москва → Худжанд", "base_days": 8},
            {"value": "moscow_kulob", "label": "Москва → Кулоб", "base_days": 9},
            {"value": "moscow_kurgantyube", "label": "Москва → Курган-Тюбе", "base_days": 8}
        ],
        "delivery_types": [
            {"value": "economy", "label": "Эконом (-20%)", "modifier": -0.2, "days_add": 3},
            {"value": "standard", "label": "Обычная", "modifier": 0, "days_add": 0},
            {"value": "express", "label": "Срочная (+50%)", "modifier": 0.5, "days_subtract": 2}
        ],
        "additional_services": [
            {"service": "insurance", "label": "Страхование", "description": "0.5% от стоимости, мин. 500 руб"},
            {"service": "packaging", "label": "Упаковка", "cost": 800, "description": "Профессиональная упаковка"},
            {"service": "home_pickup", "label": "Забор на дому", "cost": 1500, "description": "Заберем груз по вашему адресу"},
            {"service": "home_delivery", "label": "Доставка на дом", "cost": 1200, "description": "Доставим груз по адресу получателя"},
            {"service": "fragile", "label": "Хрупкий груз", "cost": 500, "description": "Особая осторожность при транспортировке"},
            {"service": "temperature", "label": "Температурный режим", "cost": 800, "description": "Контроль температуры"}
        ],
        "weight_limits": {
            "min": 0.1,
            "max": 10000,
            "unit": "кг"
        },
        "value_limits": {
            "min": 100,
            "max": 10000000,
            "unit": "руб"
        }
    }

# === API ДЛЯ КЛИЕНТСКОГО ЛИЧНОГО КАБИНЕТА (Функция 1) ===

@app.get("/api/client/dashboard")
async def get_client_dashboard(
    current_user: User = Depends(get_current_user)
):
    """Главная страница личного кабинета клиента"""
    # Только пользователи (клиенты) могут получать свой дашборд
    if current_user.role != UserRole.USER:
        raise HTTPException(status_code=403, detail="Access denied - Only for clients")
    
    # Получить грузы клиента
    user_cargo = list(db.cargo.find({"created_by": current_user.id}, {"_id": 0}).sort("created_at", -1))
    
    # Статистика по статусам
    status_stats = {}
    for status in ['accepted', 'placed_in_warehouse', 'on_transport', 'in_transit', 'arrived_destination', 'delivered']:
        count = len([cargo for cargo in user_cargo if cargo.get("status") == status])
        status_stats[status] = count
    
    # Последние 5 грузов
    recent_cargo = user_cargo[:5]
    
    # Unpaid cargo (ожидающие оплаты)
    unpaid_cargo = [cargo for cargo in user_cargo if cargo.get("payment_status") == "pending"]
    
    # Активные трекинг коды
    active_tracking = list(db.cargo_tracking.find({
        "client_phone": current_user.phone,
        "is_active": True
    }, {"_id": 0}))
    
    return {
        "client_info": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "member_since": current_user.created_at
        },
        "cargo_summary": {
            "total_cargo": len(user_cargo),
            "status_breakdown": status_stats,
            "unpaid_cargo_count": len(unpaid_cargo),
            "active_tracking_codes": len(active_tracking)
        },
        "recent_cargo": serialize_mongo_document(recent_cargo),
        "unpaid_cargo": serialize_mongo_document(unpaid_cargo),
        "active_tracking": active_tracking
    }

@app.get("/api/client/cargo")
async def get_client_cargo(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Получить все грузы клиента с фильтрацией"""
    # Только пользователи (клиенты) могут получать свои грузы
    if current_user.role != UserRole.USER:
        raise HTTPException(status_code=403, detail="Access denied - Only for clients")
    
    query = {"created_by": current_user.id}
    if status and status != "all":
        query["status"] = status
    
    cargo_list = list(db.cargo.find(query, {"_id": 0}).sort("created_at", -1))
    
    # Обогащаем каждый груз дополнительной информацией
    enriched_cargo = []
    for cargo in cargo_list:
        # Информация о складе
        warehouse_info = None
        if cargo.get("warehouse_id"):
            warehouse = db.warehouses.find_one({"id": cargo["warehouse_id"]})
            if warehouse:
                warehouse_info = {
                    "name": warehouse["name"],
                    "location": warehouse["location"]
                }
        
        # Информация о транспорте
        transport_info = None
        if cargo.get("transport_id"):
            transport = db.transports.find_one({"id": cargo["transport_id"]})
            if transport:
                transport_info = {
                    "transport_number": transport["transport_number"],
                    "direction": transport["direction"],
                    "status": transport["status"]
                }
        
        # Трекинг код
        tracking = db.cargo_tracking.find_one({"cargo_id": cargo["id"]})
        tracking_code = tracking["tracking_code"] if tracking else None
        
        # Количество фото
        photo_count = db.cargo_photos.count_documents({"cargo_id": cargo["id"]})
        
        # Количество комментариев (только публичные)
        comment_count = db.cargo_comments.count_documents({
            "cargo_id": cargo["id"],
            "is_internal": False
        })
        
        enriched_cargo.append({
            **cargo,
            "warehouse_info": warehouse_info,
            "transport_info": transport_info,
            "tracking_code": tracking_code,
            "photo_count": photo_count,
            "comment_count": comment_count,
            "location_description": _get_location_description(cargo)
        })
    
    return {
        "cargo": serialize_mongo_document(enriched_cargo),
        "total_count": len(enriched_cargo),
        "filters": {
            "available_statuses": list(set([c.get("status", "unknown") for c in cargo_list])),
            "current_filter": status or "all"
        }
    }

@app.get("/api/client/cargo/{cargo_id}/details")
async def get_client_cargo_details(
    cargo_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить детальную информацию о грузе клиента"""
    # Только пользователи (клиенты) могут получать свои грузы
    if current_user.role != UserRole.USER:
        raise HTTPException(status_code=403, detail="Access denied - Only for clients")
    
    # Найти груз и убедиться что он принадлежит клиенту
    cargo = db.cargo.find_one({"id": cargo_id, "created_by": current_user.id})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Получить фото груза
    photos = list(db.cargo_photos.find(
        {"cargo_id": cargo_id},
        {"_id": 0, "photo_data": 0}  # Исключаем base64 данные для производительности
    ).sort("upload_date", -1))
    
    # Получить комментарии (только публичные)
    comments = list(db.cargo_comments.find(
        {"cargo_id": cargo_id, "is_internal": False},
        {"_id": 0}
    ).sort("created_at", -1))
    
    # Получить историю (только публичные события)
    public_history = list(db.cargo_history.find(
        {
            "cargo_id": cargo_id,
            "action_type": {"$in": ["created", "status_changed", "placed_on_transport", "dispatched", "arrived", "delivered"]}
        },
        {"_id": 0}
    ).sort("change_date", -1))
    
    # Трекинг информация
    tracking = db.cargo_tracking.find_one({"cargo_id": cargo_id})
    
    return {
        "cargo": serialize_mongo_document(cargo),
        "photos": serialize_mongo_document(photos),
        "comments": serialize_mongo_document(comments),
        "history": serialize_mongo_document(public_history),
        "tracking": serialize_mongo_document(tracking) if tracking else None,
        "available_actions": {
            "view_photos": len(photos) > 0,
            "track_cargo": tracking is not None,
            "contact_support": True,
            "request_info": True
        }
    }

@app.post("/api/admin/fix-operator-role")
async def fix_warehouse_operator_role(current_user: User = Depends(get_current_user)):
    """Временный эндпоинт для исправления роли оператора склада"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can fix operator roles")
    
    try:
        # Исправляем роль оператора +79777888999
        warehouse_operator = db.users.find_one({"phone": "+79777888999"})
        if warehouse_operator:
            # Обновляем роль и учетные данные
            update_result = db.users.update_one(
                {"phone": "+79777888999"},
                {"$set": {
                    "role": UserRole.WAREHOUSE_OPERATOR.value,
                    "password_hash": hash_password("warehouse123"),
                    "token_version": 1,
                    "user_number": warehouse_operator.get("user_number") or generate_user_number(),
                    "full_name": "Оператор Складской Обновленный",
                    "is_active": True
                }}
            )
            
            if update_result.modified_count > 0:
                return {"message": "Роль оператора успешно исправлена", "fixed": True}
            else:
                return {"message": "Оператор уже имеет корректные настройки", "fixed": False}
        else:
            # Создаем нового оператора
            operator_id = str(uuid.uuid4())
            operator_user_number = generate_user_number()
            db.users.insert_one({
                "id": operator_id,
                "user_number": operator_user_number,
                "full_name": "Оператор Складской Обновленный",
                "phone": "+79777888999",
                "password_hash": hash_password("warehouse123"),
                "role": UserRole.WAREHOUSE_OPERATOR.value,
                "is_active": True,
                "token_version": 1,
                "created_at": datetime.utcnow()
            })
            return {"message": "Новый оператор склада создан", "created": True}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка исправления роли: {str(e)}")

# ===== НОВЫЕ ENDPOINTS УПРАВЛЕНИЯ ЯЧЕЙКАМИ СКЛАДА =====

@app.get("/api/warehouses/{warehouse_id}/cells")
async def get_warehouse_cells(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить список всех ячеек склада"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        cells = []
        blocks_count = warehouse.get("blocks_count", 0)
        shelves_per_block = warehouse.get("shelves_per_block", 0)
        cells_per_shelf = warehouse.get("cells_per_shelf", 0)
        
        for block in range(1, blocks_count + 1):
            for shelf in range(1, shelves_per_block + 1):
                for cell in range(1, cells_per_shelf + 1):
                    cell_location = f"Б{block}-П{shelf}-Я{cell}"
                    
                    # Проверяем занятость ячейки
                    is_occupied = db.operator_cargo.find_one({
                        "warehouse_id": warehouse_id,
                        "block_number": block,
                        "shelf_number": shelf, 
                        "cell_number": cell,
                        "processing_status": {"$in": ["placed_in_warehouse", "awaiting_delivery"]}
                    }) is not None
                    
                    cells.append({
                        "id": f"{warehouse_id}-{block}-{shelf}-{cell}",
                        "warehouse_id": warehouse_id,
                        "block_number": block,
                        "shelf_number": shelf,
                        "cell_number": cell,
                        "location": cell_location,
                        "is_occupied": is_occupied
                    })
        
        return {"cells": cells}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouse cells: {str(e)}")

@app.put("/api/warehouses/{warehouse_id}/structure")
async def update_warehouse_structure(
    warehouse_id: str,
    structure_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить структуру склада (количество блоков, полок, ячеек)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        blocks_count = structure_data.get("blocks_count")
        shelves_per_block = structure_data.get("shelves_per_block")
        cells_per_shelf = structure_data.get("cells_per_shelf")
        
        if not all([blocks_count, shelves_per_block, cells_per_shelf]):
            raise HTTPException(status_code=400, detail="All structure fields are required")
        
        if blocks_count <= 0 or shelves_per_block <= 0 or cells_per_shelf <= 0:
            raise HTTPException(status_code=400, detail="All structure values must be positive")
        
        # Обновляем структуру склада
        db.warehouses.update_one(
            {"id": warehouse_id},
            {
                "$set": {
                    "blocks_count": blocks_count,
                    "shelves_per_block": shelves_per_block,
                    "cells_per_shelf": cells_per_shelf,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "message": "Warehouse structure updated successfully",
            "warehouse_id": warehouse_id,
            "new_structure": {
                "blocks_count": blocks_count,
                "shelves_per_block": shelves_per_block,
                "cells_per_shelf": cells_per_shelf,
                "total_cells": blocks_count * shelves_per_block * cells_per_shelf
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating warehouse structure: {str(e)}")

@app.get("/api/warehouses/cells/{cell_id}/qr")
async def generate_cell_qr(
    cell_id: str,
    current_user: User = Depends(get_current_user)
):
    """Генерировать QR код для отдельной ячейки"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Извлекаем информацию о ячейке из ID (формат: warehouse_uuid-block-shelf-cell)
        parts = cell_id.split("-")
        if len(parts) < 4:
            raise HTTPException(status_code=400, detail="Invalid cell ID format")
        
        # UUID склада может содержать дефисы, поэтому берем последние 3 части как block-shelf-cell
        block = parts[-3]
        shelf = parts[-2] 
        cell = parts[-1]
        warehouse_id = "-".join(parts[:-3])  # Восстанавливаем UUID склада
        
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        # Получаем номер склада для QR кода (используем порядковый номер или warehouse_number)
        warehouse_number = warehouse.get("warehouse_number", 1)
        if isinstance(warehouse_number, str):
            try:
                warehouse_number = int(warehouse_number)
            except ValueError:
                warehouse_number = 1
        
        # Создаем числовой QR код в формате: номер_склада номер_блока номер_полки номер_ячейки (без пробелов)
        qr_code_data = f"{warehouse_number:02d}{int(block):02d}{int(shelf):02d}{int(cell):02d}"
        
        # Генерируем QR код с числовыми данными
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_code_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Конвертируем в base64
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_code_data_url = f"data:image/png;base64,{qr_code_base64}"
        
        cell_location = f"Б{block}-П{shelf}-Я{cell}"
        
        return {
            "cell_id": cell_id,
            "cell_location": cell_location,
            "warehouse_name": warehouse.get("name", ""),
            "warehouse_number": warehouse_number,
            "qr_code": qr_code_data_url,
            "qr_data": qr_code_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cell QR code: {str(e)}")

@app.get("/api/warehouses/{warehouse_id}/cells/qr-batch")
async def generate_all_cells_qr(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Генерировать QR коды для всех ячеек склада"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        blocks_count = warehouse.get("blocks_count", 0)
        shelves_per_block = warehouse.get("shelves_per_block", 0)
        cells_per_shelf = warehouse.get("cells_per_shelf", 0)
        
        if not all([blocks_count, shelves_per_block, cells_per_shelf]):
            raise HTTPException(status_code=400, detail="Warehouse structure not defined")
        
        # Получаем номер склада для QR кода
        warehouse_number = warehouse.get("warehouse_number", 1)
        if isinstance(warehouse_number, str):
            try:
                warehouse_number = int(warehouse_number)
            except ValueError:
                warehouse_number = 1
        
        qr_codes = []
        
        for block in range(1, blocks_count + 1):
            for shelf in range(1, shelves_per_block + 1):
                for cell in range(1, cells_per_shelf + 1):
                    cell_location = f"Б{block}-П{shelf}-Я{cell}"
                    
                    # Создаем числовой QR код в формате: номер_склада номер_блока номер_полки номер_ячейки (без пробелов)
                    qr_code_data = f"{warehouse_number:02d}{block:02d}{shelf:02d}{cell:02d}"
                    
                    # Генерируем QR код с числовыми данными
                    qr = qrcode.QRCode(version=1, box_size=10, border=5)
                    qr.add_data(qr_code_data)
                    qr.make(fit=True)
                    
                    img = qr.make_image(fill_color="black", back_color="white")
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    buffer.seek(0)
                    
                    # Конвертируем в base64
                    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
                    qr_code_data_url = f"data:image/png;base64,{qr_code_base64}"
                    
                    qr_codes.append({
                        "cell_location": cell_location,
                        "qr_code": qr_code_data_url,
                        "qr_data": qr_code_data
                    })
        
        return {
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse.get("name", ""),
            "total_cells": len(qr_codes),
            "qr_codes": qr_codes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating batch QR codes: {str(e)}")

@app.post("/api/warehouses/{warehouse_id}/cells/batch-delete")
async def delete_cells_batch(
    warehouse_id: str,
    cell_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Удалить выбранные ячейки (освободить их от грузов)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        warehouse = db.warehouses.find_one({"id": warehouse_id})
        if not warehouse:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        cell_ids = cell_data.get("cell_ids", [])
        if not cell_ids:
            raise HTTPException(status_code=400, detail="No cell IDs provided")
        
        affected_cargo = []
        
        for cell_id in cell_ids:
            # Извлекаем информацию о ячейке из ID
            parts = cell_id.split("-")
            if len(parts) != 4:
                continue
                
            _, block, shelf, cell = parts
            
            # Ищем грузы в этой ячейке
            cargo_in_cell = list(db.operator_cargo.find({
                "warehouse_id": warehouse_id,
                "block_number": int(block),
                "shelf_number": int(shelf),
                "cell_number": int(cell),
                "processing_status": {"$in": ["placed_in_warehouse", "awaiting_delivery"]}
            }))
            
            for cargo in cargo_in_cell:
                # Переводим груз в статус "готов к размещению"
                db.operator_cargo.update_one(
                    {"id": cargo["id"]},
                    {
                        "$set": {
                            "processing_status": "awaiting_placement",
                            "block_number": None,
                            "shelf_number": None,
                            "cell_number": None,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                affected_cargo.append(cargo["cargo_number"])
        
        return {
            "message": f"Successfully cleared {len(cell_ids)} cells",
            "cleared_cells": len(cell_ids),
            "affected_cargo": affected_cargo,
            "affected_cargo_count": len(affected_cargo)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting cells: {str(e)}")

@app.post("/api/admin/warehouses/assign-numbers")
async def assign_warehouse_numbers(
    current_user: User = Depends(get_current_user)
):
    """Присвоить номера складам (только для администратора)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Получаем все склады без номеров
        warehouses = list(db.warehouses.find({"warehouse_number": {"$exists": False}}))
        
        for i, warehouse in enumerate(warehouses, start=1):
            db.warehouses.update_one(
                {"id": warehouse["id"]},
                {"$set": {"warehouse_number": i}}
            )
        
        return {
            "message": f"Assigned numbers to {len(warehouses)} warehouses",
            "updated_count": len(warehouses)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning warehouse numbers: {str(e)}")

# НОВЫЕ ENDPOINTS ДЛЯ КУРЬЕРСКОЙ СЛУЖБЫ (ЭТАП 1)

@app.post("/api/admin/couriers/create")
async def create_courier(
    courier_data: CourierCreate,
    current_user: User = Depends(get_current_user)
):
    """Создать нового курьера (админ или оператор)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем существование пользователя с таким телефоном
    if db.users.find_one({"phone": courier_data.phone}):
        raise HTTPException(status_code=400, detail="User with this phone already exists")
    
    # Проверяем что склад существует
    warehouse = db.warehouses.find_one({"id": courier_data.assigned_warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    try:
        # Создаем пользователя с ролью курьер
        user_id = str(uuid.uuid4())
        user_number = generate_user_number()
        courier_user = {
            "id": user_id,
            "user_number": user_number,
            "full_name": courier_data.full_name,
            "phone": courier_data.phone,
            "password_hash": hash_password(courier_data.password),
            "role": UserRole.COURIER.value,
            "address": courier_data.address,
            "is_active": True,
            "token_version": 1,
            "created_at": datetime.utcnow()
        }
        db.users.insert_one(courier_user)
        
        # Создаем профиль курьера
        courier_id = str(uuid.uuid4())
        courier_profile = {
            "id": courier_id,
            "user_id": user_id,
            "full_name": courier_data.full_name,
            "phone": courier_data.phone,
            "address": courier_data.address,
            "transport_type": courier_data.transport_type.value,
            "transport_number": courier_data.transport_number,
            "transport_capacity": courier_data.transport_capacity,
            "assigned_warehouse_id": courier_data.assigned_warehouse_id,
            "assigned_warehouse_name": warehouse["name"],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.id
        }
        db.couriers.insert_one(courier_profile)
        
        # Создаем уведомление
        create_notification(
            user_id=current_user.id,
            message=f"Курьер {courier_data.full_name} успешно создан и назначен на склад {warehouse['name']}",
            related_id=courier_id
        )
        
        return {
            "message": "Courier created successfully",
            "courier_id": courier_id,
            "user_id": user_id,
            "login_credentials": {
                "phone": courier_data.phone,
                "password": courier_data.password
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating courier: {str(e)}")

@app.get("/api/admin/couriers/list")
async def get_couriers_list(
    current_user: User = Depends(get_current_user),
    page: int = 1,
    per_page: int = 25,
    show_inactive: bool = False  # Новый параметр для показа неактивных курьеров
):
    """Получить список курьеров (админ/оператор)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Базовый фильтр - по умолчанию показываем только активных курьеров
        if show_inactive:
            # Показываем всех курьеров (только для админов)
            if current_user.role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="Only admins can view inactive couriers")
            active_filter = {}
        else:
            # Показываем только активных курьеров (не удаленных)
            active_filter = {
                "$and": [
                    {"$or": [{"is_active": {"$ne": False}}, {"is_active": {"$exists": False}}]},
                    {"$or": [{"deleted": {"$ne": True}}, {"deleted": {"$exists": False}}]}
                ]
            }
        
        # Для операторов - только курьеры их складов
        if current_user.role == UserRole.WAREHOUSE_OPERATOR:
            operator_warehouses = get_operator_warehouse_ids(current_user.id)
            if not operator_warehouses:
                return create_pagination_response([], 0, page, per_page)
            
            couriers_query = {
                "assigned_warehouse_id": {"$in": operator_warehouses},
                **active_filter
            }
        else:
            # Админы видят курьеров согласно фильтру активности
            couriers_query = active_filter
        
        # Получаем курьеров с пагинацией
        total_count = db.couriers.count_documents(couriers_query)
        skip = (page - 1) * per_page
        
        couriers = list(db.couriers.find(couriers_query, {"_id": 0})
                       .sort("created_at", -1)
                       .skip(skip)
                       .limit(per_page))
        
        return create_pagination_response(couriers, total_count, page, per_page)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching couriers: {str(e)}")

@app.get("/api/admin/couriers/locations")
async def get_all_couriers_locations(
    current_user: User = Depends(get_current_user)
):
    """Получить местоположения всех курьеров (для админов)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view all courier locations")
    
    try:
        # Получить все активные местоположения курьеров
        locations = list(db.courier_locations.find({}, {"_id": 0}))
        
        # Сортировать по времени последнего обновления
        locations.sort(key=lambda x: x.get('last_updated', datetime.min), reverse=True)
        
        # Добавить информацию о времени последнего обновления в читаемом формате
        for location in locations:
            last_updated = location.get('last_updated')
            if last_updated:
                time_diff = datetime.utcnow() - last_updated
                minutes_ago = int(time_diff.total_seconds() / 60)
                
                if minutes_ago < 1:
                    location['time_since_update'] = "только что"
                elif minutes_ago < 60:
                    location['time_since_update'] = f"{minutes_ago} мин назад"
                else:
                    hours_ago = int(minutes_ago / 60)
                    location['time_since_update'] = f"{hours_ago} ч назад"
            else:
                location['time_since_update'] = "неизвестно"
        
        return {
            "locations": locations,
            "total_count": len(locations),
            "active_couriers": len([l for l in locations if l.get('status') != 'offline']),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching courier locations: {str(e)}")

# НОВАЯ ФУНКЦИЯ: Получить список неактивных курьеров
@app.get("/api/admin/couriers/inactive")
async def get_inactive_couriers(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Access denied: Only admins")
    
    try:
        # Получаем неактивных курьеров
        inactive_couriers = list(db.couriers.find({"is_active": False}, {"_id": 0}))
        
        # Добавляем информацию о пользователе для каждого курьера
        for courier in inactive_couriers:
            user = db.users.find_one({"id": courier.get("user_id")}, {"_id": 0})
            if user:
                courier["user_info"] = {
                    "full_name": user.get("full_name", ""),
                    "phone": user.get("phone", ""),
                    "is_active": user.get("is_active", False)
                }
            
            # Добавляем информацию о складе
            warehouse = db.warehouses.find_one({"id": courier.get("assigned_warehouse_id")}, {"_id": 0})
            if warehouse:
                courier["assigned_warehouse_name"] = warehouse.get("name", "Неизвестный склад")
        
        return {
            "inactive_couriers": inactive_couriers,
            "total_count": len(inactive_couriers)
        }
        
    except Exception as e:
        print(f"Error getting inactive couriers: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении неактивных курьеров")

@app.get("/api/admin/couriers/{courier_id}")
async def get_courier_profile(
    courier_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить профиль курьера"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    courier = db.couriers.find_one({"id": courier_id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    # Получаем статистику курьера
    courier_requests = list(db.courier_requests.find(
        {"assigned_courier_id": courier_id}, {"_id": 0}
    ).sort("created_at", -1).limit(10))
    
    total_completed = db.courier_requests.count_documents({
        "assigned_courier_id": courier_id,
        "request_status": "completed"
    })
    
    total_assigned = db.courier_requests.count_documents({
        "assigned_courier_id": courier_id,
        "request_status": {"$in": ["assigned", "accepted"]}
    })
    
    courier["statistics"] = {
        "total_completed": total_completed,
        "total_assigned": total_assigned,
        "recent_requests": courier_requests
    }
    
    return courier

@app.put("/api/admin/couriers/{courier_id}")
async def update_courier_profile(
    courier_id: str,
    courier_update: CourierCreate,
    current_user: User = Depends(get_current_user)
):
    """Обновить профиль курьера"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    courier = db.couriers.find_one({"id": courier_id})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    # Проверяем новый склад
    warehouse = db.warehouses.find_one({"id": courier_update.assigned_warehouse_id})
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    try:
        # Обновляем профиль курьера
        update_data = {
            "full_name": courier_update.full_name,
            "phone": courier_update.phone,
            "address": courier_update.address,
            "transport_type": courier_update.transport_type.value,
            "transport_number": courier_update.transport_number,
            "transport_capacity": courier_update.transport_capacity,
            "assigned_warehouse_id": courier_update.assigned_warehouse_id,
            "assigned_warehouse_name": warehouse["name"],
            "updated_at": datetime.utcnow()
        }
        
        db.couriers.update_one({"id": courier_id}, {"$set": update_data})
        
        # Обновляем пользователя
        db.users.update_one(
            {"id": courier["user_id"]}, 
            {"$set": {
                "full_name": courier_update.full_name,
                "phone": courier_update.phone,
                "address": courier_update.address,
                "updated_at": datetime.utcnow()
            }}
        )
        
        return {"message": "Courier profile updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating courier: {str(e)}")

@app.delete("/api/admin/couriers/{courier_id}")
async def delete_courier(
    courier_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удалить курьера (только для админов)"""
    # БЕЗОПАСНОСТЬ: Только администраторы могут удалять курьеров
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can delete couriers")
    
    try:
        # Находим курьера
        courier = db.couriers.find_one({"id": courier_id})
        if not courier:
            raise HTTPException(status_code=404, detail="Courier not found")
        
        # Проверяем есть ли активные заявки у курьера
        active_requests = db.courier_requests.count_documents({
            "assigned_courier_id": courier_id,
            "status": {"$in": ["new", "accepted", "picked_up"]}
        })
        
        if active_requests > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Нельзя удалить курьера с активными заявками ({active_requests}). Завершите или отмените заявки сначала."
            )
        
        # Получаем информацию о курьере для логирования
        courier_name = courier.get("full_name", "Unknown")
        courier_phone = courier.get("phone", "Unknown")
        user_id = courier.get("user_id")
        
        # SOFT DELETE: Деактивируем курьера вместо физического удаления
        # Это сохраняет историю для аудита
        db.couriers.update_one(
            {"id": courier_id},
            {
                "$set": {
                    "is_active": False,
                    "deleted": True,
                    "deleted_at": datetime.utcnow(),
                    "deleted_by": current_user.id,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Деактивируем пользователя-курьера
        if user_id:
            db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "deleted": True,
                        "deleted_at": datetime.utcnow(),
                        "deleted_by": current_user.id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        # Логируем операцию удаления
        db.admin_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "courier_deleted",
            "admin_id": current_user.id,
            "admin_name": current_user.full_name,
            "target_courier_id": courier_id,
            "target_courier_name": courier_name,
            "target_courier_phone": courier_phone,
            "reason": "Админ удалил курьера через интерфейс",
            "created_at": datetime.utcnow()
        })
        
        return {
            "message": f"Курьер '{courier_name}' успешно удален",
            "courier_id": courier_id,
            "courier_name": courier_name,
            "deleted_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting courier: {str(e)}")

@app.post("/api/operator/courier-requests/create")
async def create_courier_request_for_pickup(
    cargo_id: str,
    assigned_courier_id: str,
    current_user: User = Depends(get_current_user)
):
    """Создать заявку курьеру для забора груза (оператор)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Проверяем груз
    cargo = db.operator_cargo.find_one({"id": cargo_id}, {"_id": 0})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    # Проверяем что груз требует забор
    if not cargo.get("pickup_required"):
        raise HTTPException(status_code=400, detail="Cargo does not require pickup")
    
    # Проверяем курьера
    courier = db.couriers.find_one({"id": assigned_courier_id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    try:
        # Обновляем статус груза и назначаем курьера
        db.operator_cargo.update_one(
            {"id": cargo_id},
            {"$set": {
                "status": CargoStatus.ASSIGNED_TO_COURIER,
                "assigned_courier_id": assigned_courier_id,
                "assigned_courier_name": courier["full_name"],
                "courier_request_status": "assigned",
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Обновляем существующую заявку курьера
        db.courier_requests.update_one(
            {"cargo_id": cargo_id},
            {"$set": {
                "assigned_courier_id": assigned_courier_id,
                "assigned_courier_name": courier["full_name"],
                "request_status": "assigned",
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Создаем уведомления
        create_notification(
            user_id=courier["user_id"],
            message=f"Вам назначена новая заявка на забор груза {cargo['cargo_number']} от {cargo['sender_full_name']}",
            related_id=cargo_id
        )
        
        create_notification(
            user_id=current_user.id,
            message=f"Заявка на забор груза {cargo['cargo_number']} назначена курьеру {courier['full_name']}",
            related_id=cargo_id
        )
        
        return {
            "message": "Courier request created and assigned successfully",
            "cargo_number": cargo["cargo_number"],
            "courier_name": courier["full_name"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating courier request: {str(e)}")

# ENDPOINTS ДЛЯ КУРЬЕРА

@app.get("/api/courier/requests/new")
async def get_courier_new_requests(
    current_user: User = Depends(get_current_user)
):
    """Получить новые заявки для курьера (включая заявки на забор груза)"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # ИСПРАВЛЕНИЕ: Получаем ТОЛЬКО НОВЫЕ заявки - неназначенные с статусом pending
    courier_requests = list(db.courier_requests.find({
        "assigned_courier_id": None, 
        "request_status": "pending"
    }, {"_id": 0}).sort("created_at", -1))
    
    # ИСПРАВЛЕНИЕ: Получаем ТОЛЬКО НОВЫЕ заявки на забор груза - неназначенные с статусом pending
    pickup_requests = list(db.courier_pickup_requests.find({
        "assigned_courier_id": None,
        "request_status": "pending"
    }, {"_id": 0}).sort("created_at", -1))
    
    # Добавляем тип заявки для различения в интерфейсе
    for request in courier_requests:
        request['request_type'] = 'delivery'  # Обычная доставка
        
    for request in pickup_requests:
        request['request_type'] = 'pickup'  # Забор груза
        # Добавляем поля совместимости для единообразного отображения
        request['cargo_name'] = request.get('destination', 'Груз для забора')
        request['weight'] = 'Не указано'
        request['declared_value'] = request.get('courier_fee', 0)
    
    # Объединяем все заявки и сортируем по дате создания
    all_requests = courier_requests + pickup_requests
    all_requests.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    
    return {
        "courier_info": courier,
        "new_requests": all_requests,
        "courier_requests": courier_requests,  # Обычные заявки
        "pickup_requests": pickup_requests,   # Заявки на забор
        "total_count": len(all_requests),
        "delivery_count": len(courier_requests),
        "pickup_count": len(pickup_requests)
    }

@app.post("/api/courier/requests/{request_id}/accept")
async def accept_courier_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Принять заявку курьером (обычную или на забор груза)"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Сначала ищем в обычных заявках
    request = db.courier_requests.find_one({"id": request_id}, {"_id": 0})
    request_type = "delivery"
    
    # Если не найдено, ищем в заявках на забор груза
    if not request:
        request = db.courier_pickup_requests.find_one({"id": request_id}, {"_id": 0})
        request_type = "pickup"
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Проверяем что заявка может быть принята этим курьером
    # Для заявок на забор груза (pickup) - любой курьер может принять заявку со статусом pending
    # Для обычных заявок (delivery) - следуем старой логике
    if request_type == "pickup":
        # ИСПРАВЛЕНИЕ: Любой курьер может принять заявку на забор груза со статусом "pending"
        # без предварительного назначения
        can_accept = request.get("request_status") == "pending"
    else:  # delivery
        can_accept = (
            request.get("assigned_courier_id") == courier["id"] or 
            (request.get("assigned_courier_id") is None and request.get("request_status") == "pending")
        )
    
    if not can_accept:
        raise HTTPException(status_code=403, detail="Request not available for acceptance")
    
    try:
        # Подготавливаем данные для обновления
        update_data = {
            "request_status": "accepted",
            "updated_at": datetime.utcnow()
        }
        
        if request.get("assigned_courier_id") is None:
            update_data["assigned_courier_id"] = courier["id"]
            update_data["assigned_courier_name"] = courier["full_name"]
        
        # Обновляем заявку в соответствующей коллекции
        if request_type == "pickup":
            db.courier_pickup_requests.update_one(
                {"id": request_id},
                {"$set": update_data}
            )
            
            # Создаем уведомление для создателя заявки на забор
            create_notification(
                user_id=request["created_by"],
                message=f"Курьер {courier['full_name']} принял заявку на забор груза от {request.get('sender_full_name', 'Клиент')}",
                related_id=request_id
            )
            
        else:  # delivery
            db.courier_requests.update_one(
                {"id": request_id},
                {"$set": update_data}
            )
            
            # Обновляем груз если есть
            if request.get("cargo_id"):
                db.operator_cargo.update_one(
                    {"id": request["cargo_id"]},
                    {"$set": {
                        "courier_request_status": "accepted",
                        "updated_at": datetime.utcnow()
                    }}
                )
            
            # Уведомляем оператора
            create_notification(
                user_id=request["created_by"],
                message=f"Курьер {courier['full_name']} принял заявку на доставку груза {request.get('cargo_name', 'N/A')}",
                related_id=request_id
            )
        
        return {
            "message": "Request accepted successfully",
            "request_type": request_type,
            "request_id": request_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accepting request: {str(e)}")

@app.get("/api/courier/requests/history")
async def get_courier_requests_history(
    current_user: User = Depends(get_current_user),
    page: int = 1,
    per_page: int = 20
):
    """Получить историю заявок курьера"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Получаем историю заявок
    total_count = db.courier_requests.count_documents({"assigned_courier_id": courier["id"]})
    skip = (page - 1) * per_page
    
    requests_history = list(db.courier_requests.find(
        {"assigned_courier_id": courier["id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(per_page))
    
    return create_pagination_response(requests_history, total_count, page, per_page)

# ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS ДЛЯ ПОДДЕРЖКИ

@app.post("/api/courier/requests/{request_id}/cancel")
async def cancel_courier_request(
    request_id: str,
    cancel_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Отменить заявку курьером"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Получаем заявку (проверяем обе коллекции)
    request = db.courier_requests.find_one({"id": request_id}, {"_id": 0})
    request_collection = "courier_requests"
    
    if not request:
        # Проверяем коллекцию заявок на забор груза
        request = db.courier_pickup_requests.find_one({"id": request_id}, {"_id": 0})
        request_collection = "courier_pickup_requests"
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Проверяем что заявка может быть отменена этим курьером
    # Курьер может отменить заявку если она назначена ему или он может ее принять
    can_cancel = (
        request.get("assigned_courier_id") == courier["id"] or 
        (request.get("assigned_courier_id") is None and request.get("request_status") == "pending")
    )
    
    if not can_cancel:
        raise HTTPException(status_code=403, detail="Request not available for cancellation")
    
    try:
        # Обновляем статус заявки (используем определенную ранее коллекцию)
        if request_collection == "courier_requests":
            db.courier_requests.update_one(
                {"id": request_id},
                {"$set": {
                    "request_status": "cancelled",
                    "courier_notes": cancel_data.get("reason", "Отменено курьером"),
                    "updated_at": datetime.utcnow()
                }}
            )
        else:  # courier_pickup_requests
            db.courier_pickup_requests.update_one(
                {"id": request_id},
                {"$set": {
                    "request_status": "cancelled",
                    "courier_notes": cancel_data.get("reason", "Отменено курьером"),
                    "updated_at": datetime.utcnow()
                }}
            )
        
        # Обновляем груз если есть
        if request.get("cargo_id"):
            db.operator_cargo.update_one(
                {"id": request["cargo_id"]},
                {"$set": {
                    "courier_request_status": "cancelled",
                    "updated_at": datetime.utcnow()
                }}
            )
        
        # Уведомляем оператора
        create_notification(
            user_id=request["created_by"],
            message=f"Курьер {courier['full_name']} отменил заявку на забор груза: {cancel_data.get('reason', 'Причина не указана')}",
            related_id=request_id
        )
        
        return {"message": "Request cancelled successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling request: {str(e)}")

@app.post("/api/courier/requests/{request_id}/pickup")
async def pickup_cargo_by_courier(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Забрать груз курьером (после принятия заявки - обычной или на забор груза)"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Сначала ищем в обычных заявках
    request = db.courier_requests.find_one({"id": request_id}, {"_id": 0})
    request_type = "delivery"
    
    # Если не найдено, ищем в заявках на забор груза
    if not request:
        request = db.courier_pickup_requests.find_one({"id": request_id}, {"_id": 0})
        request_type = "pickup"
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Проверяем что заявка принята этим курьером
    if request.get("assigned_courier_id") != courier["id"] or request.get("request_status") != "accepted":
        raise HTTPException(status_code=403, detail="Request not accepted by you or invalid status")
    
    try:
        current_time = datetime.utcnow()
        
        # Обновляем заявку в соответствующей коллекции
        update_data = {
            "request_status": "picked_up",
            "pickup_time": current_time,
            "updated_at": current_time
        }
        
        if request_type == "pickup":
            db.courier_pickup_requests.update_one(
                {"id": request_id},
                {"$set": update_data}
            )
            
            # Создаем уведомление для создателя заявки на забор
            create_notification(
                user_id=request["created_by"],
                message=f"Курьер {courier['full_name']} забрал груз по заявке от {request.get('sender_full_name', 'Клиент')}",
                related_id=request_id
            )
            
        else:  # delivery
            db.courier_requests.update_one(
                {"id": request_id},
                {"$set": update_data}
            )
            
            # Обновляем груз если есть
            if request.get("cargo_id"):
                # Создаем историю операций
                operation_history = {
                    "operation_type": "picked_up_by_courier",
                    "timestamp": current_time,
                    "performed_by": courier["full_name"],
                    "performed_by_id": courier["id"],
                    "details": "Груз забран курьером"
                }
                
                db.operator_cargo.update_one(
                    {"id": request["cargo_id"]},
                    {"$set": {
                        "courier_request_status": "picked_up",
                        "updated_at": current_time
                    },
                    "$push": {"operation_history": operation_history}}
                )
            
            # Уведомляем оператора
            create_notification(
                user_id=request["created_by"],
                message=f"Курьер {courier['full_name']} забрал груз {request.get('cargo_name', 'N/A')}",
                related_id=request_id
            )
        
        return {
            "message": "Cargo picked up successfully",
            "request_type": request_type,
            "request_id": request_id,
            "pickup_time": current_time.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error picking up cargo: {str(e)}")

@app.post("/api/courier/requests/{request_id}/deliver-to-warehouse")
async def deliver_cargo_to_warehouse(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Сдать груз на склад курьером (обычный груз или заявка на забор груза)"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Сначала ищем в обычных заявках
    request = db.courier_requests.find_one({"id": request_id}, {"_id": 0})
    request_type = "delivery"
    
    # Если не найдено, ищем в заявках на забор груза
    if not request:
        request = db.courier_pickup_requests.find_one({"id": request_id}, {"_id": 0})
        request_type = "pickup"
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Проверяем что груз забран этим курьером
    if request.get("assigned_courier_id") != courier["id"] or request.get("request_status") != "picked_up":
        raise HTTPException(status_code=403, detail="Cargo not picked up by you or invalid status")
    
    try:
        current_time = datetime.utcnow()
        
        # Создаем полную историю действий для заявки
        action_history = []
        
        # Добавляем базовые действия
        action_history.append({
            "action": "request_created",
            "timestamp": request.get("created_at", current_time),
            "performed_by": "Оператор",
            "performed_by_id": request.get("created_by"),
            "details": f"Заявка создана {'на забор груза' if request_type == 'pickup' else 'на доставку'}"
        })
        
        if request.get("updated_at") and request.get("request_status") == "picked_up":
            action_history.append({
                "action": "request_accepted",
                "timestamp": request.get("updated_at"),
                "performed_by": courier["full_name"],
                "performed_by_id": courier["id"],
                "details": "Заявка принята курьером"
            })
            
            action_history.append({
                "action": "cargo_picked_up",
                "timestamp": request.get("pickup_time", request.get("updated_at")),
                "performed_by": courier["full_name"],
                "performed_by_id": courier["id"],
                "details": "Груз забран курьером"
            })
        
        # Добавляем действие сдачи на склад
        action_history.append({
            "action": "delivered_to_warehouse",
            "timestamp": current_time,
            "performed_by": courier["full_name"],
            "performed_by_id": courier["id"],
            "details": "Груз сдан на склад"
        })
        
        # Обновляем заявку в соответствующей коллекции
        update_data = {
            "request_status": "delivered_to_warehouse",
            "delivery_time": current_time,
            "updated_at": current_time,
            "action_history": action_history,
            "completed": True
        }
        
        if request_type == "pickup":
            db.courier_pickup_requests.update_one(
                {"id": request_id},
                {"$set": update_data}
            )
            
            # Создаем уведомление для операторов о поступившем грузе
            notification_id = f"WN_{str(uuid.uuid4())}"  # Unique UUID-based ID
            warehouse_notification = {
                "id": notification_id,
                "request_id": request_id,  # Оставляем для совместимости
                "pickup_request_id": request_id,  # ИСПРАВЛЕНИЕ: Добавляем pickup_request_id для frontend
                "request_number": request.get("request_number", request_id[:6]),
                "request_type": "pickup",
                "courier_name": courier["full_name"],
                "courier_id": courier["id"], 
                "sender_full_name": request.get("sender_full_name"),
                "sender_phone": request.get("sender_phone"),
                "pickup_address": request.get("pickup_address"),
                "destination": request.get("destination"),
                "courier_fee": request.get("courier_fee", 0),
                "payment_method": request.get("payment_method", "not_paid"),
                "delivered_at": current_time,
                "status": "pending_acceptance",
                "action_history": action_history,
                "created_at": current_time
            }
            
            # Сохраняем уведомление для операторов
            db.warehouse_notifications.insert_one(warehouse_notification)
            
            # Создаем уведомления для всех операторов и администраторов
            operators_and_admins = list(db.users.find({
                "role": {"$in": ["warehouse_operator", "admin"]}
            }, {"_id": 0}))
            
            for operator in operators_and_admins:
                create_notification(
                    user_id=operator["id"],
                    message=f"Курьер {courier['full_name']} сдал груз на склад. Заявка №{request.get('request_number', request_id[:6])} готова к приемке",
                    related_id=request_id
                )
            
        else:  # delivery
            db.courier_requests.update_one(
                {"id": request_id},
                {"$set": update_data}
            )
            
            # Обновляем груз если есть
            if request.get("cargo_id"):
                # Создаем историю операций для груза
                operation_history = {
                    "operation_type": "delivered_to_warehouse",
                    "timestamp": current_time,
                    "performed_by": courier["full_name"],
                    "performed_by_id": courier["id"],
                    "details": "Груз сдан курьером на склад"
                }
                
                db.operator_cargo.update_one(
                    {"id": request["cargo_id"]},
                    {"$set": {
                        "status": "delivered_to_warehouse",
                        "courier_request_status": "delivered_to_warehouse",
                        "updated_at": current_time
                    },
                    "$push": {"operation_history": operation_history}}
                )
        
        return {
            "message": "Cargo delivered to warehouse successfully",
            "request_type": request_type,
            "request_id": request_id,
            "delivery_time": current_time.isoformat(),
            "action_history": action_history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error delivering cargo to warehouse: {str(e)}")

# НОВЫЙ ENDPOINT: Получение уведомлений о поступивших грузах для операторов
@app.get("/api/operator/warehouse-notifications")
async def get_warehouse_notifications(
    current_user: User = Depends(get_current_user)
):
    """Получить уведомления о грузах, сданных курьерами на склад"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Получаем только активные уведомления о поступивших грузах (не обработанные)
        notifications = list(db.warehouse_notifications.find({
            "status": {"$in": ["pending_acceptance", "in_processing"]}  # Только активные статусы
        }, {"_id": 0}).sort("delivered_at", -1))
        
        return {
            "notifications": notifications,
            "total_count": len(notifications),
            "pending_count": len([n for n in notifications if n.get("status") == "pending_acceptance"]),
            "in_processing_count": len([n for n in notifications if n.get("status") == "in_processing"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouse notifications: {str(e)}")

# ОБНОВЛЕННЫЙ ENDPOINT: Принятие груза оператором со склада (упрощенный)
@app.post("/api/operator/warehouse-notifications/{notification_id}/accept")
async def accept_warehouse_delivery(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Принять уведомление о грузе для оформления"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Получаем уведомление
        notification = db.warehouse_notifications.find_one({"id": notification_id}, {"_id": 0})
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        # Проверяем статус уведомления (разрешаем повторную обработку для completed и sent_to_placement)
        allowed_statuses = ["pending_acceptance", "completed", "sent_to_placement"]
        if notification.get("status") not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"Notification cannot be processed. Current status: {notification.get('status')}. Allowed statuses: {allowed_statuses}")
        
        current_time = datetime.utcnow()
        
        # Обновляем статус уведомления на "в процессе оформления"
        update_result = db.warehouse_notifications.update_one(
            {"id": notification_id},
            {"$set": {
                "status": "in_processing",
                "processing_by": current_user.full_name,
                "processing_by_id": current_user.id,
                "processing_started_at": current_time,
                "updated_at": current_time
            }}
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to update notification status")
        
        return {
            "message": "Notification accepted for processing",
            "notification_id": notification_id,
            "status": "in_processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = f"Error accepting notification: {str(e)}. Traceback: {traceback.format_exc()}"
        print(f"DEBUG: {error_details}")  # This will appear in logs
        raise HTTPException(status_code=500, detail=f"Error accepting notification: {str(e)}")

# НОВЫЙ ENDPOINT: Обновление данных принятого уведомления
@app.put("/api/operator/warehouse-notifications/{notification_id}")
async def update_warehouse_notification(
    notification_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить данные принятого уведомления"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Получаем существующее уведомление
        notification = db.warehouse_notifications.find_one({"id": notification_id}, {"_id": 0})
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        current_time = datetime.utcnow()
        
        # Подготавливаем данные для обновления
        allowed_fields = [
            'sender_full_name', 'sender_phone', 'pickup_address', 
            'destination', 'courier_fee', 'payment_method'
        ]
        
        update_fields = {}
        for field in allowed_fields:
            if field in update_data:
                update_fields[field] = update_data[field]
        
        # Добавляем информацию об обновлении
        update_fields.update({
            "updated_at": current_time,
            "updated_by": current_user.full_name,
            "updated_by_id": current_user.id
        })
        
        # Обновляем уведомление
        update_result = db.warehouse_notifications.update_one(
            {"id": notification_id},
            {"$set": update_fields}
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes were made to the notification")
        
        # Получаем обновленное уведомление
        updated_notification = db.warehouse_notifications.find_one({"id": notification_id}, {"_id": 0})
        
        return {
            "message": "Notification updated successfully",
            "notification_id": notification_id,
            "updated_fields": list(update_fields.keys()),
            "notification": updated_notification
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = f"Error updating notification: {str(e)}. Traceback: {traceback.format_exc()}"
        print(f"DEBUG: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error updating notification: {str(e)}")

# НОВЫЙ ENDPOINT: Полное оформление груза с деталями
@app.post("/api/operator/warehouse-notifications/{notification_id}/complete")
async def complete_cargo_processing(
    notification_id: str,
    cargo_details: dict,
    current_user: User = Depends(get_current_user)
):
    """Завершить оформление груза с полными деталями"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Получаем уведомление в процессе обработки
        notification = db.warehouse_notifications.find_one({"id": notification_id}, {"_id": 0})
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        if notification.get("status") != "in_processing":
            raise HTTPException(status_code=400, detail="Notification not in processing status")
        
        current_time = datetime.utcnow()
        
        # Получаем склады оператора для назначения грузам
        operator_warehouses = get_operator_warehouse_ids(current_user.id)
        
        if not operator_warehouses:
            # Если нет привязок, используем первый активный склад
            warehouses = list(db.warehouses.find({"is_active": True}))
            if warehouses:
                warehouse_id = warehouses[0]["id"]
            else:
                raise HTTPException(status_code=400, detail="No active warehouses found")
        else:
            warehouse_id = operator_warehouses[0]
        
        # Создаем грузы на основе данных формы
        cargo_items = cargo_details.get("cargo_items", [])
        created_cargos = []
        
        for index, item in enumerate(cargo_items):
            cargo_id = str(uuid.uuid4())  # Используем UUID для гарантированной уникальности
            # Создаем уникальный номер груза на основе cargo_id для предотвращения дубликатов
            cargo_number = f"{cargo_id[:6]}/{str(index + 1).zfill(2)}"
            
            cargo_data = {
                "id": cargo_id,
                "cargo_number": cargo_number,
                "sender_full_name": cargo_details.get("sender_full_name", ""),
                "sender_phone": cargo_details.get("sender_phone", ""),
                "sender_address": cargo_details.get("sender_address", ""),
                "recipient_full_name": cargo_details.get("recipient_full_name", ""),
                "recipient_phone": cargo_details.get("recipient_phone", ""),
                "recipient_address": cargo_details.get("recipient_address", ""),
                "cargo_name": item.get("name", ""),
                "weight": float(item.get("weight", 0)),
                "declared_value": float(item.get("price", 0)),
                "payment_method": cargo_details.get("payment_method", "cash"),
                "payment_status": cargo_details.get("payment_status", "not_paid"),
                "delivery_method": cargo_details.get("delivery_method", "pickup"),
                "status": "awaiting_placement",  # ИСПРАВЛЕНО: используем валидный статус вместо placement_ready
                "processing_status": "paid",  # Добавляем для появления в списке размещения
                "warehouse_id": warehouse_id,  # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: добавляем warehouse_id
                
                # НОВОЕ: Информация о маршруте складирования
                "source_warehouse_id": cargo_details.get("source_warehouse_id", warehouse_id),
                "source_warehouse_name": cargo_details.get("source_warehouse_name", ""),
                "destination_warehouse_id": cargo_details.get("destination_warehouse_id", cargo_details.get("warehouse_id")),
                "destination_warehouse_name": cargo_details.get("destination_warehouse_name", ""),
                "is_route_delivery": cargo_details.get("is_route_delivery", False),
                "route_info": cargo_details.get("route_info", {}),
                
                "created_by": current_user.id,
                "created_by_name": current_user.full_name,
                "created_at": current_time,
                "updated_at": current_time,
                "pickup_request_id": notification.get("request_id"),
                "pickup_request_number": notification.get("request_number"),
                "courier_delivered_by": notification.get("courier_name"),
                "courier_delivered_at": notification.get("delivered_at"),
                "route": "moscow_to_tajikistan",  # Добавляем обязательное поле
                "description": f"Груз создан из заявки на забор №{notification.get('request_number')}, позиция {index + 1}. Маршрут: {cargo_details.get('source_warehouse_name', 'Неизвестно')} → {cargo_details.get('destination_warehouse_name', 'Неизвестно')}",  # Добавляем обязательное поле с маршрутом
                "total_weight": sum(float(item.get("weight", 0)) for item in cargo_items),
                "total_value": sum(float(item.get("price", 0)) for item in cargo_items),
                "operation_history": [
                    {
                        "operation_type": "created_from_pickup_request",
                        "timestamp": current_time,
                        "performed_by": current_user.full_name,
                        "performed_by_id": current_user.id,
                        "details": f"Груз создан из заявки на забор №{notification.get('request_number')}. Маршрут: {cargo_details.get('source_warehouse_name', '')} → {cargo_details.get('destination_warehouse_name', '')}"
                    }
                ],
                "original_action_history": notification.get("action_history", [])
            }
            
            # Сохраняем груз
            db.operator_cargo.insert_one(cargo_data)
            created_cargos.append({
                "cargo_id": cargo_id,
                "cargo_number": cargo_number
            })
        
        # Помечаем уведомление как завершенное
        db.warehouse_notifications.update_one(
            {"id": notification_id},
            {"$set": {
                "status": "completed",
                "completed_by": current_user.full_name,
                "completed_by_id": current_user.id,
                "completed_at": current_time,
                "created_cargos": created_cargos,
                "updated_at": current_time
            }}
        )
        
        return {
            "message": "Cargo processing completed successfully",
            "notification_id": notification_id,
            "cargo_id": created_cargos[0]["cargo_id"] if created_cargos else None,
            "cargo_number": created_cargos[0]["cargo_number"] if created_cargos else None,
            "notification_status": "completed",
            "created_cargos": created_cargos,
            "total_items": len(created_cargos)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing cargo processing: {str(e)}")

# НОВЫЙ ENDPOINT: Отправка заявки на размещение
@app.post("/api/operator/warehouse-notifications/{notification_id}/send-to-placement")
async def send_pickup_request_to_placement(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Отправить заявку на забор груза на размещение и исключить из текущего списка"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Получаем уведомление
        notification = db.warehouse_notifications.find_one({"id": notification_id}, {"_id": 0})
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        if notification.get("status") != "in_processing":
            raise HTTPException(status_code=400, detail="Notification not in processing status")
        
        current_time = datetime.utcnow()
        
        # Получаем данные заявки на забор груза (поддержка обратной совместимости)
        pickup_request_id = notification.get("pickup_request_id") or notification.get("request_id")
        if not pickup_request_id:
            raise HTTPException(status_code=400, detail="Pickup request ID not found in notification (neither pickup_request_id nor request_id)")
        
        # Пытаемся найти pickup_request в базе данных
        pickup_request = db.courier_pickup_requests.find_one({"id": pickup_request_id}, {"_id": 0})
        
        # Если pickup_request не найден, используем данные из уведомления
        if not pickup_request:
            # Используем данные прямо из уведомления
            pickup_request = {
                "id": pickup_request_id,
                "sender_full_name": notification.get("sender_full_name", ""),
                "sender_phone": notification.get("sender_phone", ""),
                "pickup_address": notification.get("pickup_address", ""),
                "destination": notification.get("destination", ""),
                "courier_fee": notification.get("courier_fee", 0),
                "payment_method": notification.get("payment_method", "not_paid")
            }
            print(f"INFO: Pickup request {pickup_request_id} not found in courier_pickup_requests, using notification data")
        
        # Получаем склады оператора для назначения грузу
        operator_warehouses = get_operator_warehouse_ids(current_user.id)
        
        if not operator_warehouses:
            # Если нет привязок, используем первый активный склад
            warehouses = list(db.warehouses.find({"is_active": True}))
            if warehouses:
                warehouse_id = warehouses[0]["id"]
            else:
                raise HTTPException(status_code=400, detail="No active warehouses found")
        else:
            warehouse_id = operator_warehouses[0]
        
        # Создаем базовый груз на основе данных заявки с UUID для уникальности
        cargo_id = str(uuid.uuid4())  # ИСПРАВЛЕНИЕ: используем UUID вместо generate_readable_request_number()
        cargo_number = f"{cargo_id[:6]}/01"  # ИСПРАВЛЕНИЕ: номер груза основан на UUID, не на request_number
        
        cargo_data = {
            "id": cargo_id,
            "cargo_number": cargo_number,
            "sender_full_name": pickup_request.get("sender_full_name", ""),
            "sender_phone": pickup_request.get("sender_phone", ""),
            "sender_address": pickup_request.get("pickup_address", ""),
            "recipient_full_name": pickup_request.get("recipient_full_name", ""),  # Данные получателя от курьера/оператора
            "recipient_phone": pickup_request.get("recipient_phone", ""),
            "recipient_address": pickup_request.get("recipient_address", ""),
            "cargo_name": pickup_request.get("destination", "Груз по заявке на забор"),
            "weight": 0.0,  # Будет заполнен при размещении
            "declared_value": 0.0,
            "payment_method": "cash",
            "payment_status": "not_paid",
            "delivery_method": "pickup",
            "status": "awaiting_placement",
            "processing_status": "paid",  # Изменяем на "paid" чтобы груз появился в списке для размещения
            "warehouse_id": warehouse_id,
            "pickup_request_id": pickup_request_id,  # Связываем с заявкой на забор
            "created_by": current_user.id,
            "created_by_name": current_user.full_name,
            "created_at": current_time,
            "route": pickup_request.get("route", "moscow_to_tajikistan"),
            "description": f"Груз создан из заявки на забор №{notification.get('request_number')}"
        }
        
        # Вставляем груз в коллекцию
        db.cargo.insert_one(cargo_data)
        
        # Обновляем статус уведомления на "sent_to_placement"
        db.warehouse_notifications.update_one(
            {"id": notification_id},
            {
                "$set": {
                    "status": "sent_to_placement",
                    "sent_to_placement_at": current_time,
                    "sent_to_placement_by": current_user.full_name,
                    "sent_to_placement_by_id": current_user.id,
                    "created_cargo_id": cargo_id,
                    "created_cargo_number": cargo_number
                }
            }
        )
        
        # Обновляем заявку на забор груза
        db.courier_pickup_requests.update_one(
            {"id": pickup_request_id},
            {
                "$set": {
                    "sent_to_placement": True,
                    "sent_to_placement_at": current_time,
                    "created_cargo_id": cargo_id,
                    "created_cargo_number": cargo_number
                }
            }
        )
        
        return {
            "message": "Pickup request sent to placement successfully",
            "notification_id": notification_id,
            "cargo_id": cargo_id,
            "cargo_number": cargo_number,
            "status": "sent_to_placement"
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in send_pickup_request_to_placement: {str(e)}")
        print(f"TRACEBACK: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error sending to placement: {str(e)} | Details: {error_details[:200]}")

# НОВЫЙ ENDPOINT: История заявок на забор груза  
@app.get("/api/operator/pickup-requests/history")
async def get_pickup_requests_history(
    current_user: User = Depends(get_current_user)
):
    """Получить историю завершенных заявок на забор груза"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Получаем завершенные заявки на забор груза
        history_requests = list(db.courier_pickup_requests.find({
            "request_status": "delivered_to_warehouse",
            "completed": True
        }, {"_id": 0}).sort("delivery_time", -1))
        
        # Добавляем информацию о созданных грузах
        for request in history_requests:
            # Ищем соответствующее уведомление
            notification = db.warehouse_notifications.find_one({
                "request_id": request.get("id"),
                "status": "completed"
            }, {"_id": 0})
            
            if notification:
                request["created_cargos"] = notification.get("created_cargos", [])
                request["processed_by"] = notification.get("completed_by")
                request["processed_at"] = notification.get("completed_at")
            
            request['request_type'] = 'pickup'
        
        return {
            "history_requests": history_requests,
            "total_count": len(history_requests)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pickup requests history: {str(e)}")

# НОВЫЙ ENDPOINT: Получение всех заявок на забор для операторов и администраторов
@app.get("/api/operator/pickup-requests")
async def get_all_pickup_requests(
    current_user: User = Depends(get_current_user)
):
    """Получить все заявки на забор груза для операторов и администраторов"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Получаем только активные заявки на забор груза (исключаем выполненные)
        pickup_requests = list(db.courier_pickup_requests.find({
            "request_status": {"$nin": ["delivered_to_warehouse", "completed"]}  # Исключаем выполненные
        }, {"_id": 0}).sort("created_at", -1))
        
        # Добавляем информацию о статусах
        for request in pickup_requests:
            request['request_type'] = 'pickup'
        
        # Группируем по статусам (только активные)
        by_status = {
            "pending": [r for r in pickup_requests if r.get("request_status") == "pending"],
            "accepted": [r for r in pickup_requests if r.get("request_status") == "accepted"],
            "picked_up": [r for r in pickup_requests if r.get("request_status") == "picked_up"],
            "cancelled": [r for r in pickup_requests if r.get("request_status") == "cancelled"]
        }
        
        return {
            "pickup_requests": pickup_requests,
            "by_status": by_status,
            "total_count": len(pickup_requests),
            "status_counts": {
                "pending": len(by_status["pending"]),
                "accepted": len(by_status["accepted"]),
                "picked_up": len(by_status["picked_up"]),
                "cancelled": len(by_status["cancelled"])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pickup requests: {str(e)}")

@app.get("/api/operator/pickup-requests/{request_id}")
async def get_pickup_request_by_id(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить полную информацию о заявке на забор груза по ID с расширенными данными для модального окна"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Ищем заявку в коллекции заявок на забор груза
        pickup_request = db.courier_pickup_requests.find_one({"id": request_id}, {"_id": 0})
        
        if not pickup_request:
            raise HTTPException(status_code=404, detail="Pickup request not found")
        
        # Добавляем тип заявки
        pickup_request['request_type'] = 'pickup'
        
        # Получаем информацию о курьере, если заявка назначена
        courier_info = {}
        if pickup_request.get('assigned_courier_id'):
            courier = db.couriers.find_one({"id": pickup_request.get('assigned_courier_id')}, {"_id": 0})
            if courier:
                courier_info = {
                    "courier_id": courier.get("id"),
                    "courier_name": courier.get("full_name"),
                    "courier_phone": courier.get("phone"),
                    "transport_type": courier.get("transport_type"),
                    "transport_number": courier.get("transport_number")
                }
        
        # Структурированная информация для модального окна
        modal_data = {
            # Основная информация о заявке
            "request_info": {
                "id": pickup_request.get("id"),
                "request_number": pickup_request.get("request_number"),
                "status": pickup_request.get("request_status"),
                "created_at": pickup_request.get("created_at"),
                "updated_at": pickup_request.get("updated_at"),
                "delivered_at": pickup_request.get("delivered_at")
            },
            
            # Информация о курьере
            "courier_info": courier_info,
            
            # Данные отправителя
            "sender_data": {
                "sender_full_name": pickup_request.get("sender_full_name"),
                "sender_phone": pickup_request.get("sender_phone"),
                "pickup_address": pickup_request.get("pickup_address"),
                "pickup_date": pickup_request.get("pickup_date"),
                "pickup_time_from": pickup_request.get("pickup_time_from"),
                "pickup_time_to": pickup_request.get("pickup_time_to")
            },
            
            # Данные получателя (заполненные курьером)
            "recipient_data": {
                "recipient_full_name": pickup_request.get("recipient_full_name", ""),
                "recipient_phone": pickup_request.get("recipient_phone", ""),
                "recipient_address": pickup_request.get("recipient_address", ""),
                "delivery_method": pickup_request.get("delivery_method", "pickup")
            },
            
            # Информация о грузе
            "cargo_info": {
                "destination": pickup_request.get("destination"),
                "cargo_name": pickup_request.get("cargo_name"),
                "weight": pickup_request.get("weight"),
                "total_value": pickup_request.get("total_value"),
                "declared_value": pickup_request.get("declared_value"),
                "price_per_kg": pickup_request.get("price_per_kg"),  # Добавлено: цена за кг от курьера
                "cargo_items": pickup_request.get("cargo_items", []),
                
                # ИСПРАВЛЕНИЕ: Рассчитываем общий вес и стоимость на основе cargo_items
                "total_weight": sum(item.get("weight", 0) for item in pickup_request.get("cargo_items", [])) if pickup_request.get("cargo_items") else pickup_request.get("weight"),
                "total_cost": sum(item.get("weight", 0) * item.get("price_per_kg", 0) for item in pickup_request.get("cargo_items", [])) if pickup_request.get("cargo_items") else (pickup_request.get("weight", 0) * pickup_request.get("price_per_kg", 0) if pickup_request.get("price_per_kg") else pickup_request.get("total_value", 0))
            },
            
            # Информация об оплате
            "payment_info": {
                "payment_method": pickup_request.get("payment_method"),
                "courier_fee": pickup_request.get("courier_fee"),
                "payment_status": pickup_request.get("payment_status", "not_paid")
            },
            
            # Полные данные заявки для совместимости
            "full_request": pickup_request
        }
        
        return modal_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pickup request: {str(e)}")

@app.get("/api/courier/requests/accepted")
async def get_courier_accepted_requests(
    current_user: User = Depends(get_current_user)
):
    """Получить принятые заявки курьера (включая заявки на забор груза)"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Получаем принятые обычные заявки
    accepted_requests = list(db.courier_requests.find({
        "assigned_courier_id": courier["id"],
        "request_status": "accepted"
    }, {"_id": 0}).sort("created_at", -1))
    
    # Получаем принятые заявки на забор груза
    accepted_pickup_requests = list(db.courier_pickup_requests.find({
        "assigned_courier_id": courier["id"],
        "request_status": "accepted"
    }, {"_id": 0}).sort("created_at", -1))
    
    # Добавляем тип заявки для различения в интерфейсе
    for request in accepted_requests:
        request['request_type'] = 'delivery'  # Обычная доставка
        
    for request in accepted_pickup_requests:
        request['request_type'] = 'pickup'  # Забор груза
        # Добавляем поля совместимости для единообразного отображения
        request['cargo_name'] = request.get('destination', 'Груз для забора')
        request['weight'] = 'Не указано'
        request['declared_value'] = request.get('courier_fee', 0)
    
    # Объединяем все принятые заявки и сортируем по дате создания
    all_accepted = accepted_requests + accepted_pickup_requests
    all_accepted.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    
    return {
        "courier_info": courier,
        "accepted_requests": all_accepted,
        "delivery_requests": accepted_requests,  # Обычные заявки
        "pickup_requests": accepted_pickup_requests,   # Заявки на забор
        "total_count": len(all_accepted),
        "delivery_count": len(accepted_requests),
        "pickup_count": len(accepted_pickup_requests)
    }

@app.get("/api/courier/requests/picked")
async def get_courier_picked_requests(
    current_user: User = Depends(get_current_user)
):
    """Получить забранные грузы курьера (готовые к сдаче на склад - включая заявки на забор груза)"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Получаем забранные обычные заявки
    picked_requests = list(db.courier_requests.find({
        "assigned_courier_id": courier["id"],
        "request_status": "picked_up"
    }, {"_id": 0}).sort("pickup_time", -1))
    
    # Получаем забранные заявки на забор груза
    picked_pickup_requests = list(db.courier_pickup_requests.find({
        "assigned_courier_id": courier["id"],
        "request_status": "picked_up"
    }, {"_id": 0}).sort("pickup_time", -1))
    
    # Добавляем тип заявки для различения в интерфейсе
    for request in picked_requests:
        request['request_type'] = 'delivery'  # Обычная доставка
        
    for request in picked_pickup_requests:
        request['request_type'] = 'pickup'  # Забор груза
        # Добавляем поля совместимости для единообразного отображения
        request['cargo_name'] = request.get('destination', 'Груз для забора')
        request['weight'] = 'Не указано'
        request['declared_value'] = request.get('courier_fee', 0)
    
    # Объединяем все забранные заявки и сортируем по времени забора
    all_picked = picked_requests + picked_pickup_requests
    all_picked.sort(key=lambda x: x.get('pickup_time', datetime.min), reverse=True)
    
    return {
        "courier_info": courier,
        "picked_requests": all_picked,
        "delivery_requests": picked_requests,  # Обычные заявки
        "pickup_requests": picked_pickup_requests,   # Заявки на забор
        "total_count": len(all_picked),
        "delivery_count": len(picked_requests),
        "pickup_count": len(picked_pickup_requests)
    }

@app.put("/api/courier/cargo/{cargo_id}/update")
async def update_cargo_by_courier(
    cargo_id: str,
    cargo_update: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить информацию о грузе курьером"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Проверяем что груз назначен этому курьеру
    cargo = db.operator_cargo.find_one({"id": cargo_id}, {"_id": 0})
    if not cargo:
        raise HTTPException(status_code=404, detail="Cargo not found")
    
    if cargo.get("assigned_courier_id") != courier["id"]:
        raise HTTPException(status_code=403, detail="Cargo not assigned to you")
    
    try:
        current_time = datetime.utcnow()
        
        # Подготавливаем данные для обновления
        update_data = {
            "updated_at": current_time,
            "updated_by_courier": courier["full_name"]
        }
        
        # Обновляем разрешенные поля
        allowed_fields = [
            "cargo_name", "weight", "recipient_full_name", "recipient_phone", 
            "recipient_address", "delivery_method", "payment_method", "declared_value"
        ]
        
        for field in allowed_fields:
            if field in cargo_update:
                update_data[field] = cargo_update[field]
        
        # Создаем историю операций
        operation_history = {
            "operation_type": "updated_by_courier",
            "timestamp": current_time,
            "performed_by": courier["full_name"],
            "performed_by_id": courier["id"],
            "details": "Информация о грузе обновлена курьером",
            "updated_fields": list(cargo_update.keys())
        }
        
        # Обновляем груз
        db.operator_cargo.update_one(
            {"id": cargo_id},
            {
                "$set": update_data,
                "$push": {"operation_history": operation_history}
            }
        )
        
        return {"message": "Cargo updated successfully", "updated_fields": list(cargo_update.keys())}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating cargo: {str(e)}")

@app.get("/api/courier/requests/cancelled")
async def get_courier_cancelled_requests(
    current_user: User = Depends(get_current_user)
):
    """Получить отмененные заявки курьера"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Получаем отмененные заявки курьера
    cancelled_requests = list(db.courier_requests.find({
        "assigned_courier_id": courier["id"],
        "request_status": "cancelled"
    }, {"_id": 0}).sort("updated_at", -1))
    
    # Также получаем заявки, которые были отменены оператором или админом до назначения курьера
    # но курьер их видел в новых заявках
    cancelled_general_requests = list(db.courier_requests.find({
        "request_status": "cancelled",
        "$or": [
            {"assigned_courier_id": None},
            {"assigned_courier_id": courier["id"]}
        ]
    }, {"_id": 0}).sort("updated_at", -1))
    
    # Объединяем и убираем дубликаты по ID
    all_cancelled = []
    seen_ids = set()
    
    for request in cancelled_requests + cancelled_general_requests:
        if request["id"] not in seen_ids:
            all_cancelled.append(request)
            seen_ids.add(request["id"])
    
    # Сортируем по времени обновления
    all_cancelled.sort(key=lambda x: x.get("updated_at", x.get("created_at")), reverse=True)
    
    return {
        "courier_info": courier,
        "cancelled_requests": all_cancelled,
        "total_count": len(all_cancelled)
    }

@app.put("/api/courier/requests/{request_id}/update")
async def update_courier_request(
    request_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить заявку курьером"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Получаем заявку (проверяем обе коллекции)
    request = db.courier_requests.find_one({"id": request_id}, {"_id": 0})
    request_collection = "courier_requests"
    
    if not request:
        # Проверяем коллекцию заявок на забор груза
        request = db.courier_pickup_requests.find_one({"id": request_id}, {"_id": 0})
        request_collection = "courier_pickup_requests"
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Проверяем что заявка назначена этому курьеру
    if request.get("assigned_courier_id") != courier["id"]:
        raise HTTPException(status_code=403, detail="Request not assigned to you")
    
    try:
        current_time = datetime.utcnow()
        
        # Подготавливаем данные для обновления
        update_fields = {}
        
        # Обновляем основную информацию
        if "sender_full_name" in update_data:
            update_fields["sender_full_name"] = update_data["sender_full_name"]
        if "sender_phone" in update_data:
            update_fields["sender_phone"] = update_data["sender_phone"]
        if "sender_address" in update_data:
            update_fields["pickup_address"] = update_data["sender_address"]
        if "recipient_full_name" in update_data:
            update_fields["recipient_full_name"] = update_data["recipient_full_name"]
        if "recipient_phone" in update_data:
            update_fields["recipient_phone"] = update_data["recipient_phone"]
        if "recipient_address" in update_data:
            update_fields["recipient_address"] = update_data["recipient_address"]
        
        # Обновляем информацию о грузах
        if "cargo_items" in update_data and isinstance(update_data["cargo_items"], list):
            # ИСПРАВЛЕНИЕ: Сохраняем полный массив cargo_items с индивидуальными параметрами
            clean_cargo_items = []
            cargo_names = []
            total_weight = 0
            total_value = 0
            
            for item in update_data["cargo_items"]:
                if item.get("name"):  # Только грузы с названием
                    clean_item = {
                        "name": item.get("name", ""),
                        "weight": float(item.get("weight", 0)) if item.get("weight") else 0,
                        "price": float(item.get("total_price", 0)) if item.get("total_price") else 0
                    }
                    
                    # Альтернативные имена полей
                    if not clean_item["price"] and item.get("price"):
                        clean_item["price"] = float(item.get("price", 0))
                    
                    clean_cargo_items.append(clean_item)
                    cargo_names.append(clean_item["name"])
                    total_weight += clean_item["weight"]
                    total_value += clean_item["price"]
            
            if clean_cargo_items:
                # Сохраняем массив cargo_items для детального отображения
                update_fields["cargo_items"] = clean_cargo_items
                
                # Также сохраняем объединенное название для совместимости
                update_fields["cargo_name"] = ", ".join(cargo_names)
                
                # Для заявок на забор груза также обновляем поле destination
                if request_collection == "courier_pickup_requests":
                    update_fields["destination"] = ", ".join(cargo_names)
                
                # Сохраняем общие расчеты
                if total_weight > 0:
                    update_fields["weight"] = total_weight
                if total_value > 0:
                    update_fields["total_value"] = total_value
            
            print(f"💾 Обновляем cargo_items для заявки {request_id}: {len(clean_cargo_items)} грузов, общий вес: {total_weight} кг, общая стоимость: {total_value} ₽")
        
        # Обновляем информацию об оплате
        if "payment_method" in update_data:
            update_fields["payment_method"] = update_data["payment_method"]
        if "payment_received" in update_data:
            update_fields["payment_received"] = update_data["payment_received"]
            update_fields["payment_status"] = "paid" if update_data["payment_received"] else "not_paid"
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Добавляем прямое обновление payment_status
        if "payment_status" in update_data:
            update_fields["payment_status"] = update_data["payment_status"]
        
        # Обновляем способ доставки
        if "delivery_method" in update_data:
            update_fields["delivery_method"] = update_data["delivery_method"]
        if "special_instructions" in update_data:
            update_fields["special_instructions"] = update_data["special_instructions"]
        
        # Добавляем время обновления
        update_fields["updated_at"] = current_time
        
        # Обновляем заявку в базе данных (используем определенную ранее коллекцию)
        if request_collection == "courier_requests":
            result = db.courier_requests.update_one(
                {"id": request_id},
                {"$set": update_fields}
            )
        else:  # courier_pickup_requests
            result = db.courier_pickup_requests.update_one(
                {"id": request_id},
                {"$set": update_fields}
            )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Создаем уведомление оператору об обновлении заявки
        if request.get("created_by"):
            create_notification(
                user_id=request["created_by"],
                message=f"Курьер {courier['full_name']} обновил информацию по заявке №{request.get('request_number', request_id)}",
                related_id=request_id
            )
        
        return {"message": "Request updated successfully", "request_id": request_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating request: {str(e)}")

# НОВЫЕ ENDPOINTS: Обновление данных оплаты
@app.put("/api/courier/pickup-requests/{request_id}/payment")
async def update_pickup_request_payment(
    request_id: str,
    payment_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить данные оплаты для заявки на забор груза"""
    try:
        # Проверяем что заявка существует
        request = db.courier_pickup_requests.find_one({"id": request_id}, {"_id": 0})
        if not request:
            raise HTTPException(status_code=404, detail="Pickup request not found")

        current_time = datetime.utcnow()
        
        # Подготавливаем данные для обновления
        update_fields = {
            "updated_at": current_time,
            "payment_updated_by": current_user.full_name,
            "payment_updated_by_id": current_user.id
        }
        
        # Обновляем поля оплаты
        if "payment_status" in payment_data:
            update_fields["payment_status"] = payment_data["payment_status"]
        if "payment_method" in payment_data:
            update_fields["payment_method"] = payment_data["payment_method"]
        if "amount_paid" in payment_data:
            update_fields["amount_paid"] = float(payment_data["amount_paid"]) if payment_data["amount_paid"] else 0
        
        # Обновляем заявку
        result = db.courier_pickup_requests.update_one(
            {"id": request_id},
            {"$set": update_fields}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes were made")
        
        return {
            "message": "Payment data updated successfully",
            "request_id": request_id,
            "updated_fields": list(update_fields.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating payment data: {str(e)}")

@app.put("/api/admin/warehouse-notifications/{notification_id}/payment")
async def update_warehouse_notification_payment(
    notification_id: str,
    payment_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Обновить данные оплаты для уведомления склада"""
    if current_user.role not in [UserRole.WAREHOUSE_OPERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied: Only operators and admins")
    
    try:
        # Проверяем что уведомление существует
        notification = db.warehouse_notifications.find_one({"id": notification_id}, {"_id": 0})
        if not notification:
            raise HTTPException(status_code=404, detail="Warehouse notification not found")

        current_time = datetime.utcnow()
        
        # Подготавливаем данные для обновления
        update_fields = {
            "updated_at": current_time,
            "payment_updated_by": current_user.full_name,
            "payment_updated_by_id": current_user.id
        }
        
        # Обновляем поля оплаты
        if "payment_status" in payment_data:
            update_fields["payment_status"] = payment_data["payment_status"]
        if "payment_method" in payment_data:
            update_fields["payment_method"] = payment_data["payment_method"]
        if "amount_paid" in payment_data:
            update_fields["amount_paid"] = float(payment_data["amount_paid"]) if payment_data["amount_paid"] else 0
        
        # Обновляем уведомление
        result = db.warehouse_notifications.update_one(
            {"id": notification_id},
            {"$set": update_fields}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes were made")
        
        return {
            "message": "Payment data updated successfully",
            "notification_id": notification_id,
            "updated_fields": list(update_fields.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating payment data: {str(e)}")

@app.put("/api/courier/requests/{request_id}/restore")
async def restore_cancelled_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Восстановить отмененную заявку (вернуть в статус 'pending')"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Получаем профиль курьера
    courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
    if not courier:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    
    # Получаем отмененную заявку
    request = db.courier_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Проверяем что заявка отменена
    if request.get("request_status") != "cancelled":
        raise HTTPException(status_code=400, detail="Request is not cancelled")
    
    try:
        current_time = datetime.utcnow()
        
        # Обновляем статус заявки на 'pending' (новая)
        update_result = db.courier_requests.update_one(
            {"id": request_id},
            {
                "$set": {
                    "request_status": "pending",
                    "assigned_courier_id": None,  # Убираем назначение курьера
                    "assigned_courier_name": None,
                    "cancelled_by": None,
                    "cancelled_at": None,
                    "cancellation_reason": None,
                    "restored_at": current_time,
                    "restored_by": current_user.id,
                    "restored_by_courier": courier["full_name"],
                    "updated_at": current_time
                }
            }
        )
        
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Request not found")
        
        # Создаем уведомление оператору о восстановлении заявки
        if request.get("created_by"):
            create_notification(
                user_id=request["created_by"],
                message=f"Курьер {courier['full_name']} восстановил отмененную заявку №{request.get('request_number', request_id)}",
                related_id=request_id
            )
        
        # Добавляем уведомление всем админам
        admins = list(db.users.find({"role": "admin"}, {"_id": 0}))
        for admin in admins:
            create_notification(
                user_id=admin["id"],
                message=f"Заявка №{request.get('request_number', request_id)} восстановлена курьером {courier['full_name']}",
                related_id=request_id
            )
        
        return {"message": "Request restored successfully", "request_id": request_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restoring request: {str(e)}")

@app.get("/api/admin/couriers/available/{warehouse_id}")
async def get_available_couriers_for_warehouse(
    warehouse_id: str,
    current_user: User = Depends(get_current_user)
):
    """Получить доступных курьеров для склада"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    couriers = list(db.couriers.find({
        "assigned_warehouse_id": warehouse_id,
        "is_active": True
    }, {"_id": 0}))
    
    return {"couriers": couriers, "count": len(couriers)}

# НОВЫЕ ENDPOINTS ДЛЯ ОТСЛЕЖИВАНИЯ МЕСТОПОЛОЖЕНИЯ КУРЬЕРОВ

@app.post("/api/courier/location/update")
async def update_courier_location(
    location_data: CourierLocationUpdate,
    current_user: User = Depends(get_current_user)
):
    """Обновить местоположение курьера (только для курьеров)"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Only couriers can update location")
    
    try:
        # Найти информацию о курьере (создать профиль если не существует)
        courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
        if not courier:
            # Автоматически создать профиль курьера при первом GPS update
            courier_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            courier_profile = {
                "id": courier_id,
                "user_id": current_user.id,
                "full_name": current_user.full_name,
                "phone": current_user.phone,
                "address": "Не указан",
                "transport_type": "car",  # По умолчанию
                "transport_number": "Не указан",
                "transport_capacity": 50.0,  # По умолчанию
                "assigned_warehouse_id": None,  # Будет назначен админом позже
                "assigned_warehouse_name": None,
                "is_active": True,
                "created_at": current_time,
                "updated_at": current_time,
                "status": "offline",
                "notes": "Профиль создан автоматически при первом GPS update"
            }
            
            db.couriers.insert_one(courier_profile)
            courier = courier_profile
            print(f"✅ Auto-created courier profile for user {current_user.id}")
        
        # Получить информацию о текущей заявке (если есть)
        current_request = db.courier_requests.find_one({
            "assigned_courier_id": courier["id"],
            "request_status": {"$in": ["accepted", "picked_up"]}
        }, {"_id": 0})
        
        current_request_id = current_request["id"] if current_request else None
        current_request_address = current_request.get("pickup_address") if current_request else None
        
        # Создать запись местоположения
        location_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        location_record = {
            "id": location_id,
            "courier_id": courier["id"],
            "courier_name": courier["full_name"],
            "courier_phone": courier["phone"],
            "transport_type": courier["transport_type"],
            "latitude": location_data.latitude,
            "longitude": location_data.longitude,
            "status": location_data.status.value,
            "current_address": location_data.current_address,
            "accuracy": location_data.accuracy,
            "speed": location_data.speed,
            "heading": location_data.heading,
            "current_request_id": current_request_id,
            "current_request_address": current_request_address,
            "last_updated": now,
            "created_at": now
        }
        
        # Обновить или создать запись местоположения
        db.courier_locations.update_one(
            {"courier_id": courier["id"]},
            {"$set": location_record},
            upsert=True
        )
        
        # НОВОЕ: Обновить статус в профиле курьера
        db.couriers.update_one(
            {"id": courier["id"]},
            {"$set": {
                "status": location_data.status.value,
                "updated_at": now
            }}
        )
        
        # НОВОЕ: Отправить real-time обновление через WebSocket
        await connection_manager.broadcast_courier_location_update(location_record)
        
        # НОВОЕ: Сохранить в историю перемещений
        history_record = {
            "id": str(uuid.uuid4()),
            "courier_id": courier["id"],
            "courier_name": courier["full_name"],
            "latitude": location_data.latitude,
            "longitude": location_data.longitude,
            "status": location_data.status.value,
            "current_address": location_data.current_address,
            "accuracy": location_data.accuracy,
            "speed": location_data.speed,
            "heading": location_data.heading,
            "timestamp": now,
            "date": now.date().isoformat(),
            "hour": now.hour
        }
        
        db.courier_location_history.insert_one(history_record)
        
        return {
            "message": "Location updated successfully",
            "location_id": location_id,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating location: {str(e)}")


@app.get("/api/operator/couriers/locations")
async def get_warehouse_couriers_locations(
    current_user: User = Depends(get_current_user)
):
    """Получить местоположения курьеров склада (для операторов склада)"""
    if current_user.role != UserRole.WAREHOUSE_OPERATOR:
        raise HTTPException(status_code=403, detail="Only warehouse operators can view their courier locations")
    
    try:
        # Найти склады, назначенные данному оператору
        operator_warehouses = list(db.warehouse_operators.find(
            {"user_id": current_user.id}, 
            {"warehouse_id": 1, "_id": 0}
        ))
        
        if not operator_warehouses:
            return {
                "locations": [],
                "total_count": 0,
                "active_couriers": 0,
                "message": "No warehouses assigned to this operator"
            }
        
        warehouse_ids = [w["warehouse_id"] for w in operator_warehouses]
        
        # Найти курьеров, назначенных к этим складам
        couriers = list(db.couriers.find({
            "assigned_warehouse_id": {"$in": warehouse_ids},
            "is_active": True
        }, {"id": 1, "_id": 0}))
        
        if not couriers:
            return {
                "locations": [],
                "total_count": 0,
                "active_couriers": 0,
                "message": "No couriers assigned to your warehouses"
            }
        
        courier_ids = [c["id"] for c in couriers]
        
        # Получить местоположения этих курьеров
        locations = list(db.courier_locations.find({
            "courier_id": {"$in": courier_ids}
        }, {"_id": 0}))
        
        # Сортировать по времени последнего обновления
        locations.sort(key=lambda x: x.get('last_updated', datetime.min), reverse=True)
        
        # Добавить информацию о времени последнего обновления
        for location in locations:
            last_updated = location.get('last_updated')
            if last_updated:
                time_diff = datetime.utcnow() - last_updated
                minutes_ago = int(time_diff.total_seconds() / 60)
                
                if minutes_ago < 1:
                    location['time_since_update'] = "только что"
                elif minutes_ago < 60:
                    location['time_since_update'] = f"{minutes_ago} мин назад"
                else:
                    hours_ago = int(minutes_ago / 60)
                    location['time_since_update'] = f"{hours_ago} ч назад"
            else:
                location['time_since_update'] = "неизвестно"
        
        return {
            "locations": locations,
            "total_count": len(locations),
            "active_couriers": len([l for l in locations if l.get('status') != 'offline']),
            "warehouse_count": len(warehouse_ids),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching courier locations: {str(e)}")

@app.get("/api/courier/location/status")
async def get_courier_location_status(
    current_user: User = Depends(get_current_user)
):
    """Получить статус отслеживания местоположения курьера"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Only couriers can check location status")
    
    try:
        # Найти информацию о курьере
        courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
        if not courier:
            raise HTTPException(status_code=404, detail="Courier profile not found")
        
        # Найти последнее местоположение
        location = db.courier_locations.find_one(
            {"courier_id": courier["id"]}, 
            {"_id": 0}
        )
        
        if not location:
            return {
                "tracking_enabled": False,
                "status": "offline",
                "message": "Location tracking not started"
            }
        
        # Проверить, как давно было последнее обновление
        last_updated = location.get('last_updated')
        if last_updated:
            time_diff = datetime.utcnow() - last_updated
            minutes_ago = int(time_diff.total_seconds() / 60)
            
            if minutes_ago > 10:  # Считаем оффлайн если нет обновлений больше 10 минут
                tracking_status = "stale"
                time_since = f"{minutes_ago} мин назад"
            else:
                tracking_status = "active"
                time_since = "активно"
        else:
            tracking_status = "unknown"
            time_since = "неизвестно"
        
        return {
            "tracking_enabled": True,
            "status": location.get('status', 'offline'),
            "tracking_status": tracking_status,
            "last_updated": last_updated.isoformat() if last_updated else None,
            "time_since_update": time_since,
            "current_address": location.get('current_address'),
            "current_request_id": location.get('current_request_id')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking location status: {str(e)}")

# НОВЫЕ WEBSOCKET ENDPOINTS ДЛЯ REAL-TIME ОТСЛЕЖИВАНИЯ

@app.websocket("/ws/courier-tracking/admin/{token}")
async def websocket_admin_courier_tracking(websocket: WebSocket, token: str):
    """WebSocket для real-time отслеживания курьеров админом"""
    try:
        # Верифицировать токен админа
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            token_version = payload.get("token_version", 0)
            
            # Найти пользователя и проверить версию токена
            user_doc = db.users.find_one({"id": user_id}, {"_id": 0})
            if not user_doc or user_doc.get("token_version", 0) != token_version:
                await websocket.close(code=4001, reason="Invalid token")
                return
                
            if user_doc["role"] != "admin":
                await websocket.close(code=4003, reason="Admin access required")
                return
                
        except jwt.InvalidTokenError:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Подключить админа
        await connection_manager.connect(websocket, user_id, "admin")
        
        # Отправить текущее состояние всех курьеров
        locations = list(db.courier_locations.find({}, {"_id": 0}))
        welcome_message = {
            "type": "initial_data",
            "data": {
                "locations": locations,
                "total_count": len(locations),
                "active_couriers": len([l for l in locations if l.get('status') != 'offline'])
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await connection_manager.send_personal_message(welcome_message, user_id)
        
        # Отправить статистику подключений
        stats_message = {
            "type": "connection_stats",
            "data": connection_manager.get_connection_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
        await connection_manager.send_personal_message(stats_message, user_id)
        
        # Ожидать отключения
        try:
            while True:
                # Ping каждые 30 секунд для поддержания соединения
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Обработать входящие сообщения (например, запросы на обновление)
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        pong_message = {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await connection_manager.send_personal_message(pong_message, user_id)
                except json.JSONDecodeError:
                    pass
                    
        except asyncio.TimeoutError:
            # Периодический ping для поддержания соединения
            ping_message = {
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }
            await connection_manager.send_personal_message(ping_message, user_id)
        except WebSocketDisconnect:
            pass
            
    except Exception as e:
        print(f"❌ WebSocket error for admin: {e}")
    finally:
        connection_manager.disconnect(user_id)

@app.websocket("/ws/courier-tracking/operator/{token}")
async def websocket_operator_courier_tracking(websocket: WebSocket, token: str):
    """WebSocket для real-time отслеживания курьеров оператором склада"""
    try:
        # Верифицировать токен оператора
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            token_version = payload.get("token_version", 0)
            
            # Найти пользователя и проверить версию токена
            user_doc = db.users.find_one({"id": user_id}, {"_id": 0})
            if not user_doc or user_doc.get("token_version", 0) != token_version:
                await websocket.close(code=4001, reason="Invalid token")
                return
                
            if user_doc["role"] != "warehouse_operator":
                await websocket.close(code=4003, reason="Warehouse operator access required")
                return
                
        except jwt.InvalidTokenError:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Найти склады оператора
        operator_warehouses = list(db.warehouse_operators.find(
            {"user_id": user_id}, 
            {"warehouse_id": 1, "_id": 0}
        ))
        warehouse_ids = [w["warehouse_id"] for w in operator_warehouses]
        
        if not warehouse_ids:
            await websocket.close(code=4004, reason="No warehouses assigned")
            return
        
        # Подключить оператора
        await connection_manager.connect(websocket, user_id, "warehouse_operator", warehouse_ids)
        
        # Найти курьеров складов оператора
        couriers = list(db.couriers.find({
            "assigned_warehouse_id": {"$in": warehouse_ids},
            "is_active": True
        }, {"id": 1, "_id": 0}))
        
        courier_ids = [c["id"] for c in couriers]
        
        # Отправить текущее состояние курьеров складов
        locations = list(db.courier_locations.find({
            "courier_id": {"$in": courier_ids}
        }, {"_id": 0}))
        
        welcome_message = {
            "type": "initial_data",
            "data": {
                "locations": locations,
                "total_count": len(locations),
                "active_couriers": len([l for l in locations if l.get('status') != 'offline']),
                "warehouse_count": len(warehouse_ids),
                "assigned_warehouses": warehouse_ids
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await connection_manager.send_personal_message(welcome_message, user_id)
        
        # Ожидать отключения
        try:
            while True:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Обработать входящие сообщения
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        pong_message = {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await connection_manager.send_personal_message(pong_message, user_id)
                except json.JSONDecodeError:
                    pass
                    
        except asyncio.TimeoutError:
            ping_message = {
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }
            await connection_manager.send_personal_message(ping_message, user_id)
        except WebSocketDisconnect:
            pass
            
    except Exception as e:
        print(f"❌ WebSocket error for operator: {e}")
    finally:
        connection_manager.disconnect(user_id)

@app.get("/api/admin/websocket/stats")
async def get_websocket_connection_stats(
    current_user: User = Depends(get_current_user)
):
    """Получить статистику WebSocket подключений (только для админов)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view WebSocket stats")
    
    stats = connection_manager.get_connection_stats()
    
    # Добавить дополнительную информацию
    detailed_connections = []
    for user_id, connection in connection_manager.connections.items():
        user_info = db.users.find_one({"id": user_id}, {"_id": 0, "full_name": 1, "role": 1})
        detailed_connections.append({
            "user_id": user_id,
            "user_name": user_info.get("full_name", "Unknown") if user_info else "Unknown",
            "role": connection["role"],
            "warehouse_ids": connection.get("warehouse_ids", []),
            "connected_at": connection["connected_at"].isoformat(),
            "connected_duration": str(datetime.utcnow() - connection["connected_at"])
        })
    
    return {
        "connection_stats": stats,
        "detailed_connections": detailed_connections,
        "server_uptime": datetime.utcnow().isoformat()
    }

# НОВЫЕ ENDPOINTS ДЛЯ ИСТОРИИ ПЕРЕМЕЩЕНИЙ И ETA

@app.post("/api/courier/location/history")
async def save_location_to_history(
    location_data: CourierLocationUpdate,
    current_user: User = Depends(get_current_user)
):
    """Сохранить местоположение курьера в историю (автоматически при обновлении)"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Only couriers can save location history")
    
    try:
        # Найти информацию о курьере
        courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
        if not courier:
            raise HTTPException(status_code=404, detail="Courier profile not found")
        
        # Создать запись истории
        history_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        history_record = {
            "id": history_id,
            "courier_id": courier["id"],
            "courier_name": courier["full_name"],
            "latitude": location_data.latitude,
            "longitude": location_data.longitude,
            "status": location_data.status.value,
            "current_address": location_data.current_address,
            "accuracy": location_data.accuracy,
            "speed": location_data.speed,
            "heading": location_data.heading,
            "timestamp": now,
            "date": now.date().isoformat(),  # Для группировки по дням
            "hour": now.hour  # Для группировки по часам
        }
        
        # Сохранить в коллекцию истории
        db.courier_location_history.insert_one(history_record)
        
        return {
            "message": "Location history saved successfully",
            "history_id": history_id,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving location history: {str(e)}")

@app.get("/api/admin/couriers/{courier_id}/history")
async def get_courier_location_history(
    courier_id: str,
    date_from: str = None,  # YYYY-MM-DD
    date_to: str = None,    # YYYY-MM-DD
    current_user: User = Depends(get_current_user)
):
    """Получить историю перемещений курьера (для админов)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view courier history")
    
    try:
        # Подготовить фильтр по датам
        date_filter = {"courier_id": courier_id}
        
        if date_from or date_to:
            date_range = {}
            if date_from:
                date_range["$gte"] = date_from
            if date_to:
                date_range["$lte"] = date_to
            date_filter["date"] = date_range
        else:
            # По умолчанию - последние 7 дней
            week_ago = (datetime.utcnow() - timedelta(days=7)).date().isoformat()
            date_filter["date"] = {"$gte": week_ago}
        
        # Получить историю перемещений
        history = list(db.courier_location_history.find(
            date_filter,
            {"_id": 0}
        ).sort("timestamp", 1))
        
        # Группировать по дням для статистики
        daily_stats = {}
        total_distance = 0
        
        for i, record in enumerate(history):
            date = record["date"]
            if date not in daily_stats:
                daily_stats[date] = {
                    "date": date,
                    "points_count": 0,
                    "distance_km": 0,
                    "avg_speed": 0,
                    "statuses": set()
                }
            
            daily_stats[date]["points_count"] += 1
            daily_stats[date]["statuses"].add(record["status"])
            
            # Рассчитать расстояние между точками
            if i > 0 and history[i-1]["date"] == date:
                distance = calculate_distance(
                    history[i-1]["latitude"], history[i-1]["longitude"],
                    record["latitude"], record["longitude"]
                )
                daily_stats[date]["distance_km"] += distance
                total_distance += distance
            
            # Средняя скорость
            if record.get("speed"):
                daily_stats[date]["avg_speed"] = max(daily_stats[date]["avg_speed"], record["speed"])
        
        # Конвертировать set в list для JSON
        for stats in daily_stats.values():
            stats["statuses"] = list(stats["statuses"])
        
        return {
            "courier_id": courier_id,
            "date_from": date_from or week_ago,
            "date_to": date_to or datetime.utcnow().date().isoformat(),
            "history": history,
            "total_points": len(history),
            "total_distance_km": round(total_distance, 2),
            "daily_stats": list(daily_stats.values())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching courier history: {str(e)}")

@app.get("/api/operator/couriers/{courier_id}/history")
async def get_courier_location_history_operator(
    courier_id: str,
    date_from: str = None,
    date_to: str = None,
    current_user: User = Depends(get_current_user)
):
    """Получить историю перемещений курьера (для операторов склада)"""
    if current_user.role != UserRole.WAREHOUSE_OPERATOR:
        raise HTTPException(status_code=403, detail="Only warehouse operators can view courier history")
    
    try:
        # Проверить, что курьер принадлежит складам оператора
        operator_warehouses = list(db.warehouse_operators.find(
            {"user_id": current_user.id}, 
            {"warehouse_id": 1, "_id": 0}
        ))
        
        if not operator_warehouses:
            raise HTTPException(status_code=404, detail="No warehouses assigned to this operator")
        
        warehouse_ids = [w["warehouse_id"] for w in operator_warehouses]
        
        # Проверить, что курьер назначен к одному из складов оператора
        courier = db.couriers.find_one({
            "id": courier_id,
            "assigned_warehouse_id": {"$in": warehouse_ids}
        }, {"_id": 0})
        
        if not courier:
            raise HTTPException(status_code=403, detail="Courier not assigned to your warehouses")
        
        # Использовать ту же логику, что и для админов
        date_filter = {"courier_id": courier_id}
        
        if date_from or date_to:
            date_range = {}
            if date_from:
                date_range["$gte"] = date_from
            if date_to:
                date_range["$lte"] = date_to
            date_filter["date"] = date_range
        else:
            # По умолчанию - последние 3 дня для операторов
            days_ago = (datetime.utcnow() - timedelta(days=3)).date().isoformat()
            date_filter["date"] = {"$gte": days_ago}
        
        history = list(db.courier_location_history.find(
            date_filter,
            {"_id": 0}
        ).sort("timestamp", 1))
        
        # Упрощенная статистика для операторов
        total_points = len(history)
        total_distance = 0
        
        for i in range(1, len(history)):
            if history[i]["date"] == history[i-1]["date"]:
                distance = calculate_distance(
                    history[i-1]["latitude"], history[i-1]["longitude"],
                    history[i]["latitude"], history[i]["longitude"]
                )
                total_distance += distance
        
        return {
            "courier_id": courier_id,
            "courier_name": courier["full_name"],
            "date_from": date_from or days_ago,
            "date_to": date_to or datetime.utcnow().date().isoformat(),
            "history": history,
            "total_points": total_points,
            "total_distance_km": round(total_distance, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching courier history: {str(e)}")

@app.post("/api/courier/eta/calculate")
async def calculate_eta_to_address(
    request_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Рассчитать время прибытия курьера к адресу"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Only couriers can calculate ETA")
    
    try:
        destination_address = request_data.get("destination_address")
        if not destination_address:
            raise HTTPException(status_code=400, detail="Destination address is required")
        
        # Найти курьера
        courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
        if not courier:
            raise HTTPException(status_code=404, detail="Courier profile not found")
        
        # Найти текущее местоположение курьера
        current_location = db.courier_locations.find_one(
            {"courier_id": courier["id"]}, 
            {"_id": 0}
        )
        
        if not current_location:
            raise HTTPException(status_code=404, detail="Current location not found")
        
        # Рассчитать расстояние и время
        # Простой расчет на основе прямого расстояния (можно улучшить с API маршрутов)
        current_lat = current_location["latitude"]
        current_lng = current_location["longitude"]
        
        # Здесь должна быть геокодирование адреса назначения
        # Для примера используем фиксированные координаты Москвы
        # В реальности нужно использовать Yandex Geocoding API
        dest_lat, dest_lng = 55.751244, 37.618423  # Москва центр
        
        distance_km = calculate_distance(current_lat, current_lng, dest_lat, dest_lng)
        
        # Оценка времени в зависимости от типа транспорта
        transport_speeds = {
            "car": 40,      # км/ч в городе
            "motorcycle": 35,
            "bicycle": 15,
            "on_foot": 5
        }
        
        avg_speed = transport_speeds.get(courier.get("transport_type", "car"), 30)
        eta_hours = distance_km / avg_speed
        eta_minutes = int(eta_hours * 60)
        
        # Добавить буферное время (пробки, светофоры)
        buffer_minutes = max(5, int(eta_minutes * 0.2))  # 20% буфер, минимум 5 минут
        total_eta_minutes = eta_minutes + buffer_minutes
        
        eta_time = datetime.utcnow() + timedelta(minutes=total_eta_minutes)
        
        return {
            "destination_address": destination_address,
            "current_location": {
                "latitude": current_lat,
                "longitude": current_lng
            },
            "destination_location": {
                "latitude": dest_lat,
                "longitude": dest_lng
            },
            "distance_km": round(distance_km, 2),
            "estimated_time_minutes": total_eta_minutes,
            "estimated_arrival": eta_time.isoformat(),
            "transport_type": courier.get("transport_type", "car"),
            "avg_speed_kmh": avg_speed,
            "buffer_minutes": buffer_minutes,
            "calculated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating ETA: {str(e)}")

@app.get("/api/admin/couriers/analytics")
async def get_couriers_analytics(
    date_from: str = None,
    date_to: str = None,
    current_user: User = Depends(get_current_user)
):
    """Получить аналитику по курьерам (для админов)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view courier analytics")
    
    try:
        # Подготовить фильтр по датам
        if not date_from:
            date_from = (datetime.utcnow() - timedelta(days=7)).date().isoformat()
        if not date_to:
            date_to = datetime.utcnow().date().isoformat()
        
        date_filter = {
            "date": {"$gte": date_from, "$lte": date_to}
        }
        
        # Получить всех курьеров
        couriers = list(db.couriers.find({"is_active": True}, {"_id": 0}))
        
        analytics_data = []
        
        for courier in couriers:
            # История перемещений курьера
            history = list(db.courier_location_history.find(
                {**date_filter, "courier_id": courier["id"]},
                {"_id": 0}
            ).sort("timestamp", 1))
            
            if not history:
                continue
            
            # Рассчитать метрики
            total_distance = 0
            total_time_active = 0
            statuses = []
            
            for i in range(1, len(history)):
                # Расстояние
                distance = calculate_distance(
                    history[i-1]["latitude"], history[i-1]["longitude"],
                    history[i]["latitude"], history[i]["longitude"]
                )
                total_distance += distance
                
                # Время активности (между точками)
                time_diff = (datetime.fromisoformat(history[i]["timestamp"].replace('Z', '+00:00')) - 
                           datetime.fromisoformat(history[i-1]["timestamp"].replace('Z', '+00:00')))
                total_time_active += time_diff.total_seconds() / 3600  # в часах
                
                statuses.append(history[i]["status"])
            
            # Заявки курьера за период
            requests = list(db.courier_requests.find({
                "assigned_courier_id": courier["id"],
                "created_at": {
                    "$gte": datetime.fromisoformat(date_from + "T00:00:00"),
                    "$lte": datetime.fromisoformat(date_to + "T23:59:59")
                }
            }, {"_id": 0}))
            
            completed_requests = [r for r in requests if r.get("request_status") == "delivered"]
            
            analytics_data.append({
                "courier_id": courier["id"],
                "courier_name": courier["full_name"],
                "transport_type": courier["transport_type"],
                "warehouse_name": courier.get("assigned_warehouse_name", "N/A"),
                "metrics": {
                    "total_distance_km": round(total_distance, 2),
                    "total_active_hours": round(total_time_active, 2),
                    "avg_speed_kmh": round(total_distance / total_time_active, 2) if total_time_active > 0 else 0,
                    "total_requests": len(requests),
                    "completed_requests": len(completed_requests),
                    "completion_rate": round(len(completed_requests) / len(requests) * 100, 1) if requests else 0,
                    "tracking_points": len(history),
                    "status_breakdown": {
                        status: statuses.count(status) for status in set(statuses)
                    }
                }
            })
        
        # Общая статистика
        total_analytics = {
            "period": {"from": date_from, "to": date_to},
            "total_couriers": len(analytics_data),
            "total_distance_km": sum(c["metrics"]["total_distance_km"] for c in analytics_data),
            "total_requests": sum(c["metrics"]["total_requests"] for c in analytics_data),
            "total_completed": sum(c["metrics"]["completed_requests"] for c in analytics_data),
            "avg_completion_rate": round(
                sum(c["metrics"]["completion_rate"] for c in analytics_data) / len(analytics_data), 1
            ) if analytics_data else 0
        }
        
        return {
            "analytics": analytics_data,
            "summary": total_analytics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating courier analytics: {str(e)}")

# Вспомогательная функция для расчета расстояния между координатами
def calculate_distance(lat1, lon1, lat2, lon2):
    """Рассчитать расстояние между двумя точками в километрах (формула Haversine)"""
    import math
    
    # Радиус Земли в километрах
    R = 6371.0
    
    # Преобразовать градусы в радианы
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Разность координат
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Формула Haversine
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c
    
    return distance

# НОВЫЙ ENDPOINT ДЛЯ ЗАЯВОК НА ЗАБОР ГРУЗА

@app.post("/api/admin/courier/pickup-request")
async def create_courier_pickup_request(
    request_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Создать заявку на забор груза курьером (для админов и операторов)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.WAREHOUSE_OPERATOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Генерировать ID заявки на забор груза
        request_id = generate_pickup_request_number()
        now = datetime.utcnow()
        
        # Подготовить данные заявки на забор
        pickup_request = {
            "id": request_id,
            "request_number": request_id,  # Для совместимости
            "request_type": "pickup",  # Тип заявки - забор груза
            "request_status": "pending",  # Статус заявки
            
            # Информация об отправителе
            "sender_full_name": request_data.get("sender_full_name", ""),
            "sender_phone": request_data.get("sender_phone", ""),
            "pickup_address": request_data.get("pickup_address", ""),
            
            # Информация о получателе (добавлено для отображения в размещении)
            "recipient_full_name": request_data.get("recipient_full_name", ""),
            "recipient_phone": request_data.get("recipient_phone", ""),
            "recipient_address": request_data.get("recipient_address", ""),
            
            # Информация о заборе
            "pickup_date": request_data.get("pickup_date", ""),
            "pickup_time_from": request_data.get("pickup_time_from", ""),
            "pickup_time_to": request_data.get("pickup_time_to", ""),
            
            # Назначение груза (наименование груза)
            "destination": request_data.get("destination", ""),
            "route": request_data.get("route", ""),  # Сохраняем для совместимости
            
            # Информация о грузе (добавлено для модального окна)
            "cargo_name": request_data.get("cargo_name", ""),
            "weight": float(request_data.get("weight", 0)) if request_data.get("weight") else None,
            "total_value": float(request_data.get("total_value", 0)) if request_data.get("total_value") else None,
            "declared_value": float(request_data.get("declared_value", 0)) if request_data.get("declared_value") else None,
            "price_per_kg": float(request_data.get("price_per_kg", 0)) if request_data.get("price_per_kg") else None,  # Добавлено: цена за кг от курьера
            
            # ИСПРАВЛЕНИЕ: Добавляем поддержку cargo_items для множественных грузов с индивидуальными ценами
            "cargo_items": request_data.get("cargo_items", []),  # Массив грузов с индивидуальными ценами
            
            # Курьерская служба
            "courier_fee": float(request_data.get("courier_fee", 0)),
            "payment_method": request_data.get("payment_method", "not_paid"),  # Исправлено: сохраняем как payment_method
            "payment_status": request_data.get("payment_method", "not_paid"),  # Для совместимости
            
            # Системная информация
            "created_by": current_user.id,
            "created_by_name": current_user.full_name,
            "created_at": now,
            "updated_at": now,
            "assigned_courier_id": None,  # Будет назначен позже
            
            # Статус обработки
            "is_processed": False,
            "processed_at": None,
            "processed_by": None
        }
        
        # Сохранить заявку в базу данных
        result = db.courier_pickup_requests.insert_one(pickup_request)
        
        if result.inserted_id:
            # Создать уведомление для курьеров
            notification = {
                "id": str(uuid.uuid4()),
                "type": "new_pickup_request",
                "title": "Новая заявка на забор груза",
                "message": f"Заявка #{request_id} на забор груза от {pickup_request['sender_full_name']}",
                "recipient_role": "courier",
                "recipient_id": None,  # Для всех курьеров
                "data": {
                    "request_id": request_id,
                    "sender_name": pickup_request['sender_full_name'],
                    "pickup_address": pickup_request['pickup_address'],
                    "pickup_date": pickup_request['pickup_date'],
                    "pickup_time": f"{pickup_request['pickup_time_from']} - {pickup_request['pickup_time_to']}"
                },
                "is_read": False,
                "created_at": now
            }
            
            db.notifications.insert_one(notification)
            
            return {
                "success": True,
                "message": "Заявка на забор груза успешно создана",
                "request_id": request_id,
                "request_number": request_id,
                "created_at": now.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create pickup request")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating pickup request: {str(e)}")

@app.get("/api/courier/pickup-requests")
async def get_courier_pickup_requests(
    current_user: User = Depends(get_current_user)
):
    """Получить заявки на забор груза для курьера"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Only couriers can view pickup requests")
    
    try:
        # Найти профиль курьера
        courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
        if not courier:
            raise HTTPException(status_code=404, detail="Courier profile not found")
        
        # Получить все доступные заявки на забор (незанятые)
        available_requests = list(db.courier_pickup_requests.find({
            "request_status": "pending",
            "assigned_courier_id": None,
            "is_processed": False
        }, {"_id": 0}).sort("created_at", -1))
        
        # Получить заявки, назначенные этому курьеру
        assigned_requests = list(db.courier_pickup_requests.find({
            "assigned_courier_id": courier["id"],
            "request_status": {"$in": ["accepted", "in_progress"]},
            "is_processed": False
        }, {"_id": 0}).sort("created_at", -1))
        
        return {
            "available_requests": available_requests,
            "assigned_requests": assigned_requests,
            "total_available": len(available_requests),
            "total_assigned": len(assigned_requests)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pickup requests: {str(e)}")

@app.post("/api/courier/pickup-requests/{request_id}/accept")
async def accept_pickup_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Принять заявку на забор груза курьером"""
    if current_user.role != UserRole.COURIER:
        raise HTTPException(status_code=403, detail="Only couriers can accept pickup requests")
    
    try:
        # Найти профиль курьера
        courier = db.couriers.find_one({"user_id": current_user.id}, {"_id": 0})
        if not courier:
            raise HTTPException(status_code=404, detail="Courier profile not found")
        
        # Найти заявку
        request = db.courier_pickup_requests.find_one({
            "id": request_id,
            "request_status": "pending",
            "assigned_courier_id": None
        }, {"_id": 0})
        
        if not request:
            raise HTTPException(status_code=404, detail="Pickup request not found or already assigned")
        
        # Обновить заявку
        now = datetime.utcnow()
        result = db.courier_pickup_requests.update_one(
            {"id": request_id},
            {
                "$set": {
                    "request_status": "accepted",
                    "assigned_courier_id": courier["id"],
                    "assigned_courier_name": courier["full_name"],
                    "accepted_at": now,
                    "updated_at": now
                }
            }
        )
        
        if result.modified_count > 0:
            # Создать уведомление для создателя заявки
            notification = {
                "id": str(uuid.uuid4()),
                "type": "pickup_request_accepted",
                "title": "Заявка на забор груза принята",
                "message": f"Курьер {courier['full_name']} принял заявку #{request_id}",
                "recipient_role": "admin",
                "recipient_id": request["created_by"],
                "data": {
                    "request_id": request_id,
                    "courier_name": courier["full_name"],
                    "courier_phone": courier["phone"]
                },
                "is_read": False,
                "created_at": now
            }
            
            db.notifications.insert_one(notification)
            
            return {
                "success": True,
                "message": "Заявка на забор груза принята",
                "request_id": request_id,
                "courier_name": courier["full_name"],
                "accepted_at": now.isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to accept pickup request")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accepting pickup request: {str(e)}")

# ИСПРАВЛЕНИЕ: Индивидуальное удаление заявки на забор груза
@app.delete("/api/admin/pickup-requests/{request_id}")
async def delete_pickup_request(request_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Access denied: Only admins")
    
    try:
        # Удаляем заявку на забор по ID
        result = db.courier_pickup_requests.delete_one({"id": request_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        
        # Удаляем связанные уведомления
        db.warehouse_notifications.delete_many({"pickup_request_id": request_id})
        db.warehouse_notifications.delete_many({"request_id": request_id})
        
        return {
            "message": "Заявка на забор груза успешно удалена",
            "deleted_request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting pickup request: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при удалении заявки")

# ИСПРАВЛЕНИЕ: Индивидуальное удаление заявки на забор через courier endpoint (альтернативный доступ)
@app.delete("/api/admin/courier/pickup-requests/{request_id}")
async def delete_courier_pickup_request(request_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Access denied: Only admins")
    
    try:
        # Удаляем заявку на забор по ID
        result = db.courier_pickup_requests.delete_one({"id": request_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        
        # Удаляем связанные уведомления
        db.warehouse_notifications.delete_many({"pickup_request_id": request_id})
        db.warehouse_notifications.delete_many({"request_id": request_id})
        
        return {
            "message": "Заявка на забор груза успешно удалена",
            "deleted_request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting courier pickup request: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при удалении заявки")
# НОВАЯ ФУНКЦИЯ: Активировать курьера (перевести из неактивного в активное состояние)
@app.post("/api/admin/couriers/{courier_id}/activate")
async def activate_courier(courier_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Access denied: Only admins")
    
    try:
        # Находим курьера
        courier = db.couriers.find_one({"id": courier_id}, {"_id": 0})
        if not courier:
            raise HTTPException(status_code=404, detail="Курьер не найден")
        
        # Активируем курьера
        result = db.couriers.update_one(
            {"id": courier_id},
            {
                "$set": {
                    "is_active": True,
                    "reactivated_at": datetime.utcnow(),
                    "reactivated_by": current_user.id,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Не удалось активировать курьера")
        
        # Также активируем связанного пользователя
        if courier.get("user_id"):
            db.users.update_one(
                {"id": courier["user_id"]},
                {"$set": {"is_active": True}}
            )
        
        return {
            "message": "Курьер успешно активирован",
            "courier_id": courier_id,
            "activated_by": current_user.full_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error activating courier: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при активации курьера")

# НОВАЯ ФУНКЦИЯ: Полное удаление курьера из базы данных
@app.delete("/api/admin/couriers/{courier_id}/permanent")
async def permanently_delete_courier(courier_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Access denied: Only admins")
    
    try:
        # Находим курьера
        courier = db.couriers.find_one({"id": courier_id}, {"_id": 0})
        if not courier:
            raise HTTPException(status_code=404, detail="Курьер не найден")
        
        user_id = courier.get("user_id")
        
        # Проверяем, есть ли активные заявки у курьера
        active_requests = list(db.courier_requests.find({
            "assigned_courier_id": courier_id,
            "request_status": {"$in": ["assigned", "accepted"]}
        }))
        
        if len(active_requests) > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Невозможно удалить курьера. У него есть {len(active_requests)} активных заявок. Сначала завершите или переназначьте заявки."
            )
        
        # Удаляем курьера из базы данных
        courier_result = db.couriers.delete_one({"id": courier_id})
        
        # Удаляем связанного пользователя (если он существует и не используется в других ролях)
        user_deleted = False
        if user_id:
            # Проверяем, используется ли пользователь в других ролях
            user = db.users.find_one({"id": user_id}, {"_id": 0})
            if user and user.get("role") == "courier":
                # Безопасно удаляем пользователя только если он имеет роль курьера
                user_result = db.users.delete_one({"id": user_id})
                user_deleted = user_result.deleted_count > 0
        
        # Удаляем связанные записи (местоположения, история и т.д.)
        db.courier_locations.delete_many({"courier_id": courier_id})
        db.courier_requests.update_many(
            {"assigned_courier_id": courier_id},
            {"$set": {"assigned_courier_id": None, "assigned_courier_name": "Удаленный курьер"}}
        )
        
        return {
            "message": "Курьер полностью удален из базы данных",
            "courier_id": courier_id,
            "user_deleted": user_deleted,
            "deleted_by": current_user.full_name,
            "deletion_date": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error permanently deleting courier: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при полном удалении курьера")
@app.post("/api/admin/cleanup-duplicate-notifications")
async def cleanup_duplicate_notifications(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Access denied: Only admins")
    
    try:
        # Находим и удаляем дублированные уведомления
        pipeline = [
            {"$group": {"_id": "$id", "count": {"$sum": 1}, "docs": {"$push": "$$ROOT"}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = list(db.warehouse_notifications.aggregate(pipeline))
        removed_count = 0
        
        for duplicate_group in duplicates:
            docs_to_remove = duplicate_group["docs"][1:]  # Оставляем первый документ
            for doc in docs_to_remove:
                db.warehouse_notifications.delete_one({"_id": doc["_id"]})
                removed_count += 1
        
        return {
            "message": f"Cleanup completed: removed {removed_count} duplicate notifications",
            "duplicates_found": len(duplicates),
            "notifications_removed": removed_count
        }
        
    except Exception as e:
        print(f"Error cleaning up duplicates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)