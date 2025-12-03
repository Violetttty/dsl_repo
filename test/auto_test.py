"""
auto_test.py

统一自动测试入口脚本：

- 集成 DSL 解析器单元测试（`test_parser.py`）
- 集成 意图识别自动测试（`test_intent_single.py`，只跑自动部分）
- 集成 DSL 对话流程测试（`test_order.py` 中的 DSLTester + 两个业务 DSL）
- 可选：LLM 环境连通性测试（`test_env.py`，通过子进程执行）
"""

import argparse
import os
import sys
import time
from typing import Any, Dict, List

# 保证项目根目录在 sys.path 中，便于以 test.xxx 形式导入
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 本项目内部测试模块
import test.test_parser as parser_tests  # type: ignore
import test.test_intent_single as intent_tests  # type: ignore
from test.test_order import (  # type: ignore
    DSLTester,
    create_order_service_test_cases,
    create_user_service_test_cases,
)


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "auto_test.log")

os.makedirs(LOG_DIR, exist_ok=True)


# =======================================================
# 解析器测试
# =======================================================
def run_parser_suite() -> List[Dict[str, Any]]:
    """运行 dsl_parser 的单元测试集合（来自 test_parser.py）"""
    print("\n================ 解析器测试 (test_parser) ================")

    cases = [
        ("test_valid_file", parser_tests.test_valid_file),
        ("test_references", parser_tests.test_references),
        ("test_invalid_keyword", parser_tests.test_invalid_keyword),
        ("test_missing_step_name", parser_tests.test_missing_step_name),
        ("test_expression_parsing", parser_tests.test_expression_parsing),
        ("test_listen_parse", parser_tests.test_listen_parse),
        ("test_exit_parse", parser_tests.test_exit_parse),
        ("test_branch_parse", parser_tests.test_branch_parse),
    ]

    results: List[Dict[str, Any]] = []

    for name, fn in cases:
        print(f"\n--- {name} ---")
        try:
            fn()
            results.append({"name": f"parser::{name}", "passed": True, "error": ""})
        except Exception as e:  # noqa: BLE001
            results.append(
                {"name": f"parser::{name}", "passed": False, "error": str(e)}
            )

    return results


# =======================================================
# 意图识别测试
# =======================================================
def run_intent_suite() -> List[Dict[str, Any]]:
    """运行意图识别的自动测试（只跑 mock 模式的 auto tests）"""
    print("\n================ 意图识别测试 (test_intent_single) ================")

    results: List[Dict[str, Any]] = []
    name = "intent::auto_tests"
    try:
        # 只调用自动测试部分，不进入交互模式
        intent_tests.run_auto_tests()
        results.append({"name": name, "passed": True, "error": ""})
    except Exception as e:  # noqa: BLE001
        results.append({"name": name, "passed": False, "error": str(e)})

    return results


# =======================================================
# DSL 对话流程测试（订单 / 用户服务）
# =======================================================
def run_dsl_suite(quick: bool = False) -> List[Dict[str, Any]]:
    """
    运行 DSL 脚本层面的自动对话测试：
    - dsl_data/order_service.dsl
    - dsl_data/user_service.dsl
    """
    print("\n================ DSL 对话流程测试 (test_order) ================")

    dsl_configs = [
        ("dsl_data/order_service.dsl", create_order_service_test_cases),
        ("dsl_data/user_service.dsl", create_user_service_test_cases),
    ]

    all_results: List[Dict[str, Any]] = []

    for dsl_file, create_cases_fn in dsl_configs:
        if not os.path.exists(dsl_file):
            msg = f"DSL 文件不存在: {dsl_file}"
            print(f"[ERROR] {msg}")
            all_results.append(
                {"name": f"dsl::{dsl_file}", "passed": False, "error": msg}
            )
            continue

        print(f"\n>>> 运行 DSLTester 用例: {dsl_file}")
        tester = DSLTester(dsl_file)
        create_cases_fn(tester)

        if quick and tester.test_cases:
            # 只运行前若干关键测试
            tester.test_cases = tester.test_cases[:5]
            print("（quick 模式，仅运行前若干关键用例）")

        results = tester.run_all_tests()

        for r in results:
            name = r.get("name", "")
            passed = bool(r.get("passed"))
            errors = r.get("errors") or []
            err_msg = "; ".join(errors)
            all_results.append(
                {
                    "name": f"dsl::{os.path.basename(dsl_file)}::{name}",
                    "passed": passed,
                    "error": err_msg,
                }
            )

    return all_results


