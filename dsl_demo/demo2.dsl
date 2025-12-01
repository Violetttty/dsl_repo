# demo2.dsl
# 流程：欢迎 → 询问姓名 → 询问充值金额 → 确认 → 完成

Step S1
Speak "您好，我是智能客服，请问怎么称呼您？"
Listen 1 10
Branch "姓名" S2
Default S2

Step S2
Speak "好的，$name，请问您要充值的金额是多少？"
Listen 1 10
Branch "金额" S3
Default S5

Step S3
Speak "收到，已记录充值金额：$amount 元。请确认是否提交？（是/否）"
Listen 1 10
Branch "是" S4
Branch "否" S5
Default S3

Step S4
Speak "您的充值请求金额 $amount 元已提交成功！"
Exit

Step S5
Speak "已取消本次充值请求，如需其它帮助可以继续告诉我哦。"
Exit
