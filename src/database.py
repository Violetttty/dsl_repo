# database.py
import sqlite3
import json
from datetime import datetime, timedelta
import re

class DatabaseService:
    def __init__(self, db_path="app.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.init_sample_data()

    def create_tables(self):
        cur = self.conn.cursor()

        # 用户表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            balance REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 商品表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            category TEXT,
            description TEXT
        )
        """)

        # 订单表（增强）
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            items_json TEXT NOT NULL,  -- JSON格式存储多商品
            quantities_json TEXT NOT NULL, -- JSON格式存储多数量
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, paid, shipped, delivered, cancelled, refunded
            address TEXT,
            phone TEXT,
            estimated_delivery TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)

        # 订单状态历史表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS order_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            status TEXT NOT NULL,
            detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
        """)

        # 退款表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS refunds (
            refund_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'processing', -- processing, completed, failed
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
        """)

        # 操作日志表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.conn.commit()

    def init_sample_data(self):
        """初始化示例数据"""
        cur = self.conn.cursor()
        
        # 检查是否已有数据
        cur.execute("SELECT COUNT(*) as count FROM users")
        if cur.fetchone()["count"] > 0:
            return
        
        # 添加示例用户
        users = [
            ("U1001", "张三", "13800138001", "zhangsan@example.com", "北京市海淀区", 5000.0),
            ("U1002", "李四", "13800138002", "lisi@example.com", "上海市浦东新区", 3000.0),
            ("U1003", "王五", "13800138003", "wangwu@example.com", "广州市天河区", 8000.0)
        ]
        
        for user in users:
            try:
                cur.execute("""
                INSERT OR IGNORE INTO users (user_id, name, phone, email, address, balance)
                VALUES (?, ?, ?, ?, ?, ?)
                """, user)
            except:
                pass
        
        # 添加示例商品
        products = [
            ("iPhone 15 Pro", 8999.0, 100, "手机", "苹果最新款手机"),
            ("MacBook Pro", 12999.0, 50, "电脑", "苹果笔记本电脑"),
            ("华为Mate 60", 6999.0, 200, "手机", "华为旗舰手机"),
            ("小米电视", 3999.0, 150, "家电", "4K智能电视"),
            ("联想笔记本", 5999.0, 80, "电脑", "商务笔记本电脑")
        ]
        
        for product in products:
            try:
                cur.execute("""
                INSERT OR IGNORE INTO products (name, price, stock, category, description)
                VALUES (?, ?, ?, ?, ?)
                """, product)
            except:
                pass
        
        # 添加示例订单
        import json
        orders = [
            ("ORD20241215001", "U1001", 
             json.dumps(["iPhone 15 Pro", "MacBook Pro"]),
             json.dumps([1, 1]),
             21998.0, "delivered", "北京市海淀区", "13800138001",
             datetime.now() - timedelta(days=2)),
            ("ORD20241215002", "U1002",
             json.dumps(["华为Mate 60"]),
             json.dumps([2]),
             13998.0, "shipped", "上海市浦东新区", "13800138002",
             datetime.now() + timedelta(days=3))
        ]
        
        for order in orders:
            try:
                cur.execute("""
                INSERT OR IGNORE INTO orders 
                (order_id, user_id, items_json, quantities_json, total_amount, status, address, phone, estimated_delivery)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, order)
            except:
                pass
        
        # 添加订单状态历史
        status_history = [
            ("ORD20241215001", "pending", "订单创建"),
            ("ORD20241215001", "paid", "已支付"),
            ("ORD20241215001", "shipped", "已发货"),
            ("ORD20241215001", "delivered", "已送达"),
            ("ORD20241215002", "pending", "订单创建"),
            ("ORD20241215002", "paid", "已支付"),
            ("ORD20241215002", "shipped", "已发货")
        ]
        
        for history in status_history:
            try:
                cur.execute("""
                INSERT OR IGNORE INTO order_status_history (order_id, status, detail)
                VALUES (?, ?, ?)
                """, history)
            except:
                pass
        
        self.conn.commit()

    # ==================== 用户操作 ====================
    
    def get_user(self, user_id):
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    
    def get_user_by_phone(self, phone):
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM users WHERE phone = ?",
            (phone,)
        ).fetchone()
        return dict(row) if row else None
    
    def verify_user(self, user_id, phone=None):
        user = self.get_user(user_id)
        if user:
            return {"exists": True, "user": user}
        
        if phone:
            user = self.get_user_by_phone(phone)
            if user:
                return {"exists": True, "user": user}
        
        return {"exists": False, "user": None}
    
    def update_user_info(self, user_id, address=None, phone=None):
        cur = self.conn.cursor()
        updates = []
        params = []
        
        if address:
            updates.append("address = ?")
            params.append(address)
        if phone:
            updates.append("phone = ?")
            params.append(phone)
        
        if updates:
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            cur.execute(query, params)
            self.conn.commit()
            return True
        return False
    
    def change_user_balance(self, user_id, amount_delta):
        """变更用户余额（正数为充值，负数为取款）
        
        返回结构：
        {
            "success": bool,
            "reason": str,
            "new_balance": float 或 None
        }
        """
        cur = self.conn.cursor()
        user = self.get_user(user_id)
        if not user:
            return {"success": False, "reason": "用户不存在", "new_balance": None}

        current_balance = float(user.get("balance", 0.0))
        new_balance = current_balance + float(amount_delta)

        # 取款时余额不足
        if new_balance < 0:
            return {"success": False, "reason": "余额不足", "new_balance": current_balance}

        cur.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_balance, user_id)
        )
        self.conn.commit()
        return {"success": True, "reason": "OK", "new_balance": new_balance}
    
    # ==================== 商品操作 ====================
    
    def get_product_by_name(self, product_name):
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM products WHERE name LIKE ?",
            (f"%{product_name}%",)
        ).fetchone()
        return dict(row) if row else None
    
    def get_products_by_names(self, product_names):
        """查询多个商品"""
        placeholders = ','.join(['?'] * len(product_names))
        cur = self.conn.cursor()
        rows = cur.execute(
            f"SELECT * FROM products WHERE name IN ({placeholders})",
            product_names
        ).fetchall()
        return [dict(row) for row in rows]
    
    def get_all_products(self):
        """获取所有商品（用于在创建订单界面展示商品列表）"""
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT name, price, stock FROM products ORDER BY name"
        ).fetchall()
        return [dict(row) for row in rows]
    
    def check_stock(self, product_name, quantity):
        """检查库存"""
        product = self.get_product_by_name(product_name)
        if not product:
            return {"available": False, "current_stock": 0, "product": None}
        
        available = product["stock"] >= quantity
        return {
            "available": available,
            "current_stock": product["stock"],
            "product": product
        }
    
    def update_stock(self, product_name, quantity_change):
        """更新库存"""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE products SET stock = stock + ? WHERE name = ?",
            (quantity_change, product_name)
        )
        self.conn.commit()
        return cur.rowcount > 0
    
    # ==================== 订单操作 ====================
    
    def get_orders_by_user(self, user_id, page=1, page_size=10):
        """分页获取用户订单"""
        offset = (page - 1) * page_size
        cur = self.conn.cursor()
        
        # 获取总订单数
        cur.execute(
            "SELECT COUNT(*) as total FROM orders WHERE user_id = ?",
            (user_id,)
        )
        total = cur.fetchone()["total"]
        
        # 获取分页数据
        rows = cur.execute("""
            SELECT * FROM orders 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (user_id, page_size, offset)).fetchall()
        
        return {
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
            "page": page,
            "page_size": page_size,
            "orders": [dict(row) for row in rows]
        }
    
    def get_order(self, order_id):
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            (order_id,)
        ).fetchone()
        if row:
            order = dict(row)
            # 解析JSON字段
            import json
            order["items"] = json.loads(order["items_json"])
            order["quantities"] = json.loads(order["quantities_json"])
            return order
        return None
    
    def check_order_ownership(self, order_id, user_id):
        """检查订单是否属于用户"""
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT 1 FROM orders WHERE order_id = ? AND user_id = ?",
            (order_id, user_id)
        ).fetchone()
        return bool(row)
    
    def check_order_cancel_eligibility(self, order_id):
        """检查订单是否可取消"""
        order = self.get_order(order_id)
        if not order:
            return {"eligible": False, "reason": "订单不存在"}
        
        # 已发货或已完成的订单不可取消
        if order["status"] in ["shipped", "delivered", "cancelled", "refunded"]:
            return {"eligible": False, "reason": f"订单状态为{order['status']}"}
        
        return {"eligible": True, "reason": "可取消"}
    
    def check_order_modify_eligibility(self, order_id):
        """检查订单是否可修改"""
        order = self.get_order(order_id)
        if not order:
            return {"eligible": False, "reason": "订单不存在"}
        
        # 只有pending状态的订单可修改
        if order["status"] != "pending":
            return {"eligible": False, "reason": f"订单状态为{order['status']}"}
        
        return {"eligible": True, "reason": "可修改"}
    
    def create_order(self, order_data):
        """创建新订单"""
        import json
        cur = self.conn.cursor()
        
        # 生成订单号
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        order_id = f"ORD{timestamp}"
        
        try:
            cur.execute("""
                INSERT INTO orders 
                (order_id, user_id, items_json, quantities_json, total_amount, 
                 status, address, phone, estimated_delivery)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                order_data["user_id"],
                json.dumps(order_data["items"]),
                json.dumps(order_data["quantities"]),
                order_data["total_amount"],
                "pending",
                order_data.get("address", ""),
                order_data.get("phone", ""),
                order_data.get("estimated_delivery", 
                             datetime.now() + timedelta(days=3))
            ))
            
            # 添加状态历史
            cur.execute("""
                INSERT INTO order_status_history (order_id, status, detail)
                VALUES (?, ?, ?)
            """, (order_id, "pending", "订单创建"))
            
            # 减少库存
            for item, quantity in zip(order_data["items"], order_data["quantities"]):
                self.update_stock(item, -quantity)
            
            self.conn.commit()
            return order_id
            
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def cancel_order(self, order_id, refund_amount=None):
        """取消订单"""
        cur = self.conn.cursor()
        
        try:
            # 获取订单信息
            order = self.get_order(order_id)
            if not order:
                return False
            
            # 更新订单状态
            cur.execute(
                "UPDATE orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                (order_id,)
            )
            
            # 添加状态历史
            cur.execute("""
                INSERT INTO order_status_history (order_id, status, detail)
                VALUES (?, ?, ?)
            """, (order_id, "cancelled", "订单已取消"))
            
            # 恢复库存
            for item, quantity in zip(order["items"], order["quantities"]):
                self.update_stock(item, quantity)
            
            # 如果有退款，创建退款记录
            if refund_amount:
                refund_id = f"REF{order_id[3:]}"
                cur.execute("""
                    INSERT INTO refunds (refund_id, order_id, amount, status, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (refund_id, order_id, refund_amount, "processing", "订单取消"))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def update_order_address(self, order_id, address):
        """更新订单地址"""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE orders SET address = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
            (address, order_id)
        )
        self.conn.commit()
        return cur.rowcount > 0
    
    def update_order_phone(self, order_id, phone):
        """更新订单联系电话"""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE orders SET phone = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
            (phone, order_id)
        )
        self.conn.commit()
        return cur.rowcount > 0
    
    def update_order_delivery_time(self, order_id, delivery_time):
        """更新订单配送时间"""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE orders SET estimated_delivery = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
            (delivery_time, order_id)
        )
        self.conn.commit()
        return cur.rowcount > 0


    # ==================== 退款操作 ====================
    
    def get_refund_status(self, order_id):
        """获取退款状态"""
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM refunds WHERE order_id = ? ORDER BY created_at DESC LIMIT 1",
            (order_id,)
        ).fetchone()
        return dict(row) if row else None
    
    # ==================== 日志操作 ====================
    
    def log_operation(self, user_id, action, details, ip_address=None):
        """记录操作日志"""
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO operation_logs (user_id, action, details, ip_address)
            VALUES (?, ?, ?, ?)
        """, (user_id, action, details, ip_address))
        self.conn.commit()
        return cur.lastrowid
    
    def get_operation_logs(self, user_id=None, limit=100):
        """获取操作日志"""
        cur = self.conn.cursor()
        if user_id:
            rows = cur.execute("""
                SELECT * FROM operation_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit)).fetchall()
        else:
            rows = cur.execute("""
                SELECT * FROM operation_logs 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(row) for row in rows]