#!/usr/bin/env python3
"""把 clean.jsonl 导入 SQLite（purpose=discourse，仅管理员检索）。"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.corpus import import_records, stats
from app.db import Database


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/corpus")
    ap.add_argument("--db", default=os.getenv("XQ_DB", "data/xingqiao.db"))
    args = ap.parse_args()

    path = Path(args.dir) / "clean.jsonl"
    records = [json.loads(line) for line in open(path, encoding="utf-8")]
    db = Database(args.db)
    n = import_records(db, records)
    print(json.dumps({"input": n, **stats(db)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()