# ============================
# Order Service DSL (Enhanced Version)
# ============================

Step Start
Speak "您好，欢迎使用订单服务！请问需要什么帮助？\n1. 查看我的订单\n2. 创建新订单\n3. 帮助\n4. 退出"
Listen 1 15
Branch 订单列表 OrderList_AskUser
Branch 1 OrderList_AskUser
Branch 创建订单 CreateOrder_AskUser
Branch 2 CreateOrder_AskUser
Branch 帮助 ShowHelp
Branch 3 ShowHelp
Branch 退出 ExitConfirm
Branch 4 ExitConfirm
Silence Start_Reprompt
Default Start_Reprompt

Step Start_Reprompt
Speak "我没有听清，请回答 1-4 中的一个选项，或者直接说出命令名称。请回答。"
Listen 1 15
Branch 订单列表 OrderList_AskUser
Branch 1 OrderList_AskUser
Branch 创建订单 CreateOrder_AskUser
Branch 2 CreateOrder_AskUser
Branch 帮助 ShowHelp
Branch 3 ShowHelp
Branch 4 ExitConfirm
Branch 退出 ExitConfirm
Silence Start_Reprompt
Default ExitConfirm


# --- 帮助页面 ---
Step ShowHelp
Speak "可用命令：\n1. 查看订单 - 查看您的所有订单\n2. 创建订单 - 创建新的订单\n3. 帮助 - 显示此帮助\n4. 退出 - 退出系统\n输入任意符号返回主菜单。"
Listen 1 10
Branch 返回 Start
Branch 1 Start
Default Start


# --- 查询订单列表 ---
Step OrderList_AskUser
Speak "请输入您的用户ID或手机号码："
Listen 1 10
Action ValidateUserInput userId
Action LogAccess "用户尝试查询订单列表"
Branch 取消 Start
Silence OrderList_AskUser
Default OrderList_VerifyUser

Step OrderList_VerifyUser
Action VerifyUserExists $user_id
Branch 用户存在 OrderList_Run
Default OrderList_UserNotFound

Step OrderList_UserNotFound
Speak "用户ID不存在，请重新输入或输入'取消'返回主菜单。"
Listen 1 10
Action ValidateUserInput userId
Branch 取消 Start
Default OrderList_VerifyUser

Step OrderList_Run
Action SetVar page 1
Action SetVar page_size 100
Action QueryOrders
Default OrderList_ShowPage

Step OrderList_ShowPage
Speak "您的订单有：\n" + $orders + "\n\n1. 查看详情\n2. 返回主菜单"
Listen 1 15
Branch 查看详情 OrderList_AskDetail
Branch 1 OrderList_AskDetail
Branch 返回主菜单 Start
Branch 2 Start
Silence Start
Default Start

Step OrderList_AskDetail
Speak "请输入要查看详情的订单号："
Listen 1 10
Action ValidateOrderId
Branch 取消 OrderList_ShowPage
Default OrderList_ShowDetail

Step OrderList_ShowDetail
Action GetOrderDetail
Speak "订单详情：\n订单号：" + $order_id + "\n商品：" + $item_name + "\n数量：" + $quantity + "\n金额：" + $amount + "\n状态：" + $order_status + "\n创建时间：" + $created_at + "\n\n1. 查询订单状态\n2. 取消该订单\n3. 修改该订单\n4. 返回列表\n5. 主菜单"
Listen 1 10
Branch 查询状态 OrderStatus_Run
Branch 1 OrderStatus_Run
Branch 取消 CancelOrder_FromStatus
Branch 2 CancelOrder_FromStatus
Branch 修改 ModifyOrder_FromStatus
Branch 3 ModifyOrder_FromStatus
Branch 返回 OrderList_ShowPage
Branch 4 OrderList_ShowPage
Branch 主菜单 Start
Branch 5 Start
Default Start


# --- 查询订单状态 ---
Step OrderStatus_AskId
Speak "请输入订单号（格式如：ORD20241215001）："
Listen 1 10
Action ValidateOrderId
Action LogAccess "用户查询订单状态"
Branch 取消 Start
Silence OrderStatus_AskId
Default OrderStatus_Check

Step OrderStatus_Check
Action VerifyOrderExists $order_id
Branch 订单存在 OrderStatus_Run
Default OrderStatus_NotFound

Step OrderStatus_NotFound
Speak "订单号不存在，请重新输入或输入'取消'返回主菜单。"
Listen 1 10
Action ValidateOrderId
Branch 取消 Start
Default OrderStatus_Check

