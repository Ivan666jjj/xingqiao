#!/usr/bin/env python3
"""端到端冒烟：报名 → 同意 → 三回合 → 报告。只用标准库。"""
import json
import os
import time
import urllib.error
import urllib.request

BASE = os.getenv("XQ_BASE", "http://127.0.0.1:8000")
ADMIN = os.getenv("XQ_ADMIN_TOKEN", "dev-admin-token")


def call(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None


def main():
    code, health = call("GET", "/health")
    assert code == 200, (code, health)
    print("health:", health)

    code, p = call(
        "POST",
        "/api/v1/participants",
        {
            "code": f"SMOKE-{int(time.time())}",
            "ageBand": "12-14",
            "gender": "unspecified",
            "diagnosisStatus": "diagnosed",
            "languageLevel": "verbal",
        },
        {"X-Admin-Token": ADMIN},
    )
    assert code == 201, (code, p)
    print("participant:", p["participantId"])

    auth = {"Authorization": f"Bearer {p['token']}"}
    code, consent = call(
        "POST",
        "/api/v1/consent",
        {
            "version": "2026-11-21",
            "scopes": ["practice"],
            "guardianConfirmed": True,
            "childAssent": True,
            "method": "digital",
            "guardianRef": "smoke-guardian",
        },
        auth,
    )
    assert code == 201, (code, consent)
    print("consent:", consent["consentId"])

    code, coach = call(
        "POST", "/api/v1/coach/reply", {"sceneId": "borrow", "text": "给我笔记"}, auth
    )
    assert code == 200 and coach["suggestions"], (code, coach)
    print("coach:", coach["intent"], "| suggestions:", len(coach["suggestions"]))

    code, scenes = call("GET", "/api/v1/scenes")
    assert code == 200 and scenes["items"], (code, scenes)
    print("scenes:", [s["id"] for s in scenes["items"]])

    code, session = call(
        "POST", "/api/v1/sessions", {"sceneId": "borrow", "mode": "solo"}, auth
    )
    assert code == 201, (code, session)
    sid = session["sessionId"]
    print("session:", sid, "turns:", session["totalTurns"])

    total = session["totalTurns"]
    for i in range(total):
        code, body = call(
            "POST",
            f"/api/v1/sessions/{sid}/turns",
            {"turnIndex": i, "optionId": "a", "latencyMs": 900 + i * 100, "hintLevel": 0},
            auth,
        )
        assert code == 200, (code, body)
        print(f"turn {i + 1}: {body['kind']} | {body['reply']}")

    code, report = call("GET", f"/api/v1/reports/student/{p['participantId']}", None, auth)
    assert code == 200, (code, report)
    print("report:", json.dumps(report, ensure_ascii=False, indent=2))

    code, corpus = call("GET", "/api/v1/corpus/stats", None, {"X-Admin-Token": ADMIN})
    assert code == 200, (code, corpus)
    print("corpus:", corpus["total"], "docs |", corpus["purpose"])

    code, verdict = call(
        "POST",
        "/api/v1/safety/check",
        {"text": "自闭症是可以治愈的。"},
        {"X-Admin-Token": ADMIN},
    )
    assert code == 200 and verdict["allowed"] is False, (code, verdict)
    print("guard:", verdict["hits"][0]["ruleId"], "| alternatives:", len(verdict["safeAlternatives"]))
    print("\nOK")


if __name__ == "__main__":
    main()