# =======================================================
# 可选：LLM 环境连通性测试（dashscope / Qwen）
# =======================================================
def run_env_check() -> List[Dict[str, Any]]:
    """
    通过子进程运行 test_env.py，检查 DASHSCOPE_API_KEY / dashscope 是否配置正确。
    没有 test_env.py 时视为跳过（不算失败）。
    """
    print("\n================ LLM 环境检查 (test_env) ================")

    script_path = os.path.join(os.path.dirname(__file__), "test_env.py")
    results: List[Dict[str, Any]] = []

    if not os.path.exists(script_path):
        print("未找到 test_env.py，跳过 LLM 环境检查。")
        return results

    import subprocess  # noqa: PLC0415

    name = "env::dashscope_qwen"
    try:
        proc = subprocess.run(  # noqa: S603
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        print(proc.stdout)
        passed = proc.returncode == 0
        results.append(
            {
                "name": name,
                "passed": passed,
                "error": "" if passed else "test_env.py 返回非 0",
            }
        )
    except Exception as e:  # noqa: BLE001
        results.append({"name": name, "passed": False, "error": str(e)})

    return results


# =======================================================
# 主程序：统一调度所有测试
# =======================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="统一自动测试脚本")
    parser.add_argument(
        "--skip-parser", action="store_true", help="跳过 DSL 解析器单元测试"
    )
    parser.add_argument(
        "--skip-intent", action="store_true", help="跳过意图识别自动测试"
    )
    parser.add_argument(
        "--skip-dsl", action="store_true", help="跳过 DSL 对话流程测试"
    )
    parser.add_argument(
        "--quick-dsl",
        action="store_true",
        help="DSL 对话测试只跑前若干关键用例（加快测试速度）",
    )
    parser.add_argument(
        "--with-env", action="store_true", help="额外运行 LLM 环境连通性检查"
    )

    args = parser.parse_args()

    all_results: List[Dict[str, Any]] = []

    start_all = time.time()

    if not args.skip_parser:
        all_results.extend(run_parser_suite())

    if not args.skip_intent:
        all_results.extend(run_intent_suite())

    if not args.skip_dsl:
        all_results.extend(run_dsl_suite(quick=args.quick_dsl))

    if args.with_env:
        all_results.extend(run_env_check())

    elapsed_all = time.time() - start_all

    # 统计并输出总报告
    total = len(all_results)
    passed = sum(1 for r in all_results if r.get("passed"))
    failed = total - passed

    print("\n================ 测试总览 ================")
    print(f"总用例数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总耗时: {elapsed_all:.2f} 秒")

    if failed:
        print("\n未通过用例明细：")
        for r in all_results:
            if not r.get("passed"):
                print(f"  - {r.get('name')}: {r.get('error')}")

    # 写入日志文件（便于课程文档附录使用）
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总用例数: {total}, 通过: {passed}, 失败: {failed}\n\n")
        for r in all_results:
            status = "PASS" if r.get("passed") else "FAIL"
            line = f"[{status}] {r.get('name')}"
            if r.get("error"):
                line += f" | {r.get('error')}"
            f.write(line + "\n")

    print(f"\n📄 详细结果已写入: {LOG_FILE}")


if __name__ == "__main__":
    main()