Step OrderStatus_Run
Action QueryOrderStatus
Default OrderStatus_Show


Step OrderStatus_Show
Speak "订单 " + $order_id + " 的订单状态是：" + $order_status + "\n\n状态详情：" + $status_detail + "\n最后更新时间：" + $updated_at + "\n\n1. 刷新状态\n2. 取消该订单\n3. 修改该订单\n4. 联系客服\n5. 返回主菜单"
Listen 1 10
Branch 刷新 OrderStatus_Run
Branch 1 OrderStatus_Run
Branch 取消 CancelOrder_FromStatus
Branch 2 CancelOrder_FromStatus
Branch 修改 ModifyOrder_FromStatus
Branch 3 ModifyOrder_FromStatus
Branch 客服 TransferToAgent
Branch 4 TransferToAgent
Branch 返回 Start
Branch 5 Start
Default Start


# --- 创建订单 ---
Step CreateOrder_AskUser
Speak "请输入您的用户ID："
Listen 1 10
Action ValidateUserInput userId
Action VerifyUserExists $user_id
Branch 用户存在 CreateOrder_PrepareItems
Default CreateOrder_UserError

Step CreateOrder_UserError
Speak "用户ID不存在或格式错误，请按任意键返回，重新输入："
Listen 1 10
Action ValidateUserInput userId
Default CreateOrder_AskUser

Step CreateOrder_AskItem
Speak "当前可选商品：\n" + $product_list + "\n\n请输入商品名称（支持多商品，用逗号分隔）："
Listen 1 15
Action ValidateItemName
Action ParseItems
Branch 取消 Start
Silence CreateOrder_AskItem
Default CreateOrder_AskQuantity

Step CreateOrder_PrepareItems
Action GetProductList
Default CreateOrder_AskItem

Step CreateOrder_AskQuantity
Speak "请输入商品数量（多个数量用逗号分隔，与商品对应）："
Listen 1 15
Action ValidateQuantity
Action ParseQuantities
Action MatchItemsQuantities
Branch 取消 Start
Silence CreateOrder_AskQuantity
Default CreateOrder_CalcAmount

Step CreateOrder_CalcAmount
Action UseCalculatedAmount
Default CreateOrder_AskAddress

Step CreateOrder_AskAddress
Speak "请输入收货地址："
Listen 1 20
Action ValidateAddress
Branch 取消 Start
Silence CreateOrder_AskAddress
Default CreateOrder_AskPhone

Step CreateOrder_AskPhone
Speak "请输入联系电话："
Listen 1 10
Action ValidatePhone
Branch 取消 Start
Silence CreateOrder_AskPhone
Default CreateOrder_Confirm

Step CreateOrder_Confirm
Speak "请确认订单信息：\n\n用户ID：" + $user_id + "\n商品：" + $item_name + "\n数量：" + $quantity + "\n总金额：" + $amount + "元\n收货地址：" + $address + "\n联系电话：" + $phone + "\n\n1. 确认下单\n2. 修改信息\n3. 取消"
Listen 1 15
Branch 确认 CreateOrder_Run
Branch 1 CreateOrder_Run
Branch 修改 CreateOrder_ModifySelect
Branch 2 CreateOrder_ModifySelect
Branch 取消 Start
Branch 3 Start
Default Start

Step CreateOrder_ModifySelect
Speak "请选择要修改的内容：\n1. 商品\n2. 数量\n3. 地址\n4. 电话\n5. 返回确认"
Listen 1 10
Branch 商品 CreateOrder_ModifyItem
Branch 1 CreateOrder_ModifyItem
Branch 数量 CreateOrder_ModifyQuantity
Branch 2 CreateOrder_ModifyQuantity
Branch 地址 CreateOrder_ModifyAddress
Branch 3 CreateOrder_ModifyAddress
Branch 电话 CreateOrder_ModifyPhone
Branch 4 CreateOrder_ModifyPhone
Branch 返回 CreateOrder_Confirm
Branch 5 CreateOrder_Confirm
Default CreateOrder_Confirm

Step CreateOrder_ModifyItem
Speak "请输入新的商品名称（支持多商品，用逗号分隔）："
Listen 1 15
Action ValidateItemName
Action ParseItems
Action MatchItemsQuantities
Action UseCalculatedAmount
Branch 取消 CreateOrder_Confirm
Silence CreateOrder_ModifyItem
Default CreateOrder_Confirm

