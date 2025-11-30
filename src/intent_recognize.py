# intent_recognizer.py
import os

try:
    import dashscope
    HAS_DASHSCOPE = True
except Exception:
    HAS_DASHSCOPE = False


def resolve_intent_qwen(user_input: str, branch_keys: list, system_context: str = "") -> str | None:
    """
    Use Alibaba Qwen model to choose the best matching branch key.
    Returns:
        - matched branch key (string)
        - None if not matched
    """

    if not HAS_DASHSCOPE:
        print("[LLM] dashscope package missing → fallback to None.")
        return None

    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("[LLM] DASHSCOPE_API_KEY not found → fallback to None.")
        return None

    dashscope.api_key = api_key

    options_text = ", ".join([f"'{k}'" for k in branch_keys])

    prompt = f"""
你是一个客服机器人系统中的意图分类模块。
请从以下意图关键词中选出最符合用户输入意思的一项。

候选意图：
{options_text}

要求：
1. 输出必须是上述关键词之一。
2. 不要返回解释，不要多余内容。
3. 如果无法匹配，请返回：未识别

用户输入：{user_input}
"""

    try:
        response = dashscope.Generation.call(
            model="qwen-turbo",  # 也可以使用 "qwen-plus", "qwen-max" 等
            prompt=prompt,
            temperature=0,
            max_tokens=16
        )

        if response.status_code == 200:
            result = response.output.text.strip()
            result = result.strip('"').strip("'")

            if result == "未识别":
                return None

            # normalize match
            for k in branch_keys:
                if result.lower() == k.lower():
                    return k

            # fuzzy fallback
            for k in branch_keys:
                if k.lower() in result.lower():
                    return k

        return None

    except Exception as e:
        print("[LLM] Error:", e)
        return None


def resolve_intent_mock(user_input: str, branch_keys: list) -> str | None:
    """Simple substring keyword match."""
    ui = user_input.lower()
    for key in branch_keys:
        if key.lower() in ui:
            return key
    return None


def recognize_intent(user_input: str, branch_keys: list, mode="mock") -> str | None:
    """Unified interface."""
    if mode == "openai":
        ans = resolve_intent_qwen(user_input, branch_keys)
        if ans is not None:
            return ans
    return resolve_intent_mock(user_input, branch_keys)