import sys
import os

# 自动加入 src/ 到 import 路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.database import DatabaseService

db = DatabaseService()

# ===============================
#  添加用户数据
# ===============================
users = [
    ("1003", "Charlie", 75),
    ("1004", "Daisy", 60),
    ("1005", "Evan", 200),
    ("1006", "Fiona", 150),
]

print("插入用户数据...")
for u in users:
    db.conn.execute(
        "INSERT OR IGNORE INTO users(user_id, name, balance) VALUES(?,?,?)",
        u
    )
db.conn.commit()


# ===============================
#  添加订单数据
# ===============================
orders = [
    ("C001", "1003", "Keyboard", 120, "Shipped"),
    ("C002", "1003", "Mouse", 40, "Paid"),

    ("D001", "1004", "Notebook", 10, "Delivered"),
    ("D002", "1004", "Water Bottle", 30, "Processing"),

    ("E001", "1005", "Monitor", 800, "Paid"),

    ("F001", "1006", "Earphones", 90, "Shipped"),
    ("F002", "1006", "USB Cable", 15, "Created"),
]

print("插入订单数据...")
for o in orders:
    db.conn.execute(
        "INSERT OR IGNORE INTO orders(order_id, user_id, item, amount, status) VALUES(?,?,?,?,?)",
        o
    )
db.conn.commit()

print("数据插入完成！")
