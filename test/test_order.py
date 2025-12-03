# auto_test.py
import sys
import os
import time
from io import StringIO
from typing import List, Dict, Any, Callable
import re

# 添加src到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dsl_parser import parse_text, Script
from src.interpreter import run_interpreter

class DSLTester:
    """DSL脚本自动测试器"""
    
    def __init__(self, dsl_file_path: str):
        """
        初始化测试器
        
        Args:
            dsl_file_path: DSL脚本文件路径
        """
        self.dsl_file_path = dsl_file_path
        self.test_cases = []
        self.results = []
        
    def load_dsl(self) -> Script:
        """加载并解析DSL脚本"""
        with open(self.dsl_file_path, 'r', encoding='utf-8') as f:
            dsl_content = f.read()
        
        return parse_text(dsl_content)
    
    def add_test_case(self, name: str, inputs: List[str], 
                     expected_outputs: List[str] = None,
                     expected_vars: Dict[str, Any] = None,
                     description: str = ""):
        """
        添加测试用例
        
        Args:
            name: 测试用例名称
            inputs: 模拟的用户输入列表
            expected_outputs: 期望的输出列表（可选）
            expected_vars: 期望的环境变量（可选）
            description: 测试描述
        """
        self.test_cases.append({
            'name': name,
            'inputs': inputs,
            'expected_outputs': expected_outputs or [],
            'expected_vars': expected_vars or {},
            'description': description,
            'inputs_index': 0
        })
    
    def create_input_provider(self, test_case: Dict) -> Callable:
        """创建输入提供函数"""
        def input_provider():
            if test_case['inputs_index'] < len(test_case['inputs']):
                input_text = test_case['inputs'][test_case['inputs_index']]
                test_case['inputs_index'] += 1
                print(f"模拟输入: {input_text}")  # 调试输出
                return input_text
            # 输入用完后返回 None，解释器会立即结束对话，避免在静音分支里死循环
            print("模拟输入: (None)  (测试输入已用完，结束对话)")
            return None
        return input_provider
    
    def capture_output(self, script: Script, input_provider: Callable) -> tuple:
        """
        捕获运行输出
        
        Returns:
            tuple: (输出文本列表, 环境变量字典)
        """
        import io
        from contextlib import redirect_stdout
        
        # 捕获标准输出
        output_capture = io.StringIO()
        
        # 同时需要模拟标准输入
        import sys
        from unittest.mock import patch
        
        # 创建一个模拟输入队列
        input_queue = []
        original_input = input_provider
        
        def mock_input(prompt=""):
            # 从测试用例获取输入
            try:
                result = original_input()
                print(f"\n[测试模拟输入] {result}")  # 调试信息
                return result
            except Exception as e:
                print(f"\n[测试输入错误] {e}")
                return ""
        
        # 使用patch模拟input函数
        with patch('builtins.input', side_effect=mock_input):
            # 重定向输出
            with redirect_stdout(output_capture):
                try:
                    # 运行解释器
                    env_vars = run_interpreter(script, mode="mock", input_provider=input_provider)
                except Exception as e:
                    print(f"[测试运行异常] {e}")
                    env_vars = {}
        
        output_text = output_capture.getvalue()
        output_lines = [line.strip() for line in output_text.split('\n') if line.strip()]
        
        # 返回原始文本，便于后续写入日志
        return output_lines, env_vars, output_text
    
    def run_test(self, test_case: Dict, script: Script) -> Dict:
        """运行单个测试用例"""
        print(f"\n{'='*60}")
        print(f"执行测试: {test_case['name']}")
        if test_case['description']:
            print(f"描述: {test_case['description']}")
        print(f"{'='*60}")
        
        # 准备输入提供器
        input_provider = self.create_input_provider(test_case)
        
        # 运行并捕获输出（同时获取完整对话文本用于日志）
        start_time = time.time()
        output_lines, env_vars, raw_output_text = self.capture_output(script, input_provider)
        end_time = time.time()
        
        # 分析结果
        result = {
            'name': test_case['name'],
            'passed': True,
            'output_lines': output_lines,
            'env_vars': env_vars,
            'execution_time': end_time - start_time,
            'errors': [],
            'warnings': []
        }
        
        # 检查期望的输出
        if test_case['expected_outputs']:
            for expected in test_case['expected_outputs']:
                found = False
                for line in output_lines:
                    if expected in line:
                        found = True
                        break
                if not found:
                    result['passed'] = False
                    result['errors'].append(f"未找到期望的输出: '{expected}'")
        
        # 检查期望的环境变量
        if test_case['expected_vars']:
            for var_name, expected_value in test_case['expected_vars'].items():
                actual_value = env_vars.get(var_name)
                if actual_value != expected_value:
                    result['passed'] = False
                    result['errors'].append(
                        f"变量 {var_name} 期望值: {expected_value}, 实际值: {actual_value}"
                    )
        
        # 检查是否有异常退出
        if not output_lines:
            result['passed'] = False
            result['errors'].append("没有输出，可能脚本异常退出")
        
        # 检查是否所有输入都被使用
        unused_inputs = test_case['inputs'][test_case['inputs_index']:]
        if unused_inputs:
            result['warnings'].append(f"未使用的输入: {unused_inputs}")
        
        # 将完整对话（BOT / 模拟输入）写入日志文件
        try:
            log_dir = os.path.join("logs", "test_dialogs")
            os.makedirs(log_dir, exist_ok=True)
            # 根据 DSL 文件名和用例名称生成文件名
            base_name = os.path.splitext(os.path.basename(self.dsl_file_path))[0]
            # 清理测试用例名称中的特殊字符
            safe_name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", test_case['name'])
            log_path = os.path.join(log_dir, f"{base_name}_{safe_name}.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"DSL 文件: {self.dsl_file_path}\n")
                f.write(f"测试用例: {test_case['name']}\n")
                if test_case.get("description"):
                    f.write(f"描述: {test_case['description']}\n")
                f.write("\n===== 对话开始 =====\n")
                f.write(raw_output_text)
                f.write("\n===== 对话结束 =====\n")
        except Exception as e:
            # 日志写入失败时，不影响测试结果，仅打印警告
            print(f"[WARN] 写入对话日志失败: {e}")
        
        return result
    
    def run_all_tests(self) -> List[Dict]:
        """运行所有测试用例"""
        print("🚀 DSL脚本自动化测试开始")
        print(f"测试文件: {self.dsl_file_path}")
        print(f"测试用例数: {len(self.test_cases)}")
        
        # 加载DSL脚本
        try:
            script = self.load_dsl()
            print("✅ DSL脚本加载成功")
        except Exception as e:
            print(f"❌ DSL脚本加载失败: {e}")
            return []
        
        # 运行每个测试用例
        for test_case in self.test_cases:
            result = self.run_test(test_case, script)
            self.results.append(result)
        
        # 生成测试报告
        self.generate_report()
        
        return self.results
    
    def generate_report(self):
        """生成测试报告"""
        print(f"\n{'='*60}")
        print("📊 测试报告")
        print(f"{'='*60}")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        
        print(f"总计测试: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        
        # 详细结果
        for i, result in enumerate(self.results, 1):
            status = "✅ 通过" if result['passed'] else "❌ 失败"
            print(f"\n{i}. {result['name']} - {status}")
            print(f"   执行时间: {result['execution_time']:.2f}秒")
            
            if not result['passed']:
                for error in result['errors']:
                    print(f"   ✗ 错误: {error}")
            
            if result['warnings']:
                for warning in result['warnings']:
                    print(f"   ⚠ 警告: {warning}")
            
            # 显示最后5行输出（可选）
            if result['output_lines']:
                print(f"   最后输出:")
                for line in result['output_lines'][-5:]:
                    print(f"     {line}")
        
        # 总结
        print(f"\n{'='*60}")
        if failed == 0:
            print("🎉 所有测试通过！")
        else:
            print(f"⚠  {failed} 个测试失败，请检查")
        print(f"{'='*60}")

def create_order_service_test_cases(tester: DSLTester):
    """为订单服务DSL创建测试用例（适配当前新版 order_service.dsl）"""
    
    # 1. 帮助功能（从主菜单进入帮助，再返回）
    tester.add_test_case(
        name="测试帮助功能",
        inputs=["3", "返回"],
        expected_outputs=["可用命令", "查看订单", "创建订单", "退出系统"],
        description="测试帮助页面显示和返回功能"
    )
    
    # 2. 查看订单列表（成功）
    tester.add_test_case(
        name="测试查看订单列表-成功",
        inputs=["1", "U1001", "2"],  # 查看订单 → 输入用户ID → 返回主菜单
        expected_outputs=["请输入您的用户ID或手机号码", "您的订单有", "返回主菜单"],
        expected_vars={"user_id": "U1001"},
        description="测试正常查看订单列表流程"
    )
    
    # 3. 查看订单列表（用户不存在）
    tester.add_test_case(
        name="测试查看订单列表-用户不存在",
        inputs=["1", "U9999", "U1001", "2"],  # 用户不存在 → 重新输入正确ID
        expected_outputs=["用户ID不存在", "请重新输入", "您的订单有"],
        description="测试用户不存在时的错误处理和重试"
    )
    
    # 4. 从订单列表进入订单详情，并查询状态后返回主菜单
    tester.add_test_case(
        name="测试从列表查询订单状态-成功",
        inputs=[
            "1",                 # 主菜单 → 查看订单列表
            "U1001",             # 用户ID
            "1",                 # 查看详情
            "ORD20241215001",    # 订单号
            "1",                 # 在详情页选择“查询订单状态”
            "5"                  # 在状态页选择“返回主菜单”
        ],
        expected_outputs=[
            "请输入要查看详情的订单号",
            "订单详情",
            "订单状态是",
            "返回主菜单"
        ],
        expected_vars={"order_id": "ORD20241215001"},
        description="从列表→详情→状态→返回主菜单的完整流程"
    )
    
    # 5. 创建订单（完整流程）
    tester.add_test_case(
        name="测试创建订单-完整流程",
        inputs=[
            "2",              # 主菜单 → 创建订单
            "U1001",          # 用户ID
            "iPhone 15 Pro",  # 商品名称
            "2",              # 数量
            "北京市海淀区",     # 地址
            "13800138001",    # 电话
            "1",              # 确认下单
            "3"               # 返回主菜单
        ],
        expected_outputs=[
            "请输入您的用户ID",
            "请输入商品名称", 
            "请输入商品数量",
            "请输入收货地址",
            "请输入联系电话",
            "请确认订单信息",
            "订单创建成功",
            "返回主菜单"
        ],
        description="测试完整的创建订单流程"
    )
    
    # 6. 创建订单（库存不足）
    tester.add_test_case(
        name="测试创建订单-库存不足",
        inputs=[
            "2",                   # 创建订单
            "U1001",               # 用户ID
            "iPhone 15 Pro",       # 商品名称
            "200",                 # 数量（超过库存）
            "北京市海淀区",          # 地址
            "13800138001",         # 电话
            "1",                   # 确认下单
            "3"                    # 返回主菜单
        ],
        expected_outputs=[
            "抱歉，商品库存不足",
            "返回主菜单"
        ],
        description="测试库存不足时的处理"
    )
    
    # 7. 取消订单资格检查（从状态页发起，订单已发货不可取消）
    tester.add_test_case(
        name="测试取消订单-不可取消",
        inputs=[
            "1",                  # 查看订单
            "U1002",              # 用户ID（有已发货订单 ORD20241215002）
            "1",                  # 查看详情
            "ORD20241215002",     # 订单号
            "1",                  # 在详情页选择“查询订单状态”
            "2"                   # 在状态页选择“取消该订单”
        ],
        expected_outputs=[
            "订单状态是",
            "此订单无法取消",
            "返回主菜单"
        ],
        description="测试已发货订单的取消资格检查"
    )
    
    # 8. 修改订单地址（从状态页进入修改流程）
    tester.add_test_case(
        name="测试修改订单地址",
        inputs=[
            "1",                  # 查看订单
            "U1001",              # 用户ID
            "1",                  # 查看详情
            "ORD20241215001",     # 订单号
            "1",                  # 在详情页选择“查询订单状态”
            "3",                  # 在状态页选择“修改该订单”
            "1",                  # 选择修改收货地址
            "上海市浦东新区",      # 新地址
            "3"                   # 在更新结果页选择“主菜单”
        ],
        expected_outputs=[
            "订单详情",
            "请选择要修改的内容",
            "修改收货地址",
            "收货地址已更新",
            "主菜单"
        ],
        description="测试从状态页进入修改收货地址流程"
    )
    
    # 9. 客服转接（在订单状态页选择联系客服）
    tester.add_test_case(
        name="测试客服转接",
        inputs=[
            "1",                  # 查看订单
            "U1001",              # 用户ID
            "1",                  # 查看详情
            "ORD20241215001",     # 订单号
            "1",                  # 在详情页选择“查询订单状态”
            "4",                  # 在状态页选择“联系客服”
            "返回"                # 从客服转接流程返回主菜单
        ],
        expected_outputs=[
            "订单状态是",
            "转接人工客服",
            "返回主菜单"
        ],
        description="测试从状态页转接人工客服"
    )
    
    # 10. 退出系统
    tester.add_test_case(
        name="测试退出系统",
        inputs=[
            "退出",       # 说退出
            "确认"        # 确认退出
        ],
        expected_outputs=[
            "确认要退出系统吗",
            "感谢使用订单服务，再见"
        ],
        description="测试退出系统流程"
    )
    
    # 11. 静音处理
    tester.add_test_case(
        name="测试静音处理",
        inputs=[
            "",           # 空输入（模拟静音）
            "",           # 再次空输入
            "1"           # 然后选择查看订单
        ],
        expected_outputs=[
            "请问需要什么帮助",
            "请回答"
        ],
        description="测试用户无输入（静音）时的处理"
    )
    
    # 12. 多商品下单
    tester.add_test_case(
        name="测试多商品下单",
        inputs=[
            "2",                           # 创建订单
            "U1001",                       # 用户ID
            "iPhone 15 Pro, MacBook Pro",  # 多个商品
            "1, 1",                        # 对应数量
            "北京市海淀区",                 # 地址
            "13800138001",                 # 电话
            "1",                           # 确认
            "3"                            # 返回主菜单
        ],
        expected_outputs=[
            "请输入商品名称（支持多商品",
            "多个数量用逗号分隔",
            "订单创建成功",
            "iPhone 15 Pro",
            "MacBook Pro"
        ],
        description="测试多个商品同时下单"
    )
    
    # 13. 错误输入恢复
    tester.add_test_case(
        name="测试错误输入恢复",
        inputs=[
            "99",        # 无效选项
            "abc",       # 无效输入
            "",          # 静音
            "帮助",      # 请求帮助
            "返回",      # 返回主菜单
            "1",         # 然后选择查看订单
            "U1001",     # 正常输入用户ID
            "2"          # 返回主菜单
        ],
        expected_outputs=[
            "请问需要什么帮助",
            "请回答",
            "可用命令",
            "您的订单有"
        ],
        description="测试各种错误输入后的恢复能力"
    )
    
    # 14. 创建订单并多次修改信息（商品/数量/地址），然后下单
    tester.add_test_case(
        name="测试创建订单-多次修改信息",
        inputs=[
            "2",                              # 主菜单 → 创建订单
            "U1001",                          # 用户ID
            "iPhone 15 Pro, MacBook Pro",    # 初始商品
            "1, 2",                           # 初始数量
            "北京市海淀区",                    # 初始地址
            "13800138001",                    # 初始电话
            "2",                              # 在确认页选择“修改信息”
            "1",                              # 修改商品
            "MacBook Pro",                    # 新商品列表（只保留一个）
            "2",                              # 再次选择“修改信息”
            "2",                              # 修改数量
            "3",                              # 新数量
            "2",                              # 再次选择“修改信息”
            "3",                              # 修改地址
            "上海市浦东新区",                  # 新地址
            "1",                              # 确认下单
            "3"                               # 从成功页返回主菜单
        ],
        expected_outputs=[
            "请选择要修改的内容",
            "请输入新的商品名称",
            "请输入新的商品数量",
            "请输入新的收货地址",
            "请确认订单信息",
            "订单创建成功",
            "返回主菜单"
        ],
        description="测试在创建订单确认页多次修改商品/数量/地址后仍能正常下单"
    )
    
    # 15. 从订单详情进入状态页，多次刷新后转接客服再返回主菜单
    tester.add_test_case(
        name="测试订单状态-多次刷新并转接客服",
        inputs=[
            "1",                  # 查看订单列表
            "U1001",              # 用户ID
            "1",                  # 查看详情
            "ORD20241215001",     # 订单号
            "1",                  # 在详情页选择“查询订单状态”
            "1",                  # 在状态页选择“刷新状态”
            "1",                  # 再次“刷新状态”
            "4",                  # 选择“联系客服”
            "返回"                # 从客服转接流程返回主菜单
        ],
        expected_outputs=[
            "订单详情",
            "订单状态是",
            "刷新状态",
            "转接人工客服",
            "返回主菜单"
        ],
        description="测试订单状态页多次刷新后转接人工客服的复杂流程"
    )
    
    # 16. 创建订单时用户ID最初不存在，重新输入后恢复并完成下单
    tester.add_test_case(
        name="测试创建订单-用户ID不存在后恢复",
        inputs=[
            "2",              # 主菜单 → 创建订单
            "U9999",          # 错误用户ID
            "取消",           # 返回主菜单
            "U1001",          # 重新输入正确用户ID
            "iPhone 15 Pro",  # 商品名称
            "1",              # 数量
            "北京市海淀区",     # 地址
            "13800138001",    # 电话
            "1",              # 确认下单
            "3"               # 返回主菜单
        ],
        expected_outputs=[
            "用户ID不存在",
            "重新输入",
            "请输入商品名称",
            "请输入商品数量",
            "请确认订单信息",
            "订单创建成功",
            "返回主菜单"
        ],
        description="测试创建订单时用户ID第一次输入错误，修正后仍能正常完成下单"
    )
    
    # 17. 修改订单失败路径：订单状态不可修改（如已发货）
    tester.add_test_case(
        name="测试修改订单-不可修改",
        inputs=[
            "1",                  # 查看订单列表
            "U1002",              # 用户ID（有已发货订单 ORD20241215002）
            "1",                  # 查看详情
            "ORD20241215002",     # 订单号
            "1",                  # 在详情页选择“查询订单状态”
            "3",                  # 在状态页选择“修改该订单”
            "2"                   # 在“此订单无法修改”页选择“返回主菜单”
        ],
        expected_outputs=[
            "订单详情",
            "订单状态是",
            "此订单无法修改",
            "返回主菜单"
        ],
        description="测试订单状态不可修改时的失败路径（从状态页进入修改流程）"
    )


def create_user_service_test_cases(tester: DSLTester):
    """为用户服务DSL创建测试用例（user_service.dsl）"""
    
    # 1. 查询用户（存在）
    tester.add_test_case(
        name="用户服务-查询用户-存在",
        inputs=["查询用户", "U1001"],
        expected_outputs=[
            "请输入您的用户ID",
            "用户ID：U1001",
            "余额"
        ],
        expected_vars={"user_id": "U1001"},
        description="查询已存在用户的信息"
    )
    
    # 2. 查询用户（不存在）
    tester.add_test_case(
        name="用户服务-查询用户-不存在",
        inputs=["查询用户", "U9999"],
        expected_outputs=[
            "请输入您的用户ID",
            "未知用户"
        ],
        description="查询不存在用户时的返回"
    )
    
    # 3. 充值成功
    tester.add_test_case(
        name="用户服务-充值成功",
        inputs=["充值", "U1001", "1000"],
        expected_outputs=[
            "请输入您的用户ID",
            "请输入充值金额",
            "充值成功",
            "当前余额为"
        ],
        description="为用户充值并查看余额"
    )
    
    # 4. 取款成功（余额充足）
    tester.add_test_case(
        name="用户服务-取款成功",
        inputs=["取款", "U1001", "1"],
        expected_outputs=[
            "请输入您的用户ID",
            "请输入取款金额",
            "取款结果：取款成功"
        ],
        description="用户余额充足时取款"
    )
    
    # 5. 取款失败（余额不足）
    tester.add_test_case(
        name="用户服务-取款失败-余额不足",
        inputs=["取款", "U1001", "1000000"],
        expected_outputs=[
            "请输入您的用户ID",
            "请输入取款金额",
            "取款结果：余额不足"
        ],
        description="用户余额不足时取款失败"
    )

def run_interactive_test(dsl_file_path: str):
    """运行交互式测试（手动测试）"""
    print("🎮 交互式测试模式")
    print("输入 'quit' 退出测试")
    print("输入 'restart' 重新开始")
    print("-" * 40)
    
    with open(dsl_file_path, 'r', encoding='utf-8') as f:
        dsl_content = f.read()
    
    script = parse_text(dsl_content)
    
    # 简单的手动测试循环
    while True:
        print("\n选择测试模式:")
        print("1. 完整流程测试")
        print("2. 单步调试")
        print("3. 退出")
        
        choice = input("请输入选择: ").strip()
        
        if choice == "3" or choice.lower() == "quit":
            break
        
        elif choice == "1":
            print("\n🔍 完整流程测试开始")
            print("系统将自动模拟用户输入")
            
            # 模拟一个完整流程
            test_inputs = [
                "1", "U1001", "1", "2", "4",  # 查看订单，翻页，返回
                "3", "U1001", "iPhone 15 Pro", "1", "8999", 
                "北京", "13800138001", "1", "3"  # 创建订单
            ]
            
            input_index = 0
            def test_input_provider():
                nonlocal input_index
                if input_index < len(test_inputs):
                    inp = test_inputs[input_index]
                    input_index += 1
                    print(f"[系统自动输入] {inp}")
                    return inp
                return "退出"
            
            run_interpreter(script, mode="mock", input_provider=test_input_provider)
            
        elif choice == "2":
            print("\n🔧 单步调试模式")
            print("请输入每一步的输入，系统会实时响应")
            print("输入 'back' 返回上一层，'exit' 退出调试")
            
            def debug_input_provider():
                while True:
                    user_input = input("YOU: ").strip()
                    if user_input.lower() == 'exit':
                        return "退出"
                    elif user_input.lower() == 'back':
                        return "返回"
                    elif user_input.lower() == 'restart':
                        return "restart"
                    else:
                        return user_input
            
            result = run_interpreter(script, mode="mock", input_provider=debug_input_provider)
            print(f"\n调试结束，环境变量: {result}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DSL脚本自动化测试工具")
    parser.add_argument("dsl_file", help="DSL脚本文件路径")
    parser.add_argument("--mode", choices=["auto", "interactive", "both"], 
                       default="auto", help="测试模式")
    parser.add_argument("--report", action="store_true", help="生成详细报告")
    parser.add_argument("--quick", action="store_true", help="快速测试（只运行关键测试）")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.dsl_file):
        print(f"❌ 文件不存在: {args.dsl_file}")
        sys.exit(1)
    
    # 自动测试
    if args.mode in ["auto", "both"]:
        tester = DSLTester(args.dsl_file)
        
        # 根据 DSL 文件名决定加载哪一组测试
        base_name = os.path.basename(args.dsl_file)
        if "order_service" in base_name:
            create_order_service_test_cases(tester)
        elif "user_service" in base_name:
            create_user_service_test_cases(tester)
        else:
            print(f"⚠ 未识别的 DSL 类型: {base_name}，将不会添加测试用例")
        
        if args.quick and tester.test_cases:
            # 只运行前几个关键测试
            quick_tests = list(range(min(5, len(tester.test_cases))))
            tester.test_cases = [tester.test_cases[i] for i in quick_tests]
            print("🚀 快速测试模式（只运行前若干关键测试）")
        
        results = tester.run_all_tests()
        
        if args.report:
            # 生成详细报告文件
            with open("test_report.txt", "w", encoding="utf-8") as f:
                f.write(f"DSL测试报告\n")
                f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"测试文件: {args.dsl_file}\n\n")
                
                for result in results:
                    status = "PASS" if result['passed'] else "FAIL"
                    f.write(f"{status} - {result['name']}\n")
                    if result['errors']:
                        f.write("  错误:\n")
                        for error in result['errors']:
                            f.write(f"    {error}\n")
                    f.write("\n")
            
            print(f"📄 详细报告已保存到: test_report.txt")
    
    # 交互式测试
    if args.mode in ["interactive", "both"]:
        run_interactive_test(args.dsl_file)

if __name__ == "__main__":
    main()