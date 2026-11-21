#!/usr/bin/env python3
"""清洗 BCC 自闭症语料：解压 → 归一化/PII 脱敏 → 分级 → 去重 → JSONL + 报告。"""
import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.cleaning import process_rows


def safe_extract(zip_path: str, dest: str) -> list[Path]:
    out: list[Path] = []
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
                raise ValueError(f"unsafe zip entry: {name}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            out.append(target)
    return out


def pick_csv(files: list[Path]) -> Path:
    csvs = [p for p in files if p.suffix.lower() == ".csv"]
    if not csvs:
        raise SystemExit("zip 内没有 CSV")
    expanded = [p for p in csvs if "扩展" in p.name]
    return (expanded or csvs)[0]


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--out", default="data/corpus")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        files = safe_extract(args.zip, tmp)
        csv_path = pick_csv(files)
        with open(csv_path, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))

    records = process_rows(rows)
    groups = {"clean": [], "review": [], "quarantine": []}
    for rec in records:
        groups[rec["status"]].append(rec)

    for status, items in groups.items():
        write_jsonl(out_dir / f"{status}.jsonl", items)

    flag_counter = Counter(f for rec in records for f in rec["flags"])
    report = {
        "sourceRows": len(rows),
        "uniqueRows": len(records),
        "byStatus": {k: len(v) for k, v in groups.items()},
        "byChannel": dict(Counter(rec["channel"] for rec in records).most_common()),
        "byKeyword": dict(Counter(rec["keyword"] for rec in records).most_common()),
        "flags": dict(flag_counter.most_common()),
        "redactedRows": sum(1 for rec in records if "pii" in rec["flags"]),
        "note": "quarantine/review 仅本地留存，不进入检索库；报告不含原文。",
    }
    with open(out_dir / "report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()