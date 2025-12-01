# auto_test.py
import os
import sys
import argparse
from unittest.mock import patch

from src.dsl_parser import parse_text, ParseError
from src.interpreter import run_interpreter

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "auto_test.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


# =======================================================
# 自动测试输入生成器
# =======================================================
class AutoInput:
    def __init__(self, inputs):
        self.inputs = inputs
        self.index = 0

    def __call__(self, prompt=""):
        if self.index < len(self.inputs):
            value = self.inputs[self.index]
            print(f"YOU(auto): {value}")
            self.index += 1
            return value

        # 超过输入范围 → 返回空
        print("YOU(auto): (empty)")
        return ""


# =======================================================
# 预设测试输入（按业务 DSL）
# =======================================================
PRESET_TEST_SETS = {

    # ----------------------
    # Order Service DSL
    # ----------------------
    "order_service.dsl": [
        # 测试 1：查询订单列表
        ["订单列表", "1001"],

        # 测试 2：查询订单状态
        ["订单状态", "A001"],

        # 测试 3：创建订单
        ["创建订单", "1002", "电脑", "5000"]
    ],

    # ----------------------
    # User Service DSL
    # ----------------------
    "user_service.dsl": [
        # 测试 1：查询用户信息
        ["查询用户", "1001"],

        # 测试 2：充值
        ["充值", "1001", "50"]
    ]
}


# =======================================================
# 运行单次 DSL 测试 （一套测试输入）
# =======================================================
def run_single_test(script_path, auto_inputs):
    log_output = []

    try:
        text = open(script_path, "r", encoding="utf-8").read()
        script = parse_text(text)
    except ParseError as e:
        msg = f"[ERROR] Parse failed in {script_path}: {e}"
        print(msg)
        return msg

    auto_input_obj = AutoInput(auto_inputs)

    log_output.append("\n==============================")
    log_output.append(f"Running script: {script_path}")
    log_output.append(f"Auto inputs: {auto_inputs}")
    log_output.append("==============================\n")

    # Patch input()
    with patch("builtins.input", auto_input_obj):
        try:
            run_interpreter(script, mode="mock")
            log_output.append("[OK] Executed successfully.\n")
        except Exception as e:
            log_output.append(f"[ERROR] Runtime exception: {e}\n")

    return "\n".join(log_output)


# =======================================================
# 主程序：自动选择输入并批量跑测试
# =======================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scripts", nargs="+", help="DSL script paths")
    args = parser.parse_args()

    final_logs = []

    for script_path in args.scripts:
        filename = os.path.basename(script_path)

        if filename not in PRESET_TEST_SETS:
            print(f"[WARN] No preset tests for {filename}, skipping.")
            continue

        test_sets = PRESET_TEST_SETS[filename]

        # 对脚本的每一套测试输入运行一遍
        for test_inputs in test_sets:
            result = run_single_test(script_path, test_inputs)
            final_logs.append(result)

    # 写入日志
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(final_logs))

    print("\n=== Auto Test Finished ===")
    print(f"Logs saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()
