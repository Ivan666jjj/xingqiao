from fastapi.testclient import TestClient

from conftest import ADMIN
from app.chat import FALLBACK
from app.qwen import QwenError


class FakeQwen:
    model = "qwen-plus"

    def __init__(self, replies, models=None, error=None):
        self.replies = list(replies)
        self.calls = []
        self._models = models or ["qwen-plus", "qwen3.8-omni-flash-realtime"]
        self.error = error

    def chat(self, messages, model=None, max_tokens=400):
        self.calls.append(messages)
        if self.error:
            raise QwenError(self.error)
        content = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    def models(self):
        if self.error:
            raise QwenError(self.error)
        return self._models


def make_client(tmp_path, monkeypatch, fake):
    monkeypatch.setenv("XQ_DB", str(tmp_path / "chat.db"))
    monkeypatch.setenv("XQ_CHAT_TOKEN", "test-chat")
    monkeypatch.setenv("XQ_ADMIN_TOKEN", "test-admin")
    monkeypatch.setenv("XQ_RATE_LIMIT", "10000")
    from app.main import create_app

    return TestClient(create_app(qwen_client=fake))


def body(text="你好"):
    return {
        "model": "xingqiao",
        "messages": [{"role": "user", "content": text}],
        "max_tokens": 50,
    }


AUTH = {"Authorization": "Bearer test-chat"}


def test_chat_completion_requires_chat_token(tmp_path, monkeypatch):
    c = make_client(tmp_path, monkeypatch, FakeQwen(["你好"]))
    assert c.post("/v1/chat/completions", json=body()).status_code == 401


def test_chat_completion_returns_openai_shape_and_system_prompt(tmp_path, monkeypatch):
    fake = FakeQwen(["你好，我在。"])
    c = make_client(tmp_path, monkeypatch, fake)
    r = c.post("/v1/chat/completions", json=body(), headers=AUTH)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["object"] == "chat.completion"
    assert d["choices"][0]["message"]["content"] == "你好，我在。"
    assert d["xq"]["guard"]["allowed"] is True
    assert fake.calls[0][0]["role"] == "system"
    assert "星桥" in fake.calls[0][0]["content"]


def test_roleplay_mode_uses_scene_specific_prompt(tmp_path, monkeypatch):
    fake = FakeQwen(["往前走两个路口，右边有家书店。"])
    c = make_client(tmp_path, monkeypatch, fake)
    payload = body()
    payload["xq_mode"] = "roleplay"
    payload["xq_scene"] = "向路人问去书店的路"
    r = c.post("/v1/chat/completions", json=payload, headers=AUTH)
    assert r.status_code == 200
    system = fake.calls[0][0]["content"]
    assert "对方" in system
    assert "书店" in system


def test_banned_output_is_regenerated_once(tmp_path, monkeypatch):
    fake = FakeQwen(["自闭症是可以治愈的。", "我在，你慢慢说。"])
    c = make_client(tmp_path, monkeypatch, fake)
    r = c.post("/v1/chat/completions", json=body(), headers=AUTH)
    d = r.json()
    assert d["choices"][0]["message"]["content"] == "我在，你慢慢说。"
    assert d["xq"]["guard"]["retried"] is True
    assert d["xq"]["guard"]["fallback"] is False
    assert len(fake.calls) == 2


def test_banned_twice_falls_back_to_safe_template(tmp_path, monkeypatch):
    fake = FakeQwen(["自闭症是可以治愈的。", "你别想太多。"])
    c = make_client(tmp_path, monkeypatch, fake)
    r = c.post("/v1/chat/completions", json=body(), headers=AUTH)
    d = r.json()
    assert d["choices"][0]["message"]["content"] == FALLBACK
    assert d["xq"]["guard"]["fallback"] is True
    assert "治愈" not in d["choices"][0]["message"]["content"]


def test_risk_input_escalates_without_calling_model(tmp_path, monkeypatch):
    fake = FakeQwen(["不应该被调用"])
    c = make_client(tmp_path, monkeypatch, fake)
    r = c.post("/v1/chat/completions", json=body("我不想活了"), headers=AUTH)
    d = r.json()
    assert d["xq"]["safety"]["escalated"] is True
    assert fake.calls == []
    q = c.get("/api/v1/moderation/queue", headers=ADMIN).json()["items"]
    assert q and q[0]["source"] == "chat_free_text"


def test_qwen_error_returns_safe_fallback(tmp_path, monkeypatch):
    fake = FakeQwen(["x"], error="http_401")
    c = make_client(tmp_path, monkeypatch, fake)
    r = c.post("/v1/chat/completions", json=body(), headers=AUTH)
    assert r.status_code == 200
    d = r.json()
    assert d["choices"][0]["message"]["content"] == FALLBACK
    assert d["xq"]["error"]


def test_realtime_status_reports_model_availability(tmp_path, monkeypatch):
    fake = FakeQwen(["x"])
    c = make_client(tmp_path, monkeypatch, fake)
    r = c.get("/api/v1/realtime/status", headers=ADMIN)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["realtimeAvailable"] is True