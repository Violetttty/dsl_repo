# database.py
import sqlite3

class DatabaseService:
    def __init__(self, db_path="app.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            balance REAL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT,
            item TEXT,
            amount REAL,
            status TEXT
        )
        """)

        self.conn.commit()

    # 用户表 ---------------------------------------------------------
    def get_user(self, user_id):
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def increase_balance(self, user_id, amount):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        self.conn.commit()

    # 订单表 ---------------------------------------------------------
    def get_orders_by_user(self, user_id):
        cur = self.conn.cursor()
        rows = cur.execute(
            "SELECT * FROM orders WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_order(self, order_id):
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            (order_id,)
        ).fetchone()
        return dict(row) if row else None

    def create_order(self, order_id, user_id, item, amount):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO orders(order_id, user_id, item, amount, status) VALUES (?,?,?,?,?)",
            (order_id, user_id, item, amount, "Created")
        )
        self.conn.commit()

