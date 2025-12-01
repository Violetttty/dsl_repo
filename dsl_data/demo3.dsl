# demo3.dsl
# 流程：问候 → 意图识别（查询/投诉/人工） → 子流程 → 结束

Step S1
Speak "您好，这里是在线客服，请问您需要什么帮助？（查询订单 / 投诉 / 转人工）"
Listen 1 15
Branch "查询订单" S2
Branch "投诉" S5
Branch "人工" S9
Silence S1
Default S1

# --- 订单查询流程 ---
Step S2
Speak "请告诉我您的订单号是多少？"
Listen 1 20
Branch "订单" S3
Silence S2
Default S10

Step S3
Speak "订单号 $order 已查询，正在为您获取最新状态……"
Default S4

Step S4
Speak "您的订单目前状态：已发货，正在配送中。还有其他需要帮忙的吗？（是/否）"
Listen 1 10
Branch "是" S1
Branch "否" S10
Default S1

# --- 投诉流程 ---
Step S5
Speak "请描述一下您的投诉内容，我会为您记录。"
Listen 1 20
Default S6

Step S6
Speak "已记录投诉内容：$complaint。请问是否需要提交到后台处理？（确认/取消）"
Listen 1 10
Branch "确认" S7
Branch "取消" S8
Silence S10
Default S6

Step S7
Speak "投诉已成功提交，我们会在 24 小时内处理。"
Exit

Step S8
Speak "已取消投诉，如仍需帮助可继续告诉我。"
Default S1

# --- 转人工 ---
Step S9
Speak "正在为您转接人工服务，请稍候……"
Exit

# --- 结束 ---
Step S10
Speak "感谢使用我们的服务，祝您生活愉快～"
Exit
