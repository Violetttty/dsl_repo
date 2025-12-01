# actions.py
import logging
from typing import Dict, Any

from src.database import DatabaseService

logger = logging.getLogger("actions")

# 初始化 SQLite 服务
db = DatabaseService()

# ==========================================================
# 工具函数
# ==========================================================
def set_var(env_vars: Dict[str, Any], key: str, value: Any):
    env_vars[key] = value
    logger.info(f"[SET_VAR] {key} = {value}")


# ==========================================================
# Action 实现
# ==========================================================

def action_local_set_var(env_vars, input_text, step):
    varname = step.action_args[0]
    set_var(env_vars, varname, input_text)
    return {}


def action_compute(env_vars, input_text, step):
    expr = " ".join(step.action_args)
    if "=" not in expr:
        logger.error("Compute action missing '='")
        return {}

    left, right = expr.split("=", 1)
    left = left.strip()
    right = right.strip()

    for var in env_vars:
        right = right.replace(var, str(env_vars[var]))

    try:
        result = eval(right, {}, {})
        set_var(env_vars, left, result)
    except Exception as e:
        logger.error(f"Compute error: {e}")

    return {}


# ====================== 用户操作 ========================

def action_query_user(env_vars, input_text, step):
    uid = env_vars.get("user_id")
    if uid is None:
        logger.error("QueryUser: missing user_id")
        return {}

    user = db.get_user(uid)
    if not user:
        set_var(env_vars, "user_exists", False)
        return {}

    set_var(env_vars, "user_exists", True)
    set_var(env_vars, "user_name", user["name"])
    set_var(env_vars, "balance", user["balance"])
    return {}


def action_increase_balance(env_vars, input_text, step):
    uid = env_vars.get("user_id")
    amount = float(env_vars.get("amount", 0))

    user = db.get_user(uid)
    if not user:
        logger.error("IncreaseBalance: user not found")
        return {}

    db.increase_balance(uid, amount)
    # 从数据库查询最新余额
    new_user = db.get_user(uid)
    set_var(env_vars, "balance", new_user["balance"])
    return {}


# ====================== 订单操作 ========================

def action_query_orders(env_vars, input_text, step):
    uid = env_vars.get("user_id")
    rows = db.get_orders_by_user(uid)

    if not rows:
        set_var(env_vars, "orders", "无订单")
        return {}

    orders = [
        f"{o['order_id']}({o['item']}, {o['status']})"
        for o in rows
    ]
    set_var(env_vars, "orders", ", ".join(orders))
    return {}


def action_query_order_status(env_vars, input_text, step):
    oid = env_vars.get("order_id")
    order = db.get_order(oid)

    if not order:
        set_var(env_vars, "order_status", "订单不存在")
        return {}

    set_var(env_vars, "order_status", order["status"])
    return {}


_new_order_counter = 999

def action_create_order(env_vars, input_text, step):
    # 自动从数据库中获取当前最大订单号
    cur = db.conn.execute("SELECT order_id FROM orders ORDER BY order_id DESC LIMIT 1")
    row = cur.fetchone()

    if row:
        last_id = row["order_id"]
        # 假设是 "N1000"，提取数字部分
        num = int(last_id[1:])
        new_id = f"N{num + 1}"
    else:
        # 如果数据库为空
        new_id = "N1000"

    # 用新的 order_id
    env_vars["order_id"] = new_id

    db.create_order(
        new_id,
        env_vars.get("user_id"),
        env_vars.get("item_name"),
        float(env_vars.get("amount", 0))
    )


def action_log(env_vars, input_text, step):
    text = " ".join(step.action_args)
    logger.info(f"[DSL_LOG] {text}")
    return {}


# ==========================================================
# Action 分发表
# ==========================================================
ACTION_TABLE = {
    "LocalSetVar": action_local_set_var,
    "Compute": action_compute,
    "QueryUser": action_query_user,
    "QueryOrders": action_query_orders,
    "QueryOrderStatus": action_query_order_status,
    "CreateOrder": action_create_order,
    "IncreaseBalance": action_increase_balance,
    "Log": action_log,
}
