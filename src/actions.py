# actions.py
import logging
import re
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from src.database import DatabaseService

logger = logging.getLogger("actions")

# 初始化数据库服务
db = DatabaseService()

# ==========================================================
# 工具函数
# ==========================================================
def set_var(env_vars: Dict[str, Any], key: str, value: Any):
    """设置环境变量"""
    env_vars[key] = value
    logger.info(f"[SET_VAR] {key} = {value}")

def get_var(env_vars: Dict[str, Any], key: str, default=None):
    """获取环境变量"""
    return env_vars.get(key, default)

# ==========================================================
# 输入验证相关 Action
# ==========================================================

def action_validate_user_input(env_vars, input_text, step):
    """验证用户输入并提取信息"""
    input_type = step.action_args[0] if step.action_args else "text"
    if input_type == "userId":
        # 用户ID验证：U开头+数字
        if re.match(r'^U\d+$', input_text):
            set_var(env_vars, "user_id", input_text)
            set_var(env_vars, "input_valid", True)
        else:
            # 也可能是手机号
            if re.match(r'^\d{11}$', input_text):
                user = db.get_user_by_phone(input_text)
                if user:
                    set_var(env_vars, "user_id", user["user_id"])
                    set_var(env_vars, "input_valid", True)
                else:
                    set_var(env_vars, "input_valid", False)
            else:
                set_var(env_vars, "input_valid", False)
    
    elif input_type == "orderId":
        # 订单号验证：ORD开头+数字
        if re.match(r'^ORD\d+$', input_text.upper()):
            set_var(env_vars, "order_id", input_text.upper())
            set_var(env_vars, "input_valid", True)
        else:
            set_var(env_vars, "input_valid", False)
    
    elif input_type == "amount":
        # 金额验证：数字，可包含小数点
        match = re.search(r'(\d+(\.\d+)?)', input_text)
        if match:
            set_var(env_vars, "amount", float(match.group(1)))
            set_var(env_vars, "input_valid", True)
        else:
            set_var(env_vars, "input_valid", False)
    
    elif input_type == "phone":
        # 电话验证：11位数字
        match = re.search(r'(\d{11})', input_text)
        if match:
            set_var(env_vars, "phone", match.group(1))
            set_var(env_vars, "input_valid", True)
        else:
            set_var(env_vars, "input_valid", False)
    
    else:
        set_var(env_vars, "input_valid", True)
    
    return {}

def action_verify_user_exists(env_vars, input_text, step):
    """验证用户是否存在"""
    user_id = get_var(env_vars, "user_id")
    result = db.verify_user(user_id)
    set_var(env_vars, "user_exists", result["exists"])
    if result["exists"]:
        user = result["user"]
        set_var(env_vars, "user_name", user["name"])
        set_var(env_vars, "user_balance", user["balance"])
        set_var(env_vars, "user_address", user["address"])
        set_var(env_vars, "user_phone", user["phone"])
    
    return {}

def action_verify_order_exists(env_vars, input_text, step):
    """验证订单是否存在"""
    order_id = get_var(env_vars, "order_id")
    order = db.get_order(order_id)
    
    set_var(env_vars, "order_exists", bool(order))
    if order:
        set_var(env_vars, "order_status", order["status"])
        set_var(env_vars, "order_amount", order["total_amount"])
        set_var(env_vars, "order_items", ", ".join(order["items"]))
    
    return {}

def action_validate_order_id(env_vars, input_text, step):
    """验证订单号格式"""
    if re.match(r'^ORD\d+$', input_text.upper()):
        set_var(env_vars, "order_id", input_text.upper())
        set_var(env_vars, "order_id_valid", True)
    else:
        set_var(env_vars, "order_id_valid", False)
    
    return {}

def action_validate_item_name(env_vars, input_text, step):
    """验证商品名称"""
    items = [item.strip() for item in input_text.split(',') if item.strip()]
    set_var(env_vars, "item_names_raw", items)
    set_var(env_vars, "item_names_valid", len(items) > 0)
    return {}

