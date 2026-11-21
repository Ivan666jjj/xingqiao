#!/usr/bin/env python3
"""审计 BCC 里能否支撑「开放式陪伴」：只输出统计，不输出敏感原文。"""
import argparse
import csv
import json
import re
import shutil
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.cleaning import flags_for, normalize

SUPPORT = re.compile(r"没事|抱抱|理解|难受|开心|害怕|孤单|陪你|听你说|别怕|加油|辛苦|我在|慢慢来")
BLOCK = {
    "sexual_content",
    "self_harm",
    "violence",
    "non_autism_usage",
    "stigma",
    "cure_narrative",
    "misinformation",
}


def extract(zip_path: str, dest: str) -> list[Path]:
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename
            if not (info.flag_bits & 0x800):
                try:
                    name = name.encode("cp437").decode("utf-8")
                except Exception:
                    pass
            target = Path(dest, name).resolve()
            if not str(target).startswith(str(Path(dest).resolve())):
                raise ValueError("unsafe zip entry")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            out.append(target)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--out", default="data/corpus/companion_audit.json")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        files = extract(args.zip, tmp)
        csvs = [p for p in files if p.suffix.lower() == ".csv"]
        expanded = [p for p in csvs if "扩展" in p.name]
        rows = list(
            csv.DictReader(open((expanded or csvs)[0], encoding="utf-8-sig", newline=""))
        )

    both = 0
    with_support = 0
    blocked = Counter()
    candidates = []
    for row in rows:
        text = normalize(row.get("完整上下文", ""))
        if len(text) < 20 or "我" not in text or "你" not in text:
            continue
        both += 1
        if not SUPPORT.search(text):
            continue
        with_support += 1
        flags = set(
            flags_for(
                text,
                provided_non_autism=row.get("疑似非自闭症用法") == "是",
                channel=row.get("频道", ""),
            )
        )
        hit = flags & BLOCK
        if hit:
            blocked.update(hit)
            continue
        quotes = len(re.findall(r"[“”\"]", text))
        score = sum(
            [
                bool(re.search(r"[？?]", text)),
                bool(SUPPORT.search(text)),
                quotes >= 2,
                quotes >= 4,
            ]
        )
        candidates.append(
            {
                "channel": row.get("频道", ""),
                "score": score,
                "quotes": quotes,
            }
        )

    report = {
        "sourceRows": len(rows),
        "bothPronouns": both,
        "withSupportTerms": with_support,
        "strictCandidates": len(candidates),
        "multiTurnCandidates": sum(1 for c in candidates if c["quotes"] >= 4),
        "byChannel": dict(Counter(c["channel"] for c in candidates)),
        "scoreHistogram": dict(Counter(c["score"] for c in candidates)),
        "blockedAmongSupportRows": dict(blocked),
        "conclusion": "无可用的多轮陪伴对话；仅可做词表/语气参考。",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()