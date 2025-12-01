# 一个最基础的流程：问候 → 分类 → 回复 → 结束

Step welcome
Speak "您好，这里是智能客服，请问有什么可以帮您?"
Listen 5, 20
Branch "投诉", complain
Branch "查询", query
Silence silenceHandler
Default defaultHandler

Step complain
Speak "请问您要投诉什么问题呢?"
Listen 5, 20
Default thanks

Step query
Speak "您想查询什么内容呢？"
Listen 5, 20
Default thanks

Step silenceHandler
Speak "我没有听清，请您再说一遍可以吗？"
Listen 5, 20
Default defaultHandler

Step defaultHandler
Speak "抱歉，我暂时无法理解您的意思。"
Exit

Step thanks
Speak "好的，我已经记录了您的信息，谢谢您的来电，再见"
Exit
