# demo4.dsl
# 流程：诊断网络问题 → 按步骤排查 → 判断修复结果

Step S1
Speak "您好，我是技术支持助手，请问您的问题是哪一类？（网络断开 / 网速慢 / 其它）"
Listen 1 20
Branch "网络断开" S2
Branch "网速慢" S4
Branch "其它" S10
Default S1

# ---- 网络断开排查 ----
Step S2
Speak "请确认路由器电源是否正常？（已确认/未确认）"
Listen 1 10
Branch "已确认" S3
Branch "未确认" S9
Default S2

Step S3
Speak "请重启路由器，再告诉我是否恢复正常？（恢复/仍未恢复）"
Listen 1 10
Branch "恢复" S8
Branch "仍未恢复" S9
Default S3

# ---- 网速慢排查 ----
Step S4
Speak "请问网速变慢有多久了？（几分钟/几小时/几天）"
Listen 1 10
Branch "几分钟" S5
Branch "几小时" S6
Branch "几天" S7
Default S4

Step S5
Speak "可能是临时波动，请稍后再测试是否恢复。"
Exit

Step S6
Speak "建议重启路由器或检查是否有人占用带宽。"
Default S8

Step S7
Speak "建议联系宽带运营商检查线路故障。"
Exit

# ---- 统一修复成功 ----
Step S8
Speak "网络问题已处理完毕！如有需要我随时在～"
Exit

# ---- 仍未修复 / 回到人工 ----
Step S9
Speak "当前无法自动修复，正在转接人工服务……"
Exit

# ---- 其它问题 ----
Step S10
Speak "请描述您的问题，我会尽力为您提供建议。"
Listen 1 20
Default S8
