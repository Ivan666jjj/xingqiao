import json
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .chat import FALLBACK as CHAT_FALLBACK, guarded_chat
from .coach import DISCLAIMER, suggestions_for
from .config import load_config
from .content import Content
from .corpus import search as corpus_search
from .corpus import stats as corpus_stats
from .db import Database
from .qwen import QwenClient, QwenError
from .rules import SAFE_PHRASES, VERSION as RULES_VERSION, check_text, list_rules
from .security import (
    new_participant_token,
    ref_hash,
    same,
    sign_payload,
    token_hash,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ParticipantIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    ageBand: str
    gender: str = "unspecified"
    diagnosisStatus: str
    languageLevel: str


class ConsentIn(BaseModel):
    version: str
    scopes: list[str] = Field(min_length=1)
    guardianConfirmed: bool
    childAssent: bool
    method: str = "digital"
    guardianRef: str | None = None


class SessionIn(BaseModel):
    sceneId: str
    mode: str = "solo"


class TurnIn(BaseModel):
    turnIndex: int = Field(ge=0)
    optionId: str
    latencyMs: int | None = Field(default=None, ge=0, le=600_000)
    hintLevel: int = Field(default=0, ge=0, le=2)
    freeText: str | None = Field(default=None, max_length=500)


class ReviewIn(BaseModel):
    itemId: int
    decision: str
    reason: str | None = Field(default=None, max_length=300)


class QuizIn(BaseModel):
    itemId: str
    choice: str
    rtMs: int | None = Field(default=None, ge=0, le=600_000)


class TaskCheckinIn(BaseModel):
    note: str | None = Field(default=None, max_length=300)
    mood: int | None = Field(default=None, ge=0, le=4)


class CoachIn(BaseModel):
    sceneId: str
    text: str = Field(min_length=1, max_length=500)


class SafetyIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ChatMessageIn(BaseModel):
    role: str
    content: str | list | None = None


class ChatCompletionIn(BaseModel):
    model: str | None = None
    messages: list[ChatMessageIn]
    max_tokens: int | None = Field(default=400, ge=1, le=2000)
    temperature: float | None = Field(default=0.6, ge=0, le=2)
    stream: bool | None = False


RISK_TERMS = {
    "self_harm": ("自杀", "自伤", "割腕", "不想活", "活着没意思", "跳楼"),
    "violence": ("打我", "欺负", "霸凌", "家暴", "威胁我"),
}

SAFE_REPLY = "这句话我会转给一位大人一起看。现在先停在这里，你不需要一个人处理。"


def detect_risk(text: str | None) -> list[str]:
    if not text:
        return []
    return [flag for flag, terms in RISK_TERMS.items() if any(t in text for t in terms)]


def create_app(db_path: str | None = None, qwen_client=None) -> FastAPI:
    cfg = load_config(db_path)
    db = Database(cfg.db_path)
    content = Content.load(Path(__file__).resolve().parents[1] / "data")
    qwen = qwen_client or QwenClient(
        cfg.qwen_api_key, cfg.qwen_base_url, cfg.qwen_text_model, cfg.qwen_timeout
    )

    app = FastAPI(title="星桥 API", version="0.1.0")
    app.state.db = db
    app.state.config = cfg
    app.state.qwen = qwen
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cfg.allowed_origins),
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
    )

    hits: dict[str, deque] = defaultdict(deque)

    @app.middleware("http")
    async def rate_limit(request, call_next):
        if request.url.path.startswith(("/health", "/docs", "/openapi.json")):
            return await call_next(request)
        key = (
            request.headers.get("authorization")
            or request.headers.get("x-admin-token")
            or (request.client.host if request.client else "anonymous")
        )
        t = time.monotonic()
        q = hits[key]
        while q and t - q[0] >= 60:
            q.popleft()
        if len(q) >= cfg.rate_limit_per_min:
            return JSONResponse(status_code=429, content={"detail": "rate_limited"})
        q.append(t)
        return await call_next(request)

    def admin_ok(token: str | None) -> bool:
        return same(token, cfg.admin_token)

    def participant(authorization: str | None):
        if not authorization or not authorization.startswith("Bearer "):
            return None
        raw = authorization.removeprefix("Bearer ").strip()
        return db.one(
            "SELECT * FROM participants WHERE token_hash = ?", (token_hash(raw),)
        )

    def require_participant(authorization: str | None):
        row = participant(authorization)
        if row is None:
            raise HTTPException(status_code=401, detail="invalid_participant_token")
        return row

    def has_consent(pid: str) -> bool:
        row = db.one(
            "SELECT 1 FROM consents WHERE participant_id = ? AND withdrawn_at IS NULL LIMIT 1",
            (pid,),
        )
        return row is not None

    def add_moderation(
        pid: str | None, source: str, ref_id: str, text: str, flags: list[str]
    ) -> int:
        cur = db.execute(
            """INSERT INTO moderation_items
               (participant_id, source, ref_id, excerpt, risk_flags, status, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                pid,
                source,
                ref_id,
                (text or "")[:60],
                json.dumps(flags),
                "pending",
                now(),
            ),
        )
        return cur.lastrowid

    def turn_payload(scene: dict, index: int, hint: str | None = None):
        if index >= len(scene["turns"]):
            return None
        t = scene["turns"][index]
        return {
            "index": index,
            "them": t["them"],
            "prompt": t["prompt"],
            "options": [
                {"id": o["id"], "tag": o.get("tag", o["id"].upper()), "say": o["say"]}
                for o in t["options"]
            ],
            "hint": hint,
        }

    @app.get("/health")
    def health():
        return {"status": "ok", "version": app.version}

    @app.post("/api/v1/participants", status_code=201)
    def create_participant(body: ParticipantIn, x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        pid = "p_" + token_hash(body.code)[:16]
        token = new_participant_token()
        try:
            db.execute(
                """INSERT INTO participants
                   (id, code, age_band, gender, diagnosis_status, language_level, token_hash, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    pid,
                    body.code,
                    body.ageBand,
                    body.gender,
                    body.diagnosisStatus,
                    body.languageLevel,
                    token_hash(token),
                    now(),
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="code_exists")
        db.execute(
            "INSERT INTO audit_log (actor, action, target, detail, created_at) VALUES (?,?,?,?,?)",
            ("admin", "participant.create", pid, "{}", now()),
        )
        return {"participantId": pid, "code": body.code, "token": token}

    @app.post("/api/v1/consent", status_code=201)
    def give_consent(body: ConsentIn, authorization: str | None = Header(None)):
        p = require_participant(authorization)
        if not body.guardianConfirmed or not body.childAssent:
            raise HTTPException(status_code=400, detail="consent_incomplete")
        cur = db.execute(
            """INSERT INTO consents
               (participant_id, version, scopes, guardian_confirmed, child_assent,
                method, guardian_ref_hash, granted_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                p["id"],
                body.version,
                json.dumps(body.scopes, ensure_ascii=False),
                1,
                1,
                body.method,
                ref_hash(body.guardianRef) if body.guardianRef else None,
                now(),
            ),
        )
        db.execute(
            "INSERT INTO audit_log (actor, action, target, detail, created_at) VALUES (?,?,?,?,?)",
            (p["id"], "consent.grant", p["id"], body.version, now()),
        )
        return {"consentId": cur.lastrowid, "grantedAt": now()}

    @app.get("/api/v1/scenes")
    def list_scenes():
        return {"items": content.public_scenes()}

    @app.post("/api/v1/sessions", status_code=201)
    def start_session(body: SessionIn, authorization: str | None = Header(None)):
        p = require_participant(authorization)
        if not has_consent(p["id"]):
            raise HTTPException(status_code=403, detail="consent_required")
        scene = content.scenes.get(body.sceneId)
        if scene is None:
            raise HTTPException(status_code=404, detail="scene_not_found")
        sid = "s_" + new_participant_token()[:18]
        db.execute(
            """INSERT INTO sessions (id, participant_id, scene_id, mode, status, current_turn, started_at)
               VALUES (?,?,?,?,?,?,?)""",
            (sid, p["id"], body.sceneId, body.mode, "active", 0, now()),
        )
        return {
            "sessionId": sid,
            "scene": {"id": scene["id"], "title": scene["title"], "desc": scene["desc"]},
            "totalTurns": len(scene["turns"]),
            "turn": turn_payload(scene, 0),
        }

    @app.post("/api/v1/sessions/{sid}/turns")
    def submit_turn(
        sid: str, body: TurnIn, authorization: str | None = Header(None)
    ):
        p = require_participant(authorization)
        session = db.one("SELECT * FROM sessions WHERE id = ?", (sid,))
        if session is None or session["participant_id"] != p["id"]:
            raise HTTPException(status_code=404, detail="session_not_found")
        if session["status"] != "active":
            raise HTTPException(status_code=409, detail="session_finished")
        scene = content.scenes.get(session["scene_id"])
        if body.turnIndex != session["current_turn"]:
            raise HTTPException(status_code=409, detail="turn_out_of_order")
        turn = scene["turns"][body.turnIndex]
        option = next((o for o in turn["options"] if o["id"] == body.optionId), None)
        if option is None:
            raise HTTPException(status_code=400, detail="option_not_found")
        try:
            db.execute(
                """INSERT INTO turns
                   (session_id, turn_index, option_id, latency_ms, hint_level, reply, feedback_kind, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    sid,
                    body.turnIndex,
                    body.optionId,
                    body.latencyMs,
                    body.hintLevel,
                    option["reply"],
                    option["kind"],
                    now(),
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="turn_already_submitted")

        risk_flags = detect_risk(body.freeText)
        if risk_flags:
            moderation_id = add_moderation(
                p["id"], "turn_free_text", sid, body.freeText or "", risk_flags
            )
            db.execute(
                "UPDATE sessions SET status = 'flagged', current_turn = ? WHERE id = ?",
                (body.turnIndex + 1, sid),
            )
            return {
                "reply": SAFE_REPLY,
                "feedback": "系统已暂停这一轮，并把它放进人工审核队列。",
                "kind": "safety",
                "hint": None,
                "next": None,
                "completed": False,
                "safety": {"escalated": True, "moderationId": moderation_id},
            }

        next_index = body.turnIndex + 1
        finished = next_index >= len(scene["turns"])
        ts = now()
        db.execute(
            "UPDATE sessions SET current_turn = ?, status = ?, ended_at = ? WHERE id = ?",
            (next_index, "completed" if finished else "active", ts if finished else None, sid),
        )
        if finished:
            payload = json.dumps(
                {
                    "event": "session.completed",
                    "sessionId": sid,
                    "participantId": p["id"],
                    "sceneId": scene["id"],
                    "turns": len(scene["turns"]),
                    "completedAt": ts,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            db.execute(
                """INSERT INTO webhook_outbox (event, payload, signature, status, created_at)
                   VALUES (?,?,?,?,?)""",
                (
                    "session.completed",
                    payload,
                    sign_payload(cfg.webhook_secret, payload),
                    "pending",
                    ts,
                ),
            )
        return {
            "reply": option["reply"],
            "feedback": option["feedback"],
            "kind": option["kind"],
            "hint": turn.get("hint") if body.hintLevel > 0 else None,
            "next": None if finished else turn_payload(scene, next_index),
            "completed": finished,
        }

    @app.get("/api/v1/reports/student/{pid}")
    def student_report(
        pid: str,
        x_admin_token: str | None = Header(None),
        authorization: str | None = Header(None),
    ):
        if not admin_ok(x_admin_token):
            p = require_participant(authorization)
            if p["id"] != pid:
                raise HTTPException(status_code=403, detail="forbidden")
        p = db.one("SELECT * FROM participants WHERE id = ?", (pid,))
        if p is None:
            raise HTTPException(status_code=404, detail="participant_not_found")
        s = db.one(
            """SELECT COUNT(*) AS sessions,
                      SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed
               FROM sessions WHERE participant_id = ?""",
            (pid,),
        )
        t = db.one(
            """SELECT COUNT(*) AS turns,
                      SUM(CASE WHEN t.hint_level > 0 THEN 1 ELSE 0 END) AS hinted,
                      AVG(t.latency_ms) AS avg_latency
               FROM turns t JOIN sessions s ON s.id = t.session_id
               WHERE s.participant_id = ?""",
            (pid,),
        )
        last = db.one(
            "SELECT MAX(started_at) AS last FROM sessions WHERE participant_id = ?", (pid,)
        )
        sr = db.one(
            """SELECT
                 SUM(CASE WHEN kind='task' THEN 1 ELSE 0 END) AS task_checkins,
                 SUM(CASE WHEN kind='quiz' THEN 1 ELSE 0 END) AS quizzes
               FROM self_reports WHERE participant_id = ?""",
            (pid,),
        )
        turns = t["turns"] or 0
        return {
            "participantId": pid,
            "code": p["code"],
            "sessions": s["sessions"] or 0,
            "completedSessions": s["completed"] or 0,
            "turns": turns,
            "hintUseRate": round((t["hinted"] or 0) / turns, 4) if turns else 0.0,
            "avgLatencyMs": int(t["avg_latency"]) if t["avg_latency"] is not None else None,
            "taskCheckins": sr["task_checkins"] or 0,
            "quizzes": sr["quizzes"] or 0,
            "lastActivity": last["last"],
        }

    @app.get("/api/v1/moderation/queue")
    def moderation_queue(x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        rows = db.query(
            """SELECT id, participant_id, source, ref_id, excerpt, risk_flags, created_at
               FROM moderation_items WHERE status = 'pending'
               ORDER BY id DESC"""
        )
        return {
            "items": [
                {
                    "id": r["id"],
                    "participantId": r["participant_id"],
                    "source": r["source"],
                    "refId": r["ref_id"],
                    "excerpt": r["excerpt"],
                    "riskFlags": json.loads(r["risk_flags"]),
                    "status": "pending",
                    "createdAt": r["created_at"],
                }
                for r in rows
            ]
        }

    @app.post("/api/v1/moderation/review")
    def moderation_review(body: ReviewIn, x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        item = db.one("SELECT * FROM moderation_items WHERE id = ?", (body.itemId,))
        if item is None:
            raise HTTPException(status_code=404, detail="item_not_found")
        if item["status"] != "pending":
            raise HTTPException(status_code=409, detail="item_already_reviewed")
        db.execute(
            """UPDATE moderation_items
               SET status='reviewed', reviewer=?, decision=?, reason=?, reviewed_at=?
               WHERE id=?""",
            ("admin", body.decision, body.reason, now(), body.itemId),
        )
        db.execute(
            "INSERT INTO audit_log (actor, action, target, detail, created_at) VALUES (?,?,?,?,?)",
            ("admin", "moderation.review", str(body.itemId), body.decision, now()),
        )
        return {
            "itemId": body.itemId,
            "status": "reviewed",
            "decision": body.decision,
            "reviewedAt": now(),
        }

    @app.delete("/api/v1/subject", status_code=204)
    def delete_subject(authorization: str | None = Header(None)):
        p = require_participant(authorization)
        db.execute("DELETE FROM participants WHERE id = ?", (p["id"],))
        db.execute(
            "INSERT INTO audit_log (actor, action, target, detail, created_at) VALUES (?,?,?,?,?)",
            (p["id"], "subject.delete", p["id"], "{}", now()),
        )
        return Response(status_code=204)

    @app.get("/api/v1/admin/audit")
    def audit_log(x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        rows = db.query(
            "SELECT id, actor, action, target, created_at FROM audit_log ORDER BY id DESC LIMIT 50"
        )
        return {
            "items": [
                {
                    "id": r["id"],
                    "actor": r["actor"],
                    "action": r["action"],
                    "target": r["target"],
                    "createdAt": r["created_at"],
                }
                for r in rows
            ]
        }

    @app.get("/api/v1/reports/cohort")
    def cohort_report(
        sceneId: str | None = None, x_admin_token: str | None = Header(None)
    ):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        where = "WHERE s.scene_id = ?" if sceneId else ""
        params: tuple = (sceneId,) if sceneId else ()
        s = db.one(
            f"""SELECT COUNT(DISTINCT s.participant_id) AS participants,
                       COUNT(*) AS sessions,
                       SUM(CASE WHEN s.status='completed' THEN 1 ELSE 0 END) AS completed
                FROM sessions s {where}""",
            params,
        )
        participants = s["participants"] or 0
        if participants < 10:
            return {
                "sceneId": sceneId,
                "participants": participants,
                "sessions": s["sessions"] or 0,
                "suppressed": True,
                "message": "样本不足 10 人，已抑制",
            }
        t = db.one(
            f"""SELECT COUNT(*) AS turns,
                       SUM(CASE WHEN t.hint_level > 0 THEN 1 ELSE 0 END) AS hinted,
                       AVG(t.latency_ms) AS avg_latency
                FROM turns t JOIN sessions s ON s.id = t.session_id {where}""",
            params,
        )
        turns = t["turns"] or 0
        return {
            "sceneId": sceneId,
            "participants": participants,
            "sessions": s["sessions"] or 0,
            "completedSessions": s["completed"] or 0,
            "turns": turns,
            "hintUseRate": round((t["hinted"] or 0) / turns, 4) if turns else 0.0,
            "avgLatencyMs": int(t["avg_latency"]) if t["avg_latency"] is not None else None,
            "suppressed": False,
        }

    @app.get("/api/v1/admin/outbox")
    def outbox(x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        rows = db.query(
            """SELECT id, event, payload, signature, status, attempts, created_at
               FROM webhook_outbox ORDER BY id DESC LIMIT 50"""
        )
        return {
            "items": [
                {
                    "id": r["id"],
                    "event": r["event"],
                    "payload": r["payload"],
                    "signature": r["signature"],
                    "status": r["status"],
                    "attempts": r["attempts"],
                    "createdAt": r["created_at"],
                }
                for r in rows
            ]
        }

    @app.post("/api/v1/emotion/quiz/submit")
    def submit_quiz(body: QuizIn, authorization: str | None = Header(None)):
        p = require_participant(authorization)
        if not has_consent(p["id"]):
            raise HTTPException(status_code=403, detail="consent_required")
        item = content.emotion_items.get(body.itemId)
        if item is None:
            raise HTTPException(status_code=404, detail="item_not_found")
        if body.choice not in {o["id"] for o in item["options"]}:
            raise HTTPException(status_code=400, detail="choice_not_found")
        db.execute(
            """INSERT INTO self_reports
               (participant_id, session_id, kind, ref_id, mood, confidence, note, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (p["id"], None, "quiz", body.itemId, None, None, body.choice, now()),
        )
        return {
            "itemId": body.itemId,
            "correct": body.choice == item["answer"],
            "answer": item["answer"],
            "explain": item["explain"],
        }

    @app.post("/api/v1/tasks/{task_id}/checkin", status_code=201)
    def task_checkin(
        task_id: str, body: TaskCheckinIn, authorization: str | None = Header(None)
    ):
        p = require_participant(authorization)
        if not has_consent(p["id"]):
            raise HTTPException(status_code=403, detail="consent_required")
        task = content.tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task_not_found")
        cur = db.execute(
            """INSERT INTO self_reports
               (participant_id, session_id, kind, ref_id, mood, confidence, note, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (p["id"], None, "task", task_id, body.mood, None, body.note, now()),
        )
        return {"checkinId": cur.lastrowid, "taskId": task_id, "mood": body.mood}

    @app.post("/api/v1/coach/reply")
    def coach_reply(body: CoachIn, authorization: str | None = Header(None)):
        p = require_participant(authorization)
        if not has_consent(p["id"]):
            raise HTTPException(status_code=403, detail="consent_required")
        if body.sceneId not in content.scenes:
            raise HTTPException(status_code=404, detail="scene_not_found")

        risk_flags = detect_risk(body.text)
        if risk_flags:
            moderation_id = add_moderation(
                p["id"], "coach_free_text", body.sceneId, body.text, risk_flags
            )
            return {
                "matched": False,
                "intent": "safety",
                "reply": SAFE_REPLY,
                "suggestions": [],
                "disclaimer": DISCLAIMER,
                "safety": {"escalated": True, "moderationId": moderation_id},
            }

        return suggestions_for(body.sceneId, body.text)

    def _chat_authorized(authorization: str | None) -> bool:
        if not authorization or not authorization.startswith("Bearer "):
            return False
        return same(authorization.removeprefix("Bearer ").strip(), cfg.chat_token)

    def _content_text(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") in ("text", "input_text"):
                    parts.append(str(part.get("text", "")))
            return "\n".join(p for p in parts if p)
        return ""

    def _completion(content: str, model: str, usage: dict, xq: dict) -> dict:
        return {
            "id": "chatcmpl-" + str(int(time.time() * 1000)),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": usage or {},
            "xq": xq,
        }

    @app.post("/v1/chat/completions")
    @app.post("/api/v1/chat/completions")
    def chat_completions(
        body: ChatCompletionIn, authorization: str | None = Header(None)
    ):
        if not _chat_authorized(authorization):
            raise HTTPException(status_code=401, detail="invalid_chat_token")
        messages = [
            {"role": m.role, "content": _content_text(m.content)}
            for m in body.messages
            if m.role in ("user", "assistant", "system")
        ]
        if not messages:
            raise HTTPException(status_code=400, detail="messages_required")

        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        risk_flags = detect_risk(last_user)
        if risk_flags:
            moderation_id = add_moderation(
                None, "chat_free_text", "chat", last_user, risk_flags
            )
            return _completion(
                SAFE_REPLY,
                "xingqiao-guard",
                {},
                {"safety": {"escalated": True, "moderationId": moderation_id}},
            )

        result = guarded_chat(
            qwen, messages, model=body.model, max_tokens=body.max_tokens or 400
        )
        xq = {"guard": result["guard"], "model": result["model"]}
        if result.get("error"):
            xq["error"] = result["error"]
        return _completion(result["content"], result["model"], result["usage"], xq)

    @app.get("/api/v1/realtime/status")
    def realtime_status(x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        try:
            models = qwen.models()
        except QwenError as exc:
            return {"ok": False, "error": str(exc)}
        target = cfg.qwen_realtime_model
        return {
            "ok": target in models,
            "textModel": cfg.qwen_text_model,
            "textAvailable": cfg.qwen_text_model in models,
            "realtimeModel": target,
            "realtimeAvailable": target in models,
        }

    @app.post("/api/v1/safety/check")
    def safety_check(body: SafetyIn, x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        return check_text(body.text)

    @app.get("/api/v1/rules")
    def rules_catalog(x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        return {
            "version": RULES_VERSION,
            "items": list_rules(),
            "safePhrases": SAFE_PHRASES,
        }

    @app.get("/api/v1/corpus/stats")
    def corpus_stats_endpoint(x_admin_token: str | None = Header(None)):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        return corpus_stats(db)

    @app.get("/api/v1/corpus/search")
    def corpus_search_endpoint(
        q: str = "", limit: int = 10, x_admin_token: str | None = Header(None)
    ):
        if not admin_ok(x_admin_token):
            raise HTTPException(status_code=401, detail="invalid_admin_token")
        if not q.strip():
            raise HTTPException(status_code=400, detail="query_required")
        return {"items": corpus_search(db, q, limit)}

    return app