Step CreateOrder_ModifyQuantity
Speak "请输入新的商品数量（多个数量用逗号分隔，与商品对应）："
Listen 1 15
Action ValidateQuantity
Action ParseQuantities
Action MatchItemsQuantities
Action UseCalculatedAmount
Branch 取消 CreateOrder_Confirm
Silence CreateOrder_ModifyQuantity
Default CreateOrder_Confirm

Step CreateOrder_ModifyAddress
Speak "请输入新的收货地址："
Listen 1 20
Action ValidateAddress
Branch 取消 CreateOrder_Confirm
Silence CreateOrder_ModifyAddress
Default CreateOrder_Confirm

Step CreateOrder_ModifyPhone
Speak "请输入新的联系电话："
Listen 1 10
Action ValidatePhone
Branch 取消 CreateOrder_Confirm
Silence CreateOrder_ModifyPhone
Default CreateOrder_Confirm

Step CreateOrder_Run
Action ValidateStock $item_name $quantity
Branch 库存充足 CreateOrder_Process
Default CreateOrder_OutOfStock

Step CreateOrder_OutOfStock
Speak "抱歉，商品库存不足。\n当前库存：" + $stock_info + "\n\n1. 修改数量\n2. 更换商品\n3. 返回主菜单"
Listen 1 10
Branch 修改数量 CreateOrder_AskQuantity
Branch 1 CreateOrder_AskQuantity
Branch 更换商品 CreateOrder_AskItem
Branch 2 CreateOrder_AskItem
Branch 返回 Start
Branch 3 Start
Default Start

Step CreateOrder_Process
Action CreateOrder
Action GenerateOrderId
Action SendOrderNotification
Action LogOrder "创建订单"
Default CreateOrder_Show

Step CreateOrder_Show
Speak "✅ 订单创建成功！\n\n📋 订单信息：\n订单号：" + $order_id + "\n商品：" + $item_name + "\n数量：" + $quantity + "\n总金额：" + $amount + "元\n状态：" + $order_status + "\n预计送达：" + $estimated_delivery + "\n\n1. 查看订单状态\n2. 继续购物\n3. 返回主菜单"
Listen 1 15
Branch 查看状态 OrderStatus_AskId
Branch 1 OrderStatus_AskId
Branch 继续 CreateOrder_AskItem
Branch 2 CreateOrder_AskItem
Branch 返回 Start
Branch 3 Start
Default Start


# --- 取消订单 ---
Step CancelOrder_FromStatus
Action CheckCancelEligibility
Branch 可取消 CancelOrder_Confirm
Default CancelOrder_NotEligible

Step CancelOrder_AskId
Speak "请输入要取消的订单号："
Listen 1 10
Action ValidateOrderId
Action VerifyOrderExists $order_id
Action CheckCancelEligibility
Branch 可取消 CancelOrder_Confirm
Default CancelOrder_NotEligible

Step CancelOrder_NotEligible
Speak "此订单无法取消：\n原因：" + $cancel_reason + "\n当前状态：" + $order_status + "\n\n1. 联系客服\n2. 返回主菜单"
Listen 1 10
Branch 客服 TransferToAgent
Branch 1 TransferToAgent
Branch 返回 Start
Branch 2 Start
Default Start

Step CancelOrder_Confirm
Speak "确认要取消订单 " + $order_id + " 吗？\n商品：" + $item_name + "\n金额：" + $amount + "\n\n取消可能产生手续费：" + $cancellation_fee + "元\n\n1. 确认取消\n2. 不取消"
Listen 1 10
Branch 确认 CancelOrder_Execute
Branch 1 CancelOrder_Execute
Branch 不取消 Start
Branch 2 Start
Default Start

Step CancelOrder_Execute
Action CancelOrder
Action ProcessRefund
Action SendCancellationNotification
Speak "✅ 订单取消成功！\n订单号：" + $order_id + "\n退款金额：" + $refund_amount + "元\n预计到账时间：" + $refund_eta + "\n\n1. 查看退款进度\n2. 返回主菜单"
Listen 1 10
Branch 查看进度 CheckRefundStatus
Branch 1 CheckRefundStatus
Branch 返回 Start
Branch 2 Start
Default Start


# --- 修改订单 ---
Step ModifyOrder_FromStatus
Action CheckModifyEligibility
Branch 可修改 ModifyOrder_Options
Default ModifyOrder_NotEligible

Step ModifyOrder_Select
Speak "请选择要修改的订单号："
Listen 1 10
Action ValidateOrderId
Action VerifyOrderExists $order_id
Action CheckModifyEligibility
Branch 可修改 ModifyOrder_Options
Default ModifyOrder_NotEligible

