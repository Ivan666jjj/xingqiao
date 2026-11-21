import json
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS corpus_docs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT,
  channel TEXT,
  keyword TEXT,
  text TEXT NOT NULL,
  status TEXT NOT NULL,
  flags TEXT NOT NULL,
  purpose TEXT NOT NULL DEFAULT 'discourse',
  imported_at TEXT NOT NULL,
  UNIQUE(source_id, text)
);
CREATE INDEX IF NOT EXISTS idx_corpus_channel ON corpus_docs(channel);
CREATE INDEX IF NOT EXISTS idx_corpus_purpose ON corpus_docs(purpose);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure(db) -> None:
    db.conn.executescript(SCHEMA)
    db.conn.commit()


def import_records(db, records) -> int:
    _ensure(db)
    for rec in records:
        if rec.get("status") != "clean":
            continue
        db.execute(
            """INSERT OR IGNORE INTO corpus_docs
               (source_id, channel, keyword, text, status, flags, purpose, imported_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                rec.get("sourceId"),
                rec.get("channel"),
                rec.get("keyword"),
                rec["text"],
                "clean",
                json.dumps(rec.get("flags", []), ensure_ascii=False),
                "discourse",
                _now(),
            ),
        )
    return len(records)


def stats(db) -> dict:
    _ensure(db)
    total = db.one("SELECT COUNT(*) AS c FROM corpus_docs")["c"]
    channels = db.query(
        "SELECT channel, COUNT(*) AS c FROM corpus_docs GROUP BY channel ORDER BY c DESC"
    )
    keywords = db.query(
        "SELECT keyword, COUNT(*) AS c FROM corpus_docs GROUP BY keyword ORDER BY c DESC"
    )
    return {
        "total": total,
        "byChannel": {r["channel"]: r["c"] for r in channels},
        "byKeyword": {r["keyword"]: r["c"] for r in keywords},
        "purpose": "discourse",
    }


def search(db, query: str, limit: int = 10) -> list[dict]:
    _ensure(db)
    q = (query or "").strip()
    if not q:
        return []
    limit = max(1, min(int(limit), 50))
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = db.query(
        """SELECT id, source_id, channel, keyword, text, purpose
           FROM corpus_docs
           WHERE text LIKE ? ESCAPE '\\'
           ORDER BY id LIMIT ?""",
        (f"%{escaped}%", limit),
    )
    return [
        {
            "id": r["id"],
            "sourceId": r["source_id"],
            "channel": r["channel"],
            "keyword": r["keyword"],
            "text": r["text"],
            "purpose": r["purpose"],
        }
        for r in rows
    ]