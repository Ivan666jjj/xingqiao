import json
import re
from pathlib import Path

VERSION = "2026-11-21.1"

RULES = [
    {
        "id": "cure-01",
        "category": "cure_narrative",
        "severity": "block",
        "pattern": r"治愈|根治|治好|痊愈|摆脱自闭|告别自闭|恢复正常",
        "why": "把自闭症当成需要消除的病，既不准确，也会把压力推给孩子。",
        "sayInstead": [
            "社交能力可以练，但我不替你下“治好”的结论。",
            "我们可以练具体场景，不承诺消除自闭症。",
        ],
    },
    {
        "id": "diagnose-01",
        "category": "diagnosis_claim",
        "severity": "block",
        "pattern": r"你就是(?:自闭症|孤独症|阿斯伯格)|你患有(?:自闭症|孤独症)|我诊断你|根据你的描述[，,]\s*你(?:就)?是",
        "why": "AI 不能做诊断；误判会直接影响孩子和家庭。",
        "sayInstead": [
            "我不做诊断。你的感受可以先说出来，诊断要找专业医生。",
            "我可以陪你把困扰说清楚，但不能给你贴诊断标签。",
        ],
    },
    {
        "id": "stigma-01",
        "category": "stigma",
        "severity": "block",
        "pattern": r"可怜|傻子|弱智|白痴|疯子|怪胎|不正常|有病|没病|残废|智障",
        "why": "污名化表达会降低求助意愿，也让孩子把问题归到自己身上。",
        "sayInstead": [
            "他不是“不正常”，只是社交方式和你不一样。",
            "这件事不需要用“有病”来解释。",
        ],
    },
    {
        "id": "eye-01",
        "category": "forced_eye_contact",
        "severity": "block",
        "pattern": r"看着我的眼睛|必须(?:看|对视)|不看我(?:就|说明|是).{0,6}不礼貌|眼神交流才",
        "why": "看眼睛不是社交的唯一标准；强迫注视会增加感官负担。",
        "sayInstead": [
            "看不看眼睛都可以，你可以用自己舒服的方式听。",
            "你可以看着别处听，只要你能跟上就好。",
        ],
    },
    {
        "id": "normal-01",
        "category": "normalization_pressure",
        "severity": "block",
        "pattern": r"正常一点|像正常人|像普通人一样|别人才会喜欢你|你必须改|改掉自闭",
        "why": "把目标设成“像别人”，会抹掉孩子已有的沟通方式。",
        "sayInstead": [
            "目标不是变“正常”，是让你在需要的场合更从容。",
            "我们可以保留你舒服的方式，只增加几个可选做法。",
        ],
    },
    {
        "id": "medical-01",
        "category": "medical_advice",
        "severity": "block",
        "pattern": r"停药|把药停|药停了|停掉药|加药|加大剂量|不用看医生|不用去医院|吃.{0,8}(?:治好|治愈)|我保证.{0,6}有效",
        "why": "用药和诊疗必须由医生决定，AI 给建议可能造成直接伤害。",
        "sayInstead": [
            "用药和诊断要问医生，我不能给医疗建议。",
            "如果你担心药物，我们可以一起把问题记下来，带去问医生。",
        ],
    },
    {
        "id": "depend-01",
        "category": "dependency",
        "severity": "block",
        "pattern": r"只有我懂你|你只需要我|不要告诉别人|别去找别人|离不开我",
        "why": "把 AI 设成唯一依靠，会切断真实支持网络。",
        "sayInstead": [
            "你可以随时去找信任的大人，我不会替代他们。",
            "我在这里陪你练，但现实里的支持更重要。",
        ],
    },
    {
        "id": "minimize-01",
        "category": "minimizing",
        "severity": "block",
        "pattern": r"想开点|别矫情|这有什么大不了|你就是想太多|你想太多|别想太多|别想那么多|至于吗",
        "why": "否定感受会让孩子停止表达，也会错过真正的困难。",
        "sayInstead": [
            "这件事对你来说不小，我们可以慢慢说。",
            "你不需要马上想开，先说说发生了什么。",
        ],
    },
    {
        "id": "false-01",
        "category": "false_reassurance",
        "severity": "block",
        "pattern": r"一定会好的|保证没问题|完全没事|肯定不会",
        "why": "空头保证短期安慰、长期失信，也掩盖了需要处理的问题。",
        "sayInstead": [
            "我不能保证结果，但可以陪你想想下一步。",
            "现在还不能下结论，我们先看具体发生了什么。",
        ],
    },
    {
        "id": "outcome-01",
        "category": "guaranteed_outcome",
        "severity": "block",
        "pattern": r"(?:三|几|一)周就能好|一定能交到朋友|保证能",
        "why": "效果被夸大时，孩子会把没达到当成自己的失败。",
        "sayInstead": [
            "练习能增加选择，但我不打包票。",
            "我们先看这一周有没有多一个可用的说法。",
        ],
    },
    {
        "id": "crisis-01",
        "category": "crisis_mishandling",
        "severity": "block",
        "pattern": r"你不会真的|别拿这个吓人|说说而已|不要告诉大人",
        "why": "危机表达必须当真处理，不能淡化或要求保密。",
        "sayInstead": [
            "你现在的安全最重要，我会帮你联系可信任的大人。",
            "我会认真对待你说的话，并让一个大人知道。",
        ],
    },
    {
        "id": "privacy-01",
        "category": "privacy_probe",
        "severity": "block",
        "pattern": r"你家住哪|学校叫什么|发张照片|你全名",
        "why": "AI 不需要也不应该索要未成年人的住址、学校、照片或全名。",
        "sayInstead": [
            "不需要告诉我住址、学校或照片。",
            "说个大概就好，不用提供能定位到你的信息。",
        ],
    },
    {
        "id": "infant-01",
        "category": "infantilizing",
        "severity": "warn",
        "pattern": r"小朋友真棒|乖，|听话",
        "why": "过度幼儿化会削弱青少年的自主感。",
        "sayInstead": [
            "谢谢你愿意说这些。",
            "这一步是你自己做的，可以记住它。",
        ],
    },
]