def action_validate_quantity(env_vars, input_text, step):
    """验证数量"""
    quantities = []
    valid = True
    
    for qty_str in input_text.split(','):
        qty_str = qty_str.strip()
        if qty_str.isdigit():
            quantities.append(int(qty_str))
        else:
            valid = False
            break
    
    set_var(env_vars, "quantities_raw", quantities)
    set_var(env_vars, "quantities_valid", valid and len(quantities) > 0)
    return {}

def action_validate_amount(env_vars, input_text, step):
    """验证金额"""
    match = re.search(r'(\d+(\.\d+)?)', input_text)
    if match:
        amount = float(match.group(1))
        set_var(env_vars, "amount", amount)
        set_var(env_vars, "amount_valid", True)
    else:
        set_var(env_vars, "amount_valid", False)
    
    return {}

def action_validate_address(env_vars, input_text, step):
    """验证地址"""
    if len(input_text.strip()) >= 5:  # 简单长度验证
        set_var(env_vars, "address", input_text.strip())
        set_var(env_vars, "address_valid", True)
    else:
        set_var(env_vars, "address_valid", False)
    
    return {}

def action_validate_phone(env_vars, input_text, step):
    """验证电话号码"""
    match = re.search(r'(\d{11})', input_text)
    if match:
        set_var(env_vars, "phone", match.group(1))
        set_var(env_vars, "phone_valid", True)
    else:
        set_var(env_vars, "phone_valid", False)
    
    return {}

# ==========================================================
# 数据处理相关 Action
# ==========================================================

def action_parse_items(env_vars, input_text, step):
    """解析商品列表"""
    items = get_var(env_vars, "item_names_raw", [])
    valid_items = []
    
    for item_name in items:
        product = db.get_product_by_name(item_name)
        if product:
            valid_items.append(product["name"])
        else:
            # 如果找不到精确匹配，使用输入的名称
            valid_items.append(item_name)

    # 保存标准化后的商品列表，同时提供一个展示用的字符串 item_name
    set_var(env_vars, "item_names", valid_items)
    if valid_items:
        set_var(env_vars, "item_name", ", ".join(valid_items))
    return {}

def action_parse_quantities(env_vars, input_text, step):
    """解析数量列表"""
    quantities = get_var(env_vars, "quantities_raw", [])
    set_var(env_vars, "quantities", quantities)
    return {}

def action_match_items_quantities(env_vars, input_text, step):
    """匹配商品和数量"""
    items = get_var(env_vars, "item_names", [])
    quantities = get_var(env_vars, "quantities", [])
    
    # 如果商品和数量数量不匹配，用1填充缺失的数量
    if len(quantities) < len(items):
        quantities.extend([1] * (len(items) - len(quantities)))
    elif len(quantities) > len(items):
        quantities = quantities[:len(items)]
    
    set_var(env_vars, "item_names", items)
    set_var(env_vars, "quantities", quantities)
    # 提供展示用的数量字符串 quantity，便于 DSL 中直接使用
    if quantities:
        set_var(env_vars, "quantity", ", ".join(map(str, quantities)))
    set_var(env_vars, "matched", True)
    
    # 计算总金额
    total = 0
    for item, qty in zip(items, quantities):
        product = db.get_product_by_name(item)
        if product:
            total += product["price"] * qty
    
    set_var(env_vars, "calculated_amount", total)
    return {}

def action_calculate_unit_price(env_vars, input_text, step):
    """计算单价"""
    items = get_var(env_vars, "item_names", [])
    quantities = get_var(env_vars, "quantities", [])
    total_amount = get_var(env_vars, "amount", 0)
    
    if items and quantities and total_amount > 0:
        # 简单平均分配（实际业务会更复杂）
        set_var(env_vars, "unit_price", total_amount / sum(quantities))
    
    return {}


def action_get_product_list(env_vars, input_text, step):
    """获取所有商品列表，用于在创建订单时向用户展示可选商品"""
    products = db.get_all_products()
    if not products:
        set_var(env_vars, "product_list", "（当前暂无商品信息）")
        return {}

    lines = []
    for p in products:
        # 示例：iPhone 15 Pro - ¥8999.0（库存: 100）
        lines.append(f"{p['name']} - ¥{p['price']}（库存: {p['stock']}）")
    set_var(env_vars, "product_list", "\n".join(lines))
    return {}


