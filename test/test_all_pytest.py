"""
test_all_pytest.py

使用 pytest 统一跑一遍项目里的核心自动测试：

- 解析器单元测试（来自 test_parser.py，通过 auto_test.run_parser_suite 包装）
- 意图识别自动测试（auto_test.run_intent_suite）
- DSL 对话流程测试（order_service.dsl / user_service.dsl，auto_test.run_dsl_suite）

这样你既可以：
- 直接运行 `python test/auto_test.py` 做命令行总测，
- 也可以运行 `pytest`，由本文件触发一次“总集成测试”。
"""

from __future__ import annotations

from typing import Any, Dict, List

from test.auto_test import (  # type: ignore
    run_dsl_suite,
    run_intent_suite,
    run_parser_suite,
)


def _collect_all_results() -> List[Dict[str, Any]]:
    """调用 auto_test 中的各个测试子套件，汇总结果。"""
    all_results: List[Dict[str, Any]] = []

    # 1. 解析器测试
    all_results.extend(run_parser_suite())

    # 2. 意图识别测试（mock 自动用例）
    all_results.extend(run_intent_suite())

    # 3. DSL 对话流程测试（订单 / 用户服务，跑全量用例）
    all_results.extend(run_dsl_suite(quick=False))

    return all_results


def test_all_suites_pass() -> None:
    """
    总集成测试：
    - 如果任意一个子用例失败，就让 pytest 报错，并把失败明细打印出来。
    """
    results = _collect_all_results()

    failed = [r for r in results if not r.get("passed")]

    if failed:
        # 拼装一个可读性较好的错误消息
        messages = []
        for r in failed:
            name = r.get("name", "<unknown>")
            error = r.get("error", "")
            messages.append(f"{name}: {error}")

        joined = "\n".join(messages)
        raise AssertionError(f"以下自动测试未通过（pytest 版总集成）：\n{joined}")

