# interpreter.py
import argparse
import re
import os
import sys
from typing import Optional


# 确保 dsl_parser.py 在同一目录
from src.dsl_parser import parse_text, ParseError, Script, Step
from src.intent_recognize import recognize_intent



# -------------------------
# Helper: evaluate Expression
# -------------------------
def eval_expression(expr, env_vars: dict) -> str:
    """
    expr: Expression (from parser) with items where each item is either var or string
    env_vars: dict mapping varname -> str
    """
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
    """
    Heuristic rules:
    - if there's a var that contains 'name' in its name, set it to user_input (trim)
    - if there's a var that contains 'amount', extract first number and set
    - else do nothing
    """
    if not user_input:
        return

    # amount extraction
    for v in varnames:
        if "amount" in v.lower() or "money" in v.lower() or "金额" in v.lower():
            m = re.search(r"(\d+(?:[.,]\d+)?)", user_input)
            if m:
                env_vars[v] = m.group(1).replace(",", "")
                return

    # name extraction (fallback)
    for v in varnames:
        if "name" in v.lower() or "姓名" in v.lower() or "user" in v.lower():
            env_vars[v] = user_input.strip()
            return

    # If nothing matched, do not set variables (or optionally set a generic var)
    return


# -------------------------
# Interpreter main loop
# -------------------------
def run_interpreter(script: Script, mode: str = "mock"):
    """
    mode: 'mock' or 'openai'
    """
    env_vars = {}  # runtime variables, keyed by varname (without $)
    current_step_id = script.entry
    if current_step_id is None:
        print("Script has no entry step.")
        return

    print(f"--- Starting script (entry: {current_step_id}) ---\n")

    while True:
        step: Step = script.steps.get(current_step_id)
        if step is None:
            print(f"ERROR: Unknown step id '{current_step_id}'. Stopping.")
            break

        # Speak
        if step.speak:
            out = eval_expression(step.speak, env_vars)
            if out:
                print(f"BOT: {out}")

        # If this is an exit step -> finish
        if step.is_exit:
            print("[Conversation ended by script (Exit).]")
            break

        # If there's a Listen, prompt user
        if step.listen:
            try:
                user_input = input("YOU: ").strip()
            except EOFError:
                user_input = ""
            # silence detection (empty input)
            if not user_input:
                # silence: go to silence step if available, else default, else end
                if step.silence and step.silence in script.steps:
                    next_id = step.silence
                    print(f"(no input) -> jump to Silence: {next_id}")
                elif step.default and step.default in script.steps:
                    next_id = step.default
                    print(f"(no input) -> jump to Default: {next_id}")
                else:
                    print("(no input) -> no next step defined, exiting.")
                    break
                current_step_id = next_id
                continue

            # populate some variables heuristically
            populate_vars_from_input(env_vars, script.vars, user_input)

            # resolve intent by selected mode
            branch_keys = list(step.branches.keys())
            intent = recognize_intent(user_input, branch_keys, mode)


            # Determine next step
            if intent:
                # found matching branch key
                next_id = step.branches.get(intent)
                if next_id:
                    current_step_id = next_id
                    continue
            # fallback: default
            if step.default and step.default in script.steps:
                current_step_id = step.default
                continue
            else:
                print("No matching branch or default; ending conversation.")
                break

        else:
            # No Listen: follow default or silence or end
            if step.default and step.default in script.steps:
                current_step_id = step.default
                continue
            else:
                # nothing to do -> end
                print("[No Listen and no Default -> conversation ends]")
                break


# -------------------------
# CLI
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="Run DSL script interpreter (CLI).")
    parser.add_argument("script", help="Path to DSL script file (e.g., demo1.dsl)")
    parser.add_argument("--mode", choices=["mock", "openai"], default="mock",
                        help="Intent resolution mode. 'mock' uses local keyword matching. 'openai' calls OpenAI (requires API key and package).")
    args = parser.parse_args()


    if not os.path.exists(args.script):
        print("Script file not found:", args.script)
        sys.exit(2)

    text = open(args.script, "r", encoding="utf-8").read()
    try:
        script = parse_text(text)
    except ParseError as e:
        print("Parse error:", e)
        sys.exit(3)

    run_interpreter(script, mode=args.mode)


if __name__ == "__main__":
    main()
