# interpreter.py
import argparse
import os
import sys
import re
import logging

from src.dsl_parser import parse_text, ParseError, Script, Step
from src.actions import ACTION_TABLE   
from src.intent_recognize import recognize_intent


# ============================
# Logging
# ============================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("interpreter")
logger.setLevel(logging.INFO)

fh = logging.FileHandler(os.path.join(LOG_DIR, "interpreter.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(fh)


# ============================
# Expression evaluation
# ============================
def eval_expression(expr, env_vars: dict) -> str:
    if expr is None:
        return ""
    parts = []
    for it in expr.items:
        if it.is_var:
            parts.append(str(env_vars.get(it.value, "")))
        else:
            parts.append(str(it.value))

    # 将 DSL 文本中的转义换行符 \n 转成真实换行，方便多行展示
    text = "".join(parts)
    text = text.replace("\\n", "\n")
    return text


# ============================
# Variable extraction
# ============================
def populate_vars_from_input(env_vars: dict, script_vars: set, user_input: str):
    if not user_input:
        return

    # If var name looks like amount, extract number
    for v in script_vars:
        name = v.lower()
        if "amount" in name or "money" in name or "金额" in name:
            # 已经有明确的数值就不要被后续输入覆盖
            if v not in env_vars:
                m = re.search(r"(\d+(?:[.,]\d+)?)", user_input)
                if m:
                    env_vars[v] = m.group(1).replace(",", "")
                    return

    # Name-like variable
    for v in script_vars:
        name = v.lower()
        # 避免把 user_id 这种 ID 类字段当成“姓名”来覆盖
        if (("name" in name) or ("姓名" in name)) and not name.endswith("_id"):
            # 如果已经通过显式的 Action（如 VerifyUserExists）写入，就不要再覆盖
            if v not in env_vars:
                env_vars[v] = user_input.strip()
                return

    # default: store raw
    if script_vars:
        # pick any one? no. safer: store to special var
        env_vars["_last_input"] = user_input.strip()


# ============================
# Run Interpreter
# ============================
def run_interpreter(script: Script, mode="mock", input_provider=None):
    """
    input_provider: a function that returns next input (auto_test uses this)
    """
    env_vars = {}
    current_step_id = script.entry
    pending_jump = None

    if current_step_id is None:
        print("Script has no entry step.")
        return

    print(f"--- Starting script (entry: {current_step_id}) ---\n")

    while True:
        step: Step = script.steps.get(current_step_id)
        if step is None:
            print(f"[ERROR] step not found: {current_step_id}")
            logger.error(f"Unknown step id: {current_step_id}")
            break

        # ========== Speak ==========
        if step.speak:
            out = eval_expression(step.speak, env_vars)
            print(f"BOT: {out}")
            logger.info(f"Speak: {out}")

        # ========== Exit ========== 
        if step.is_exit:
            print("[Conversation ended by script (Exit).]")
            logger.info("Exit step reached.")
            break

        # ========== Listen ==========
        if step.listen:
            # 1. get input
            if input_provider:
                user_input = input_provider()
            else:
                try:
                    user_input = input("YOU: ").strip()
                except EOFError:
                    user_input = ""

            # None 作为特殊信号：测试输入耗尽，直接结束对话，避免在静音分支中死循环
            if user_input is None:
                logger.info("Input provider returned None -> end conversation from interpreter.")
                break

            logger.info(f"User input: {user_input}")

            # silence
            if not user_input:
                if step.silence:
                    pending_jump = step.silence
                elif step.default:
                    pending_jump = step.default
                else:
                    print("(no input) -> end.")
                    logger.info("End due to silence with no default.")
                    break
            else:
                # store input
                env_vars["_last_input"] = user_input
                populate_vars_from_input(env_vars, script.vars, user_input)

                # intent
                intent = recognize_intent(user_input, list(step.branches.keys()), mode)
                logger.info(f"Recognized intent: {intent}")

                if intent and intent in step.branches:
                    pending_jump = step.branches[intent]
                else:
                    if step.default:
                        pending_jump = step.default
                    else:
                        print("No matching branch; ending conversation.")
                        logger.info("No branch or default.")
                        break

        # ========== Execute Actions ==========
        # 把同一个 Step 里的多条 Action
        # 收集到 step.actions: List[{"name": str, "args": List[str]}]
        if getattr(step, "actions", None):
            # Action 需要的 input_text：优先使用最近一次用户输入
            input_text = env_vars.get("_last_input", "")

            for action in step.actions:
                name = action.get("name")
                args = action.get("args", [])

                # 为 actions.py 里的实现构造一个“伪 step”，只提供 action_args
                class _ActionStep:
                    pass

                action_step = _ActionStep()
                action_step.action_args = args

                logger.info(f"Action: {name}, args={args}, input_text={input_text}")

                func = ACTION_TABLE.get(name)
                if func:
                    # actions.py 中的函数签名：func(env_vars, input_text, step)
                    func(env_vars, input_text, action_step)
                else:
                    print(f"Unknown action: {name}")
                    logger.error(f"Unknown action: {name}")

            # ========== Condition-based Branching (after actions) ==========
            #
            # 部分 Step 没有 Listen，而是依赖前面 Action 设置的布尔变量来决定跳转。
            # 例如：
            #   Action VerifyUserExists -> 设置 env_vars["user_exists"]
            #   Branch 用户存在 OrderList_Run
            #
            # 这里对这些“语义分支”做一次统一处理，根据 env_vars 中的结果来覆盖 pending_jump。
            if step.branches:
                condition_map = {
                    "用户存在": "user_exists",
                    "订单存在": "order_exists",
                    "可取消": "cancel_eligible",
                    "可修改": "modify_eligible",
                    "库存充足": "stock_available",
                }

                for branch_key, var_name in condition_map.items():
                    if branch_key in step.branches:
                        # 对应变量为真时，跳转到该分支
                        if env_vars.get(var_name):
                            pending_jump = step.branches[branch_key]
                        # 找到一个匹配 key 后就退出（每个 Step 目前只会用到一种语义分支）
                        break

        # ========== Jump (after actions!) ==========
        if pending_jump:
            logger.info(f"Jump to: {pending_jump}")
            current_step_id = pending_jump
            pending_jump = None
            continue

        # ========== If step has no listen: go default or stop ==========
        if not step.listen:
            if step.default:
                current_step_id = step.default
                continue
            else:
                # conversation ends (no input expected)
                print("[No Listen and no Default -> conversation ends]")
                logger.info("End: no Listen and no Default.")
                break

    return env_vars


# ============================
# CLI
# ============================
def main():
    parser = argparse.ArgumentParser(description="Run DSL interpreter.")
    parser.add_argument("script", help="Path to DSL file")
    parser.add_argument("--mode", choices=["mock", "openai"], default="mock")
    args = parser.parse_args()

    if not os.path.exists(args.script):
        print("[ERROR] Script not found:", args.script)
        sys.exit(2)

    text = open(args.script, "r", encoding="utf-8").read()

    try:
        script = parse_text(text)
    except ParseError as e:
        print("[ERROR] Parse failed:", e)
        sys.exit(3)

    run_interpreter(script, mode=args.mode)


if __name__ == "__main__":
    main()
