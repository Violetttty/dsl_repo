# actions.py
# -----------------------------------------
# 内置 Mock 数据库 + 8 个 Action 动作
# -----------------------------------------

import logging
from typing import Dict, Any

logger = logging.getLogger("actions")


# ==========================================================
#  Mock 数据库（你之后可以替换成真正数据库）
# ==========================================================

MOCK_DB = {
    "users": {
        "1001": {"name": "Alice", "balance": 50},
        "1002": {"name": "Bob", "balance": 120},
    },
    "orders": {
        "A001": {"user_id": "1001", "item": "Book", "amount": 30, "status": "Shipped"},
        "A002": {"user_id": "1001", "item": "Pen", "amount": 5,  "status": "Paid"},
        "B001": {"user_id": "1002", "item": "Laptop", "amount": 3000, "status": "Processing"},
    }
}


# ==========================================================
# 工具函数：存变量到 env_vars
# ==========================================================

def set_var(env_vars: Dict[str, Any], key: str, value: Any):
    env_vars[key] = value
    logger.info(f"[SET_VAR] {key} = {value}")


# ==========================================================
# Action 实现
# ==========================================================


# 1. LocalSetVar ---------------------------------------------------

def action_local_set_var(env_vars, input_text, step):
    """
    把用户输入写入 DSL 的变量。
    DSL 中你会写：
        Action LocalSetVar user_id
    parser 解析为 step.action_args = ["user_id"]
    """
    varname = step.action_args[0]
    set_var(env_vars, varname, input_text)
    return {}


# 2. Compute --------------------------------------------------------

def action_compute(env_vars, input_text, step):
    """
    执行四则运算：
        Action Compute total = amount * 2
    """
    expr = " ".join(step.action_args)      # e.g. "total = amount * 2"
    if "=" not in expr:
        logger.error("Compute action missing '='")
        return {}

    left, right = expr.split("=", 1)
    left = left.strip()
    right = right.strip()

    # 替换变量
    for var in env_vars:
        right = right.replace(var, str(env_vars[var]))

    try:
        result = eval(right, {}, {})
    except Exception as e:
        logger.error(f"Compute error: {e}")
        return {}

    set_var(env_vars, left, result)
    return {}


# 3. QueryUser ------------------------------------------------------

def action_query_user(env_vars, input_text, step):
    """
    根据 user_id 查询用户信息。
        Action QueryUser
    需要 env_vars["user_id"]
    """
    uid = env_vars.get("user_id")
    if uid is None:
        logger.error("QueryUser: missing user_id")
        return {}

    user = MOCK_DB["users"].get(uid)
    if not user:
        set_var(env_vars, "user_exists", False)
        return {}

    set_var(env_vars, "user_exists", True)
    set_var(env_vars, "user_name", user["name"])
    set_var(env_vars, "balance", user["balance"])
    return {}


# 4. QueryOrders ----------------------------------------------------

def action_query_orders(env_vars, input_text, step):
    """
    查询用户所有订单：
        Action QueryOrders
    输出 $orders
    """
    uid = env_vars.get("user_id")
    if uid is None:
        logger.error("QueryOrders: missing user_id")
        return {}

    orders = []
    for oid, info in MOCK_DB["orders"].items():
        if info["user_id"] == uid:
            orders.append(f"{oid}({info['item']}, {info['status']})")

    set_var(env_vars, "orders", ", ".join(orders) if orders else "无订单")
    return {}


# 5. QueryOrderStatus -----------------------------------------------

def action_query_order_status(env_vars, input_text, step):
    """
    查询单个订单状态：
        Action QueryOrderStatus
    要求 env_vars["order_id"]
    """
    oid = env_vars.get("order_id")
    if oid is None:
        logger.error("QueryOrderStatus: missing order_id")
        return {}

    order = MOCK_DB["orders"].get(oid)
    if not order:
        set_var(env_vars, "order_status", "订单不存在")
        return {}

    set_var(env_vars, "order_status", order["status"])
    return {}


# 6. CreateOrder -----------------------------------------------------

_new_order_counter = 999

def action_create_order(env_vars, input_text, step):
    """
    创建订单：
        Action CreateOrder
    需要：
        user_id
        item_name
        amount
    """
    global _new_order_counter
    _new_order_counter += 1

    oid = f"N{_new_order_counter}"  # 新订单 ID

    MOCK_DB["orders"][oid] = {
        "user_id": env_vars.get("user_id"),
        "item": env_vars.get("item_name"),
        "amount": float(env_vars.get("amount", 0)),
        "status": "Created"
    }

    set_var(env_vars, "order_id", oid)
    return {}


# 7. IncreaseBalance -------------------------------------------------

def action_increase_balance(env_vars, input_text, step):
    """
    增加余额：
        Action IncreaseBalance
    """
    uid = env_vars.get("user_id")
    amount = float(env_vars.get("amount", 0))

    user = MOCK_DB["users"].get(uid)
    if not user:
        logger.error("IncreaseBalance: user not found")
        return {}

    user["balance"] += amount
    set_var(env_vars, "balance", user["balance"])
    return {}


# 8. Log -------------------------------------------------------------

def action_log(env_vars, input_text, step):
    """
    打日志：
        Action Log "some text"
    """
    text = " ".join(step.action_args)
    logger.info(f"[DSL_LOG] {text}")
    return {}


# ==========================================================
#  Action 调用分发器（Interpreter 会调用这一层）
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


def execute_action(action_name: str, env_vars, input_text, step):
    func = ACTION_TABLE.get(action_name)
    if not func:
        logger.error(f"Unknown action: {action_name}")
        return {}

    logger.info(f"Running action {action_name} ...")
    return func(env_vars, input_text, step)
