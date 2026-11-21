from conftest import ADMIN

from app.corpus import import_records, search, stats
from app.db import Database


def rec(text, channel="新闻", sid="s1", keyword="自闭症"):
    return {
        "text": text,
        "channel": channel,
        "keyword": keyword,
        "sourceId": sid,
        "source": "BCC",
        "flags": [],
        "status": "clean",
    }


def test_import_search_and_stats(tmp_path):
    db = Database(str(tmp_path / "corpus.db"))
    n = import_records(
        db,
        [
            rec("自闭症儿童在超市练习排队结账，家长在休息区等着。", sid="s1"),
            rec("孤独症青年在公交车上练习问路，先去哪里要说清楚。", sid="s2", keyword="孤独症"),
        ],
    )
    assert n == 2

    s = stats(db)
    assert s["total"] == 2
    assert s["byChannel"]["新闻"] == 2

    hits = search(db, "超市")
    assert len(hits) == 1
    assert "超市" in hits[0]["text"]
    assert search(db, "完全不存在的词") == []


def test_import_is_idempotent(tmp_path):
    db = Database(str(tmp_path / "corpus2.db"))
    items = [rec("自闭症儿童在超市练习排队结账，家长在休息区等着。")]
    assert import_records(db, items) == 1
    assert import_records(db, items) == 1
    assert stats(db)["total"] == 1


def test_corpus_endpoints_require_admin_and_return_results(client):
    assert client.get("/api/v1/corpus/stats").status_code == 401
    assert client.get("/api/v1/corpus/search?q=超市").status_code == 401

    import_records(
        client.app.state.db,
        [rec("自闭症儿童在超市练习排队结账，家长在休息区等着。")],
    )

    s = client.get("/api/v1/corpus/stats", headers=ADMIN)
    assert s.status_code == 200
    assert s.json()["total"] == 1

    r = client.get("/api/v1/corpus/search?q=超市", headers=ADMIN)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert "purpose" in items[0] and items[0]["purpose"] == "discourse"