def action_use_calculated_amount(env_vars, input_text, step):
    """将根据商品和数量计算出的金额写入 amount，形成最终订单金额"""
    calculated = get_var(env_vars, "calculated_amount", 0)
    set_var(env_vars, "amount", calculated)
    return {}

# ==========================================================
# 库存和订单检查相关 Action
# ==========================================================

def action_validate_stock(env_vars, input_text, step):
    """检查库存"""
    items = get_var(env_vars, "item_names", [])
    quantities = get_var(env_vars, "quantities", [])
    
    stock_info = []
    all_available = True
    
    for item, qty in zip(items, quantities):
        result = db.check_stock(item, qty)
        if not result["available"]:
            all_available = False
            stock_info.append(f"{item}: 库存不足(当前{result['current_stock']})")
        else:
            stock_info.append(f"{item}: 库存充足")
    
    set_var(env_vars, "stock_available", all_available)
    set_var(env_vars, "stock_info", "\n".join(stock_info))
    return {}

def action_check_cancel_eligibility(env_vars, input_text, step):
    """检查订单是否可取消"""
    order_id = get_var(env_vars, "order_id")
    result = db.check_order_cancel_eligibility(order_id)
    
    set_var(env_vars, "cancel_eligible", result["eligible"])
    set_var(env_vars, "cancel_reason", result["reason"])
    
    # 如果可取消，计算退款金额
    if result["eligible"]:
        order = db.get_order(order_id)
        if order:
            # 退款金额为订单金额的90%（模拟手续费）
            refund_amount = order["total_amount"] * 0.9
            set_var(env_vars, "cancellation_fee", order["total_amount"] * 0.1)
            set_var(env_vars, "refund_amount", refund_amount)
    
    return {}

def action_check_modify_eligibility(env_vars, input_text, step):
    """检查订单是否可修改"""
    order_id = get_var(env_vars, "order_id")
    result = db.check_order_modify_eligibility(order_id)
    
    set_var(env_vars, "modify_eligible", result["eligible"])
    set_var(env_vars, "modify_reason", result["reason"])
    return {}

def action_check_order_permission(env_vars, input_text, step):
    """检查订单权限"""
    order_id = get_var(env_vars, "order_id")
    user_id = get_var(env_vars, "user_id")
    
    has_permission = db.check_order_ownership(order_id, user_id)
    set_var(env_vars, "has_order_permission", has_permission)
    return {}

# ==========================================================
# 订单操作相关 Action
# ==========================================================

def action_query_orders(env_vars, input_text, step):
    """查询用户订单"""
    user_id = get_var(env_vars, "user_id")
    page = get_var(env_vars, "page", 1)
    page_size = get_var(env_vars, "page_size", 5)
    
    result = db.get_orders_by_user(user_id, page, page_size)
    
    set_var(env_vars, "total_orders", result["total"])
    set_var(env_vars, "total_pages", result["total_pages"])
    
    # 格式化订单信息
    orders_text = []
    for order in result["orders"]:
        try:
            items = json.loads(order["items_json"])
            items_text = ", ".join(items[:2])  # 只显示前两个商品
            if len(items) > 2:
                items_text += f"等{len(items)}件商品"
        except:
            items_text = order.get("items_json", "N/A")
        
        orders_text.append(
            f"{order['order_id']}: {items_text} - ¥{order['total_amount']} - {order['status']}"
        )
    
    if orders_text:
        set_var(env_vars, "orders", "\n".join(orders_text))
    else:
        set_var(env_vars, "orders", "暂无订单")
    
    return {}

def action_count_orders(env_vars, input_text, step):
    """统计订单数量"""
    user_id = get_var(env_vars, "user_id")
    result = db.get_orders_by_user(user_id, 1, 1)  # 只获取总数
    
    set_var(env_vars, "order_count", result["total"])
    return {}

