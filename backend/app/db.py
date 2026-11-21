import sqlite3
import threading
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS participants (
  id TEXT PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  age_band TEXT,
  gender TEXT,
  diagnosis_status TEXT,
  language_level TEXT,
  token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  version TEXT NOT NULL,
  scopes TEXT NOT NULL,
  guardian_confirmed INTEGER NOT NULL,
  child_assent INTEGER NOT NULL,
  method TEXT,
  guardian_ref_hash TEXT,
  granted_at TEXT NOT NULL,
  withdrawn_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  scene_id TEXT NOT NULL,
  mode TEXT,
  status TEXT NOT NULL,
  current_turn INTEGER NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL,
  ended_at TEXT
);

CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  turn_index INTEGER NOT NULL,
  option_id TEXT NOT NULL,
  latency_ms INTEGER,
  hint_level INTEGER NOT NULL DEFAULT 0,
  reply TEXT,
  feedback_kind TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(session_id, turn_index)
);

CREATE TABLE IF NOT EXISTS self_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_id TEXT NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  session_id TEXT,
  kind TEXT NOT NULL,
  ref_id TEXT,
  mood INTEGER,
  confidence INTEGER,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS moderation_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_id TEXT,
  source TEXT NOT NULL,
  ref_id TEXT,
  excerpt TEXT,
  risk_flags TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  reviewer TEXT,
  decision TEXT,
  reason TEXT,
  created_at TEXT NOT NULL,
  reviewed_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT,
  detail TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS webhook_outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event TEXT NOT NULL,
  payload TEXT NOT NULL,
  signature TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  delivered_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_participant ON sessions(participant_id);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_moderation_status ON moderation_items(status);
"""


class Database:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def execute(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()):
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def one(self, sql: str, params: tuple = ()):
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def close(self):
        with self._lock:
            self.conn.close()