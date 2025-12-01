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
    return "".join(parts)


# ============================
# Variable extraction
# ============================
def populate_vars_from_input(env_vars: dict, script_vars: set, user_input: str):
    if not user_input:
        return

    # If var name looks like amount, extract number
    for v in script_vars:
        if "amount" in v.lower() or "money" in v.lower() or "金额" in v.lower():
            m = re.search(r"(\d+(?:[.,]\d+)?)", user_input)
            if m:
                env_vars[v] = m.group(1).replace(",", "")
                return

    # Name-like variable
    for v in script_vars:
        if "name" in v.lower() or "user" in v.lower() or "姓名" in v.lower():
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
        # 现在的 Parser 会把同一个 Step 里的多条 Action
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
