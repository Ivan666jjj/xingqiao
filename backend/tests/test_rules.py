from conftest import ADMIN

from app.coach import BANK
from app.rules import check_text, list_rules


def test_blocks_cure_narrative():
    r = check_text("坚持训练，自闭症是可以治愈的。")
    assert r["allowed"] is False
    assert any(h["category"] == "cure_narrative" for h in r["hits"])
    assert r["safeAlternatives"]


def test_blocks_diagnosis_claim_and_medical_advice():
    assert check_text("根据你的描述，你就是自闭症。")["allowed"] is False
    assert check_text("把药停了，不用看医生。")["allowed"] is False


def test_blocks_stigma_and_minimizing():
    assert check_text("你这样看起来有点不正常。")["allowed"] is False
    assert check_text("别矫情了，想开点。")["allowed"] is False


def test_blocks_forced_eye_contact_and_normalization_pressure():
    assert check_text("说话的时候看着我的眼睛。")["allowed"] is False
    assert check_text("你要正常一点，别人才会喜欢你。")["allowed"] is False


def test_blocks_dependency_and_privacy_probe():
    assert check_text("只有我懂你，别去找别人。")["allowed"] is False
    assert check_text("你家住哪里？学校叫什么？")["allowed"] is False


def test_allows_supportive_language():
    r = check_text("我在，你慢慢说。不想说也可以，我们可以先停一下。")
    assert r["allowed"] is True
    assert r["hits"] == []


def test_rule_catalog_contains_alternatives():
    rules = list_rules()
    assert len(rules) >= 10
    assert all(r["sayInstead"] for r in rules)
    assert {r["severity"] for r in rules} <= {"block", "warn"}
    assert {r["evidenceSource"] for r in rules} <= {"bcc", "research"}


def test_every_coach_suggestion_passes_the_guard():
    for (scene, intent), items in BANK.items():
        for text, _ in items:
            r = check_text(text)
            assert r["allowed"] is True, (scene, intent, text, r["hits"])


def test_safety_check_endpoint_requires_admin(client):
    r = client.post("/api/v1/safety/check", json={"text": "我在，你慢慢说。"})
    assert r.status_code == 401


def test_safety_check_endpoint_returns_hits_and_alternatives(client):
    r = client.post(
        "/api/v1/safety/check",
        json={"text": "自闭症是可以治愈的。"},
        headers=ADMIN,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is False
    assert body["hits"]
    assert body["safeAlternatives"]


def test_rules_endpoint_lists_catalog(client):
    r = client.get("/api/v1/rules", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["version"]
    assert len(body["items"]) >= 10
    assert body["safePhrases"]