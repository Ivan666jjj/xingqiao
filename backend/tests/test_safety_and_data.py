from conftest import ADMIN, auth, enroll, give_consent, start


def _first_turn(client, token):
    session = start(client, token).json()
    return session, session["turn"]


def test_risk_text_escalates_to_moderation_queue(client):
    p = enroll(client, code="P-RISK")
    give_consent(client, p["token"])
    session, _ = _first_turn(client, p["token"])

    r = client.post(
        f"/api/v1/sessions/{session['sessionId']}/turns",
        json={
            "turnIndex": 0,
            "optionId": "a",
            "latencyMs": 900,
            "hintLevel": 0,
            "freeText": "我不想活了",
        },
        headers=auth(p["token"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "safety"
    assert body["safety"]["escalated"] is True
    assert body["next"] is None

    q = client.get("/api/v1/moderation/queue", headers=ADMIN)
    assert q.status_code == 200
    items = q.json()["items"]
    assert len(items) == 1
    assert "self_harm" in items[0]["riskFlags"]
    assert items[0]["status"] == "pending"


def test_flagged_session_cannot_continue(client):
    p = enroll(client, code="P-FLAG")
    give_consent(client, p["token"])
    session, _ = _first_turn(client, p["token"])
    client.post(
        f"/api/v1/sessions/{session['sessionId']}/turns",
        json={"turnIndex": 0, "optionId": "a", "latencyMs": 100, "freeText": "他们一直欺负我"},
        headers=auth(p["token"]),
    )
    r = client.post(
        f"/api/v1/sessions/{session['sessionId']}/turns",
        json={"turnIndex": 1, "optionId": "a", "latencyMs": 100},
        headers=auth(p["token"]),
    )
    assert r.status_code == 409


def test_reviewer_can_close_moderation_item(client):
    p = enroll(client, code="P-REV")
    give_consent(client, p["token"])
    session, _ = _first_turn(client, p["token"])
    client.post(
        f"/api/v1/sessions/{session['sessionId']}/turns",
        json={"turnIndex": 0, "optionId": "a", "latencyMs": 100, "freeText": "我想自伤"},
        headers=auth(p["token"]),
    )
    item = client.get("/api/v1/moderation/queue", headers=ADMIN).json()["items"][0]

    r = client.post(
        "/api/v1/moderation/review",
        json={"itemId": item["id"], "decision": "escalate", "reason": "已通知监护人"},
        headers=ADMIN,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "reviewed"

    q = client.get("/api/v1/moderation/queue", headers=ADMIN).json()["items"]
    assert q == []


def test_delete_subject_removes_all_records_and_audits(client):
    p = enroll(client, code="P-DEL")
    give_consent(client, p["token"])
    session, _ = _first_turn(client, p["token"])

    r = client.delete("/api/v1/subject", headers=auth(p["token"]))
    assert r.status_code == 204

    # token is gone
    assert client.get(
        f"/api/v1/reports/student/{p['participantId']}", headers=auth(p["token"])
    ).status_code == 401
    # admin sees no participant
    assert client.get(
        f"/api/v1/reports/student/{p['participantId']}", headers=ADMIN
    ).status_code == 404
    # child rows are actually gone, not orphaned
    db = client.app.state.db
    assert db.one("SELECT COUNT(*) AS c FROM sessions")["c"] == 0
    assert db.one("SELECT COUNT(*) AS c FROM turns")["c"] == 0
    assert db.one("SELECT COUNT(*) AS c FROM consents")["c"] == 0

    # audit trail remains
    audit = client.get("/api/v1/admin/audit", headers=ADMIN).json()["items"]
    assert any(a["action"] == "subject.delete" for a in audit)