# simple_test.py
import sys
import os
import time
from unittest.mock import patch
from io import StringIO

# 添加src到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dsl_parser import parse_text
from src.interpreter import run_interpreter

class SimpleDSLTester:
    """简化版DSL测试器"""
    
    def __init__(self, dsl_file_path: str):
        self.dsl_file_path = dsl_file_path
        self.script = None
        self.load_dsl()
    
    def load_dsl(self):
        """加载DSL脚本"""
        with open(self.dsl_file_path, 'r', encoding='utf-8') as f:
            dsl_content = f.read()
        self.script = parse_text(dsl_content)
        print(f"✅ DSL脚本加载成功: {len(self.script.steps)} 个步骤")
    
    def run_test_sequence(self, test_name: str, inputs: list, timeout=10):
        """运行测试序列"""
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print(f"输入序列: {inputs}")
        print(f"{'='*50}")
        
        # 创建输入队列
        input_queue = inputs.copy()
        
        def input_provider():
            if input_queue:
                return input_queue.pop(0)
            return ""  # 没有更多输入时返回空
        
        # 模拟输入
        start_time = time.time()
        
        # 捕获输出
        output_buffer = StringIO()
        
        # 运行解释器
        try:
            env_vars = run_interpreter(self.script, mode="mock", input_provider=input_provider)
            elapsed = time.time() - start_time
            
            print(f"✅ 测试完成 ({elapsed:.2f}秒)")
            print(f"环境变量: {env_vars}")
            
            # 检查是否所有输入都被使用
            if input_queue:
                print(f"⚠ 警告: {len(input_queue)} 个输入未使用: {input_queue}")
            
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_basic_navigation(self):
        """测试基本导航"""
        tests = [
            ("测试帮助页面", ["6", "返回"]),  # 帮助 → 返回
            ("测试退出系统", ["退出", "确认"]),
            ("测试静音恢复", ["", "1", "U1001", "4"]),  # 静音 → 查看订单 → 返回
        ]
        
        results = []
        for name, inputs in tests:
            success = self.run_test_sequence(name, inputs)
            results.append((name, success))
        
        return results
    
    def test_order_operations(self):
        """测试订单操作"""
        tests = [
            ("测试查看订单", ["1", "U1001", "4"]),
            ("测试查询订单状态", ["2", "ORD20241215001", "3"]),
            ("测试创建订单简单", ["3", "U1001", "iPhone", "1", "100", "北京", "13800138001", "1", "3"]),
        ]
        
        results = []
        for name, inputs in tests:
            success = self.run_test_sequence(name, inputs)
            results.append((name, success))
        
        return results

def main():
    if len(sys.argv) < 2:
        print("用法: python simple_test.py <dsl文件路径>")
        sys.exit(1)
    
    dsl_file = sys.argv[1]
    
    if not os.path.exists(dsl_file):
        print(f"❌ 文件不存在: {dsl_file}")
        sys.exit(1)
    
    print("🚀 启动DSL简单测试")
    
    tester = SimpleDSLTester(dsl_file)
    
    # 运行测试
    print("\n📋 运行基本导航测试...")
    nav_results = tester.test_basic_navigation()
    
    print("\n📋 运行订单操作测试...")
    order_results = tester.test_order_operations()
    
    # 统计结果
    all_results = nav_results + order_results
    total = len(all_results)
    passed = sum(1 for _, success in all_results if success)
    
    print(f"\n{'='*50}")
    print("📊 测试总结")
    print(f"{'='*50}")
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    
    if total - passed == 0:
        print("🎉 所有测试通过！")
    else:
        print("⚠ 有测试失败，请检查")
        for name, success in all_results:
            if not success:
                print(f"  ❌ {name}")

if __name__ == "__main__":
    main()