def action_query_order_status(env_vars, input_text, step):
    """查询订单状态"""
    order_id = get_var(env_vars, "order_id")
    order = db.get_order(order_id)
    
    if order:
        set_var(env_vars, "order_status", order["status"])
        set_var(env_vars, "status_detail", f"订单总金额: ¥{order['total_amount']}")
        
        # 预估送达时间
        if order.get("estimated_delivery"):
            delivery_time = datetime.fromisoformat(order["estimated_delivery"])
            set_var(env_vars, "estimated_delivery", delivery_time.strftime("%Y-%m-%d"))
        
        # 更新时间
        if order.get("updated_at"):
            updated_time = datetime.fromisoformat(order["updated_at"])
            set_var(env_vars, "updated_at", updated_time.strftime("%Y-%m-%d %H:%M"))
    
    return {}

def action_get_order_detail(env_vars, input_text, step):
    """获取订单详情"""
    order_id = get_var(env_vars, "order_id")
    order = db.get_order(order_id)
    
    if order:
        # 商品详情
        items_text = []
        for item, qty in zip(order["items"], order["quantities"]):
            product = db.get_product_by_name(item)
            price = product["price"] if product else "N/A"
            items_text.append(f"{item} × {qty} (单价: ¥{price})")
        
        set_var(env_vars, "item_name", ", ".join(order["items"]))
        set_var(env_vars, "quantity", ", ".join(map(str, order["quantities"])))
        set_var(env_vars, "amount", order["total_amount"])
        set_var(env_vars, "order_status", order["status"])
        set_var(env_vars, "created_at", 
                datetime.fromisoformat(order["created_at"]).strftime("%Y-%m-%d %H:%M"))
        set_var(env_vars, "item_details", "\n".join(items_text))
    
    return {}

def action_get_order_owner(env_vars, input_text, step):
    """获取订单所有者"""
    order_id = get_var(env_vars, "order_id")
    order = db.get_order(order_id)
    
    if order:
        user = db.get_user(order["user_id"])
        if user:
            set_var(env_vars, "order_owner_name", user["name"])
            set_var(env_vars, "order_owner_phone", user["phone"])
    
    return {}

def action_create_order(env_vars, input_text, step):
    """创建订单"""
    order_data = {
        "user_id": get_var(env_vars, "user_id"),
        "items": get_var(env_vars, "item_names", []),
        "quantities": get_var(env_vars, "quantities", []),
        "total_amount": get_var(env_vars, "amount", 0),
        "address": get_var(env_vars, "address", ""),
        "phone": get_var(env_vars, "phone", ""),
        "estimated_delivery": datetime.now() + timedelta(days=3)
    }
    
    try:
        order_id = db.create_order(order_data)
        set_var(env_vars, "order_id", order_id)
        set_var(env_vars, "order_status", "pending")
        
        # 记录日志
        db.log_operation(
            order_data["user_id"],
            "create_order",
            f"创建订单 {order_id}, 金额: ¥{order_data['total_amount']}"
        )
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        set_var(env_vars, "order_create_error", str(e))
    
    return {}

def action_cancel_order(env_vars, input_text, step):
    """取消订单"""
    order_id = get_var(env_vars, "order_id")
    refund_amount = get_var(env_vars, "refund_amount")
    
    try:
        success = db.cancel_order(order_id, refund_amount)
        set_var(env_vars, "cancel_success", success)
        
        if success:
            # 设置退款信息
            set_var(env_vars, "refund_status", "processing")
            set_var(env_vars, "refund_eta", "3-7个工作日")
            
            # 记录日志
            user_id = get_var(env_vars, "user_id", "unknown")
            db.log_operation(
                user_id,
                "cancel_order",
                f"取消订单 {order_id}, 退款金额: ¥{refund_amount}"
            )
    except Exception as e:
        logger.error(f"取消订单失败: {e}")
        set_var(env_vars, "cancel_success", False)
        set_var(env_vars, "cancel_error", str(e))
    
    return {}

def action_update_order_address(env_vars, input_text, step):
    """更新订单地址"""
    order_id = get_var(env_vars, "order_id")
    address = get_var(env_vars, "address")
    
    success = db.update_order_address(order_id, address)
    set_var(env_vars, "update_success", success)
    
    if success:
        db.log_operation(
            get_var(env_vars, "user_id", "unknown"),
            "update_order_address",
            f"更新订单 {order_id} 地址为: {address}"
        )
    
    return {}

