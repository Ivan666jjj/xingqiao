import re
import unicodedata

URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
CONTACT_RE = re.compile(
    r"(?:QQ|qq|微信|vx|VX|Vx|v信|薇信)\s*[:：]?\s*[A-Za-z0-9_-]{5,20}"
)
LONG_NUM_RE = re.compile(r"(?<!\d)\d{11,}(?!\d)")

AUTISM_TERMS = ("自闭症", "孤独症", "阿斯伯格", "亚斯伯格", "星星的孩子", "ASD", "autism")

PATTERNS = {
    "non_autism_usage": re.compile(
        r"我自闭(?!症)|自闭门户|夜晚孤独症|孤独症犯了|自闭症闭嘴|"
        r"得自闭症|得了自闭|患上自闭|快得自闭|就(?:是|得)自闭症了|"
        r"自闭症狂怒|我都自闭"
    ),
    "self_harm": re.compile(r"自杀|自伤|割腕|不想活|活着没意思|跳楼"),
    "sexual_content": re.compile(r"性侵|强奸|猥亵|脱裤|裸体|裸露|裸照|做那种事情|破处|性行为"),
    "violence": re.compile(r"打死|虐待|家暴|打我|威胁我|霸凌|欺凌"),
    "stigma": re.compile(
        r"智障|弱智|白痴|低能|傻子|傻|疯子|疯|怪胎|残废|重残|脑子有病|可怜|不正常|有病|没病|得病"
    ),
    "cure_narrative": re.compile(r"治愈|根治|治好|痊愈|告别自闭|摆脱自闭|摆脱孤独"),
    "misinformation": re.compile(r"冰箱母亲|疫苗导致|疫苗引起|父母冷漠导致|父母冷淡导致"),
}

QUARANTINE = {
    "sexual_content",
    "self_harm",
    "violence",
    "non_autism_usage",
    "informal_channel",
    "too_short",
    "no_autism_term",
}
REVIEW = {"stigma", "pii", "cure_narrative", "misinformation"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("【", "").replace("】", "")
    text = text.replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def redact(text: str) -> str:
    out = URL_RE.sub("[URL]", text)
    out = EMAIL_RE.sub("[EMAIL]", out)
    out = ID_RE.sub("[ID]", out)
    out = PHONE_RE.sub("[PHONE]", out)
    out = CONTACT_RE.sub("[CONTACT]", out)
    out = LONG_NUM_RE.sub("[NUMBER]", out)
    return out


def flags_for(
    text: str, provided_non_autism: bool = False, channel: str = ""
) -> list[str]:
    flags: list[str] = []
    if provided_non_autism:
        flags.append("non_autism_usage")
    if channel in ("口语", "近代汉语"):
        flags.append("informal_channel")
    for flag, pattern in PATTERNS.items():
        if pattern.search(text) and flag not in flags:
            flags.append(flag)
    if redact(text) != text:
        flags.append("pii")
    if len(text) < 25:
        flags.append("too_short")
    if not any(term.lower() in text.lower() for term in AUTISM_TERMS):
        flags.append("no_autism_term")
    return flags


def status_for(flags: list[str]) -> str:
    if any(f in QUARANTINE for f in flags):
        return "quarantine"
    if any(f in REVIEW for f in flags):
        return "review"
    return "clean"


def _dedupe_key(text: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text).lower()


def dedupe(records: list[dict]) -> list[dict]:
    priority = {"clean": 3, "review": 2, "quarantine": 1}
    kept: dict[str, dict] = {}
    for rec in records:
        key = _dedupe_key(rec.get("text", ""))
        if not key:
            continue
        prev = kept.get(key)
        if prev is None:
            kept[key] = rec
        elif priority.get(rec.get("status", ""), 0) > priority.get(prev.get("status", ""), 0):
            kept[key] = rec
    return list(kept.values())


def process_rows(rows: list[dict]) -> list[dict]:
    records: list[dict] = []
    for i, row in enumerate(rows, start=1):
        raw = row.get("完整上下文", "")
        normalized = normalize(raw)
        flags = flags_for(
            normalized,
            provided_non_autism=row.get("疑似非自闭症用法") == "是",
            channel=row.get("频道", ""),
        )
        records.append(
            {
                "index": row.get("序号") or str(i),
                "keyword": row.get("检索词", ""),
                "channel": row.get("频道", ""),
                "text": redact(normalized),
                "source": row.get("语料来源", ""),
                "sourceId": row.get("来源ID", ""),
                "flags": flags,
                "status": status_for(flags),
            }
        )
    return dedupe(records)