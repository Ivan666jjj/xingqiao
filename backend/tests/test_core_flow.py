from conftest import ADMIN, auth, enroll, give_consent, start


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_participant_creation_requires_admin_token(client):
    body = {
        "code": "P-X",
        "ageBand": "12-14",
        "gender": "unspecified",
        "diagnosisStatus": "diagnosed",
        "languageLevel": "verbal",
    }
    assert client.post("/api/v1/participants", json=body).status_code == 401
    assert (
        client.post(
            "/api/v1/participants", json=body, headers={"X-Admin-Token": "wrong"}
        ).status_code
        == 401
    )


def test_session_requires_active_consent(client):
    p = enroll(client)
    r = start(client, p["token"])
    assert r.status_code == 403


def test_full_scene_flow_and_student_report(client):
    p = enroll(client)
    give_consent(client, p["token"])

    r = start(client, p["token"])
    assert r.status_code == 201, r.text
    session = r.json()
    assert session["totalTurns"] == 3
    assert session["turn"]["index"] == 0
    assert [o["id"] for o in session["turn"]["options"]] == ["a", "b", "c"]
    assert "feedback" not in session["turn"]["options"][0]
    assert "kind" not in session["turn"]["options"][0]

    sid = session["sessionId"]
    for i, latency in enumerate([1000, 1100, 1200]):
        r = client.post(
            f"/api/v1/sessions/{sid}/turns",
            json={
                "turnIndex": i,
                "optionId": "a",
                "latencyMs": latency,
                "hintLevel": 0,
            },
            headers=auth(p["token"]),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["kind"] == "ok"
        assert body["feedback"]

    assert body["completed"] is True
    assert body["next"] is None

    r = client.get(f"/api/v1/reports/student/{p['participantId']}", headers=auth(p["token"]))
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["sessions"] == 1
    assert rep["completedSessions"] == 1
    assert rep["turns"] == 3
    assert rep["hintUseRate"] == 0.0
    assert rep["avgLatencyMs"] == 1100


def test_hint_level_is_recorded_and_reported(client):
    p = enroll(client, code="P-002")
    give_consent(client, p["token"])
    session = start(client, p["token"]).json()

    r = client.post(
        f"/api/v1/sessions/{session['sessionId']}/turns",
        json={"turnIndex": 0, "optionId": "a", "latencyMs": 800, "hintLevel": 2},
        headers=auth(p["token"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["hint"]

    rep = client.get(
        f"/api/v1/reports/student/{p['participantId']}", headers=auth(p["token"])
    ).json()
    assert rep["hintUseRate"] == 1.0