def action_update_order_phone(env_vars, input_text, step):
    """更新订单电话"""
    order_id = get_var(env_vars, "order_id")
    phone = get_var(env_vars, "phone")
    
    success = db.update_order_phone(order_id, phone)
    set_var(env_vars, "update_success", success)
    
    if success:
        db.log_operation(
            get_var(env_vars, "user_id", "unknown"),
            "update_order_phone",
            f"更新订单 {order_id} 电话为: {phone}"
        )
    
    return {}

def action_validate_delivery_time(env_vars, input_text, step):
    """验证配送时间"""
    from datetime import datetime
    
    try:
        # 尝试解析时间
        delivery_time = datetime.strptime(input_text, "%Y-%m-%d %H:%M")
        set_var(env_vars, "delivery_time", delivery_time.isoformat())
        set_var(env_vars, "delivery_time_valid", True)
    except ValueError:
        set_var(env_vars, "delivery_time_valid", False)
    
    return {}

def action_update_order_delivery_time(env_vars, input_text, step):
    """更新订单配送时间"""
    order_id = get_var(env_vars, "order_id")
    delivery_time = get_var(env_vars, "delivery_time")
    
    if delivery_time:
        success = db.update_order_delivery_time(order_id, delivery_time)
        set_var(env_vars, "update_success", success)
        
        if success:
            db.log_operation(
                get_var(env_vars, "user_id", "unknown"),
                "update_order_delivery_time",
                f"更新订单 {order_id} 配送时间为: {delivery_time}"
            )
    
    return {}    

def action_process_refund(env_vars, input_text, step):
    """处理退款"""
    order_id = get_var(env_vars, "order_id")
    refund_amount = get_var(env_vars, "refund_amount")
    
    # 这里模拟退款处理，实际业务需要调用支付接口
    set_var(env_vars, "refund_processed", True)
    set_var(env_vars, "refund_status", "processing")
    set_var(env_vars, "refund_message", "退款申请已提交")
    
    return {}

# ==========================================================
# 退款相关 Action
# ==========================================================

def action_get_refund_status(env_vars, input_text, step):
    """获取退款状态"""
    order_id = get_var(env_vars, "order_id")
    refund = db.get_refund_status(order_id)
    
    if refund:
        set_var(env_vars, "refund_status", refund["status"])
        set_var(env_vars, "refund_amount", refund["amount"])
        set_var(env_vars, "refund_reason", refund.get("reason", ""))
        set_var(env_vars, "refund_updated_at", 
                datetime.fromisoformat(refund["created_at"]).strftime("%Y-%m-%d %H:%M"))
    else:
        set_var(env_vars, "refund_status", "no_refund")
    
    return {}

# ==========================================================
# 分页相关 Action
# ==========================================================

def action_increment_var(env_vars, input_text, step):
    """变量自增"""
    var_name = step.action_args[0] if step.action_args else "page"
    current_value = get_var(env_vars, var_name, 0)
    set_var(env_vars, var_name, current_value + 1)
    return {}

def action_decrement_var(env_vars, input_text, step):
    """变量自减"""
    var_name = step.action_args[0] if step.action_args else "page"
    current_value = get_var(env_vars, var_name, 1)
    if current_value > 1:
        set_var(env_vars, var_name, current_value - 1)
    return {}

def action_validate_page_range(env_vars, input_text, step):
    """验证页码范围"""
    page = get_var(env_vars, "page", 1)
    total_pages = get_var(env_vars, "total_pages", 1)
    
    if page < 1:
        set_var(env_vars, "page", 1)
    elif page > total_pages:
        set_var(env_vars, "page", total_pages)
    
    return {}

# ==========================================================
# 通知和日志相关 Action
# ==========================================================

def action_send_order_notification(env_vars, input_text, step):
    """发送订单通知（模拟）"""
    order_id = get_var(env_vars, "order_id")
    user_id = get_var(env_vars, "user_id")
    
    logger.info(f"[NOTIFICATION] 订单 {order_id} 创建成功，已通知用户 {user_id}")
    return {}

def action_send_cancellation_notification(env_vars, input_text, step):
    """发送取消通知（模拟）"""
    order_id = get_var(env_vars, "order_id")
    
    logger.info(f"[NOTIFICATION] 订单 {order_id} 已取消，已通知用户")
    return {}

