from .qwen import QwenClient, QwenError
from .rules import check_text

SYSTEM_PROMPT = """你是“星桥”的社交练习陪练，面向自闭症谱系青少年。
规则：
1. 用简短、具体、温和的中文，每次最多 3 句话。
2. 不诊断、不评估、不承诺疗效；不给用药或其他医疗建议。
3. 不要求眼神接触，不使用“正常/不正常”“可怜”“治愈”这类说法。
4. 先接住感受，再给一个可以试着说的句子，或问一个具体的小问题。
5. 允许对方拒绝、暂停、离开；不制造依赖，不暗示“只有我懂你”。
6. 遇到自伤、被欺凌、家暴等内容，停止练习，建议找可信任的大人。
"""

RETRY_PROMPT = """上一版回复包含不允许的表达。请改写为更安全的一版：
不要出现治愈/诊断/污名/说教/依赖/医疗建议/强迫眼神接触；最多 3 句。"""

FALLBACK = "我在，你慢慢说。你现在最想练的是哪一个小场景？如果不想说，我们也可以先停一下。"


def _text_of(response: dict) -> str:
    try:
        return (response["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _clean_messages(messages: list[dict]) -> list[dict]:
    out = []
    for m in messages[-12:]:
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        out.append({"role": role, "content": content[:2000]})
    return out


def resolve_model(requested: str | None, default: str) -> str:
    if not requested or requested in ("xingqiao", "xingqiao-guard"):
        return default
    if requested.startswith("qwen"):
        return requested
    return default


def guarded_chat(
    client: QwenClient,
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 400,
) -> dict:
    model_name = resolve_model(model, client.model)
    history = _clean_messages(messages)
    base = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try:
        first = client.chat(base, model=model_name, max_tokens=max_tokens)
    except QwenError as exc:
        return {
            "content": FALLBACK,
            "usage": {},
            "model": model_name,
            "guard": {"allowed": True, "hits": [], "retried": False, "fallback": True},
            "error": str(exc),
        }

    text = _text_of(first)
    verdict = check_text(text)
    if verdict["allowed"] and text:
        return {
            "content": text,
            "usage": first.get("usage", {}),
            "model": model_name,
            "guard": {
                "allowed": True,
                "hits": [],
                "retried": False,
                "fallback": False,
                "rulesVersion": verdict["rulesVersion"],
            },
        }

    retry = base + [
        {"role": "system", "content": RETRY_PROMPT},
        {"role": "assistant", "content": text},
    ]
    try:
        second = client.chat(retry, model=model_name, max_tokens=max_tokens)
    except QwenError as exc:
        return {
            "content": FALLBACK,
            "usage": {},
            "model": model_name,
            "guard": {
                "allowed": True,
                "hits": verdict["hits"],
                "retried": True,
                "fallback": True,
            },
            "error": str(exc),
        }

    text2 = _text_of(second)
    verdict2 = check_text(text2)
    if verdict2["allowed"] and text2:
        return {
            "content": text2,
            "usage": second.get("usage", {}),
            "model": model_name,
            "guard": {
                "allowed": True,
                "hits": verdict["hits"],
                "retried": True,
                "fallback": False,
                "rulesVersion": verdict2["rulesVersion"],
            },
        }

    return {
        "content": FALLBACK,
        "usage": second.get("usage", {}),
        "model": model_name,
        "guard": {
            "allowed": True,
            "hits": verdict2["hits"] or verdict["hits"],
            "retried": True,
            "fallback": True,
            "rulesVersion": verdict2["rulesVersion"],
        },
    }