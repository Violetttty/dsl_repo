"""
fake_db.py

一个用于单元测试的“数据库测试桩”（FakeDatabaseService）。

设计目标：
- 提供与 src.database.DatabaseService 部分兼容的接口；
- 使用内存中的 Python 数据结构，而不是实际的 SQLite；
- 让依赖数据库的逻辑在不访问真实数据库的情况下也能被测试。

在测试中可以这样使用：

    from test.fake_db import FakeDatabaseService
    from src import actions

    def test_something():
        actions.db = FakeDatabaseService()
        # 后续调用 actions 中的函数时，就会使用内存数据而不是 app.db
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime, timedelta


@dataclass
class FakeUser:
    user_id: str
    name: str = "测试用户"
    phone: str = "13800000000"
    address: str = "测试地址"
    balance: float = 1000.0


@dataclass
class FakeProduct:
    name: str
    price: float
    stock: int = 100


@dataclass
class FakeOrder:
    order_id: str
    user_id: str
    items: List[str]
    quantities: List[int]
    total_amount: float
    status: str = "pending"
    address: str = ""
    phone: str = ""
    estimated_delivery: datetime = field(
        default_factory=lambda: datetime.now() + timedelta(days=3)
    )
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class FakeDatabaseService:
    """
    一个简单的内存数据库，用于替代真实的 DatabaseService 进行单元测试。
    """

    def __init__(self):
        # 预置一个用户和几个商品，方便测试
        self.users: Dict[str, FakeUser] = {
            "U1001": FakeUser("U1001", name="张三"),
            "U1002": FakeUser("U1002", name="李四"),
        }

        self.products: Dict[str, FakeProduct] = {
            "iPhone 15 Pro": FakeProduct("iPhone 15 Pro", 8999.0, 10),
            "MacBook Pro": FakeProduct("MacBook Pro", 12999.0, 5),
        }

        self.orders: Dict[str, FakeOrder] = {}
        self.operation_logs: List[Dict[str, Any]] = []
        self.refunds: Dict[str, Dict[str, Any]] = {}

    # ========== 用户相关 ==========
    def get_user(self, user_id):
        user = self.users.get(user_id)
        return vars(user) if user else None

    def get_user_by_phone(self, phone):
        for u in self.users.values():
            if u.phone == phone:
                return vars(u)
        return None

    def verify_user(self, user_id, phone=None):
        user = self.get_user(user_id)
        if user:
            return {"exists": True, "user": user}
        if phone:
            user = self.get_user_by_phone(phone)
            if user:
                return {"exists": True, "user": user}
        return {"exists": False, "user": None}

    # ========== 商品相关 ==========
    def get_product_by_name(self, product_name):
        # 简单包含匹配，模拟模糊搜索
        for name, p in self.products.items():
            if product_name.lower() in name.lower():
                return {"name": p.name, "price": p.price, "stock": p.stock}
        return None

    def check_stock(self, product_name, quantity):
        p = self.get_product_by_name(product_name)
        if not p:
            return {"available": False, "current_stock": 0, "product": None}
        available = p["stock"] >= quantity
        return {
            "available": available,
            "current_stock": p["stock"],
            "product": p,
        }

    # ========== 订单相关（只实现最常用的几个） ==========
    def get_orders_by_user(self, user_id, page=1, page_size=10):
        orders = [o for o in self.orders.values() if o.user_id == user_id]
        total = len(orders)
        # 简单不分页
        return {
            "total": total,
            "total_pages": 1,
            "page": 1,
            "page_size": page_size,
            "orders": [
                {
                    "order_id": o.order_id,
                    "user_id": o.user_id,
                    "items_json": repr(o.items),
                    "quantities_json": repr(o.quantities),
                    "total_amount": o.total_amount,
                    "status": o.status,
                    "address": o.address,
                    "phone": o.phone,
                    "estimated_delivery": o.estimated_delivery.isoformat(),
                    "created_at": o.created_at.isoformat(),
                    "updated_at": o.updated_at.isoformat(),
                }
                for o in orders
            ],
        }

    def get_order(self, order_id):
        o = self.orders.get(order_id)
        if not o:
            return None
        return {
            "order_id": o.order_id,
            "user_id": o.user_id,
            "items_json": repr(o.items),
            "quantities_json": repr(o.quantities),
            "total_amount": o.total_amount,
            "status": o.status,
            "address": o.address,
            "phone": o.phone,
            "estimated_delivery": o.estimated_delivery.isoformat(),
            "created_at": o.created_at.isoformat(),
            "updated_at": o.updated_at.isoformat(),
            "items": o.items,
            "quantities": o.quantities,
        }

    def create_order(self, order_data):
        # 生成一个简单的订单号
        order_id = f"ORD_FAKE_{len(self.orders) + 1}"
        o = FakeOrder(
            order_id=order_id,
            user_id=order_data["user_id"],
            items=list(order_data.get("items", [])),
            quantities=list(order_data.get("quantities", [])),
            total_amount=float(order_data.get("total_amount", 0)),
            address=order_data.get("address", ""),
            phone=order_data.get("phone", ""),
        )
        self.orders[order_id] = o
        return order_id

    def check_order_cancel_eligibility(self, order_id):
        o = self.orders.get(order_id)
        if not o:
            return {"eligible": False, "reason": "订单不存在"}
        if o.status in ["shipped", "delivered", "cancelled", "refunded"]:
            return {"eligible": False, "reason": f"订单状态为{o.status}"}
        return {"eligible": True, "reason": "可取消"}

    def check_order_modify_eligibility(self, order_id):
        o = self.orders.get(order_id)
        if not o:
            return {"eligible": False, "reason": "订单不存在"}
        if o.status != "pending":
            return {"eligible": False, "reason": f"订单状态为{o.status}"}
        return {"eligible": True, "reason": "可修改"}

    # ========== 日志相关（简单记录） ==========
    def log_operation(self, user_id, action, details, ip_address=None):
        self.operation_logs.append(
            {
                "user_id": user_id,
                "action": action,
                "details": details,
                "ip_address": ip_address,
                "created_at": datetime.now().isoformat(),
            }
        )
        return len(self.operation_logs)