def action_log_access(env_vars, input_text, step):
    """记录访问日志"""
    log_text = " ".join(step.action_args) if step.action_args else "用户访问"
    user_id = get_var(env_vars, "user_id", "anonymous")
    
    db.log_operation(user_id, "access", log_text)
    logger.info(f"[ACCESS] {user_id}: {log_text}")
    return {}

def action_log_order(env_vars, input_text, step):
    """记录订单日志"""
    log_text = " ".join(step.action_args) if step.action_args else "订单操作"
    user_id = get_var(env_vars, "user_id", "anonymous")
    
    db.log_operation(user_id, "order", log_text)
    logger.info(f"[ORDER_LOG] {user_id}: {log_text}")
    return {}

def action_log_transfer(env_vars, input_text, step):
    """记录转接日志"""
    log_text = " ".join(step.action_args) if step.action_args else "转接客服"
    user_id = get_var(env_vars, "user_id", "anonymous")
    
    db.log_operation(user_id, "transfer", log_text)
    logger.info(f"[TRANSFER] {user_id}: {log_text}")
    return {}

def action_log_exit(env_vars, input_text, step):
    """记录退出日志"""
    log_text = " ".join(step.action_args) if step.action_args else "用户退出"
    user_id = get_var(env_vars, "user_id", "anonymous")
    
    db.log_operation(user_id, "exit", log_text)
    logger.info(f"[EXIT] {user_id}: {log_text}")
    return {}

# ==========================================================
# 基础 Action（保留原有）
# ==========================================================

def action_local_set_var(env_vars, input_text, step):
    """设置本地变量"""
    varname = step.action_args[0] if step.action_args else "_input"
    set_var(env_vars, varname, input_text)
    return {}

def action_set_var(env_vars, input_text, step):
    """设置变量"""
    if len(step.action_args) >= 2:
        varname = step.action_args[0]
        value = step.action_args[1]
        
        # 尝试解析为数字
        try:
            if '.' in value:
                value = float(value)
            else:
                value = int(value)
        except:
            pass  # 保持字符串
        
        set_var(env_vars, varname, value)
    return {}

