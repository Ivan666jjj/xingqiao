import json

from conftest import ADMIN, auth, enroll, give_consent, start

from app.security import sign_payload


def _complete_borrow(client, token):
    session = start(client, token, "borrow").json()
    sid = session["sessionId"]
    for i in range(3):
        r = client.post(
            f"/api/v1/sessions/{sid}/turns",
            json={"turnIndex": i, "optionId": "a", "latencyMs": 900 + i * 100},
            headers=auth(token),
        )
        assert r.status_code == 200, r.text
    return sid


def test_duplicate_turn_is_rejected(client):
    p = enroll(client, code="P-DUP")
    give_consent(client, p["token"])
    sid = start(client, p["token"]).json()["sessionId"]

    payload = {"turnIndex": 0, "optionId": "a", "latencyMs": 100}
    assert client.post(
        f"/api/v1/sessions/{sid}/turns", json=payload, headers=auth(p["token"])
    ).status_code == 200
    assert client.post(
        f"/api/v1/sessions/{sid}/turns", json=payload, headers=auth(p["token"])
    ).status_code == 409


def test_cohort_report_is_suppressed_below_ten(client):
    for i in range(9):
        p = enroll(client, code=f"P-C{i:02d}")
        give_consent(client, p["token"])
        start(client, p["token"], "borrow")

    r = client.get("/api/v1/reports/cohort?sceneId=borrow", headers=ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["suppressed"] is True
    assert body["participants"] == 9


def test_cohort_report_releases_at_ten(client):
    for i in range(10):
        p = enroll(client, code=f"P-D{i:02d}")
        give_consent(client, p["token"])
        start(client, p["token"], "borrow")

    r = client.get("/api/v1/reports/cohort?sceneId=borrow", headers=ADMIN)
    body = r.json()
    assert body["suppressed"] is False
    assert body["participants"] == 10
    assert body["sessions"] == 10
    assert "hintUseRate" in body


def test_completion_writes_signed_webhook_outbox(client):
    p = enroll(client, code="P-HOOK")
    give_consent(client, p["token"])
    _complete_borrow(client, p["token"])

    r = client.get("/api/v1/admin/outbox", headers=ADMIN)
    assert r.status_code == 200, r.text
    rows = r.json()["items"]
    assert len(rows) == 1
    row = rows[0]
    assert row["event"] == "session.completed"
    assert row["status"] == "pending"
    assert row["signature"] == sign_payload("test-secret", row["payload"])
    payload = json.loads(row["payload"])
    assert payload["sceneId"] == "borrow"
    assert payload["turns"] == 3
    assert "code" not in payload


def test_emotion_quiz_returns_feedback(client):
    p = enroll(client, code="P-QUIZ")
    give_consent(client, p["token"])
    r = client.post(
        "/api/v1/emotion/quiz/submit",
        json={"itemId": "emo-1", "choice": "b", "rtMs": 1500},
        headers=auth(p["token"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["correct"] is True
    assert r.json()["explain"]

    r = client.post(
        "/api/v1/emotion/quiz/submit",
        json={"itemId": "emo-1", "choice": "a", "rtMs": 800},
        headers=auth(p["token"]),
    )
    assert r.json()["correct"] is False


def test_task_checkin_is_stored_and_reported(client):
    p = enroll(client, code="P-TASK")
    give_consent(client, p["token"])
    r = client.post(
        "/api/v1/tasks/task-borrow-1/checkin",
        json={"note": "在小区里试了一次", "mood": 3},
        headers=auth(p["token"]),
    )
    assert r.status_code == 201, r.text

    rep = client.get(
        f"/api/v1/reports/student/{p['participantId']}", headers=auth(p["token"])
    ).json()
    assert rep["taskCheckins"] == 1
    assert rep["quizzes"] == 0