SAFE_PHRASES = [
    "我在，你慢慢说。",
    "不想说也可以，我们可以先停一下。",
    "你现在是什么感觉？可以只选一个词。",
    "这件事听起来很难受。",
    "你愿意的话，我们可以一起想下一步。",
    "你可以拒绝，也可以随时离开。",
    "我不替你下结论。",
    "需要的话，我帮你找可信任的大人。",
]

_COMPILED = [(rule, re.compile(rule["pattern"])) for rule in RULES]


def _load_evidence() -> dict:
    path = Path(__file__).resolve().parents[1] / "data" / "rule_evidence.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data.get("rules", {})


def check_text(text: str) -> dict:
    hits = []
    for rule, pattern in _COMPILED:
        match = pattern.search(text or "")
        if match:
            hits.append(
                {
                    "ruleId": rule["id"],
                    "category": rule["category"],
                    "severity": rule["severity"],
                    "matched": match.group(0),
                    "why": rule["why"],
                    "sayInstead": rule["sayInstead"],
                }
            )

    alternatives: list[str] = []
    for hit in hits:
        if hit["severity"] != "block":
            continue
        for phrase in hit["sayInstead"]:
            if phrase not in alternatives:
                alternatives.append(phrase)

    return {
        "allowed": not any(h["severity"] == "block" for h in hits),
        "hits": hits,
        "safeAlternatives": alternatives,
        "rulesVersion": VERSION,
    }


def list_rules() -> list[dict]:
    evidence = _load_evidence()
    items = []
    for rule in RULES:
        ev = evidence.get(rule["id"], {})
        items.append(
            {
                "id": rule["id"],
                "category": rule["category"],
                "severity": rule["severity"],
                "why": rule["why"],
                "sayInstead": rule["sayInstead"],
                "evidence": ev,
                "evidenceSource": "bcc" if ev.get("rows", 0) > 0 else "research",
            }
        )
    return items