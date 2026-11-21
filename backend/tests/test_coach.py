from conftest import ADMIN, auth, enroll, give_consent


def test_coach_requires_consent(client):
    p = enroll(client, code="C-1")
    r = client.post(
        "/api/v1/coach/reply",
        json={"sceneId": "borrow", "text": "给我笔记"},
        headers=auth(p["token"]),
    )
    assert r.status_code == 403


def test_coach_suggests_for_direct_demand(client):
    p = enroll(client, code="C-2")
    give_consent(client, p["token"])
    r = client.post(
        "/api/v1/coach/reply",
        json={"sceneId": "borrow", "text": "给我笔记"},
        headers=auth(p["token"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matched"] is True
    assert body["intent"] == "direct_demand"
    assert len(body["suggestions"]) >= 1
    assert all("错了" not in s["text"] for s in body["suggestions"])
    assert body["safety"]["escalated"] is False


def test_coach_handles_refusal_repair(client):
    p = enroll(client, code="C-3")
    give_consent(client, p["token"])
    r = client.post(
        "/api/v1/coach/reply",
        json={"sceneId": "rejected", "text": "为什么别人可以借你就不行"},
        headers=auth(p["token"]),
    )
    body = r.json()
    assert body["intent"] == "retaliate"
    assert body["suggestions"]


def test_coach_unknown_text_returns_scaffolds_not_fake_empathy(client):
    p = enroll(client, code="C-4")
    give_consent(client, p["token"])
    r = client.post(
        "/api/v1/coach/reply",
        json={"sceneId": "borrow", "text": "今天天气不错"},
        headers=auth(p["token"]),
    )
    body = r.json()
    assert body["matched"] is False
    assert len(body["suggestions"]) == 2
    assert body["disclaimer"]


def test_coach_risk_escalates_without_generating(client):
    p = enroll(client, code="C-5")
    give_consent(client, p["token"])
    r = client.post(
        "/api/v1/coach/reply",
        json={"sceneId": "borrow", "text": "我不想活了"},
        headers=auth(p["token"]),
    )
    body = r.json()
    assert body["safety"]["escalated"] is True
    assert body["suggestions"] == []

    q = client.get("/api/v1/moderation/queue", headers=ADMIN).json()["items"]
    assert len(q) == 1
    assert q[0]["source"] == "coach_free_text"


def test_coach_rejects_unknown_scene(client):
    p = enroll(client, code="C-6")
    give_consent(client, p["token"])
    r = client.post(
        "/api/v1/coach/reply",
        json={"sceneId": "nope", "text": "你好"},
        headers=auth(p["token"]),
    )
    assert r.status_code == 404