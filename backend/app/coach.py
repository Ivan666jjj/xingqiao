import re

RULES = [
    ("apology", re.compile(r"对不起|抱歉|不好意思|我不是故意")),
    ("retaliate", re.compile(r"凭什么|为什么他|为什么别人|不理他|活该|谁让他")),
    ("direct_demand", re.compile(r"给我|必须|现在就要|快点|拿来")),
    ("alternative", re.compile(r"明天|下次|改天|之后|回头")),
    ("accept", re.compile(r"好吧|行吧|那算了|没关系|可以")),
    ("avoidance", re.compile(r"等他|先不说|走开|装作|不管|算了不")),
    ("repair", re.compile(r"纸巾|帮你|擦一下|我拿|我赔")),
    ("request", re.compile(r"借|笔记|抄|方便吗")),
]

DISCLAIMER = "这是练习建议，不是诊断，也不评价你这个人。你可以只挑一句试试。"

BANK = {
    ("borrow", "direct_demand"): [
        ("能把今天的笔记借我抄一下吗？我昨天请假没来。", "说清要什么、为什么，对方才知道怎么回应。"),
        ("你现在方便吗？我想借今天的笔记，十分钟就能拍完。", "先问方便，再给时长，对方拒绝的成本更低。"),
    ],
    ("borrow", "avoidance"): [
        ("我想借一下今天的笔记，你现在方便吗？", "直接开口比等对方先说话更容易发生。"),
        ("打扰一下，我昨天请假了，能拍一下你的笔记吗？", "先说明原因，再提请求，对方更容易答应。"),
    ],
    ("borrow", "request"): [
        ("谢谢，我三点二十来拿，大概二十分钟。", "把模糊的承诺变成具体时间，双方都省事。"),
        ("好，那我在教室等你，抄完就还你。", "确认地点和归还方式。"),
    ],
    ("rejected", "retaliate"): [
        ("那明天可以借我吗？", "先接受这次拒绝，再给一个替代方案，对话不会断。"),
        ("好，那我明天再问你。谢谢。", "不追问理由，保留下一次开口的空间。"),
    ],
    ("rejected", "accept"): [
        ("好，那我明天第一节下课来找你。", "确认具体时间，约定才真正成立。"),
    ],
    ("rejected", "alternative"): [
        ("好，明天可以的话我下课来找你。", "把对方的口头答应落到时间上。"),
    ],
    ("apologize", "excuse"): [
        ("对不起，撞到你了。我帮你拿纸巾。", "先道歉，再解释；顺序反了，解释会像辩解。"),
        ("抱歉，是我转身太急。袖子脏了，我来处理。", "承认动作，再给具体补救。"),
    ],
    ("apologize", "apology"): [
        ("纸巾给你，要不要去擦一下？", "给一个具体、马上能做的帮助。"),
    ],
    ("apologize", "repair"): [
        ("我陪你去洗手间处理一下吧。", "把帮助做完，而不是只说一次对不起。"),
    ],
}

GENERIC = [
    ("先说清你要什么、为什么。", "对方知道该做什么，回应会更容易。"),
    ("再给一个具体的时间或做法。", "模糊的请求容易拖成没有结果。"),
]

SCENE_KEYS = {"borrow", "rejected", "apologize"}


def classify(text: str) -> str:
    for intent, pattern in RULES:
        if pattern.search(text or ""):
            return intent
    return "unknown"


def suggestions_for(scene_id: str, text: str) -> dict:
    intent = classify(text)
    bank = BANK.get((scene_id, intent))
    if bank:
        items = [{"text": t, "why": w} for t, w in bank]
    else:
        items = [{"text": t, "why": w} for t, w in GENERIC]
    return {
        "matched": bank is not None,
        "intent": intent,
        "suggestions": items,
        "disclaimer": DISCLAIMER,
        "safety": {"escalated": False},
    }