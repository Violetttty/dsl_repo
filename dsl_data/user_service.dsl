# ============================
# User Service DSL
# ============================

Step Start
Speak "您好，请问需要什么服务？（查询用户 / 充值）"
Listen 1 10
Branch 查询用户 QueryUser_AskId
Branch 充值 Recharge_AskId
Default Start

# --- 查询用户 ---
Step QueryUser_AskId
Speak "请输入您的用户ID："
Listen 1 10
Default QueryUser_Run

Step QueryUser_Run
Action LocalSetVar user_id
Action QueryUser
Default QueryUser_Show

Step QueryUser_Show
Speak "用户ID：" + $user_id + "，姓名：" + $user_name + "，余额：" + $balance
Exit


# --- 充值 ---
Step Recharge_AskId
Speak "请输入您的用户ID："
Listen 1 10
Action LocalSetVar user_id
Default Recharge_AskAmount

Step Recharge_AskAmount
Speak "请输入充值金额："
Listen 1 10
Action LocalSetVar amount
Default Recharge_Run

Step Recharge_Run
Action IncreaseBalance
Default Recharge_Show

Step Recharge_Show
Speak "充值成功，当前余额为：" + $balance
Exit
