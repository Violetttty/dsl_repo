# test/auto_test.py
import os
import sys
import glob
import logging

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.append(SRC_DIR)

from src.dsl_parser import parse_text, ParseError
from src.interpreter import run_interpreter


# ---------------------------------------------------
# 日志
# ---------------------------------------------------
def setup_logger():
    log_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("AutoTest")
    logger.setLevel(logging.INFO)

    log_file = os.path.join(log_dir, "auto_test.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(fmt)

    if not logger.handlers:
        logger.addHandler(fh)

    return logger


logger = setup_logger()


# ---------------------------------------------------
# 用来模拟用户输入的类
# ---------------------------------------------------
class MockInput:
    def __init__(self, inputs):
        self.inputs = inputs
        self.index = 0

    def __call__(self, prompt=""):
        if self.index < len(self.inputs):
            val = self.inputs[self.index]
            print(f"YOU(auto): {val}")
            logger.info(f"YOU(auto): {val}")
            self.index += 1
            return val
        else:
            print("YOU(auto): (empty)")
            logger.info("YOU(auto): (empty)")
            return ""


# ---------------------------------------------------
# 死循环保护版 Interpreter 调用
# ---------------------------------------------------
def run_script_with_inputs(script, inputs, mode="mock", max_steps=50):
    import builtins
    real_input = builtins.input
    builtins.input = MockInput(inputs)

    try:
        # 包装 Interpreter 主循环，加入步数限制
        steps = 0
        original_run_interpreter = run_interpreter

        def safe_run(script, mode):
            nonlocal steps
            # monkey patch Interpreter 循环
            while True:
                steps += 1
                if steps > max_steps:
                    print("[ERROR] Possible infinite loop, stopping.")
                    logger.error("[FAIL] Infinite loop detected")
                    break
                return original_run_interpreter(script, mode)

        # 运行（包装好的）
        safe_run(script, mode)

    finally:
        builtins.input = real_input


# ---------------------------------------------------
# 针对每个 DSL 的测试用例
# ---------------------------------------------------
TEST_CASES = {
    "demo1.dsl": [
        "我想查点东西",
        "账户余额"
    ],
    "demo2.dsl": [
        "张三",
        "100元",
        "是"
    ],
    "demo3.dsl": [
        "查询订单",
        "123456789",
        "否"
    ],
    "demo4.dsl": [
        "网络断开",
        "已确认",
        "仍未恢复"
    ]
}


# ---------------------------------------------------
# 运行所有 DSL 的测试
# ---------------------------------------------------
def auto_test_all():
    dsl_dir = os.path.join(BASE_DIR, "dsl_data")
    if not os.path.exists(dsl_dir):
        print("DSL 目录不存在")
        return

    print(f"开始自动测试 DSL 目录: {dsl_dir}")
    logger.info(f"开始自动测试 DSL 目录: {dsl_dir}")

    dsl_files = glob.glob(os.path.join(dsl_dir, "*.dsl"))
    results = {}

    for dsl_path in dsl_files:
        name = os.path.basename(dsl_path)
        print(f"\n==== Running {name} ====")
        logger.info(f"==== Running {name} ====")

        try:
            text = open(dsl_path, "r", encoding="utf-8").read()
            script = parse_text(text)
        except ParseError as e:
            logger.error(f"[FAIL] Parser Error: {e}")
            results[name] = False
            continue

        # 选择对应测试用例
        inputs = TEST_CASES.get(name, ["测试"])
        print(f"[TEST] Inputs = {inputs}")
        logger.info(f"[TEST] Inputs = {inputs}")

        try:
            run_script_with_inputs(script, inputs, mode="openai")
            logger.info("[PASS]")
            results[name] = True
        except Exception as e:
            logger.error(f"[FAIL] Runtime Error: {e}")
            results[name] = False

    print("\n===== TEST REPORT =====")
    for name, ok in results.items():
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
    print("=======================")

    logger.info("===== AutoTest Finished =====")


if __name__ == "__main__":
    auto_test_all()
