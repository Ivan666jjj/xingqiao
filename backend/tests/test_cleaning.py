from app.cleaning import (
    dedupe,
    flags_for,
    normalize,
    process_rows,
    redact,
    status_for,
)


def test_normalize_and_redact_pii():
    raw = "  【自闭症】 联系电话 13800138000，邮箱 a@b.com，链接 https://x.cn "
    out = redact(normalize(raw))
    assert "自闭症" in out
    assert "【" not in out and "】" not in out
    assert "13800138000" not in out and "[PHONE]" in out
    assert "a@b.com" not in out and "[EMAIL]" in out
    assert "https://x.cn" not in out and "[URL]" in out


def test_redact_id_and_contact():
    assert "[ID]" in redact("身份证 110101199001011234")
    assert "[CONTACT]" in redact("加我微信：abc_12345")


def test_flags_detect_misuse_and_sensitive_content():
    assert "non_autism_usage" in flags_for("我自闭了，今晚不想说话")
    assert "self_harm" in flags_for("我不想活了")
    assert "sexual_content" in flags_for("他被脱裤猥亵")
    assert "stigma" in flags_for("他就是个智障")


def test_stigma_and_cure_narrative_are_flagged():
    assert "stigma" in flags_for("自闭症的人蛮可怜的")
    assert "stigma" in flags_for("把他们叫做弱智或白痴")
    assert "cure_narrative" in flags_for("希望他早日治愈自闭症")
    assert "misinformation" in flags_for("冰箱母亲导致孩子自闭症")


def test_colloquial_self_diagnosis_is_misuse():
    assert "non_autism_usage" in flags_for("我觉得我得了自闭症，不想说话")
    assert "non_autism_usage" in flags_for("我好像患上自闭了")


def test_informal_channel_is_quarantined():
    flags = flags_for("自闭症儿童在超市练习结账，家长在旁边等着。", channel="口语")
    assert "informal_channel" in flags
    assert status_for(flags) == "quarantine"


def test_normal_sentence_has_no_blocking_flags():
    flags = flags_for("自闭症儿童在超市练习排队结账，家长在旁边等着。", channel="新闻")
    assert "non_autism_usage" not in flags
    assert "self_harm" not in flags
    assert "sexual_content" not in flags
    assert "stigma" not in flags


def test_status_mapping():
    assert status_for(["sexual_content"]) == "quarantine"
    assert status_for(["self_harm"]) == "quarantine"
    assert status_for(["non_autism_usage"]) == "quarantine"
    assert status_for(["stigma"]) == "review"
    assert status_for(["pii"]) == "review"
    assert status_for([]) == "clean"


def test_dedupe_uses_normalized_text():
    records = [
        {"text": "自闭症 儿童 练习 结账。"},
        {"text": "自闭症  儿童 练习 结账"},
        {"text": "另一条完全不同的句子"},
    ]
    assert len(dedupe(records)) == 2


def test_process_rows_quarantines_sensitive_rows():
    rows = [
        {
            "序号": "1",
            "检索词": "自闭症",
            "频道": "新闻",
            "完整上下文": "自闭症儿童在超市练习排队结账，家长在旁边的休息区等着他。",
            "语料来源": "新闻-1",
            "来源ID": "a1",
            "疑似非自闭症用法": "",
        },
        {
            "序号": "2",
            "检索词": "自闭",
            "频道": "口语",
            "完整上下文": "我自闭了，今晚不想说话",
            "语料来源": "口语-2",
            "来源ID": "a2",
            "疑似非自闭症用法": "是",
        },
        {
            "序号": "3",
            "检索词": "自闭症",
            "频道": "口语",
            "完整上下文": "他被脱裤猥亵，后来一直不敢出门",
            "语料来源": "口语-3",
            "来源ID": "a3",
            "疑似非自闭症用法": "",
        },
    ]
    out = process_rows(rows)
    assert len(out) == 3
    by_id = {r["sourceId"]: r for r in out}
    assert by_id["a1"]["status"] == "clean"
    assert by_id["a2"]["status"] == "quarantine"
    assert by_id["a3"]["status"] == "quarantine"
    assert all("脱裤" not in r["text"] for r in out if r["status"] == "clean")


def test_short_text_is_quarantined():
    rows = [
        {
            "序号": "1",
            "检索词": "自闭症",
            "频道": "新闻",
            "完整上下文": "自闭症",
            "语料来源": "新闻-1",
            "来源ID": "s1",
            "疑似非自闭症用法": "",
        }
    ]
    assert process_rows(rows)[0]["status"] == "quarantine"