# interpreter.py
import argparse
import re
import os
import sys
import logging
from datetime import datetime
from typing import Optional

# 设置基础路径
from src.dsl_parser import parse_text, ParseError, Script, Step
from src.intent_recognize import recognize_intent


# -------------------------
#  Logging Setup
# -------------------------
def setup_logger():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "interpreter.log")

    logger = logging.getLogger("Interpreter")
    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)

    # 避免重复 handler
    if not logger.handlers:
        logger.addHandler(fh)

    return logger


logger = setup_logger()


# -------------------------
# Helper: evaluate Expression
# -------------------------
def eval_expression(expr, env_vars: dict) -> str:
    out_parts = []
    if expr is None:
        return ""
    for it in expr.items:
        if it.is_var:
            out_parts.append(str(env_vars.get(it.value, "")))
        else:
            out_parts.append(str(it.value))
    return "".join(out_parts)


# -------------------------
# Heuristics to populate variables
# -------------------------
def populate_vars_from_input(env_vars: dict, varnames: set, user_input: str):
    if not user_input:
        return

    logger.info(f"[Var Extract] Input='{user_input}'")

    # extract amount
    for v in varnames:
        if "amount" in v.lower() or "money" in v.lower() or "金额" in v.lower():
            m = re.search(r"(\d+(?:[.,]\d+)?)", user_input)
            if m:
                env_vars[v] = m.group(1).replace(",", "")
                logger.info(f"[Var Extract] Set {v} = {env_vars[v]}")
                return

    # extract name
    for v in varnames:
        if "name" in v.lower() or "user" in v.lower() or "姓名" in v.lower():
            env_vars[v] = user_input.strip()
            logger.info(f"[Var Extract] Set {v} = {env_vars[v]}")
            return


# -------------------------
# Interpreter main loop
# -------------------------
def run_interpreter(script: Script, mode: str = "mock"):
    env_vars = {}
    current_step_id = script.entry

    logger.info("========== Interpreter Started ==========")
    logger.info(f"Entry step = {current_step_id}, Mode = {mode}")

    print(f"--- Starting script (entry: {current_step_id}) ---\n")

    while True:
        step: Step = script.steps.get(current_step_id)
        logger.info(f"[Step Enter] {current_step_id}")

        if step is None:
            logger.error(f"[Error] Unknown step id '{current_step_id}'")
            print(f"ERROR: Unknown step id '{current_step_id}'. Stopping.")
            break

        # SPEAK
        if step.speak:
            out = eval_expression(step.speak, env_vars)
            logger.info(f"[Speak] {out}")
            if out:
                print(f"BOT: {out}")

        # EXIT
        if step.is_exit:
            logger.info("[Exit] Script ended by Exit flag.")
            print("[Conversation ended by script (Exit).]")
            break

        # LISTEN
        if step.listen:
            try:
                user_input = input("YOU: ").strip()
            except EOFError:
                user_input = ""

            logger.info(f"[User Input] '{user_input}'")

            # S I L E N C E
            if not user_input:
                logger.info("[Silence] Detected empty input.")

                if step.silence and step.silence in script.steps:
                    logger.info(f"[Jump Silence] → {step.silence}")
                    print(f"(no input) -> jump to Silence: {step.silence}")
                    current_step_id = step.silence
                elif step.default and step.default in script.steps:
                    logger.info(f"[Jump Default] → {step.default}")
                    print(f"(no input) -> jump to Default: {step.default}")
                    current_step_id = step.default
                else:
                    logger.warning("[End] No silence/default path defined.")
                    print("(no input) -> no next step defined, exiting.")
                    break
                continue

            # Extract variables
            populate_vars_from_input(env_vars, script.vars, user_input)

            # Intent recognition
            branch_keys = list(step.branches.keys())
            intent = recognize_intent(user_input, branch_keys, mode)

            logger.info(f"[Intent] Input='{user_input}', Result={intent}")

            # Jump to matched branch
            if intent:
                next_id = step.branches.get(intent)
                logger.info(f"[Jump Branch] '{intent}' → {next_id}")
                current_step_id = next_id
                continue

            # DEFAULT
            if step.default and step.default in script.steps:
                logger.info(f"[Jump Default] → {step.default}")
                current_step_id = step.default
                continue

            logger.warning("[End] No branch matched; no default.")
            print("No matching branch or default; ending conversation.")
            break

        else:
            # No Listen
            if step.default and step.default in script.steps:
                logger.info(f"[Jump Default] → {step.default}")
                current_step_id = step.default
                continue
            else:
                logger.info("[End] No Listen and no Default.")
                print("[No Listen and no Default -> conversation ends]")
                break


# -------------------------
# CLI
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="Run DSL script interpreter (CLI).")
    parser.add_argument("script", help="Path to DSL script file (e.g., demo1.dsl)")
    parser.add_argument("--mode", choices=["mock", "openai"], default="mock",
                        help="Intent resolution mode.")
    args = parser.parse_args()

    if not os.path.exists(args.script):
        print("Script file not found:", args.script)
        logger.error(f"Script not found: {args.script}")
        sys.exit(2)

    text = open(args.script, "r", encoding="utf-8").read()

    try:
        script = parse_text(text)
        logger.info("Script parsed successfully.")
    except ParseError as e:
        logger.error(f"Parse Error: {e}")
        print("Parse error:", e)
        sys.exit(3)

    run_interpreter(script, mode=args.mode)


if __name__ == "__main__":
    main()
