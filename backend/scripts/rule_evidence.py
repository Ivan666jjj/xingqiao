#!/usr/bin/env python3
"""统计每条负规则在 BCC 语料中的命中数。只输出计数，不输出原文。"""
import argparse
import csv
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.cleaning import normalize
from app.rules import RULES, VERSION


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
    ap.add_argument("--out", default="data/rule_evidence.json")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        files = extract(args.zip, tmp)
        csvs = [p for p in files if p.suffix.lower() == ".csv"]
        expanded = [p for p in csvs if "扩展" in p.name]
        rows = list(
            csv.DictReader(open((expanded or csvs)[0], encoding="utf-8-sig", newline=""))
        )

    compiled = [(rule, re.compile(rule["pattern"])) for rule in RULES]
    counts = {rule["id"]: {"category": rule["category"], "rows": 0, "matches": 0} for rule in RULES}
    for row in rows:
        text = normalize(row.get("完整上下文", ""))
        for rule, pattern in compiled:
            found = pattern.findall(text)
            if found:
                counts[rule["id"]]["rows"] += 1
                counts[rule["id"]]["matches"] += len(found)

    report = {
        "version": VERSION,
        "source": "BCC 自闭症及扩展词语料",
        "sourceRows": len(rows),
        "note": "计数来自原始语料，仅用于证明规则必要性；不包含原文。",
        "rules": counts,
    }
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()