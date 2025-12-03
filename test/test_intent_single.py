"""
test_intent_single.py

意图识别模块的简单自动化测试 + 交互式单次测试。

- 自动测试部分：使用 mock 模式验证常见输入是否能匹配到正确的分支；
- 交互模式：允许你手动输入一句话，查看在 openai/mock 两种模式下的识别结果。
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(BASE_DIR, "src"))

from src.intent_recognize import recognize_intent  # noqa: E402


def run_auto_tests():
    """运行一组基于 mock 的意图识别测试用例"""
    print("=== Intent Recognizer Auto Tests (mock mode) ===")

    test_cases = [
        # (description, user_input, branches, expected_intent)
        ("精确匹配-查询订单", "我想查询订单", ["查询订单", "投诉", "退款"], "查询订单"),
        ("包含关键词-投诉", "我要投诉一下你们的服务", ["查询订单", "投诉", "退款"], "投诉"),
        ("包含关键词-退款", "想要退款", ["查询订单", "投诉", "退款"], "退款"),
        ("无法匹配-返回 None", "聊聊天", ["查询订单", "投诉", "退款"], None),
    ]

    passed = 0
    for desc, user_input, branches, expected in test_cases:
        result = recognize_intent(user_input, branches, mode="mock")
        ok = result == expected
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {desc} | input='{user_input}' -> {result} (expected={expected})")
        if ok:
            passed += 1

    print(f"\nSummary: {passed}/{len(test_cases)} tests passed.\n")


def run_interactive_single():
    """交互式单次测试：方便你手动输入一句话观察识别结果"""
    print("=== Interactive Intent Test ===")
    branches = ["投诉", "查询订单", "退款", "取消订单", "帮助"]
    print("候选意图：", branches)
    user_input = input("YOU: ").strip()

    # mock 模式
    mock_res = recognize_intent(user_input, branches, mode="mock")
    print(f"[mock] 识别结果：{mock_res}")

    # openai / qwen 模式（如果配置了 DASHSCOPE_API_KEY）
    print("\n尝试使用 openai 模式（qwen），如果没有配置会自动回落到 mock：")
    openai_res = recognize_intent(user_input, branches, mode="openai")
    print(f"[openai] 识别结果：{openai_res}")


if __name__ == "__main__":
    # 先跑一遍自动测试
    run_auto_tests()

    # 再进入交互式单次测试
    run_interactive_single()
