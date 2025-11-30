import sys, os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.append(SRC_DIR)

from intent_recognize import recognize_intent

branch = ["投诉", "查询订单", "退款"]

print("输入内容测试 Qwen 意图识别：")
user_input = input("YOU: ")

result = recognize_intent(user_input, branch, mode="openai")

print("识别结果：", result)
