"""
test_order_pytest_wrapper.py

使用 pytest 对 DSLTester 做一层包装，让“自定义 DSL 测试框架 + pytest 集成”更清晰：

- 针对 `dsl_data/order_service.dsl` 和 `dsl_data/user_service.dsl` 分别跑一遍 DSLTester 全量用例；
- 如果有任何一个用例失败，就让 pytest 报错，并在错误信息中附上失败用例名称和错误原因。
"""

import os

from test.test_order import (  # type: ignore
    DSLTester,
    create_order_service_test_cases,
    create_user_service_test_cases,
)


def _run_dsltester_and_assert(dsl_file: str, create_cases_fn):
    """通用封装：跑 DSLTester，检查所有用例是否通过。"""
    assert os.path.exists(dsl_file), f"DSL 文件不存在: {dsl_file}"

    tester = DSLTester(dsl_file)
    create_cases_fn(tester)

    results = tester.run_all_tests()

    failed = [r for r in results if not r.get("passed")]
    if failed:
        # 拼接一个可读性好的错误信息，方便在 pytest 输出里查看
        messages = []
        for r in failed:
            name = r.get("name")
            errors = r.get("errors") or []
            msgs = "; ".join(errors) if errors else "未知错误"
            messages.append(f"{name}: {msgs}")
        joined = "\n".join(messages)
        assert False, f"以下 DSLTester 用例未通过：\n{joined}"


def test_order_service_dsl_all_cases():
    """使用 DSLTester 跑订单服务 DSL 的所有自动化对话用例。"""
    _run_dsltester_and_assert("dsl_data/order_service.dsl", create_order_service_test_cases)


def test_user_service_dsl_all_cases():
    """使用 DSLTester 跑用户服务 DSL 的所有自动化对话用例。"""
    _run_dsltester_and_assert("dsl_data/user_service.dsl", create_user_service_test_cases)


