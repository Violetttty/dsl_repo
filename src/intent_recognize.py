# intent_recognizer.py
import os
import logging

# 引入 dashscope（可选）
try:
    import dashscope
    HAS_DASHSCOPE = True
except Exception:
    HAS_DASHSCOPE = False


# -------------------------
# Logging Setup (共享 interpreter logger)
# -------------------------
def get_logger():
    """
    与 interpreter.py 中的 logger 同名（'interpreter'），
    这样日志会一起写入 logs/interpreter.log。
    """
    logger = logging.getLogger("interpreter")
    logger.setLevel(logging.INFO)
    return logger


logger = get_logger()


# -------------------------
# Qwen 意图识别
# -------------------------
def resolve_intent_qwen(user_input: str, branch_keys: list, system_context: str = "") -> str | None:
    """
    Use Alibaba Qwen model to choose the best matching branch key.
    Returns:
        - matched branch key (string)
        - None if not matched
    """

    logger.info(f"[LLM] resolve_intent_qwen called, input='{user_input}', keys={branch_keys}")

    if not HAS_DASHSCOPE:
        logger.warning("[LLM] dashscope package missing → fallback to None.")
        return None

    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("[LLM] DASHSCOPE_API_KEY not found → fallback to None.")
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
        logger.info("[LLM] Sending request to Qwen...")

        response = dashscope.Generation.call(
            model="qwen-plus",
            prompt=prompt,
            temperature=0,
            max_tokens=16
        )

        logger.info(f"[LLM] Qwen response status={response.status_code}")

        if response.status_code == 200:
            result = response.output.text.strip()
            logger.info(f"[LLM] Raw result = {result}")

            result = result.strip('"').strip("'")

            if result == "未识别":
                logger.info("[LLM] Model returned 未识别 → None")
                return None

            # normalize match
            for k in branch_keys:
                if result.lower() == k.lower():
                    logger.info(f"[LLM] Exact match: {result} -> {k}")
                    return k

            # fuzzy fallback
            for k in branch_keys:
                if k.lower() in result.lower():
                    logger.info(f"[LLM] Fuzzy match: {result} -> {k}")
                    return k

            logger.info(f"[LLM] No match found for: {result}")
            return None

        else:
            logger.error(f"[LLM] Non-200 status: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"[LLM] Exception: {e}")
        return None


# -------------------------
# Mock 意图识别
# -------------------------
def resolve_intent_mock(user_input: str, branch_keys: list) -> str | None:
    ui = user_input.lower()

    logger.info(f"[Mock] resolve_intent_mock called, input='{user_input}'")

    for key in branch_keys:
        if key.lower() in ui:
            logger.info(f"[Mock] Matched: {key}")
            return key

    logger.info("[Mock] No match, return None")
    return None


# -------------------------
# Unified interface
# -------------------------
def recognize_intent(user_input: str, branch_keys: list, mode="mock") -> str | None:
    logger.info(f"[Intent] Recognize intent mode={mode}, input='{user_input}'")

    # LLM 优先
    if mode == "openai":
        ans = resolve_intent_qwen(user_input, branch_keys)
        # 同时在终端打印一次，方便调试每次识别到的意图
        print(f"[LLM] LLM input='{user_input}' -> {ans}")
        if ans is not None:
            logger.info(f"[Intent] LLM determined → {ans}")
            return ans
        else:
            logger.info("[Intent] LLM returned None → fallback to mock")

    # 本地 mock
    ans = resolve_intent_mock(user_input, branch_keys)
    logger.info(f"[Intent] Final result → {ans}")
    
    return ans
