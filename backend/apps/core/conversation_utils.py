GENERIC_AI_CONVERSATION_TITLES = frozenset({"", "新对话", "新建科创对话", "通用咨询", "未命名对话"})


def conversation_title_from_prompt(content):
    """Turn the first user question into a compact, stable history title."""
    normalized = " ".join(str(content or "").split())
    if not normalized:
        return "新对话"
    return f"{normalized[:63]}…" if len(normalized) > 64 else normalized


def is_generic_conversation_title(title):
    return str(title or "").strip() in GENERIC_AI_CONVERSATION_TITLES
