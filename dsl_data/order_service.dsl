# ============================
# Order Service DSL
# ============================

Step Start
Speak "您好，请问需要什么服务？（订单列表 / 订单状态 / 创建订单）"
Listen 1 10
Branch 订单列表 OrderList_AskUser
Branch 订单状态 OrderStatus_AskId
Branch 创建订单 CreateOrder_AskUser
Default Start


# --- 查询订单列表 ---
Step OrderList_AskUser
Speak "请输入您的用户ID："
Listen 1 10
Default OrderList_Run

Step OrderList_Run
Action LocalSetVar user_id
Action QueryOrders
Default OrderList_Show

Step OrderList_Show
Speak "您的订单有：" + $orders
Exit


# --- 查询订单状态 ---
Step OrderStatus_AskId
Speak "请输入订单号："
Listen 1 10
Default OrderStatus_Run

Step OrderStatus_Run
Action LocalSetVar order_id
Action QueryOrderStatus
Default OrderStatus_Show

Step OrderStatus_Show
Speak "订单 " + $order_id + " 的状态是：" + $order_status
Exit


# --- 创建订单 ---
Step CreateOrder_AskUser
Speak "请输入您的用户ID："
Listen 1 10
Default CreateOrder_AskItem

Step CreateOrder_AskItem
Speak "请输入商品名称："
Listen 1 10
Default CreateOrder_AskAmount

Step CreateOrder_AskAmount
Speak "请输入商品金额："
Listen 1 10
Default CreateOrder_Run

Step CreateOrder_Run
Action LocalSetVar amount
# 注意：item_name 也要设置
Action LocalSetVar item_name
# user_id 同样必须设置（由前一步写入）
Action CreateOrder
Default CreateOrder_Show

Step CreateOrder_Show
Speak "订单创建成功！订单号：" + $order_id + "，商品：" + $item_name + "，金额：" + $amount
Exit