Step ModifyOrder_NotEligible
Speak "此订单无法修改：\n原因：" + $modify_reason + "\n\n1. 联系客服\n2. 返回主菜单"
Listen 1 10
Branch 客服 TransferToAgent
Branch 1 TransferToAgent
Branch 返回 Start
Branch 2 Start
Default Start

Step ModifyOrder_Options
Speak "订单 " + $order_id + " 当前信息：\n商品：" + $item_name + "\n数量：" + $quantity + "\n地址：" + $address + "\n\n请选择要修改的内容：\n1. 修改收货地址\n2. 修改联系电话\n3. 修改配送时间\n4. 返回主菜单"
Listen 1 10
Branch 地址 ModifyOrder_Address
Branch 1 ModifyOrder_Address
Branch 电话 ModifyOrder_Phone
Branch 2 ModifyOrder_Phone
Branch 时间 ModifyOrder_DeliveryTime
Branch 3 ModifyOrder_DeliveryTime
Branch 返回 Start
Branch 4 Start
Default Start

Step ModifyOrder_Address
Speak "请输入新的收货地址："
Listen 1 20
Action ValidateAddress
Action UpdateOrderAddress
Default ModifyOrder_AddressResult

Step ModifyOrder_AddressResult
Speak "✅ 收货地址已更新！\n\n1. 继续修改其他信息\n2. 返回订单详情\n3. 主菜单"
Listen 1 10
Branch 继续 ModifyOrder_Options
Branch 1 ModifyOrder_Options
Branch 详情 OrderList_ShowDetail
Branch 2 OrderList_ShowDetail
Branch 主菜单 Start
Branch 3 Start
Default Start


Step ModifyOrder_Phone
Speak "请输入新的联系电话："
Listen 1 10
Action ValidatePhone
Action UpdateOrderPhone
Default ModifyOrder_PhoneResult

Step ModifyOrder_PhoneResult
Speak "✅ 联系电话已更新！\n\n1. 继续修改其他信息\n2. 返回订单详情\n3. 主菜单"
Listen 1 10
Branch 继续 ModifyOrder_Options
Branch 1 ModifyOrder_Options
Branch 详情 OrderList_ShowDetail
Branch 2 OrderList_ShowDetail
Branch 主菜单 Start
Branch 3 Start
Default Start

Step ModifyOrder_DeliveryTime
Speak "请输入新的配送时间（格式：YYYY-MM-DD HH:MM）："
Listen 1 10
Action ValidateDeliveryTime
Action UpdateOrderDeliveryTime
Default ModifyOrder_DeliveryTimeResult

Step ModifyOrder_DeliveryTimeResult
Speak "✅ 配送时间已更新！\n\n1. 继续修改其他信息\n2. 返回订单详情\n3. 主菜单"
Listen 1 10
Branch 继续 ModifyOrder_Options
Branch 1 ModifyOrder_Options
Branch 详情 OrderList_ShowDetail
Branch 2 OrderList_ShowDetail
Branch 主菜单 Start
Branch 3 Start
Default Start

# --- 客服转接 ---
Step TransferToAgent
Speak "正在为您转接人工客服...\n（如果需要其他帮助，请说'返回'）"
Listen 1 30
Action LogTransfer "转接人工客服"
Branch 返回 Start
Silence TransferToAgent
Default TransferToAgent_Waiting

Step TransferToAgent_Waiting
Speak "客服忙线中，请稍候...\n预计等待时间：" + $wait_time + "分钟\n\n1. 继续等待\n2. 返回主菜单"
Listen 1 10
Branch 继续 TransferToAgent
Branch 1 TransferToAgent
Branch 返回 Start
Branch 2 Start
Default TransferToAgent


# --- 退出确认 ---
Step ExitConfirm
Speak "确认要退出系统吗？"
Listen 1 5
Branch 确认 ExitSystem
Branch 是 ExitSystem
Branch 不 Start
Branch 否 Start
Default Start

Step ExitSystem
Speak "感谢使用订单服务，再见！"
Action LogExit "用户退出系统"
Exit


# --- 其他功能 ---
Step CheckRefundStatus
Action GetRefundStatus
Speak "退款进度：\n订单号：" + $order_id + "\n退款金额：" + $refund_amount + "\n状态：" + $refund_status + "\n最后更新：" + $refund_updated_at + "\n\n1. 刷新状态\n2. 联系客服\n3. 返回主菜单"
Listen 1 10
Branch 刷新 CheckRefundStatus
Branch 1 CheckRefundStatus
Branch 客服 TransferToAgent
Branch 2 TransferToAgent
Branch 返回 Start
Branch 3 Start
Default Start