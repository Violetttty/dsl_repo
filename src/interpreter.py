# interpreter.py
import argparse
import re
import os
import sys
from typing import Optional

# 确保 dsl_parser.py 在同一目录
from src.dsl_parser import parse_text, ParseError, Script, Step

# Optional OpenAI support (only used if user supplies --mode openai and OPENAI_API_KEY is set)
try:
    import openai
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False


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
# Intent resolution - mock (keyword match)
# -------------------------
def resolve_intent_mock(user_input: str, branch_keys: list) -> Optional[str]:
    """
    Simple heuristic: if any branch key appears as substring in user_input -> return it.
    Matching is case-insensitive.
    If none matched -> return None.
    """
    if not user_input:
        return None
    ui = user_input.lower()
    for key in branch_keys:
        if not key:
            continue
        k = key.lower()
        if k in ui:
            return key
    return None


# -------------------------
# Intent resolution - OpenAI (optional)
# -------------------------
def resolve_intent_openai(user_input: str, branch_keys: list, system_context: str = "") -> Optional[str]:
    """
    Call OpenAI ChatCompletion to ask which keyword fits best.
    Requires OPENAI_API_KEY in environment and openai package installed.
    Returns matched branch key (string) or None if '未识别'.
    """
    if not HAS_OPENAI:
        print("OpenAI package not installed; falling back to mock.")
        return resolve_intent_mock(user_input, branch_keys)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set; falling back to mock.")
        return resolve_intent_mock(user_input, branch_keys)

    openai.api_key = api_key

    # Build a concise prompt that asks model to return just one keyword from branch_keys or "未识别"
    options = ", ".join([f"'{k}'" for k in branch_keys if k])
    if not options:
        return None

    prompt = (
        f"{system_context}\n\n"
        "任务：请根据用户输入，在以下候选意图关键词中选择最匹配的一项，"
        "只返回关键词文本本身（例如：投诉），不要带解释。"
        f"\n候选关键词：{options}\n\n用户输入：\"\"\"\n{user_input}\n\"\"\"\n\n"
        "如果不匹配任何选项，请返回“未识别”。"
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # 可替换为你有权限的模型
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=32,
        )
        text = resp.choices[0].message.content.strip()
        # normalize
        text = text.strip().strip('"').strip("'")
        if text == "未识别":
            return None
        # check if text matches any branch key (fuzzy)
        for k in branch_keys:
            if k and text.lower() == k.lower():
                return k
        # try containment match
        for k in branch_keys:
            if k and k.lower() in text.lower():
                return k
        # fallback: None
        return None
    except Exception as e:
        print("OpenAI call failed:", e)
        return resolve_intent_mock(user_input, branch_keys)


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
            if mode == "openai":
                intent = resolve_intent_openai(user_input, branch_keys)
            else:
                intent = resolve_intent_mock(user_input, branch_keys)

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

    if args.mode == "openai" and not HAS_OPENAI:
        print("Warning: openai package not installed. Falling back to mock mode.")
        args.mode = "mock"

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