def action_generate_order_id(env_vars, input_text, step):
    """生成订单号"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    order_id = f"ORD{timestamp}"
    set_var(env_vars, "order_id", order_id)
    return {}


# ==========================================================
# 用户余额相关 Action（适配 user_service.dsl）
# ==========================================================

def _parse_amount_from_env(env_vars, key: str = "amount") -> float:
    """从 env_vars[key] 中解析金额，失败则返回 None"""
    raw = get_var(env_vars, key)
    if raw is None:
        return None
    # 允许是数字或字符串
    if isinstance(raw, (int, float)):
        return float(raw)
    m = re.search(r'(\d+(\.\d+)?)', str(raw))
    if not m:
        return None
    return float(m.group(1))


def action_increase_balance(env_vars, input_text, step):
    """充值：根据 user_id 和 amount 为用户增加余额"""
    user_id = get_var(env_vars, "user_id")
    amount = _parse_amount_from_env(env_vars, "amount")

    if not user_id or amount is None or amount <= 0:
        set_var(env_vars, "recharge_success", False)
        set_var(env_vars, "recharge_message", "充值金额无效或用户不存在")
        return {}

    result = db.change_user_balance(user_id, amount)
    if result["success"]:
        set_var(env_vars, "balance", result["new_balance"])
        set_var(env_vars, "recharge_success", True)
        set_var(env_vars, "recharge_message", "充值成功")
    else:
        # 对充值来说，目前只有“用户不存在”这类错误
        set_var(env_vars, "recharge_success", False)
        set_var(env_vars, "recharge_message", result.get("reason", "充值失败"))

    return {}


def action_decrease_balance(env_vars, input_text, step):
    """取款：根据 user_id 和 amount 为用户扣减余额

    通过 env_vars['withdraw_success'] / env_vars['withdraw_message'] 暴露结果，
    同时更新 env_vars['balance'] 为当前余额。
    """
    user_id = get_var(env_vars, "user_id")
    amount = _parse_amount_from_env(env_vars, "amount")

    if not user_id or amount is None or amount <= 0:
        set_var(env_vars, "withdraw_success", False)
        set_var(env_vars, "withdraw_message", "取款金额无效或用户不存在")
        return {}

    # 负数代表扣减
    result = db.change_user_balance(user_id, -amount)
    if result["success"]:
        set_var(env_vars, "balance", result["new_balance"])
        set_var(env_vars, "withdraw_success", True)
        set_var(env_vars, "withdraw_message", "取款成功")
    else:
        # 可能是余额不足或用户不存在
        set_var(env_vars, "withdraw_success", False)
        set_var(env_vars, "withdraw_message", result.get("reason", "取款失败"))
        # 失败时也把当前余额返回给 DSL
        if result.get("new_balance") is not None:
            set_var(env_vars, "balance", result["new_balance"])

    return {}


def action_query_user(env_vars, input_text, step):
    """查询用户信息（适配 user_service.dsl 的 QueryUser）"""
    user_id = get_var(env_vars, "user_id")
    if not user_id:
        # 尝试从最近输入中取
        user_id = env_vars.get("_last_input")

    user = db.get_user(user_id) if user_id else None
    if not user:
        set_var(env_vars, "user_name", "未知用户")
        set_var(env_vars, "balance", 0)
    else:
        set_var(env_vars, "user_id", user["user_id"])
        set_var(env_vars, "user_name", user["name"])
        set_var(env_vars, "balance", user["balance"])

    return {}
# ==========================================================
# Action 分发表
# ==========================================================
ACTION_TABLE = {
    # 输入验证
    "ValidateUserInput": action_validate_user_input,
    "ValidateOrderId": action_validate_order_id,
    "ValidateItemName": action_validate_item_name,
    "ValidateQuantity": action_validate_quantity,
    "ValidateAmount": action_validate_amount,
    "ValidateAddress": action_validate_address,
    "ValidatePhone": action_validate_phone,
    
    # 验证检查
    "VerifyUserExists": action_verify_user_exists,
    "VerifyOrderExists": action_verify_order_exists,
    "CheckOrderPermission": action_check_order_permission,
    "CheckCancelEligibility": action_check_cancel_eligibility,
    "CheckModifyEligibility": action_check_modify_eligibility,
    
    # 数据处理
    "ParseItems": action_parse_items,
    "ParseQuantities": action_parse_quantities,
    "MatchItemsQuantities": action_match_items_quantities,
    "CalculateUnitPrice": action_calculate_unit_price,
    "GetProductList": action_get_product_list,
    "UseCalculatedAmount": action_use_calculated_amount,
    
    # 库存检查
    "ValidateStock": action_validate_stock,
    
    # 订单查询
    "QueryOrders": action_query_orders,
    "QueryOrderStatus": action_query_order_status,
    "GetOrderDetail": action_get_order_detail,
    "GetOrderOwner": action_get_order_owner,
    "CountOrders": action_count_orders,
    
    # 订单操作
    "CreateOrder": action_create_order,
    "CancelOrder": action_cancel_order,
    "UpdateOrderAddress": action_update_order_address,
    "ProcessRefund": action_process_refund,
    "UpdateOrderPhone": action_update_order_phone,
    "ValidateDeliveryTime": action_validate_delivery_time,
    "UpdateOrderDeliveryTime": action_update_order_delivery_time,

    # 退款操作
    "GetRefundStatus": action_get_refund_status,
    
    # 分页操作
    "IncrementVar": action_increment_var,
    "DecrementVar": action_decrement_var,
    "ValidatePageRange": action_validate_page_range,
    
    # 通知和日志
    "SendOrderNotification": action_send_order_notification,
    "SendCancellationNotification": action_send_cancellation_notification,
    "LogAccess": action_log_access,
    "LogOrder": action_log_order,
    "LogTransfer": action_log_transfer,
    "LogExit": action_log_exit,
    
    # 基础操作（保留）
    "LocalSetVar": action_local_set_var,
    "SetVar": action_set_var,
    "GenerateOrderId": action_generate_order_id,
    
    # 旧的Action（兼容）
    "Compute": lambda env_vars, input_text, step: {},
    "QueryUser": action_query_user,
    "IncreaseBalance": action_increase_balance,
    "DecreaseBalance": action_decrease_balance,
    "Log": action_log_access,
}